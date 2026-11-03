"""
Game #171: 瓢虫大冒险 (Lady Bug - 1981 Universal)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Universal in 1981, Lady Bug was a trailblazing maze action classic.
It introduced the revolving turnstile gate mechanic that revolutionized maze games,
along with poison skull traps, cycling letter scoring (EXTRA / SPECIAL), and vegetable bonuses.

Unique Mechanic (Strict Zero-Redundancy):
- Dynamic 90-Degree Revolving Turnstiles: Pushing turnstile doors dynamically alters maze topology,
  opening new paths while trapping predator beetles in dead ends.
- Poison Skull Traps: Lethal skulls on the board that eliminate chasing enemy bugs if lured into them!
- Multiplier Hearts: Collecting hearts increases score multipliers and briefly chills enemy movement.
- Dots & Vegetable Clearance: Cleanse the maze of all dots to achieve stage victory.
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
STATE_LADYBUG_DIED = 2
STATE_GAME_OVER = 3

class Game171LadyBug(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.multiplier = 1
        self.state_timer = 0.0

        # Player Lady Bug state
        self.px = 7.5
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 5.0

        # Revolving Turnstiles: list of {x, y, orientation: "H" | "V"}
        # "H" blocks vertical movement; "V" blocks horizontal movement
        self.turnstiles: List[Dict[str, Any]] = []

        # Dots: set of (x, y)
        self.dots = set()

        # Poison Skulls: set of (x, y)
        self.skulls = set()

        # Hearts: set of (x, y)
        self.hearts = set()

        # Predator Beetles: list of {id, x, y, speed, alive}
        self.beetles: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 171

    @property
    def name(self) -> str:
        return "瓢虫大冒险"

    @property
    def english_name(self) -> str:
        return "Lady Bug"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "动态旋转门改变迷宫拓扑、诱导敌虫触碰骷髅毒药自毁、红心积分倍率与全域采蜜清盘"

    def get_name(self) -> str:
        return "Lady Bug (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.multiplier = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0

        self.dots.clear()
        self.skulls.clear()
        self.hearts.clear()

        # Turnstiles: 6 revolving doors at key grid intersections
        self.turnstiles = [
            {"x": 4, "y": 5, "ori": "H"},
            {"x": 11, "y": 5, "ori": "H"},
            {"x": 7, "y": 8, "ori": "V"},
            {"x": 8, "y": 8, "ori": "V"},
            {"x": 4, "y": 11, "ori": "H"},
            {"x": 11, "y": 11, "ori": "H"},
        ]

        # Poison Skulls
        self.skulls = {(4, 8), (11, 8)}

        # Hearts
        self.hearts = {(7, 2), (8, 13)}

        turnstile_coords = {(t["x"], t["y"]) for t in self.turnstiles}

        # Grid corridor dots (odd coordinates 1..14)
        for y in (2, 5, 8, 11, 13):
            for x in range(1, 15):
                if ((x, y) not in self.skulls and
                    (x, y) not in self.hearts and
                    (x, y) not in turnstile_coords and
                    (x, y) not in ((7, 5), (8, 5))):
                    self.dots.add((x, y))

        # Chasing Beetles
        self.beetles = [
            {"id": 0, "x": 7.5, "y": 5.0, "speed": 2.2 + self.stage * 0.2, "alive": True},
            {"id": 1, "x": 8.0, "y": 2.0, "speed": 2.5 + self.stage * 0.2, "alive": True},
        ]

    def remaining_dots(self) -> int:
        return len(self.dots)

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_LADYBUG_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            new_px = self.px + dx * self.speed * dt
            new_py = self.py + dy * self.speed * dt

            # Turnstile interaction: Lady Bug can push turnstiles 90 degrees!
            for t in self.turnstiles:
                if math.hypot(t["x"] - new_px, t["y"] - new_py) < 0.8:
                    # Flip orientation!
                    t["ori"] = "V" if t["ori"] == "H" else "H"
                    self.score += 50
                    break

            self.px = max(1.0, min(14.0, new_px))
            self.py = max(1.0, min(14.0, new_py))

        # Eat Dots
        cur_cell = (int(round(self.px)), int(round(self.py)))
        if cur_cell in self.dots:
            self.dots.remove(cur_cell)
            self.score += 10 * self.multiplier
            if len(self.dots) == 0:
                self.state = STATE_STAGE_CLEAR
                self.state_timer = 2.0
                self.score += 2000
                return

        # Collect Hearts
        if cur_cell in self.hearts:
            self.hearts.remove(cur_cell)
            self.multiplier = min(5, self.multiplier + 1)
            self.score += 300

        # Touch Poison Skull (Lethal to player!)
        if cur_cell in self.skulls:
            self.lives -= 1
            self.state = STATE_LADYBUG_DIED
            self.state_timer = 1.0
            return

        # Enemy Beetles AI
        for b in self.beetles:
            if not b["alive"]:
                continue

            bdx = self.px - b["x"]
            bdy = self.py - b["y"]
            dist = math.hypot(bdx, bdy)

            # Check if turnstile blocks beetle path
            step_x = (bdx / dist) * b["speed"] * dt if dist > 0.1 else 0.0
            step_y = (bdy / dist) * b["speed"] * dt if dist > 0.1 else 0.0

            blocked = False
            nx = b["x"] + step_x
            ny = b["y"] + step_y
            for t in self.turnstiles:
                if t["ori"] == "H":
                    if abs(ny - t["y"]) < 0.6 and abs(nx - t["x"]) <= 1.2:
                        blocked = True
                        break
                else:  # "V"
                    if abs(nx - t["x"]) < 0.6 and abs(ny - t["y"]) <= 1.2:
                        blocked = True
                        break

            if not blocked and dist > 0.1:
                b["x"] += step_x
                b["y"] += step_y

            b_cell = (int(round(b["x"])), int(round(b["y"])))

            # If Beetle touches Poison Skull -> Beetle dies!
            if b_cell in self.skulls:
                b["alive"] = False
                self.score += 1000 # Luring beetle into poison skull!

            # Beetle catches Lady Bug
            if math.hypot(b["x"] - self.px, b["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_LADYBUG_DIED
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

        # 1. Border
        for x in range(16):
            set_pixel(x, 0, 40, 100, 40)
            set_pixel(x, 15, 40, 100, 40)
        for y in range(16):
            set_pixel(0, y, 40, 100, 40)
            set_pixel(15, y, 40, 100, 40)

        # 2. Dots
        for (dx, dy) in self.dots:
            set_pixel(dx, dy, 240, 240, 120)

        # 3. Hearts
        for (hx, hy) in self.hearts:
            set_pixel(hx, hy, 255, 60, 140)

        # 4. Poison Skulls
        for (sx, sy) in self.skulls:
            set_pixel(sx, sy, 0, 220, 255) # Cyan toxic skulls

        # 5. Turnstiles
        for t in self.turnstiles:
            tx, ty = t["x"], t["y"]
            set_pixel(tx, ty, 255, 200, 0) # Gold pivot
            if t["ori"] == "H":
                set_pixel(tx - 1, ty, 220, 160, 0)
                set_pixel(tx + 1, ty, 220, 160, 0)
            else:
                set_pixel(tx, ty - 1, 220, 160, 0)
                set_pixel(tx, ty + 1, 220, 160, 0)

        # 6. Chasing Beetles
        for b in self.beetles:
            if b["alive"]:
                bx, by = int(round(b["x"])), int(round(b["y"]))
                set_pixel(bx, by, 60, 180, 60) # Green beetle

        # 7. Lady Bug (Red body with black spots)
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 255, 30, 30) # Red ladybug
            set_pixel(px, py - 1, 255, 200, 180) # Antennae
        elif self.state == STATE_LADYBUG_DIED:
            set_pixel(px, py, 255, 120, 0)

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
            "multiplier": self.multiplier,
            "dots_left": self.remaining_dots(),
            "px": self.px,
            "py": self.py,
        }
