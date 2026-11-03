"""
Game #167: 水晶城堡 (Crystal Castles - 1983 Atari / Franz Lanzinger)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Atari in 1983, Crystal Castles pioneered 2.5D pseudo-isometric stepped platforming.
Piloting Bentley Bear through Escher-like castle tiers, players collect sparkling gems,
jump over or crush Gem Eaters, devour magic honey pots to banish Berthilda the Witch,
and navigate hidden castle archway warps.

Unique Mechanic (Strict Zero-Redundancy):
- Stepped Isometric Gem Gleaning: Ascend 3D-styled terraces to harvest every gem (last gem bonus).
- Jumping Stun on Gem Eaters: Jump over or stomp crawling larvae that consume uncollected gems.
- Magic Honey Pot Invulnerability: Devour honey to turn invulnerable and banish Berthilda the Witch.
- Castle Elevation Warps: Archways that instantly transport Bentley between castle summit and courtyard.
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
STATE_BENTLEY_DIED = 2
STATE_GAME_OVER = 3

class Game167CrystalCastles(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.castle = 1
        self.state_timer = 0.0

        # Bentley Bear state
        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 4.8
        self.is_jumping = False
        self.invulnerable_timer = 0.0

        # Stepped Castle Platforms: set of (x, y)
        self.platforms = set()
        self.stairs = set()

        # Gems: list of {x, y, collected}
        self.gems: List[Dict[str, Any]] = []

        # Honey Pot: {x, y, active}
        self.honey_pot = {"x": 13.0, "y": 2.0, "active": True}

        # Gem Eater: {x, y, vx, alive}
        self.gem_eater = {"x": 6.0, "y": 9.0, "vx": 1.8, "alive": True}

        # Berthilda the Witch: {x, y, vx, alive}
        self.witch = {"x": 12.0, "y": 4.0, "vx": -2.2, "alive": True}

        self.init()

    @property
    def game_id(self) -> int:
        return 167

    @property
    def name(self) -> str:
        return "水晶城堡"

    @property
    def english_name(self) -> str:
        return "Crystal Castles"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "等轴立体阶梯城堡宝石采集、飞跃踩踏食晶毛虫、拾取魔法蜂蜜罐暴击女巫与拱门跃迁"

    def get_name(self) -> str:
        return "Crystal Castles (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.castle = 1
        self._init_castle()

    def _init_castle(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.is_jumping = False
        self.invulnerable_timer = 0.0

        self.platforms.clear()
        self.stairs.clear()
        self.gems.clear()

        # Castle Platforms:
        # Tier 0 (Ground): y=14, x=0..15
        for x in range(16):
            self.platforms.add((x, 14))

        # Tier 1 (Mid Terrace): y=10, x=3..12
        for x in range(3, 13):
            self.platforms.add((x, 10))

        # Tier 2 (Upper Balcony): y=6, x=5..14
        for x in range(5, 15):
            self.platforms.add((x, 6))

        # Tier 3 (Summit): y=2, x=2..8
        for x in range(2, 9):
            self.platforms.add((x, 2))

        # Stairs / Ramps connecting tiers
        for y in range(11, 14): self.stairs.add((3, y))
        for y in range(7, 10):  self.stairs.add((11, y))
        for y in range(3, 6):   self.stairs.add((5, y))

        # Scatter 12 Gems
        gem_coords = [
            (2, 13), (6, 13), (10, 13), (14, 13),
            (4, 9), (7, 9), (10, 9),
            (6, 5), (9, 5), (13, 5),
            (3, 1), (7, 1)
        ]
        for (gx, gy) in gem_coords:
            self.gems.append({"x": float(gx), "y": float(gy), "collected": False})

        # Honey Pot at Summit
        self.honey_pot = {"x": 8.0, "y": 1.0, "active": True}

        # Gem Eater on Tier 1
        self.gem_eater = {"x": 5.0, "y": 9.0, "vx": 1.8, "alive": True}

        # Berthilda the Witch on Tier 2
        self.witch = {"x": 12.0, "y": 5.0, "vx": -2.2, "alive": True}

    def remaining_gems_count(self) -> int:
        return sum(1 for g in self.gems if not g["collected"])

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.castle += 1
                self._init_castle()
            return

        if self.state == STATE_BENTLEY_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 2.0
                    self.py = 13.0
                    self.is_jumping = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.invulnerable_timer > 0.0:
            self.invulnerable_timer -= dt

        # Player Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            len_d = math.hypot(dx, dy)
            self.px += (dx / len_d) * self.speed * dt
            self.py += (dy / len_d) * self.speed * dt

        self.px = max(1.0, min(14.5, self.px))
        self.py = max(1.0, min(14.0, self.py))

        # Jump action
        if (keys_pressed & KEY_A) and not self.is_jumping:
            self.is_jumping = True
            self.vy = -6.0

        if self.is_jumping:
            self.py += self.vy * dt
            self.vy += 18.0 * dt
            if self.vy > 6.0:
                self.is_jumping = False
                self.vy = 0.0

        # Archway Warp passage between (1, 13) and (2, 2)
        if (keys_pressed & KEY_B):
            if abs(self.px - 1.5) < 1.0 and abs(self.py - 13.0) < 1.0:
                self.px = 3.0; self.py = 1.5
            elif abs(self.px - 3.0) < 1.0 and abs(self.py - 1.5) < 1.0:
                self.px = 1.5; self.py = 13.0

        # Collect Gems
        for g in self.gems:
            if not g["collected"] and math.hypot(g["x"] - self.px, g["y"] - self.py) < 0.9:
                g["collected"] = True
                rem = self.remaining_gems_count()
                if rem == 0:
                    self.score += 500 # Last gem bonus!
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 2000
                    return
                else:
                    self.score += 100

        # Collect Honey Pot
        if self.honey_pot["active"] and math.hypot(self.honey_pot["x"] - self.px, self.honey_pot["y"] - self.py) < 1.0:
            self.honey_pot["active"] = False
            self.invulnerable_timer = 4.0
            self.score += 500

        # Gem Eater AI
        if self.gem_eater["alive"]:
            self.gem_eater["x"] += self.gem_eater["vx"] * dt
            if self.gem_eater["x"] <= 3.0 or self.gem_eater["x"] >= 12.0:
                self.gem_eater["vx"] = -self.gem_eater["vx"]

            # Gem Eater devours gems
            for g in self.gems:
                if not g["collected"] and math.hypot(g["x"] - self.gem_eater["x"], g["y"] - self.gem_eater["y"]) < 0.8:
                    g["collected"] = True

            # Bentley interacting with Gem Eater
            if math.hypot(self.gem_eater["x"] - self.px, self.gem_eater["y"] - self.py) < 1.0:
                if self.is_jumping or self.invulnerable_timer > 0.0:
                    # Jumped on/crushed gem eater!
                    self.gem_eater["alive"] = False
                    self.score += 500
                else:
                    self.lives -= 1
                    self.state = STATE_BENTLEY_DIED
                    self.state_timer = 1.0
                    return

        # Berthilda the Witch AI
        if self.witch["alive"]:
            self.witch["x"] += self.witch["vx"] * dt
            if self.witch["x"] <= 4.0 or self.witch["x"] >= 14.0:
                self.witch["vx"] = -self.witch["vx"]

            # Bentley interacting with Witch
            if math.hypot(self.witch["x"] - self.px, self.witch["y"] - self.py) < 1.0:
                if self.invulnerable_timer > 0.0:
                    # Banish the Witch with magic honey pot power!
                    self.witch["alive"] = False
                    self.score += 3000
                else:
                    self.lives -= 1
                    self.state = STATE_BENTLEY_DIED
                    self.state_timer = 1.0
                    return

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

        # 1. Stepped Castle Platforms & Stairs
        for (px, py) in self.platforms:
            set_pixel(px, py, 60, 90, 180) # Castle blue stones
        for (sx, sy) in self.stairs:
            set_pixel(sx, sy, 100, 130, 220) # Stairway highlights

        # 2. Archway Portals
        set_pixel(1, 13, 180, 0, 220)
        set_pixel(3, 1, 180, 0, 220)

        # 3. Sparkling Gems
        for g in self.gems:
            if not g["collected"]:
                gx, gy = int(round(g["x"])), int(round(g["y"]))
                set_pixel(gx, gy, 0, 255, 255) # Cyan crystal gems

        # 4. Honey Pot
        if self.honey_pot["active"]:
            hx, hy = int(round(self.honey_pot["x"])), int(round(self.honey_pot["y"]))
            set_pixel(hx, hy, 255, 180, 0) # Gold honey pot

        # 5. Gem Eater (Crawling green caterpillar)
        if self.gem_eater["alive"]:
            ex, ey = int(round(self.gem_eater["x"])), int(round(self.gem_eater["y"]))
            set_pixel(ex, ey, 50, 220, 50)
            set_pixel(ex + 1, ey, 30, 160, 30)

        # 6. Berthilda the Witch (Red & Purple hooded sorceress)
        if self.witch["alive"]:
            wx, wy = int(round(self.witch["x"])), int(round(self.witch["y"]))
            set_pixel(wx, wy, 200, 30, 180)
            set_pixel(wx, wy - 1, 255, 40, 40)

        # 7. Bentley Bear
        bx, by = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.invulnerable_timer > 0.0:
                set_pixel(bx, by, 255, 255, 255) # Flashing magic bear
                set_pixel(bx, by - 1, 255, 220, 0)
            else:
                set_pixel(bx, by, 180, 100, 40)  # Brown bear
                set_pixel(bx, by - 1, 240, 60, 60) # Red stocking cap
        elif self.state == STATE_BENTLEY_DIED:
            set_pixel(bx, by, 255, 80, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "castle": self.castle,
            "gems_left": self.remaining_gems_count(),
            "invulnerable": (self.invulnerable_timer > 0.0),
            "px": self.px,
            "py": self.py,
        }

