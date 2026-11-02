"""
Game #086: 奇奇怪界 / 巫女退魔 (KiKi KaiKai 1986 / Taito)
Shrine Maiden Exorcism, 8-Way Ofuda Talisman Throwing & Gohei Purifying Wand Fireball Deflection.
"""

import math
import random
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

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_HERO_DEAD = 2

EN_BAKE_NEKO = 0
EN_KASA_OBAKE = 1
EN_TENGU = 2

MAX_ENEMIES = 4
MAX_PROJECTILES = 8


class Game086KiKiKaiKai(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 24000
        self.lives = 3
        self.yokai_defeated = 0

        # Sayo-chan
        self.px = 7.5
        self.py = 12.0
        self.facing_x = 0
        self.facing_y = -1
        self.gohei_timer = 0.0

        self.enemies: List[Dict[str, Any]] = []
        self.projectiles: List[Dict[str, Any]] = []

        self.spawn_timer = 0.0
        self.scroll_offset = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 86

    @property
    def name(self) -> str:
        return "奇奇怪界"

    @property
    def english_name(self) -> str:
        return "KiKi KaiKai"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "巫女破魔符咒八向投掷 + 御币神杖招架近战与反射敌方鬼火"

    def is_swinging_gohei(self) -> bool:
        return self.gohei_timer > 0.0

    def get_name(self) -> str:
        return "KiKi KaiKai (1986)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.yokai_defeated = 0
        self.reset_stage()

    def reset_stage(self):
        self.px = 7.5
        self.py = 12.0
        self.facing_x = 0
        self.facing_y = -1
        self.gohei_timer = 0.0
        self.spawn_timer = 0.0
        self.scroll_offset = 0.0

        self.enemies = [
            {"x": 4.0, "y": 2.0, "type": EN_BAKE_NEKO, "hp": 1, "active": True, "shoot_timer": 0.0},
            {"x": 11.0, "y": 3.0, "type": EN_TENGU, "hp": 2, "active": True, "shoot_timer": 1.5},
        ]
        self.projectiles = []

    def fire_talisman(self):
        if len([p for p in self.projectiles if p["active"]]) < MAX_PROJECTILES:
            spd = 14.0
            vx = self.facing_x * spd
            vy = -spd if (self.facing_x == 0 and self.facing_y == 0) else self.facing_y * spd

            self.projectiles.append({
                "x": self.px + self.facing_x * 0.8,
                "y": self.py + self.facing_y * 0.8,
                "vx": vx,
                "vy": vy,
                "is_talisman": True,
                "active": True,
            })

    def swing_gohei(self):
        self.gohei_timer = 0.28
        hit_x = self.px + self.facing_x * 1.4
        hit_y = self.py + (-1.0 if self.facing_y == 0 else self.facing_y) * 1.4

        # 1. Deflect & reflect enemy fireballs!
        for p in self.projectiles:
            if p["active"] and not p["is_talisman"]:
                if abs(p["x"] - hit_x) < 1.8 and abs(p["y"] - hit_y) < 1.8:
                    p["is_talisman"] = True
                    p["vx"] = -p["vx"]
                    p["vy"] = -p["vy"]
                    self.score += 300

        # 2. Wand melee hit yokai
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - hit_x) < 1.8 and abs(e["y"] - hit_y) < 1.8:
                e["hp"] -= 1
                if e["hp"] <= 0:
                    e["active"] = False
                    self.yokai_defeated += 1
                    self.score += 500

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_HERO_DEAD, STATE_STAGE_CLEAR):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.spawn_timer += dt
        if self.spawn_timer > 2.2:
            self.spawn_timer = 0.0
            if len([e for e in self.enemies if e["active"]]) < MAX_ENEMIES and self.yokai_defeated < 15:
                e_type = random.randint(0, 2)
                self.enemies.append({
                    "x": random.uniform(2.0, 14.0),
                    "y": 1.0,
                    "type": e_type,
                    "hp": 2 if e_type == EN_TENGU else 1,
                    "shoot_timer": 1.8,
                    "active": True,
                })

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.update_projectiles(dt)
        self.check_collisions()

        if self.yokai_defeated >= 15:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 6000

        self.scroll_offset += 2.0 * dt

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        speed = 5.2
        mx = 0.0
        my = 0.0

        if buttons & KEY_LEFT:
            mx -= 1.0
        if buttons & KEY_RIGHT:
            mx += 1.0
        if buttons & KEY_UP:
            my -= 1.0
        if buttons & KEY_DOWN:
            my += 1.0

        if mx != 0.0 or my != 0.0:
            self.facing_x = int(mx)
            self.facing_y = int(my)

        self.px += mx * speed * dt
        self.py += my * speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(2.0, min(14.0, self.py))

        if self.gohei_timer > 0.0:
            self.gohei_timer -= dt

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_talisman()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.swing_gohei()

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"]:
                continue

            if e["type"] == EN_BAKE_NEKO:
                dx = self.px - e["x"]
                dy = self.py - e["y"]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0.1:
                    e["x"] += (dx / dist) * 2.8 * dt
                    e["y"] += (dy / dist) * 2.8 * dt
            elif e["type"] == EN_KASA_OBAKE:
                e["y"] += 2.0 * dt
                e["x"] += math.sin(self.state_timer * 6.0) * 4.0 * dt
            elif e["type"] == EN_TENGU:
                e["x"] += math.cos(self.state_timer * 3.0) * 3.0 * dt
                e["shoot_timer"] = e.get("shoot_timer", 1.8) - dt
                if e["shoot_timer"] <= 0.0:
                    e["shoot_timer"] = 2.0
                    if len([p for p in self.projectiles if p["active"]]) < MAX_PROJECTILES:
                        dx = self.px - e["x"]
                        dy = self.py - e["y"]
                        d = max(0.1, math.sqrt(dx * dx + dy * dy))
                        self.projectiles.append({
                            "x": e["x"],
                            "y": e["y"] + 0.8,
                            "vx": (dx / d) * 7.0,
                            "vy": (dy / d) * 7.0,
                            "is_talisman": False,
                            "active": True,
                        })

            e["x"] = max(1.0, min(14.5, e["x"]))
            if e["y"] > 15.0:
                e["y"] = 0.5
                e["x"] = random.uniform(2.0, 14.0)

        self.enemies = [e for e in self.enemies if e["active"]]

    def update_projectiles(self, dt: float):
        for p in self.projectiles:
            if not p["active"]:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt

            if p["x"] < 0.0 or p["x"] > 15.5 or p["y"] < 0.0 or p["y"] > 15.5:
                p["active"] = False

        self.projectiles = [p for p in self.projectiles if p["active"]]

    def check_collisions(self):
        # 1. Talismans vs Yokai
        for p in self.projectiles:
            if not p["active"] or not p["is_talisman"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(p["x"] - e["x"]) < 1.4 and abs(p["y"] - e["y"]) < 1.4:
                    p["active"] = False
                    e["hp"] -= 1
                    if e["hp"] <= 0:
                        e["active"] = False
                        self.yokai_defeated += 1
                        self.score += 400
                    break

        # 2. Enemy Fireball vs Sayo
        for p in self.projectiles:
            if not p["active"] or p["is_talisman"]:
                continue
            if abs(p["x"] - self.px) < 1.1 and abs(p["y"] - self.py) < 1.1:
                p["active"] = False
                self.lives -= 1
                if self.lives > 0:
                    self.px = 7.5
                    self.py = 12.0
                else:
                    self.state = STATE_HERO_DEAD
                    self.state_timer = 0.0
                return

        # 3. Yokai touch Sayo
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - self.px) < 1.1 and abs(e["y"] - self.py) < 1.1:
                self.lives -= 1
                if self.lives > 0:
                    self.px = 7.5
                    self.py = 12.0
                else:
                    self.state = STATE_HERO_DEAD
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

        # 1. Shrine Path & Bamboo
        for y in range(16):
            for x in range(16):
                if x < 2 or x > 13:
                    set_pixel(x, y, 15, 60, 25)
                else:
                    set_pixel(x, y, 140, 130, 110)

        # Torii gate
        for x in range(4, 12):
            set_pixel(x, 1, 230, 40, 30)
        set_pixel(5, 2, 230, 40, 30)
        set_pixel(10, 2, 230, 40, 30)

        # 2. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["type"] == EN_BAKE_NEKO:
                set_pixel(ex, ey, 240, 240, 250)
                set_pixel(ex - 1, ey - 1, 255, 40, 40)
                set_pixel(ex + 1, ey - 1, 255, 40, 40)
            elif e["type"] == EN_KASA_OBAKE:
                set_pixel(ex, ey, 160, 60, 180)
                set_pixel(ex, ey - 1, 255, 255, 255)
                set_pixel(ex, ey + 1, 180, 140, 80)
            else:
                set_pixel(ex, ey, 220, 30, 30)
                set_pixel(ex, ey - 1, 30, 30, 30)
                set_pixel(ex + 1, ey, 255, 100, 100)

        # 3. Projectiles
        for p in self.projectiles:
            if not p["active"]:
                continue
            px = int(round(p["x"]))
            py = int(round(p["y"]))
            if p["is_talisman"]:
                set_pixel(px, py, 255, 255, 255)
                set_pixel(px, py - 1, 255, 30, 30)
            else:
                set_pixel(px, py, 50, 220, 255)
                set_pixel(px, py + 1, 30, 100, 255)

        # 4. Sayo-chan
        px = int(round(self.px))
        py = int(round(self.py))
        set_pixel(px, py, 220, 30, 30)
        set_pixel(px, py - 1, 255, 255, 255)
        set_pixel(px, py - 2, 240, 180, 140)
        set_pixel(px, py - 3, 20, 20, 20)

        if self.gohei_timer > 0.0:
            gx = px + self.facing_x
            gy = py + (-1 if self.facing_y == 0 else self.facing_y)
            set_pixel(gx, gy, 200, 160, 100)
            set_pixel(gx + self.facing_x, gy, 255, 255, 255)
            set_pixel(gx, gy - 1, 255, 255, 255)

        # 5. HUD
        for l in range(self.lives):
            set_pixel(l * 2, 0, 255, 50, 50)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "yokai_defeated": self.yokai_defeated,
            "px": self.px,
            "py": self.py,
            "gohei_active": self.gohei_timer > 0.0,
        }
