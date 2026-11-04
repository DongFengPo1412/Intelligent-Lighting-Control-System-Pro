# -*- coding: utf-8 -*-
"""game_044_bejeweled.py —— 目标 #044 宝石迷阵 (Bejeweled)
6x6 宝石邻接交换 + 非三连自动回退 + 重力补位瀑布连锁与闪电计时
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


def _jewel_rgb(gem: int, spec: bool) -> Tuple[int, int, int]:
    if gem == 1:
        return (255, 145, 155) if spec else (235, 40, 60)
    if gem == 2:
        return (145, 255, 170) if spec else (35, 215, 85)
    if gem == 3:
        return (150, 210, 255) if spec else (45, 130, 250)
    if gem == 4:
        return (255, 245, 150) if spec else (245, 200, 25)
    if gem == 5:
        return (235, 160, 255) if spec else (185, 60, 240)
    return (20, 22, 34)


class Game044Bejeweled(BaseCartridge):
    SIZE = 6
    TARGET_SCORE = 500

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.board: List[List[int]] = [[1 for _ in range(self.SIZE)] for _ in range(self.SIZE)]
        self.cx = 2
        self.cy = 2
        self.sel_x = -1
        self.sel_y = -1
        self.last_chain = 0
        self._seed = 0x44200109
        self.time_left = 60.0
        self.invalid_flash = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 44

    @property
    def name(self) -> str:
        return "宝石迷阵"

    @property
    def english_name(self) -> str:
        return "Bejeweled"

    @property
    def release_year(self) -> int:
        return 2001

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "6x6 宝石邻接交换 + 无效交换自动回退 + 重力下落补位与瀑布连锁"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _random_gem(self) -> int:
        return 1 + (self._next_rand() % 5)

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def find_matches(self) -> List[List[bool]]:
        mark = [[False for _ in range(self.SIZE)] for _ in range(self.SIZE)]

        for r in range(self.SIZE):
            c = 0
            while c < self.SIZE:
                g = self.board[r][c]
                if g == 0:
                    c += 1
                    continue
                end = c + 1
                while end < self.SIZE and self.board[r][end] == g:
                    end += 1
                if end - c >= 3:
                    for k in range(c, end):
                        mark[r][k] = True
                c = end

        for c in range(self.SIZE):
            r = 0
            while r < self.SIZE:
                g = self.board[r][c]
                if g == 0:
                    r += 1
                    continue
                end = r + 1
                while end < self.SIZE and self.board[end][c] == g:
                    end += 1
                if end - r >= 3:
                    for k in range(r, end):
                        mark[k][c] = True
                r = end

        return mark

    def has_valid_move(self) -> bool:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if c + 1 < self.SIZE:
                    self.board[r][c], self.board[r][c + 1] = self.board[r][c + 1], self.board[r][c]
                    m = any(any(row) for row in self.find_matches())
                    self.board[r][c], self.board[r][c + 1] = self.board[r][c + 1], self.board[r][c]
                    if m:
                        return True
                if r + 1 < self.SIZE:
                    self.board[r][c], self.board[r + 1][c] = self.board[r + 1][c], self.board[r][c]
                    m = any(any(row) for row in self.find_matches())
                    self.board[r][c], self.board[r + 1][c] = self.board[r + 1][c], self.board[r][c]
                    if m:
                        return True
        return False

    def generate_playable_board(self) -> None:
        for _ in range(32):
            for r in range(self.SIZE):
                for c in range(self.SIZE):
                    g = self._random_gem()
                    guard = 0
                    while guard < 16 and (
                        (c >= 2 and self.board[r][c - 1] == g and self.board[r][c - 2] == g)
                        or (r >= 2 and self.board[r - 1][c] == g and self.board[r - 2][c] == g)
                    ):
                        g = (g % 5) + 1
                        guard += 1
                    self.board[r][c] = g
            if self.has_valid_move():
                return
        self.board[0][0] = 1
        self.board[0][1] = 1
        self.board[0][2] = 2
        self.board[1][2] = 1

    def apply_gravity_and_refill(self) -> None:
        for c in range(self.SIZE):
            write_r = self.SIZE - 1
            for r in range(self.SIZE - 1, -1, -1):
                if self.board[r][c] != 0:
                    self.board[write_r][c] = self.board[r][c]
                    if write_r != r:
                        self.board[r][c] = 0
                    write_r -= 1
            for r in range(write_r, -1, -1):
                self.board[r][c] = self._random_gem()

    def try_swap(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        if not (0 <= x1 < self.SIZE and 0 <= y1 < self.SIZE):
            return False
        if not (0 <= x2 < self.SIZE and 0 <= y2 < self.SIZE):
            return False
        if abs(x1 - x2) + abs(y1 - y2) != 1:
            return False

        self.board[y1][x1], self.board[y2][x2] = self.board[y2][x2], self.board[y1][x1]
        mark = self.find_matches()
        matched = sum(1 for r in range(self.SIZE) for c in range(self.SIZE) if mark[r][c])
        if matched == 0:
            self.board[y1][x1], self.board[y2][x2] = self.board[y2][x2], self.board[y1][x1]
            self.invalid_flash = 0.25
            return False

        chain = 0
        while matched > 0 and chain < 24:
            chain += 1
            for r in range(self.SIZE):
                for c in range(self.SIZE):
                    if mark[r][c]:
                        self.board[r][c] = 0
            self._add_score(matched * 10 * chain)
            self.time_left = min(60.0, self.time_left + 1.5)
            self.apply_gravity_and_refill()
            mark = self.find_matches()
            matched = sum(1 for r in range(self.SIZE) for c in range(self.SIZE) if mark[r][c])

        self.last_chain = chain

        if self._score >= self.TARGET_SCORE:
            self._state = STATE_VICTORY
            self.state_timer = 0.0
            return True

        if not self.has_valid_move():
            self.generate_playable_board()
        return True

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._seed = 0x44200109
        self._score = 0
        self.cx = 2
        self.cy = 2
        self.sel_x = -1
        self.sel_y = -1
        self.last_chain = 0
        self.time_left = 60.0
        self.invalid_flash = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.generate_playable_board()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.cx = 2
            self.cy = 2
            self.sel_x = -1
            self.sel_y = -1
            self.last_chain = 0
            self.time_left = 60.0
            self.invalid_flash = 0.0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.generate_playable_board()
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
        if self.invalid_flash > 0.0:
            self.invalid_flash = max(0.0, self.invalid_flash - dt)

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

            self.time_left -= dt
            if self.time_left <= 0.0:
                self.time_left = 0.0
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                if self._score > self._high_score:
                    self._high_score = self._score
                return

            if keys_pressed & KEY_B:
                self.sel_x = -1
                self.sel_y = -1

            dx, dy = 0, 0
            if keys_pressed & KEY_LEFT:
                dx = -1
            elif keys_pressed & KEY_RIGHT:
                dx = 1
            elif keys_pressed & KEY_UP:
                dy = -1
            elif keys_pressed & KEY_DOWN:
                dy = 1

            if dx != 0 or dy != 0:
                if self.sel_x >= 0 and self.sel_y >= 0:
                    nx, ny = self.sel_x + dx, self.sel_y + dy
                    if 0 <= nx < self.SIZE and 0 <= ny < self.SIZE:
                        sx, sy = self.sel_x, self.sel_y
                        self.cx, self.cy = nx, ny
                        self.sel_x, self.sel_y = -1, -1
                        self.try_swap(sx, sy, nx, ny)
                        return
                else:
                    nx, ny = self.cx + dx, self.cy + dy
                    if 0 <= nx < self.SIZE:
                        self.cx = nx
                    if 0 <= ny < self.SIZE:
                        self.cy = ny

            if keys_pressed & KEY_A:
                if self.sel_x < 0:
                    self.sel_x, self.sel_y = self.cx, self.cy
                elif abs(self.cx - self.sel_x) + abs(self.cy - self.sel_y) == 1:
                    sx, sy = self.sel_x, self.sel_y
                    self.sel_x, self.sel_y = -1, -1
                    self.try_swap(sx, sy, self.cx, self.cy)
                else:
                    self.sel_x, self.sel_y = -1, -1

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
                set_px(x, y, 12, 14, 24)

        t_px = max(0, min(14, int((self.time_left / 60.0) * 14.0 + 0.5)))
        for i in range(14):
            if i < t_px:
                if self.time_left > 20.0:
                    set_px(1 + i, 0, 45, 220, 110)
                else:
                    set_px(1 + i, 0, 245, 70, 55)
            else:
                set_px(1 + i, 0, 30, 32, 46)

        s_px = min(14, (self._score * 14) // self.TARGET_SCORE)
        for i in range(14):
            if i < s_px:
                set_px(1 + i, 1, 255, 210, 40)
            else:
                set_px(1 + i, 1, 24, 28, 42)

        for y in range(2, 16):
            set_px(1, y, 42, 48, 72)
            set_px(14, y, 42, 48, 72)
        for x in range(1, 15):
            set_px(x, 2, 42, 48, 72)
            set_px(x, 15, 42, 48, 72)

        for r in range(self.SIZE):
            py = 3 + r * 2
            for c in range(self.SIZE):
                px = 2 + c * 2
                gem = self.board[r][c]
                for dy in range(2):
                    for dx in range(2):
                        jr, jg, jb = _jewel_rgb(gem, dx == 0 and dy == 0)
                        set_px(px + dx, py + dy, jr, jg, jb)

        blink = (int(self.anim_timer * 8.0) % 2) == 0
        if self.sel_x >= 0 and self.sel_y >= 0:
            sx, sy = 2 + self.sel_x * 2, 3 + self.sel_y * 2
            br = 255 if blink else 200
            set_px(sx, sy, br, br, br)
            set_px(sx + 1, sy, br, br, br)
            set_px(sx, sy + 1, br, br, br)
            set_px(sx + 1, sy + 1, br, br, br)
        elif self._state == STATE_PLAYING:
            kx, ky = 2 + self.cx * 2, 3 + self.cy * 2
            if self.invalid_flash > 0.0:
                set_px(kx + 1, ky + 1, 255, 30, 30)
                set_px(kx, ky + 1, 255, 30, 30)
            elif blink:
                set_px(kx + 1, ky + 1, 255, 255, 255)

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
            "time_left": round(self.time_left, 2),
            "last_chain": self.last_chain,
            "progress": min(100, (self._score * 100) // self.TARGET_SCORE),
        }
