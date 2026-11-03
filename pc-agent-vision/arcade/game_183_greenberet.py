"""
Game #183: 绿色兵团 (Green Beret / Rush'n Attack - 1985 Konami)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Konami in 1985, Green Beret (Rush'n Attack) was a legendary side-scrolling
military combat arcade action game. A lone special forces commando infiltrates a hostile
missile base armed only with a tactical combat knife, scavenging limited-use bazookas
from high-ranking enemy officers to destroy the intercontinental missile silo!

Unique Core Mechanic (Strict Zero-Redundancy):
- Tactical Combat Knife Thrust (Button A): High-speed, close-quarters stabbing attack that
  neutralizes charging foot soldiers, leaping martial artists, and attack hounds.
- Scavenged Special Ordnance (Button B): Slaying rare red-uniformed enemy officers drops
  an RPG rocket launcher with 3 piercing explosive rounds.
- Stance Modulation (Prone Ducking & Leaping): Down key drops into a low prone crawl to slip
  under hostile high rifle fire.
- Base Silo Sabotage: Infiltrate forward across enemy patrol waves to demolish the missile launcher.
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
STATE_SOLDIER_KILLED = 2
STATE_GAME_OVER = 3

class Game183GreenBeret(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Commando
        self.px = 3.0
        self.py = 13.0
        self.facing = 1 # 1: right, -1: left
        self.speed = 6.0
        self.is_prone = False
        self.knife_timer = 0.0
        self.rpg_ammo = 0

        # RPG Rockets [{x, y, vx, active}]
        self.rockets: List[Dict[str, Any]] = []

        # Patrol Enemies [{x, y, vx, is_officer, alive}]
        self.enemies: List[Dict[str, Any]] = []

        # Paratroopers [{x, y, vy, alive}]
        self.paratroopers: List[Dict[str, Any]] = []

        # Mission distance to missile silo
        self.distance = 0.0
        self.target_distance = 180.0
        self.silo_hp = 4

        self.init()

    @property
    def game_id(self) -> int:
        return 183

    @property
    def name(self) -> str:
        return "绿色兵团"

    @property
    def english_name(self) -> str:
        return "Green Beret"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "特种兵近身快刀突刺、击杀红衣军官缴获火箭筒、卧倒伏地闪避流弹与摧毁导弹发射井"

    def get_name(self) -> str:
        return "Green Beret (1985)"

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
        self.px = 3.0
        self.py = 13.0
        self.facing = 1
        self.is_prone = False
        self.knife_timer = 0.0
        self.rpg_ammo = 1 # 1 start RPG rocket
        self.distance = 0.0
        self.target_distance = 160.0 + self.stage * 40.0
        self.silo_hp = 3 + self.stage

        self.rockets.clear()
        self.enemies.clear()
        self.paratroopers.clear()

        # Seed initial enemy wave
        self._spawn_enemy_wave()

    def _spawn_enemy_wave(self):
        # Foot soldiers & 1 red officer
        self.enemies = [
            {"x": 14.0, "y": 13.0, "vx": -3.5, "is_officer": False, "alive": True},
            {"x": 19.0, "y": 13.0, "vx": -4.0, "is_officer": True, "alive": True},
            {"x": 24.0, "y": 13.0, "vx": -3.2, "is_officer": False, "alive": True},
        ]
        self.paratroopers = [
            {"x": 9.0, "y": 1.0, "vy": 2.0, "alive": True},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_SOLDIER_KILLED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 3.0
                    self.is_prone = False
                    self.knife_timer = 0.0
                    self.rockets.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Prone crawl (Down key held)
        self.is_prone = bool(keys_down & KEY_DOWN)

        # Movement
        dx = 0.0
        if not self.is_prone:
            if keys_down & KEY_LEFT:  dx -= 1.0; self.facing = -1
            if keys_down & KEY_RIGHT: dx += 1.0; self.facing = 1

        self.px += dx * self.speed * dt
        # Forward scroll advances mission distance until silo reached
        if self.distance < self.target_distance and self.px > 8.0:
            scroll = self.px - 8.0
            self.px = 8.0
            self.distance += scroll
            # Shift all enemies left with scrolling
            for e in self.enemies: e["x"] -= scroll
            for p in self.paratroopers: p["x"] -= scroll
        self.px = max(1.0, min(14.0, self.px))

        # Knife thrust (Button A)
        if self.knife_timer > 0.0:
            self.knife_timer -= dt

        if keys_pressed & KEY_A:
            self.knife_timer = 0.2
            # Knife hitbox directly in front of commando
            kx = self.px + self.facing * 1.2
            ky = self.py if not self.is_prone else (self.py + 0.5)

            for e in self.enemies:
                if e["alive"] and math.hypot(e["x"] - kx, e["y"] - ky) < 1.3:
                    e["alive"] = False
                    self.score += 100
                    if e["is_officer"]:
                        self.rpg_ammo = min(3, self.rpg_ammo + 3) # Scavenge RPG!
                        self.score += 400

            for p in self.paratroopers:
                if p["alive"] and math.hypot(p["x"] - kx, p["y"] - ky) < 1.3:
                    p["alive"] = False
                    self.score += 200

            # Knife hit silo at base
            if self.distance >= self.target_distance and math.hypot(14.0 - kx, 13.0 - ky) < 1.5:
                self.silo_hp -= 1
                self.score += 200
                if self.silo_hp <= 0:
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 3000
                    return

        # Fire Scavenged RPG (Button B)
        if (keys_pressed & KEY_B) and self.rpg_ammo > 0:
            self.rpg_ammo -= 1
            self.rockets.append({
                "x": self.px + self.facing * 1.0,
                "y": self.py - 0.2,
                "vx": self.facing * 14.0,
                "active": True,
            })

        # Update Rockets
        for r in self.rockets[:]:
            if not r["active"]:
                continue
            r["x"] += r["vx"] * dt
            if r["x"] < 0.0 or r["x"] > 16.0:
                r["active"] = False
                continue

            # Blow up enemies along path
            for e in self.enemies:
                if e["alive"] and math.hypot(e["x"] - r["x"], e["y"] - r["y"]) < 1.4:
                    e["alive"] = False
                    self.score += 150

            # Rocket hit silo
            if self.distance >= self.target_distance and math.hypot(14.0 - r["x"], 13.0 - r["y"]) < 1.5:
                r["active"] = False
                self.silo_hp -= 2
                self.score += 400
                if self.silo_hp <= 0:
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 3000
                    return

        # Update Enemies AI
        for e in self.enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"] * dt
            # Touch commando
            if math.hypot(e["x"] - self.px, e["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_SOLDIER_KILLED
                self.state_timer = 1.0
                return

        # Update Paratroopers
        for p in self.paratroopers:
            if not p["alive"]:
                continue
            p["y"] += p["vy"] * dt
            if p["y"] >= 13.0:
                p["y"] = 13.0
                # Becomes foot soldier running left
                self.enemies.append({
                    "x": p["x"],
                    "y": 13.0,
                    "vx": -3.5,
                    "is_officer": False,
                    "alive": True,
                })
                p["alive"] = False

            if math.hypot(p["x"] - self.px, p["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_SOLDIER_KILLED
                self.state_timer = 1.0
                return

        # Respawn waves as commando progresses
        if len([e for e in self.enemies if e["alive"]]) == 0:
            if self.distance < self.target_distance:
                self._spawn_enemy_wave()

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

        # 1. Base Ground (y=14..15)
        for x in range(16):
            set_pixel(x, 14, 50, 50, 60) # Concrete tarmac
            set_pixel(x, 15, 30, 30, 40)

        # 2. Missile Silo at end of track
        if self.distance >= self.target_distance:
            for y in range(8, 14):
                set_pixel(14, y, 220, 220, 230) # White ICBM rocket
                set_pixel(13, y, 160, 40, 40)   # Red gantry tower
                set_pixel(15, y, 160, 40, 40)

        # 3. Enemies
        for e in self.enemies:
            if e["alive"]:
                ex, ey = int(round(e["x"])), int(round(e["y"]))
                if e["is_officer"]:
                    set_pixel(ex, ey, 255, 30, 30) # Red uniform officer
                    set_pixel(ex, ey - 1, 255, 200, 140)
                else:
                    set_pixel(ex, ey, 140, 140, 150) # Gray uniform infantry
                    set_pixel(ex, ey - 1, 200, 160, 120)

        # 4. Paratroopers
        for p in self.paratroopers:
            if p["alive"]:
                px, py = int(round(p["x"])), int(round(p["y"]))
                set_pixel(px, py, 140, 140, 150)
                set_pixel(px - 1, py - 1, 240, 240, 240) # Parachute canopy
                set_pixel(px, py - 1, 240, 240, 240)
                set_pixel(px + 1, py - 1, 240, 240, 240)

        # 5. RPG Rockets
        for r in self.rockets:
            if r["active"]:
                rx, ry = int(round(r["x"])), int(round(r["y"]))
                set_pixel(rx, ry, 255, 220, 40) # Golden rocket flame
                set_pixel(rx - int(self.facing), ry, 255, 80, 0)

        # 6. Green Beret Commando
        cx = int(round(self.px))
        cy = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.is_prone:
                # Prone crawl
                set_pixel(cx, cy, 40, 140, 40) # Camo green suit
                set_pixel(cx + self.facing, cy, 255, 200, 140) # Face
                if self.knife_timer > 0.0:
                    set_pixel(cx + self.facing * 2, cy, 240, 240, 255) # Silver knife blade
            else:
                set_pixel(cx, cy, 30, 120, 40) # Green trousers
                set_pixel(cx, cy - 1, 50, 160, 50) # Camo jacket
                set_pixel(cx, cy - 2, 20, 180, 20) # Green Beret cap
                if self.knife_timer > 0.0:
                    set_pixel(cx + self.facing, cy - 1, 240, 240, 255) # Extended knife
        elif self.state == STATE_SOLDIER_KILLED:
            set_pixel(cx, cy, 255, 60, 0)

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
            "px": self.px,
            "distance": self.distance,
            "rpg_ammo": self.rpg_ammo,
            "is_prone": self.is_prone,
            "silo_hp": self.silo_hp,
        }
