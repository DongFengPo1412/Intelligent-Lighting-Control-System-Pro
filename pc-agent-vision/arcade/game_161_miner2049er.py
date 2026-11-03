"""
Game #161: 矿工2049 (Miner 2049er - 1982 Big Five Software / Bill Hogue)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Miner 2049er (1982) was one of the defining platform classics of early gaming,
winning Game of the Year in 1983. Starring Bounty Bob, it introduced the unique mechanic
of walking over and claiming every segment of radioactive mine scaffolding,
navigating one-way radioactive slides, hydraulic lifts, and avoiding mutant creatures.

Unique Mechanic (Strict Zero-Redundancy):
- Scaffolding Footprint Coloring: Walking across platform beams permanently paints/claims them.
- Vertical Mine Structure: Multiple tiers connected by ladders, radioactive slides, and lifts.
- One-Way Radioactive Chutes: Slide down at speed between tiers.
- 100% Beam Coverage Clears Level: Stage is complete only when all scaffolding segments are claimed!
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
STATE_BOB_DIED = 2
STATE_GAME_OVER = 3

class Game161Miner2049er(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.level = 1
        self.state_timer = 0.0

        # Player Bounty Bob state
        self.px = 1.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.on_ladder = False
        self.sliding = False

        # Scaffolding floor map: set of (x, y) representing solid beam tiles
        self.platforms = set()
        self.ladders = set()
        self.slides = set()  # (x, y) leading downwards
        self.colored_tiles = set()
        self.total_claimable = 0

        # Mutant creatures: list of {x, y, vx, min_x, max_x}
        self.mutants: List[Dict[str, float]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 161

    @property
    def name(self) -> str:
        return "矿工2049"

    @property
    def english_name(self) -> str:
        return "Miner 2049er"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "脚踏矿区钢梁全面染色圈地、攀爬梯子垂直变轨、单向放射性滑道极速俯冲与避让变异矿工"

    def get_name(self) -> str:
        return "Miner 2049er (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 1.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.on_ladder = False
        self.sliding = False

        self.platforms.clear()
        self.ladders.clear()
        self.slides.clear()
        self.colored_tiles.clear()

        # Floor 0: Bottom platform y=14, x=0..15
        for x in range(16):
            self.platforms.add((x, 14))

        # Floor 1: Middle-lower platform y=10, x=0..12
        for x in range(13):
            self.platforms.add((x, 10))

        # Floor 2: Middle-upper platform y=6, x=3..15
        for x in range(3, 16):
            self.platforms.add((x, 6))

        # Floor 3: Top platform y=2, x=0..11
        for x in range(12):
            self.platforms.add((x, 2))

        # Ladders
        # Ladder 1: x=2, y=10..13
        for y in range(10, 14):
            self.ladders.add((2, y))

        # Ladder 2: x=11, y=6..9
        for y in range(6, 10):
            self.ladders.add((11, y))

        # Ladder 3: x=5, y=2..5
        for y in range(2, 6):
            self.ladders.add((5, y))

        # Radioactive slide chute: from (14, 6) down to (13, 10)
        self.slides.add((14, 6))
        self.slides.add((13, 7))
        self.slides.add((13, 8))
        self.slides.add((13, 9))

        self.total_claimable = len(self.platforms)

        # Mutants
        self.mutants = [
            {"x": 6.0, "y": 9.0, "vx": 2.2, "min_x": 4.0, "max_x": 10.0},
            {"x": 8.0, "y": 5.0, "vx": -2.5, "min_x": 6.0, "max_x": 13.0},
        ]

        # Initial tile step
        self._claim_tile(int(round(self.px)), 14)

    def _claim_tile(self, x: int, y: int):
        if (x, y) in self.platforms and (x, y) not in self.colored_tiles:
            self.colored_tiles.add((x, y))
            self.score += 10
            if len(self.colored_tiles) >= self.total_claimable:
                self.state = STATE_STAGE_CLEAR
                self.state_timer = 2.0
                self.score += 1000 * self.level

    def coverage_percentage(self) -> float:
        if self.total_claimable == 0:
            return 100.0
        return (len(self.colored_tiles) / self.total_claimable) * 100.0

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.level += 1
                self._init_level()
            return

        if self.state == STATE_BOB_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 1.0
                    self.py = 13.0
                    self.vx = 0.0
                    self.vy = 0.0
                    self.on_ground = True
                    self.on_ladder = False
                    self.sliding = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player physics and input
        ix = int(round(self.px))
        iy = int(round(self.py))

        # Check if entering slide
        if (ix, iy) in self.slides or (ix, iy + 1) in self.slides:
            self.sliding = True

        if self.sliding:
            # Forced sliding downward diagonally
            self.vx = -1.5
            self.vy = 4.0
            self.px += self.vx * dt
            self.py += self.vy * dt
            if self.py >= 9.0: # Reached Floor 1
                self.sliding = False
                self.py = 9.0
                self.vy = 0.0
        else:
            # Check ladder contact
            can_climb = (ix, iy) in self.ladders or (ix, iy + 1) in self.ladders

            if can_climb and (keys_down & (KEY_UP | KEY_DOWN)):
                self.on_ladder = True
                self.on_ground = False
                self.vy = -3.5 if (keys_down & KEY_UP) else 3.5
            elif self.on_ladder:
                if not can_climb:
                    self.on_ladder = False
                else:
                    self.vy = 0.0
                    if keys_down & KEY_UP:
                        self.vy = -3.5
                    elif keys_down & KEY_DOWN:
                        self.vy = 3.5

            # Horizontal movement
            walk_speed = 4.5
            if keys_down & KEY_LEFT:
                self.vx = -walk_speed
            elif keys_down & KEY_RIGHT:
                self.vx = walk_speed
            else:
                self.vx = 0.0

            # Jump
            if (keys_pressed & KEY_A) and self.on_ground and not self.on_ladder:
                self.vy = -6.0
                self.on_ground = False

            # Gravity
            if not self.on_ladder:
                self.vy += 16.0 * dt
                if self.vy > 8.0:
                    self.vy = 8.0

            self.px += self.vx * dt
            self.py += self.vy * dt

            # Clamp horizontal
            self.px = max(0.0, min(15.0, self.px))

            # Platform collision detection
            foot_y = self.py + 1.0
            cur_ix = int(round(self.px))
            floor_tile_y = int(math.floor(foot_y))

            if not self.on_ladder and self.vy >= 0:
                # Check landing on platform
                if (cur_ix, floor_tile_y) in self.platforms and abs(foot_y - floor_tile_y) < 0.45:
                    self.py = floor_tile_y - 1.0
                    self.vy = 0.0
                    self.on_ground = True
                    self._claim_tile(cur_ix, floor_tile_y)

        # Mutants update
        for m in self.mutants:
            m["x"] += m["vx"] * dt
            if m["x"] <= m["min_x"]:
                m["x"] = m["min_x"]
                m["vx"] = abs(m["vx"])
            elif m["x"] >= m["max_x"]:
                m["x"] = m["max_x"]
                m["vx"] = -abs(m["vx"])

            # Check collision with Bob
            if math.hypot(m["x"] - self.px, m["y"] - self.py) < 0.85:
                self.lives -= 1
                self.state = STATE_BOB_DIED
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

        # 1. Scaffolding Platforms
        for (x, y) in self.platforms:
            if (x, y) in self.colored_tiles:
                set_pixel(x, y, 0, 240, 255)  # Cyan claimed
            else:
                set_pixel(x, y, 120, 100, 70) # Brown uncolored

        # 2. Ladders
        for (x, y) in self.ladders:
            set_pixel(x, y, 220, 220, 0)      # Yellow ladder

        # 3. Radioactive Slides
        for (x, y) in self.slides:
            set_pixel(x, y, 0, 255, 60)       # Green radioactive chute

        # 4. Mutants
        for m in self.mutants:
            mx, my = int(round(m["x"])), int(round(m["y"]))
            set_pixel(mx, my, 255, 40, 40)    # Red radioactive mutant

        # 5. Bounty Bob
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            bx, by = int(round(self.px)), int(round(self.py))
            set_pixel(bx, by, 255, 255, 255) # White miner
        elif self.state == STATE_BOB_DIED:
            bx, by = int(round(self.px)), int(round(self.py))
            set_pixel(bx, by, 255, 120, 0)   # Orange dying flash

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "coverage_pct": self.coverage_percentage(),
            "px": self.px,
            "py": self.py,
        }

