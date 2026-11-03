"""
Game #121: 太空出租车 (Space Taxi 1984 / Muse Software)
Precision anti-gravity sky cab piloting, landing gear extension/retraction,
voice-call passenger boarding, and multi-tier destination pad ferrying.
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
STATE_BOARDING = 1
STATE_FARE_PAID = 2
STATE_CRASHED = 3
STATE_GAME_OVER = 4

NUM_PADS = 4


class Game121SpaceTaxi(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.fuel = 100.0
        self.fares_completed = 0

        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.gear_deployed = True
        self.thrust_up = False
        self.thrust_left = False
        self.thrust_right = False

        self.pads: List[Dict[str, int]] = []
        self.passenger: Dict[str, Any] = {
            "current_pad": 1, "target_pad": 2, "in_taxi": False, "delivered": False
        }

        self.reset()

    @property
    def game_id(self) -> int:
        return 121

    @property
    def name(self) -> str:
        return "太空出租车"

    @property
    def english_name(self) -> str:
        return "Space Taxi"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "城市反重力穿梭对接、起落架收放控制、乘客呼叫登机与跨平台接送"

    def get_name(self) -> str:
        return "Space Taxi (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.fares_completed = 0
        self._init_pads()
        self._init_level()

    def _init_pads(self) -> None:
        self.pads = [
            {"id": 1, "x_start": 1, "x_end": 3, "y": 14},   # Pad 1 (Bottom Left)
            {"id": 2, "x_start": 12, "x_end": 14, "y": 14}, # Pad 2 (Bottom Right)
            {"id": 3, "x_start": 1, "x_end": 3, "y": 6},    # Pad 3 (Top Left)
            {"id": 4, "x_start": 12, "x_end": 14, "y": 6},  # Pad 4 (Top Right)
        ]

    def _init_level(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.fuel = 100.0

        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.gear_deployed = True
        self.thrust_up = False
        self.thrust_left = False
        self.thrust_right = False

        self._spawn_passenger()

    def _spawn_passenger(self) -> None:
        start_p = (self.fares_completed % NUM_PADS) + 1
        end_p = ((start_p + 1) % NUM_PADS) + 1
        if end_p == start_p:
            end_p = (start_p % NUM_PADS) + 1

        self.passenger = {
            "current_pad": start_p,
            "target_pad": end_p,
            "in_taxi": False,
            "delivered": False,
        }

    def toggle_gear(self) -> None:
        self.gear_deployed = not self.gear_deployed

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

        if self.state == STATE_BOARDING:
            if self.state_timer > 1.2:
                self.state = STATE_FLYING
                self.passenger["in_taxi"] = True
            return

        if self.state == STATE_FARE_PAID:
            if self.state_timer > 1.5:
                self._init_level()
            return

        if self.state == STATE_CRASHED:
            if self.state_timer > 1.4:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self._init_level()
            return

        self._update_physics(dt, buttons, prev_buttons)
        self._check_pad_landing()

    def _update_physics(self, dt: float, buttons: int, prev_buttons: int) -> None:
        city_gravity = 1.8
        self.vy += city_gravity * dt

        self.thrust_up = False
        self.thrust_left = False
        self.thrust_right = False

        if (buttons & KEY_UP) and self.fuel > 0.0:
            self.thrust_up = True
            self.vy -= 4.2 * dt
            self.fuel -= 6.0 * dt

        if (buttons & KEY_A) and self.fuel > 0.0:
            self.thrust_up = True
            self.vy -= 6.5 * dt
            self.fuel -= 12.0 * dt

        if (buttons & KEY_LEFT) and self.fuel > 0.0:
            self.thrust_left = True
            self.vx -= 3.2 * dt
            self.fuel -= 4.0 * dt
        if (buttons & KEY_RIGHT) and self.fuel > 0.0:
            self.thrust_right = True
            self.vx += 3.2 * dt
            self.fuel -= 4.0 * dt

        if (buttons & (KEY_B | KEY_DOWN)) and not (prev_buttons & (KEY_B | KEY_DOWN)):
            self.toggle_gear()

        self.vx *= (1.0 - 0.4 * dt)

        self.px += self.vx * dt
        self.py += self.vy * dt

        if self.px < 1.0:
            self.px = 1.0
            self.vx = 0.0
        if self.px > 14.5:
            self.px = 14.5
            self.vx = 0.0
        if self.py < 1.0:
            self.py = 1.0
            self.vy = 0.0

        # Central Skyscraper core collision: x in 6..9, y in 4..11
        if 5.5 <= self.px <= 9.5 and 4.0 <= self.py <= 11.5:
            self.state = STATE_CRASHED
            self.state_timer = 0.0

    def _check_pad_landing(self) -> None:
        col = int(round(self.px))

        for pad in self.pads:
            if pad["x_start"] <= col <= pad["x_end"]:
                pad_y = float(pad["y"])
                if (pad_y - 1.2) <= self.py <= (pad_y + 0.2) and self.vy >= 0.0:
                    self.py = pad_y - 1.0

                    if not self.gear_deployed or abs(self.vy) > 1.4 or abs(self.vx) > 0.9:
                        self.state = STATE_CRASHED
                        self.state_timer = 0.0
                    else:
                        self.vx = 0.0
                        self.vy = 0.0

                        if not self.passenger["in_taxi"] and pad["id"] == self.passenger["current_pad"]:
                            self.state = STATE_BOARDING
                            self.state_timer = 0.0
                            self.score += 50
                        elif self.passenger["in_taxi"] and pad["id"] == self.passenger["target_pad"]:
                            self.state = STATE_FARE_PAID
                            self.state_timer = 0.0
                            self.fares_completed += 1
                            self.score += 250 + int(self.fuel) * 2
                    break

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Central Core
        for y in range(4, 12):
            for x in range(6, 10):
                set_pixel(x, y, 60, 60, 75)
                if (x + y) % 2 == 0:
                    set_pixel(x, y, 100, 120, 140)

        # 2. Pads
        for pad in self.pads:
            for x in range(pad["x_start"], pad["x_end"] + 1):
                set_pixel(x, pad["y"], 40, 220, 80)
                set_pixel(x, pad["y"] + 1, 30, 100, 40)

        # 3. Passenger
        if not self.passenger["in_taxi"] and self.state != STATE_FARE_PAID:
            pad_idx = self.passenger["current_pad"] - 1
            px = self.pads[pad_idx]["x_start"] + 1
            py = self.pads[pad_idx]["y"] - 1
            set_pixel(px, py, 255, 60, 200)
            set_pixel(px, py - 1, 255, 200, 140)

        # 4. Taxi
        tx = int(round(self.px))
        ty = int(round(self.py))

        if self.state in (STATE_FLYING, STATE_BOARDING, STATE_FARE_PAID):
            set_pixel(tx, ty, 255, 220, 0)
            set_pixel(tx - 1, ty, 255, 200, 0)
            set_pixel(tx + 1, ty, 255, 200, 0)
            set_pixel(tx, ty - 1, 40, 40, 40)

            if self.gear_deployed:
                set_pixel(tx - 1, ty + 1, 220, 220, 240)
                set_pixel(tx + 1, ty + 1, 220, 220, 240)

            if self.thrust_up:
                set_pixel(tx, ty + 1, 0, 220, 255)
            if self.thrust_left:
                set_pixel(tx + 2, ty, 255, 120, 20)
            if self.thrust_right:
                set_pixel(tx - 2, ty, 255, 120, 20)
        elif self.state == STATE_CRASHED:
            set_pixel(tx, ty, 255, 40, 20)
            set_pixel(tx - 1, ty - 1, 255, 180, 0)
            set_pixel(tx + 1, ty + 1, 255, 220, 50)
            set_pixel(tx + 1, ty - 1, 255, 60, 20)

        # 5. HUD
        if self.gear_deployed:
            set_pixel(0, 0, 40, 255, 80)
        else:
            set_pixel(0, 0, 255, 40, 20)

        f_bars = int((self.fuel / 100.0) * 6.0)
        for f in range(f_bars):
            set_pixel(2 + f, 0, 0, 200, 255)

        target = self.passenger["target_pad"] if self.passenger["in_taxi"] else self.passenger["current_pad"]
        set_pixel(10 + target, 0, 255, 220, 0)

        for l in range(min(self.lives, 3)):
            set_pixel(15, l, 255, 255, 255)

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
            "gear_deployed": self.gear_deployed,
            "passenger_in_taxi": self.passenger["in_taxi"],
            "current_pad": self.passenger["current_pad"],
            "target_pad": self.passenger["target_pad"],
        }

