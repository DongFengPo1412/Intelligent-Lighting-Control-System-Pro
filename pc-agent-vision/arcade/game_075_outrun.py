"""
Game #075: 欧陆赛车 / 经典公路狂飙 (Out Run 1986 / Sega / Yu Suzuki)
Branching Fork Route Tree, Ferrari Testarossa Drift & Cassette Radio Selector, Checkpoint Time Extension.
"""

import math
from typing import List, Dict, Any
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

STATE_START = 0
STATE_PLAYING = 1
STATE_CRASH = 2
STATE_VICTORY = 3

MAX_CARS = 3
MAX_SCENERY = 4


class Game075OutRun(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 10000

        # Ferrari state
        self.car_x = 0.0
        self.car_speed = 40.0
        self.high_gear = False
        self.radio_station = 0

        self.road_curve = 0.0
        self.stage_distance = 0.0
        self.stage_length = 1500.0
        self.current_stage = 1
        self.time_remaining = 45.0
        self.is_at_fork = False

        self.traffic: List[Dict[str, Any]] = []
        self.scenery: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 75

    @property
    def name(self) -> str:
        return "欧陆赛车"

    @property
    def english_name(self) -> str:
        return "Out Run"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "分叉公路分支路线选择 + 法拉利漂移过弯与车载金曲电台切换 + 检查点计时冲线"

    def get_name(self) -> str:
        return "Out Run (1986)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.current_stage = 1
        self.time_remaining = 45.0
        self.init_stage()

    def init_stage(self):
        self.car_x = 0.0
        self.car_speed = 40.0
        self.high_gear = False
        self.road_curve = 0.0
        self.stage_distance = 0.0
        self.is_at_fork = False

        self.traffic = [
            {"x": -0.4, "distance": 40.0, "speed": 75.0, "color_type": 0, "active": True},
            {"x": 0.3, "distance": 80.0, "speed": 90.0, "color_type": 1, "active": True},
            {"x": -0.2, "distance": 130.0, "speed": 80.0, "color_type": 0, "active": True},
        ]

        self.scenery = [
            {"x": -1.3, "distance": 20.0, "type": 0, "active": True},
            {"x": 1.3, "distance": 50.0, "type": 0, "active": True},
            {"x": -1.3, "distance": 80.0, "type": 0, "active": True},
            {"x": 1.3, "distance": 110.0, "type": 1, "active": True},
        ]

    def cycle_radio(self):
        self.radio_station = (self.radio_station + 1) % 3

    def shift_gear(self):
        self.high_gear = not self.high_gear
        self.cycle_radio()

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_CRASH:
            if self.state_timer > 2.0:
                if self.time_remaining > 0.0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.car_speed = 30.0
                    self.car_x = 0.0
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 3.0:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.reset()
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            self.state = STATE_CRASH
            self.state_timer = 0.0
            return

        self.update_driving(dt, buttons, prev_buttons)
        self.update_road(dt)
        self.update_traffic(dt)
        self.check_collisions()

    def update_driving(self, dt: float, buttons: int, prev_buttons: int):
        steer_speed = 1.4
        if buttons & KEY_LEFT:
            self.car_x -= steer_speed * dt
        if buttons & KEY_RIGHT:
            self.car_x += steer_speed * dt

        self.car_x -= self.road_curve * (self.car_speed / 180.0) * 1.2 * dt

        top_speed = 180.0 if self.high_gear else 105.0
        accelerating = bool(buttons & KEY_A)

        if accelerating:
            self.car_speed = min(top_speed, self.car_speed + 50.0 * dt)
        else:
            self.car_speed = max(0.0, self.car_speed - 30.0 * dt)

        if abs(self.car_x) > 0.85:
            self.car_speed = max(0.0, self.car_speed - 70.0 * dt)

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.shift_gear()

        dist_step = (self.car_speed * 0.28) * dt
        self.stage_distance += dist_step
        self.score += int(dist_step * 2.0)
        if self.score > self.high_score:
            self.high_score = self.score

    def update_road(self, dt: float):
        self.road_curve = math.sin(self.stage_distance * 0.005) * 0.7

        if self.stage_distance >= 1350.0:
            self.is_at_fork = True

        if self.stage_distance >= self.stage_length:
            self.time_remaining += 25.0
            self.score += 1000
            self.current_stage += 1

            if self.current_stage > 3:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 5000
                if self.score > self.high_score:
                    self.high_score = self.score
            else:
                self.stage_distance = 0.0
                self.is_at_fork = False

    def update_traffic(self, dt: float):
        player_vel = self.car_speed * 0.28
        for i, car in enumerate(self.traffic):
            if not car["active"]:
                continue
            rel_speed = (car["speed"] * 0.28) - player_vel
            car["distance"] += rel_speed * dt

            if car["distance"] < -10.0:
                car["distance"] = 120.0 + (i * 30.0)
                car["x"] = -0.4 if (i % 2 == 0) else 0.4
            elif car["distance"] > 180.0:
                car["distance"] = 120.0

        for sc in self.scenery:
            if not sc["active"]:
                continue
            sc["distance"] -= player_vel * dt
            if sc["distance"] < 0.0:
                sc["distance"] = 120.0

    def check_collisions(self):
        for car in self.traffic:
            if not car["active"]:
                continue
            if abs(car["distance"]) < 2.0 and abs(self.car_x - car["x"]) < 0.35:
                self.state = STATE_CRASH
                self.state_timer = 0.0
                self.car_speed = 0.0
                self.time_remaining = max(0.0, self.time_remaining - 3.0)
                return

        if abs(self.car_x) > 1.25:
            self.state = STATE_CRASH
            self.state_timer = 0.0
            self.car_speed = 0.0
            self.time_remaining = max(0.0, self.time_remaining - 3.0)
            return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Sky & Horizon
        for y in range(8):
            for x in range(16):
                if y <= 3:
                    set_pixel(x, y, 40, 100, 220)
                else:
                    set_pixel(x, y, 240, 140, 60)

        # 2. Road
        for y in range(8, 16):
            t = float(y - 8) / 7.0
            road_half_width = 1.5 + t * 5.5
            curve_offset = self.road_curve * (1.0 - t) * 4.0
            center_x = 7.5 + curve_offset

            for x in range(16):
                dist = abs(float(x) - center_x)
                if dist <= road_half_width:
                    stripe = (int(self.stage_distance * 0.15 + y) % 2 == 0)
                    if dist >= road_half_width - 0.8:
                        set_pixel(x, y, 255, 30 if stripe else 255, 30 if stripe else 255)
                    elif dist <= 0.6:
                        set_pixel(x, y, 240 if stripe else 80, 240 if stripe else 80, 240 if stripe else 90)
                    else:
                        set_pixel(x, y, 70, 75, 85)
                else:
                    grass_stripe = (int(self.stage_distance * 0.15 + y) % 2 == 0)
                    set_pixel(x, y, 40, 150 if grass_stripe else 130, 40)

        # 3. Fork Banner
        if self.is_at_fork:
            for x in range(3, 13):
                set_pixel(x, 7, 255, 215, 0)

        # 4. Scenery
        for sc in self.scenery:
            if not sc["active"]:
                continue
            t = max(0.0, min(1.0, 1.0 - (sc["distance"] / 120.0)))
            if t > 0.1:
                sy = 8 + int(t * 6.0)
                sx = int(round(7.5 + sc["x"] * (2.0 + t * 5.0)))
                set_pixel(sx, sy, 30, 160, 40)
                set_pixel(sx, sy - 1, 30, 180, 50)
                set_pixel(sx, sy + 1, 140, 90, 40)

        # 5. Traffic
        for car in self.traffic:
            if not car["active"] or car["distance"] <= 0.0:
                continue
            t = max(0.0, min(1.0, 1.0 - (car["distance"] / 120.0)))
            if t > 0.15:
                cy = 8 + int(t * 5.5)
                cx = int(round(7.5 + car["x"] * (2.0 + t * 5.0)))
                if car["color_type"] == 0:
                    set_pixel(cx, cy, 40, 100, 240)
                    set_pixel(cx + 1, cy, 40, 100, 240)
                else:
                    set_pixel(cx, cy, 255, 220, 20)
                    set_pixel(cx + 1, cy, 255, 220, 20)

        # 6. Ferrari Testarossa
        if self.state != STATE_CRASH:
            fx = int(round(7.5 + self.car_x * 5.0))
            fy = 14
            set_pixel(fx - 1, fy, 230, 20, 20)
            set_pixel(fx,     fy, 255, 30, 30)
            set_pixel(fx + 1, fy, 230, 20, 20)

            set_pixel(fx - 1, fy + 1, 20, 20, 20)
            set_pixel(fx + 1, fy + 1, 20, 20, 20)
            set_pixel(fx,     fy + 1, 255, 140, 0)

            set_pixel(fx - 1, fy - 1, 120, 60, 20)
            set_pixel(fx + 1, fy - 1, 255, 220, 50)
        else:
            fx = int(round(7.5 + self.car_x * 5.0))
            fy = 14
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    set_pixel(fx + dx, fy + dy, 255, 100, 20)

        # 7. HUD
        spd_bars = int((self.car_speed / 180.0) * 6.0)
        for b in range(spd_bars):
            set_pixel(b, 0, 40, 255, 60)

        if self.high_gear:
            set_pixel(7, 0, 255, 215, 0)

        rr = 255 if self.radio_station == 0 else 50
        rg = 255 if self.radio_station == 1 else 50
        rb = 255 if self.radio_station == 2 else 50
        set_pixel(15, 0, rr, rg, rb)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "car_x": self.car_x,
            "car_speed": self.car_speed,
            "high_gear": self.high_gear,
            "current_stage": self.current_stage,
            "time_remaining": self.time_remaining,
            "is_at_fork": self.is_at_fork,
            "radio_station": self.radio_station,
        }
