# -*- coding: utf-8 -*-
"""game_063_gomoku.py —— 目标 #063 五子棋 (Gomoku, 1985)
15x15 交叉点木纹棋盘 + 四轴五连珠判定 + 活四/冲四/活三攻防评估 AI
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

GRID_SIZE = 15
EMPTY = 0
PLAYER = 1
AI = 2

GOMOKU_AXES = ((1, 0), (0, 1), (1, 1), (1, -1))


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class Game063Gomoku(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.board: List[List[int]] = [[EMPTY] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.cursor_x = 7
        self.cursor_y = 7
        self.last_x = -1
        self.last_y = -1
        self.moves_count = 0
        self.player_turn = True
        self.ai_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 63

    @property
    def name(self) -> str:
        return "五子棋"

    @property
    def english_name(self) -> str:
        return "Gomoku"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "15x15交叉点五连珠攻防博弈"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_board(self) -> None:
        self.board = [[EMPTY] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.cursor_x = 7
        self.cursor_y = 7
        self.last_x = -1
        self.last_y = -1
        self.moves_count = 0
        self.player_turn = True
        self.ai_timer = 0.0

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

    def check_win_at(self, x: int, y: int, side: int) -> bool:
        if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
            return False
        if self.board[y][x] != side:
            return False
        for dx, dy in GOMOKU_AXES:
            cnt = 1
            cx, cy = x + dx, y + dy
            while 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and self.board[cy][cx] == side:
                cnt += 1
                cx += dx
                cy += dy
            cx, cy = x - dx, y - dy
            while 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and self.board[cy][cx] == side:
                cnt += 1
                cx -= dx
                cy -= dy
            if cnt >= 5:
                return True
        return False

    def evaluate_point_for_side(self, x: int, y: int, side: int) -> int:
        total = 0
        for dx, dy in GOMOKU_AXES:
            run = 1
            open_ends = 0
            cx, cy = x + dx, y + dy
            while 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and self.board[cy][cx] == side:
                run += 1
                cx += dx
                cy += dy
            if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and self.board[cy][cx] == EMPTY:
                open_ends += 1

            cx, cy = x - dx, y - dy
            while 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and self.board[cy][cx] == side:
                run += 1
                cx -= dx
                cy -= dy
            if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and self.board[cy][cx] == EMPTY:
                open_ends += 1

            if run >= 5:
                total += 100000
            elif run == 4:
                if open_ends == 2:
                    total += 15000
                elif open_ends == 1:
                    total += 3500
            elif run == 3:
                if open_ends == 2:
                    total += 2500
                elif open_ends == 1:
                    total += 300
            elif run == 2:
                if open_ends == 2:
                    total += 160
                elif open_ends == 1:
                    total += 25
        return total

    def _make_ai_move(self) -> None:
        best_score = -1
        best_x = -1
        best_y = -1
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.board[y][x] != EMPTY:
                    continue
                atk = self.evaluate_point_for_side(x, y, AI)
                dfn = self.evaluate_point_for_side(x, y, PLAYER)
                center_bonus = 14 - (abs(x - 7) + abs(y - 7))
                val = atk * 10 + dfn * 9 + center_bonus
                if val > best_score:
                    best_score = val
                    best_x = x
                    best_y = y

        if best_x >= 0 and best_y >= 0:
            self.board[best_y][best_x] = AI
            self.last_x = best_x
            self.last_y = best_y
            self.moves_count += 1
            if self.check_win_at(best_x, best_y, AI) or self.moves_count >= GRID_SIZE * GRID_SIZE:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                return
        self.player_turn = True

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
                    if self.cursor_x < GRID_SIZE - 1:
                        self.cursor_x += 1
                if keys_pressed & KEY_UP:
                    if self.cursor_y > 0:
                        self.cursor_y -= 1
                elif keys_pressed & KEY_DOWN:
                    if self.cursor_y < GRID_SIZE - 1:
                        self.cursor_y += 1

                if keys_pressed & KEY_A:
                    if self.board[self.cursor_y][self.cursor_x] == EMPTY:
                        self.board[self.cursor_y][self.cursor_x] = PLAYER
                        self.last_x = self.cursor_x
                        self.last_y = self.cursor_y
                        self.moves_count += 1
                        self._add_score(10)

                        if self.check_win_at(self.cursor_x, self.cursor_y, PLAYER):
                            self._add_score(500)
                            self._state = STATE_VICTORY
                            self.state_timer = 0.0
                            return
                        if self.moves_count >= GRID_SIZE * GRID_SIZE:
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        self.player_turn = False
                        self.ai_timer = 0.16
            else:
                self.ai_timer -= dt
                if self.ai_timer <= 0.0:
                    self._make_ai_move()

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                if x < GRID_SIZE and y < GRID_SIZE:
                    is_star = ((x in (3, 11)) and (y in (3, 11))) or (x == 7 and y == 7)
                    if is_star:
                        _set_px(fb, x, y, 78, 54, 24)
                    elif (x + y) % 2 == 0:
                        _set_px(fb, x, y, 52, 35, 16)
                    else:
                        _set_px(fb, x, y, 42, 28, 12)
                else:
                    _set_px(fb, x, y, 22, 14, 8)

        if self.player_turn:
            _set_px(fb, 15, 0, 0, 220, 255)
        else:
            _set_px(fb, 15, 0, 255, 70, 35)

        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                v = self.board[y][x]
                if v == PLAYER:
                    if x == self.last_x and y == self.last_y:
                        _set_px(fb, x, y, 255, 255, 255)
                    else:
                        _set_px(fb, x, y, 100, 240, 255)
                elif v == AI:
                    if x == self.last_x and y == self.last_y:
                        _set_px(fb, x, y, 255, 155, 45)
                    else:
                        _set_px(fb, x, y, 245, 55, 35)

        if self._state == STATE_PLAYING and self.player_turn:
            if (int(self.anim_timer * 6.0) % 2) == 0:
                _set_px(fb, self.cursor_x, self.cursor_y, 255, 235, 40)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (self.moves_count * 100) // 40),
        }
