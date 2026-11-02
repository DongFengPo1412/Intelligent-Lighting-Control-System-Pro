"""
Game #035: 极简黑白棋 (Othello / Reversi 1980 / Namco / Nintendo)
Classic 8-Direction Sandwich Reversi with Positional Heuristic AI, Corner Control & Disc Flipping.
"""

from typing import List, Dict, Any, Tuple
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)

STATE_PLAYER_TURN = 0
STATE_AI_TURN = 1
STATE_GAMEOVER = 2

BOARD_SIZE = 8

PIECE_EMPTY = 0
PIECE_BLACK = 1
PIECE_WHITE = 2

DIRS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]

POS_WEIGHTS = [
    [ 100, -30,  20,   5,   5,  20, -30, 100 ],
    [ -30, -50,  -5,  -5,  -5,  -5, -50, -30 ],
    [  20,  -5,  15,   3,   3,  15,  -5,  20 ],
    [   5,  -5,   3,   3,   3,   3,  -5,   5 ],
    [   5,  -5,   3,   3,   3,   3,  -5,   5 ],
    [  20,  -5,  15,   3,   3,  15,  -5,  20 ],
    [ -30, -50,  -5,  -5,  -5,  -5, -50, -30 ],
    [ 100, -30,  20,   5,   5,  20, -30, 100 ],
]


class Game035Othello(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYER_TURN
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.cursor_x = 2
        self.cursor_y = 3
        self.black_count = 2
        self.white_count = 2
        self.ai_think_timer = 0.0

        self.board: List[List[int]] = [[PIECE_EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 35

    @property
    def name(self) -> str:
        return "极简黑白棋"

    @property
    def english_name(self) -> str:
        return "Othello 1980"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "八向夹吃翻转连锁 + 角位边缘死活棋拓扑 + 权值启发式棋力博弈"

    def init(self) -> None:
        self.reset()

    def init_board(self):
        self.board = [[PIECE_EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.board[3][3] = PIECE_WHITE
        self.board[3][4] = PIECE_BLACK
        self.board[4][3] = PIECE_BLACK
        self.board[4][4] = PIECE_WHITE
        self.update_counts()

    def reset(self):
        self.state = STATE_PLAYER_TURN
        self.state_timer = 0.0
        self.score = 0
        self.cursor_x = 2
        self.cursor_y = 3
        self.ai_think_timer = 0.0
        self.init_board()

    def update_counts(self):
        self.black_count = sum(row.count(PIECE_BLACK) for row in self.board)
        self.white_count = sum(row.count(PIECE_WHITE) for row in self.board)
        self.score = self.black_count * 50
        if self.score > self.high_score:
            self.high_score = self.score

    def count_flips(self, x: int, y: int, color: int, dx: int, dy: int) -> int:
        opp = PIECE_WHITE if color == PIECE_BLACK else PIECE_BLACK
        cx = x + dx
        cy = y + dy
        count = 0

        while 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and self.board[cy][cx] == opp:
            count += 1
            cx += dx
            cy += dy

        if count > 0 and 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and self.board[cy][cx] == color:
            return count
        return 0

    def is_valid_move(self, x: int, y: int, color: int) -> bool:
        if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
            return False
        if self.board[y][x] != PIECE_EMPTY:
            return False

        for dx, dy in DIRS:
            if self.count_flips(x, y, color, dx, dy) > 0:
                return True
        return False

    def has_any_valid_move(self, color: int) -> bool:
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if self.is_valid_move(x, y, color):
                    return True
        return False

    def flip_direction(self, x: int, y: int, color: int, dx: int, dy: int):
        opp = PIECE_WHITE if color == PIECE_BLACK else PIECE_BLACK
        cx = x + dx
        cy = y + dy

        while 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and self.board[cy][cx] == opp:
            self.board[cy][cx] = color
            cx += dx
            cy += dy

    def place_move(self, x: int, y: int, color: int) -> bool:
        if not self.is_valid_move(x, y, color):
            return False

        self.board[y][x] = color

        for dx, dy in DIRS:
            if self.count_flips(x, y, color, dx, dy) > 0:
                self.flip_direction(x, y, color, dx, dy)

        self.update_counts()
        return True

    def make_ai_move(self):
        best_score = -999999
        best_x = -1
        best_y = -1

        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if self.is_valid_move(x, y, PIECE_WHITE):
                    total_flips = sum(self.count_flips(x, y, PIECE_WHITE, dx, dy) for dx, dy in DIRS)
                    eval_score = POS_WEIGHTS[y][x] + total_flips * 3
                    if eval_score > best_score:
                        best_score = eval_score
                        best_x = x
                        best_y = y

        if best_x != -1 and best_y != -1:
            self.place_move(best_x, best_y, PIECE_WHITE)

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_GAMEOVER:
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PLAYER_TURN:
            if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
                self.cursor_x = max(0, self.cursor_x - 1)
            elif (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
                self.cursor_x = min(BOARD_SIZE - 1, self.cursor_x + 1)
            elif (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
                self.cursor_y = max(0, self.cursor_y - 1)
            elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
                self.cursor_y = min(BOARD_SIZE - 1, self.cursor_y + 1)

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                if self.place_move(self.cursor_x, self.cursor_y, PIECE_BLACK):
                    if self.has_any_valid_move(PIECE_WHITE):
                        self.state = STATE_AI_TURN
                        self.ai_think_timer = 0.5
                    elif not self.has_any_valid_move(PIECE_BLACK):
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        if self.black_count > self.white_count:
                            self.score += 1000 + (self.black_count - self.white_count) * 50
                            if self.score > self.high_score:
                                self.high_score = self.score

        elif self.state == STATE_AI_TURN:
            self.ai_think_timer -= dt
            if self.ai_think_timer <= 0.0:
                self.make_ai_move()

                if self.has_any_valid_move(PIECE_BLACK):
                    self.state = STATE_PLAYER_TURN
                elif not self.has_any_valid_move(PIECE_WHITE):
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    if self.black_count > self.white_count:
                        self.score += 1000 + (self.black_count - self.white_count) * 50
                        if self.score > self.high_score:
                            self.high_score = self.score
                else:
                    self.ai_think_timer = 0.5

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for cy in range(BOARD_SIZE):
            for cx in range(BOARD_SIZE):
                px0 = cx * 2
                py0 = cy * 2

                p = self.board[cy][cx]
                r, g, b = 27, 94, 32

                if p == PIECE_BLACK:
                    r, g, b = 20, 25, 30
                elif p == PIECE_WHITE:
                    r, g, b = 245, 245, 245

                for dy in range(2):
                    for dx in range(2):
                        idx = ((py0 + dy) * 16 + (px0 + dx)) * 3
                        fb[idx:idx + 3] = bytes([r, g, b])

                if self.state == STATE_PLAYER_TURN and p == PIECE_EMPTY and self.is_valid_move(cx, cy, PIECE_BLACK):
                    hint_idx = (py0 * 16 + px0) * 3
                    fb[hint_idx:hint_idx + 3] = bytes([50, 160, 60])

        if self.state == STATE_PLAYER_TURN and (int(self.state_timer * 6.0) % 2 == 0):
            cur_px = self.cursor_x * 2
            cur_py = self.cursor_y * 2
            for dy in range(2):
                for dx in range(2):
                    idx = ((cur_py + dy) * 16 + (cur_px + dx)) * 3
                    fb[idx:idx + 3] = bytes([241, 196, 15])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "black_count": self.black_count,
            "white_count": self.white_count,
            "cursor": (self.cursor_x, self.cursor_y),
            "player_turn": (self.state == STATE_PLAYER_TURN),
        }
