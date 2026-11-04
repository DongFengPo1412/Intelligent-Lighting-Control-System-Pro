# -*- coding: utf-8 -*-
"""game_019_shell_game.py —— 目标 #019 猜球杯 (Shell Shuffle)
亮珠展示(REVEAL) -> 平滑高速交错洗杯(SHUFFLE) -> 游标选杯开奖(GUESS), 第4关升至4杯
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
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

SHELL_REVEAL = 0
SHELL_SHUFFLE = 1
SHELL_GUESS = 2

TOTAL_ROUNDS = 8
PI = 3.1415926


class Game019ShellGame(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.phase = SHELL_REVEAL
        self.round = 1
        self.num_cups = 3
        self.pearl_slot = 1
        self.cursor_slot = 1
        self.chosen_slot = -1
        self.lives = 3
        self.reveal_timer = 0.90
        self.swaps_total = 4
        self.swaps_done = 0
        self.swap_dur = 0.40
        self.swap_t = 0.0
        self.swap_a = 0
        self.swap_b = 1
        self._seed = 0x19198001
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 19

    @property
    def name(self) -> str:
        return "猜球杯"

    @property
    def english_name(self) -> str:
        return "Shell Shuffle"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "高速洗杯路径目视追踪与开杯猜珠"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _get_slot_x(self, slot: int) -> float:
        if self.num_cups == 4:
            slot4 = (1.0, 5.0, 9.0, 13.0)
            return slot4[max(0, min(3, slot))]
        slot3 = (1.0, 6.0, 11.0)
        return slot3[max(0, min(2, slot))]

    def _begin_next_swap(self) -> None:
        self.swap_a = self._next_rand() % self.num_cups
        self.swap_b = (self.swap_a + 1 + (self._next_rand() % (self.num_cups - 1))) % self.num_cups
        self.swap_t = 0.0

    def _setup_round(self) -> None:
        self.num_cups = 4 if self.round >= 4 else 3
        self.pearl_slot = self._next_rand() % self.num_cups
        self.cursor_slot = self.num_cups // 2
        self.chosen_slot = -1
        self.phase = SHELL_REVEAL
        self.reveal_timer = 0.90
        self.swaps_total = min(12, 4 + ((self.round - 1) * 8) // 7)
        self.swaps_done = 0
        self.swap_dur = max(0.16, 0.40 - float(self.round - 1) * 0.032)
        self.swap_t = 0.0
        self.swap_a = 0
        self.swap_b = 1

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.round = 1
        self.lives = 3
        self._score = 0
        self._seed = 0x19198001
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._setup_round()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.round = 1
            self.lives = 3
            self._score = 0
            self._seed = 0x19198001
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._setup_round()

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
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
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

            if self.phase == SHELL_REVEAL:
                self.reveal_timer -= dt
                if self.reveal_timer <= 0.0:
                    self.reveal_timer = 0.0
                    self.phase = SHELL_SHUFFLE
                    self.swaps_done = 0
                    self._begin_next_swap()
                return

            if self.phase == SHELL_SHUFFLE:
                self.swap_t += dt / self.swap_dur
                while self.swap_t >= 1.0 and self.phase == SHELL_SHUFFLE:
                    if self.pearl_slot == self.swap_a:
                        self.pearl_slot = self.swap_b
                    elif self.pearl_slot == self.swap_b:
                        self.pearl_slot = self.swap_a
                    self.swaps_done += 1
                    if self.swaps_done >= self.swaps_total:
                        self.phase = SHELL_GUESS
                        self.cursor_slot = self.num_cups // 2
                        self.swap_t = 0.0
                    else:
                        over = self.swap_t - 1.0
                        self._begin_next_swap()
                        self.swap_t = over
                return

            if self.phase == SHELL_GUESS:
                if keys_pressed & KEY_LEFT:
                    if self.cursor_slot > 0:
                        self.cursor_slot -= 1
                if keys_pressed & KEY_RIGHT:
                    if self.cursor_slot < self.num_cups - 1:
                        self.cursor_slot += 1
                if keys_pressed & (KEY_A | KEY_B):
                    self.chosen_slot = self.cursor_slot
                    if self.chosen_slot == self.pearl_slot:
                        self._add_score(100 * self.round)
                        if self.round >= TOTAL_ROUNDS:
                            self._state = STATE_VICTORY
                            self.state_timer = 0.0
                            return
                        self.round += 1
                        self._setup_round()
                    else:
                        if self.lives > 1:
                            self.lives -= 1
                            self._setup_round()
                        else:
                            self.lives = 0
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
        for y in range(16):
            for x in range(16):
                if y >= 11:
                    self._set_px(fb, x, y, 22, 62, 42)
                else:
                    self._set_px(fb, x, y, 12, 22, 32)

        cup_w = 2 if self.num_cups == 4 else 3

        show_pearl = (
            self._state == STATE_TITLE
            or (self._state == STATE_PLAYING and self.phase == SHELL_REVEAL)
            or self._state in (STATE_GAMEOVER, STATE_VICTORY)
        )
        if show_pearl:
            px = int(round(self._get_slot_x(self.pearl_slot))) + (cup_w // 2)
            self._set_px(fb, px, 10, 255, 225, 40)

        for s in range(self.num_cups):
            fx = self._get_slot_x(s)
            fy = 8.0

            if self._state == STATE_TITLE and s == self.pearl_slot:
                fy = 5.0 + math.sin(self.anim_timer * 4.0) * 1.0
            elif self._state == STATE_PLAYING and self.phase == SHELL_REVEAL and s == self.pearl_slot:
                fy = 5.0
            elif self._state == STATE_PLAYING and self.phase == SHELL_SHUFFLE:
                if s == self.swap_a:
                    xa = self._get_slot_x(self.swap_a)
                    xb = self._get_slot_x(self.swap_b)
                    fx = xa + (xb - xa) * self.swap_t
                    fy = 8.0 - math.sin(self.swap_t * PI) * 2.0
                elif s == self.swap_b:
                    xa = self._get_slot_x(self.swap_a)
                    xb = self._get_slot_x(self.swap_b)
                    fx = xb + (xa - xb) * self.swap_t
                    fy = 8.0 + math.sin(self.swap_t * PI) * 2.0
            elif self._state in (STATE_VICTORY, STATE_GAMEOVER) and s in (self.chosen_slot, self.pearl_slot):
                fy = 5.0

            ix = int(round(fx))
            iy = int(round(fy))
            for dy in range(3):
                for dx in range(cup_w):
                    cr, cg, cb = (245, 130, 45) if dy == 0 else (210, 65, 40)
                    self._set_px(fb, ix + dx, iy + dy, cr, cg, cb)

        if self._state == STATE_PLAYING and self.phase == SHELL_GUESS:
            cx = int(round(self._get_slot_x(self.cursor_slot))) + (cup_w // 2)
            self._set_px(fb, cx, 13, 0, 245, 255)
            self._set_px(fb, cx - 1, 14, 0, 200, 240)
            self._set_px(fb, cx, 14, 255, 255, 255)
            self._set_px(fb, cx + 1, 14, 0, 200, 240)

        for i in range(min(self.lives, 3)):
            self._set_px(fb, i * 2, 0, 235, 65, 55)
        for r in range(min(self.round, TOTAL_ROUNDS)):
            self._set_px(fb, 15 - r, 0, 255, 215, 35)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        cleared = TOTAL_ROUNDS if self._state == STATE_VICTORY else (self.round - 1)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (cleared * 100) // TOTAL_ROUNDS),
        }
