"""
Game #102: 宝石方块 (Columns 1990 / Sega)
Ancient Greek temple jewel puzzle: falling 3-gem column cycling,
horizontal, vertical and diagonal 3-match shattering, and cascading gravity collapse chain reactions.
"""

from typing import List, Dict, Any
import math
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)

STATE_FALLING = 0
STATE_FLASHING_MATCH = 1
STATE_COLLAPSING = 2
STATE_GAME_OVER = 3

BOARD_COLS = 6
BOARD_ROWS = 13
NUM_GEM_TYPES = 5


class Game102Columns(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FALLING
        self.state_timer = 0.0
        self.score = 0
        self.level = 1
        self.matches_cleared = 0
        self.chain_count = 0

        self.fall_speed = 1.5
        self.move_cooldown = 0.0

        self.board: List[List[int]] = []
        self.matched_mask: List[List[bool]] = []
        self.cur_gems: List[int] = [1, 2, 3]
        self.cur_col = 2
        self.cur_y = 2.0
        self._seed = 0x5E6A1990

        self.reset()

    @property
    def game_id(self) -> int:
        return 102

    @property
    def name(self) -> str:
        return "宝石方块"

    @property
    def english_name(self) -> str:
        return "Columns"

    @property
    def release_year(self) -> int:
        return 1990

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "三色宝石三联柱循环轮换、横纵斜三向三连消除与连锁下落大塌方"

    def get_name(self) -> str:
        return "Columns (1990)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.level = 1
        self.matches_cleared = 0
        self.chain_count = 0
        self.state = STATE_FALLING
        self.state_timer = 0.0
        self.fall_speed = 1.5
        self.move_cooldown = 0.0

        self.board = [[0 for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        self.matched_mask = [[False for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]

        self.spawn_new_column()

    def _next_gem(self) -> int:
        self._seed = (self._seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._seed % NUM_GEM_TYPES) + 1

    def spawn_new_column(self) -> None:
        self.cur_col = 2
        self.cur_y = 2.0
        self.cur_gems = [self._next_gem(), self._next_gem(), self._next_gem()]

        if (
            self.board[2][self.cur_col] != 0
            or self.board[1][self.cur_col] != 0
            or self.board[0][self.cur_col] != 0
        ):
            self.state = STATE_GAME_OVER
            self.state_timer = 0.0

    def cycle_column(self) -> None:
        temp = self.cur_gems[2]
        self.cur_gems[2] = self.cur_gems[1]
        self.cur_gems[1] = self.cur_gems[0]
        self.cur_gems[0] = temp

    def force_place_column(
        self, col: int, base_row: int, g0: int, g1: int, g2: int
    ) -> None:
        if 0 <= col < BOARD_COLS and 2 <= base_row < BOARD_ROWS:
            self.board[base_row - 2][col] = g0
            self.board[base_row - 1][col] = g1
            self.board[base_row][col] = g2

    def check_placement_collision(self, col: int, row_bot: int) -> bool:
        if row_bot >= BOARD_ROWS:
            return True
        if col < 0 or col >= BOARD_COLS:
            return True
        if row_bot >= 0 and self.board[row_bot][col] != 0:
            return True
        return False

    def lock_current_column(self) -> None:
        row_bot = int(self.cur_y)
        if 0 <= row_bot < BOARD_ROWS:
            self.board[row_bot][self.cur_col] = self.cur_gems[2]
        if 0 <= row_bot - 1 < BOARD_ROWS:
            self.board[row_bot - 1][self.cur_col] = self.cur_gems[1]
        if 0 <= row_bot - 2 < BOARD_ROWS:
            self.board[row_bot - 2][self.cur_col] = self.cur_gems[0]

        self.chain_count = 0
        if self.find_matches():
            self.state = STATE_FLASHING_MATCH
            self.state_timer = 0.0
        else:
            self.spawn_new_column()

    def find_matches(self) -> bool:
        self.matched_mask = [[False for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        found = False

        # 1. Horizontal
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS - 2):
                g = self.board[r][c]
                if g != 0 and self.board[r][c + 1] == g and self.board[r][c + 2] == g:
                    self.matched_mask[r][c] = True
                    self.matched_mask[r][c + 1] = True
                    self.matched_mask[r][c + 2] = True
                    found = True

        # 2. Vertical
        for r in range(BOARD_ROWS - 2):
            for c in range(BOARD_COLS):
                g = self.board[r][c]
                if g != 0 and self.board[r + 1][c] == g and self.board[r + 2][c] == g:
                    self.matched_mask[r][c] = True
                    self.matched_mask[r + 1][c] = True
                    self.matched_mask[r + 2][c] = True
                    found = True

        # 3. Diagonal Down-Right
        for r in range(BOARD_ROWS - 2):
            for c in range(BOARD_COLS - 2):
                g = self.board[r][c]
                if g != 0 and self.board[r + 1][c + 1] == g and self.board[r + 2][c + 2] == g:
                    self.matched_mask[r][c] = True
                    self.matched_mask[r + 1][c + 1] = True
                    self.matched_mask[r + 2][c + 2] = True
                    found = True

        # 4. Diagonal Down-Left
        for r in range(BOARD_ROWS - 2):
            for c in range(2, BOARD_COLS):
                g = self.board[r][c]
                if g != 0 and self.board[r + 1][c - 1] == g and self.board[r + 2][c - 2] == g:
                    self.matched_mask[r][c] = True
                    self.matched_mask[r + 1][c - 1] = True
                    self.matched_mask[r + 2][c - 2] = True
                    found = True

        return found

    def clear_matches(self) -> None:
        count = 0
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if self.matched_mask[r][c]:
                    self.board[r][c] = 0
                    count += 1
        self.score += count * 100 * (self.chain_count + 1)
        self.matches_cleared += count
        self.level = 1 + (self.matches_cleared // 15)
        self.fall_speed = 1.5 + float(self.level) * 0.4

    def apply_gravity_collapse(self) -> bool:
        shifted = False
        for c in range(BOARD_COLS):
            write_row = BOARD_ROWS - 1
            for r in range(BOARD_ROWS - 1, -1, -1):
                if self.board[r][c] != 0:
                    if write_row != r:
                        self.board[write_row][c] = self.board[r][c]
                        self.board[r][c] = 0
                        shifted = True
                    write_row -= 1
        return shifted

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt
        self.move_cooldown -= dt

        if self.state == STATE_FLASHING_MATCH:
            if self.state_timer > 0.45:
                self.clear_matches()
                self.apply_gravity_collapse()
                self.state = STATE_COLLAPSING
                self.state_timer = 0.0
            return

        if self.state == STATE_COLLAPSING:
            if self.state_timer > 0.25:
                if self.find_matches():
                    self.chain_count += 1
                    self.state = STATE_FLASHING_MATCH
                    self.state_timer = 0.0
                else:
                    self.spawn_new_column()
                    self.state = STATE_FALLING
                    self.state_timer = 0.0
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        # Lateral movement
        if self.move_cooldown <= 0.0:
            if buttons & KEY_LEFT:
                if self.cur_col > 0 and not self.check_placement_collision(
                    self.cur_col - 1, int(self.cur_y)
                ):
                    self.cur_col -= 1
                    self.move_cooldown = 0.12
            elif buttons & KEY_RIGHT:
                if self.cur_col < BOARD_COLS - 1 and not self.check_placement_collision(
                    self.cur_col + 1, int(self.cur_y)
                ):
                    self.cur_col += 1
                    self.move_cooldown = 0.12

        # Button A: Cycle column jewels
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.cycle_column()

        # Button B or Down
        spd = self.fall_speed
        if buttons & KEY_DOWN:
            spd = 12.0
            self.score += 1
        elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
            while not self.check_placement_collision(self.cur_col, int(self.cur_y + 1.0)):
                self.cur_y += 1.0
                self.score += 2
            self.lock_current_column()
            return

        next_y = self.cur_y + spd * dt
        if self.check_placement_collision(self.cur_col, int(next_y)):
            self.lock_current_column()
        else:
            self.cur_y = next_y

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(len(fb)):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        gem_colors = [
            (0, 0, 0),
            (255, 30, 30),   # 1: Ruby
            (30, 220, 50),   # 2: Emerald
            (30, 100, 255),  # 3: Sapphire
            (255, 220, 20),  # 4: Topaz
            (180, 40, 220),  # 5: Amethyst
        ]

        # Classical Columns pillars
        for y in range(16):
            pr = 180 if (y % 2 == 0) else 150
            pg = 170 if (y % 2 == 0) else 140
            pb = 140 if (y % 2 == 0) else 110
            set_pixel(3, y, pr, pg, pb)
            set_pixel(4, y, pr - 30, pg - 30, pb - 30)
            set_pixel(11, y, pr - 30, pg - 30, pb - 30)
            set_pixel(12, y, pr, pg, pb)

        for x in range(3, 13):
            set_pixel(x, 15, 200, 190, 160)

        # Board
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                g = self.board[r][c]
                if g != 0:
                    px = 5 + c
                    py = 2 + r
                    if self.state == STATE_FLASHING_MATCH and self.matched_mask[r][c]:
                        set_pixel(px, py, 255, 255, 255)
                    else:
                        cr, cg, cb = gem_colors[g]
                        set_pixel(px, py, cr, cg, cb)

        # Falling column
        if self.state == STATE_FALLING:
            col_x = 5 + self.cur_col
            bot_y = 2 + int(self.cur_y)
            for i in range(3):
                gem_y = bot_y - (2 - i)
                if 2 <= gem_y <= 14:
                    cr, cg, cb = gem_colors[self.cur_gems[i]]
                    set_pixel(col_x, gem_y, cr, cg, cb)

        # Level on left border
        for l in range(min(self.level, 5)):
            set_pixel(0, 14 - l * 2, 255, 200, 0)
        if self.chain_count > 0:
            for ch in range(min(self.chain_count, 4)):
                set_pixel(1, 14 - ch * 2, 255, 60, 200)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "level": self.level,
            "chain_count": self.chain_count,
            "cur_col": self.cur_col,
            "cur_y": self.cur_y,
            "cur_gems": list(self.cur_gems),
            "matches_cleared": self.matches_cleared,
        }
