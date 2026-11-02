"""
Game #064: 潜艇雷击战 / 海底大战争 (In The Hunt 1993 / Irem)
Underwater Side-Scrolling Submarine Combat: Forward Torpedoes, Anti-Air Surface Missiles, Depth Charges & Mecha Kraken Boss.
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

MAX_TORPEDOES = 4
MAX_MISSILES = 3
MAX_DEPTH_CHARGES = 3
MAX_ENEMIES = 4


class Game064InTheHunt(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 4000
        self.lives = 3

        # Granvia Submarine
        self.sub_x = 2.5
        self.sub_y = 8.0
        self.sub_facing = 1
        self.shoot_cooldown = 0.0

        self.scroll_x = 0.0
        self.enemies_defeated = 0

        # Boss Mecha Kraken
        self.boss_active = False
        self.boss_x = 13.0
        self.boss_y = 8.0
        self.boss_vy = 2.0
        self.boss_health = 10
        self.boss_shoot_cooldown = 1.3

        self.torpedoes: List[Dict[str, Any]] = []
        self.missiles: List[Dict[str, Any]] = []
        self.depth_charges: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

    @property
    def game_id(self) -> int:
        return 64

    @property
    def name(self) -> str:
        return "海底大战争"

    @property
    def english_name(self) -> str:
        return "In The Hunt"

    @property
    def release_year(self) -> int:
        return 1993

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "潜艇全向雷击 + 水面防空导弹 + 垂直深水炸弹 + 机械海怪Boss战"

    def get_name(self) -> str:
        return "In The Hunt (1993)"

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
        self.sub_x = 2.5
        self.sub_y = 8.0
        self.sub_facing = 1
        self.shoot_cooldown = 0.0
        self.scroll_x = 0.0
        self.enemies_defeated = 0
        self.boss_active = False
        self.boss_x = 13.0
        self.boss_y = 8.0
        self.boss_vy = 2.0
        self.boss_health = 10
        self.boss_shoot_cooldown = 1.3

        self.torpedoes = []
        self.missiles = []
        self.depth_charges = []

        # Surface Gunboat (y=2.0), Sub (y=7.0), Sea Mine (y=12.0), Sub 2 (y=9.0)
        self.enemies = [
            {"x": 14.0, "y": 2.0, "vx": -1.8, "type": 0, "health": 1, "active": True, "shoot_cooldown": 2.0},
            {"x": 15.0, "y": 7.0, "vx": -2.0, "type": 1, "health": 1, "active": True, "shoot_cooldown": 2.2},
            {"x": 11.0, "y": 12.0, "vx": -0.8, "type": 2, "health": 1, "active": True, "shoot_cooldown": 99.0},
            {"x": 18.0, "y": 9.0, "vx": -1.5, "type": 1, "health": 1, "active": True, "shoot_cooldown": 2.5},
        ]

    def fire_torpedoes(self):
        if self.shoot_cooldown > 0.0:
            return

        # 1. Forward Torpedo
        if len([t for t in self.torpedoes if t["active"]]) < MAX_TORPEDOES:
            self.torpedoes.append({
                "x": self.sub_x + self.sub_facing * 1.0,
                "y": self.sub_y,
                "vx": self.sub_facing * 14.0,
                "vy": 0.0,
                "is_player": True,
                "active": True,
            })

        # 2. Surface Anti-Air Missile if near water surface (y <= 6.0)
        if self.sub_y <= 6.0:
            if len([m for m in self.missiles if m["active"]]) < MAX_MISSILES:
                self.missiles.append({
                    "x": self.sub_x,
                    "y": self.sub_y - 0.8,
                    "vx": self.sub_facing * 2.0,
                    "vy": -16.0,
                    "is_player": True,
                    "active": True,
                })

        self.shoot_cooldown = 0.25

    def drop_depth_charge(self):
        if len([d for d in self.depth_charges if d["active"]]) < MAX_DEPTH_CHARGES:
            self.depth_charges.append({
                "x": self.sub_x,
                "y": self.sub_y + 0.8,
                "vx": self.sub_facing * 1.5,
                "vy": 12.0,
                "is_player": True,
                "active": True,
            })

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

        if self.shoot_cooldown > 0.0:
            self.shoot_cooldown -= dt

        self.update_submarine(dt, buttons, prev_buttons)
        self.update_projectiles(dt)

        if self.boss_active:
            self.update_boss(dt)
        else:
            self.update_enemies(dt)
            if self.enemies_defeated >= 5:
                self.boss_active = True
                self.boss_x = 13.0
                self.boss_y = 8.0
                for e in self.enemies:
                    e["active"] = False

        self.check_collisions()

    def update_submarine(self, dt: float, buttons: int, prev_buttons: int):
        speed = 6.0

        if buttons & KEY_LEFT:
            self.sub_x -= speed * dt
            self.sub_facing = -1
        if buttons & KEY_RIGHT:
            self.sub_x += speed * dt
            self.sub_facing = 1
        if buttons & KEY_UP:
            self.sub_y -= speed * dt
        if buttons & KEY_DOWN:
            self.sub_y += speed * dt

        self.sub_x = max(1.0, min(14.5, self.sub_x))
        self.sub_y = max(3.0, min(14.0, self.sub_y))

        # Button A: Fire Torpedoes & Missiles
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_torpedoes()

        # Button B: Drop Depth Charge
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.drop_depth_charge()

    def update_projectiles(self, dt: float):
        for t in self.torpedoes:
            if not t["active"]:
                continue
            t["x"] += t["vx"] * dt
            t["y"] += t["vy"] * dt
            if t["x"] < 0.0 or t["x"] > 15.5:
                t["active"] = False

        for m in self.missiles:
            if not m["active"]:
                continue
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
            if m["y"] < 0.0 or m["x"] < 0.0 or m["x"] > 15.5:
                m["active"] = False

        for d in self.depth_charges:
            if not d["active"]:
                continue
            d["x"] += d["vx"] * dt
            d["y"] += d["vy"] * dt
            if d["y"] > 15.5:
                d["active"] = False

        self.torpedoes = [t for t in self.torpedoes if t["active"]]
        self.missiles = [m for m in self.missiles if m["active"]]
        self.depth_charges = [d for d in self.depth_charges if d["active"]]

    def update_enemies(self, dt: float):
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue

            e["x"] += e["vx"] * dt

            if e["type"] == 2:
                e["y"] += math.sin(self.state_timer * 3.0) * 0.8 * dt

            if e["x"] < -1.5:
                e["x"] = 17.0 + (i * 4.0)
                e["health"] = 1

            e["shoot_cooldown"] -= dt
            if e["shoot_cooldown"] <= 0.0 and e["x"] < 15.0:
                e["shoot_cooldown"] = 2.0
                if e["type"] == 0:
                    if len([d for d in self.depth_charges if d["active"]]) < MAX_DEPTH_CHARGES:
                        self.depth_charges.append({
                            "x": e["x"],
                            "y": e["y"] + 1.0,
                            "vx": 0.0,
                            "vy": 8.0,
                            "is_player": False,
                            "active": True,
                        })
                elif e["type"] == 1:
                    if len([t for t in self.torpedoes if t["active"]]) < MAX_TORPEDOES:
                        self.torpedoes.append({
                            "x": e["x"] - 1.0,
                            "y": e["y"],
                            "vx": -9.0,
                            "vy": 0.0,
                            "is_player": False,
                            "active": True,
                        })

    def update_boss(self, dt: float):
        self.boss_y += self.boss_vy * dt
        if self.boss_y < 5.0:
            self.boss_y = 5.0
            self.boss_vy = abs(self.boss_vy)
        elif self.boss_y > 12.0:
            self.boss_y = 12.0
            self.boss_vy = -abs(self.boss_vy)

        self.boss_shoot_cooldown -= dt
        if self.boss_shoot_cooldown <= 0.0:
            self.boss_shoot_cooldown = 1.4
            for dy in (-1, 1):
                if len([t for t in self.torpedoes if t["active"]]) < MAX_TORPEDOES:
                    self.torpedoes.append({
                        "x": self.boss_x - 1.5,
                        "y": self.boss_y + dy * 1.0,
                        "vx": -9.0,
                        "vy": dy * 2.5,
                        "is_player": False,
                        "active": True,
                    })

    def check_collisions(self):
        # 1. Torpedoes vs Enemies & Boss
        for t in self.torpedoes:
            if not t["active"] or not t["is_player"]:
                continue

            if self.boss_active:
                if abs(t["x"] - self.boss_x) < 2.0 and abs(t["y"] - self.boss_y) < 2.0:
                    t["active"] = False
                    self.boss_health -= 1
                    self.score += 50
                    if self.boss_health <= 0:
                        self.boss_active = False
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1500
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
            else:
                for e in self.enemies:
                    if not e["active"]:
                        continue
                    if abs(t["x"] - e["x"]) < 1.2 and abs(t["y"] - e["y"]) < 1.2:
                        t["active"] = False
                        e["health"] -= 1
                        if e["health"] <= 0:
                            e["active"] = False
                            self.enemies_defeated += 1
                            self.score += 150
                            if self.enemies_defeated >= 5:
                                self.boss_active = True
                                self.boss_x = 13.0
                                self.boss_y = 8.0
                                for other in self.enemies:
                                    other["active"] = False
                        break

        # 2. Anti-Air Missiles vs Surface Gunboats (type 0)
        for m in self.missiles:
            if not m["active"] or not m["is_player"]:
                continue
            for e in self.enemies:
                if not e["active"] or e["type"] != 0:
                    continue
                if abs(m["x"] - e["x"]) < 1.3 and abs(m["y"] - e["y"]) < 1.3:
                    m["active"] = False
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 250
                    if self.enemies_defeated >= 5:
                        self.boss_active = True
                        self.boss_x = 13.0
                        self.boss_y = 8.0
                        for other in self.enemies:
                            other["active"] = False
                    break

        # 3. Depth Charges vs Sea Mines / Deep Enemies
        for d in self.depth_charges:
            if not d["active"] or not d["is_player"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(d["x"] - e["x"]) < 1.2 and abs(d["y"] - e["y"]) < 1.2:
                    d["active"] = False
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 200
                    if self.enemies_defeated >= 5:
                        self.boss_active = True
                        self.boss_x = 13.0
                        self.boss_y = 8.0
                        for other in self.enemies:
                            other["active"] = False
                    break

        # 4. Enemy projectiles hit player sub
        for t in self.torpedoes:
            if not t["active"] or t["is_player"]:
                continue
            if abs(t["x"] - self.sub_x) < 0.9 and abs(t["y"] - self.sub_y) < 0.9:
                t["active"] = False
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        for d in self.depth_charges:
            if not d["active"] or d["is_player"]:
                continue
            if abs(d["x"] - self.sub_x) < 0.9 and abs(d["y"] - self.sub_y) < 0.9:
                d["active"] = False
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        # Direct enemy collision
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - self.sub_x) < 0.9 and abs(e["y"] - self.sub_y) < 0.9:
                e["active"] = False
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

        # Water background gradient & Seabed
        for y in range(16):
            for x in range(16):
                if y <= 1:
                    # Sky
                    set_pixel(x, y, 10, 20, 60)
                elif y == 2:
                    # Water surface foam
                    set_pixel(x, y, 40, 160, 220)
                elif y >= 14:
                    # Ocean floor / rocky seabed
                    set_pixel(x, y, 20, 30, 20)
                else:
                    # Deep sea blue
                    blue_depth = max(30, 120 - y * 6)
                    set_pixel(x, y, 0, 15, blue_depth)

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["type"] == 0:
                # Surface gunboat: grey/red
                set_pixel(ex, ey, 180, 50, 50)
                set_pixel(ex - 1, ey, 140, 140, 140)
            elif e["type"] == 1:
                # Enemy sub: yellow/orange
                set_pixel(ex, ey, 220, 140, 20)
                set_pixel(ex + 1, ey, 180, 80, 10)
            elif e["type"] == 2:
                # Sea mine: spiked iron
                set_pixel(ex, ey, 200, 200, 0)
                set_pixel(ex - 1, ey, 120, 120, 0)
                set_pixel(ex + 1, ey, 120, 120, 0)

        # Boss Mecha Kraken
        if self.boss_active:
            bx = int(round(self.boss_x))
            by = int(round(self.boss_y))
            for dy in (-1, 0, 1):
                for dx in (-1, 0):
                    set_pixel(bx + dx, by + dy, 180, 20, 180)
            set_pixel(bx - 1, by, 255, 50, 50)  # Core eye

        # Projectiles
        for t in self.torpedoes:
            if not t["active"]:
                continue
            tx = int(round(t["x"]))
            ty = int(round(t["y"]))
            if t["is_player"]:
                set_pixel(tx, ty, 50, 255, 255)  # Cyan player torpedo
            else:
                set_pixel(tx, ty, 255, 100, 30)   # Orange enemy torpedo

        for m in self.missiles:
            if not m["active"]:
                continue
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            set_pixel(mx, my, 255, 255, 50)

        for d in self.depth_charges:
            if not d["active"]:
                continue
            dx = int(round(d["x"]))
            dy = int(round(d["y"]))
            if d["is_player"]:
                set_pixel(dx, dy, 50, 200, 50)
            else:
                set_pixel(dx, dy, 255, 50, 50)

        # Player Granvia Submarine
        if self.state != STATE_DEAD:
            px = int(round(self.sub_x))
            py = int(round(self.sub_y))
            facing = self.sub_facing
            set_pixel(px, py, 40, 220, 100)       # Green hull
            set_pixel(px + facing, py, 200, 255, 200) # Bow
            set_pixel(px - facing, py, 20, 140, 60)   # Stern propeller
            set_pixel(px, py - 1, 60, 255, 140)       # Conning tower
        elif self.state == STATE_DEAD:
            # Explosion
            px = int(round(self.sub_x))
            py = int(round(self.sub_y))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    set_pixel(px + dx, py + dy, 255, 120, 20)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "sub_x": self.sub_x,
            "sub_y": self.sub_y,
            "boss_active": self.boss_active,
            "boss_health": self.boss_health,
            "enemies_defeated": self.enemies_defeated,
        }

