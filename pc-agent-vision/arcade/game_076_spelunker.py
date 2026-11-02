"""
Game #076: 经典古墓探险 / 矿洞夺宝 (Spelunker 1983 / MicroGraphic Image / Irem)
Delicate Fragility Platformer, Rope Climbing, Ghost Flare Vaporization & Cavern Key Escape.
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
STATE_DEAD = 2
STATE_VICTORY = 3

MAX_GHOSTS = 2
MAX_FLARES = 2
MAX_TREASURES = 4


class Game076Spelunker(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 8500
        self.lives = 3

        # Spelunker state
        self.px = 2.0
        self.py = 4.0
        self.pvy = 0.0
        self.fall_start_y = 4.0
        self.on_ground = True
        self.on_rope = False
        self.facing = 1
        self.oxygen = 100.0
        self.flares_count = 3
        self.treasures_collected = 0

        self.ghosts: List[Dict[str, Any]] = []
        self.flares: List[Dict[str, Any]] = []
        self.items: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 76

    @property
    def name(self) -> str:
        return "经典古墓探险"

    @property
    def english_name(self) -> str:
        return "Spelunker"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "极限下落高度限制与绳索攀爬 + 幽灵穿墙追击与信号弹驱散 + 氧气消耗与古墓脱逃"

    def get_name(self) -> str:
        return "Spelunker (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_stage()

    def init_stage(self):
        self.px = 2.0
        self.py = 4.0
        self.pvy = 0.0
        self.fall_start_y = 4.0
        self.on_ground = True
        self.on_rope = False
        self.facing = 1
        self.oxygen = 100.0
        self.flares_count = 3
        self.treasures_collected = 0

        self.flares = []

        self.ghosts = [
            {"x": 14.0, "y": 10.0, "vx": -1.2, "vy": 0.5, "active": True},
            {"x": 1.0, "y": 12.0, "vx": 1.0, "vy": -0.6, "active": False},
        ]

        self.items = [
            {"x": 12.0, "y": 4.0, "type": 0, "active": True},  # Gold Idol
            {"x": 6.0, "y": 9.0, "type": 1, "active": True},   # Oxygen
            {"x": 13.0, "y": 9.0, "type": 2, "active": True},  # Exit Key
            {"x": 8.0, "y": 14.0, "type": 0, "active": True},  # Gold Idol 2
        ]

    def get_treasures_remaining(self) -> int:
        return len([i for i in self.items if i["active"]])

    def fire_flare(self):
        if self.flares_count <= 0:
            return

        if len([f for f in self.flares if f["active"]]) < MAX_FLARES:
            self.flares.append({
                "x": self.px,
                "y": self.py - 1.0,
                "vy": -14.0,
                "duration": 1.2,
                "active": True,
            })
            self.flares_count -= 1

    def jump(self):
        if self.on_ground:
            self.pvy = -6.5
            self.fall_start_y = self.py
            self.on_ground = False
            self.on_rope = False
        elif self.on_rope:
            self.pvy = -5.0
            self.fall_start_y = self.py
            self.px += self.facing * 1.0
            self.on_rope = False
            self.on_ground = False

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.px = 2.0
                    self.py = 4.0
                    self.pvy = 0.0
                    self.fall_start_y = 4.0
                    self.on_ground = True
                    self.on_rope = False
                    self.oxygen = 100.0
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        self.oxygen -= 2.2 * dt
        if self.oxygen <= 0.0:
            self.lives -= 1
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_flares(dt)
        self.update_ghosts(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 4.5

        near_rope1 = (abs(self.px - 5.0) < 0.6 and 4.0 <= self.py <= 14.0)
        near_rope2 = (abs(self.px - 11.0) < 0.6 and 4.0 <= self.py <= 9.0)

        if (near_rope1 or near_rope2) and ((buttons & KEY_UP) or (buttons & KEY_DOWN)):
            self.on_rope = True
            self.px = 5.0 if near_rope1 else 11.0
            self.pvy = 0.0

        if self.on_rope:
            climb_speed = 3.5
            if buttons & KEY_UP:
                self.py -= climb_speed * dt
            if buttons & KEY_DOWN:
                self.py += climb_speed * dt

            if buttons & KEY_LEFT:
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.facing = 1

            self.py = max(4.0, min(14.0, self.py))
            self.fall_start_y = self.py
        else:
            if buttons & KEY_LEFT:
                self.px -= move_speed * dt
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.px += move_speed * dt
                self.facing = 1

            self.px = max(0.5, min(15.0, self.px))

            prev_y = self.py
            self.pvy += 22.0 * dt
            self.py += self.pvy * dt

            self.on_ground = False
            if self.pvy >= 0.0:
                landing_y = -1.0
                if self.py >= 14.0:
                    landing_y = 14.0
                elif prev_y <= 9.0 and self.py >= 9.0 and ((2.8 <= self.px <= 8.2) or (10.8 <= self.px <= 15.2)):
                    landing_y = 9.0
                elif prev_y <= 4.0 and self.py >= 4.0 and ((0.8 <= self.px <= 5.2) or (9.8 <= self.px <= 14.2)):
                    landing_y = 4.0

                if landing_y > 0.0:
                    if (landing_y - self.fall_start_y) > 2.2:
                        self.lives -= 1
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

                    self.py = landing_y
                    self.pvy = 0.0
                    self.on_ground = True
                    self.fall_start_y = self.py

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.jump()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.fire_flare()

    def update_flares(self, dt: float):
        for f in self.flares:
            if not f["active"]:
                continue
            f["y"] += f["vy"] * dt
            f["duration"] -= dt
            if f["duration"] <= 0.0 or f["y"] < 0.0:
                f["active"] = False

        self.flares = [f for f in self.flares if f["active"]]

    def update_ghosts(self, dt: float):
        for g in self.ghosts:
            if not g["active"]:
                continue
            dx = self.px - g["x"]
            dy = self.py - g["y"]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0.1:
                spd = 1.4
                g["x"] += (dx / dist) * spd * dt
                g["y"] += (dy / dist) * spd * dt

    def check_collisions(self):
        # 1. Flares vs Ghosts
        for f in self.flares:
            if not f["active"]:
                continue
            for g in self.ghosts:
                if not g["active"]:
                    continue
                if abs(f["x"] - g["x"]) < 3.0 and abs(f["y"] - g["y"]) < 3.0:
                    g["active"] = False
                    self.score += 500
                    break

        # 2. Ghost touches player
        for g in self.ghosts:
            if not g["active"]:
                continue
            if abs(self.px - g["x"]) < 0.9 and abs(self.py - g["y"]) < 0.9:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        # 3. Item collections
        for item in self.items:
            if not item["active"]:
                continue
            if abs(self.px - item["x"]) < 1.1 and abs(self.py - item["y"]) < 1.1:
                item["active"] = False
                if item["type"] == 0:
                    self.score += 300
                elif item["type"] == 1:
                    self.oxygen = min(100.0, self.oxygen + 35.0)
                    self.score += 150
                else:
                    self.score += 500
                self.treasures_collected += 1

        # 4. Cavern exit with key (items[2] is Key)
        if not self.items[2]["active"] and self.px >= 13.0 and self.py >= 13.5:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 4000
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Cavern Background
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 15, 12, 10)

        # 2. Platforms
        for x in range(16): set_pixel(x, 15, 120, 80, 40)
        for x in range(3, 9): set_pixel(x, 10, 130, 85, 45)
        for x in range(11, 16): set_pixel(x, 10, 130, 85, 45)
        for x in range(1, 6): set_pixel(x, 5, 140, 90, 50)
        for x in range(10, 15): set_pixel(x, 5, 140, 90, 50)

        # 3. Ropes
        for y in range(4, 15): set_pixel(5, y, 200, 160, 60)
        for y in range(4, 10): set_pixel(11, y, 200, 160, 60)

        # 4. Exit Portal
        has_key = not self.items[2]["active"]
        set_pixel(14, 14, 50 if has_key else 200, 255 if has_key else 30, 40)
        set_pixel(15, 14, 50 if has_key else 200, 255 if has_key else 30, 40)

        # 5. Items
        for item in self.items:
            if not item["active"]:
                continue
            ix = int(round(item["x"]))
            iy = int(round(item["y"]))
            if item["type"] == 0:
                set_pixel(ix, iy, 255, 215, 0)
                set_pixel(ix, iy - 1, 255, 180, 0)
            elif item["type"] == 1:
                set_pixel(ix, iy, 40, 220, 255)
                set_pixel(ix, iy - 1, 255, 255, 255)
            else:
                set_pixel(ix, iy, 255, 220, 50)
                set_pixel(ix + 1, iy, 255, 220, 50)

        # 6. Flares
        for f in self.flares:
            if not f["active"]:
                continue
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            set_pixel(fx, fy, 255, 255, 200)
            set_pixel(fx, fy + 1, 255, 120, 0)
            set_pixel(fx - 1, fy, 255, 200, 50)
            set_pixel(fx + 1, fy, 255, 200, 50)

        # 7. Ghosts
        for g in self.ghosts:
            if not g["active"]:
                continue
            gx = int(round(g["x"]))
            gy = int(round(g["y"]))
            set_pixel(gx, gy, 230, 240, 255)
            set_pixel(gx, gy - 1, 200, 220, 255)
            set_pixel(gx - 1, gy, 180, 200, 255)
            set_pixel(gx + 1, gy, 180, 200, 255)

        # 8. Spelunker
        if self.state != STATE_DEAD:
            sx = int(round(self.px))
            sy = int(round(self.py))
            set_pixel(sx, sy, 50, 120, 220)
            set_pixel(sx, sy - 1, 255, 200, 150)
            set_pixel(sx, sy - 2, 255, 220, 30)
            set_pixel(sx + self.facing, sy - 2, 255, 255, 255)
        else:
            sx = int(round(self.px))
            sy = int(round(self.py))
            set_pixel(sx, sy, 220, 20, 20)

        # 9. HUD
        o2_bars = int((self.oxygen / 100.0) * 8.0)
        for b in range(o2_bars):
            set_pixel(b, 0, 40, 220, 255)
        for f in range(self.flares_count):
            set_pixel(15 - f, 0, 255, 100, 0)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "px": self.px,
            "py": self.py,
            "oxygen": self.oxygen,
            "on_rope": self.on_rope,
            "flares_count": self.flares_count,
            "treasures_remaining": self.get_treasures_remaining(),
        }
