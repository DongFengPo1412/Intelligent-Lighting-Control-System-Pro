# -*- coding: utf-8 -*-
"""
Game #131: 太阳能战机 (Solar Fox 1981 / Bally Midway)
街机历史上最具速度感的矩阵能量网格扫掠与外围哨兵狙击对决：
矩阵太阳能晶胞高速巡航收割、外围四方巡逻哨兵向心齐射火球、双速巡航超频冲刺与能量护盾。
"""

from typing import List, Dict, Any, Optional
import math
import random
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

STATE_FLYING = 0
STATE_SHIP_EXPLODING = 1
STATE_QUADRANT_CLEAR = 2
STATE_GAME_OVER = 3

ARENA_MIN = 1.5
ARENA_MAX = 13.5
MATRIX_W = 10
MATRIX_H = 10
MAX_FIREBALLS = 4
NUM_SENTINELS = 4


class Game131SolarFox(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.quadrant = 1
        self.remaining_cells = 0

        self.px = 7.5
        self.py = 12.0
        self.dir_x = 0
        self.dir_y = -1
        self.next_dir_x = 0
        self.next_dir_y = -1
        self.is_hyperspeed = False
        self.shield_timer = 0.0
        self.shield_cooldown = 0.0

        self.cells = [[False] * MATRIX_W for _ in range(MATRIX_H)]
        self.sentinels: List[Dict[str, Any]] = []
        self.fireballs: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 131

    @property
    def name(self) -> str:
        return "太阳能战机"

    @property
    def english_name(self) -> str:
        return "Solar Fox"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "矩阵太阳能晶胞高速巡航收割、外围四向哨兵狙击火球与双速超频冲刺"

    def get_name(self) -> str:
        return "Solar Fox (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.quadrant = 1
        self._init_quadrant()

    def _init_quadrant(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0

        self.px = 7.5
        self.py = 12.0
        self.dir_x = 0
        self.dir_y = -1
        self.next_dir_x = 0
        self.next_dir_y = -1
        self.is_hyperspeed = False
        self.shield_timer = 0.0
        self.shield_cooldown = 0.0

        self.remaining_cells = 0
        self.cells = [[False] * MATRIX_W for _ in range(MATRIX_H)]
        for y in range(MATRIX_H):
            for x in range(MATRIX_W):
                if 1 <= x <= 8 and 1 <= y <= 8:
                    active = ((x + y) % 2 == 0) if (self.quadrant % 2 == 1) else True
                    self.cells[y][x] = active
                    if active:
                        self.remaining_cells += 1

        base_spd = 3.5 + self.quadrant * 0.4
        self.sentinels = [
            {"pos": 4.0, "speed": base_spd, "cooldown": 1.0},
            {"pos": 11.0, "speed": -base_spd, "cooldown": 1.8},
            {"pos": 5.0, "speed": base_spd * 0.9, "cooldown": 2.5},
            {"pos": 10.0, "speed": -base_spd * 0.9, "cooldown": 3.2},
        ]

        self.fireballs = []
        for _ in range(MAX_FIREBALLS):
            self.fireballs.append({
                "x": 0.0,
                "y": 0.0,
                "vx": 0.0,
                "vy": 0.0,
                "active": False,
            })

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_SHIP_EXPLODING:
            if self.state_timer > 1.3:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_FLYING
                    self.px = 7.5
                    self.py = 12.0
                    self.dir_x = 0
                    self.dir_y = -1
                    self.next_dir_x = 0
                    self.next_dir_y = -1
                    self.shield_timer = 0.0
            return

        if self.state == STATE_QUADRANT_CLEAR:
            if self.state_timer > 1.6:
                self.quadrant += 1
                self.score += 1500
                self._init_quadrant()
            return

        self.is_hyperspeed = (buttons & KEY_A) != 0

        if self.shield_cooldown > 0.0:
            self.shield_cooldown -= dt
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.shield_cooldown <= 0.0:
                self.shield_timer = 0.8
                self.shield_cooldown = 3.0
        if self.shield_timer > 0.0:
            self.shield_timer -= dt

        self._update_ship(dt, buttons)
        self._update_sentinels(dt)
        self._update_fireballs(dt)
        self._check_collisions()

        if self.remaining_cells == 0:
            self.state = STATE_QUADRANT_CLEAR
            self.state_timer = 0.0

    def _update_ship(self, dt: float, buttons: int) -> None:
        if buttons & KEY_UP:
            self.next_dir_x = 0
            self.next_dir_y = -1
        elif buttons & KEY_DOWN:
            self.next_dir_x = 0
            self.next_dir_y = 1
        elif buttons & KEY_LEFT:
            self.next_dir_x = -1
            self.next_dir_y = 0
        elif buttons & KEY_RIGHT:
            self.next_dir_x = 1
            self.next_dir_y = 0

        if self.next_dir_x != 0 or self.next_dir_y != 0:
            self.dir_x = self.next_dir_x
            self.dir_y = self.next_dir_y

        speed = 11.5 if self.is_hyperspeed else 6.0
        self.px += self.dir_x * speed * dt
        self.py += self.dir_y * speed * dt

        if self.px <= ARENA_MIN:
            self.px = ARENA_MIN
            self.dir_x = 1
        elif self.px >= ARENA_MAX:
            self.px = ARENA_MAX
            self.dir_x = -1

        if self.py <= ARENA_MIN:
            self.py = ARENA_MIN
            self.dir_y = 1
        elif self.py >= ARENA_MAX:
            self.py = ARENA_MAX
            self.dir_y = -1

    def _update_sentinels(self, dt: float) -> None:
        for i, s in enumerate(self.sentinels):
            s["pos"] += s["speed"] * dt
            if s["pos"] < 2.0:
                s["pos"] = 2.0
                s["speed"] = -s["speed"]
            elif s["pos"] > 13.0:
                s["pos"] = 13.0
                s["speed"] = -s["speed"]

            s["cooldown"] -= dt
            if s["cooldown"] <= 0.0:
                s["cooldown"] = max(1.0, 2.8 - self.quadrant * 0.15)
                for fb in self.fireballs:
                    if not fb["active"]:
                        fb["active"] = True
                        if i == 0:
                            sx, sy = s["pos"], 1.0
                        elif i == 1:
                            sx, sy = s["pos"], 14.0
                        elif i == 2:
                            sx, sy = 1.0, s["pos"]
                        else:
                            sx, sy = 14.0, s["pos"]

                        fb["x"] = sx
                        fb["y"] = sy

                        dx = self.px - sx
                        dy = self.py - sy
                        dist = math.sqrt(dx * dx + dy * dy)
                        fb_spd = 6.5 + self.quadrant * 0.3
                        if dist > 0.1:
                            fb["vx"] = (dx / dist) * fb_spd
                            fb["vy"] = (dy / dist) * fb_spd
                        break

    def _update_fireballs(self, dt: float) -> None:
        for fb in self.fireballs:
            if not fb["active"]:
                continue
            fb["x"] += fb["vx"] * dt
            fb["y"] += fb["vy"] * dt

            if fb["x"] < 0.5 or fb["x"] > 15.0 or fb["y"] < 0.5 or fb["y"] > 15.0:
                fb["active"] = False

    def _check_collisions(self) -> None:
        # 1. Harvest cells
        cx = int(round(self.px)) - 3
        cy = int(round(self.py)) - 3
        if 0 <= cx < MATRIX_W and 0 <= cy < MATRIX_H:
            if self.cells[cy][cx]:
                self.cells[cy][cx] = False
                self.remaining_cells -= 1
                self.score += 40 if self.is_hyperspeed else 20

        # 2. Fireballs vs Ship
        for fb in self.fireballs:
            if not fb["active"]:
                continue
            dx = abs(self.px - fb["x"])
            dy = abs(self.py - fb["y"])
            if dx < 0.8 and dy < 0.8:
                fb["active"] = False
                if self.shield_timer > 0.0:
                    self.score += 50
                else:
                    self.state = STATE_SHIP_EXPLODING
                    self.state_timer = 0.0
                    break

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        elif len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Perimeter border
        for p in range(1, 15):
            set_pixel(p, 1, 30, 40, 60)
            set_pixel(p, 14, 30, 40, 60)
            set_pixel(1, p, 30, 40, 60)
            set_pixel(14, p, 30, 40, 60)

        # 2. Energy cells
        for y in range(MATRIX_H):
            for x in range(MATRIX_W):
                if self.cells[y][x]:
                    set_pixel(x + 3, y + 3, 255, 220, 40)

        # 3. Sentinels
        if len(self.sentinels) >= 4:
            set_pixel(int(round(self.sentinels[0]["pos"])), 1, 255, 60, 40)
            set_pixel(int(round(self.sentinels[1]["pos"])), 14, 255, 60, 40)
            set_pixel(1, int(round(self.sentinels[2]["pos"])), 255, 60, 40)
            set_pixel(14, int(round(self.sentinels[3]["pos"])), 255, 60, 40)

        # 4. Fireballs
        for f in self.fireballs:
            if f["active"]:
                set_pixel(int(round(f["x"])), int(round(f["y"])), 255, 140, 0)

        # 5. Ship
        px_s = int(round(self.px))
        py_s = int(round(self.py))
        if self.state in (STATE_FLYING, STATE_QUADRANT_CLEAR):
            if self.shield_timer > 0.0:
                set_pixel(px_s, py_s, 255, 255, 255)
                set_pixel(px_s - self.dir_x, py_s - self.dir_y, 0, 255, 200)
            elif self.is_hyperspeed:
                set_pixel(px_s, py_s, 255, 255, 255)
                set_pixel(px_s - self.dir_x, py_s - self.dir_y, 255, 120, 0)
            else:
                set_pixel(px_s, py_s, 0, 220, 255)
                set_pixel(px_s - self.dir_x, py_s - self.dir_y, 0, 120, 180)
        elif self.state == STATE_SHIP_EXPLODING:
            set_pixel(px_s, py_s, 255, 220, 40)
            set_pixel(px_s - 1, py_s, 255, 50, 20)
            set_pixel(px_s + 1, py_s, 255, 50, 20)
            set_pixel(px_s, py_s - 1, 255, 50, 20)
            set_pixel(px_s, py_s + 1, 255, 50, 20)

        # 6. Lives
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 0, 220, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "quadrant": self.quadrant,
            "remaining_cells": self.remaining_cells,
            "is_hyperspeed": self.is_hyperspeed,
            "shield_active": self.shield_timer > 0.0,
            "px": self.px,
            "py": self.py,
        }
