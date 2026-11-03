"""
Game #177: 深水炸弹 (Depthcharge - 1977 Gremlin / Sega)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released in 1977 by Gremlin and licensed by Sega, Depthcharge was an arcade landmark
that defined underwater naval combat. Players command a surface destroyer patrolling
choppy ocean waves, dropping port and starboard depth charges to intercept elusive
submarines prowling at multiple depth tiers while evading rising torpedoes and floating mines.

Unique Core Mechanic (Strict Zero-Redundancy):
- Surface Destroyer Maneuvering: Cruise along the ocean surface line (y=2.0) with lateral momentum.
- Dual-Port Depth Charge Launchers: Button A drops port (left) depth charges; Button B drops
  starboard (right) depth charges, calculating sink velocity and lead distance.
- 3-Tier Multi-Depth Submarine Grid:
  * Shallow Tier (y=6): Fast scout submarines (300 pts)
  * Medium Tier (y=10): Attack submarines (200 pts)
  * Deep Trench Tier (y=14): Heavy ballistic submarines (100 pts)
- Rising Underwater Torpedoes: Submarines launch buoyant vertical torpedoes upward; destroyer
  must maneuver swiftly to evade rising torpedoes.
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
STATE_SHIP_SUNK = 2
STATE_GAME_OVER = 3

class Game177Depthcharge(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Surface Destroyer
        self.px = 7.5
        self.py = 2.0
        self.speed = 6.0

        # Sinking Depth Charges [{x, y, vy, active}]
        self.charges: List[Dict[str, Any]] = []

        # Submarines [{id, x, y, vx, tier, alive, reload_timer}]
        self.subs: List[Dict[str, Any]] = []

        # Rising Torpedoes [{x, y, vy}]
        self.torpedoes: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 177

    @property
    def name(self) -> str:
        return "深水炸弹"

    @property
    def english_name(self) -> str:
        return "Depthcharge"

    @property
    def release_year(self) -> int:
        return 1977

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "水面驱逐舰左右巡航、左右双舷深水炸弹抛投下沉爆破、三层潜深潜艇伏击与规避上浮鱼雷水雷"

    def get_name(self) -> str:
        return "Depthcharge (1977)"

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
        self.py = 2.0

        self.charges.clear()
        self.torpedoes.clear()

        # 3 Submarines at 3 depth tiers
        self.subs = [
            {"id": 0, "x": 2.0, "y": 6.0, "vx": 3.2 + self.stage * 0.3, "tier": 0, "alive": True, "reload": 1.5},
            {"id": 1, "x": 13.0, "y": 10.0, "vx": -(2.4 + self.stage * 0.25), "tier": 1, "alive": True, "reload": 2.2},
            {"id": 2, "x": 5.0, "y": 14.0, "vx": 1.8 + self.stage * 0.2, "tier": 2, "alive": True, "reload": 3.0},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_SHIP_SUNK:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.charges.clear()
                    self.torpedoes.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Destroyer Lateral Cruise
        if keys_down & KEY_LEFT:  self.px -= self.speed * dt
        if keys_down & KEY_RIGHT: self.px += self.speed * dt
        self.px = max(1.5, min(14.5, self.px))

        # Drop Port Depth Charge (Button A)
        active_charges = sum(1 for c in self.charges if c["active"])
        if (keys_pressed & KEY_A) and active_charges < 4:
            self.charges.append({
                "x": self.px - 0.8,
                "y": self.py + 0.8,
                "vy": 5.5,
                "active": True,
            })

        # Drop Starboard Depth Charge (Button B)
        active_charges = sum(1 for c in self.charges if c["active"])
        if (keys_pressed & KEY_B) and active_charges < 4:
            self.charges.append({
                "x": self.px + 0.8,
                "y": self.py + 0.8,
                "vy": 5.5,
                "active": True,
            })

        # Update Sinking Depth Charges
        for c in self.charges[:]:
            if not c["active"]:
                continue
            c["y"] += c["vy"] * dt

            # Seabed hit
            if c["y"] >= 15.0:
                c["active"] = False
                continue

            # Check hit against submarines
            for s in self.subs:
                if s["alive"] and math.hypot(s["x"] - c["x"], s["y"] - c["y"]) < 1.1:
                    s["alive"] = False
                    c["active"] = False
                    # Scoring based on depth tier
                    tier_pts = [300, 200, 100]
                    self.score += tier_pts[s["tier"]]
                    self._check_stage_clear()
                    break

        # Remove inactive charges
        self.charges = [c for c in self.charges if c["active"]]

        # Update Submarines & Torpedoes
        for s in self.subs:
            if not s["alive"]:
                continue
            s["x"] += s["vx"] * dt
            # Screen bounce / wrap
            if s["x"] > 14.5:
                s["x"] = 14.5
                s["vx"] = -abs(s["vx"])
            elif s["x"] < 1.5:
                s["x"] = 1.5
                s["vx"] = abs(s["vx"])

            # Sub launches rising torpedo
            s["reload"] -= dt
            if s["reload"] <= 0.0:
                s["reload"] = max(1.5, 3.5 - self.stage * 0.3)
                if len(self.torpedoes) < 4:
                    self.torpedoes.append({
                        "x": s["x"],
                        "y": s["y"] - 0.8,
                        "vy": -5.0,
                    })

        # Update Torpedoes
        for t in self.torpedoes[:]:
            t["y"] += t["vy"] * dt
            if t["y"] < 1.0:
                self.torpedoes.remove(t)
                continue

            # Hit Destroyer
            if math.hypot(t["x"] - self.px, t["y"] - self.py) < 1.0:
                self.torpedoes.remove(t)
                self.lives -= 1
                self.state = STATE_SHIP_SUNK
                self.state_timer = 1.2
                return

    def _check_stage_clear(self):
        if not any(s["alive"] for s in self.subs):
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 1500

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

        # 1. Sky (y=0..1)
        for x in range(16):
            set_pixel(x, 0, 40, 40, 80)
            set_pixel(x, 1, 60, 80, 120)

        # 2. Ocean Surface Line (y=2)
        for x in range(16):
            set_pixel(x, 2, 0, 140, 200)

        # 3. Ocean Water (y=3..15) with depth shading
        for y in range(3, 16):
            b_val = max(30, 140 - (y - 3) * 8)
            for x in range(16):
                set_pixel(x, y, 5, 20, b_val)

        # 4. Submarines
        for s in self.subs:
            if s["alive"]:
                sx = int(round(s["x"]))
                sy = int(round(s["y"]))
                # Sub hull & conning tower
                set_pixel(sx, sy, 180, 180, 40)       # Amber-yellow sub hull
                set_pixel(sx - 1, sy, 140, 140, 30)
                set_pixel(sx + 1, sy, 140, 140, 30)
                set_pixel(sx, sy - 1, 220, 220, 80)   # Periscope/conning tower

        # 5. Sinking Depth Charges
        for c in self.charges:
            if c["active"]:
                cx = int(round(c["x"]))
                cy = int(round(c["y"]))
                set_pixel(cx, cy, 255, 120, 20) # Orange explosive canister

        # 6. Rising Torpedoes
        for t in self.torpedoes:
            tx = int(round(t["x"]))
            ty = int(round(t["y"]))
            set_pixel(tx, ty, 255, 40, 40)   # Red rising bubble-torpedo

        # 7. Surface Destroyer
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 200, 210, 220)     # Gray naval steel hull
            set_pixel(px - 1, py, 160, 170, 180) # Bow
            set_pixel(px + 1, py, 160, 170, 180) # Stern
            set_pixel(px, py - 1, 240, 240, 250) # Bridge tower
            set_pixel(px - 1, py - 1, 220, 80, 0) # Port launcher
            set_pixel(px + 1, py - 1, 220, 80, 0) # Starboard launcher
        elif self.state == STATE_SHIP_SUNK:
            set_pixel(px, py, 255, 100, 0)
            set_pixel(px - 1, py, 255, 0, 0)
            set_pixel(px + 1, py, 255, 0, 0)

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
            "charges_count": len(self.charges),
            "torpedoes_count": len(self.torpedoes),
            "subs_alive": sum(1 for s in self.subs if s["alive"]),
        }

