# -*- coding: utf-8 -*-
"""game_052_pipe_connect.py —— 目标 #052 管道旋转接水 (Pipe Connect 1989)
5x5 3x3像素管道网络 + 90度顺时针旋转 + 实时连通水色预览 + 放水防漏导流
"""

from collections import deque
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

GRID_SIZE = 5
NUM_STAGES = 3

PORT_UP = 1 << 0
PORT_RIGHT = 1 << 1
PORT_DOWN = 1 << 2
PORT_LEFT = 1 << 3

DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]

STAGE_INIT: List[List[List[int]]] = [
    # Stage 0: S弯折管路
    [
        [2, 5, 3, 10, 6],
        [5, 6, 5, 12, 5],
        [3, 10, 9, 10, 6],
        [5, 9, 6, 5, 5],
        [3, 10, 9, 10, 1],
    ],
    # Stage 1: 十字立交桥环路 (含 CROSS=15)
    [
        [4, 10, 6, 12, 6],
        [10, 3, 3, 9, 5],
        [9, 10, 15, 6, 5],
        [5, 6, 9, 5, 6],
        [3, 10, 12, 10, 1],
    ],
    # Stage 2: 三通双支路汇流 (含两个 TEE)
    [
        [2, 7, 5, 6, 12],
        [6, 10, 6, 5, 5],
        [5, 5, 10, 10, 5],
        [3, 9, 10, 14, 6],
        [3, 10, 9, 10, 1],
    ],
]


