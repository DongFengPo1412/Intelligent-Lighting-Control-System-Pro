"""
Game #045: 花式台球 (Side Pocket 1986 / Data East)
Precision Billiards Simulation with 2D Elastic Physics, Cushion Reflection, Power Stroke & 6-Pocket Detection.
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
STATE_AIMING = 1
STATE_CHARGING = 2
STATE_ROLLING = 3
STATE_SCRATCH = 4
STATE_VICTORY = 5

TOTAL_BALLS = 6


class Game045SidePocket(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.balls_potted = 0

        self.aim_angle = 0.0
        self.charge_power = 0.5
        self.charge_dir = 1.0

        self.balls: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 45

    @property
    def name(self) -> str:
        return "花式台球"

    @property
    def english_name(self) -> str:
        return "Side Pocket (1986)"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "纯正台球物理弹性碰撞 + 360度角度微调瞄准 + 冲杆蓄力与六袋落袋判定"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_AIMING
        self.state_timer = 0.0
        self.score = 0
        self.balls_potted = 0
        self.aim_angle = 0.0
        self.charge_power = 0.5
        self.charge_dir = 1.0

        self.init_table()

    def init_table(self):
        self.balls = [
            # Cue ball
            {"x": 4.0, "y": 7.5, "vx": 0.0, "vy": 0.0, "active": True, "is_cue": True, "color": (255, 255, 255)},
            # Object balls
            {"x": 9.5, "y": 7.5, "vx": 0.0, "vy": 0.0, "active": True, "is_cue": False, "color": (231, 76, 60)},
            {"x": 10.5, "y": 7.0, "vx": 0.0, "vy": 0.0, "active": True, "is_cue": False, "color": (241, 196, 15)},
            {"x": 10.5, "y": 8.0, "vx": 0.0, "vy": 0.0, "active": True, "is_cue": False, "color": (52, 152, 219)},
            {"x": 11.5, "y": 6.5, "vx": 0.0, "vy": 0.0, "active": True, "is_cue": False, "color": (230, 126, 34)},
            {"x": 11.5, "y": 8.5, "vx": 0.0, "vy": 0.0, "active": True, "is_cue": False, "color": (155, 89, 182)},
        ]

    def get_remaining_balls(self) -> int:
        return sum(1 for i in range(1, len(self.balls)) if self.balls[i]["active"])

    def strike_cue_ball(self, angle_rad: float, power: float):
        impulse = 6.0 + power * 14.0
        self.balls[0]["vx"] = math.cos(angle_rad) * impulse
        self.balls[0]["vy"] = math.sin(angle_rad) * impulse
        self.state = STATE_ROLLING

    def are_balls_moving(self) -> bool:
        for b in self.balls:
            if not b["active"]:
                continue
            if abs(b["vx"]) > 0.08 or abs(b["vy"]) > 0.08:
                return True
        return False

    def check_pocket_collisions(self):
        pockets = [
            (2.0, 2.0),
            (13.0, 2.0),
            (2.0, 13.0),
            (13.0, 13.0),
            (2.0, 7.5),
            (13.0, 7.5),
        ]

        for b in self.balls:
            if not b["active"]:
                continue

            for px, py in pockets:
                dx = b["x"] - px
                dy = b["y"] - py
                if (dx * dx + dy * dy) <= (0.85 * 0.85):
                    if b["is_cue"]:
                        self.score = max(0, self.score - 50)
                        self.state = STATE_SCRATCH
                        self.state_timer = 0.0
                        b["vx"] = 0.0
                        b["vy"] = 0.0
                        b["x"] = 4.0
                        b["y"] = 7.5
                    else:
                        b["active"] = False
                        b["vx"] = 0.0
                        b["vy"] = 0.0
                        self.balls_potted += 1
                        self.score += 150
                        if self.score > self.high_score:
                            self.high_score = self.score
                    break

    def check_cushion_collisions(self):
        min_x = 2.0
        max_x = 13.0
        min_y = 2.0
        max_y = 13.0
        restitution = 0.82

        for b in self.balls:
            if not b["active"]:
                continue

            if b["x"] < min_x:
                b["x"] = min_x
                b["vx"] = -b["vx"] * restitution
            elif b["x"] > max_x:
                b["x"] = max_x
                b["vx"] = -b["vx"] * restitution

            if b["y"] < min_y:
                b["y"] = min_y
                b["vy"] = -b["vy"] * restitution
            elif b["y"] > max_y:
                b["y"] = max_y
                b["vy"] = -b["vy"] * restitution

    def check_ball_ball_collisions(self):
        ball_diam = 0.95
        restitution = 0.88

        for i in range(len(self.balls)):
            if not self.balls[i]["active"]:
                continue
            for j in range(i + 1, len(self.balls)):
                if not self.balls[j]["active"]:
                    continue

                dx = self.balls[j]["x"] - self.balls[i]["x"]
                dy = self.balls[j]["y"] - self.balls[i]["y"]
                dist = math.sqrt(dx * dx + dy * dy)

                if 0.001 < dist < ball_diam:
                    nx = dx / dist
                    ny = dy / dist

                    overlap = 0.5 * (ball_diam - dist)
                    self.balls[i]["x"] -= nx * overlap
                    self.balls[i]["y"] -= ny * overlap
                    self.balls[j]["x"] += nx * overlap
                    self.balls[j]["y"] += ny * overlap

                    kx = self.balls[i]["vx"] - self.balls[j]["vx"]
                    ky = self.balls[i]["vy"] - self.balls[j]["vy"]
                    p = 2.0 * (nx * kx + ny * ky) / 2.0

                    if p > 0.0:
                        self.balls[i]["vx"] -= p * nx * restitution
                        self.balls[i]["vy"] -= p * ny * restitution
                        self.balls[j]["vx"] += p * nx * restitution
                        self.balls[j]["vy"] += p * ny * restitution

    def update_physics(self, dt: float):
        friction = 1.35

        for b in self.balls:
            if not b["active"]:
                continue

            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            drag = max(0.0, 1.0 - friction * dt)
            b["vx"] *= drag
            b["vy"] *= drag

            if abs(b["vx"]) < 0.08:
                b["vx"] = 0.0
            if abs(b["vy"]) < 0.08:
                b["vy"] = 0.0

        self.check_cushion_collisions()
        self.check_ball_ball_collisions()
        self.check_pocket_collisions()

    def update_aiming(self, dt: float, buttons: int, prev_buttons: int):
        rotate_speed = 2.4

        if buttons & KEY_LEFT:
            self.aim_angle -= rotate_speed * dt
        if buttons & KEY_RIGHT:
            self.aim_angle += rotate_speed * dt

        while self.aim_angle < 0.0:
            self.aim_angle += 2.0 * math.pi
        while self.aim_angle >= 2.0 * math.pi:
            self.aim_angle -= 2.0 * math.pi

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.state = STATE_CHARGING
            self.charge_power = 0.2
            self.charge_dir = 1.0

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_SCRATCH:
            if self.state_timer >= 1.2:
                self.state = STATE_AIMING
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_AIMING:
            self.update_aiming(dt, buttons, prev_buttons)
        elif self.state == STATE_CHARGING:
            self.charge_power += self.charge_dir * 1.8 * dt
            if self.charge_power >= 1.0:
                self.charge_power = 1.0
                self.charge_dir = -1.0
            elif self.charge_power <= 0.1:
                self.charge_power = 0.1
                self.charge_dir = 1.0

            if not (buttons & KEY_A) and (prev_buttons & KEY_A):
                self.strike_cue_ball(self.aim_angle, self.charge_power)
        elif self.state == STATE_ROLLING:
            self.update_physics(dt)

            if not self.are_balls_moving():
                if self.get_remaining_balls() == 0:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 1000
                    if self.score > self.high_score:
                        self.high_score = self.score
                else:
                    self.state = STATE_AIMING

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # 1. Table Border & Felt
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if 2 <= x <= 13 and 2 <= y <= 13:
                    # Green felt
                    fb[idx + 0] = 25
                    fb[idx + 1] = 111
                    fb[idx + 2] = 61
                else:
                    # Mahogany border
                    fb[idx + 0] = 110
                    fb[idx + 1] = 44
                    fb[idx + 2] = 0

        # 2. Pockets
        pockets = [(2, 2), (13, 2), (2, 13), (13, 13), (2, 7), (13, 7)]
        for px, py in pockets:
            idx = (py * 16 + px) * 3
            fb[idx + 0] = 0
            fb[idx + 1] = 0
            fb[idx + 2] = 0

        # 3. Aiming Guide Laser
        if self.state in (STATE_AIMING, STATE_CHARGING):
            cx = self.balls[0]["x"]
            cy = self.balls[0]["y"]
            for r in (1.2, 2.2, 3.2):
                ax = int(round(cx + math.cos(self.aim_angle) * r))
                ay = int(round(cy + math.sin(self.aim_angle) * r))
                if 2 <= ax <= 13 and 2 <= ay <= 13:
                    a_idx = (ay * 16 + ax) * 3
                    fb[a_idx + 0] = 174
                    fb[a_idx + 1] = 214
                    fb[a_idx + 2] = 241

        # 4. Balls
        for b in self.balls:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                c = b["color"]
                fb[idx + 0] = c[0]
                fb[idx + 1] = c[1]
                fb[idx + 2] = c[2]

        # 5. Power Meter Bar on Row 0
        if self.state == STATE_CHARGING:
            bars = int(round(self.charge_power * 14.0))
            for x in range(1, 15):
                idx = (0 * 16 + x) * 3
                if x <= bars:
                    fb[idx + 0] = 241
                    fb[idx + 1] = 196
                    fb[idx + 2] = 15

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "remaining_balls": self.get_remaining_balls(),
            "balls_potted": self.balls_potted,
            "aim_angle": self.aim_angle,
            "charge_power": self.charge_power,
            "cue_ball_x": self.balls[0]["x"],
            "cue_ball_y": self.balls[0]["y"],
        }
