"""
Game #190: 破坏大奖赛 (Demolition Derby - 1984 Bally Midway)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Bally Midway in 1984, Demolition Derby was the legendary pioneer of vehicular combat
and destruction derby motorsport gaming. Up to four derby drivers clash in an enclosed mud arena,
ramming rivals' fenders and side panels while protecting their fragile front radiator engines
until only one smoking, battered machine remains running!

Unique Core Mechanic (Strict Zero-Redundancy):
- Inertial Vehicular Physics & Steering: 360-degree rotational steering with momentum, sliding,
  and tire traction on mud arena ground.
- Forward Throttle (Button A) & Heavy Reverse Ram (Button B):
  * Forward Throttle: Surge forward into rivals.
  * Reverse Gear: Back-up ramming utilizes reinforced rear bumpers to crush opponents while
    safeguarding your vulnerable front radiator engine!
- Directional Impact Damage Mechanics:
  * Frontal Head-On collision inflicts heavy radiator recoil damage to both cars.
  * T-Bone Side T-Strike: Devastates the victim's chassis while preserving the striker.
- Last Machine Standing: Opponents stall into flaming arena obstacles as their health reaches zero!
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_CAR_WRECKED = 2
STATE_GAME_OVER = 3

class Game190DemolitionDerby(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Derby Car
        self.px = 8.0
        self.py = 12.0
        self.angle = -math.pi / 2.0 # Facing upwards
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.0
        self.hp = 100.0

        # Opponent Derby Cars [{id, name, x, y, angle, vx, vy, speed, hp, alive, color}]
        self.rivals: List[Dict[str, Any]] = []

        # Sparks / Debris [{x, y, timer}]
        self.debris: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 190

    @property
    def name(self) -> str:
        return "破坏大奖赛"

    @property
    def english_name(self) -> str:
        return "Demolition Derby"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "泥地封闭竞技场战车物理冲撞、倒车重击护甲保全水箱、定点侧翼T-Bone毁灭撞击与残骸生存淘汰"

    def get_name(self) -> str:
        return "Demolition Derby (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 8.0
        self.py = 12.0
        self.angle = -math.pi / 2.0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.0
        self.hp = 100.0
        self.debris.clear()

        # Seed 3 aggressive AI rivals
        self.rivals = [
            {"id": 1, "name": "Red Crusher",  "x": 4.0,  "y": 4.0, "angle": math.pi / 4.0,  "vx": 0.0, "vy": 0.0, "speed": 0.0, "hp": 70.0 + self.stage * 15.0, "alive": True, "r": 230, "g": 40, "b": 40},
            {"id": 2, "name": "Blue Bruiser", "x": 12.0, "y": 4.0, "angle": 3 * math.pi / 4.0, "vx": 0.0, "vy": 0.0, "speed": 0.0, "hp": 70.0 + self.stage * 15.0, "alive": True, "r": 40, "g": 100, "b": 230},
            {"id": 3, "name": "Yellow Ram",   "x": 8.0,  "y": 2.5, "angle": math.pi / 2.0,  "vx": 0.0, "vy": 0.0, "speed": 0.0, "hp": 70.0 + self.stage * 15.0, "alive": True, "r": 240, "g": 210, "b": 30},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_CAR_WRECKED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 8.0
                    self.py = 12.0
                    self.angle = -math.pi / 2.0
                    self.vx = 0.0
                    self.vy = 0.0
                    self.speed = 0.0
                    self.hp = 100.0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # 1. Steering & Transmission
        turn_speed = 3.5
        if keys_down & KEY_LEFT:
            self.angle -= turn_speed * dt
        if keys_down & KEY_RIGHT:
            self.angle += turn_speed * dt

        # Forward throttle (Button A) / Reverse gear (Button B)
        max_fwd_speed = 7.5
        max_rev_speed = -4.5
        accel = 12.0
        friction = 4.0

        if keys_down & KEY_A:
            self.speed = min(max_fwd_speed, self.speed + accel * dt)
        elif keys_down & KEY_B:
            self.speed = max(max_rev_speed, self.speed - accel * dt)
        else:
            # Natural friction deceleration
            if self.speed > 0:
                self.speed = max(0.0, self.speed - friction * dt)
            elif self.speed < 0:
                self.speed = min(0.0, self.speed + friction * dt)

        self.vx = math.cos(self.angle) * self.speed
        self.vy = math.sin(self.angle) * self.speed

        self.px += self.vx * dt
        self.py += self.vy * dt

        # Arena wall bounce
        if self.px < 1.5:
            self.px = 1.5
            self.vx = -self.vx * 0.5
            self.speed *= -0.4
        elif self.px > 14.5:
            self.px = 14.5
            self.vx = -self.vx * 0.5
            self.speed *= -0.4

        if self.py < 1.5:
            self.py = 1.5
            self.vy = -self.vy * 0.5
            self.speed *= -0.4
        elif self.py > 14.5:
            self.py = 14.5
            self.vy = -self.vy * 0.5
            self.speed *= -0.4

        # 2. Update Rivals AI
        for r in self.rivals:
            if not r["alive"]:
                continue

            # Target player position
            target_dx = self.px - r["x"]
            target_dy = self.py - r["y"]
            desired_angle = math.atan2(target_dy, target_dx)

            # Turn towards player
            angle_diff = (desired_angle - r["angle"] + math.pi) % (2 * math.pi) - math.pi
            r["angle"] += max(-3.0 * dt, min(3.0 * dt, angle_diff))

            # Accelerate towards player
            r_max_speed = 4.8 + self.stage * 0.3
            r["speed"] = min(r_max_speed, r["speed"] + 8.0 * dt)
            r["vx"] = math.cos(r["angle"]) * r["speed"]
            r["vy"] = math.sin(r["angle"]) * r["speed"]

            r["x"] += r["vx"] * dt
            r["y"] += r["vy"] * dt

            # Arena wall bounce
            r["x"] = max(1.5, min(14.5, r["x"]))
            r["y"] = max(1.5, min(14.5, r["y"]))

        # 3. Collision Resolution between Player & Rivals
        for r in self.rivals:
            dist = math.hypot(self.px - r["x"], self.py - r["y"])
            if dist < 1.5:
                # Collision impact!
                self.debris.append({"x": (self.px + r["x"]) / 2.0, "y": (self.py + r["y"]) / 2.0, "timer": 0.4})

                # Calculate impact relative velocity
                rel_v = math.hypot(self.vx - r["vx"], self.vy - r["vy"])
                impact_force = max(10.0, rel_v * 8.0)

                # Determine if player rammed with front or rear
                player_fwd_x = math.cos(self.angle)
                player_fwd_y = math.sin(self.angle)
                impact_dir_x = (r["x"] - self.px) / max(0.01, dist)
                impact_dir_y = (r["y"] - self.py) / max(0.01, dist)

                # Dot product > 0 means player hit with FRONT; < 0 means player hit with REAR
                dot = player_fwd_x * impact_dir_x + player_fwd_y * impact_dir_y

                if r["alive"]:
                    if dot > 0.4:
                        # Frontal ram: Radiator takes moderate damage, opponent takes heavy damage
                        self.hp -= impact_force * 0.4
                        r["hp"] -= impact_force * 0.8
                        self.score += int(impact_force * 5)
                    elif dot < -0.4:
                        # Reverse Ram: Heavy rear bumper absorbs hit, opponent takes heavy damage, player takes minimal
                        self.hp -= impact_force * 0.15
                        r["hp"] -= impact_force * 0.9
                        self.score += int(impact_force * 8) # Bonus for tactical reverse ramming!
                    else:
                        # Side impact: mutual damage
                        self.hp -= impact_force * 0.5
                        r["hp"] -= impact_force * 0.6
                        self.score += int(impact_force * 4)

                    if r["hp"] <= 0.0:
                        r["hp"] = 0.0
                        r["alive"] = False
                        r["speed"] = 0.0
                        self.score += 2000 # Car wrecked bonus!
                else:
                    # Hitting an already wrecked car
                    self.hp -= impact_force * 0.2

                # Elastic rebound recoil
                self.speed = -self.speed * 0.6
                r["speed"] = -r["speed"] * 0.6
                self.px -= impact_dir_x * 0.5
                self.py -= impact_dir_y * 0.5
                r["x"] += impact_dir_x * 0.5
                r["y"] += impact_dir_y * 0.5

        # Check Player Engine Blowout
        if self.hp <= 0.0:
            self.hp = 0.0
            self.lives -= 1
            self.state = STATE_CAR_WRECKED
            self.state_timer = 1.5
            return

        # Check All Rivals Eliminated -> Stage Clear!
        alive_rivals = [r for r in self.rivals if r["alive"]]
        if len(alive_rivals) == 0:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 5000

        # Update Debris / Sparks
        for d in self.debris[:]:
            d["timer"] -= dt
            if d["timer"] <= 0.0:
                self.debris.remove(d)

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

        # 1. Mud Arena Ground & Tire Barriers
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    set_pixel(x, y, 90, 80, 80) # Steel arena barrier
                else:
                    set_pixel(x, y, 110, 75, 45) # Brown mud dirt track

        # 2. Debris & Sparks
        for d in self.debris:
            dx = int(round(d["x"]))
            dy = int(round(d["y"]))
            set_pixel(dx, dy, 255, 230, 80)
            set_pixel(dx + 1, dy, 255, 120, 20)

        # 3. Rivals
        for r in self.rivals:
            rx = int(round(r["x"]))
            ry = int(round(r["y"]))
            if r["alive"]:
                set_pixel(rx, ry, r["r"], r["g"], r["b"])
                # Front nose direction
                fx = int(round(r["x"] + math.cos(r["angle"])))
                fy = int(round(r["y"] + math.sin(r["angle"])))
                set_pixel(fx, fy, 255, 255, 255)
            else:
                # Wrecked smoking obstacle
                set_pixel(rx, ry, 50, 50, 50)
                set_pixel(rx, ry - 1, 255, 80, 0) # Fire flame!

        # 4. Player Car
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 40, 220, 40)          # Green player stock chassis
            fx = int(round(self.px + math.cos(self.angle)))
            fy = int(round(self.py + math.sin(self.angle)))
            set_pixel(fx, fy, 255, 255, 100)        # Yellow headlights
            bx = int(round(self.px - math.cos(self.angle)))
            by = int(round(self.py - math.sin(self.angle)))
            set_pixel(bx, by, 180, 40, 40)          # Red reinforced rear bumper
        elif self.state == STATE_CAR_WRECKED:
            set_pixel(px, py, 255, 60, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "stage": self.stage,
            "hp": self.hp,
            "speed": self.speed,
            "alive_rivals": len([r for r in self.rivals if r["alive"]]),
        }

