# -*- coding: utf-8 -*-
"""game_067_quoridor.py —— 目标 #067 围墙棋 (Quoridor, 1997)
7x7 棋子晶格与 2 格隔墙沟槽 + 越子跳跃 + BFS 双向通路反封死合法性检验 + 最短路博弈 AI
"""

from collections import deque
from typing import Dict, Any, List, Optional, Tuple
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

CELLS = 7
GROOVES = 6
MAX_WALLS = 5

MODE_MOVE = 0
MODE_WALL_H = 1
MODE_WALL_V = 2

QUOR_DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))  # UP, DOWN, LEFT, RIGHT


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class Game067Quoridor(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.h_walls: List[List[bool]] = [[False] * GROOVES for _ in range(GROOVES)]
        self.v_walls: List[List[bool]] = [[False] * GROOVES for _ in range(GROOVES)]
        self.player_c = 3
        self.player_r = 6
        self.ai_c = 3
        self.ai_r = 0
        self.player_walls = MAX_WALLS
        self.ai_walls = MAX_WALLS
        self.mode = MODE_MOVE
        self.aim_dir = 0
        self.wall_c = 2
        self.wall_r = 2
        self.player_turn = True
        self.ai_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 67

    @property
    def name(self) -> str:
        return "围墙棋"

    @property
    def english_name(self) -> str:
        return "Quoridor"

    @property
    def release_year(self) -> int:
        return 1997

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "迷宫筑墙阻截与双向通路反封死竞速"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_board(self) -> None:
        self.h_walls = [[False] * GROOVES for _ in range(GROOVES)]
        self.v_walls = [[False] * GROOVES for _ in range(GROOVES)]
        self.player_c = 3
        self.player_r = 6
        self.ai_c = 3
        self.ai_r = 0
        self.player_walls = MAX_WALLS
        self.ai_walls = MAX_WALLS
        self.mode = MODE_MOVE
        self.aim_dir = 0
        self.wall_c = 2
        self.wall_r = 2
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

    def is_edge_blocked(self, c1: int, r1: int, c2: int, r2: int) -> bool:
        if c1 == c2:
            r_min = min(r1, r2)
            if not (0 <= r_min < GROOVES):
                return True
            if c1 < GROOVES and self.h_walls[r_min][c1]:
                return True
            if c1 > 0 and self.h_walls[r_min][c1 - 1]:
                return True
            return False
        if r1 == r2:
            c_min = min(c1, c2)
            if not (0 <= c_min < GROOVES):
                return True
            if r1 < GROOVES and self.v_walls[r1][c_min]:
                return True
            if r1 > 0 and self.v_walls[r1 - 1][c_min]:
                return True
            return False
        return True

    def shortest_path_len(self, sc: int, sr: int, goal_row: int) -> int:
        if sr == goal_row:
            return 0
        dist = [[-1] * CELLS for _ in range(CELLS)]
        dist[sr][sc] = 0
        q = deque([(sc, sr)])
        while q:
            c, r = q.popleft()
            d = dist[r][c]
            if r == goal_row:
                return d
            for dc, dr in QUOR_DIRS:
                nc, nr = c + dc, r + dr
                if not (0 <= nc < CELLS and 0 <= nr < CELLS):
                    continue
                if dist[nr][nc] >= 0:
                    continue
                if self.is_edge_blocked(c, r, nc, nr):
                    continue
                dist[nr][nc] = d + 1
                if nr == goal_row:
                    return d + 1
                q.append((nc, nr))
        return -1

    def can_place_wall(self, wc: int, wr: int, horiz: bool) -> bool:
        if not (0 <= wc < GROOVES and 0 <= wr < GROOVES):
            return False
        if horiz:
            if self.h_walls[wr][wc]:
                return False
            if wc > 0 and self.h_walls[wr][wc - 1]:
                return False
            if wc + 1 < GROOVES and self.h_walls[wr][wc + 1]:
                return False
            if self.v_walls[wr][wc]:
                return False

            self.h_walls[wr][wc] = True
            pd = self.shortest_path_len(self.player_c, self.player_r, 0)
            ad = self.shortest_path_len(self.ai_c, self.ai_r, CELLS - 1)
            self.h_walls[wr][wc] = False
            return pd >= 0 and ad >= 0
        else:
            if self.v_walls[wr][wc]:
                return False
            if wr > 0 and self.v_walls[wr - 1][wc]:
                return False
            if wr + 1 < GROOVES and self.v_walls[wr + 1][wc]:
                return False
            if self.h_walls[wr][wc]:
                return False

            self.v_walls[wr][wc] = True
            pd = self.shortest_path_len(self.player_c, self.player_r, 0)
            ad = self.shortest_path_len(self.ai_c, self.ai_r, CELLS - 1)
            self.v_walls[wr][wc] = False
            return pd >= 0 and ad >= 0

    def compute_pawn_step(self, sc: int, sr: int, oc: int, orow: int, direction: int) -> Optional[Tuple[int, int]]:
        if not (0 <= direction < 4):
            return None
        dc, dr = QUOR_DIRS[direction]
        nc, nr = sc + dc, sr + dr
        if not (0 <= nc < CELLS and 0 <= nr < CELLS):
            return None
        if self.is_edge_blocked(sc, sr, nc, nr):
            return None

        if nc == oc and nr == orow:
            jc, jr = nc + dc, nr + dr
            if 0 <= jc < CELLS and 0 <= jr < CELLS and not self.is_edge_blocked(nc, nr, jc, jr):
                return (jc, jr)
            p1c, p1r = nc - dr, nr + dc
            if 0 <= p1c < CELLS and 0 <= p1r < CELLS and not self.is_edge_blocked(nc, nr, p1c, p1r):
                return (p1c, p1r)
            p2c, p2r = nc + dr, nr - dc
            if 0 <= p2c < CELLS and 0 <= p2r < CELLS and not self.is_edge_blocked(nc, nr, p2c, p2r):
                return (p2c, p2r)
            return None

        return (nc, nr)

    def _make_ai_turn(self) -> None:
        p_dist = self.shortest_path_len(self.player_c, self.player_r, 0)
        a_dist = self.shortest_path_len(self.ai_c, self.ai_r, CELLS - 1)

        if self.ai_walls > 0 and p_dist <= a_dist and p_dist <= 4:
            best_gain = 0
            best_wall = None
            for horiz in (True, False):
                for wr in range(GROOVES):
                    for wc in range(GROOVES):
                        if not self.can_place_wall(wc, wr, horiz):
                            continue
                        if horiz:
                            self.h_walls[wr][wc] = True
                        else:
                            self.v_walls[wr][wc] = True

                        np = self.shortest_path_len(self.player_c, self.player_r, 0)
                        na = self.shortest_path_len(self.ai_c, self.ai_r, CELLS - 1)

                        if horiz:
                            self.h_walls[wr][wc] = False
                        else:
                            self.v_walls[wr][wc] = False

                        gain = (np - p_dist) - (na - a_dist)
                        if gain > best_gain:
                            best_gain = gain
                            best_wall = (wc, wr, horiz)

            min_gain = 1 if p_dist <= 2 else 2
            if best_wall is not None and best_gain >= min_gain:
                wc, wr, horiz = best_wall
                if horiz:
                    self.h_walls[wr][wc] = True
                else:
                    self.v_walls[wr][wc] = True
                self.ai_walls -= 1
                self.player_turn = True
                return

        best_step = None
        best_len = 999999
        for d in range(4):
            step = self.compute_pawn_step(self.ai_c, self.ai_r, self.player_c, self.player_r, d)
            if step is not None:
                rem = self.shortest_path_len(step[0], step[1], CELLS - 1)
                if 0 <= rem < best_len:
                    best_len = rem
                    best_step = step

        if best_step is not None:
            self.ai_c, self.ai_r = best_step
            if self.ai_r == CELLS - 1:
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
                if keys_pressed & KEY_B:
                    if self.player_walls > 0:
                        self.mode = (self.mode + 1) % 3
                    else:
                        self.mode = MODE_MOVE

                if self.mode == MODE_MOVE:
                    if keys_pressed & KEY_UP:
                        self.aim_dir = 0
                    elif keys_pressed & KEY_DOWN:
                        self.aim_dir = 1
                    elif keys_pressed & KEY_LEFT:
                        self.aim_dir = 2
                    elif keys_pressed & KEY_RIGHT:
                        self.aim_dir = 3

                    if keys_pressed & KEY_A:
                        step = self.compute_pawn_step(
                            self.player_c, self.player_r, self.ai_c, self.ai_r, self.aim_dir
                        )
                        if step is not None:
                            self.player_c, self.player_r = step
                            self._add_score(10)
                            if self.player_r == 0:
                                self._add_score(400)
                                self._state = STATE_VICTORY
                                self.state_timer = 0.0
                                return
                            self.player_turn = False
                            self.ai_timer = 0.20
                else:
                    if keys_pressed & KEY_LEFT:
                        if self.wall_c > 0:
                            self.wall_c -= 1
                    elif keys_pressed & KEY_RIGHT:
                        if self.wall_c < GROOVES - 1:
                            self.wall_c += 1
                    if keys_pressed & KEY_UP:
                        if self.wall_r > 0:
                            self.wall_r -= 1
                    elif keys_pressed & KEY_DOWN:
                        if self.wall_r < GROOVES - 1:
                            self.wall_r += 1

                    if keys_pressed & KEY_A:
                        horiz = (self.mode == MODE_WALL_H)
                        if self.player_walls > 0 and self.can_place_wall(self.wall_c, self.wall_r, horiz):
                            if horiz:
                                self.h_walls[self.wall_r][self.wall_c] = True
                            else:
                                self.v_walls[self.wall_r][self.wall_c] = True
                            self.player_walls -= 1
                            self.mode = MODE_MOVE
                            self.player_turn = False
                            self.ai_timer = 0.20
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
        for y in range(16):
            for x in range(16):
                _set_px(fb, x, y, 12, 12, 18)

        for x in range(1, 14):
            _set_px(fb, x, 0, 0, 75, 95)
            _set_px(fb, x, 14, 95, 25, 25)

        for r in range(CELLS):
            for c in range(CELLS):
                _set_px(fb, 1 + c * 2, 1 + r * 2, 42, 36, 32)

        for wr in range(GROOVES):
            for wc in range(GROOVES):
                if self.h_walls[wr][wc]:
                    y = 2 + wr * 2
                    x0 = 1 + wc * 2
                    for dx in range(3):
                        _set_px(fb, x0 + dx, y, 235, 170, 45)
                if self.v_walls[wr][wc]:
                    x = 2 + wc * 2
                    y0 = 1 + wr * 2
                    for dy in range(3):
                        _set_px(fb, x, y0 + dy, 235, 170, 45)

        if self._state == STATE_PLAYING and self.player_turn:
            blink = ((int(self.anim_timer * 6.0) % 2) == 0)
            if self.mode == MODE_MOVE:
                step = self.compute_pawn_step(self.player_c, self.player_r, self.ai_c, self.ai_r, self.aim_dir)
                if blink and step is not None:
                    _set_px(fb, 1 + step[0] * 2, 1 + step[1] * 2, 60, 230, 120)
            else:
                horiz = (self.mode == MODE_WALL_H)
                ok = self.can_place_wall(self.wall_c, self.wall_r, horiz)
                if blink:
                    cr, cg, cb = (90, 250, 110) if ok else (240, 45, 45)
                    if horiz:
                        y = 2 + self.wall_r * 2
                        x0 = 1 + self.wall_c * 2
                        for dx in range(3):
                            _set_px(fb, x0 + dx, y, cr, cg, cb)
                    else:
                        x = 2 + self.wall_c * 2
                        y0 = 1 + self.wall_r * 2
                        for dy in range(3):
                            _set_px(fb, x, y0 + dy, cr, cg, cb)

        _set_px(fb, 1 + self.player_c * 2, 1 + self.player_r * 2, 0, 235, 255)
        _set_px(fb, 1 + self.ai_c * 2, 1 + self.ai_r * 2, 255, 65, 55)

        for i in range(self.player_walls):
            _set_px(fb, 1 + i, 15, 0, 200, 235)
        for i in range(self.ai_walls):
            _set_px(fb, 14 - i, 15, 235, 80, 65)
        if self.mode == MODE_MOVE:
            _set_px(fb, 7, 15, 0, 235, 255)
        else:
            _set_px(fb, 7, 15, 255, 215, 30)
            _set_px(fb, 8, 15, 255, 215, 30)

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
            "progress": ((6 - self.player_r) * 100) // 6,
        }
