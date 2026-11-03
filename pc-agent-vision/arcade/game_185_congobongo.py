"""
Game #185: 丛林大金刚 (Congo Bongo - 1983 Sega / Ikegami Tsushinki)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Sega in 1983, Congo Bongo (also known as Tip-Top) was the pioneering isometric
3D platforming adventure. Controlling the red-nosed safari hunter, players scale multi-tiered
cliff ledges, dodge falling jungle boulders, leap across floating river logs and hippos,
and sneak into the mountain summit to light sleeping giant gorilla Bongo's tail on fire!

Unique Core Mechanic (Strict Zero-Redundancy):
- Tiered Isometric Cliff Ascent: Traverse multi-layered jungle terrain from base camp to the mountain summit.
- High Jump (Button A): Leap over rolling jungle boulders and cross water gaps. Immune to ground boulders mid-air.
- Raging River Crossing: Time leaps across floating logs in the fast-flowing waterfall river.
- Summit Sneak & Campfire Tail Ignition (Button B): Reach Bongo's mountain lair and strike a match
  to burn the sleeping giant ape's tail, sending him howling into the waterfall below!
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
STATE_HUNTER_KILLED = 2
STATE_GAME_OVER = 3

class Game185CongoBongo(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Hunter (Safari Explorer)
        self.px = 2.0
        self.py = 14.0
        self.speed = 4.5
        self.is_jumping = False
        self.jump_timer = 0.0
        self.jump_duration = 0.45

        # Bongo (Giant Gorilla at the summit)
        self.bongo_x = 12.0
        self.bongo_y = 2.0
        self.bongo_asleep = True
        self.tail_ignited = False

        # Rolling Boulders [{x, y, vx, vy}]
        self.boulders: List[Dict[str, Any]] = []
        self.boulder_spawn_timer = 0.0

        # River Floating Logs [{x, y, speed, width}]
        self.logs: List[Dict[str, Any]] = []

        # Patrol Rhinos [{x, y, vx}]
        self.rhinos: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 185

    @property
    def name(self) -> str:
        return "丛林大金刚"

    @property
    def english_name(self) -> str:
        return "Congo Bongo"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "等轴立体阶梯攀岩爬瀑布、跳跃规避滚落巨石、浮木渡河与夜袭沉睡巨猿点燃尾巴"

    def get_name(self) -> str:
        return "Congo Bongo (1983)"

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
        self.px = 2.0
        self.py = 14.0
        self.is_jumping = False
        self.jump_timer = 0.0

        self.bongo_x = 12.0
        self.bongo_y = 2.0
        self.bongo_asleep = True
        self.tail_ignited = False

        self.boulders.clear()
        self.boulder_spawn_timer = 1.0

        # River Logs (Tier 2: y = 8, 9)
        self.logs = [
            {"x": 1.0, "y": 8.0, "speed": 3.0, "width": 3.0},
            {"x": 9.0, "y": 8.0, "speed": 3.0, "width": 3.0},
            {"x": 14.0, "y": 9.0, "speed": -2.5, "width": 3.5},
            {"x": 6.0, "y": 9.0, "speed": -2.5, "width": 3.5},
        ]

        # Charging Rhinos (Tier 3: y = 5.0)
        self.rhinos = [
            {"x": 1.0, "y": 5.0, "vx": 4.0},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_HUNTER_KILLED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 2.0
                    self.py = 14.0
                    self.is_jumping = False
                    self.boulders.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # 1. Jump Handling (Button A)
        if (keys_pressed & KEY_A) and not self.is_jumping:
            self.is_jumping = True
            self.jump_timer = self.jump_duration

        if self.is_jumping:
            self.jump_timer -= dt
            if self.jump_timer <= 0.0:
                self.is_jumping = False

        # 2. Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            inv = 1.0 / math.hypot(dx, dy)
            self.px += dx * inv * self.speed * dt
            self.py += dy * inv * self.speed * dt

        self.px = max(0.5, min(14.5, self.px))
        self.py = max(1.0, min(14.5, self.py))

        # 3. Strike Match / Light Tail at Summit (Button B)
        if keys_pressed & KEY_B:
            # Check if hunter is at summit tier near sleeping Bongo
            if self.py <= 3.5 and math.hypot(self.bongo_x - self.px, self.bongo_y - self.py) < 2.5:
                self.tail_ignited = True
                self.bongo_asleep = False
                self.state = STATE_STAGE_CLEAR
                self.state_timer = 2.0
                self.score += 2500 + self.stage * 500
                return

        # 4. Update River Logs & Water Drowning
        on_log = False
        for log in self.logs:
            log["x"] += log["speed"] * dt
            if log["speed"] > 0 and log["x"] > 16.0:
                log["x"] = -log["width"]
            elif log["speed"] < 0 and log["x"] < -log["width"]:
                log["x"] = 16.0

            # Check if hunter is standing on log
            if abs(self.py - log["y"]) < 0.6:
                if log["x"] <= self.px <= log["x"] + log["width"]:
                    on_log = True
                    # Drift with log if not jumping
                    if not self.is_jumping:
                        self.px += log["speed"] * dt

        # Water zone check (y between 7.5 and 9.5)
        if 7.5 <= self.py <= 9.5:
            if not on_log and not self.is_jumping:
                # Drown in waterfall!
                self.lives -= 1
                self.state = STATE_HUNTER_KILLED
                self.state_timer = 1.0
                return

        # 5. Spawn & Update Rolling Boulders
        self.boulder_spawn_timer -= dt
        if self.boulder_spawn_timer <= 0.0:
            self.boulder_spawn_timer = max(1.0, 2.5 - self.stage * 0.2)
            # Roll down from summit ledge
            self.boulders.append({
                "x": 10.0,
                "y": 3.0,
                "vx": -3.5,
                "vy": 2.2,
            })

        for b in self.boulders[:]:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            # Bounce off walls zig-zag down
            if b["x"] < 1.0:
                b["x"] = 1.0
                b["vx"] = -b["vx"]
            elif b["x"] > 14.5:
                b["x"] = 14.5
                b["vx"] = -b["vx"]

            # Remove when off bottom
            if b["y"] > 15.5:
                self.boulders.remove(b)
                self.score += 50
                continue

            # Collision with hunter (only when hunter is NOT jumping!)
            if not self.is_jumping and math.hypot(b["x"] - self.px, b["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_HUNTER_KILLED
                self.state_timer = 1.0
                return

        # 6. Update Charging Rhinos (Tier 3)
        for r in self.rhinos:
            r["x"] += r["vx"] * dt
            if r["x"] < 1.0:
                r["x"] = 1.0
                r["vx"] = -r["vx"]
            elif r["x"] > 14.5:
                r["x"] = 14.5
                r["vx"] = -r["vx"]

            if math.hypot(r["x"] - self.px, r["y"] - self.py) < 0.9:
                self.lives -= 1
                self.state = STATE_HUNTER_KILLED
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

        # 1. Background Tiered Cliffs & Waterfall
        for y in range(16):
            for x in range(16):
                if y >= 13:
                    set_pixel(x, y, 40, 120, 40)   # Tier 0: Base jungle grass
                elif 10 <= y <= 12:
                    set_pixel(x, y, 140, 90, 50)   # Tier 1: Earth cliff ledge
                elif 8 <= y <= 9:
                    set_pixel(x, y, 30, 80, 200)   # Tier 2: Raging river waterfall
                elif 4 <= y <= 7:
                    set_pixel(x, y, 160, 110, 60)  # Tier 3: Plateau rock
                else:
                    set_pixel(x, y, 180, 130, 70)  # Tier 4: Summit cliff

        # 2. River Logs
        for log in self.logs:
            lx_start = int(math.floor(log["x"]))
            lx_end = int(math.ceil(log["x"] + log["width"]))
            ly = int(round(log["y"]))
            for lx in range(lx_start, lx_end):
                set_pixel(lx, ly, 110, 70, 30) # Brown floating log

        # 3. Charging Rhinos
        for r in self.rhinos:
            rx = int(round(r["x"]))
            ry = int(round(r["y"]))
            set_pixel(rx, ry, 180, 180, 190)     # Gray rhino body
            horn_x = rx + (1 if r["vx"] > 0 else -1)
            set_pixel(horn_x, ry, 255, 255, 255) # White horn

        # 4. Rolling Boulders
        for b in self.boulders:
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            set_pixel(bx, by, 220, 130, 30) # Orange round boulder

        # 5. Sleeping Giant Gorilla Bongo at Summit
        bgx = int(round(self.bongo_x))
        bgy = int(round(self.bongo_y))
        if self.bongo_asleep:
            set_pixel(bgx, bgy, 130, 60, 20)      # Brown fur
            set_pixel(bgx - 1, bgy, 100, 40, 10)  # Gorilla back
            set_pixel(bgx + 1, bgy, 200, 160, 120)# Face
            set_pixel(bgx - 2, bgy + 1, 150, 80, 30) # Tail
        else:
            # Burning tail howling in shock!
            set_pixel(bgx, bgy, 255, 50, 0)
            set_pixel(bgx - 1, bgy, 255, 200, 0) # Fire flame!
            set_pixel(bgx + 1, bgy, 255, 100, 0)

        # 6. Safari Hunter
        hx = int(round(self.px))
        hy = int(round(self.py))
        if self.is_jumping:
            hy -= 1 # Visually elevated jump

        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(hx, hy, 230, 210, 50)       # Yellow safari shirt
            set_pixel(hx, hy - 1, 220, 40, 30)    # Red safari pith helmet
            if self.tail_ignited:
                set_pixel(hx + 1, hy, 255, 255, 80) # Lit match torch!
        elif self.state == STATE_HUNTER_KILLED:
            set_pixel(hx, hy, 255, 60, 0)

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
            "is_jumping": self.is_jumping,
            "bongo_asleep": self.bongo_asleep,
            "tail_ignited": self.tail_ignited,
        }

