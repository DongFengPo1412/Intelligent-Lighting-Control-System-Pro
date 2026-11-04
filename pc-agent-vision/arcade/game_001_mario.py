# -*- coding: utf-8 -*-
"""
game_001_mario.py —— 街机游戏 #001: 超级马里奥 (Super Mario Bros. 16)
力学动词: 横向平台跳跃与动力学冲刺
统一接入 BaseCartridge 抽象接口，依托 C++ 原生引擎 mario16.dll 提供 1:1 像素级物理模拟
"""

import ctypes
from pathlib import Path
from typing import Dict, Any
from arcade.arcade_result_screen import render_result_screen
from arcade.base_cartridge import (
    BaseCartridge,
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

DLL_PATH = Path(__file__).resolve().parent.parent / "mario16.dll"


class Game001Mario(BaseCartridge):
    """超级马里奥 16x16 标准卡带封装"""

    def __init__(self):
        self._dll = None
        self._game_handle = None
        self._buf = bytearray(16 * 16 * 3)
        self._status = {
            "score": 0,
            "lives": 3,
            "coins": 0,
            "state": STATE_TITLE,
            "progress": 0,
        }
        self._fallback_mode = False
        self._paused = False
        self._fallback_timer = 0.0
        self._high_score = 0
        self._anim_timer = 0.0
        self._init_engine()

    def _init_engine(self):
        if DLL_PATH.is_file():
            try:
                self._dll = ctypes.CDLL(str(DLL_PATH))
                self._dll.mario_create.restype = ctypes.c_void_p
                self._dll.mario_destroy.argtypes = [ctypes.c_void_p]
                self._dll.mario_reset.argtypes = [ctypes.c_void_p]
                self._dll.mario_update.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_float,
                    ctypes.c_uint16,
                    ctypes.c_uint16,
                ]
                self._dll.mario_render.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
                self._dll.mario_get_status.argtypes = [
                    ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_uint16),
                    ctypes.POINTER(ctypes.c_uint8),
                    ctypes.POINTER(ctypes.c_uint8),
                    ctypes.POINTER(ctypes.c_uint8),
                    ctypes.POINTER(ctypes.c_uint8),
                ]
                self._game_handle = self._dll.mario_create()
            except Exception:
                self._fallback_mode = True
        else:
            self._fallback_mode = True

    def __del__(self):
        if self._dll and self._game_handle:
            try:
                self._dll.mario_destroy(self._game_handle)
                self._game_handle = None
            except Exception:
                pass

    @property
    def game_id(self) -> int:
        return 1

    @property
    def name(self) -> str:
        return "超级马里奥"

    @property
    def english_name(self) -> str:
        return "Super Mario Bros."

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "横向平台跳跃与动力学冲刺"

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._paused = False
        if self._dll and self._game_handle:
            self._dll.mario_reset(self._game_handle)
            score = ctypes.c_uint16()
            lives = ctypes.c_uint8()
            coins = ctypes.c_uint8()
            state = ctypes.c_uint8()
            prog = ctypes.c_uint8()
            self._dll.mario_get_status(
                self._game_handle,
                ctypes.byref(score),
                ctypes.byref(lives),
                ctypes.byref(coins),
                ctypes.byref(state),
                ctypes.byref(prog),
            )
            raw_st = state.value
            if raw_st == 0:
                mapped_st = STATE_TITLE
            elif raw_st == 3:
                mapped_st = STATE_PAUSED
            elif raw_st in (4, 5):
                mapped_st = STATE_GAMEOVER
            elif raw_st == 6:
                mapped_st = STATE_VICTORY
            else:
                mapped_st = STATE_PLAYING

            self._status = {
                "score": score.value,
                "high_score": max(self._status.get("high_score", 0), score.value),
                "lives": lives.value,
                "coins": coins.value,
                "state": mapped_st,
                "progress": prog.value,
            }
        else:
            self._status = {
                "score": 0,
                "high_score": self._status.get("high_score", 0),
                "lives": 3,
                "coins": 0,
                "state": STATE_TITLE,
                "progress": 0,
            }
            self._fallback_timer = 0.0
        self._anim_timer = 0.0

    def start(self) -> None:
        """从待命或结算状态启动游戏 (幂等)"""
        st = self._status["state"]
        if st in (STATE_TITLE, STATE_GAMEOVER):
            if st == STATE_GAMEOVER:
                self.reset()
            self.update(0.02, KEY_A, KEY_A)
        elif st == STATE_PAUSED:
            self.resume()

    def pause(self) -> None:
        """安全暂停 (幂等)"""
        if self._status["state"] == STATE_PLAYING:
            self._paused = True
            self._status["state"] = STATE_PAUSED

    def resume(self) -> None:
        """从暂停恢复游玩 (幂等)"""
        if self._status["state"] == STATE_PAUSED:
            self._paused = False
            self._status["state"] = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if self._paused:
            return # Keep the actual native world frozen until explicit Resume.
        if self._dll and self._game_handle:
            self._dll.mario_update(
                self._game_handle,
                ctypes.c_float(dt),
                ctypes.c_uint16(keys_down),
                ctypes.c_uint16(keys_pressed),
            )
            score = ctypes.c_uint16()
            lives = ctypes.c_uint8()
            coins = ctypes.c_uint8()
            state = ctypes.c_uint8()
            prog = ctypes.c_uint8()
            self._dll.mario_get_status(
                self._game_handle,
                ctypes.byref(score),
                ctypes.byref(lives),
                ctypes.byref(coins),
                ctypes.byref(state),
                ctypes.byref(prog),
            )
            # Map native states (0:TITLE, 1:READY, 2:PLAY, 3:PAUSE, 4:DEAD, 5:GAMEOVER, 6:WIN)
            raw_st = state.value
            if raw_st == 0:
                mapped_st = STATE_TITLE
            elif raw_st == 3:
                mapped_st = STATE_PAUSED
            elif raw_st in (4, 5):
                mapped_st = STATE_GAMEOVER
            elif raw_st == 6:
                mapped_st = STATE_VICTORY
            else:
                mapped_st = STATE_PLAYING

            if score.value > self._high_score:
                self._high_score = score.value
            if mapped_st in (STATE_GAMEOVER, STATE_VICTORY):
                self._anim_timer += dt
            self._status = {
                "score": score.value,
                "high_score": self._high_score,
                "lives": lives.value,
                "coins": coins.value,
                "state": mapped_st,
                "progress": prog.value,
            }
        else:
            # Standalone fallback state machine
            self._fallback_timer += dt
            if self._status["state"] == STATE_TITLE:
                if keys_pressed & (KEY_A | KEY_START):
                    self._status["state"] = STATE_PLAYING
            elif self._status["state"] == STATE_PLAYING:
                if keys_pressed & KEY_START:
                    self._status["state"] = STATE_PAUSED
                if keys_down & KEY_RIGHT:
                    self._status["progress"] = min(100, self._status["progress"] + 1)
                    self._status["score"] += 10
            elif self._status["state"] == STATE_PAUSED:
                if keys_pressed & KEY_START:
                    self._status["state"] = STATE_PLAYING

    def render(self) -> bytearray:
        if self._dll and self._game_handle:
            raw_buf = ctypes.create_string_buffer(16 * 16 * 3)
            self._dll.mario_render(self._game_handle, raw_buf)
            return bytearray(raw_buf.raw)
        else:
            # Fallback frame rendering
            buf = bytearray(16 * 16 * 3)
            # Sky blue background
            for i in range(16 * 14):
                buf[i * 3 + 0] = 92
                buf[i * 3 + 1] = 148
                buf[i * 3 + 2] = 252
            # Brown ground bottom 2 rows
            for i in range(16 * 14, 16 * 16):
                buf[i * 3 + 0] = 200
                buf[i * 3 + 1] = 76
                buf[i * 3 + 2] = 12
            # Red Mario pixel at (3, 13)
            m_idx = (13 * 16 + 3) * 3
            buf[m_idx + 0] = 255
            buf[m_idx + 1] = 0
            buf[m_idx + 2] = 0
            return buf

    def get_status(self) -> Dict[str, Any]:
        st = dict(self._status)
        st["high_score"] = self._high_score
        return st
