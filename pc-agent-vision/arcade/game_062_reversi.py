# -*- coding: utf-8 -*-
"""game_062_reversi.py —— 目标 #062 黑白棋 (Reversi, 1980)
8x8 八向夹吃翻转棋盘 + 合法落点微光提示 + 无子自动让手 + 角位权重启发式 AI
"""

from typing import Dict, Any, List
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

BOARD_SIZE = 8
EMPTY = 0
PLAYER = 1
AI = 2

REV_DIRS = (
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
)

POS_WEIGHTS = (
    (100, -30,  20,   6,   6,  20, -30, 100),
    (-30, -50,  -6,  -4,  -4,  -6, -50, -30),
    ( 20,  -6,  15,   4,   4,  15,  -6,  20),
    (  6,  -4,   4,   2,   2,   4,  -4,   6),
    (  6,  -4,   4,   2,   2,   4,  -4,   6),
    ( 20,  -6,  15,   4,   4,  15,  -6,  20),
    (-30, -50,  -6,  -4,  -4,  -6, -50, -30),
    (100, -30,  20,   6,   6,  20, -30, 100),
)


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class Game062Reversi(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.board: List[List[int]] = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.cursor_x = 2
        self.cursor_y = 3
        self.player_turn = True
        self.ai_timer = 0.0
        self.player_count = 2
        self.ai_count = 2
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 62

    @property
    def name(self) -> str:
        return "黑白棋"

    @property
    def english_name(self) -> str:
        return "Reversi"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "八向夹吃翻转连锁与角位启发式博弈"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _update_disc_counts(self) -> None:
        p = 0
        a = 0
        for row in self.board:
            for cell in row:
                if cell == PLAYER:
                    p += 1
                elif cell == AI:
                    a += 1
        self.player_count = p
        self.ai_count = a

    def _init_board(self) -> None:
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.board[3][3] = AI
        self.board[3][4] = PLAYER
        self.board[4][3] = PLAYER
        self.board[4][4] = AI
        self.cursor_x = 2
        self.cursor_y = 3
        self.player_turn = True
        self.ai_timer = 0.0
        self._update_disc_counts()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._init_board()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._init_board()

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def count_flips_dir(self, x: int, y: int, side: int, dx: int, dy: int) -> int:
        opp = AI if side == PLAYER else PLAYER
        cx = x + dx
        cy = y + dy
        count = 0
        while 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and self.board[cy][cx] == opp:
            count += 1
            cx += dx
            cy += dy
        if count > 0 and 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and self.board[cy][cx] == side:
            return count
        return 0

    def total_flips(self, x: int, y: int, side: int) -> int:
        if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
            return 0
        if self.board[y][x] != EMPTY:
            return 0
        return sum(self.count_flips_dir(x, y, side, dx, dy) for dx, dy in REV_DIRS)

    def is_valid_move(self, x: int, y: int, side: int) -> bool:
        return self.total_flips(x, y, side) > 0

    def has_valid_move(self, side: int) -> bool:
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if self.is_valid_move(x, y, side):
                    return True
        return False

    def place_disc(self, x: int, y: int, side: int) -> int:
        total = self.total_flips(x, y, side)
        if total <= 0:
            return 0
        opp = AI if side == PLAYER else PLAYER
        self.board[y][x] = side
        for dx, dy in REV_DIRS:
            if self.count_flips_dir(x, y, side, dx, dy) > 0:
                cx = x + dx
                cy = y + dy
                while 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and self.board[cy][cx] == opp:
                    self.board[cy][cx] = side
                    cx += dx
                    cy += dy
        self._update_disc_counts()
        return total

    def _finish_game(self) -> None:
        self._update_disc_counts()
        if self.player_count > self.ai_count:
            self._add_score(200 + (self.player_count - self.ai_count) * 10)
            self._state = STATE_VICTORY
        else:
            self._state = STATE_GAMEOVER
        self.state_timer = 0.0

    def _resolve_next_turn(self, preferred_next: int) -> None:
        other = AI if preferred_next == PLAYER else PLAYER
        if self.has_valid_move(preferred_next):
            self.player_turn = (preferred_next == PLAYER)
            if not self.player_turn:
                self.ai_timer = 0.22
        elif self.has_valid_move(other):
            self.player_turn = (other == PLAYER)
            if not self.player_turn:
                self.ai_timer = 0.22
        else:
            self._finish_game()

    def _make_ai_move(self) -> None:
        best_eval = -999999
        best_x = -1
        best_y = -1
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                flips = self.total_flips(x, y, AI)
                if flips > 0:
                    ev = POS_WEIGHTS[y][x] + flips * 3
                    if ev > best_eval:
                        best_eval = ev
                        best_x = x
                        best_y = y
        if best_x >= 0 and best_y >= 0:
            self.place_disc(best_x, best_y, AI)

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

            if self.player_turn:
                if keys_pressed & KEY_LEFT:
                    if self.cursor_x > 0:
                        self.cursor_x -= 1
                elif keys_pressed & KEY_RIGHT:
                    if self.cursor_x < BOARD_SIZE - 1:
                        self.cursor_x += 1
                if keys_pressed & KEY_UP:
                    if self.cursor_y > 0:
                        self.cursor_y -= 1
                elif keys_pressed & KEY_DOWN:
                    if self.cursor_y < BOARD_SIZE - 1:
                        self.cursor_y += 1

                if keys_pressed & KEY_A:
                    flipped = self.place_disc(self.cursor_x, self.cursor_y, PLAYER)
                    if flipped > 0:
                        self._add_score(flipped * 10)
                        self._resolve_next_turn(AI)
            else:
                self.ai_timer -= dt
                if self.ai_timer <= 0.0:
                    self._make_ai_move()
                    self._resolve_next_turn(PLAYER)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for cy in range(BOARD_SIZE):
            for cx in range(BOARD_SIZE):
                px = cx * 2
                py = cy * 2
                even = ((cx + cy) % 2 == 0)
                br = 14 if even else 20
                bg = 58 if even else 74
                bb = 28 if even else 36

                p = self.board[cy][cx]
                if p == PLAYER:
                    _set_px(fb, px, py, 110, 250, 255)
                    _set_px(fb, px + 1, py, 0, 210, 245)
                    _set_px(fb, px, py + 1, 0, 210, 245)
                    _set_px(fb, px + 1, py + 1, 0, 165, 210)
                elif p == AI:
                    _set_px(fb, px, py, 255, 215, 80)
                    _set_px(fb, px + 1, py, 255, 150, 20)
                    _set_px(fb, px, py + 1, 255, 150, 20)
                    _set_px(fb, px + 1, py + 1, 210, 100, 10)
                else:
                    _set_px(fb, px, py, br, bg, bb)
                    _set_px(fb, px + 1, py, br, bg, bb)
                    _set_px(fb, px, py + 1, br, bg, bb)
                    _set_px(fb, px + 1, py + 1, br, bg, bb)
                    if self._state == STATE_PLAYING and self.player_turn and self.is_valid_move(cx, cy, PLAYER):
                        _set_px(fb, px, py, 55, 165, 110)

        if self._state == STATE_PLAYING and self.player_turn:
            if (int(self.anim_timer * 6.0) % 2) == 0:
                px = self.cursor_x * 2
                py = self.cursor_y * 2
                _set_px(fb, px, py, 255, 240, 60)
                _set_px(fb, px + 1, py + 1, 255, 240, 60)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        total = self.player_count + self.ai_count
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": (total * 100) // 64,
        }
