"""
Game #074: 灭虫专家 / 大金刚3 (Donkey Kong 3 1983 / Nintendo)
Vertical Fumigator Pest Control, Tug-of-War Rope Push Physics, Greenhouse Flower Defense & Super Spray.
"""

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

MAX_SPRAYS = 3
MAX_BUGS = 4
MAX_FLOWERS = 4


class Game074DonkeyKong3(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 8000
        self.lives = 3

        # Stanley state
        self.px = 4.0
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.spray_cooldown = 0.0
        self.has_super_spray = False
        self.super_spray_timer = 0.0

        # Donkey Kong state
        self.dk_x = 7.5
        self.dk_y = 5.0
        self.dk_drop_speed = 0.6
        self.super_can_active = False
        self.super_can_x = 7.5
        self.super_can_y = 5.0

        self.sprays: List[Dict[str, Any]] = []
        self.bugs: List[Dict[str, Any]] = []
        self.flowers: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 74

    @property
    def name(self) -> str:
        return "灭虫专家"

    @property
    def english_name(self) -> str:
        return "Donkey Kong 3"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "向上强力灭虫喷雾驱赶大金刚入蜂窝 + 护卫温室花朵拔河博弈 + 超级喷雾器升级"

    def get_name(self) -> str:
        return "Donkey Kong 3 (1983)"

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
        self.px = 4.0
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.spray_cooldown = 0.0
        self.has_super_spray = False
        self.super_spray_timer = 0.0

        self.dk_x = 7.5
        self.dk_y = 5.0
        self.dk_drop_speed = 0.6
        self.super_can_active = False

        self.sprays = []

        self.flowers = [
            {"x": 3.0, "y": 14.0, "active": True},
            {"x": 6.0, "y": 14.0, "active": True},
            {"x": 9.0, "y": 14.0, "active": True},
            {"x": 12.0, "y": 14.0, "active": True},
        ]

        self.bugs = [
            {"x": 2.0, "y": 2.0, "vx": 2.5, "vy": 1.5, "type": 0, "has_flower": False, "active": True},
            {"x": 13.0, "y": 3.0, "vx": -2.2, "vy": 1.8, "type": 0, "has_flower": False, "active": True},
            {"x": 4.0, "y": 1.0, "vx": 2.0, "vy": 2.0, "type": 1, "has_flower": False, "active": True},
            {"x": 11.0, "y": 1.0, "vx": -2.0, "vy": 2.0, "type": 1, "has_flower": False, "active": True},
        ]

    def get_flowers_remaining(self) -> int:
        return len([f for f in self.flowers if f["active"]])

    def spray_upward(self):
        if self.spray_cooldown > 0.0:
            return

        if len([s for s in self.sprays if s["active"]]) < MAX_SPRAYS:
            self.sprays.append({
                "x": self.px,
                "y": self.py - 1.2,
                "vy": -16.0,
                "is_super": self.has_super_spray,
                "active": True,
            })

        self.spray_cooldown = 0.22

    def jump(self):
        if self.on_ground:
            self.pvy = -8.5
            self.on_ground = False

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.px = 4.0
                    self.py = 14.0
                    self.pvy = 0.0
                    self.dk_y = 5.0
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        if self.spray_cooldown > 0.0:
            self.spray_cooldown -= dt

        if self.super_spray_timer > 0.0:
            self.super_spray_timer -= dt
            if self.super_spray_timer <= 0.0:
                self.has_super_spray = False

        self.update_player(dt, buttons, prev_buttons)
        self.update_sprays(dt)
        self.update_donkey_kong(dt)
        self.update_bugs(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 5.5

        if buttons & KEY_LEFT:
            self.px -= move_speed * dt
        if buttons & KEY_RIGHT:
            self.px += move_speed * dt

        self.px = max(0.5, min(15.0, self.px))

        # Gravity
        self.pvy += 22.0 * dt
        self.py += self.pvy * dt

        self.on_ground = False
        if self.pvy >= 0.0:
            if self.py >= 14.0:
                self.py = 14.0
                self.pvy = 0.0
                self.on_ground = True
            elif 10.0 <= self.py <= 10.6 and ((1.8 <= self.px <= 6.2) or (8.8 <= self.px <= 13.2)):
                self.py = 10.0
                self.pvy = 0.0
                self.on_ground = True

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.jump()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.spray_upward()

    def update_sprays(self, dt: float):
        for s in self.sprays:
            if not s["active"]:
                continue
            s["y"] += s["vy"] * dt
            if s["y"] < 1.0:
                s["active"] = False

        self.sprays = [s for s in self.sprays if s["active"]]

    def update_donkey_kong(self, dt: float):
        self.dk_y += self.dk_drop_speed * dt

        if self.dk_y >= 11.5:
            self.lives -= 1
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        if self.dk_y <= 3.5 and not self.super_can_active and not self.has_super_spray:
            self.super_can_active = True
            self.super_can_x = self.dk_x
            self.super_can_y = self.dk_y + 1.5

        if self.super_can_active:
            self.super_can_y += 3.0 * dt
            if self.super_can_y > 14.5:
                self.super_can_active = False

    def update_bugs(self, dt: float):
        for b in self.bugs:
            if not b["active"]:
                continue

            if b["has_flower"]:
                b["y"] -= 3.0 * dt
                if b["y"] < 0.0:
                    b["active"] = False
            else:
                b["x"] += b["vx"] * dt
                b["y"] += b["vy"] * dt

                if b["x"] <= 1.0:
                    b["x"] = 1.0
                    b["vx"] = abs(b["vx"])
                elif b["x"] >= 14.5:
                    b["x"] = 14.5
                    b["vx"] = -abs(b["vx"])

                if b["y"] <= 1.0:
                    b["y"] = 1.0
                    b["vy"] = abs(b["vy"])
                elif b["y"] >= 14.0:
                    for f in self.flowers:
                        if f["active"] and abs(b["x"] - f["x"]) < 1.4:
                            f["active"] = False
                            b["has_flower"] = True
                            break
                    b["vy"] = -abs(b["vy"])

    def check_collisions(self):
        # 1. Sprays hit Donkey Kong
        for s in self.sprays:
            if not s["active"]:
                continue

            if abs(s["x"] - self.dk_x) < 2.0 and self.dk_y - 1.0 <= s["y"] <= self.dk_y + 1.8:
                s["active"] = False
                push = 1.6 if s["is_super"] else 0.8
                self.dk_y -= push
                self.score += 100 if s["is_super"] else 50

                if self.dk_y <= 1.5:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 3500
                    if self.score > self.high_score:
                        self.high_score = self.score
                    return

        # 2. Sprays hit bugs
        for s in self.sprays:
            if not s["active"]:
                continue
            for b in self.bugs:
                if not b["active"]:
                    continue
                if abs(s["x"] - b["x"]) < 1.3 and abs(s["y"] - b["y"]) < 1.3:
                    s["active"] = False
                    b["active"] = False
                    self.score += 200

                    if b["has_flower"]:
                        for f in self.flowers:
                            if not f["active"]:
                                f["active"] = True
                                f["x"] = b["x"]
                                f["y"] = 14.0
                                break
                    break

        # 3. Super Spray Can pickup
        if self.super_can_active:
            if abs(self.px - self.super_can_x) < 1.2 and abs(self.py - self.super_can_y) < 1.2:
                self.super_can_active = False
                self.has_super_spray = True
                self.super_spray_timer = 6.0
                self.score += 500

        # 4. Bugs sting Stanley
        for b in self.bugs:
            if not b["active"]:
                continue
            if abs(self.px - b["x"]) < 0.9 and abs(self.py - b["y"]) < 0.9:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Background
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 15, 30, 20)

        for x in range(6, 10):
            set_pixel(x, 1, 255, 200, 30)

        for y in range(1, 13):
            set_pixel(6, y, 180, 150, 80)
            set_pixel(9, y, 180, 150, 80)

        for x in range(16): set_pixel(x, 15, 80, 140, 50)
        for x in range(2, 7): set_pixel(x, 10, 140, 90, 40)
        for x in range(9, 14): set_pixel(x, 10, 140, 90, 40)

        # Flowers
        for f in self.flowers:
            if not f["active"]:
                continue
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            set_pixel(fx, fy, 255, 60, 60)
            set_pixel(fx, fy - 1, 255, 220, 40)

        # Super can
        if self.super_can_active:
            cx = int(round(self.super_can_x))
            cy = int(round(self.super_can_y))
            set_pixel(cx, cy, 255, 215, 0)
            set_pixel(cx, cy - 1, 255, 50, 50)

        # Bugs
        for b in self.bugs:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["type"] == 0:
                set_pixel(bx, by, 255, 220, 0)
                set_pixel(bx - 1, by, 40, 40, 40)
                set_pixel(bx + 1, by, 40, 40, 40)
            else:
                set_pixel(bx, by, 255, 50, 200)
                set_pixel(bx - 1, by, 50, 150, 255)
                set_pixel(bx + 1, by, 50, 150, 255)
            if b["has_flower"]:
                set_pixel(bx, by + 1, 255, 60, 60)

        # Donkey Kong
        dkx = int(round(self.dk_x))
        dky = int(round(self.dk_y))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                set_pixel(dkx + dx, dky + dy, 140, 70, 20)
        set_pixel(dkx, dky, 240, 180, 120)
        set_pixel(dkx - 1, dky, 255, 30, 30)
        set_pixel(dkx - 2, dky - 1, 140, 70, 20)
        set_pixel(dkx + 2, dky - 1, 140, 70, 20)

        # Sprays
        for s in self.sprays:
            if not s["active"]:
                continue
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            if s["is_super"]:
                set_pixel(sx, sy, 255, 255, 50)
                set_pixel(sx, sy - 1, 255, 200, 0)
            else:
                set_pixel(sx, sy, 200, 240, 255)
                set_pixel(sx, sy - 1, 150, 220, 255)

        # Stanley
        if self.state != STATE_DEAD:
            sx = int(round(self.px))
            sy = int(round(self.py))
            set_pixel(sx, sy, 40, 60, 180)
            set_pixel(sx, sy - 1, 255, 200, 160)
            set_pixel(sx, sy - 2, 220, 30, 30)
            set_pixel(sx, sy - 3, 220, 220, 240)
        else:
            sx = int(round(self.px))
            sy = int(round(self.py))
            set_pixel(sx, sy, 220, 30, 30)

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
            "dk_y": self.dk_y,
            "flowers_remaining": self.get_flowers_remaining(),
            "has_super_spray": self.has_super_spray,
        }
