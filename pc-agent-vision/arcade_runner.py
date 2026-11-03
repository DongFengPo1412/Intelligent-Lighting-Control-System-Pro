# -*- coding: utf-8 -*-
"""
arcade_runner.py —— 统一 16x16 街机卡带运行时中枢
负责在 Web 服务端承载卡带实例、驱动 30FPS 逻辑循环、向手机端广播实时渲染帧与 HUD 计分，
并在连接真实 ESP32-S3 时通过 Wi-Fi UDP 下发 arcade 协议指令与心跳保活。
"""

import asyncio
import time
from typing import Dict, Any, Optional
from arcade.base_cartridge import (
    BaseCartridge,
    CTRL_TAP_SINGLE,
    CTRL_TWO_BUTTON,
    CTRL_DPAD_4WAY,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    KEY_SELECT,
)
from arcade.game_001_mario import Game001Mario
from arcade.game_033_snake import Game033Snake
from arcade.game_041_tetris import Game041Tetris

KEY_MAP = {
    "left": KEY_LEFT,
    "right": KEY_RIGHT,
    "up": KEY_UP,
    "down": KEY_DOWN,
    "a": KEY_A,
    "b": KEY_B,
    "start": KEY_START,
    "select": KEY_SELECT,
}


class ArcadeSession:
    def __init__(self, controller=None, broadcast_fn=None):
        self.controller = controller
        self.broadcast_fn = broadcast_fn
        self.cartridges: Dict[int, BaseCartridge] = {
            1: Game001Mario(),
            33: Game033Snake(),
            41: Game041Tetris(),
        }
        self.current_cartridge: Optional[BaseCartridge] = None
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.keys_down = 0
        self.keys_pressed = 0
        self.current_hex = ""
        self.status = {
            "game_id": 0,
            "game_name": "None",
            "control_type": CTRL_ARCADE_AB,
            "score": 0,
            "high_score": 0,
            "lives": 1,
            "state": STATE_TITLE,
            "progress": 0,
        }
        self._last_heartbeat_time = 0.0

    def select_game(self, game_id: int) -> bool:
        if game_id not in self.cartridges:
            return False
        self.current_cartridge = self.cartridges[game_id]
        self.current_cartridge.reset()
        self.keys_down = 0
        self.keys_pressed = 0
        self._refresh_status()

        # 如果连接了硬件，下发选择卡带指令
        if self.controller and hasattr(self.controller, "send_command"):
            import json
            cmd = json.dumps({"cmd": "arcade", "action": "select", "game_id": game_id})
            try:
                self.controller.send_command(cmd)
            except Exception:
                pass
        return True

    def start(self) -> None:
        if self.current_cartridge:
            self.current_cartridge.start()
            self._refresh_status()
            if self.controller and hasattr(self.controller, "send_command"):
                import json
                self.controller.send_command(json.dumps({"cmd": "arcade", "action": "start"}))

    def pause(self) -> None:
        if self.current_cartridge:
            self.current_cartridge.pause()
            self._refresh_status()
            if self.controller and hasattr(self.controller, "send_command"):
                import json
                self.controller.send_command(json.dumps({"cmd": "arcade", "action": "pause"}))

    def resume(self) -> None:
        if self.current_cartridge:
            self.current_cartridge.resume()
            self._refresh_status()
            if self.controller and hasattr(self.controller, "send_command"):
                import json
                self.controller.send_command(json.dumps({"cmd": "arcade", "action": "resume"}))

    def reset(self) -> None:
        if self.current_cartridge:
            self.current_cartridge.reset()
            self.keys_down = 0
            self.keys_pressed = 0
            self._refresh_status()
            if self.controller and hasattr(self.controller, "send_command"):
                import json
                self.controller.send_command(json.dumps({"cmd": "arcade", "action": "reset"}))

    def stop(self) -> None:
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
        if self.current_cartridge:
            self.current_cartridge.pause()
        self.keys_down = 0
        self.keys_pressed = 0
        if self.controller and hasattr(self.controller, "send_command"):
            import json
            self.controller.send_command(json.dumps({"cmd": "arcade", "action": "exit"}))

    def key(self, key_name: str, is_down: bool) -> None:
        mask = KEY_MAP.get(key_name.lower(), 0)
        if not mask:
            return
        if is_down:
            if not (self.keys_down & mask):
                self.keys_pressed |= mask
            self.keys_down |= mask
        else:
            self.keys_down &= ~mask

        # 下发输入指令给硬件
        if self.controller and hasattr(self.controller, "send_command"):
            import json
            cmd = json.dumps({"cmd": "arcade", "action": "input", "down": self.keys_down, "pressed": self.keys_pressed})
            try:
                self.controller.send_command(cmd)
            except Exception:
                pass

    def _refresh_status(self) -> None:
        if not self.current_cartridge:
            self.status = {
                "game_id": 0,
                "game_name": "None",
                "control_type": CTRL_ARCADE_AB,
                "score": 0,
                "high_score": 0,
                "lives": 0,
                "state": STATE_TITLE,
                "progress": 0,
            }
            return

        c = self.current_cartridge
        st = c.get_status()
        self.status = {
            "game_id": c.game_id,
            "game_name": c.name,
            "english_name": c.english_name,
            "control_type": c.control_type,
            "score": st.get("score", 0),
            "high_score": st.get("high_score", 0),
            "lives": st.get("lives", 1),
            "state": st.get("state", STATE_TITLE),
            "progress": st.get("progress", 0),
        }

    async def run_loop(self) -> None:
        self.is_running = True
        dt = 0.033
        while self.is_running:
            t0 = time.monotonic()
            if self.current_cartridge:
                pressed = self.keys_pressed
                self.keys_pressed = 0

                self.current_cartridge.update(dt, self.keys_down, pressed)
                fb = self.current_cartridge.render()
                self.current_hex = fb.hex()
                self._refresh_status()

                # 广播至网页端手柄
                if self.broadcast_fn:
                    try:
                        await self.broadcast_fn({
                            "type": "arcade_frame",
                            "hex": self.current_hex,
                            "status": self.status,
                        })
                    except Exception:
                        pass

                # 周期性心跳下发 (每 300ms 一次)
                now = time.monotonic()
                if now - self._last_heartbeat_time > 0.3:
                    self._last_heartbeat_time = now
                    if self.controller and hasattr(self.controller, "send_command"):
                        import json
                        try:
                            self.controller.send_command(json.dumps({"cmd": "arcade", "action": "heartbeat"}))
                        except Exception:
                            pass

            elapsed = time.monotonic() - t0
            sleep_time = max(0.005, dt - elapsed)
            await asyncio.sleep(sleep_time)


_global_arcade_session: Optional[ArcadeSession] = None

def get_arcade_session(controller=None, broadcast_fn=None) -> ArcadeSession:
    global _global_arcade_session
    if _global_arcade_session is None:
        _global_arcade_session = ArcadeSession(controller, broadcast_fn)
    else:
        if controller:
            _global_arcade_session.controller = controller
        if broadcast_fn:
            _global_arcade_session.broadcast_fn = broadcast_fn
    return _global_arcade_session
