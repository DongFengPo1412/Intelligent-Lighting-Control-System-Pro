# -*- coding: utf-8 -*-
"""
Game #139: 阿米达格网 (Amidar 1981 / Konami & Stern)
街机历史上最经典的阿弥陀签梯子画线与区域封合格网涂色益智游戏：
沿纵横交错格线巡回描边、闭合矩形四周边界涂实填色、
按键B起跳腾空规避追击巡逻怪、全图九宫格点亮清屏通关。
"""

from typing import List, Dict, Any, Optional
import math
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

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_CAUGHT = 2
STATE_GAME_OVER = 3

GRID_COLS = [2, 6, 10, 14]
GRID_ROWS = [2, 6, 10, 14]


class Game139Amidar(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 2.0
        self.py = 2.0
        self.jumps_left = 3
        self.jump_timer = 0.0

        # Traced pixels along grid lines: 16x16 boolean array
        self.traced = [[False for _ in range(16)] for _ in range(16)]

        # 3x3 closed boxes: filled state
        self.boxes = [[False for _ in range(3)] for _ in range(3)]

        # Enemies patrolling grid
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 139

    @property
    def name(self) -> str:
        return "阿米达格网"

    @property
    def english_name(self) -> str:
        return "Amidar"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "阿弥陀签梯网描边圈地、矩形方格封合涂色、跳跃键跨越巡逻怪、全域涂满通关"

    def get_name(self) -> str:
        return "Amidar (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 2.0
        self.jumps_left = 3
        self.jump_timer = 0.0

        self.traced = [[False for _ in range(16)] for _ in range(16)]
        self.boxes = [[False for _ in range(3)] for _ in range(3)]

        # Mark starting pixel as traced
        self.traced[2][2] = True

        self.enemies = [
            {"x": 14.0, "y": 2.0, "dir": (0.0, 1.0), "speed": 3.0},
            {"x": 14.0, "y": 14.0, "dir": (-1.0, 0.0), "speed": 3.2},
            {"x": 2.0, "y": 14.0, "dir": (0.0, -1.0), "speed": 3.5},
        ]

    def _is_on_grid(self, x: float, y: float) -> bool:
        # Check if point is along any valid grid row or col
        ix = int(round(x))
        iy = int(round(y))
        if not (2 <= ix <= 14 and 2 <= iy <= 14):
            return False
        # Valid if on any row or col in GRID_COLS/GRID_ROWS
        on_col = any(abs(x - col) < 0.2 for col in GRID_COLS)
        on_row = any(abs(y - row) < 0.2 for row in GRID_ROWS)
        return on_col or on_row

    def _check_boxes(self) -> None:
        all_cleared = True
        for by in range(3):
            for bx in range(3):
                if not self.boxes[by][bx]:
                    # Check 4 edges
                    x1 = GRID_COLS[bx]
                    x2 = GRID_COLS[bx + 1]
                    y1 = GRID_ROWS[by]
                    y2 = GRID_ROWS[by + 1]

                    top_traced = all(self.traced[y1][x] for x in range(x1, x2 + 1))
                    bot_traced = all(self.traced[y2][x] for x in range(x1, x2 + 1))
                    left_traced = all(self.traced[y][x1] for y in range(y1, y2 + 1))
                    right_traced = all(self.traced[y][x2] for y in range(y1, y2 + 1))

                    if top_traced and bot_traced and left_traced and right_traced:
                        self.boxes[by][bx] = True
                        self.score += 200
                    else:
                        all_cleared = False

        if all_cleared:
            self.score += 1000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_CAUGHT):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_CAUGHT:
                    if self.lives > 0:
                        self.px = 2.0
                        self.py = 2.0
                        self.state = STATE_PLAYING
                        self.state_timer = 0.0
                    else:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.state_timer += dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()

    def _update_playing(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Jump handling (Key B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.jumps_left > 0 and self.jump_timer <= 0.0:
                self.jump_timer = 0.6
                self.jumps_left -= 1

        if self.jump_timer > 0.0:
            self.jump_timer -= dt
            if self.jump_timer < 0.0:
                self.jump_timer = 0.0

        # Player Movement along grid
        move_speed = 6.0
        if buttons & KEY_A:
            move_speed = 8.5  # Dash

        # Find closest intersection / line alignment
        on_col_idx = -1
        for idx, col in enumerate(GRID_COLS):
            if abs(self.px - col) < 0.2:
                on_col_idx = idx
                break

        on_row_idx = -1
        for idx, row in enumerate(GRID_ROWS):
            if abs(self.py - row) < 0.2:
                on_row_idx = idx
                break

        dx = 0.0
        dy = 0.0
        if (buttons & KEY_LEFT) and on_row_idx != -1:
            dx = -move_speed * dt
            self.py = float(GRID_ROWS[on_row_idx])
        elif (buttons & KEY_RIGHT) and on_row_idx != -1:
            dx = move_speed * dt
            self.py = float(GRID_ROWS[on_row_idx])
        elif (buttons & KEY_UP) and on_col_idx != -1:
            dy = -move_speed * dt
            self.px = float(GRID_COLS[on_col_idx])
        elif (buttons & KEY_DOWN) and on_col_idx != -1:
            dy = move_speed * dt
            self.px = float(GRID_COLS[on_col_idx])

        new_x = max(2.0, min(14.0, self.px + dx))
        new_y = max(2.0, min(14.0, self.py + dy))

        if self._is_on_grid(new_x, new_y):
            self.px = new_x
            self.py = new_y

            ix = int(round(self.px))
            iy = int(round(self.py))
            if not self.traced[iy][ix]:
                self.traced[iy][ix] = True
                self.score += 5
                self._check_boxes()

        # Update Enemies (Patrol along grid lines)
        for e in self.enemies:
            if self.jump_timer > 0.0:
                # Enemies pause/freeze while jumping
                continue

            ex = e["x"] + e["dir"][0] * e["speed"] * dt
            ey = e["y"] + e["dir"][1] * e["speed"] * dt

            # Reverse or turn at grid corners / intersections
            if ex <= 2.0 or ex >= 14.0 or ey <= 2.0 or ey >= 14.0:
                ex = max(2.0, min(14.0, ex))
                ey = max(2.0, min(14.0, ey))
                # Cycle direction 90 degrees
                e["dir"] = (-e["dir"][1], e["dir"][0])

            e["x"] = ex
            e["y"] = ey

            # Collision with player
            if abs(self.px - e["x"]) < 0.8 and abs(self.py - e["y"]) < 0.8:
                if self.jump_timer <= 0.0:
                    self.lives -= 1
                    self.state = STATE_CAUGHT
                    self.state_timer = 0.0
                    return

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(16 * 16 * 3):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Render Filled Boxes
        for by in range(3):
            for bx in range(3):
                if self.boxes[by][bx]:
                    x1 = GRID_COLS[bx] + 1
                    x2 = GRID_COLS[bx + 1] - 1
                    y1 = GRID_ROWS[by] + 1
                    y2 = GRID_ROWS[by + 1] - 1
                    for y in range(y1, y2 + 1):
                        for x in range(x1, x2 + 1):
                            set_pixel(x, y, 40, 160, 80)

        # 2. Render Grid Lines (Untraced: Dark Blue, Traced: Bright Yellow)
        for col in GRID_COLS:
            for y in range(2, 15):
                if self.traced[y][col]:
                    set_pixel(col, y, 255, 230, 50)
                else:
                    set_pixel(col, y, 30, 40, 90)

        for row in GRID_ROWS:
            for x in range(2, 15):
                if self.traced[row][x]:
                    set_pixel(x, row, 255, 230, 50)
                else:
                    set_pixel(x, row, 30, 40, 90)

        # 3. Render Enemies (Pink/Red Amidar patrol monsters)
        for e in self.enemies:
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            set_pixel(ex, ey, 255, 50, 60)

        # 4. Render Player
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.jump_timer > 0.0:
                # White-cyan jump flash
                set_pixel(px, py, 255, 255, 255)
            else:
                # Bright Cyan Painter
                set_pixel(px, py, 50, 220, 255)
        elif self.state == STATE_CAUGHT:
            set_pixel(px, py, 255, 40, 40)

        # 5. Jump indicator dots at bottom (Row 15)
        for j in range(min(self.jumps_left, 3)):
            set_pixel(2 + j * 2, 15, 255, 255, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "px": self.px,
            "py": self.py,
            "jumps_left": self.jumps_left,
            "is_jumping": self.jump_timer > 0.0,
            "boxes_cleared": sum(sum(1 for b in row if b) for row in self.boxes),
        }
