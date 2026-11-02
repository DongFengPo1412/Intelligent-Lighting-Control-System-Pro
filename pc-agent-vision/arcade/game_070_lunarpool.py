"""
Game #070: 经典台球 / 斯诺克大师 (Lunar Pool 1985 / FCI / Compile)
Variable Friction Cue Ball Physics, Geometric Lunar Table, Elastic Collisions & Combo Multipliers.
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
STATE_BALLS_MOVING = 2
STATE_DEAD = 3
STATE_VICTORY = 4

MAX_BALLS = 5
MAX_POCKETS = 4


class Game070LunarPool(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 8000
        self.lives = 3

        self.aim_angle = 0.0
        self.shot_power = 0.0
        self.is_charging_power = False
        self.combo_multiplier = 1
        self.friction = 1.4

        self.balls: List[Dict[str, Any]] = []
        self.pockets: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 70

    @property
    def name(self) -> str:
        return "经典台球"

    @property
    def english_name(self) -> str:
        return "Lunar Pool"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "异形月球球台 + 杆度蓄力母球撞击与弹性动量守恒 + 连续落袋连击翻倍"

    def get_name(self) -> str:
        return "Lunar Pool (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_table()

    def init_table(self):
        self.aim_angle = 0.0
        self.shot_power = 0.0
        self.is_charging_power = False
        self.combo_multiplier = 1
        self.friction = 1.4

        self.pockets = [
            {"x": 1.5, "y": 1.5, "radius": 1.3},
            {"x": 14.5, "y": 1.5, "radius": 1.3},
            {"x": 1.5, "y": 14.5, "radius": 1.3},
            {"x": 14.5, "y": 14.5, "radius": 1.3},
        ]

        self.balls = [
            {"x": 4.0, "y": 8.0, "vx": 0.0, "vy": 0.0, "is_cue": True, "number": 0, "in_pocket": False},
            {"x": 10.0, "y": 8.0, "vx": 0.0, "vy": 0.0, "is_cue": False, "number": 1, "in_pocket": False},
            {"x": 11.5, "y": 7.0, "vx": 0.0, "vy": 0.0, "is_cue": False, "number": 2, "in_pocket": False},
            {"x": 11.5, "y": 9.0, "vx": 0.0, "vy": 0.0, "is_cue": False, "number": 3, "in_pocket": False},
            {"x": 13.0, "y": 8.0, "vx": 0.0, "vy": 0.0, "is_cue": False, "number": 4, "in_pocket": False},
        ]

    def get_balls_remaining(self) -> int:
        return len([b for b in self.balls[1:] if not b["in_pocket"]])

    def shoot_cue_ball(self, power: float):
        if self.balls[0]["in_pocket"]:
            return

        self.balls[0]["vx"] = math.cos(self.aim_angle) * power
        self.balls[0]["vy"] = math.sin(self.aim_angle) * power
        self.state = STATE_BALLS_MOVING
        self.shot_power = 0.0
        self.is_charging_power = False

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.balls[0]["x"] = 4.0
                    self.balls[0]["y"] = 8.0
                    self.balls[0]["vx"] = 0.0
                    self.balls[0]["vy"] = 0.0
                    self.balls[0]["in_pocket"] = False
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_table()
            return

        if self.state == STATE_PLAYING:
            self.update_aiming(dt, buttons, prev_buttons)
        elif self.state == STATE_BALLS_MOVING:
            self.update_physics(dt)
            self.check_ball_collisions()
            self.check_pocket_collisions()

            moving = False
            for b in self.balls:
                if not b["in_pocket"] and (abs(b["vx"]) > 0.1 or abs(b["vy"]) > 0.1):
                    moving = True
                    break

            if not moving:
                self.state = STATE_PLAYING
                self.combo_multiplier = 1

    def update_aiming(self, dt: float, buttons: int, prev_buttons: int):
        rot_speed = 3.0
        if buttons & KEY_LEFT:
            self.aim_angle -= rot_speed * dt
        if buttons & KEY_RIGHT:
            self.aim_angle += rot_speed * dt

        while self.aim_angle > math.pi:
            self.aim_angle -= 2 * math.pi
        while self.aim_angle < -math.pi:
            self.aim_angle += 2 * math.pi

        if buttons & KEY_A:
            self.is_charging_power = True
            self.shot_power = min(18.0, self.shot_power + 14.0 * dt)
        elif self.is_charging_power:
            self.shoot_cue_ball(max(3.0, self.shot_power))

    def update_physics(self, dt: float):
        for b in self.balls:
            if b["in_pocket"]:
                continue

            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            decel = self.friction * dt
            speed = math.sqrt(b["vx"] * b["vx"] + b["vy"] * b["vy"])
            if speed > 0.05:
                new_speed = max(0.0, speed - speed * decel)
                b["vx"] = (b["vx"] / speed) * new_speed
                b["vy"] = (b["vy"] / speed) * new_speed
            else:
                b["vx"] = 0.0
                b["vy"] = 0.0

            # Cushions
            if b["x"] <= 1.8:
                b["x"] = 1.8
                b["vx"] = -b["vx"] * 0.85
            elif b["x"] >= 14.2:
                b["x"] = 14.2
                b["vx"] = -b["vx"] * 0.85

            if b["y"] <= 1.8:
                b["y"] = 1.8
                b["vy"] = -b["vy"] * 0.85
            elif b["y"] >= 14.2:
                b["y"] = 14.2
                b["vy"] = -b["vy"] * 0.85

    def check_ball_collisions(self):
        for i in range(MAX_BALLS):
            if self.balls[i]["in_pocket"]:
                continue
            for j in range(i + 1, MAX_BALLS):
                if self.balls[j]["in_pocket"]:
                    continue

                dx = self.balls[j]["x"] - self.balls[i]["x"]
                dy = self.balls[j]["y"] - self.balls[i]["y"]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < 1.1 and dist > 0.001:
                    overlap = 0.5 * (1.1 - dist)
                    nx = dx / dist
                    ny = dy / dist

                    self.balls[i]["x"] -= nx * overlap
                    self.balls[i]["y"] -= ny * overlap
                    self.balls[j]["x"] += nx * overlap
                    self.balls[j]["y"] += ny * overlap

                    kx = self.balls[i]["vx"] - self.balls[j]["vx"]
                    ky = self.balls[i]["vy"] - self.balls[j]["vy"]
                    p = (nx * kx + ny * ky)

                    self.balls[i]["vx"] -= p * nx * 0.95
                    self.balls[i]["vy"] -= p * ny * 0.95
                    self.balls[j]["vx"] += p * nx * 0.95
                    self.balls[j]["vy"] += p * ny * 0.95

    def check_pocket_collisions(self):
        for b in self.balls:
            if b["in_pocket"]:
                continue
            for p in self.pockets:
                dx = b["x"] - p["x"]
                dy = b["y"] - p["y"]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < p["radius"]:
                    b["in_pocket"] = True
                    b["vx"] = 0.0
                    b["vy"] = 0.0

                    if b["is_cue"]:
                        self.lives -= 1
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return
                    else:
                        self.score += 250 * self.combo_multiplier
                        self.combo_multiplier *= 2

                        if self.get_balls_remaining() == 0:
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                            self.score += 3000
                            if self.score > self.high_score:
                                self.high_score = self.score
                            return
                    break

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Table cushions and felt
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    set_pixel(x, y, 90, 50, 20)
                else:
                    set_pixel(x, y, 35, 20, 65)

        # 2. Corner pockets
        set_pixel(1, 1, 0, 0, 0); set_pixel(2, 1, 0, 0, 0); set_pixel(1, 2, 0, 0, 0)
        set_pixel(14, 1, 0, 0, 0); set_pixel(13, 1, 0, 0, 0); set_pixel(14, 2, 0, 0, 0)
        set_pixel(1, 14, 0, 0, 0); set_pixel(2, 14, 0, 0, 0); set_pixel(1, 13, 0, 0, 0)
        set_pixel(14, 14, 0, 0, 0); set_pixel(13, 14, 0, 0, 0); set_pixel(14, 13, 0, 0, 0)

        # 3. Aiming line
        if self.state == STATE_PLAYING and not self.balls[0]["in_pocket"]:
            for step in range(1, 5):
                ax = int(round(self.balls[0]["x"] + math.cos(self.aim_angle) * step))
                ay = int(round(self.balls[0]["y"] + math.sin(self.aim_angle) * step))
                set_pixel(ax, ay, 200, 200, 200)

        # 4. Balls
        for b in self.balls:
            if b["in_pocket"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))

            if b["is_cue"]:
                set_pixel(bx, by, 255, 255, 255)
            elif b["number"] == 1:
                set_pixel(bx, by, 255, 220, 30)
            elif b["number"] == 2:
                set_pixel(bx, by, 40, 100, 255)
            elif b["number"] == 3:
                set_pixel(bx, by, 255, 40, 40)
            else:
                set_pixel(bx, by, 40, 220, 50)

        # 5. Power Meter
        if self.is_charging_power:
            power_bars = int((self.shot_power / 18.0) * 10.0)
            for p in range(power_bars):
                set_pixel(3 + p, 0, 255, 120, 0)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "aim_angle": self.aim_angle,
            "shot_power": self.shot_power,
            "balls_remaining": self.get_balls_remaining(),
            "combo_multiplier": self.combo_multiplier,
        }
