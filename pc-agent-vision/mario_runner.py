# -*- coding: utf-8 -*-
"""
mario_runner.py —— 16x16 马里奥游戏运行时中枢

1. 加载 C++ 原生引擎动态库 mario16.dll；
2. 驱动高帧率物理与逻辑步进；
3. 将渲染出来的 16x16 RGB 帧以纯视觉直推至已连接的 ESP32-S3 灯板 (静音纯光效，绝不开声音)；
4. 同时通过 WebSocket 向 Web 前端实时广播帧与 HUD 计分数据；
5. 接收来自 Web 前端（触控手柄 / 键盘事件）的按键输入。
"""

import asyncio
import ctypes
import json
import os
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
DLL_PATH = ROOT / "mario16.dll"

KEY_LEFT   = 1 << 0
KEY_RIGHT  = 1 << 1
KEY_UP     = 1 << 2
KEY_DOWN   = 1 << 3
KEY_A      = 1 << 4   # Jump
KEY_B      = 1 << 5   # Run
KEY_START  = 1 << 6   # Pause / Start
KEY_SELECT = 1 << 7


class MarioSession:
    def __init__(self, controller=None, broadcast_fn=None):
        self.controller = controller
        self.broadcast_fn = broadcast_fn
        self.dll = None
        self.game = None
        self.is_running = False
        self.task = None
        self.keys_down = 0
        self.keys_pressed = 0
        self.current_hex = ""
        self.status = {
            "score": 0, "lives": 3, "coins": 0, "state": 0, "progress": 0
        }
        self.prev_mode = None
        self._load_dll()

    def _load_dll(self):
        if DLL_PATH.is_file():
            self.dll = ctypes.CDLL(str(DLL_PATH))
            self.dll.mario_create.restype = ctypes.c_void_p
            self.dll.mario_destroy.argtypes = [ctypes.c_void_p]
            self.dll.mario_reset.argtypes = [ctypes.c_void_p]
            self.dll.mario_update.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_uint16, ctypes.c_uint16]
            self.dll.mario_render.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            self.dll.mario_get_status.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint16),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
            ]

    async def start(self):
        if self.is_running:
            return True
        if not self.dll:
            raise RuntimeError("mario16.dll 未加载")

        self.game = self.dll.mario_create()
        self.is_running = True
        self.keys_down = 0
        self.keys_pressed = 0

        # 初始步进与渲染一帧，确保首次启动即可返回完整的标题画面像素
        fb0 = np.zeros((16, 16, 3), dtype=np.uint8)
        self.dll.mario_update(self.game, ctypes.c_float(0.0), ctypes.c_uint16(0), ctypes.c_uint16(0))
        self.dll.mario_render(self.game, fb0.ctypes.data_as(ctypes.c_char_p))
        self.current_hex = fb0.tobytes().hex()

        # 后台异步切换板端画布模式 (29: PIXEL_CANVAS)，保持完全静音，且不阻塞 HTTP 立即响应
        if self.controller and hasattr(self.controller, "set_mode"):
            async def _bg_set_mode():
                try:
                    self.prev_mode = getattr(self.controller, "current_mode", 23)
                    await asyncio.to_thread(self.controller.set_mode, 29)
                except Exception as e:
                    print(f"[MarioRunner] 切换板端画布模式提示: {e}")
            asyncio.create_task(_bg_set_mode())

        self.task = asyncio.create_task(self._loop())
        return True

    def key(self, k: str, down: bool):
        k = str(k).lower()
        mask = 0
        if k in ("left", "l"):
            mask = KEY_LEFT
        elif k in ("right", "r"):
            mask = KEY_RIGHT
        elif k in ("up", "u", "a", "jump"):
            mask = KEY_A
        elif k in ("down", "d"):
            mask = KEY_DOWN
        elif k in ("b", "run"):
            mask = KEY_B
        elif k in ("start", "s"):
            mask = KEY_START
        elif k in ("select", "x"):
            mask = KEY_SELECT

        if mask:
            if down:
                if not (self.keys_down & mask):
                    self.keys_pressed |= mask
                self.keys_down |= mask
            else:
                self.keys_down &= ~mask

    def reset(self):
        if self.game and self.dll:
            self.dll.mario_reset(self.game)
            self.keys_pressed |= KEY_START
            fb0 = np.zeros((16, 16, 3), dtype=np.uint8)
            self.dll.mario_render(self.game, fb0.ctypes.data_as(ctypes.c_char_p))
            self.current_hex = fb0.tobytes().hex()

    async def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        if self.game and self.dll:
            self.dll.mario_destroy(self.game)
            self.game = None
        # 恢复板端之前模式
        if self.controller and hasattr(self.controller, "set_mode"):
            try:
                revert_mode = self.prev_mode if self.prev_mode and self.prev_mode != 29 else 23
                await asyncio.to_thread(self.controller.set_mode, revert_mode)
            except Exception:
                pass

    async def _loop(self):
        fb = np.zeros((16, 16, 3), dtype=np.uint8)
        score = ctypes.c_uint16()
        lives = ctypes.c_uint8()
        coins = ctypes.c_uint8()
        state = ctypes.c_uint8()
        prog = ctypes.c_uint8()

        from wifi_gateway import get_wifi_gateway
        gw = get_wifi_gateway()

        tick_dt = 0.033  # 约 30 FPS
        while self.is_running and self.game:
            t0 = time.monotonic()
            down = self.keys_down
            pressed = self.keys_pressed
            self.keys_pressed = 0

            # 步进 C++ 引擎
            self.dll.mario_update(self.game, ctypes.c_float(tick_dt), ctypes.c_uint16(down), ctypes.c_uint16(pressed))
            self.dll.mario_render(self.game, fb.ctypes.data_as(ctypes.c_char_p))
            self.dll.mario_get_status(
                self.game,
                ctypes.byref(score),
                ctypes.byref(lives),
                ctypes.byref(coins),
                ctypes.byref(state),
                ctypes.byref(prog)
            )

            hex_str = fb.tobytes().hex()
            self.current_hex = hex_str
            self.status = {
                "score": score.value,
                "lives": lives.value,
                "coins": coins.value,
                "state": state.value,
                "progress": prog.value,
            }

            # 1. 向物理灯板直推帧 (纯视觉，完全静音)
            if gw and gw.sock and gw.is_online():
                cmd_data = json.dumps({"cmd": "canvas", "hex": hex_str}, separators=(',', ':')).encode('utf-8')
                for ip in gw.get_target_ips():
                    try:
                        gw.sock.sendto(cmd_data, (ip, gw.port))
                    except OSError:
                        pass

            # 2. 向 Web 客户端广播
            if self.broadcast_fn:
                try:
                    await self.broadcast_fn({
                        "type": "mario_frame",
                        "hex": hex_str,
                        "status": self.status
                    })
                except Exception:
                    pass

            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0.005, tick_dt - elapsed))


_global_mario_session = None

def get_mario_session(controller=None, broadcast_fn=None):
    global _global_mario_session
    if _global_mario_session is None:
        _global_mario_session = MarioSession(controller, broadcast_fn)
    elif controller and not _global_mario_session.controller:
        _global_mario_session.controller = controller
    elif broadcast_fn and not _global_mario_session.broadcast_fn:
        _global_mario_session.broadcast_fn = broadcast_fn
    return _global_mario_session

