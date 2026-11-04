# -*- coding: utf-8 -*-
"""game_045_samegame.py —— 目标 #045 同色消块 (SameGame)
10x10 连通同色簇洪泛消除 + 二次方计分 + 列内重力与空列整体左移收拢
"""

from typing import Dict, Any, List, Tuple
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
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


def _block_rgb(col: int, hi: bool) -> Tuple[int, int, int]:
    if col == 1:
        return (255, 120, 120) if hi else (235, 55, 60)
    if col == 2:
        return (120, 255, 150) if hi else (45, 215, 95)
    if col == 3:
        return (130, 195, 255) if hi else (50, 140, 250)
    if col == 4:
        return (255, 235, 120) if hi else (245, 195, 30)
    return (16, 18, 28)


class Game045SameGame(BaseCartridge):
    SIZE = 10

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.grid: List[List[int]] = [[0 for _ in range(self.SIZE)] for _ in range(self.SIZE)]
        self.cx = 4
        self.cy = 5
        self._seed = 0x45198507
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 45

    @property
    def name(self) -> str:
        return "同色消块"

    @property
    def english_name(self) -> str:
        return "SameGame"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "10x10 同色连通簇洪泛消除 + 二次方计分 + 列内重力与空列整体左移"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def generate_board(self) -> None:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                self.grid[r][c] = 1 + (self._next_rand() % 4)
        if not self.has_removable_group():
            self.grid[self.SIZE - 1][0] = 1
            self.grid[self.SIZE - 1][1] = 1

    def flood_component(self, sx: int, sy: int) -> List[Tuple[int, int]]:
        if not (0 <= sx < self.SIZE and 0 <= sy < self.SIZE):
            return []
        target = self.grid[sy][sx]
        if target == 0:
            return []

        visited = [[False for _ in range(self.SIZE)] for _ in range(self.SIZE)]
        q = [(sx, sy)]
        visited[sy][sx] = True
        head = 0
        while head < len(q):
            x, y = q[head]
            head += 1
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.SIZE and 0 <= ny < self.SIZE:
                    if not visited[ny][nx] and self.grid[ny][nx] == target:
                        visited[ny][nx] = True
                        q.append((nx, ny))
        return q

    def apply_gravity_and_shift_left(self) -> None:
        for c in range(self.SIZE):
            write_r = self.SIZE - 1
            for r in range(self.SIZE - 1, -1, -1):
                if self.grid[r][c] != 0:
                    if write_r != r:
                        self.grid[write_r][c] = self.grid[r][c]
                        self.grid[r][c] = 0
                    write_r -= 1

        write_c = 0
        for c in range(self.SIZE):
            if self.grid[self.SIZE - 1][c] != 0:
                if write_c != c:
                    for r in range(self.SIZE):
                        self.grid[r][write_c] = self.grid[r][c]
                        self.grid[r][c] = 0
                write_c += 1

    def has_removable_group(self) -> bool:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                v = self.grid[r][c]
                if v == 0:
                    continue
                if c + 1 < self.SIZE and self.grid[r][c + 1] == v:
                    return True
                if r + 1 < self.SIZE and self.grid[r + 1][c] == v:
                    return True
        return False

    def count_remaining(self) -> int:
        return sum(1 for r in range(self.SIZE) for c in range(self.SIZE) if self.grid[r][c] != 0)

    def eliminate_at(self, cx: int, cy: int) -> int:
        comp = self.flood_component(cx, cy)
        n = len(comp)
        if n < 2:
            return 0

        for x, y in comp:
            self.grid[y][x] = 0

        self._add_score(n * (n - 1) * 5)
        self.apply_gravity_and_shift_left()

        if not self.has_removable_group():
            rem = self.count_remaining()
            if rem <= 3:
                clear_bonus = 500 if rem == 0 else (4 - rem) * 100
                self._add_score(clear_bonus)
                self._state = STATE_VICTORY
                self.state_timer = 0.0
            else:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                if self._score > self._high_score:
                    self._high_score = self._score
        return n

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._seed = 0x45198507
        self._score = 0
        self.cx = 4
        self.cy = 5
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.generate_board()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.cx = 4
            self.cy = 5
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.generate_board()
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
                if self.cx > 0:
                    self.cx -= 1
            elif keys_pressed & KEY_RIGHT:
                if self.cx < self.SIZE - 1:
                    self.cx += 1
            elif keys_pressed & KEY_UP:
                if self.cy > 0:
                    self.cy -= 1
            elif keys_pressed & KEY_DOWN:
                if self.cy < self.SIZE - 1:
                    self.cy += 1

            if keys_pressed & KEY_A:
                self.eliminate_at(self.cx, self.cy)

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
                set_px(x, y, 10, 12, 22)

        for y in range(2, 14):
            set_px(2, y, 50, 60, 95)
            set_px(13, y, 50, 60, 95)
        for x in range(2, 14):
            set_px(x, 2, 50, 60, 95)
            set_px(x, 13, 50, 60, 95)

        comp = self.flood_component(self.cx, self.cy)
        hover_set = set(comp) if (self._state == STATE_PLAYING and len(comp) >= 2) else set()

        for r in range(self.SIZE):
            for c in range(self.SIZE):
                v = self.grid[r][c]
                br, bg, bb = _block_rgb(v, (c, r) in hover_set)
                set_px(3 + c, 3 + r, br, bg, bb)

        cleared = 100 - self.count_remaining()
        bar = cleared // 10
        for i in range(10):
            if i < bar:
                set_px(3 + i, 0, 50, 230, 130)
            else:
                set_px(3 + i, 0, 28, 32, 46)

        if self._state == STATE_PLAYING and (int(self.anim_timer * 8.0) % 2 == 0):
            set_px(3 + self.cx, 3 + self.cy, 255, 255, 255)

        if self._state == STATE_PAUSED:
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
            "remaining": self.count_remaining(),
            "progress": 100 - self.count_remaining(),
        }
