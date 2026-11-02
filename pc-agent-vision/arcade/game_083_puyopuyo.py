"""
Game #083: 魔法气泡 / 噗哟噗哟 (Puyo Puyo 1991 / Compile / Sega)
Falling Gelatinous Puyo Pairs, 4+ Connected Color Match Flood Fill & Cascade Chain Reactions.
"""

from typing import List, Dict, Any
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
STATE_CHAIN_RESOLVE = 1
STATE_GAME_OVER = 2

PUYO_EMPTY = 0
PUYO_RED = 1
PUYO_GREEN = 2
PUYO_BLUE = 3
PUYO_YELLOW = 4
PUYO_GARBAGE = 5

COLS = 6
ROWS = 13


class Game083PuyoPuyo(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.current_chain = 0
        self.max_chain = 0

        self.grid = [[PUYO_EMPTY for _ in range(COLS)] for _ in range(ROWS)]

        self.cur_col = 2
        self.cur_row = 1.0
        self.puyo_main = PUYO_RED
        self.puyo_sub = PUYO_GREEN
        self.sub_offset_x = 0
        self.sub_offset_y = -1

        self.reset()

    @property
    def game_id(self) -> int:
        return 83

    @property
    def name(self) -> str:
        return "魔法气泡"

    @property
    def english_name(self) -> str:
        return "Puyo Puyo"

    @property
    def release_year(self) -> int:
        return 1991

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "软体双联气泡旋转下落 + 四连邻接粘合消除 + 重力阶梯连锁反应"

    def get_name(self) -> str:
        return "Puyo Puyo (1991)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.current_chain = 0
        self.max_chain = 0
        self.clear_board()
        self.spawn_pair()

    def clear_board(self):
        self.grid = [[PUYO_EMPTY for _ in range(COLS)] for _ in range(ROWS)]

    def get_cell(self, col: int, row: int) -> int:
        if 0 <= col < COLS and 0 <= row < ROWS:
            return self.grid[row][col]
        return PUYO_EMPTY

    def spawn_pair(self):
        import random
        self.cur_col = 2
        self.cur_row = 1.0
        self.sub_offset_x = 0
        self.sub_offset_y = -1

        colors = [PUYO_RED, PUYO_GREEN, PUYO_BLUE, PUYO_YELLOW]
        self.puyo_main = random.choice(colors)
        self.puyo_sub = random.choice(colors)

        if self.grid[1][2] != PUYO_EMPTY:
            self.state = STATE_GAME_OVER
            self.state_timer = 0.0

    def rotate_pair(self, direction: int):
        old_ox = self.sub_offset_x
        old_oy = self.sub_offset_y

        if direction > 0:  # CW: (0,-1) -> (1,0) -> (0,1) -> (-1,0)
            new_ox = -old_oy
            new_oy = old_ox
        else:
            new_ox = old_oy
            new_oy = -old_ox

        test_col = self.cur_col + new_ox
        r = int(self.cur_row)

        if test_col < 0:
            if self.cur_col + 1 < COLS and self.grid[r][self.cur_col + 1] == PUYO_EMPTY:
                self.cur_col += 1
            else:
                return
        elif test_col >= COLS:
            if self.cur_col - 1 >= 0 and self.grid[r][self.cur_col - 1] == PUYO_EMPTY:
                self.cur_col -= 1
            else:
                return

        test_col = self.cur_col + new_ox
        test_row = r + new_oy
        if 0 <= test_col < COLS and 0 <= test_row < ROWS:
            if self.grid[test_row][test_col] == PUYO_EMPTY:
                self.sub_offset_x = new_ox
                self.sub_offset_y = new_oy

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_CHAIN_RESOLVE:
            if self.state_timer > 0.35:
                self.state_timer = 0.0
                fell = self.apply_gravity()
                if fell:
                    return

                matched = self.check_matches()
                if matched:
                    self.current_chain += 1
                    if self.current_chain > self.max_chain:
                        self.max_chain = self.current_chain
                    self.score += 100 * (1 << self.current_chain)
                else:
                    self.current_chain = 0
                    if self.grid[1][2] != PUYO_EMPTY:
                        self.state = STATE_GAME_OVER
                    else:
                        self.state = STATE_PLAYING
                        self.spawn_pair()
            return

        # Lateral shift
        r = int(self.cur_row)
        if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
            if self.cur_col > 0 and self.grid[r][self.cur_col - 1] == PUYO_EMPTY:
                sub_c = self.cur_col - 1 + self.sub_offset_x
                sub_r = r + self.sub_offset_y
                if sub_c >= 0 and (sub_r < 0 or self.grid[sub_r][sub_c] == PUYO_EMPTY):
                    self.cur_col -= 1

        if (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
            if self.cur_col + 1 < COLS and self.grid[r][self.cur_col + 1] == PUYO_EMPTY:
                sub_c = self.cur_col + 1 + self.sub_offset_x
                sub_r = r + self.sub_offset_y
                if sub_c < COLS and (sub_r < 0 or self.grid[sub_r][sub_c] == PUYO_EMPTY):
                    self.cur_col += 1

        # Rotations
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.rotate_pair(1)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.rotate_pair(-1)

        # Drop speed
        speed = 12.0 if (buttons & KEY_DOWN) else 1.5
        self.cur_row += speed * dt

        r_main = int(self.cur_row)
        r_sub = r_main + self.sub_offset_y
        c_sub = self.cur_col + self.sub_offset_x

        hit_ground = False
        if r_main >= ROWS - 1 or r_sub >= ROWS - 1:
            hit_ground = True
        else:
            if r_main + 1 < ROWS and self.grid[r_main + 1][self.cur_col] != PUYO_EMPTY:
                hit_ground = True
            if 0 <= r_sub + 1 < ROWS and self.grid[r_sub + 1][c_sub] != PUYO_EMPTY:
                hit_ground = True

        if hit_ground:
            self.drop_pair()

    def drop_pair(self):
        r_main = min(ROWS - 1, max(0, int(self.cur_row)))
        r_sub = min(ROWS - 1, max(0, r_main + self.sub_offset_y))
        c_sub = self.cur_col + self.sub_offset_x

        self.grid[r_main][self.cur_col] = self.puyo_main
        self.grid[r_sub][c_sub] = self.puyo_sub

        self.apply_gravity()

        self.state = STATE_CHAIN_RESOLVE
        self.state_timer = 0.0
        self.current_chain = 0

    def apply_gravity(self) -> bool:
        moved = False
        for c in range(COLS):
            for r in range(ROWS - 2, -1, -1):
                if self.grid[r][c] != PUYO_EMPTY and self.grid[r + 1][c] == PUYO_EMPTY:
                    fall_to = r
                    while fall_to + 1 < ROWS and self.grid[fall_to + 1][c] == PUYO_EMPTY:
                        fall_to += 1
                    self.grid[fall_to][c] = self.grid[r][c]
                    self.grid[r][c] = PUYO_EMPTY
                    moved = True
        return moved

    def check_matches(self) -> bool:
        visited = [[False for _ in range(COLS)] for _ in range(ROWS)]
        to_clear = [[False for _ in range(COLS)] for _ in range(ROWS)]
        any_cleared = False

        dr = [-1, 1, 0, 0]
        dc = [0, 0, -1, 1]

        for r in range(ROWS):
            for c in range(COLS):
                color = self.grid[r][c]
                if color in (PUYO_EMPTY, PUYO_GARBAGE) or visited[r][c]:
                    continue

                group = []
                queue = [(r, c)]
                visited[r][c] = True

                while queue:
                    cr, cc = queue.pop(0)
                    group.append((cr, cc))

                    for d in range(4):
                        nr, nc = cr + dr[d], cc + dc[d]
                        if 0 <= nr < ROWS and 0 <= nc < COLS:
                            if not visited[nr][nc] and self.grid[nr][nc] == color:
                                visited[nr][nc] = True
                                queue.append((nr, nc))

                if len(group) >= 4:
                    any_cleared = True
                    for gr, gc in group:
                        to_clear[gr][gc] = True
                        for d in range(4):
                            ar, ac = gr + dr[d], gc + dc[d]
                            if 0 <= ar < ROWS and 0 <= ac < COLS:
                                if self.grid[ar][ac] == PUYO_GARBAGE:
                                    to_clear[ar][ac] = True

        if any_cleared:
            for r in range(ROWS):
                for c in range(COLS):
                    if to_clear[r][c]:
                        self.grid[r][c] = PUYO_EMPTY

        return any_cleared

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Backdrop
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 15, 20, 35)

        # 2. Well Borders (Columns x: 4..9, walls at 3 & 10, floor at 15)
        for y in range(2, 16):
            set_pixel(3, y, 100, 100, 150)
            set_pixel(10, y, 100, 100, 150)
        for x in range(3, 11):
            set_pixel(x, 15, 100, 100, 150)

        color_map = {
            PUYO_RED: (255, 40, 40),
            PUYO_GREEN: (30, 220, 40),
            PUYO_BLUE: (40, 120, 255),
            PUYO_YELLOW: (255, 220, 20),
            PUYO_GARBAGE: (180, 180, 180),
        }

        # 3. Grid
        for r in range(ROWS):
            for c in range(COLS):
                val = self.grid[r][c]
                if val != PUYO_EMPTY and val in color_map:
                    pr, pg, pb = color_map[val]
                    set_pixel(4 + c, 2 + r, pr, pg, pb)

        # 4. Falling pair
        if self.state == STATE_PLAYING:
            r_main = int(self.cur_row)
            r_sub = r_main + self.sub_offset_y
            c_sub = self.cur_col + self.sub_offset_x

            if 0 <= r_main < ROWS and self.puyo_main in color_map:
                mr, mg, mb = color_map[self.puyo_main]
                set_pixel(4 + self.cur_col, 2 + r_main, mr, mg, mb)

            if 0 <= r_sub < ROWS and self.puyo_sub in color_map:
                sr, sg, sb = color_map[self.puyo_sub]
                set_pixel(4 + c_sub, 2 + r_sub, sr, sg, sb)

        # 5. Chain combo spark
        if self.current_chain > 0:
            for i in range(min(10, self.current_chain * 2)):
                set_pixel(1, 14 - i, 255, 200, 0)

        # 6. Score Bar
        score_dots = min(15, self.score // 500)
        for s in range(score_dots):
            set_pixel(s, 0, 50, 200, 255)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "current_chain": self.current_chain,
            "max_chain": self.max_chain,
            "cur_col": self.cur_col,
            "cur_row": self.cur_row,
        }
