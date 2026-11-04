# -*- coding: utf-8 -*-
"""game_016_whack_a_mole.py —— 目标 #016 打地鼠 (Whack-A-Mole)
3x3 地洞网格 + 方向键锤子准星移动 + A键挥锤敲击普通地鼠/避开红紫刺雷地鼠
"""

from typing import Dict, Any, List
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

WHACK_MOLE_NORMAL = 0
WHACK_MOLE_BOMB = 1

HOLE_X = (3, 8, 13)
HOLE_Y = (4, 9, 14)
TOTAL_HOLES = 9
TARGET_SCORE = 100
ROUND_DURATION = 45.0


class WhackHoleSlot:
    def __init__(self):
        self.popped = False
        self.whacked = False
        self.kind = WHACK_MOLE_NORMAL
        self.pop_timer = 0.0


class Game016WhackAMole(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.holes: List[WhackHoleSlot] = [WhackHoleSlot() for _ in range(TOTAL_HOLES)]
        self.cursor_row = 1
        self.cursor_col = 1
        self.hammer_timer = 0.0
        self.lives = 3
        self.time_remaining = ROUND_DURATION
        self.spawn_cooldown = 0.45
        self.spawn_count = 0
        self._seed = 0x16197601
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 16

    @property
    def name(self) -> str:
        return "打地鼠"

    @property
    def english_name(self) -> str:
        return "Whack-A-Mole"

    @property
    def release_year(self) -> int:
        return 1976

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "九宫格地洞快速反应准星锤击与炸弹甄别"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_holes(self) -> None:
        self.holes = [WhackHoleSlot() for _ in range(TOTAL_HOLES)]

    def _spawn_mole(self, force_normal: bool = False) -> None:
        pick = self._next_rand() % TOTAL_HOLES
        for t in range(TOTAL_HOLES):
            idx = (pick + t) % TOTAL_HOLES
            if not self.holes[idx].popped:
                self.holes[idx].popped = True
                self.holes[idx].whacked = False
                self.holes[idx].pop_timer = 1.15 + float(self._next_rand() % 5) * 0.10
                if force_normal or self.spawn_count == 0 or (self._next_rand() % 100) < 74:
                    self.holes[idx].kind = WHACK_MOLE_NORMAL
                else:
                    self.holes[idx].kind = WHACK_MOLE_BOMB
                self.spawn_count += 1
                break

    def _strike_hammer(self) -> None:
        self.hammer_timer = 0.16
        idx = self.cursor_row * 3 + self.cursor_col
        slot = self.holes[idx]
        if slot.popped and not slot.whacked:
            slot.whacked = True
            slot.pop_timer = 0.14
            if slot.kind == WHACK_MOLE_NORMAL:
                self._add_score(10)
            else:
                if self.lives > 1:
                    self.lives -= 1
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.cursor_row = 1
        self.cursor_col = 1
        self.hammer_timer = 0.0
        self.lives = 3
        self.time_remaining = ROUND_DURATION
        self.spawn_cooldown = 0.35
        self.spawn_count = 0
        self._score = 0
        self._seed = 0x16197601
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._init_holes()
        self._spawn_mole(True)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.cursor_row = 1
            self.cursor_col = 1
            self.hammer_timer = 0.0
            self.lives = 3
            self.time_remaining = ROUND_DURATION
            self.spawn_cooldown = 0.55
            self.spawn_count = 0
            self._score = 0
            self._seed = 0x16197601
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._init_holes()
            self._spawn_mole(True)

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
            if self.state_timer > 0.5 and (
                keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)
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

            if keys_pressed & KEY_UP:
                if self.cursor_row > 0:
                    self.cursor_row -= 1
            if keys_pressed & KEY_DOWN:
                if self.cursor_row < 2:
                    self.cursor_row += 1
            if keys_pressed & KEY_LEFT:
                if self.cursor_col > 0:
                    self.cursor_col -= 1
            if keys_pressed & KEY_RIGHT:
                if self.cursor_col < 2:
                    self.cursor_col += 1

            if self.hammer_timer > 0.0:
                self.hammer_timer = max(0.0, self.hammer_timer - dt)
            if keys_pressed & (KEY_A | KEY_B):
                self._strike_hammer()
                if self._state != STATE_PLAYING:
                    return

            for slot in self.holes:
                if not slot.popped:
                    continue
                slot.pop_timer -= dt
                if slot.pop_timer <= 0.0:
                    missed_normal = (not slot.whacked) and (slot.kind == WHACK_MOLE_NORMAL)
                    slot.popped = False
                    slot.whacked = False
                    if missed_normal:
                        self.time_remaining -= 2.5

            self.spawn_cooldown -= dt
            if self.spawn_cooldown <= 0.0:
                self.spawn_cooldown = 0.60 + float(self._next_rand() % 4) * 0.08
                self._spawn_mole(False)

            self.time_remaining -= dt
            if self.time_remaining <= 0.0:
                self.time_remaining = 0.0
                if self._score >= TARGET_SCORE:
                    self._state = STATE_VICTORY
                else:
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
                self._set_px(fb, x, y, 22, 56, 26)

        for r in range(3):
            for c in range(3):
                cx = HOLE_X[c]
                cy = HOLE_Y[r]
                slot = self.holes[r * 3 + c]

                for dy in (-1, 0):
                    for dx in (-1, 0):
                        self._set_px(fb, cx + dx, cy + dy, 40, 26, 16)

                if slot.popped:
                    if slot.whacked:
                        self._set_px(fb, cx - 1, cy - 1, 255, 255, 255)
                        self._set_px(fb, cx, cy - 1, 255, 240, 120)
                    elif slot.kind == WHACK_MOLE_NORMAL:
                        self._set_px(fb, cx - 1, cy - 1, 205, 115, 38)
                        self._set_px(fb, cx, cy - 1, 240, 165, 90)
                        self._set_px(fb, cx - 1, cy, 165, 85, 28)
                    else:
                        self._set_px(fb, cx - 1, cy - 1, 225, 35, 125)
                        self._set_px(fb, cx, cy - 1, 255, 90, 60)
                        self._set_px(fb, cx - 1, cy, 145, 25, 110)

        cur_cx = HOLE_X[self.cursor_col]
        cur_cy = HOLE_Y[self.cursor_row]
        swinging = self.hammer_timer > 0.0
        hr, hg, hb = (255, 255, 60) if swinging else (0, 255, 255)
        self._set_px(fb, cur_cx, cur_cy, hr, hg, hb)
        self._set_px(fb, cur_cx - 2, cur_cy - 1, hr, hg, hb)
        self._set_px(fb, cur_cx + 1, cur_cy - 1, hr, hg, hb)

        for i in range(min(self.lives, 3)):
            self._set_px(fb, i * 2, 0, 235, 65, 55)

        timer_px = int((self.time_remaining / ROUND_DURATION) * 9.0 + 0.5)
        for i in range(min(max(0, timer_px), 9)):
            self._set_px(fb, 15 - i, 0, 245, 200, 20)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (self._score * 100) // TARGET_SCORE),
        }
