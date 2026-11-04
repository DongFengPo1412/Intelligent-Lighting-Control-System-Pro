# -*- coding: utf-8 -*-
"""game_051_flow_free.py —— 目标 #051 同色连线 (Flow Free 2012)
6x6 网格四色端点配对 + 非交叉导线逐步延伸/回退/截断 + 满格奖励通关
"""

from typing import Dict, Any, List, Tuple, Optional
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
    KEY_SELECT,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

GRID_SIZE = 6
GRID_CELLS = GRID_SIZE * GRID_SIZE
NUM_COLORS = 4
NUM_STAGES = 4

STAGES: List[List[Tuple[Tuple[int, int], Tuple[int, int]]]] = [
    # Stage 0: 嵌套 L 形走廊
    [
        ((0, 0), (5, 2)),
        ((0, 1), (4, 3)),
        ((0, 2), (5, 3)),
        ((2, 3), (5, 5)),
    ],
    # Stage 1: 风车螺旋
    [
        ((0, 5), (3, 0)),
        ((4, 0), (3, 5)),
        ((2, 5), (4, 1)),
        ((4, 2), (2, 4)),
    ],
    # Stage 2: 纵向编织
    [
        ((0, 0), (2, 5)),
        ((1, 0), (3, 4)),
        ((2, 0), (3, 5)),
        ((3, 2), (5, 5)),
    ],
    # Stage 3: 镜像风车螺旋
    [
        ((5, 5), (2, 0)),
        ((1, 0), (2, 5)),
        ((3, 5), (1, 1)),
        ((1, 2), (3, 4)),
    ],
]

ENDPOINT_RGB = [
    (255, 75, 65),
    (60, 235, 110),
    (70, 180, 255),
    (255, 225, 45),
]

WIRE_RGB = [
    (185, 45, 40),
    (34, 160, 74),
    (38, 118, 195),
    (190, 155, 20),
]


