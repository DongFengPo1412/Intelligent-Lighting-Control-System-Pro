# -*- coding: utf-8 -*-
"""game_042_puyo_puyo.py —— 目标 #042 彩球连锁 (Puyo Puyo)
6x12 井道双联彩球下落旋转 + 悬空半截重力分离 + 4连通洪泛消除与阶梯连锁反应
"""

from typing import Dict, Any, Tuple
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

PUYO_RGB = {
    1: (250, 45, 55),
    2: (40, 230, 75),
    3: (50, 140, 255),
    4: (255, 220, 30),
}


class Game042PuyoPuyo(BaseCartridge):
    COLS = 6
    ROWS = 12

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.grid = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.cur_col = 2
        self.cur_row = 1
        self.cur_rot = 0
        self.main_color = 1
        self.sub_color = 2
        self.next_main = 3
        self.next_sub = 4
        self.last_chain = 0
        self.max_chain = 0
        self._seed = 0x42199101
        self.drop_timer = 0.0
        self.drop_interval = 0.55
        self.chain_flash_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 42

    @property
    def name(self) -> str:
        return "彩球连锁"

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
        return "6x12 双联彩球旋转下落 + 悬空半截重力分离 + 四连通洪泛消除与阶梯连锁"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _random_color(self) -> int:
        return 1 + (self._next_rand() % 4)

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    @staticmethod
    def get_sub_offset(rot: int) -> Tuple[int, int]:
        r = rot & 3
        if r == 0:
            return 0, -1
        if r == 1:
            return 1, 0
        if r == 2:
            return 0, 1
        return -1, 0

    def _is_cell_free(self, c: int, r: int) -> bool:
        if c < 0 or c >= self.COLS or r >= self.ROWS:
            return False
        if r < 0:
            return True
        return self.grid[r][c] == 0

    def can_place_pair(self, c: int, r: int, rot: int) -> bool:
        ox, oy = self.get_sub_offset(rot)
        return self._is_cell_free(c, r) and self._is_cell_free(c + ox, r + oy)

    def spawn_pair(self) -> None:
        if self.grid[0][2] != 0 or self.grid[1][2] != 0:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            if self._score > self._high_score:
                self._high_score = self._score
            return

        self.cur_col = 2
        self.cur_row = 1
        self.cur_rot = 0
        self.main_color = self.next_main
        self.sub_color = self.next_sub
        self.next_main = self._random_color()
        self.next_sub = self._random_color()
        self.drop_timer = 0.0

    def rotate_pair(self) -> None:
        nrot = (self.cur_rot + 1) & 3
        if self.can_place_pair(self.cur_col, self.cur_row, nrot):
            self.cur_rot = nrot
            return
        if self.can_place_pair(self.cur_col - 1, self.cur_row, nrot):
            self.cur_col -= 1
            self.cur_rot = nrot
            return
        if self.can_place_pair(self.cur_col + 1, self.cur_row, nrot):
            self.cur_col += 1
            self.cur_rot = nrot
            return
        if self.can_place_pair(self.cur_col, self.cur_row - 1, nrot):
            self.cur_row -= 1
            self.cur_rot = nrot
            return
        flip_rot = (self.cur_rot + 2) & 3
        if self.can_place_pair(self.cur_col, self.cur_row, flip_rot):
            self.cur_rot = flip_rot

    def apply_gravity(self) -> bool:
        moved = False
        for c in range(self.COLS):
            write_r = self.ROWS - 1
            for r in range(self.ROWS - 1, -1, -1):
                if self.grid[r][c] != 0:
                    if write_r != r:
                        self.grid[write_r][c] = self.grid[r][c]
                        self.grid[r][c] = 0
                        moved = True
                    write_r -= 1
        return moved

    def pop_connected_groups(self) -> int:
        visited = [[False for _ in range(self.COLS)] for _ in range(self.ROWS)]
        to_pop = [[False for _ in range(self.COLS)] for _ in range(self.ROWS)]
        total_popped = 0
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for r in range(self.ROWS):
            for c in range(self.COLS):
                col = self.grid[r][c]
                if col == 0 or visited[r][c]:
                    continue
                q = [(r, c)]
                visited[r][c] = True
                head = 0
                while head < len(q):
                    cr, cc = q[head]
                    head += 1
                    for dr, dc in dirs:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < self.ROWS and 0 <= nc < self.COLS:
                            if not visited[nr][nc] and self.grid[nr][nc] == col:
                                visited[nr][nc] = True
                                q.append((nr, nc))
                if len(q) >= 4:
                    total_popped += len(q)
                    for gr, gc in q:
                        to_pop[gr][gc] = True

        if total_popped > 0:
            for r in range(self.ROWS):
                for c in range(self.COLS):
                    if to_pop[r][c]:
                        self.grid[r][c] = 0
        return total_popped

    def lock_and_resolve(self) -> None:
        ox, oy = self.get_sub_offset(self.cur_rot)
        sc = self.cur_col + ox
        sr = self.cur_row + oy

        if 0 <= self.cur_row < self.ROWS and 0 <= self.cur_col < self.COLS:
            self.grid[self.cur_row][self.cur_col] = self.main_color
        if 0 <= sr < self.ROWS and 0 <= sc < self.COLS:
            self.grid[sr][sc] = self.sub_color

        self.apply_gravity()

        chain = 0
        while True:
            popped = self.pop_connected_groups()
            if popped <= 0:
                break
            chain += 1
            self._add_score(popped * 10 + chain * 40)
            self.apply_gravity()

        self.last_chain = chain
        if chain > self.max_chain:
            self.max_chain = chain
        if chain > 0:
            self.chain_flash_timer = 0.45

        self.drop_interval = max(0.20, 0.55 - (self._score // 400) * 0.04)
        self.spawn_pair()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.grid = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self._seed = 0x42199101
        self._score = 0
        self.last_chain = 0
        self.max_chain = 0
        self.drop_timer = 0.0
        self.drop_interval = 0.55
        self.chain_flash_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.next_main = self._random_color()
        self.next_sub = self._random_color()
        self.spawn_pair()
        self._state = STATE_TITLE

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self.grid = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
            self._score = 0
            self.last_chain = 0
            self.max_chain = 0
            self.drop_timer = 0.0
            self.drop_interval = 0.55
            self.chain_flash_timer = 0.0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.next_main = self._random_color()
            self.next_sub = self._random_color()
            self._state = STATE_PLAYING
            self.spawn_pair()

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt
        if self.chain_flash_timer > 0.0:
            self.chain_flash_timer = max(0.0, self.chain_flash_timer - dt)

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
                self.start()
            return

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            if keys_pressed & KEY_LEFT:
                if self.can_place_pair(self.cur_col - 1, self.cur_row, self.cur_rot):
                    self.cur_col -= 1
            elif keys_pressed & KEY_RIGHT:
                if self.can_place_pair(self.cur_col + 1, self.cur_row, self.cur_rot):
                    self.cur_col += 1

            if keys_pressed & (KEY_A | KEY_UP):
                self.rotate_pair()

            if keys_pressed & KEY_B:
                while self.can_place_pair(self.cur_col, self.cur_row + 1, self.cur_rot):
                    self.cur_row += 1
                self._add_score(2)
                self.lock_and_resolve()
                return

            if keys_pressed & KEY_DOWN:
                if self.can_place_pair(self.cur_col, self.cur_row + 1, self.cur_rot):
                    self.cur_row += 1
                    self.drop_timer = 0.0
                else:
                    self.lock_and_resolve()
                    return

            eff_interval = 0.07 if (keys_down & KEY_DOWN) else self.drop_interval
            self.drop_timer += dt
            if self.drop_timer >= eff_interval:
                self.drop_timer -= eff_interval
                if self.can_place_pair(self.cur_col, self.cur_row + 1, self.cur_rot):
                    self.cur_row += 1
                else:
                    self.lock_and_resolve()

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)

        def set_px(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        for y in range(16):
            for x in range(16):
                set_px(x, y, 12, 14, 24)

        for y in range(2, 16):
            set_px(1, y, 75, 85, 130)
            set_px(8, y, 75, 85, 130)
        for x in range(1, 9):
            set_px(x, 15, 75, 85, 130)
        set_px(4, 3, 55, 25, 35)

        for r in range(self.ROWS):
            for c in range(self.COLS):
                val = self.grid[r][c]
                if val in PUYO_RGB:
                    pr, pg, pb = PUYO_RGB[val]
                    set_px(2 + c, 3 + r, pr, pg, pb)

        if self._state in (STATE_PLAYING, STATE_TITLE, STATE_PAUSED):
            ox, oy = self.get_sub_offset(self.cur_rot)
            sc = self.cur_col + ox
            sr = self.cur_row + oy
            if 0 <= self.cur_row < self.ROWS and self.main_color in PUYO_RGB:
                mr, mg, mb = PUYO_RGB[self.main_color]
                set_px(2 + self.cur_col, 3 + self.cur_row, mr, mg, mb)
            if 0 <= sr < self.ROWS and 0 <= sc < self.COLS and self.sub_color in PUYO_RGB:
                sr_c, sg_c, sb_c = PUYO_RGB[self.sub_color]
                set_px(2 + sc, 3 + sr, sr_c, sg_c, sb_c)

        for x in range(10, 15):
            set_px(x, 3, 45, 55, 85)
            set_px(x, 8, 45, 55, 85)
        for y in range(3, 9):
            set_px(10, y, 45, 55, 85)
            set_px(14, y, 45, 55, 85)

        if self.next_sub in PUYO_RGB:
            nsr, nsg, nsb = PUYO_RGB[self.next_sub]
            set_px(12, 5, nsr, nsg, nsb)
        if self.next_main in PUYO_RGB:
            nmr, nmg, nmb = PUYO_RGB[self.next_main]
            set_px(12, 6, nmr, nmg, nmb)

        display_chain = min(5, self.last_chain if self.chain_flash_timer > 0.0 else self.max_chain)
        for i in range(display_chain):
            cr = 255 if self.chain_flash_timer > 0.0 else 180
            cg = 215 if self.chain_flash_timer > 0.0 else 140
            set_px(11, 14 - i, cr, cg, 25)
            set_px(12, 14 - i, cr, cg, 25)

        dots = min(16, self._score // 80)
        for x in range(dots):
            set_px(x, 0, 40, 210, 255)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                set_px(x, 0, 235, 50, 50)
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_px(6, y, 250, 250, 250)
                set_px(9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "last_chain": self.last_chain,
            "max_chain": self.max_chain,
            "progress": min(100, self._score // 10),
        }
