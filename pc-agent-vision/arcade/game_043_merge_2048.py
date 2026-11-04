# -*- coding: utf-8 -*-
"""game_043_merge_2048.py —— 目标 #043 2048滑块 (Neon 2048)
4x4 网格滑移对撞单次合并 + 霓虹色阶与点位编码 + 随机落子与死锁判定
"""

import math
from typing import Dict, Any, List, Tuple
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

TILE_BASE_RGB = {
    0: (22, 24, 34),
    1: (45, 140, 220),
    2: (26, 195, 165),
    3: (46, 215, 100),
    4: (245, 205, 25),
    5: (240, 130, 30),
    6: (235, 65, 55),
    7: (170, 80, 235),
    8: (255, 40, 150),
    9: (255, 215, 0),
    10: (90, 245, 235),
    11: (255, 255, 255),
}


class Game043Merge2048(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.board: List[List[int]] = [[0 for _ in range(4)] for _ in range(4)]
        self.max_tile = 1
        self._seed = 0x20482014
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 43

    @property
    def name(self) -> str:
        return "2048滑块"

    @property
    def english_name(self) -> str:
        return "Neon 2048"

    @property
    def release_year(self) -> int:
        return 2014

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "4x4 网格滑移对撞单次合并 + 霓虹色阶升维 + 随机落子与死锁判定"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _refresh_max_tile(self) -> None:
        self.max_tile = max(self.board[r][c] for r in range(4) for c in range(4))

    def spawn_random_tile(self) -> None:
        empties = [(r, c) for r in range(4) for c in range(4) if self.board[r][c] == 0]
        if not empties:
            return
        pick = self._next_rand() % len(empties)
        exp = 2 if (self._next_rand() % 10 == 0) else 1
        r, c = empties[pick]
        self.board[r][c] = exp
        self._refresh_max_tile()

    def can_move(self) -> bool:
        for r in range(4):
            for c in range(4):
                if self.board[r][c] == 0:
                    return True
                if c < 3 and self.board[r][c] == self.board[r][c + 1]:
                    return True
                if r < 3 and self.board[r][c] == self.board[r + 1][c]:
                    return True
        return False

    @staticmethod
    def _merge_line4(line: List[int]) -> Tuple[List[int], int, bool]:
        nz = [x for x in line if x != 0]
        res: List[int] = []
        gain = 0
        i = 0
        while i < len(nz):
            if i + 1 < len(nz) and nz[i] == nz[i + 1]:
                merged = nz[i] + 1
                res.append(merged)
                gain += 1 << merged
                i += 2
            else:
                res.append(nz[i])
                i += 1
        while len(res) < 4:
            res.append(0)
        return res, gain, (res != line)

    def slide(self, dx: int, dy: int) -> bool:
        moved = False
        gain = 0

        if dx != 0:
            for r in range(4):
                orig = list(self.board[r])
                line = orig if dx < 0 else list(reversed(orig))
                new_line, g, chg = self._merge_line4(line)
                if dx > 0:
                    new_line = list(reversed(new_line))
                if chg:
                    moved = True
                    self.board[r] = new_line
                    gain += g
        elif dy != 0:
            for c in range(4):
                orig = [self.board[r][c] for r in range(4)]
                line = orig if dy < 0 else list(reversed(orig))
                new_line, g, chg = self._merge_line4(line)
                if dy > 0:
                    new_line = list(reversed(new_line))
                if chg:
                    moved = True
                    for r in range(4):
                        self.board[r][c] = new_line[r]
                    gain += g

        if gain > 0:
            self._add_score(gain)

        if moved:
            self._refresh_max_tile()
            if self.max_tile >= 11:
                self._state = STATE_VICTORY
                self.state_timer = 0.0
                return True
            self.spawn_random_tile()
            if self.max_tile >= 11:
                self._state = STATE_VICTORY
                self.state_timer = 0.0
            elif not self.can_move():
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0

        return moved

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.board = [[0 for _ in range(4)] for _ in range(4)]
        self._seed = 0x20482014
        self._score = 0
        self.max_tile = 1
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.spawn_random_tile()
        self.spawn_random_tile()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self.board = [[0 for _ in range(4)] for _ in range(4)]
            self._score = 0
            self.max_tile = 1
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.spawn_random_tile()
            self.spawn_random_tile()
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
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

            if keys_pressed & KEY_LEFT:
                self.slide(-1, 0)
            elif keys_pressed & KEY_RIGHT:
                self.slide(1, 0)
            elif keys_pressed & KEY_UP:
                self.slide(0, -1)
            elif keys_pressed & KEY_DOWN:
                self.slide(0, 1)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)

        def set_px(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        for y in range(16):
            for x in range(16):
                set_px(x, y, 10, 12, 18)

        for r in range(4):
            y0 = r * 4
            for c in range(4):
                x0 = c * 4
                exp = self.board[r][c]
                br, bg, bb = TILE_BASE_RGB.get(exp, (255, 255, 255))
                for dy in range(3):
                    for dx in range(3):
                        set_px(x0 + dx, y0 + dy, br, bg, bb)

                if exp == 2:
                    set_px(x0 + 1, y0 + 1, 210, 255, 245)
                elif exp == 3:
                    set_px(x0 + 0, y0 + 0, 220, 255, 220)
                elif exp == 4:
                    set_px(x0 + 0, y0 + 0, 255, 255, 220)
                    set_px(x0 + 1, y0 + 1, 255, 255, 220)
                elif exp == 5:
                    set_px(x0 + 0, y0 + 0, 255, 240, 200)
                    set_px(x0 + 2, y0 + 2, 255, 240, 200)
                elif exp == 6:
                    set_px(x0 + 1, y0 + 1, 255, 255, 255)
                elif exp == 7:
                    for dx in range(3):
                        set_px(x0 + dx, y0 + 1, 245, 215, 255)
                elif exp == 8:
                    for dy in range(3):
                        set_px(x0 + 1, y0 + dy, 255, 225, 245)
                elif exp == 9:
                    set_px(x0 + 1, y0 + 0, 255, 255, 255)
                    set_px(x0 + 0, y0 + 1, 255, 255, 255)
                    set_px(x0 + 1, y0 + 1, 255, 255, 255)
                    set_px(x0 + 2, y0 + 1, 255, 255, 255)
                    set_px(x0 + 1, y0 + 2, 255, 255, 255)
                elif exp == 10:
                    set_px(x0 + 0, y0 + 0, 255, 255, 255)
                    set_px(x0 + 2, y0 + 0, 255, 255, 255)
                    set_px(x0 + 0, y0 + 2, 255, 255, 255)
                    set_px(x0 + 2, y0 + 2, 255, 255, 255)
                elif exp >= 11:
                    g = int(180 + 75.0 * (0.5 + 0.5 * math.sin(self.anim_timer * 8.0)))
                    set_px(x0 + 1, y0 + 1, 255, g, 20)

        if self._state == STATE_VICTORY:
            for x in range(16):
                set_px(x, 15, 46, 215, 100)
        elif self._state == STATE_GAMEOVER:
            for x in range(16):
                set_px(x, 15, 235, 50, 50)
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_px(6, y, 250, 250, 250)
                set_px(9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "max_tile": self.max_tile,
            "progress": min(100, (self.max_tile * 100) // 11),
        }