class Game051FlowFree(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.stage = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.active_color = -1
        self.drawing = False
        self.moves = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.endpoints: List[List[Tuple[int, int]]] = []
        self.paths: List[List[Tuple[int, int]]] = [[] for _ in range(NUM_COLORS)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 51

    @property
    def name(self) -> str:
        return "同色连线"

    @property
    def english_name(self) -> str:
        return "Flow Free"

    @property
    def release_year(self) -> int:
        return 2012

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "网格非交叉四色导线连接与异色截断解谜"

    def init(self) -> None:
        self.reset()

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _load_stage(self, stage_idx: int) -> None:
        if not (0 <= stage_idx < NUM_STAGES):
            stage_idx = 0
        self.stage = stage_idx
        self.endpoints = [[ep[0], ep[1]] for ep in STAGES[self.stage]]
        self.paths = [[] for _ in range(NUM_COLORS)]
        self.cursor_x, self.cursor_y = self.endpoints[0][0]
        self.active_color = -1
        self.drawing = False

    def endpoint_color_at(self, x: int, y: int) -> int:
        for c in range(NUM_COLORS):
            if (x, y) == self.endpoints[c][0] or (x, y) == self.endpoints[c][1]:
                return c
        return -1

    def wire_color_at(self, x: int, y: int) -> Tuple[int, int]:
        for c in range(NUM_COLORS):
            for i, pt in enumerate(self.paths[c]):
                if pt == (x, y):
                    return c, i
        return -1, -1

    def is_color_connected(self, color: int) -> bool:
        if not (0 <= color < NUM_COLORS):
            return False
        path = self.paths[color]
        if len(path) < 2:
            return False
        p0, p1 = path[0], path[-1]
        e0, e1 = self.endpoints[color][0], self.endpoints[color][1]
        return (p0 == e0 and p1 == e1) or (p0 == e1 and p1 == e0)

    def count_connected_colors(self) -> int:
        return sum(1 for c in range(NUM_COLORS) if self.is_color_connected(c))

    def count_covered_cells(self) -> int:
        used = set()
        for c in range(NUM_COLORS):
            used.add(self.endpoints[c][0])
            used.add(self.endpoints[c][1])
            for pt in self.paths[c]:
                used.add(pt)
        return len(used)

    def _check_stage_clear(self) -> None:
        if self.count_connected_colors() == NUM_COLORS:
            bonus = 100 if self.count_covered_cells() == GRID_CELLS else 0
            self._add_score(200 + bonus)
            self.drawing = False
            self.active_color = -1
            if self.stage + 1 < NUM_STAGES:
                self._load_stage(self.stage + 1)
            else:
                self._state = STATE_VICTORY
                self.state_timer = 0.0

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self.moves = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._load_stage(0)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.moves = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._load_stage(0)

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

            if keys_pressed & KEY_SELECT:
                self._load_stage(self.stage)
                return

            if keys_pressed & KEY_B:
                if self.drawing and self.active_color >= 0:
                    self.paths[self.active_color] = []
                    self.drawing = False
                    self.active_color = -1
                else:
                    wc, _ = self.wire_color_at(self.cursor_x, self.cursor_y)
                    ec = self.endpoint_color_at(self.cursor_x, self.cursor_y)
                    tc = wc if wc >= 0 else ec
                    if tc >= 0 and len(self.paths[tc]) > 0:
                        self.paths[tc] = []
                    else:
                        self._load_stage(self.stage)
                return

            if keys_pressed & KEY_A:
                if self.drawing:
                    self.drawing = False
                    self.active_color = -1
                else:
                    ec = self.endpoint_color_at(self.cursor_x, self.cursor_y)
                    wc, seg = self.wire_color_at(self.cursor_x, self.cursor_y)
                    if ec >= 0:
                        self.paths[ec] = [(self.cursor_x, self.cursor_y)]
                        self.active_color = ec
                        self.drawing = True
                    elif wc >= 0 and seg >= 0:
                        self.paths[wc] = self.paths[wc][: seg + 1]
                        self.active_color = wc
                        self.drawing = True
                return

            dx, dy = 0, 0
            if keys_pressed & KEY_UP:
                dy = -1
            elif keys_pressed & KEY_DOWN:
                dy = 1
            elif keys_pressed & KEY_LEFT:
                dx = -1
            elif keys_pressed & KEY_RIGHT:
                dx = 1

            if dx != 0 or dy != 0:
                nx = self.cursor_x + dx
                ny = self.cursor_y + dy
                if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    return

                if not self.drawing or self.active_color < 0:
                    self.cursor_x, self.cursor_y = nx, ny
                    return

                c = self.active_color
                ep_c = self.endpoint_color_at(nx, ny)
                if ep_c >= 0 and ep_c != c:
                    return

                if (nx, ny) in self.paths[c]:
                    own_idx = self.paths[c].index((nx, ny))
                    self.paths[c] = self.paths[c][: own_idx + 1]
                    self.cursor_x, self.cursor_y = nx, ny
                    self.moves += 1
                    return

                if self.is_color_connected(c):
                    self.drawing = False
                    self.active_color = -1
                    return

                other_c, _ = self.wire_color_at(nx, ny)
                if other_c >= 0 and other_c != c:
                    self.paths[other_c] = []

                if len(self.paths[c]) < GRID_CELLS:
                    self.paths[c].append((nx, ny))
                    self.cursor_x, self.cursor_y = nx, ny
                    self.moves += 1
                    if self.is_color_connected(c):
                        self.drawing = False
                        self.active_color = -1
                        self._check_stage_clear()

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
                if 2 <= x <= 13 and 2 <= y <= 13:
                    gx = (x - 2) // 2
                    gy = (y - 2) // 2
                    base = 24 if ((gx + gy) & 1) else 18
                    self._set_px(fb, x, y, base, base + 4, base + 10)
                else:
                    self._set_px(fb, x, y, 10, 14, 24)

        for s in range(NUM_STAGES):
            px = 4 + s * 2 + (1 if s >= 2 else 0)
            if s < self.stage:
                self._set_px(fb, px, 0, 46, 215, 100)
            elif s == self.stage:
                self._set_px(fb, px, 0, 255, 215, 40)
            else:
                self._set_px(fb, px, 0, 45, 55, 70)

        for c in range(NUM_COLORS):
            wr, wg, wb = WIRE_RGB[c]
            for gx, gy in self.paths[c]:
                px, py = 2 + gx * 2, 2 + gy * 2
                for dy in range(2):
                    for dx in range(2):
                        self._set_px(fb, px + dx, py + dy, wr, wg, wb)

        for c in range(NUM_COLORS):
            er, eg, eb = ENDPOINT_RGB[c]
            for k in range(2):
                gx, gy = self.endpoints[c][k]
                px, py = 2 + gx * 2, 2 + gy * 2
                for dy in range(2):
                    for dx in range(2):
                        r, g, b = er, eg, eb
                        if dx == 0 and dy == 0:
                            r = (r + 255) >> 1
                            g = (g + 255) >> 1
                            b = (b + 255) >> 1
                        self._set_px(fb, px + dx, py + dy, r, g, b)

            bx = 4 + c * 2 + (1 if c >= 2 else 0)
            if self.is_color_connected(c):
                self._set_px(fb, bx, 15, er, eg, eb)
            else:
                wr, wg, wb = WIRE_RGB[c]
                self._set_px(fb, bx, 15, wr // 3, wg // 3, wb // 3)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            blink = (int(self.anim_timer * 6.0) % 2) == 0
            cpx = 2 + self.cursor_x * 2
            cpy = 2 + self.cursor_y * 2
            if self.drawing and self.active_color >= 0:
                self._set_px(fb, cpx, cpy, 255, 255, 255)
                self._set_px(fb, cpx + 1, cpy + 1, 255, 255, 255)
            elif blink:
                self._set_px(fb, cpx + 1, cpy, 255, 255, 255)
                self._set_px(fb, cpx, cpy + 1, 255, 255, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = self.stage * 25 + (self.count_connected_colors() * 25) // NUM_COLORS
        if self._state == STATE_VICTORY:
            prog = 100
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 1,
            "state": self._state,
            "progress": min(100, prog),
        }