class Game052PipeConnect(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.stage = 0
        self.cursor_x = 1
        self.cursor_y = 0
        self.flow_active = False
        self.prep_countdown = 15.0
        self.flow_timer = 0.0
        self.flow_interval = 0.22
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.masks: List[List[int]] = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.fixed: List[List[bool]] = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.wet_preview: List[List[bool]] = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.flowing: List[List[bool]] = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 52

    @property
    def name(self) -> str:
        return "管道旋转接水"

    @property
    def english_name(self) -> str:
        return "Pipe Connect"

    @property
    def release_year(self) -> int:
        return 1989

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "网格管件90度旋转配接与实时水流防漏导通"

    @staticmethod
    def rotate_mask_cw(mask: int) -> int:
        return ((mask << 1) & 0x0F) | ((mask >> 3) & 0x01)

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
        self.masks = [list(row) for row in STAGE_INIT[self.stage]]
        self.fixed = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.flowing = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.fixed[0][0] = True
        self.fixed[4][4] = True
        self.cursor_x = 1
        self.cursor_y = 0
        self.flow_active = False
        self.prep_countdown = 15.0
        self.flow_timer = 0.0
        self.flow_interval = 0.22
        self._recompute_wet_preview()

    def _recompute_wet_preview(self) -> None:
        self.wet_preview = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.wet_preview[0][0] = True
        q = deque([(0, 0)])
        while q:
            cx, cy = q.popleft()
            m = self.masks[cy][cx]
            for d in range(4):
                if not (m & (1 << d)):
                    continue
                nx, ny = cx + DX[d], cy + DY[d]
                if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    continue
                opp = (d + 2) & 3
                if (self.masks[ny][nx] & (1 << opp)) and not self.wet_preview[ny][nx]:
                    self.wet_preview[ny][nx] = True
                    q.append((nx, ny))

    def _step_water_flow(self) -> None:
        next_flowing = [list(row) for row in self.flowing]
        leak = False
        newly_wet = 0

        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if not self.flowing[y][x]:
                    continue
                m = self.masks[y][x]
                for d in range(4):
                    if not (m & (1 << d)):
                        continue
                    nx, ny = x + DX[d], y + DY[d]
                    if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                        leak = True
                        continue
                    opp = (d + 2) & 3
                    if not (self.masks[ny][nx] & (1 << opp)):
                        leak = True
                        continue
                    if not next_flowing[ny][nx]:
                        next_flowing[ny][nx] = True
                        newly_wet += 1

        self.flowing = next_flowing

        if leak:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return

        if self.flowing[4][4]:
            self._add_score(200)
            if self.stage + 1 < NUM_STAGES:
                self._load_stage(self.stage + 1)
            else:
                self._state = STATE_VICTORY
                self.state_timer = 0.0
            return

        if newly_wet == 0:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._load_stage(0)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
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

            if keys_pressed & KEY_LEFT:
                if self.cursor_x > 0:
                    self.cursor_x -= 1
            elif keys_pressed & KEY_RIGHT:
                if self.cursor_x < GRID_SIZE - 1:
                    self.cursor_x += 1
            elif keys_pressed & KEY_UP:
                if self.cursor_y > 0:
                    self.cursor_y -= 1
            elif keys_pressed & KEY_DOWN:
                if self.cursor_y < GRID_SIZE - 1:
                    self.cursor_y += 1

            if keys_pressed & KEY_A:
                if not self.fixed[self.cursor_y][self.cursor_x] and not self.flowing[self.cursor_y][self.cursor_x]:
                    self.masks[self.cursor_y][self.cursor_x] = self.rotate_mask_cw(
                        self.masks[self.cursor_y][self.cursor_x]
                    )
                    self._recompute_wet_preview()

            if keys_pressed & KEY_B:
                if not self.flow_active:
                    self.flow_active = True
                    self.prep_countdown = 0.0
                    self.flowing[0][0] = True
                    self.flow_timer = 0.0
                self.flow_interval = 0.06

            if not self.flow_active:
                self.prep_countdown -= dt
                if self.prep_countdown <= 0.0:
                    self.prep_countdown = 0.0
                    self.flow_active = True
                    self.flowing[0][0] = True
                    self.flow_timer = 0.0
            else:
                self.flow_timer += dt
                while self.flow_timer >= self.flow_interval and self._state == STATE_PLAYING and self.flow_active:
                    self.flow_timer -= self.flow_interval
                    self._step_water_flow()

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
                self._set_px(fb, x, y, 16, 20, 28)

        bar_len = int((self.prep_countdown / 15.0) * 15.0 + 0.5)
        for x in range(15):
            if self.flow_active:
                self._set_px(fb, x, 0, 0, 220, 255)
            elif x < bar_len:
                self._set_px(fb, x, 0, 245, 180, 25)
            else:
                self._set_px(fb, x, 0, 35, 40, 50)

        for s in range(NUM_STAGES):
            py = 3 + s * 4
            if s < self.stage:
                self._set_px(fb, 15, py, 46, 215, 100)
            elif s == self.stage:
                self._set_px(fb, 15, py, 255, 215, 35)
            else:
                self._set_px(fb, 15, py, 50, 55, 68)

        for gy in range(GRID_SIZE):
            for gx in range(GRID_SIZE):
                px0 = gx * 3
                py0 = 1 + gy * 3
                m = self.masks[gy][gx]
                if m == 0:
                    continue

                r, g, b = 115, 126, 138
                if self.flowing[gy][gx]:
                    r, g, b = 90, 255, 255
                elif self.wet_preview[gy][gx]:
                    r, g, b = 0, 195, 245

                if gx == 0 and gy == 0:
                    r, g, b = 35, 235, 140
                elif gx == 4 and gy == 4:
                    if self.flowing[4][4] or self.wet_preview[4][4]:
                        r, g, b = 80, 255, 160
                    else:
                        r, g, b = 245, 165, 25

                self._set_px(fb, px0 + 1, py0 + 1, r, g, b)
                if m & PORT_UP:
                    self._set_px(fb, px0 + 1, py0, r, g, b)
                if m & PORT_RIGHT:
                    self._set_px(fb, px0 + 2, py0 + 1, r, g, b)
                if m & PORT_DOWN:
                    self._set_px(fb, px0 + 1, py0 + 2, r, g, b)
                if m & PORT_LEFT:
                    self._set_px(fb, px0, py0 + 1, r, g, b)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            if (int(self.anim_timer * 6.0) % 2) == 0:
                cx0 = self.cursor_x * 3
                cy0 = 1 + self.cursor_y * 3
                self._set_px(fb, cx0, cy0, 255, 255, 100)
                self._set_px(fb, cx0 + 2, cy0, 255, 255, 100)
                self._set_px(fb, cx0, cy0 + 2, 255, 255, 100)
                self._set_px(fb, cx0 + 2, cy0 + 2, 255, 255, 100)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                self._set_px(fb, x, 0, 240, 50, 45)
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = self.stage * 33 + (20 if self.wet_preview[4][4] else 0)
        if self._state == STATE_VICTORY:
            prog = 100
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, prog),
        }
