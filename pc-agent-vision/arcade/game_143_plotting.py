# -*- coding: utf-8 -*-
"""
Game #143: 翻转方块 (Plotting / Flipull 1989 / Taito)
街机历史上最经典的横向投掷置换消解与重力沉降益智消除游戏：
升降台垂直滑轨对准目标行、按键A水平投掷手牌方块撞击同色消除并置换异色手牌、
按键B发射全消彩虹万能弹、重力级联崩落与限时清消达成通关。
"""

from typing import List, Dict, Any, Optional
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

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_NO_MOVES = 2
STATE_GAME_OVER = 3

COLOR_RED = 1
COLOR_BLUE = 2
COLOR_GREEN = 3
COLOR_YELLOW = 4


class Game143Plotting(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.time_left = 45.0
        self.blocks_cleared = 0
        self.target_blocks = 12

        # Player paddle pos on vertical rail (x=1, py in [2..13])
        self.py = 6.0
        self.hand_block = COLOR_RED
        self.wildcards_left = 2

        # Flying projectile block
        self.projectile: Optional[Dict[str, Any]] = None

        # 16x16 grid board: 0 = empty, 1..4 = block colors
        self.board = [[0 for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 143

    @property
    def name(self) -> str:
        return "翻转方块"

    @property
    def english_name(self) -> str:
        return "Plotting"

    @property
    def release_year(self) -> int:
        return 1989

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "横向投掷几何方块同色撞击消除、异色撞击置换手牌、重力沉降级联消除与彩虹万能弹"

    def get_name(self) -> str:
        return "Plotting (1989)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.time_left = 45.0
        self.blocks_cleared = 0
        self.target_blocks = 12 + (self.level - 1) * 3
        self.py = 6.0
        self.hand_block = COLOR_RED
        self.wildcards_left = 2
        self.projectile = None

        # Clear board
        for y in range(16):
            for x in range(16):
                self.board[y][x] = 0

        # Construct stacked puzzle matrix (cols 6..13, rows 3..12)
        pattern = [
            [1, 1, 2, 2, 3, 3],
            [2, 2, 3, 3, 1, 1],
            [3, 3, 1, 1, 2, 2],
            [1, 2, 3, 1, 2, 3],
            [2, 3, 1, 2, 3, 1],
            [3, 1, 2, 3, 1, 2],
        ]
        for r_idx, row in enumerate(pattern):
            y = 5 + r_idx
            for c_idx, val in enumerate(row):
                x = 7 + c_idx
                self.board[y][x] = val

    def _apply_gravity(self) -> None:
        # For each column in board, drop blocks downward
        for x in range(6, 15):
            write_y = 13
            for y in range(13, 2, -1):
                if self.board[y][x] != 0:
                    val = self.board[y][x]
                    self.board[y][x] = 0
                    self.board[write_y][x] = val
                    write_y -= 1

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_NO_MOVES):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_NO_MOVES:
                    if self.lives > 0:
                        self._init_level()
                    else:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.state_timer += dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()

    def _update_playing(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.time_left -= dt
        if self.time_left <= 0.0:
            self.time_left = 0.0
            self.lives -= 1
            self.state = STATE_NO_MOVES
            self.state_timer = 0.0
            return

        # Paddle vertical movement
        rail_speed = 8.0
        if buttons & KEY_UP:
            self.py = max(3.0, self.py - rail_speed * dt)
        if buttons & KEY_DOWN:
            self.py = min(12.0, self.py + rail_speed * dt)

        # 1. Fire Projectile: Key A (Normal Throw)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.projectile is None:
                row_y = int(round(self.py))
                self.projectile = {
                    "x": 2.0,
                    "y": float(row_y),
                    "color": self.hand_block,
                    "is_wildcard": False,
                }

        # 2. Fire Wildcard Laser Block: Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.projectile is None and self.wildcards_left > 0:
                self.wildcards_left -= 1
                row_y = int(round(self.py))
                self.projectile = {
                    "x": 2.0,
                    "y": float(row_y),
                    "color": 99,  # Wildcard
                    "is_wildcard": True,
                }

        # 3. Update Flying Projectile
        if self.projectile:
            p = self.projectile
            p["x"] += 20.0 * dt
            target_x = int(round(p["x"]))
            target_y = int(round(p["y"]))

            # Check collision with block on grid or wall
            hit = False
            if target_x >= 14:
                hit = True
                self.projectile = None
            elif target_x >= 6:
                if self.board[target_y][target_x] != 0:
                    hit = True
                    hit_color = self.board[target_y][target_x]

                    if p["is_wildcard"]:
                        # Wildcard clears entire row segment!
                        for x in range(target_x, 14):
                            if self.board[target_y][x] != 0:
                                self.board[target_y][x] = 0
                                self.blocks_cleared += 1
                                self.score += 100
                        self._apply_gravity()
                        self.projectile = None
                    elif p["color"] == hit_color:
                        # Identical match: clear cluster along row!
                        curr_x = target_x
                        while curr_x < 14 and self.board[target_y][curr_x] == hit_color:
                            self.board[target_y][curr_x] = 0
                            self.blocks_cleared += 1
                            self.score += 50
                            curr_x += 1
                        # If a different block is right behind it, swap into hand!
                        if curr_x < 14 and self.board[target_y][curr_x] != 0:
                            self.hand_block = self.board[target_y][curr_x]
                        self._apply_gravity()
                        self.projectile = None
                    else:
                        # Mismatch: swap hand block with hit block!
                        self.board[target_y][target_x] = p["color"]
                        self.hand_block = hit_color
                        self.score += 20
                        self.projectile = None

                    # Check stage clear quota
                    if self.blocks_cleared >= self.target_blocks:
                        self.score += 1000
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 0.0
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

        def get_color_rgb(c: int) -> tuple[int, int, int]:
            if c == COLOR_RED:
                return (240, 40, 40)
            elif c == COLOR_BLUE:
                return (40, 120, 240)
            elif c == COLOR_GREEN:
                return (40, 220, 60)
            elif c == COLOR_YELLOW:
                return (240, 220, 40)
            elif c == 99:
                return (255, 255, 255)
            return (0, 0, 0)

        # 1. Render Left Vertical Rail (x=0)
        for y in range(2, 14):
            set_pixel(0, y, 60, 60, 80)

        # 2. Render Player Paddle & Hand Block (x=1)
        py_i = int(round(self.py))
        set_pixel(1, py_i, 220, 220, 240)
        set_pixel(1, py_i - 1, 160, 160, 180)
        set_pixel(1, py_i + 1, 160, 160, 180)

        # Hand block at x=2
        rgb = get_color_rgb(self.hand_block)
        set_pixel(2, py_i, rgb[0], rgb[1], rgb[2])

        # 3. Render Flying Projectile
        if self.projectile:
            px = int(round(self.projectile["x"]))
            py = int(round(self.projectile["y"]))
            prgb = get_color_rgb(self.projectile["color"])
            set_pixel(px, py, prgb[0], prgb[1], prgb[2])
            set_pixel(px - 1, py, 255, 255, 255)  # Trail flash

        # 4. Render Board Blocks
        for y in range(16):
            for x in range(16):
                val = self.board[y][x]
                if val != 0:
                    brgb = get_color_rgb(val)
                    set_pixel(x, y, brgb[0], brgb[1], brgb[2])

        # 5. Right Wall (x=14)
        for y in range(2, 14):
            set_pixel(14, y, 90, 70, 60)

        # 6. Wildcards indicator (Row 15)
        for w in range(min(self.wildcards_left, 3)):
            set_pixel(2 + w * 2, 15, 255, 255, 255)

        # 7. Quota Progress (Row 0)
        quota_p = int(round((self.blocks_cleared / float(self.target_blocks)) * 15.0))
        for x in range(min(16, quota_p + 1)):
            set_pixel(x, 0, 50, 220, 60)

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
            "time_left": self.time_left,
            "blocks_cleared": self.blocks_cleared,
            "target_blocks": self.target_blocks,
            "py": self.py,
            "hand_block": self.hand_block,
            "wildcards": self.wildcards_left,
        }
