"""
Game #187: 侵略者归来 (Return of the Invaders - 1985 Taito / UPL)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Taito in 1985 (developed with UPL), Return of the Invaders was the official
revolutionary sequel that transformed the original fixed-shooter pioneer. It introduced
cell-splitting biological invaders (mitosis), diving flanking swarmers, mothership tractor
beams, and the iconic arched energy boomerang weapon that damages enemies on both its
ascent and curved descent!

Unique Core Mechanic (Strict Zero-Redundancy):
- Dual Rapid Laser Blasters (Button A): High-cadence twin lasers firing straight upwards.
- Arched Boomerang Cutter (Button B): Launches a whirling energy disc that arcs upwards to
  mid-screen, then curves backward towards the player's current position, cutting through
  invaders along both forward and return paths!
- Invader Cellular Mitosis: Certain armored invaders divide into two smaller, hyper-fast
  flanking mini-aliens when struck by primary weapons.
- Mothership UFO EMP Burst: Mothership traverses the high heavens; blasting it detonates
  an electromagnetic pulse that neutralizes all alien missiles on screen!
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

class Game187ReturnOfTheInvaders(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Defender Ship
        self.px = 7.5
        self.py = 14.0
        self.speed = 7.0

        # Lasers [{x, y, vy, active}]
        self.lasers: List[Dict[str, Any]] = []

        # Boomerang Cutter {x, y, vx, vy, state: "ascending"|"returning", active}
        self.boomerang: Optional[Dict[str, Any]] = None

        # Aliens [{x, y, vx, vy, type: "normal"|"splitter"|"mini", alive, hp}]
        self.aliens: List[Dict[str, Any]] = []
        self.alien_dir = 1.0
        self.alien_drop_timer = 0.0

        # Mothership UFO
        self.ufo_x = -2.0
        self.ufo_active = False
        self.ufo_timer = 5.0

        # Alien Bombs [{x, y, vy}]
        self.alien_bombs: List[Dict[str, Any]] = []
        self.bomb_timer = 0.8

        self.init()

    @property
    def game_id(self) -> int:
        return 187

    @property
    def name(self) -> str:
        return "侵略者归来"

    @property
    def english_name(self) -> str:
        return "Return of the Invaders"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "外星侵略者细胞分裂增殖、弧形回旋光镖双程贯通、引力光束母舰核爆与集束能量反攻"

    def get_name(self) -> str:
        return "Return of the Invaders (1985)"

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
        self.py = 14.0
        self.lasers.clear()
        self.boomerang = None
        self.alien_bombs.clear()
        self.ufo_active = False
        self.ufo_timer = 5.0
        self.alien_dir = 1.0

        # Spawn Invader Formation
        self.aliens.clear()
        # Row 1: Splitters
        for col in range(5):
            self.aliens.append({
                "x": 3.0 + col * 2.2,
                "y": 3.0,
                "vx": 1.2,
                "vy": 0.0,
                "type": "splitter",
                "hp": 2,
                "alive": True,
            })
        # Row 2: Standard Invaders
        for col in range(6):
            self.aliens.append({
                "x": 2.0 + col * 2.2,
                "y": 5.0,
                "vx": 1.2,
                "vy": 0.0,
                "type": "normal",
                "hp": 1,
                "alive": True,
            })

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_SHIP_DESTROYED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.lasers.clear()
                    self.boomerang = None
                    self.alien_bombs.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # 1. Player Movement (Left/Right)
        if keys_down & KEY_LEFT:
            self.px = max(1.0, self.px - self.speed * dt)
        if keys_down & KEY_RIGHT:
            self.px = min(14.0, self.px + self.speed * dt)

        # 2. Fire Primary Lasers (Button A)
        if keys_pressed & KEY_A:
            if len(self.lasers) < 3:
                self.lasers.append({"x": self.px, "y": self.py - 1.0, "vy": -16.0, "active": True})

        # 3. Launch Boomerang Cutter (Button B)
        if (keys_pressed & KEY_B) and (self.boomerang is None):
            self.boomerang = {
                "x": self.px,
                "y": self.py - 1.0,
                "vx": 0.0,
                "vy": -12.0,
                "state": "ascending",
                "active": True,
            }

        # 4. Update Lasers
        for l in self.lasers[:]:
            l["y"] += l["vy"] * dt
            if l["y"] < 0.0:
                l["active"] = False
                continue

            # Check hit against aliens
            for a in self.aliens:
                if a["alive"] and math.hypot(a["x"] - l["x"], a["y"] - l["y"]) < 0.9:
                    l["active"] = False
                    a["hp"] -= 1
                    if a["hp"] <= 0:
                        a["alive"] = False
                        self.score += 150 if a["type"] == "splitter" else 80
                        # Trigger Mitosis if splitter
                        if a["type"] == "splitter":
                            self._split_alien(a["x"], a["y"])
                    break

            # Hit UFO
            if self.ufo_active and math.hypot(self.ufo_x - l["x"], 1.0 - l["y"]) < 1.2:
                l["active"] = False
                self.ufo_active = False
                self.score += 1000
                # Detonate EMP: clear all enemy bombs!
                self.alien_bombs.clear()

        self.lasers = [l for l in self.lasers if l["active"]]

        # 5. Update Boomerang Cutter
        if self.boomerang is not None:
            b = self.boomerang
            if b["state"] == "ascending":
                b["y"] += b["vy"] * dt
                # Peak reached around y = 4.0 -> transition to returning
                if b["y"] <= 4.0:
                    b["state"] = "returning"
            else:
                # Curve back towards player's current X position
                dx = self.px - b["x"]
                b["x"] += dx * 6.0 * dt
                b["y"] += 10.0 * dt # Descent velocity

                # Catch boomerang
                if b["y"] >= self.py:
                    self.boomerang = None

            if self.boomerang is not None:
                # Boomerang cuts through all aliens it touches!
                for a in self.aliens:
                    if a["alive"] and math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 1.0:
                        a["hp"] -= 2 # Powerful cutter damage
                        if a["hp"] <= 0:
                            a["alive"] = False
                            self.score += 150 if a["type"] == "splitter" else 80
                            if a["type"] == "splitter":
                                self._split_alien(a["x"], a["y"])

                # Hit UFO
                if self.ufo_active and math.hypot(self.ufo_x - b["x"], 1.0 - b["y"]) < 1.4:
                    self.ufo_active = False
                    self.score += 1000
                    self.alien_bombs.clear()

        # 6. Update Aliens Formation & March
        hit_edge = False
        alive_aliens = [a for a in self.aliens if a["alive"]]
        if len(alive_aliens) == 0:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 1.8
            self.score += 2000
            return

        inv_speed = 1.0 + (11.0 - len(alive_aliens)) * 0.15
        for a in alive_aliens:
            if a["type"] == "mini":
                # Minis flank rapidly
                a["x"] += a["vx"] * dt
                if a["x"] < 1.0 or a["x"] > 14.5:
                    a["vx"] = -a["vx"]
            else:
                a["x"] += self.alien_dir * inv_speed * dt
                if (self.alien_dir > 0 and a["x"] >= 14.0) or (self.alien_dir < 0 and a["x"] <= 1.0):
                    hit_edge = True

        if hit_edge:
            self.alien_dir = -self.alien_dir
            for a in alive_aliens:
                if a["type"] != "mini":
                    a["y"] += 0.8

        # Check alien invasion reached bottom
        for a in alive_aliens:
            if a["y"] >= 13.5:
                self.lives = 0
                self.state = STATE_GAME_OVER
                return

        # 7. Alien Bombs Dropping
        self.bomb_timer -= dt
        if self.bomb_timer <= 0.0 and len(alive_aliens) > 0:
            self.bomb_timer = max(0.4, 1.2 - self.stage * 0.1)
            shooter = alive_aliens[len(alive_aliens) // 2]
            self.alien_bombs.append({"x": shooter["x"], "y": shooter["y"] + 0.5, "vy": 7.0})

        for bmb in self.alien_bombs[:]:
            bmb["y"] += bmb["vy"] * dt
            if bmb["y"] > 15.5:
                self.alien_bombs.remove(bmb)
                continue

            # Hit player
            if math.hypot(bmb["x"] - self.px, bmb["y"] - self.py) < 0.8:
                self.alien_bombs.remove(bmb)
                self.lives -= 1
                self.state = STATE_SHIP_DESTROYED
                self.state_timer = 1.0
                return

        # 8. Mothership UFO
        if not self.ufo_active:
            self.ufo_timer -= dt
            if self.ufo_timer <= 0.0:
                self.ufo_active = True
                self.ufo_x = 0.0
                self.ufo_timer = 8.0
        else:
            self.ufo_x += 4.5 * dt
            if self.ufo_x > 16.0:
                self.ufo_active = False

    def _split_alien(self, x: float, y: float):
        # Cell mitosis produces two mini-invaders
        self.aliens.append({
            "x": max(1.0, x - 0.8),
            "y": y,
            "vx": -4.0,
            "vy": 0.0,
            "type": "mini",
            "hp": 1,
            "alive": True,
        })
        self.aliens.append({
            "x": min(14.0, x + 0.8),
            "y": y,
            "vx": 4.0,
            "vy": 0.0,
            "type": "mini",
            "hp": 1,
            "alive": True,
        })

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

        # 1. Mothership UFO at top (y = 1)
        if self.ufo_active:
            ux = int(round(self.ufo_x))
            set_pixel(ux, 1, 255, 60, 60)
            set_pixel(ux - 1, 1, 200, 30, 30)
            set_pixel(ux + 1, 1, 200, 30, 30)
            set_pixel(ux, 0, 255, 255, 100)

        # 2. Aliens & Mitosis Mini-Aliens
        for a in self.aliens:
            if a["alive"]:
                ax, ay = int(round(a["x"])), int(round(a["y"]))
                if a["type"] == "splitter":
                    set_pixel(ax, ay, 220, 50, 220)       # Purple mitotic alien
                    set_pixel(ax - 1, ay, 180, 40, 180)
                    set_pixel(ax + 1, ay, 180, 40, 180)
                elif a["type"] == "mini":
                    set_pixel(ax, ay, 50, 255, 200)       # Cyan fast mini-alien
                else:
                    set_pixel(ax, ay, 50, 220, 50)        # Green standard invader
                    set_pixel(ax - 1, ay, 40, 160, 40)
                    set_pixel(ax + 1, ay, 40, 160, 40)

        # 3. Alien Bombs
        for bmb in self.alien_bombs:
            set_pixel(int(round(bmb["x"])), int(round(bmb["y"])), 255, 200, 40)

        # 4. Player Lasers
        for l in self.lasers:
            set_pixel(int(round(l["x"])), int(round(l["y"])), 100, 220, 255)

        # 5. Boomerang Cutter
        if self.boomerang is not None:
            bx, by = int(round(self.boomerang["x"])), int(round(self.boomerang["y"]))
            set_pixel(bx, by, 255, 255, 50) # Bright yellow whirling cutter
            set_pixel(bx - 1, by, 255, 140, 0)
            set_pixel(bx + 1, by, 255, 140, 0)

        # 6. Defender Ship
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 255, 255, 255)       # White ship center
            set_pixel(px - 1, py, 40, 120, 240)    # Blue wings
            set_pixel(px + 1, py, 40, 120, 240)
            set_pixel(px, py - 1, 255, 100, 50)    # Gun barrel
        elif self.state == STATE_SHIP_DESTROYED:
            set_pixel(px, py, 255, 50, 0)

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
            "lasers_count": len(self.lasers),
            "boomerang_active": self.boomerang is not None,
            "alive_aliens": len([a for a in self.aliens if a["alive"]]),
            "ufo_active": self.ufo_active,
        }
