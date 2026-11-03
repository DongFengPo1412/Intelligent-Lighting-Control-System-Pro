"""
Game #188: 钱币交换机 (Money Puzzle Exchanger - 1997 Face / Neo Geo MVS)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Face in 1997 for the Neo Geo MVS arcade system, Money Puzzle Exchanger is one of
the most acclaimed cult puzzle games in arcade history. Instead of standard color matching,
it features genuine currency denomination conversions: five 1-yen coins merge into a 5-yen coin,
two 5-yen coins merge into a 10-yen coin, five 10s become a 50, two 50s become a 100, five 100s
become a 500, and two 500s cash out in an explosive jackpot cascade!

Unique Core Mechanic (Strict Zero-Redundancy):
- Currency Value Consolidation:
  * 5x 1s -> 1x 5
  * 2x 5s -> 1x 10
  * 5x 10s -> 1x 50
  * 2x 50s -> 1x 100
  * 5x 100s -> 1x 500
  * 2x 500s -> Cleared in Cash Out Cascade!
- Bottom Suction & Toss (Button A: Suction/Catch, Button B: Toss/Shoot):
  * Button A grabs all consecutive identical coins from the bottom of the targeted column.
  * Button B fires the held coins back up into a column to trigger conversions and chain reactions.
- Descending Ceiling Pressure: Rows push downward over time; clear coins before they cross
  the bottom danger threshold!
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
STATE_GAME_OVER = 2

# Denominations: 1, 5, 10, 50, 100, 500
COIN_1 = 1
COIN_5 = 5
COIN_10 = 10
COIN_50 = 50
COIN_100 = 100
COIN_500 = 500

class Game188MoneyPuzzleExchanger(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.stage = 1
        self.state_timer = 0.0

        # Matrix Board: 7 columns (X: 1, 3, 5, 7, 9, 11, 13), rows up to 12
        # grid[col] = list of coin denominations from top (index 0) to bottom
        self.cols = 7
        self.grid: List[List[int]] = [[] for _ in range(self.cols)]

        # Player catcher position (cursor col: 0..6)
        self.cursor_col = 3
        self.cursor_cooldown = 0.0

        # Held coins in player's suction hands [denomination, count]
        self.held_denom = 0
        self.held_count = 0

        # Ceiling descent timer
        self.drop_timer = 12.0
        self.max_drop_timer = 12.0

        self.init()

    @property
    def game_id(self) -> int:
        return 188

    @property
    def name(self) -> str:
        return "钱币交换机"

    @property
    def english_name(self) -> str:
        return "Money Puzzle Exchanger"

    @property
    def release_year(self) -> int:
        return 1997

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "魔法硬币面值合并进位（5枚1分变5分、2枚5分变10分）、双向吸吐硬币重组与防止硬币压线"

    def get_name(self) -> str:
        return "Money Puzzle Exchanger (1997)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.stage = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.cursor_col = 3
        self.held_denom = 0
        self.held_count = 0
        self.max_drop_timer = max(4.0, 12.0 - self.stage * 1.5)
        self.drop_timer = self.max_drop_timer

        # Seed initial puzzle rows
        # Initial coins: 3 rows of alternating coins (no adjacent identical coins)
        self.grid = [[] for _ in range(self.cols)]
        preset_denoms = [
            [1, 5, 1, 5, 1, 5, 1],
            [10, 50, 10, 50, 10, 50, 10],
            [100, 500, 100, 500, 100, 500, 100],
        ]
        for row in range(3):
            for col in range(self.cols):
                self.grid[col].append(preset_denoms[row][col])

    def _push_ceiling_row(self):
        # Adds 1 new row at the top of all columns
        denoms = [COIN_1, COIN_5, COIN_10, COIN_50, COIN_100]
        for c in range(self.cols):
            # Seed pseudo-random coin
            idx = (c + int(self.score // 50) + self.stage) % len(denoms)
            self.grid[c].insert(0, denoms[idx])
            # Check bottom threshold overflow
            if len(self.grid[c]) >= 13:
                self.state = STATE_GAME_OVER
                return

    def _resolve_exchanges(self) -> bool:
        """Finds connected clusters of coins and merges them into higher denominations."""
        changed = False

        # We check each column for contiguous runs of identical coins
        for c in range(self.cols):
            col_coins = self.grid[c]
            i = 0
            while i < len(col_coins):
                val = col_coins[i]
                run = 1
                while i + run < len(col_coins) and col_coins[i + run] == val:
                    run += 1

                # Check conversion thresholds
                req = 5 if val in (COIN_1, COIN_10, COIN_100) else 2
                if run >= req:
                    changed = True
                    # Remove merged coins
                    del col_coins[i:i + req]
                    # Insert next denomination (or cash out for 500)
                    if val == COIN_1:
                        col_coins.insert(i, COIN_5)
                        self.score += 50
                    elif val == COIN_5:
                        col_coins.insert(i, COIN_10)
                        self.score += 100
                    elif val == COIN_10:
                        col_coins.insert(i, COIN_50)
                        self.score += 500
                    elif val == COIN_50:
                        col_coins.insert(i, COIN_100)
                        self.score += 1000
                    elif val == COIN_100:
                        col_coins.insert(i, COIN_500)
                        self.score += 5000
                    elif val == COIN_500:
                        # Full Jackpot Clear!
                        self.score += 10000
                    break # Break to re-evaluate after list mutation
                else:
                    i += run

        # Check stage clear (all columns completely cleared)
        total_coins = sum(len(col) for col in self.grid)
        if total_coins == 0:
            if self.state != STATE_STAGE_CLEAR:
                self.state = STATE_STAGE_CLEAR
                self.state_timer = 2.0
                self.score += 20000
            return False

        return changed

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # 1. Cursor Movement Left / Right
        if (keys_pressed & KEY_LEFT) or ((keys_down & KEY_LEFT) and self.cursor_cooldown <= 0.0):
            if self.cursor_col > 0:
                self.cursor_col -= 1
                self.cursor_cooldown = 0.18
        elif (keys_pressed & KEY_RIGHT) or ((keys_down & KEY_RIGHT) and self.cursor_cooldown <= 0.0):
            if self.cursor_col < self.cols - 1:
                self.cursor_col += 1
                self.cursor_cooldown = 0.18

        if self.cursor_cooldown > 0.0:
            self.cursor_cooldown -= dt

        # 2. Suction / Grab Coins (Button A)
        if (keys_pressed & KEY_A) and self.held_count == 0:
            col_coins = self.grid[self.cursor_col]
            if len(col_coins) > 0:
                denom = col_coins[-1]
                count = 0
                while len(col_coins) > 0 and col_coins[-1] == denom:
                    col_coins.pop()
                    count += 1
                self.held_denom = denom
                self.held_count = count

        # 3. Toss / Shoot Coins Upward (Button B)
        elif (keys_pressed & KEY_B) and self.held_count > 0:
            col_coins = self.grid[self.cursor_col]
            for _ in range(self.held_count):
                col_coins.append(self.held_denom)
            self.held_denom = 0
            self.held_count = 0

            # Chain reaction resolution
            while self._resolve_exchanges():
                pass

            # Overflow check
            if len(col_coins) >= 13:
                self.state = STATE_GAME_OVER
                return

        # 4. Ceiling descent
        self.drop_timer -= dt
        if self.drop_timer <= 0.0:
            self.drop_timer = self.max_drop_timer
            self._push_ceiling_row()

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

        def get_coin_color(denom: int) -> Tuple[int, int, int]:
            if denom == COIN_1:
                return (180, 180, 190) # Aluminum 1-yen
            elif denom == COIN_5:
                return (220, 160, 40)  # Brass with hole 5-yen
            elif denom == COIN_10:
                return (180, 80, 30)   # Bronze 10-yen
            elif denom == COIN_50:
                return (200, 200, 220) # Nickel 50-yen
            elif denom == COIN_100:
                return (240, 240, 255) # Silver 100-yen
            elif denom == COIN_500:
                return (255, 215, 0)   # Gold brass 500-yen
            return (100, 100, 100)

        # 1. Background Grid & Red Hazard Line at y = 13
        for x in range(16):
            set_pixel(x, 13, 180, 20, 20) # Danger threshold wire

        # 2. Render Coins in 7 columns (mapped to x = 1, 3, 5, 7, 9, 11, 13)
        for c in range(self.cols):
            x = 1 + c * 2
            col_coins = self.grid[c]
            for r, denom in enumerate(col_coins):
                if r < 13:
                    cr, cg, cb = get_coin_color(denom)
                    set_pixel(x, r, cr, cg, cb)
                    set_pixel(x + 1, r, max(0, cr - 40), max(0, cg - 40), max(0, cb - 40))

        # 3. Player Catcher / Hands Cursor at y = 14..15
        cx = 1 + self.cursor_col * 2
        set_pixel(cx, 14, 40, 120, 240)     # Blue suction nozzle
        set_pixel(cx + 1, 14, 40, 120, 240)
        set_pixel(cx, 15, 220, 40, 40)      # Base chassis
        set_pixel(cx + 1, 15, 220, 40, 40)

        # 4. Render Held Coins in Hands
        if self.held_count > 0:
            hr, hg, hb = get_coin_color(self.held_denom)
            set_pixel(cx, 14, hr, hg, hb)
            set_pixel(cx + 1, 14, hr, hg, hb)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "stage": self.stage,
            "cursor_col": self.cursor_col,
            "held_denom": self.held_denom,
            "held_count": self.held_count,
            "total_coins": sum(len(col) for col in self.grid),
        }
