"""
Game #071: 经典魔界村 (Ghosts 'n Goblins 1985 / Capcom)
Two-Stage Armor System (Steel Armor / Boxer Shorts), Multi-Trajectory Lance & Fire Flask, and Red Arremer Demon.
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

ARMOR_STEEL = 0
ARMOR_BOXERS = 1

WEAPON_LANCE = 0
WEAPON_TORCH = 1

MAX_WEAPONS = 3
MAX_ENEMIES = 4
MAX_FLAMES = 2


class Game071GhostsNGoblins(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 7500
        self.lives = 3

        # Arthur state
        self.px = 2.0
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.is_ducking = False
        self.facing = 1
        self.armor_stage = ARMOR_STEEL
        self.weapon_type = WEAPON_LANCE
        self.throw_cooldown = 0.0

        self.enemies_defeated = 0
        self.armor_drop_active = False
        self.armor_drop_x = 0.0
        self.armor_drop_y = 0.0

        self.weapons: List[Dict[str, Any]] = []
        self.flames: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 71

    @property
    def name(self) -> str:
        return "魔界村"

    @property
    def english_name(self) -> str:
        return "Ghosts 'n Goblins"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "盔甲碎裂内裤狂奔双阶段承伤 + 抛物线火把地面延烧与长矛贯通 + 墓地僵尸与红魔鬼俯冲"

    def get_name(self) -> str:
        return "Ghosts 'n Goblins (1985)"

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
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.is_ducking = False
        self.facing = 1
        self.armor_stage = ARMOR_STEEL
        self.weapon_type = WEAPON_LANCE
        self.throw_cooldown = 0.0
        self.enemies_defeated = 0
        self.armor_drop_active = False

        self.weapons = []
        self.flames = []

        self.enemies = [
            {"x": 14.0, "y": 14.0, "vx": -2.0, "vy": 0.0, "type": 0, "health": 1, "active": True},
            {"x": 10.0, "y": 14.0, "vx": -1.8, "vy": 0.0, "type": 0, "health": 1, "active": True},
            {"x": 6.0, "y": 14.0, "vx": -2.2, "vy": 0.0, "type": 0, "health": 1, "active": True},
            {"x": 8.0, "y": 5.0, "vx": -2.5, "vy": 1.5, "type": 1, "health": 2, "active": True},
        ]

    def throw_weapon(self):
        if self.throw_cooldown > 0.0:
            return

        if len([w for w in self.weapons if w["active"]]) < MAX_WEAPONS:
            vx = self.facing * (14.0 if self.weapon_type == WEAPON_LANCE else 8.0)
            vy = 0.0 if self.weapon_type == WEAPON_LANCE else -7.0

            self.weapons.append({
                "x": self.px + self.facing * 0.8,
                "y": self.py + 0.5 if self.is_ducking else self.py - 0.5,
                "vx": vx,
                "vy": vy,
                "type": self.weapon_type,
                "active": True,
            })

        self.throw_cooldown = 0.25

    def jump(self):
        if self.on_ground and not self.is_ducking:
            self.pvy = -8.8
            self.on_ground = False

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.init_stage()
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        if self.throw_cooldown > 0.0:
            self.throw_cooldown -= dt

        self.update_player(dt, buttons, prev_buttons)
        self.update_weapons(dt)
        self.update_enemies(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        self.is_ducking = bool((buttons & KEY_DOWN) and self.on_ground)

        speed = 0.0 if self.is_ducking else 5.0
        if not self.is_ducking:
            if buttons & KEY_LEFT:
                self.px -= speed * dt
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.px += speed * dt
                self.facing = 1

        self.px = max(0.5, min(15.0, self.px))

        # Gravity
        self.pvy += 26.0 * dt
        self.py += self.pvy * dt

        self.on_ground = False
        if self.pvy >= 0.0:
            if self.py >= 14.0:
                self.py = 14.0
                self.pvy = 0.0
                self.on_ground = True
            elif 9.0 <= self.py <= 9.6 and 3.8 <= self.px <= 11.2:
                self.py = 9.0
                self.pvy = 0.0
                self.on_ground = True

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.jump()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.throw_weapon()

    def update_weapons(self, dt: float):
        for w in self.weapons:
            if not w["active"]:
                continue
            w["x"] += w["vx"] * dt

            if w["type"] == WEAPON_TORCH:
                w["vy"] += 22.0 * dt
                w["y"] += w["vy"] * dt

                if w["y"] >= 14.0:
                    w["active"] = False
                    if len([f for f in self.flames if f["active"]]) < MAX_FLAMES:
                        self.flames.append({
                            "x": w["x"],
                            "y": 14.0,
                            "duration": 1.8,
                            "active": True,
                        })

            if w["x"] < 0.0 or w["x"] > 15.5 or w["y"] < 0.0:
                w["active"] = False

        self.weapons = [w for w in self.weapons if w["active"]]

        for f in self.flames:
            if not f["active"]:
                continue
            f["duration"] -= dt
            if f["duration"] <= 0.0:
                f["active"] = False

        self.flames = [f for f in self.flames if f["active"]]

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"]:
                continue

            if e["type"] == 0:
                e["x"] += e["vx"] * dt
                if e["x"] < -1.0:
                    e["x"] = 16.5
                elif e["x"] > 17.0:
                    e["x"] = -0.5
            else:
                e["x"] += e["vx"] * dt
                e["y"] += math.sin(self.state_timer * 5.0) * 3.5 * dt
                if e["x"] < 1.0:
                    e["x"] = 1.0
                    e["vx"] = abs(e["vx"])
                elif e["x"] >= 14.0:
                    e["x"] = 14.0
                    e["vx"] = -abs(e["vx"])

    def check_collisions(self):
        # 1. Weapons hit enemies
        for w in self.weapons:
            if not w["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(w["x"] - e["x"]) < 1.2 and abs(w["y"] - e["y"]) < 1.2:
                    w["active"] = False
                    e["health"] -= 1
                    if e["health"] <= 0:
                        e["active"] = False
                        self.enemies_defeated += 1
                        self.score += 500 if e["type"] == 1 else 150

                        if self.armor_stage == ARMOR_BOXERS and not self.armor_drop_active:
                            self.armor_drop_active = True
                            self.armor_drop_x = e["x"]
                            self.armor_drop_y = 14.0

                        if self.enemies_defeated >= 8:
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                            self.score += 3000
                            if self.score > self.high_score:
                                self.high_score = self.score
                            return
                    break

        # 2. Flames burn enemies
        for f in self.flames:
            if not f["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(f["x"] - e["x"]) < 1.2 and abs(f["y"] - e["y"]) < 1.2:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 200
                    if self.enemies_defeated >= 8:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 3000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

        # 3. Armor Jar collect
        if self.armor_drop_active:
            if abs(self.px - self.armor_drop_x) < 1.2 and abs(self.py - self.armor_drop_y) < 1.2:
                self.armor_drop_active = False
                self.armor_stage = ARMOR_STEEL
                self.score += 500

        # 4. Enemy hits Arthur
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(self.px - e["x"]) < 0.9 and abs(self.py - e["y"]) < 0.9:
                if self.armor_stage == ARMOR_STEEL:
                    self.armor_stage = ARMOR_BOXERS
                    self.px -= self.facing * 1.5
                    self.pvy = -4.0
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
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

        # 1. Background
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 5, 10, 25)

        # Blood Moon
        set_pixel(13, 2, 220, 50, 40)
        set_pixel(14, 2, 220, 50, 40)

        # Ground & Platforms
        for x in range(16):
            set_pixel(x, 15, 30, 60, 25)
        for x in range(4, 12):
            set_pixel(x, 10, 70, 70, 80)

        # Tombstones
        set_pixel(3, 14, 120, 120, 130)
        set_pixel(8, 14, 120, 120, 130)

        # Armor jar
        if self.armor_drop_active:
            ax = int(round(self.armor_drop_x))
            ay = int(round(self.armor_drop_y))
            set_pixel(ax, ay, 200, 200, 220)
            set_pixel(ax, ay - 1, 255, 215, 0)

        # Flames
        for f in self.flames:
            if not f["active"]:
                continue
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            set_pixel(fx, fy, 255, 100, 20)
            set_pixel(fx, fy - 1, 255, 220, 40)

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["type"] == 0:
                set_pixel(ex, ey, 70, 130, 80)
                set_pixel(ex, ey - 1, 100, 160, 110)
                set_pixel(ex, ey - 2, 220, 220, 200)
            else:
                set_pixel(ex, ey, 220, 20, 20)
                set_pixel(ex - 1, ey, 160, 10, 10)
                set_pixel(ex + 1, ey, 160, 10, 10)
                set_pixel(ex, ey - 1, 255, 60, 60)

        # Weapons
        for w in self.weapons:
            if not w["active"]:
                continue
            wx = int(round(w["x"]))
            wy = int(round(w["y"]))
            if w["type"] == WEAPON_LANCE:
                set_pixel(wx, wy, 220, 220, 240)
            else:
                set_pixel(wx, wy, 255, 120, 0)

        # Arthur
        if self.state != STATE_DEAD:
            px = int(round(self.px))
            py = int(round(self.py))
            if self.armor_stage == ARMOR_STEEL:
                set_pixel(px, py, 190, 200, 210)
                set_pixel(px, py - 1, 220, 230, 240)
                set_pixel(px + self.facing, py - 1, 255, 50, 50)
            else:
                set_pixel(px, py, 255, 255, 255)
                set_pixel(px, py - 1, 230, 170, 130)
                set_pixel(px, py - 2, 160, 90, 40)
        else:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px - 1, py, 220, 220, 220)
            set_pixel(px,     py, 255, 255, 255)
            set_pixel(px + 1, py, 220, 220, 220)

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
            "armor_stage": self.armor_stage,
            "weapon_type": self.weapon_type,
            "enemies_defeated": self.enemies_defeated,
        }
