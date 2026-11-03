"""
Game #182: 魔法水滴 (Magical Drop - 1995 Data East)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Data East in 1995, Magical Drop revolutionized the arcade action puzzle genre
with its blistering speed and inverted mechanics. Instead of waiting for falling pieces,
the player actively reaches up to suck down chains of colored bubbles and flings them back
into other columns to trigger chain-reaction cascades before the descending ceiling crushes them.

Unique Core Mechanic (Strict Zero-Redundancy):
- Dynamic Bottom-Up Pull (Button A): Sucks down contiguous matching bubbles from the bottom
  of any column directly into the clown's hands (holding up to 4 bubbles of the same color).
- Rapid Reverse Fling (Button B): Launches all held bubbles straight up into any chosen column.
- Vertical Match-3 & Gravity Cascade: Aligning 3 or more vertical matching bubbles bursts them;
  flanking bubbles collapse downward to trigger cascade combos!
- Descending Ceiling Pressure: Rows advance steadily downward; letting bubbles cross the floor
  line costs a life.
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
STATE_FLOOR_CRUSHED = 2
STATE_GAME_OVER = 3

COLOR_NONE = 0
COLOR_RED = 1
COLOR_BLUE = 2
COLOR_GREEN = 3
COLOR_YELLOW = 4

class Game182MagicalDrop(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Clown
        self.col = 7 # Column index 1..14
        self.held_color = COLOR_NONE
        self.held_count = 0
        self.max_held = 4

        # Board grid (16 rows x 16 columns)
        # grid[y][x]: 0 is empty, 1..4 colors
        self.grid = [[COLOR_NONE for _ in range(16)] for _ in range(16)]

        # Ceiling descent timer
        self.drop_timer = 6.0
        self.cleared_target = 30
        self.bubbles_cleared = 0

        self.init()

    @property
    def game_id(self) -> int:
        return 182

    @property
    def name(self) -> str:
        return "魔法水滴"

    @property
    def english_name(self) -> str:
        return "Magical Drop"

    @property
    def release_year(self) -> int:
        return 1995

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "小丑底线穿梭同色多球瞬吸入腹、向上弹射列置换重组、三连消除与磁力级联连锁爆破"

    def get_name(self) -> str:
        return "Magical Drop (1995)"

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
        self.col = 7
        self.held_color = COLOR_NONE
        self.held_count = 0
        self.drop_timer = max(3.5, 6.0 - self.stage * 0.4)
        self.cleared_target = 25 + self.stage * 5
        self.bubbles_cleared = 0

        # Clear grid
        for y in range(16):
            for x in range(16):
                self.grid[y][x] = COLOR_NONE

        # Seed initial top 5 rows across active columns 3..12
        pattern = [COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_YELLOW]
        for y in range(1, 6):
            for x in range(3, 13):
                # Pseudo-random structured colors
                c = pattern[(x * 2 + y * 3 + self.stage) % 4]
                self.grid[y][x] = c

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_FLOOR_CRUSHED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.held_color = COLOR_NONE
                    self.held_count = 0
                    self._init_stage()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Movement across columns 3..12
        if (keys_pressed & KEY_LEFT):
            self.col = max(3, self.col - 1)
        elif (keys_pressed & KEY_RIGHT):
            self.col = min(12, self.col + 1)

        # Button A: PULL / SUCK BUBBLE(S) from column
        if keys_pressed & KEY_A:
            self._pull_bubbles(self.col)

        # Button B: FLING / SHOOT HELD BUBBLES up into column
        if keys_pressed & KEY_B:
            self._fling_bubbles(self.col)

        # Ceiling descent timer
        self.drop_timer -= dt
        if self.drop_timer <= 0.0:
            self.drop_timer = max(3.5, 6.0 - self.stage * 0.4)
            self._drop_ceiling_row()

    def _pull_bubbles(self, x: int):
        # Find lowest bubble in column x
        lowest_y = -1
        for y in range(13, -1, -1):
            if self.grid[y][x] != COLOR_NONE:
                lowest_y = y
                break

        if lowest_y == -1:
            return # Column is empty

        bubble_col = self.grid[lowest_y][x]
        if self.held_color == COLOR_NONE or self.held_color == bubble_col:
            # Can pull this color
            self.held_color = bubble_col
            # Pull all contiguous bubbles of this color upwards up to max_held
            while lowest_y >= 0 and self.grid[lowest_y][x] == self.held_color and self.held_count < self.max_held:
                self.grid[lowest_y][x] = COLOR_NONE
                self.held_count += 1
                lowest_y -= 1

    def _fling_bubbles(self, x: int):
        if self.held_count == 0 or self.held_color == COLOR_NONE:
            return

        # Find first empty slot in column x from top down
        insert_y = -1
        for y in range(14):
            if self.grid[y][x] == COLOR_NONE:
                insert_y = y
                break

        if insert_y == -1:
            return # Column full

        # Place held bubbles into column
        while self.held_count > 0 and insert_y < 14:
            self.grid[insert_y][x] = self.held_color
            self.held_count -= 1
            insert_y += 1

        self.held_color = COLOR_NONE
        self.held_count = 0

        # Check Match-3 in this column
        self._check_column_matches(x)

    def _check_column_matches(self, x: int):
        # Check vertical consecutive matching groups of 3+
        y = 0
        while y < 14:
            c = self.grid[y][x]
            if c != COLOR_NONE:
                run_start = y
                while y < 14 and self.grid[y][x] == c:
                    y += 1
                run_len = y - run_start
                if run_len >= 3:
                    # Pop matching bubbles!
                    for ry in range(run_start, y):
                        self.grid[ry][x] = COLOR_NONE
                    popped = run_len
                    self.score += popped * 100
                    self.bubbles_cleared += popped

                    # Check stage clear
                    if self.bubbles_cleared >= self.cleared_target:
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 2.0
                        self.score += 2500
                        return
            else:
                y += 1

    def _drop_ceiling_row(self):
        # Shift all rows down by 1
        for y in range(13, 0, -1):
            for x in range(3, 13):
                self.grid[y][x] = self.grid[y - 1][x]

        # Check if any bubble crossed into row 13 (floor threshold)
        for x in range(3, 13):
            if self.grid[13][x] != COLOR_NONE:
                self.lives -= 1
                self.state = STATE_FLOOR_CRUSHED
                self.state_timer = 1.2
                return

        # Inject new top row
        pattern = [COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_YELLOW]
        for x in range(3, 13):
            self.grid[0][x] = pattern[(x + int(self.score / 100)) % 4]

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

        color_palette = {
            COLOR_RED: (255, 30, 40),
            COLOR_BLUE: (40, 120, 255),
            COLOR_GREEN: (40, 220, 50),
            COLOR_YELLOW: (255, 220, 30),
        }

        # 1. Side Borders & Floor Line at y=13
        for y in range(16):
            set_pixel(2, y, 60, 40, 80)
            set_pixel(13, y, 60, 40, 80)
        for x in range(2, 14):
            set_pixel(x, 13, 80, 20, 40)

        # 2. Grid Bubbles
        for y in range(13):
            for x in range(3, 13):
                c = self.grid[y][x]
                if c != COLOR_NONE:
                    r, g, b = color_palette.get(c, (200, 200, 200))
                    set_pixel(x, y, r, g, b)

        # 3. Clown Player at row 14
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(self.col, 14, 255, 255, 255) # White clown face
            set_pixel(self.col, 15, 255, 60, 60)   # Red clown suit
            # Show held bubbles in clown's hands
            if self.held_count > 0:
                hr, hg, hb = color_palette.get(self.held_color, (255, 255, 255))
                set_pixel(self.col, 13, hr, hg, hb)
                if self.held_count > 1:
                    set_pixel(self.col - 1, 14, hr, hg, hb)
                if self.held_count > 2:
                    set_pixel(self.col + 1, 14, hr, hg, hb)
        elif self.state == STATE_FLOOR_CRUSHED:
            set_pixel(self.col, 14, 255, 80, 0)

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
            "col": self.col,
            "held_color": self.held_color,
            "held_count": self.held_count,
            "bubbles_cleared": self.bubbles_cleared,
            "drop_timer": self.drop_timer,
        }

