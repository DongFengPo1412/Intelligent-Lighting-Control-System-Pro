# -*- coding: utf-8 -*-
"""game_015_simon_memory.py —— 目标 #015 闪灯记忆 (Simon Says)
四象限彩色序列记忆回放 + 玩家按四轨按键逐拍复现
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_MULTI_TRACK,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

SIMON_SHOW_ON = 0
SIMON_SHOW_GAP = 1
SIMON_INPUT = 2
SIMON_ROUND_PAUSE = 3
MAX_SEQUENCE = 15

PAD_KEYS = (KEY_LEFT, KEY_DOWN, KEY_UP, KEY_RIGHT)
TRACK_MASK = KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT

PAD_RECTS = (
    (1, 1, 6, 6),
    (1, 9, 6, 14),
    (9, 1, 14, 6),
    (9, 9, 14, 14),
)
DIM_COLORS = (
    (75, 16, 20),
    (14, 72, 28),
    (16, 38, 90),
    (85, 72, 12),
)
BRIGHT_COLORS = (
    (255, 55, 65),
    (45, 250, 95),
    (55, 155, 255),
    (255, 235, 45),
)


class Game015SimonMemory(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.phase = SIMON_SHOW_ON
        self.sequence: List[int] = [0] * MAX_SEQUENCE
        self.seq_len = 1
        self.show_idx = 0
        self.input_idx = 0
        self.lit_pad = -1
        self.phase_timer = 0.45
        self.input_flash_timer = 0.0
        self._seed = 0x15197801
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 15

    @property
    def name(self) -> str:
        return "闪灯记忆"

    @property
    def english_name(self) -> str:
        return "Simon Says"

    @property
    def release_year(self) -> int:
        return 1978

    @property
    def control_type(self) -> int:
        return CTRL_MULTI_TRACK

    @property
    def core_mechanic(self) -> str:
        return "四象限声光序列记忆与复现"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.phase = SIMON_SHOW_ON
        self.sequence = [0] * MAX_SEQUENCE
        self._seed = 0x15197801
        self.sequence[0] = self._next_rand() % 4
        self.seq_len = 1
        self.show_idx = 0
        self.input_idx = 0
        self.lit_pad = 0
        self.phase_timer = 0.45
        self.input_flash_timer = 0.0
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.phase = SIMON_SHOW_ON
            self.sequence = [0] * MAX_SEQUENCE
            self._seed = 0x15197801
            self.sequence[0] = self._next_rand() % 4
            self.seq_len = 1
            self.show_idx = 0
            self.input_idx = 0
            self.lit_pad = self.sequence[0]
            self.phase_timer = 0.45
            self.input_flash_timer = 0.0
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt < 0.0:
            dt = 0.0
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.lit_pad = int(self.anim_timer * 3.0) % 4
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (
                keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT)
            ):
                self.start()
            return

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            show_dur = max(0.20, 0.45 - float(self.seq_len - 1) * 0.015)

            if self.phase == SIMON_SHOW_ON:
                self.lit_pad = self.sequence[self.show_idx]
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    self.lit_pad = -1
                    self.phase = SIMON_SHOW_GAP
                    self.phase_timer = 0.14
                return

            if self.phase == SIMON_SHOW_GAP:
                self.lit_pad = -1
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    self.show_idx += 1
                    if self.show_idx < self.seq_len:
                        self.phase = SIMON_SHOW_ON
                        self.phase_timer = show_dur
                        self.lit_pad = self.sequence[self.show_idx]
                    else:
                        self.phase = SIMON_INPUT
                        self.input_idx = 0
                        self.lit_pad = -1
                        self.input_flash_timer = 0.0
                return

            if self.phase == SIMON_ROUND_PAUSE:
                if self.input_flash_timer > 0.0:
                    self.input_flash_timer -= dt
                    if self.input_flash_timer <= 0.0:
                        self.lit_pad = -1
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    self.show_idx = 0
                    self.phase = SIMON_SHOW_ON
                    self.phase_timer = show_dur
                    self.lit_pad = self.sequence[0]
                return

            if self.phase == SIMON_INPUT:
                if self.input_flash_timer > 0.0:
                    self.input_flash_timer -= dt
                    if self.input_flash_timer <= 0.0:
                        self.input_flash_timer = 0.0
                        self.lit_pad = -1

                pressed_tracks = keys_pressed & TRACK_MASK
                if pressed_tracks != 0:
                    expected = self.sequence[self.input_idx]
                    if pressed_tracks == PAD_KEYS[expected]:
                        self.lit_pad = expected
                        self.input_flash_timer = 0.18
                        self.input_idx += 1
                        if self.input_idx >= self.seq_len:
                            self._add_score(10 * self.seq_len)
                            if self.seq_len >= MAX_SEQUENCE:
                                self._state = STATE_VICTORY
                                self.state_timer = 0.0
                                return
                            self.sequence[self.seq_len] = self._next_rand() % 4
                            self.seq_len += 1
                            self.phase = SIMON_ROUND_PAUSE
                            self.phase_timer = 0.35
                    else:
                        self.lit_pad = -1
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

    @staticmethod
    def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < 16 and 0 <= y < 16:
            idx = (y * 16 + x) * 3
            fb[idx] = r
            fb[idx + 1] = g
            fb[idx + 2] = b

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)
        for p in range(4):
            is_lit = (self.lit_pad == p) and (self._state != STATE_GAMEOVER)
            cr, cg, cb = BRIGHT_COLORS[p] if is_lit else DIM_COLORS[p]
            if self._state == STATE_GAMEOVER:
                cr, cg, cb = 180, 20, 20

            x1, y1, x2, y2 = PAD_RECTS[p]
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    self._set_px(fb, x, y, cr, cg, cb)
            if is_lit:
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                self._set_px(fb, cx, cy, 255, 255, 255)
                self._set_px(fb, cx + 1, cy, 255, 255, 255)
                self._set_px(fb, cx, cy + 1, 255, 255, 255)
                self._set_px(fb, cx + 1, cy + 1, 255, 255, 255)

        hr, hg, hb = 120, 120, 140
        if self._state == STATE_PLAYING:
            if self.phase == SIMON_INPUT:
                hr, hg, hb = 40, 230, 120
            else:
                hr, hg, hb = 0, 200, 255
        elif self._state == STATE_GAMEOVER:
            hr, hg, hb = 255, 30, 30
        self._set_px(fb, 7, 7, hr, hg, hb)
        self._set_px(fb, 8, 7, hr, hg, hb)
        self._set_px(fb, 7, 8, hr, hg, hb)
        self._set_px(fb, 8, 8, hr, hg, hb)

        for i in range(min(self.seq_len, 15)):
            self._set_px(fb, i, 0, 220, 190, 40)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        completed = MAX_SEQUENCE if self._state == STATE_VICTORY else (self.seq_len - 1)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (completed * 100) // MAX_SEQUENCE),
        }
