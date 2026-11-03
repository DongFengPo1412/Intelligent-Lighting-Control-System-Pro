"""
Game #189: 雷电 (Raiden - 1990 Seibu Kaihatsu)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Seibu Kaihatsu in 1990, Raiden set the golden standard for 1990s vertical military
shooters. It introduced the tactical color-crystal weapon system (Red Vulcan Spread vs Blue
Piercing Laser), homing missiles, devastating delayed-fuse thermonuclear bombs, and massive
multi-turret heavy land walkers and dreadnought tanks!

Unique Core Mechanic (Strict Zero-Redundancy):
- Dual Tactical Weapons via Color Crystals:
  * Red Crystal: Wide-angle 3-Way Vulcan Cannon for broad crowd control.
  * Blue Crystal: Ultra high-velocity concentrated Piercing Plasma Beam for single-target boss melting.
- Primary Fire & Homing Missiles (Button A): High-cadence barrage in current weapon configuration.
- Delayed Thermonuclear Mega-Bomb (Button B): Drops an explosive ordnance capsule that detonates
  after a short ignition fuse into a massive expanding shockwave, wiping all hostile bullets and
  incinerating heavy ground armor!
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
STATE_SHIP_DESTROYED = 2
STATE_GAME_OVER = 3

WEAPON_VULCAN = 0
WEAPON_LASER = 1

class Game189Raiden(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Raiden Mk-II Fighter
        self.px = 7.5
        self.py = 13.0
        self.speed = 6.5
        self.weapon_type = WEAPON_VULCAN
        self.weapon_level = 1
        self.bombs = 3

        # Player Projectiles [{x, y, vx, vy, is_laser, damage, active}]
        self.bullets: List[Dict[str, Any]] = []

        # Thermonuclear Bomb [{x, y, fuse, radius, exploding, active}]
        self.mega_bomb: Optional[Dict[str, Any]] = None

        # Floating Color Crystal {x, y, vx, vy, color: "red"|"blue", timer}
        self.crystal: Optional[Dict[str, Any]] = None

        # Enemies [{x, y, vx, vy, type: "chopper"|"tank"|"boss", hp, max_hp, alive}]
        self.enemies: List[Dict[str, Any]] = []
        self.enemy_bullets: List[Dict[str, Any]] = []
        self.enemy_shoot_timer = 1.0

        self.init()

    @property
    def game_id(self) -> int:
        return 189

    @property
    def name(self) -> str:
        return "雷电"

    @property
    def english_name(self) -> str:
        return "Raiden"

    @property
    def release_year(self) -> int:
        return 1990

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "红蓝双色战术晶石主武切换（红散弹火神炮/蓝集中聚能光束）、追踪导弹拦截与延时热核航弹全屏清场"

    def get_name(self) -> str:
        return "Raiden (1990)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.weapon_type = WEAPON_VULCAN
        self.weapon_level = 1
        self.bombs = 3
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 13.0
        self.bullets.clear()
        self.mega_bomb = None
        self.enemy_bullets.clear()
        self.enemy_shoot_timer = 1.0

        # Spawn Floating Weapon Crystal
        self.crystal = {
            "x": 8.0,
            "y": 5.0,
            "vx": 1.2,
            "vy": 0.8,
            "color": "red",
            "swap_timer": 3.0,
        }

        # Spawn Enemies Wave
        self.enemies = [
            {"x": 3.0, "y": 2.0, "vx": 1.5, "vy": 0.5, "type": "chopper", "hp": 2, "max_hp": 2, "alive": True},
            {"x": 12.0, "y": 2.0, "vx": -1.5, "vy": 0.5, "type": "chopper", "hp": 2, "max_hp": 2, "alive": True},
            {"x": 5.0, "y": 4.0, "vx": 0.0, "vy": 0.0, "type": "tank", "hp": 4, "max_hp": 4, "alive": True},
            {"x": 10.0, "y": 4.0, "vx": 0.0, "vy": 0.0, "type": "tank", "hp": 4, "max_hp": 4, "alive": True},
            {"x": 7.5, "y": 1.5, "vx": 0.8, "vy": 0.0, "type": "boss", "hp": 15 + self.stage * 5, "max_hp": 15 + self.stage * 5, "alive": True},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self.bombs = min(5, self.bombs + 1)
                self._init_stage()
            return

        if self.state == STATE_SHIP_DESTROYED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.0
                    self.bullets.clear()
                    self.enemy_bullets.clear()
                    self.mega_bomb = None
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # 1. 8-Way Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            inv = 1.0 / math.hypot(dx, dy)
            self.px += dx * inv * self.speed * dt
            self.py += dy * inv * self.speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(2.0, min(14.0, self.py))

        # 2. Fire Primary Weapons (Button A)
        if keys_pressed & KEY_A:
            if self.weapon_type == WEAPON_VULCAN:
                # 3-Way Spread
                self.bullets.append({"x": self.px, "y": self.py - 1.0, "vx": 0.0, "vy": -15.0, "is_laser": False, "damage": 1, "active": True})
                self.bullets.append({"x": self.px - 0.5, "y": self.py - 1.0, "vx": -4.0, "vy": -14.0, "is_laser": False, "damage": 1, "active": True})
                self.bullets.append({"x": self.px + 0.5, "y": self.py - 1.0, "vx": 4.0, "vy": -14.0, "is_laser": False, "damage": 1, "active": True})
            else: # WEAPON_LASER
                # Piercing High-Damage Twin Blue Laser
                self.bullets.append({"x": self.px - 0.3, "y": self.py - 1.0, "vx": 0.0, "vy": -20.0, "is_laser": True, "damage": 3, "active": True})
                self.bullets.append({"x": self.px + 0.3, "y": self.py - 1.0, "vx": 0.0, "vy": -20.0, "is_laser": True, "damage": 3, "active": True})

        # 3. Deploy Thermonuclear Mega-Bomb (Button B)
        if (keys_pressed & KEY_B) and self.bombs > 0 and (self.mega_bomb is None):
            self.bombs -= 1
            self.mega_bomb = {
                "x": self.px,
                "y": self.py - 2.0,
                "fuse": 0.45,       # 0.45s ignition fuse
                "radius": 1.0,
                "exploding": False,
                "active": True,
            }

        # 4. Update Player Bullets
        for b in self.bullets[:]:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            if not (0.0 <= b["x"] <= 15.0 and 0.0 <= b["y"] <= 15.0):
                b["active"] = False
                continue

            # Check hit enemies
            for e in self.enemies:
                if e["alive"] and math.hypot(e["x"] - b["x"], e["y"] - b["y"]) < (1.4 if e["type"] == "boss" else 0.9):
                    if not b["is_laser"]:
                        b["active"] = False
                    e["hp"] -= b["damage"]
                    if e["hp"] <= 0:
                        e["alive"] = False
                        self.score += 5000 if e["type"] == "boss" else (300 if e["type"] == "tank" else 150)
                    break

        self.bullets = [b for b in self.bullets if b["active"]]

        # 5. Update Mega-Bomb
        if self.mega_bomb is not None:
            mb = self.mega_bomb
            if not mb["exploding"]:
                mb["fuse"] -= dt
                if mb["fuse"] <= 0.0:
                    mb["exploding"] = True
                    mb["fuse"] = 0.5 # Explosion duration
            else:
                mb["fuse"] -= dt
                mb["radius"] = min(6.5, mb["radius"] + 12.0 * dt)
                # Bomb incinerates all enemy bullets on screen!
                self.enemy_bullets.clear()
                # Heavy damage to enemies within radius
                for e in self.enemies:
                    if e["alive"] and math.hypot(e["x"] - mb["x"], e["y"] - mb["y"]) < mb["radius"]:
                        e["hp"] -= 8 * dt
                        if e["hp"] <= 0:
                            e["alive"] = False
                            self.score += 5000 if e["type"] == "boss" else 300

                if mb["fuse"] <= 0.0:
                    self.mega_bomb = None

        # 6. Update Color Crystal
        if self.crystal is not None:
            c = self.crystal
            c["x"] += c["vx"] * dt
            c["y"] += c["vy"] * dt
            if c["x"] < 1.0 or c["x"] > 14.5: c["vx"] = -c["vx"]
            if c["y"] < 3.0 or c["y"] > 12.0: c["vy"] = -c["vy"]

            c["swap_timer"] -= dt
            if c["swap_timer"] <= 0.0:
                c["swap_timer"] = 3.0
                c["color"] = "blue" if c["color"] == "red" else "red"

            # Player touches crystal -> weapon upgrade/swap!
            if math.hypot(c["x"] - self.px, c["y"] - self.py) < 1.2:
                if c["color"] == "red":
                    self.weapon_type = WEAPON_VULCAN
                else:
                    self.weapon_type = WEAPON_LASER
                self.score += 500
                self.crystal = None

        # 7. Update Enemies & Enemy Bullets
        for e in self.enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["type"] == "chopper":
                if e["x"] < 1.0 or e["x"] > 14.5: e["vx"] = -e["vx"]
            elif e["type"] == "boss":
                if e["x"] < 3.0 or e["x"] > 12.0: e["vx"] = -e["vx"]

            # Enemy touches player ship
            if math.hypot(e["x"] - self.px, e["y"] - self.py) < 1.0:
                self.lives -= 1
                self.state = STATE_SHIP_DESTROYED
                self.state_timer = 1.0
                return

        # Enemy shooting
        self.enemy_shoot_timer -= dt
        if self.enemy_shoot_timer <= 0.0:
            self.enemy_shoot_timer = max(0.5, 1.4 - self.stage * 0.1)
            for e in self.enemies:
                if e["alive"]:
                    self.enemy_bullets.append({
                        "x": e["x"],
                        "y": e["y"] + 0.5,
                        "vx": 0.0,
                        "vy": 6.5,
                    })

        for eb in self.enemy_bullets[:]:
            eb["y"] += eb["vy"] * dt
            if eb["y"] > 15.5:
                self.enemy_bullets.remove(eb)
                continue

            if math.hypot(eb["x"] - self.px, eb["y"] - self.py) < 0.8:
                self.enemy_bullets.remove(eb)
                self.lives -= 1
                self.state = STATE_SHIP_DESTROYED
                self.state_timer = 1.0
                return

        # Check Boss Defeated -> Stage Clear
        boss = [e for e in self.enemies if e["type"] == "boss"][0]
        if not boss["alive"]:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 5000

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

        # 1. Background Earth Terrain & River
        for y in range(16):
            for x in range(16):
                if 6 <= x <= 9:
                    set_pixel(x, y, 20, 60, 140)   # River canal
                else:
                    set_pixel(x, y, 50, 90, 40)    # Green military base

        # 2. Enemies
        for e in self.enemies:
            if e["alive"]:
                ex, ey = int(round(e["x"])), int(round(e["y"]))
                if e["type"] == "boss":
                    # Giant Fortress Heavy Tank
                    for bx in range(ex - 2, ex + 3):
                        for by in range(ey - 1, ey + 2):
                            set_pixel(bx, by, 120, 80, 50) # Brown tank armor
                    set_pixel(ex, ey, 220, 60, 60)         # Red central reactor core
                elif e["type"] == "tank":
                    set_pixel(ex, ey, 90, 90, 90)          # Gray tank
                    set_pixel(ex, ey - 1, 140, 140, 140)   # Cannon barrel
                else: # Chopper
                    set_pixel(ex, ey, 200, 180, 50)        # Yellow recon chopper
                    set_pixel(ex - 1, ey, 140, 120, 30)
                    set_pixel(ex + 1, ey, 140, 120, 30)

        # 3. Enemy Bullets
        for eb in self.enemy_bullets:
            set_pixel(int(round(eb["x"])), int(round(eb["y"])), 255, 120, 40)

        # 4. Color Crystal (Red/Blue flashing)
        if self.crystal is not None:
            cx, cy = int(round(self.crystal["x"])), int(round(self.crystal["y"]))
            if self.crystal["color"] == "red":
                set_pixel(cx, cy, 255, 40, 40)
            else:
                set_pixel(cx, cy, 40, 140, 255)

        # 5. Mega-Bomb Shockwave
        if self.mega_bomb is not None:
            mb = self.mega_bomb
            bx, by = int(round(mb["x"])), int(round(mb["y"]))
            if not mb["exploding"]:
                set_pixel(bx, by, 255, 200, 40) # Detonator capsule
            else:
                rad = int(round(mb["radius"]))
                for dy in range(-rad, rad + 1):
                    for dx in range(-rad, rad + 1):
                        if 1.0 <= math.hypot(dx, dy) <= mb["radius"]:
                            set_pixel(bx + dx, by + dy, 255, 100, 20)

        # 6. Player Bullets
        for b in self.bullets:
            bx, by = int(round(b["x"])), int(round(b["y"]))
            if b["is_laser"]:
                set_pixel(bx, by, 60, 180, 255)     # Bright cyan piercing laser
            else:
                set_pixel(bx, by, 255, 220, 80)     # Golden vulcan shell

        # 7. Raiden Mk-II Fighter
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 220, 40, 40)          # Red supersonic fuselage
            set_pixel(px - 1, py, 200, 200, 220)    # Titanium wings
            set_pixel(px + 1, py, 200, 200, 220)
            set_pixel(px, py - 1, 255, 255, 255)    # Cockpit nose
        elif self.state == STATE_SHIP_DESTROYED:
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
            "weapon_type": "vulcan" if self.weapon_type == WEAPON_VULCAN else "laser",
            "bombs": self.bombs,
            "px": self.px,
            "py": self.py,
        }
