# -*- coding: utf-8 -*-
"""game_064_checkers.py —— 目标 #064 西洋跳棋 (Checkers, 1980)
8x8 棋盘斜向行棋 + 隔子连跳吃子 + 底线升王四向机动 + 战术启发式 AI
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
P_MAN = 1
P_KING = 2
AI_MAN = 3
AI_KING = 4


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class Game064Checkers(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.board: List[List[int]] = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.cursor_x = 1
        self.cursor_y = 5
        self.selected_x = -1
        self.selected_y = -1
        self.in_chain_jump = False
        self.player_turn = True
        self.ai_timer = 0.0
        self.quiet_turns = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 64

    @property
    def name(self) -> str:
        return "西洋跳棋"

    @property
    def english_name(self) -> str:
        return "Checkers"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "斜向隔子连跳吃子与底线升王机动"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_board(self) -> None:
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if (x + y) % 2 == 1:
                    if y <= 2:
                        self.board[y][x] = AI_MAN
                    elif y >= 5:
                        self.board[y][x] = P_MAN
        self.cursor_x = 1
        self.cursor_y = 5
        self.selected_x = -1
        self.selected_y = -1
        self.in_chain_jump = False
        self.player_turn = True
        self.ai_timer = 0.0
        self.quiet_turns = 0

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

    @staticmethod
    def is_player_piece(p: int) -> bool:
        return p in (P_MAN, P_KING)

    @staticmethod
    def is_ai_piece(p: int) -> bool:
        return p in (AI_MAN, AI_KING)

    @staticmethod
    def _can_dir_y(p: int, dy: int) -> bool:
        if p == P_MAN:
            return dy == -1
        if p == AI_MAN:
            return dy == 1
        if p in (P_KING, AI_KING):
            return dy in (-1, 1)
        return False

    def is_valid_move(self, sx: int, sy: int, tx: int, ty: int, jump_only: bool = False) -> bool:
        if not (0 <= sx < BOARD_SIZE and 0 <= sy < BOARD_SIZE):
            return False
        if not (0 <= tx < BOARD_SIZE and 0 <= ty < BOARD_SIZE):
            return False
        if self.board[ty][tx] != EMPTY:
            return False

        p = self.board[sy][sx]
        if p == EMPTY:
            return False
        p_side = self.is_player_piece(p)
        dx = tx - sx
        dy = ty - sy

        if not jump_only and abs(dx) == 1 and abs(dy) == 1:
            return self._can_dir_y(p, dy)

        if abs(dx) == 2 and abs(dy) == 2:
            step_y = dy // 2
            if not self._can_dir_y(p, step_y):
                return False
            mx = (sx + tx) // 2
            my = (sy + ty) // 2
            mid = self.board[my][mx]
            if p_side and self.is_ai_piece(mid):
                return True
            if (not p_side) and self.is_player_piece(mid):
                return True
        return False

    def has_move_from(self, sx: int, sy: int, jump_only: bool = False) -> bool:
        for dy in (-2, -1, 1, 2):
            for dx in (-2, -1, 1, 2):
                if abs(dx) != abs(dy):
                    continue
                if self.is_valid_move(sx, sy, sx + dx, sy + dy, jump_only):
                    return True
        return False

    def side_has_any_move(self, for_player: bool) -> bool:
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                p = self.board[y][x]
                if (for_player and self.is_player_piece(p)) or ((not for_player) and self.is_ai_piece(p)):
                    if self.has_move_from(x, y, False):
                        return True
        return False

    def count_pieces(self, for_player: bool) -> int:
        cnt = 0
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                p = self.board[y][x]
                if (for_player and self.is_player_piece(p)) or ((not for_player) and self.is_ai_piece(p)):
                    cnt += 1
        return cnt

    def _would_be_capturable_at(self, tx: int, ty: int, from_x: int, from_y: int) -> bool:
        for dy in (-1, 1):
            for dx in (-1, 1):
                ax, ay = tx + dx, ty + dy
                lx, ly = tx - dx, ty - dy
                if not (0 <= ax < BOARD_SIZE and 0 <= ay < BOARD_SIZE):
                    continue
                if not (0 <= lx < BOARD_SIZE and 0 <= ly < BOARD_SIZE):
                    continue
                landing_empty = (self.board[ly][lx] == EMPTY) or (lx == from_x and ly == from_y)
                if not landing_empty:
                    continue
                opp = self.board[ay][ax]
                if self.is_player_piece(opp) and self._can_dir_y(opp, ly - ty):
                    return True
        return False

    def _end_player_turn(self) -> None:
        self.selected_x = -1
        self.selected_y = -1
        self.in_chain_jump = False

        if self.count_pieces(False) == 0 or not self.side_has_any_move(False):
            self._add_score(300)
            self._state = STATE_VICTORY
            self.state_timer = 0.0
            return
        if self.quiet_turns >= 80:
            if self.count_pieces(True) > self.count_pieces(False):
                self._add_score(200)
                self._state = STATE_VICTORY
            else:
                self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return

        self.player_turn = False
        self.ai_timer = 0.22

    def _make_ai_turn(self) -> None:
        best_eval = -999999
        best_move = None

        for sy in range(BOARD_SIZE):
            for sx in range(BOARD_SIZE):
                p = self.board[sy][sx]
                if not self.is_ai_piece(p):
                    continue
                for dy in (-2, -1, 1, 2):
                    for dx in (-2, -1, 1, 2):
                        if abs(dx) != abs(dy):
                            continue
                        tx, ty = sx + dx, sy + dy
                        if not self.is_valid_move(sx, sy, tx, ty, False):
                            continue
                        ev = 0
                        if abs(dx) == 2:
                            ev += 120
                        else:
                            if p == AI_MAN and dy > 0:
                                ev += 8 + ty * 2
                            if sy == 0 and p == AI_MAN:
                                ev -= 6
                        if p == AI_MAN and ty == BOARD_SIZE - 1:
                            ev += 40
                        if self._would_be_capturable_at(tx, ty, sx, sy):
                            ev -= 35
                        if 2 <= tx <= 5:
                            ev += 3

                        if ev > best_eval:
                            best_eval = ev
                            best_move = (sx, sy, tx, ty)

        if best_move is not None:
            sx, sy, tx, ty = best_move
            p = self.board[sy][sx]
            self.board[sy][sx] = EMPTY
            jumped = (abs(tx - sx) == 2)
            if jumped:
                self.board[(sy + ty) // 2][(sx + tx) // 2] = EMPTY
                self.quiet_turns = 0
            else:
                self.quiet_turns += 1
            promoted = False
            if p == AI_MAN and ty == BOARD_SIZE - 1:
                p = AI_KING
                promoted = True
            self.board[ty][tx] = p

            while jumped and (not promoted) and self.has_move_from(tx, ty, True):
                next_pos = None
                for dy in (-2, 2):
                    for dx in (-2, 2):
                        if self.is_valid_move(tx, ty, tx + dx, ty + dy, True):
                            next_pos = (tx + dx, ty + dy)
                            break
                    if next_pos is not None:
                        break
                if next_pos is None:
                    break
                next_tx, next_ty = next_pos
                self.board[ty][tx] = EMPTY
                self.board[(ty + next_ty) // 2][(tx + next_tx) // 2] = EMPTY
                tx, ty = next_tx, next_ty
                if p == AI_MAN and ty == BOARD_SIZE - 1:
                    p = AI_KING
                    promoted = True
                self.board[ty][tx] = p

        if self.count_pieces(True) == 0 or not self.side_has_any_move(True):
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return
        if self.quiet_turns >= 80:
            if self.count_pieces(True) > self.count_pieces(False):
                self._add_score(200)
                self._state = STATE_VICTORY
            else:
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
                    if self.cursor_x < BOARD_SIZE - 1:
                        self.cursor_x += 1
                if keys_pressed & KEY_UP:
                    if self.cursor_y > 0:
                        self.cursor_y -= 1
                elif keys_pressed & KEY_DOWN:
                    if self.cursor_y < BOARD_SIZE - 1:
                        self.cursor_y += 1

                if keys_pressed & KEY_B:
                    if self.in_chain_jump:
                        self._end_player_turn()
                    else:
                        self.selected_x = -1
                        self.selected_y = -1
                    return

                if keys_pressed & KEY_A:
                    if self.selected_x >= 0 and self.is_valid_move(
                        self.selected_x, self.selected_y, self.cursor_x, self.cursor_y, self.in_chain_jump
                    ):
                        sx, sy = self.selected_x, self.selected_y
                        tx, ty = self.cursor_x, self.cursor_y
                        p = self.board[sy][sx]
                        self.board[sy][sx] = EMPTY

                        jumped = (abs(tx - sx) == 2)
                        if jumped:
                            self.board[(sy + ty) // 2][(sx + tx) // 2] = EMPTY
                            self._add_score(50)
                            self.quiet_turns = 0
                        else:
                            self.quiet_turns += 1

                        promoted = False
                        if p == P_MAN and ty == 0:
                            p = P_KING
                            promoted = True
                        self.board[ty][tx] = p

                        if self.count_pieces(False) == 0:
                            self._add_score(300)
                            self._state = STATE_VICTORY
                            self.state_timer = 0.0
                            return

                        if jumped and (not promoted) and self.has_move_from(tx, ty, True):
                            self.selected_x = tx
                            self.selected_y = ty
                            self.in_chain_jump = True
                        else:
                            self._end_player_turn()
                    elif not self.in_chain_jump:
                        clicked = self.board[self.cursor_y][self.cursor_x]
                        if self.is_player_piece(clicked) and self.has_move_from(self.cursor_x, self.cursor_y, False):
                            self.selected_x = self.cursor_x
                            self.selected_y = self.cursor_y
            else:
                self.ai_timer -= dt
                if self.ai_timer <= 0.0:
                    self._make_ai_turn()

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
                dark = ((cx + cy) % 2 == 1)
                br = 24 if dark else 64
                bg = 20 if dark else 52
                bb = 18 if dark else 38

                p = self.board[cy][cx]
                if p == EMPTY:
                    _set_px(fb, px, py, br, bg, bb)
                    _set_px(fb, px + 1, py, br, bg, bb)
                    _set_px(fb, px, py + 1, br, bg, bb)
                    _set_px(fb, px + 1, py + 1, br, bg, bb)
                    if (
                        self._state == STATE_PLAYING
                        and self.player_turn
                        and self.selected_x >= 0
                        and self.is_valid_move(self.selected_x, self.selected_y, cx, cy, self.in_chain_jump)
                    ):
                        _set_px(fb, px, py, 46, 210, 115)
                        _set_px(fb, px + 1, py + 1, 46, 210, 115)
                elif self.is_player_piece(p):
                    _set_px(fb, px, py, 80, 245, 255)
                    _set_px(fb, px + 1, py, 0, 205, 240)
                    _set_px(fb, px, py + 1, 0, 205, 240)
                    _set_px(fb, px + 1, py + 1, 0, 160, 205)
                    if p == P_KING:
                        _set_px(fb, px + 1, py, 255, 220, 20)
                else:
                    _set_px(fb, px, py, 255, 110, 100)
                    _set_px(fb, px + 1, py, 230, 45, 45)
                    _set_px(fb, px, py + 1, 230, 45, 45)
                    _set_px(fb, px + 1, py + 1, 180, 25, 25)
                    if p == AI_KING:
                        _set_px(fb, px + 1, py, 255, 220, 20)

                if cx == self.selected_x and cy == self.selected_y:
                    _set_px(fb, px, py, 130, 255, 140)

        if self._state == STATE_PLAYING and self.player_turn:
            if (int(self.anim_timer * 6.0) % 2) == 0:
                px = self.cursor_x * 2
                py = self.cursor_y * 2
                _set_px(fb, px, py, 255, 240, 50)
                _set_px(fb, px + 1, py + 1, 255, 240, 50)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        captured = max(0, 12 - self.count_pieces(False))
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": (captured * 100) // 12,
        }
