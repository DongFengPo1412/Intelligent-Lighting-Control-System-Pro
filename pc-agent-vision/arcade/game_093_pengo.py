"""
Game #093: 敲冰块 / 企鹅推冰块 (Pengo 1982 / Sega / Coreland)
Sliding ice blocks across maze squishing Sno-Bees, shattering blocked ice, perimeter wall shaking & diamond alignment flash.
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

STATE_PLAYING = 0
STATE_PENGO_HIT = 1
STATE_ROUND_CLEAR = 2
STATE_GAME_OVER = 3

BLOCK_EMPTY = 0
BLOCK_ICE = 1
BLOCK_DIAMOND = 2
BLOCK_WALL = 3

GRID_SIZE = 16
MAX_SNOBEES = 3


class Game093Pengo(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.snobees_crushed = 0

        # Pengo
        self.px = 7
        self.py = 13
        self.facing_x = 0
        self.facing_y = -1
        self.move_cooldown = 0.0

        # Grid
        self.grid: List[List[int]] = [[BLOCK_EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Sliding block
        self.sliding_active = False
        self.sl_x = 0.0
        self.sl_y = 0.0
        self.sl_vx = 0.0
        self.sl_vy = 0.0
        self.sl_is_diamond = False

        self.snobees: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 93

    @property
    def name(self) -> str:
        return "企鹅推冰块"

    @property
    def english_name(self) -> str:
        return "Pengo"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "推滑冰块碾压击杀、粉碎开路、震墙晕怪与对齐三钻闪光"

    def get_name(self) -> str:
        return "Pengo (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._reset_maze(hard_reset=True)

    def _reset_maze(self, hard_reset: bool = False) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.snobees_crushed = 0

        self.px = 7
        self.py = 13
        self.facing_x = 0
        self.facing_y = -1
        self.move_cooldown = 0.0

        self.sliding_active = False

        self.grid = [[BLOCK_EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    self.grid[y][x] = BLOCK_WALL
                else:
                    self.grid[y][x] = BLOCK_EMPTY

        for y in range(2, 13, 2):
            for x in range(2, 14, 2):
                self.grid[y][x] = BLOCK_ICE

        self.grid[4][4] = BLOCK_DIAMOND
        self.grid[4][10] = BLOCK_DIAMOND
        self.grid[8][7] = BLOCK_DIAMOND

        self.grid[13][7] = BLOCK_EMPTY
        self.grid[12][7] = BLOCK_EMPTY

        self.snobees = []
        spawn_pos = [(2, 2), (13, 2), (7, 2)]
        for i in range(MAX_SNOBEES):
            self.snobees.append({
                "x": spawn_pos[i][0],
                "y": spawn_pos[i][1],
                "stun_timer": 0.0,
                "move_timer": 0.0,
                "respawn_timer": 0.0,
                "active": True,
            })
            self.grid[spawn_pos[i][1]][spawn_pos[i][0]] = BLOCK_EMPTY

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_PENGO_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_maze(hard_reset=False)
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 2.0:
                self.round += 1
                self._reset_maze(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_sliding_block(dt)
        self._update_snobees(dt)

        if self.snobees_crushed >= 4:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.move_cooldown > 0.0:
            self.move_cooldown -= dt

        if self.move_cooldown <= 0.0:
            dx, dy = 0, 0
            if buttons & KEY_LEFT:
                dx, dy = -1, 0
            elif buttons & KEY_RIGHT:
                dx, dy = 1, 0
            elif buttons & KEY_UP:
                dx, dy = 0, -1
            elif buttons & KEY_DOWN:
                dx, dy = 0, 1

            if dx != 0 or dy != 0:
                self.facing_x = dx
                self.facing_y = dy
                nx = self.px + dx
                ny = self.py + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if self.grid[ny][nx] == BLOCK_EMPTY:
                        self.px = nx
                        self.py = ny
                        self.move_cooldown = 0.14

        # Push / Crush ice block (Button A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not self.sliding_active:
                tx = self.px + self.facing_x
                ty = self.py + self.facing_y
                if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                    target = self.grid[ty][tx]
                    if target in (BLOCK_ICE, BLOCK_DIAMOND):
                        bx = tx + self.facing_x
                        by = ty + self.facing_y
                        if 0 <= bx < GRID_SIZE and 0 <= by < GRID_SIZE and self.grid[by][bx] == BLOCK_EMPTY:
                            self.sliding_active = True
                            self.sl_x = float(tx)
                            self.sl_y = float(ty)
                            self.sl_vx = float(self.facing_x) * 12.0
                            self.sl_vy = float(self.facing_y) * 12.0
                            self.sl_is_diamond = (target == BLOCK_DIAMOND)
                            self.grid[ty][tx] = BLOCK_EMPTY
                            self.score += 20
                        else:
                            if target == BLOCK_ICE:
                                self.grid[ty][tx] = BLOCK_EMPTY
                                self.score += 100

        # Shake wall (Button B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            tx = self.px + self.facing_x
            ty = self.py + self.facing_y
            if tx <= 0 or tx >= 15 or ty <= 0 or ty >= 15:
                self.score += 50
                for b in self.snobees:
                    if b["active"]:
                        if b["x"] in (1, 14) or b["y"] in (1, 14):
                            b["stun_timer"] = 3.5

    def _update_sliding_block(self, dt: float) -> None:
        if not self.sliding_active:
            return

        self.sl_x += self.sl_vx * dt
        self.sl_y += self.sl_vy * dt

        cx = int(round(self.sl_x))
        cy = int(round(self.sl_y))

        # Check squishing Sno-Bees
        for b in self.snobees:
            if b["active"]:
                dist = abs(self.sl_x - b["x"]) + abs(self.sl_y - b["y"])
                if dist < 1.0:
                    b["active"] = False
                    b["respawn_timer"] = 2.0
                    self.score += 400
                    self.snobees_crushed += 1

        # Check collision ahead
        dir_x = 1 if self.sl_vx > 0.0 else (-1 if self.sl_vx < 0.0 else 0)
        dir_y = 1 if self.sl_vy > 0.0 else (-1 if self.sl_vy < 0.0 else 0)

        next_x = cx + dir_x
        next_y = cy + dir_y

        hit = False
        if next_x <= 0 or next_x >= 15 or next_y <= 0 or next_y >= 15:
            hit = True
        elif self.grid[next_y][next_x] != BLOCK_EMPTY:
            hit = True

        if hit:
            cx = max(1, min(14, cx))
            cy = max(1, min(14, cy))
            self.grid[cy][cx] = BLOCK_DIAMOND if self.sl_is_diamond else BLOCK_ICE
            self.sliding_active = False

            if self.sl_is_diamond:
                self._check_diamond_alignment()

    def _check_diamond_alignment(self) -> None:
        diamonds = []
        for y in range(1, 15):
            for x in range(1, 15):
                if self.grid[y][x] == BLOCK_DIAMOND:
                    diamonds.append((x, y))

        if len(diamonds) == 3:
            dxs = [d[0] for d in diamonds]
            dys = [d[1] for d in diamonds]

            horiz = (dys[0] == dys[1] == dys[2]) and (abs(dxs[0] - dxs[1]) <= 2 and abs(dxs[1] - dxs[2]) <= 2)
            vert = (dxs[0] == dxs[1] == dxs[2]) and (abs(dys[0] - dys[1]) <= 2 and abs(dys[1] - dys[2]) <= 2)

            if horiz or vert:
                self.score += 5000
                for b in self.snobees:
                    if b["active"]:
                        b["stun_timer"] = 5.0

    def _update_snobees(self, dt: float) -> None:
        for idx, b in enumerate(self.snobees):
            if not b["active"]:
                if b["respawn_timer"] > 0.0:
                    b["respawn_timer"] -= dt
                else:
                    b["active"] = True
                    b["stun_timer"] = 0.0
                    b["x"] = 2 + (idx * 5) % 12
                    b["y"] = 2
                    self.grid[b["y"]][b["x"]] = BLOCK_EMPTY
                continue

            if b["stun_timer"] > 0.0:
                b["stun_timer"] -= dt
                if b["x"] == self.px and b["y"] == self.py:
                    b["active"] = False
                    b["respawn_timer"] = 2.0
                    self.score += 100
                    self.snobees_crushed += 1
                continue

            b["move_timer"] += dt
            if b["move_timer"] >= 0.28:
                b["move_timer"] = 0.0

                dx = 1 if self.px > b["x"] else (-1 if self.px < b["x"] else 0)
                dy = 1 if self.py > b["y"] else (-1 if self.py < b["y"] else 0)

                nx = b["x"] + dx
                ny = b["y"]

                if dx != 0 and 1 <= nx <= 14 and self.grid[ny][nx] == BLOCK_EMPTY:
                    b["x"] = nx
                else:
                    ny = b["y"] + dy
                    nx = b["x"]
                    if dy != 0 and 1 <= ny <= 14 and self.grid[ny][nx] == BLOCK_EMPTY:
                        b["y"] = ny

                if b["x"] == self.px and b["y"] == self.py:
                    self.state = STATE_PENGO_HIT
                    self.state_timer = 0.0
                    break

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

        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                cell = self.grid[y][x]
                if cell == BLOCK_WALL:
                    set_pixel(x, y, 0, 130, 240)
                elif cell == BLOCK_ICE:
                    set_pixel(x, y, 160, 230, 255)
                elif cell == BLOCK_DIAMOND:
                    set_pixel(x, y, 255, 215, 0)

        if self.sliding_active:
            sx = int(round(self.sl_x))
            sy = int(round(self.sl_y))
            if self.sl_is_diamond:
                set_pixel(sx, sy, 255, 230, 60)
            else:
                set_pixel(sx, sy, 220, 250, 255)

        for b in self.snobees:
            if not b["active"]:
                continue
            if b["stun_timer"] > 0.0:
                set_pixel(b["x"], b["y"], 40, 180, 255)
            else:
                set_pixel(b["x"], b["y"], 220, 200, 30)

        if self.state == STATE_PENGO_HIT:
            set_pixel(self.px, self.py, 255, 60, 60)
            set_pixel(self.px, self.py - 1, 255, 220, 0)
        else:
            set_pixel(self.px, self.py, 230, 30, 30)
            set_pixel(self.px + self.facing_x, self.py + self.facing_y, 255, 200, 0)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 80, 80)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "round": self.round,
            "snobees_crushed": self.snobees_crushed,
            "player_x": self.px,
            "player_y": self.py,
        }
