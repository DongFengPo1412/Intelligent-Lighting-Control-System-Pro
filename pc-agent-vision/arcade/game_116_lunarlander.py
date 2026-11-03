"""
Game #116: 月球着陆器 (Lunar Lander 1979 / Atari)
Realistic gravitational descent physics, main thruster & RCS vector feathering,
fuel economy management, and precision soft touchdown on multi-multiplier lunar crags.
"""

from typing import List, Dict, Any
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

STATE_FLYING = 0
STATE_TOUCHDOWN_SAFE = 1
STATE_CRASHED = 2
STATE_GAME_OVER = 3

SAFE_MAX_VY = 1.25
SAFE_MAX_VX = 0.85


class Game116LunarLander(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.fuel = 450.0

        self.px = 8.0
        self.py = 1.5
        self.vx = 0.0
        self.vy = 0.0
        self.thrusting = False

        self.terrain_y: List[int] = [0] * 16
        self.pads: List[Dict[str, int]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 116

    @property
    def name(self) -> str:
        return "月球着陆器"

    @property
    def english_name(self) -> str:
        return "Lunar Lander"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "月面重力下坠仿真、反冲推力微调、有限燃料配额与多倍率悬崖软着陆"

    def get_name(self) -> str:
        return "Lunar Lander (1979)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.fuel = 450.0
        self._build_terrain()
        self._init_site()

    def _build_terrain(self) -> None:
        self.terrain_y = [
            12,
            14, 14, 14,  # Pad 0 (1X)
            13, 11, 13,
            15, 15,      # Pad 1 (3X)
            14, 12, 11, 11,
            12,          # Pad 2 (5X)
            13, 14
        ]
        self.pads = [
            {"x_start": 1, "x_end": 3, "y": 14, "multiplier": 1},
            {"x_start": 7, "x_end": 8, "y": 15, "multiplier": 3},
            {"x_start": 13, "x_end": 13, "y": 12, "multiplier": 5},
        ]

    def _init_site(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.px = 8.0
        self.py = 1.5
        self.vx = 0.0
        self.vy = 0.0
        self.thrusting = False

    def set_position_and_velocity(self, x: float, y: float, vx: float, vy: float) -> None:
        self.px = x
        self.py = y
        self.vx = vx
        self.vy = vy

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

        if self.state == STATE_TOUCHDOWN_SAFE:
            if self.state_timer > 1.6:
                self._init_site()
            return

        if self.state == STATE_CRASHED:
            if self.state_timer > 1.6:
                self.lives -= 1
                if self.lives <= 0 or self.fuel <= 0.0:
                    self.state = STATE_GAME_OVER
                else:
                    self._init_site()
            return

        self._update_physics(dt, buttons)
        self._check_touchdown()

    def _update_physics(self, dt: float, buttons: int) -> None:
        lunar_gravity = 1.6
        self.vy += lunar_gravity * dt
        self.thrusting = False

        if (buttons & (KEY_A | KEY_UP)) and self.fuel > 0.0:
            self.thrusting = True
            main_thrust = 4.0
            self.vy -= main_thrust * dt
            self.fuel -= 25.0 * dt

        if (buttons & KEY_LEFT) and self.fuel > 0.0:
            self.vx -= 2.4 * dt
            self.fuel -= 10.0 * dt
        if (buttons & KEY_RIGHT) and self.fuel > 0.0:
            self.vx += 2.4 * dt
            self.fuel -= 10.0 * dt

        if self.fuel < 0.0:
            self.fuel = 0.0

        self.px += self.vx * dt
        self.py += self.vy * dt

        if self.px < 1.0:
            self.px = 1.0
            self.vx = 0.0
        if self.px > 14.0:
            self.px = 14.0
            self.vx = 0.0
        if self.py < 1.0:
            self.py = 1.0
            self.vy = 0.0

    def _check_touchdown(self) -> None:
        col = int(round(self.px))
        col = max(0, min(15, col))
        surface_y = self.terrain_y[col]

        if self.py + 1.0 >= float(surface_y):
            self.py = float(surface_y) - 1.0

            matched_pad = -1
            for i, pad in enumerate(self.pads):
                if pad["x_start"] <= col <= pad["x_end"] and surface_y == pad["y"]:
                    matched_pad = i
                    break

            if matched_pad >= 0:
                if abs(self.vy) <= SAFE_MAX_VY and abs(self.vx) <= SAFE_MAX_VX:
                    self.state = STATE_TOUCHDOWN_SAFE
                    self.state_timer = 0.0
                    self.score += 100 * self.pads[matched_pad]["multiplier"]
                    self.fuel += 120.0
                else:
                    self.state = STATE_CRASHED
                    self.state_timer = 0.0
            else:
                self.state = STATE_CRASHED
                self.state_timer = 0.0

            self.vx = 0.0
            self.vy = 0.0

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Lunar Terrain
        for x in range(16):
            ty = self.terrain_y[x]
            set_pixel(x, ty, 80, 80, 95)
            for y in range(ty + 1, 16):
                set_pixel(x, y, 40, 40, 50)

        for pad in self.pads:
            for x in range(pad["x_start"], pad["x_end"] + 1):
                py = pad["y"]
                if pad["multiplier"] == 1:
                    set_pixel(x, py, 40, 220, 60)
                elif pad["multiplier"] == 3:
                    set_pixel(x, py, 40, 200, 255)
                else:
                    set_pixel(x, py, 255, 200, 30)

        # 2. Lunar Lander
        lx = int(round(self.px))
        ly = int(round(self.py))

        if self.state in (STATE_FLYING, STATE_TOUCHDOWN_SAFE):
            set_pixel(lx, ly, 255, 255, 255)
            set_pixel(lx - 1, ly + 1, 160, 180, 220)
            set_pixel(lx + 1, ly + 1, 160, 180, 220)

            if self.thrusting:
                set_pixel(lx, ly + 1, 255, 120, 20)
                set_pixel(lx, ly + 2, 255, 220, 40)

            if self.state == STATE_TOUCHDOWN_SAFE:
                set_pixel(lx, ly - 1, 40, 255, 80)
        elif self.state == STATE_CRASHED:
            set_pixel(lx, ly, 255, 60, 20)
            set_pixel(lx - 1, ly - 1, 255, 180, 0)
            set_pixel(lx + 1, ly + 1, 255, 220, 50)
            set_pixel(lx + 1, ly - 1, 255, 60, 20)

        # 3. Fuel HUD
        fuel_bars = int((self.fuel / 450.0) * 10.0)
        fuel_bars = max(0, min(10, fuel_bars))
        for f in range(fuel_bars):
            if fuel_bars > 5:
                set_pixel(f, 0, 40, 220, 80)
            elif fuel_bars > 2:
                set_pixel(f, 0, 255, 200, 30)
            else:
                set_pixel(f, 0, 255, 40, 20)

        for l in range(min(self.lives, 3)):
            set_pixel(15 - l, 0, 255, 255, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "fuel": self.fuel,
            "px": self.px,
            "py": self.py,
            "vx": self.vx,
            "vy": self.vy,
            "thrusting": self.thrusting,
        }

