# -*- coding: utf-8 -*-
"""game_072_hex_board.py —— 目标 #072 Hex连通棋 (Hex Connection, 1985)
7x7 平行四边形错位六角格棋盘 + 严格 6 邻接连通判定 + 双桥最短路 AI
"""

import math
from typing import Dict, Any, Tuple
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

HEX_NEIGHBORS = (
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
)

HEX_BRIDGES = (
    (-1, 2, -1, 1, 0, 1),
    (1, -2, 0, -1, 1, -1),
    (-2, 1, -1, 0, -1, 1),
    (2, -1, 1, -1, 1, 0),
    (1, 1, 0, 1, 1, 0),
    (-1, -1, -1, 0, 0, -1),
)


class Game072HexBoard(BaseCartridge):
    BOARD_SIZE = 7

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.board = [[0] * 7 for _ in range(7)]
        self.cursor_r = 3
        self.cursor_c = 3
        self.turn_player = True
        self.ai_timer = 0.0
        self.moves_count = 0
        self.last_ai_r = -1
        self.last_ai_c = -1
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_state = 0x72721985
        self.reset()

    @property
    def game_id(self) -> int:
        return 72

    @property
    def name(self) -> str:
        return "Hex连通棋"

    @property
    def english_name(self) -> str:
        return "Hex Connection"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "7x7六角格对边连通博弈与双桥最短路AI"

    def _next_rand(self) -> int:
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._rng_state >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_game_data(self) -> None:
        self.board = [[0] * self.BOARD_SIZE for _ in range(self.BOARD_SIZE)]
        self.cursor_r = 3
        self.cursor_c = 3
        self.turn_player = True
        self.ai_timer = 0.0
        self.moves_count = 0
        self.last_ai_r = -1
        self.last_ai_c = -1
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_state = 0x72721985

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._init_game_data()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._init_game_data()
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def check_connectivity(self, who: int) -> bool:
        n = self.BOARD_SIZE
        visited = [[False] * n for _ in range(n)]
        queue = []

        if who == 1:
            for c in range(n):
                if self.board[0][c] == 1:
                    visited[0][c] = True
                    queue.append((0, c))
        else:
            for r in range(n):
                if self.board[r][0] == 2:
                    visited[r][0] = True
                    queue.append((r, 0))

        head = 0
        while head < len(queue):
            cr, cc = queue[head]
            head += 1
            if who == 1 and cr == n - 1:
                return True
            if who == 2 and cc == n - 1:
                return True

            for dr, dc in HEX_NEIGHBORS:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < n and 0 <= nc < n and not visited[nr][nc] and self.board[nr][nc] == who:
                    visited[nr][nc] = True
                    queue.append((nr, nc))
        return False

    def compute_shortest_cost(self, who: int) -> int:
        n = self.BOARD_SIZE
        inf = 999
        dist = [[inf] * n for _ in range(n)]

        if who == 1:
            for c in range(n):
                if self.board[0][c] == 1:
                    dist[0][c] = 0
                elif self.board[0][c] == 0:
                    dist[0][c] = 1
        else:
            for r in range(n):
                if self.board[r][0] == 2:
                    dist[r][0] = 0
                elif self.board[r][0] == 0:
                    dist[r][0] = 1

        for _ in range(14):
            changed = False
            for r in range(n):
                for c in range(n):
                    d_rc = dist[r][c]
                    if d_rc >= inf:
                        continue
                    for dr, dc in HEX_NEIGHBORS:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < n and 0 <= nc < n:
                            cell = self.board[nr][nc]
                            if cell != 0 and cell != who:
                                continue
                            step = 0 if cell == who else 1
                            if d_rc + step < dist[nr][nc]:
                                dist[nr][nc] = d_rc + step
                                changed = True
            if not changed:
                break

        if who == 1:
            return min(dist[n - 1][c] for c in range(n))
        return min(dist[r][n - 1] for r in range(n))

    def choose_ai_move(self) -> Tuple[int, int]:
        n = self.BOARD_SIZE
        # 1. Immediate AI win
        for r in range(n):
            for c in range(n):
                if self.board[r][c] == 0:
                    self.board[r][c] = 2
                    win = self.check_connectivity(2)
                    self.board[r][c] = 0
                    if win:
                        return r, c

        # 2. Immediate Player block
        for r in range(n):
            for c in range(n):
                if self.board[r][c] == 0:
                    self.board[r][c] = 1
                    pwin = self.check_connectivity(1)
                    self.board[r][c] = 0
                    if pwin:
                        return r, c

        base_ai = self.compute_shortest_cost(2)
        base_pl = self.compute_shortest_cost(1)

        best_score = -999999
        best_move = (-1, -1)

        for r in range(n):
            for c in range(n):
                if self.board[r][c] != 0:
                    continue
                self.board[r][c] = 2
                new_ai = self.compute_shortest_cost(2)
                new_pl = self.compute_shortest_cost(1)
                self.board[r][c] = 0

                val = (base_ai - new_ai) * 32 + (new_pl - base_pl) * 26

                for b_dr, b_dc, c1_dr, c1_dc, c2_dr, c2_dc in HEX_BRIDGES:
                    for r1 in range(n):
                        for c1 in range(n):
                            if self.board[r1][c1] != 2:
                                continue
                            r2, c2 = r1 + b_dr, c1 + b_dc
                            if not (0 <= r2 < n and 0 <= c2 < n) or self.board[r2][c2] != 2:
                                continue
                            m1r, m1c = r1 + c1_dr, c1 + c1_dc
                            m2r, m2c = r1 + c2_dr, c1 + c2_dc
                            if m1r == r and m1c == c and self.board[m2r][m2c] == 1:
                                val += 42
                            if m2r == r and m2c == c and self.board[m1r][m1c] == 1:
                                val += 42

                    br, bc = r + b_dr, c + b_dc
                    m1r, m1c = r + c1_dr, c + c1_dc
                    m2r, m2c = r + c2_dr, c + c2_dc
                    if 0 <= br < n and 0 <= bc < n:
                        if self.board[br][bc] == 2 and self.board[m1r][m1c] == 0 and self.board[m2r][m2c] == 0:
                            val += 10

                center_bias = 6 - abs(r - 3) - abs(c - 3)
                val += center_bias * 2 + (self._next_rand() % 4)
                if val > best_score:
                    best_score = val
                    best_move = (r, c)

        return best_move

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

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

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            if self.turn_player:
                if keys_pressed & KEY_LEFT and self.cursor_c > 0:
                    self.cursor_c -= 1
                if keys_pressed & KEY_RIGHT and self.cursor_c < self.BOARD_SIZE - 1:
                    self.cursor_c += 1
                if keys_pressed & KEY_UP and self.cursor_r > 0:
                    self.cursor_r -= 1
                if keys_pressed & KEY_DOWN and self.cursor_r < self.BOARD_SIZE - 1:
                    self.cursor_r += 1

                if (keys_pressed & KEY_A) and self.board[self.cursor_r][self.cursor_c] == 0:
                    self.board[self.cursor_r][self.cursor_c] = 1
                    self.moves_count += 1
                    self._add_score(15)

                    if self.check_connectivity(1):
                        self._add_score(400)
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
                        return

                    self.turn_player = False
                    self.ai_timer = 0.20
            else:
                self.ai_timer -= dt
                if self.ai_timer <= 0.0:
                    ar, ac = self.choose_ai_move()
                    if ar >= 0 and ac >= 0 and self.board[ar][ac] == 0:
                        self.board[ar][ac] = 2
                        self.last_ai_r = ar
                        self.last_ai_c = ac
                        self.moves_count += 1
                        if self.check_connectivity(2):
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                    self.turn_player = True

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

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                self._set_px(fb, x, y, 10, 12, 20)

        for c in range(self.BOARD_SIZE):
            self._set_px(fb, 1 + c, 3, 220, 55, 35)
            self._set_px(fb, 1 + c + 6, 11, 220, 55, 35)

        for r in range(self.BOARD_SIZE):
            self._set_px(fb, r, 4 + r, 35, 130, 235)
            self._set_px(fb, 8 + r, 4 + r, 35, 130, 235)

        for r in range(self.BOARD_SIZE):
            for c in range(self.BOARD_SIZE):
                px = 1 + c + r
                py = 4 + r
                cell = self.board[r][c]
                if cell == 0:
                    shade = 46 if ((r + c) % 2 == 0) else 36
                    self._set_px(fb, px, py, shade, shade + 6, shade + 18)
                elif cell == 1:
                    self._set_px(fb, px, py, 255, 120, 25)
                else:
                    if r == self.last_ai_r and c == self.last_ai_c:
                        self._set_px(fb, px, py, 110, 235, 255)
                    else:
                        self._set_px(fb, px, py, 30, 185, 250)

        if self._state == STATE_PLAYING and self.turn_player:
            if math.fmod(self.anim_timer, 0.4) < 0.24:
                cx = 1 + self.cursor_c + self.cursor_r
                cy = 4 + self.cursor_r
                if self.board[self.cursor_r][self.cursor_c] == 0:
                    self._set_px(fb, cx, cy, 255, 240, 120)
                else:
                    self._set_px(fb, cx, cy, 255, 255, 255)
        elif self._state == STATE_TITLE:
            self._set_px(fb, 1 + 3 + 2, 4 + 2, 255, 130, 30)
            self._set_px(fb, 1 + 3 + 4, 4 + 4, 255, 130, 30)
            self._set_px(fb, 1 + 2 + 3, 4 + 3, 40, 195, 255)
            self._set_px(fb, 1 + 4 + 3, 4 + 3, 40, 195, 255)

        if self.turn_player:
            self._set_px(fb, 1, 0, 255, 130, 30)
            self._set_px(fb, 2, 0, 255, 180, 40)
        else:
            self._set_px(fb, 13, 0, 40, 195, 255)
            self._set_px(fb, 14, 0, 40, 195, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        cost = self.compute_shortest_cost(1)
        prog = 0 if cost >= 7 else ((7 - cost) * 100) // 7
        if self._state == STATE_VICTORY:
            prog = 100
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": prog,
        }
