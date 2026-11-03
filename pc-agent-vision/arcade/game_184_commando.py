"""
Game #184: 战场之狼 (Commando - 1985 Capcom / Tokuro Fujiwara)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Capcom in 1985 and designed by Tokuro Fujiwara, Commando (Senjo no Okami) was
the definitive pioneer of the vertical run-and-gun combat genre. Controlling lone hero
Super Joe, players battle through hostile desert and jungle battlefields, lobbing grenades
over pillboxes, freeing allied POWs, and storming the enemy fortress gates.

Unique Core Mechanic (Strict Zero-Redundancy):
- 8-Way Rapid Machine Gun (Button A): Spray high-velocity rifle rounds in the current facing vector.
- Parabolic Hand Grenade Lob (Button B): Throws high-arcing grenades over obstacles (sandbags,
  trenches, and wire entanglements) to obliterate hardened pillbox nests and mortar bunkers.
- Grenade Box Resupply: Slaying enemy supply officers and scavenging crate caches restores grenade ammo.
- POW Rescue: Liberate captured allied POWs marching under armed guard for bonus points.
- Fortress Iron Gate Breach: Hold the line at the fortress entrance against rushing reinforcements
  to blast open the steel gates!
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
STATE_JOE_KILLED = 2
STATE_GAME_OVER = 3

class Game184Commando(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Super Joe
        self.px = 7.5
        self.py = 13.0
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.speed = 5.5
        self.grenades = 5

        # Bullets [{x, y, vx, vy, active}]
        self.bullets: List[Dict[str, Any]] = []

        # Grenades [{x, y, target_y, vx, vy, active}]
        self.grenade_projectiles: List[Dict[str, Any]] = []

        # Explosions [{x, y, timer, radius}]
        self.explosions: List[Dict[str, Any]] = []

        # Enemies [{x, y, vx, vy, type: "infantry"|"bunker"|"officer", hp, alive}]
        self.enemies: List[Dict[str, Any]] = []

        # POWs [{x, y, rescued}]
        self.pows: List[Dict[str, Any]] = []

        # Vertical advancement distance
        self.distance = 0.0
        self.target_distance = 180.0
        self.gate_breached = False

        self.init()

    @property
    def game_id(self) -> int:
        return 184

    @property
    def name(self) -> str:
        return "战场之狼"

    @property
    def english_name(self) -> str:
        return "Commando"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "八向冲锋枪倾泻射击、高弧度抛投破片手榴弹轰炸掩体、营救战俘与强攻敌军要塞铁闸"

    def get_name(self) -> str:
        return "Commando (1985)"

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
        self.px = 7.5
        self.py = 13.0
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.grenades = 6
        self.distance = 0.0
        self.target_distance = 160.0 + self.stage * 40.0
        self.gate_breached = False

        self.bullets.clear()
        self.grenade_projectiles.clear()
        self.explosions.clear()
        self.enemies.clear()
        self.pows.clear()

        # Seed initial enemy wave
        self._spawn_wave()

    def _spawn_wave(self):
        self.enemies = [
            {"x": 4.0, "y": 2.0, "vx": 1.2, "vy": 1.5, "type": "infantry", "hp": 1, "alive": True},
            {"x": 11.0, "y": 1.5, "vx": -1.2, "vy": 1.5, "type": "infantry", "hp": 1, "alive": True},
            {"x": 7.5, "y": 4.0, "vx": 0.0, "vy": 0.0, "type": "bunker", "hp": 2, "alive": True},
            {"x": 13.0, "y": 6.0, "vx": -1.5, "vy": 0.5, "type": "officer", "hp": 1, "alive": True},
        ]
        self.pows = [
            {"x": 3.0, "y": 5.0, "rescued": False},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_JOE_KILLED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.0
                    self.bullets.clear()
                    self.grenade_projectiles.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # 8-Way Movement & Facing
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            inv = 1.0 / math.hypot(dx, dy)
            self.facing_x = dx * inv
            self.facing_y = dy * inv
            self.px += dx * self.speed * dt
            self.py += dy * self.speed * dt

        # Forward scrolling upwards
        if self.distance < self.target_distance and self.py < 8.0:
            scroll = 8.0 - self.py
            self.py = 8.0
            self.distance += scroll
            # Shift enemies, pows downwards
            for e in self.enemies: e["y"] += scroll
            for p in self.pows: p["y"] += scroll

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(2.0, min(14.0, self.py))

        # Fire Machine Gun (Button A)
        if keys_pressed & KEY_A:
            b_spd = 16.0
            self.bullets.append({
                "x": self.px,
                "y": self.py,
                "vx": self.facing_x * b_spd,
                "vy": self.facing_y * b_spd,
                "active": True,
            })

        # Lob Grenade (Button B)
        if (keys_pressed & KEY_B) and self.grenades > 0:
            self.grenades -= 1
            # Lob grenade 4.0 units ahead in facing vector
            target_x = self.px + self.facing_x * 4.0
            target_y = self.py + self.facing_y * 4.0
            self.grenade_projectiles.append({
                "x": self.px,
                "y": self.py,
                "tx": target_x,
                "ty": target_y,
                "active": True,
                "timer": 0.4, # 0.4s air travel time
            })

        # Update Machine Gun Bullets
        for b in self.bullets[:]:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            if not (0.0 <= b["x"] <= 15.0 and 0.0 <= b["y"] <= 15.0):
                b["active"] = False
                continue

            # Hit enemies
            for e in self.enemies:
                if e["alive"] and math.hypot(e["x"] - b["x"], e["y"] - b["y"]) < 0.9:
                    b["active"] = False
                    if e["type"] != "bunker": # Machine gun bullets bounce off hardened bunkers!
                        e["alive"] = False
                        self.score += 100
                        if e["type"] == "officer":
                            self.grenades = min(8, self.grenades + 4) # Scavenge crate!
                            self.score += 300
                    break

        self.bullets = [b for b in self.bullets if b["active"]]

        # Update Grenades
        for g in self.grenade_projectiles[:]:
            if not g["active"]:
                continue
            g["timer"] -= dt
            # Move towards target
            g["x"] += (g["tx"] - g["x"]) * 8.0 * dt
            g["y"] += (g["ty"] - g["y"]) * 8.0 * dt

            if g["timer"] <= 0.0:
                g["active"] = False
                # Detonate grenade explosion!
                self.explosions.append({"x": g["tx"], "y": g["ty"], "timer": 0.3, "radius": 1.8})
                # Check explosion damage on all nearby enemies (including bunkers!)
                for e in self.enemies:
                    if e["alive"] and math.hypot(e["x"] - g["tx"], e["y"] - g["ty"]) < 1.8:
                        e["hp"] -= 2
                        if e["hp"] <= 0:
                            e["alive"] = False
                            self.score += 300 if e["type"] == "bunker" else 150

                # Check hit on Fortress Iron Gate
                if self.distance >= self.target_distance and math.hypot(7.5 - g["tx"], 1.5 - g["ty"]) < 2.5:
                    self.gate_breached = True
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 3000
                    return

        self.grenade_projectiles = [g for g in self.grenade_projectiles if g["active"]]

        # Update Explosions
        for ex in self.explosions[:]:
            ex["timer"] -= dt
            if ex["timer"] <= 0.0:
                self.explosions.remove(ex)

        # Rescue POWs
        for p in self.pows:
            if not p["rescued"] and math.hypot(p["x"] - self.px, p["y"] - self.py) < 1.0:
                p["rescued"] = True
                self.score += 500

        # Update Enemies AI
        for e in self.enemies:
            if not e["alive"]:
                continue
            if e["type"] != "bunker":
                e["x"] += e["vx"] * dt
                e["y"] += e["vy"] * dt

            # Enemy touches Joe
            if math.hypot(e["x"] - self.px, e["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_JOE_KILLED
                self.state_timer = 1.0
                return

        # Wave Respawn
        if len([e for e in self.enemies if e["alive"]]) == 0:
            if self.distance < self.target_distance:
                self._spawn_wave()

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

        # 1. Desert Battlefield Ground
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 160, 130, 80) # Sand dune ground

        # 2. Fortress Iron Gate at top (if arrived)
        if self.distance >= self.target_distance:
            for x in range(4, 12):
                set_pixel(x, 1, 80, 80, 90) # Steel battlements
                set_pixel(x, 2, 140, 140, 150) # Iron gate doors
            set_pixel(4, 0, 180, 40, 40) # Fortress red banners
            set_pixel(11, 0, 180, 40, 40)

        # 3. POWs
        for p in self.pows:
            if not p["rescued"]:
                set_pixel(int(round(p["x"])), int(round(p["y"])), 255, 255, 255) # White shirt POW

        # 4. Enemies & Bunkers
        for e in self.enemies:
            if e["alive"]:
                ex, ey = int(round(e["x"])), int(round(e["y"]))
                if e["type"] == "bunker":
                    set_pixel(ex, ey, 90, 70, 50)     # Concrete pillbox
                    set_pixel(ex - 1, ey, 70, 50, 40)
                    set_pixel(ex + 1, ey, 70, 50, 40)
                    set_pixel(ex, ey - 1, 20, 20, 20) # Gun port
                elif e["type"] == "officer":
                    set_pixel(ex, ey, 255, 200, 0)    # Yellow officer
                else:
                    set_pixel(ex, ey, 80, 140, 60)    # Green infantry

        # 5. Bullets
        for b in self.bullets:
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 140)

        # 6. Grenades
        for g in self.grenade_projectiles:
            set_pixel(int(round(g["x"])), int(round(g["y"])), 40, 220, 40) # Green grenade

        # 7. Explosions
        for ex in self.explosions:
            cx, cy = int(round(ex["x"])), int(round(ex["y"]))
            set_pixel(cx, cy, 255, 255, 80)
            set_pixel(cx - 1, cy, 255, 100, 20)
            set_pixel(cx + 1, cy, 255, 100, 20)
            set_pixel(cx, cy - 1, 255, 100, 20)
            set_pixel(cx, cy + 1, 255, 100, 20)

        # 8. Super Joe
        jx = int(round(self.px))
        jy = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(jx, jy, 40, 100, 220)       # Blue commando vest
            set_pixel(jx, jy - 1, 255, 60, 40)    # Red bandana
            set_pixel(jx + int(self.facing_x), jy + int(self.facing_y), 220, 220, 240) # Gun muzzle
        elif self.state == STATE_JOE_KILLED:
            set_pixel(jx, jy, 255, 60, 0)

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
            "py": self.py,
            "grenades": self.grenades,
            "distance": self.distance,
            "gate_breached": self.gate_breached,
        }

