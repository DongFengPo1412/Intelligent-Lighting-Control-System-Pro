# -*- coding: utf-8 -*-
"""game_065_dots_and_boxes.py —— 目标 #065 点格棋 (Dots and Boxes, 1988)
5x5 顶点 4x4 方格网 + 封口占格连击奖励回合 + 防送三边安全策略 AI
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

TOTAL_EDGES = 40
UNCLAIMED = 0
PLAYER = 1
AI = 2


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class Game065DotsAndBoxes(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.h_edges: List[List[int]] = [[UNCLAIMED] * 4 for _ in range(5)]
        self.v_edges: List[List[int]] = [[UNCLAIMED] * 5 for _ in range(4)]
        self.boxes: List[List[int]] = [[UNCLAIMED] * 4 for _ in range(4)]
        self.cur_edge = 0
        self.player_boxes = 0
        self.ai_boxes = 0
        self.player_turn = True
        self.ai_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 65

    @property
    def name(self) -> str:
        return "点格棋"

    @property
    def english_name(self) -> str:
        return "Dots and Boxes"

    @property
    def release_year(self) -> int:
        return 1988

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "网格边线封口占格与额外连击回合博弈"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_board(self) -> None:
        self.h_edges = [[UNCLAIMED] * 4 for _ in range(5)]
        self.v_edges = [[UNCLAIMED] * 5 for _ in range(4)]
        self.boxes = [[UNCLAIMED] * 4 for _ in range(4)]
        self.cur_edge = 0
        self.player_boxes = 0
        self.ai_boxes = 0
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

    def is_edge_claimed(self, edge_id: int) -> bool:
        if not (0 <= edge_id < TOTAL_EDGES):
            return True
        if edge_id < 20:
            return self.h_edges[edge_id // 4][edge_id % 4] != UNCLAIMED
        v = edge_id - 20
        return self.v_edges[v // 5][v % 5] != UNCLAIMED

    def _set_edge_owner(self, edge_id: int, owner: int) -> None:
        if not (0 <= edge_id < TOTAL_EDGES):
            return
        if edge_id < 20:
            self.h_edges[edge_id // 4][edge_id % 4] = owner
        else:
            v = edge_id - 20
            self.v_edges[v // 5][v % 5] = owner

    @staticmethod
    def _edge_center_2x(edge_id: int) -> Tuple[int, int]:
        if edge_id < 20:
            r = edge_id // 4
            c = edge_id % 4
            return 7 + c * 6, 4 + r * 6
        v = edge_id - 20
        r = v // 5
        c = v % 5
        return 4 + c * 6, 7 + r * 6

    def box_edge_count(self, br: int, bc: int) -> int:
        cnt = 0
        if self.h_edges[br][bc] != UNCLAIMED:
            cnt += 1
        if self.h_edges[br + 1][bc] != UNCLAIMED:
            cnt += 1
        if self.v_edges[br][bc] != UNCLAIMED:
            cnt += 1
        if self.v_edges[br][bc + 1] != UNCLAIMED:
            cnt += 1
        return cnt

    def claim_edge(self, edge_id: int, owner: int) -> int:
        if self.is_edge_claimed(edge_id):
            return -1
        self._set_edge_owner(edge_id, owner)

        completed = 0
        if edge_id < 20:
            r = edge_id // 4
            c = edge_id % 4
            if r > 0 and self.boxes[r - 1][c] == UNCLAIMED and self.box_edge_count(r - 1, c) == 4:
                self.boxes[r - 1][c] = owner
                completed += 1
            if r < 4 and self.boxes[r][c] == UNCLAIMED and self.box_edge_count(r, c) == 4:
                self.boxes[r][c] = owner
                completed += 1
        else:
            v = edge_id - 20
            r = v // 5
            c = v % 5
            if c > 0 and self.boxes[r][c - 1] == UNCLAIMED and self.box_edge_count(r, c - 1) == 4:
                self.boxes[r][c - 1] = owner
                completed += 1
            if c < 4 and self.boxes[r][c] == UNCLAIMED and self.box_edge_count(r, c) == 4:
                self.boxes[r][c] = owner
                completed += 1

        if completed > 0:
            if owner == PLAYER:
                self.player_boxes += completed
                self._add_score(completed * 50)
            else:
                self.ai_boxes += completed
        return completed

    def _snap_cursor_to_unclaimed(self) -> None:
        if not self.is_edge_claimed(self.cur_edge):
            return
        cx2, cy2 = self._edge_center_2x(self.cur_edge)
        best_id = -1
        best_dist = 999999
        for i in range(TOTAL_EDGES):
            if not self.is_edge_claimed(i):
                jx2, jy2 = self._edge_center_2x(i)
                d = abs(jx2 - cx2) + abs(jy2 - cy2)
                if d < best_dist:
                    best_dist = d
                    best_id = i
        if best_id >= 0:
            self.cur_edge = best_id

    def _move_cursor_dir(self, dx: int, dy: int) -> None:
        self._snap_cursor_to_unclaimed()
        cx2, cy2 = self._edge_center_2x(self.cur_edge)
        best_id = -1
        best_cost = 999999
        for i in range(TOTAL_EDGES):
            if i == self.cur_edge or self.is_edge_claimed(i):
                continue
            jx2, jy2 = self._edge_center_2x(i)
            primary = (jx2 - cx2) * dx + (jy2 - cy2) * dy
            if primary <= 0:
                continue
            perp = abs(jy2 - cy2) if dx != 0 else abs(jx2 - cx2)
            cost = primary * 5 + perp * 6
            if cost < best_cost:
                best_cost = cost
                best_id = i
        if best_id >= 0:
            self.cur_edge = best_id

    def _toggle_cursor_orientation(self) -> None:
        self._snap_cursor_to_unclaimed()
        cx2, cy2 = self._edge_center_2x(self.cur_edge)
        rng = range(20, 40) if self.cur_edge < 20 else range(0, 20)
        best_id = -1
        best_dist = 999999
        for i in rng:
            if not self.is_edge_claimed(i):
                jx2, jy2 = self._edge_center_2x(i)
                d = abs(jx2 - cx2) + abs(jy2 - cy2)
                if d < best_dist:
                    best_dist = d
                    best_id = i
        if best_id >= 0:
            self.cur_edge = best_id

    def _choose_ai_edge(self) -> int:
        best_edge = -1
        best_score = -999999
        for i in range(TOTAL_EDGES):
            if self.is_edge_claimed(i):
                continue
            completes = 0
            gives_third = 0
            if i < 20:
                r = i // 4
                c = i % 4
                if r > 0:
                    ec = self.box_edge_count(r - 1, c)
                    if ec == 3:
                        completes += 1
                    elif ec == 2:
                        gives_third += 1
                if r < 4:
                    ec = self.box_edge_count(r, c)
                    if ec == 3:
                        completes += 1
                    elif ec == 2:
                        gives_third += 1
            else:
                v = i - 20
                r = v // 5
                c = v % 5
                if c > 0:
                    ec = self.box_edge_count(r, c - 1)
                    if ec == 3:
                        completes += 1
                    elif ec == 2:
                        gives_third += 1
                if c < 4:
                    ec = self.box_edge_count(r, c)
                    if ec == 3:
                        completes += 1
                    elif ec == 2:
                        gives_third += 1

            ev = completes * 1000 - gives_third * 200
            if ev > best_score:
                best_score = ev
                best_edge = i
        return best_edge

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
                self._snap_cursor_to_unclaimed()
                if keys_pressed & KEY_LEFT:
                    self._move_cursor_dir(-1, 0)
                elif keys_pressed & KEY_RIGHT:
                    self._move_cursor_dir(1, 0)
                elif keys_pressed & KEY_UP:
                    self._move_cursor_dir(0, -1)
                elif keys_pressed & KEY_DOWN:
                    self._move_cursor_dir(0, 1)

                if keys_pressed & KEY_B:
                    self._toggle_cursor_orientation()

                if keys_pressed & KEY_A:
                    made = self.claim_edge(self.cur_edge, PLAYER)
                    if made >= 0:
                        if self.player_boxes + self.ai_boxes >= 16:
                            if self.player_boxes > self.ai_boxes:
                                self._add_score(200)
                                self._state = STATE_VICTORY
                            else:
                                self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        self._snap_cursor_to_unclaimed()
                        if made == 0:
                            self.player_turn = False
                            self.ai_timer = 0.20
            else:
                self.ai_timer -= dt
                if self.ai_timer <= 0.0:
                    ai_e = self._choose_ai_edge()
                    if ai_e >= 0:
                        made = self.claim_edge(ai_e, AI)
                        if self.player_boxes + self.ai_boxes >= 16:
                            if self.player_boxes > self.ai_boxes:
                                self._add_score(200)
                                self._state = STATE_VICTORY
                            else:
                                self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        self._snap_cursor_to_unclaimed()
                        if made > 0:
                            self.ai_timer = 0.18
                        else:
                            self.player_turn = True
                    else:
                        self.player_turn = True

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                _set_px(fb, x, y, 12, 14, 24)

        for r in range(4):
            for c in range(4):
                b = self.boxes[r][c]
                if b != UNCLAIMED:
                    cr, cg, cb = (0, 130, 170) if b == PLAYER else (165, 35, 48)
                    x0 = 3 + c * 3
                    y0 = 3 + r * 3
                    for dy in range(2):
                        for dx in range(2):
                            _set_px(fb, x0 + dx, y0 + dy, cr, cg, cb)

        for r in range(5):
            for c in range(4):
                owner = self.h_edges[r][c]
                cr, cg, cb = 28, 32, 46
                if owner == PLAYER:
                    cr, cg, cb = 0, 215, 255
                elif owner == AI:
                    cr, cg, cb = 255, 75, 75
                x0 = 3 + c * 3
                y0 = 2 + r * 3
                _set_px(fb, x0, y0, cr, cg, cb)
                _set_px(fb, x0 + 1, y0, cr, cg, cb)

        for r in range(4):
            for c in range(5):
                owner = self.v_edges[r][c]
                cr, cg, cb = 28, 32, 46
                if owner == PLAYER:
                    cr, cg, cb = 0, 215, 255
                elif owner == AI:
                    cr, cg, cb = 255, 75, 75
                x0 = 2 + c * 3
                y0 = 3 + r * 3
                _set_px(fb, x0, y0, cr, cg, cb)
                _set_px(fb, x0, y0 + 1, cr, cg, cb)

        if self._state == STATE_PLAYING and self.player_turn and not self.is_edge_claimed(self.cur_edge):
            blink = ((int(self.anim_timer * 6.0) % 2) == 0)
            cr, cg, cb = (255, 235, 35) if blink else (140, 130, 25)
            if self.cur_edge < 20:
                r = self.cur_edge // 4
                c = self.cur_edge % 4
                x0 = 3 + c * 3
                y0 = 2 + r * 3
                _set_px(fb, x0, y0, cr, cg, cb)
                _set_px(fb, x0 + 1, y0, cr, cg, cb)
            else:
                v = self.cur_edge - 20
                r = v // 5
                c = v % 5
                x0 = 2 + c * 3
                y0 = 3 + r * 3
                _set_px(fb, x0, y0, cr, cg, cb)
                _set_px(fb, x0, y0 + 1, cr, cg, cb)

        for gy in range(5):
            for gx in range(5):
                _set_px(fb, 2 + gx * 3, 2 + gy * 3, 235, 240, 250)

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
            "progress": ((self.player_boxes + self.ai_boxes) * 100) // 16,
        }
