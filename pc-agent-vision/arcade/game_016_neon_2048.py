# -*- coding: utf-8 -*-
"""
game_016_neon_2048.py —— 霓虹 2048 (Neon 2048 2014)
编号: #016
年代: 2014 (Gabriele Cirulli)
核心独占机制: 4x4 网格滑移对撞合并 + 霓虹色阶升维 + 随机落子与死锁判定
手柄类型: CTRL_DPAD_4WAY (上下左右滑动推压)
"""

import random
from typing import Dict, Any, List, Tuple
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    CTRL_DPAD_4WAY,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

COLOR_MAP = {
    0: (25, 25, 30),      # 空槽微弱黑蓝
    1: (41, 128, 185),    # 2: 冰蓝
    2: (26, 188, 156),    # 4: 碧绿
    3: (46, 204, 113),    # 8: 鲜翠
    4: (241, 196, 15),    # 16: 明黄
    5: (230, 126, 34),    # 32: 烈橙
    6: (231, 76, 60),     # 64: 猩红
    7: (155, 89, 182),    # 128: 紫罗兰
    8: (255, 0, 128),     # 256: 霓虹粉
    9: (255, 215, 0),     # 512: 纯金辉光
    10: (127, 255, 212),  # 1024: 碧晶白
    11: (255, 255, 255),  # 2048: 终极炫白
}

class Game016Neon2048(BaseCartridge):
    def __init__(self):
        self._id = 16
        self._name = "霓虹 2048"
        self._english_name = "Neon 2048 2014"
        self._year = 2014
        self._control_type = CTRL_DPAD_4WAY
        self._core_mechanic = "4x4 网格滑移对撞合并 + 霓虹色阶升维 + 随机落子与死锁判定"

        self.state = STATE_TITLE
        self.board: List[List[int]] = [[0 for _ in range(4)] for _ in range(4)]
        self.score = 0
        self.high_score = 0
        self.max_tile_level = 1
        self.state_timer = 0.0

        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def english_name(self) -> str:
        return self._english_name

    @property
    def release_year(self) -> int:
        return self._year

    @property
    def control_type(self) -> int:
        return self._control_type

    @property
    def core_mechanic(self) -> str:
        return self._core_mechanic

    def spawn_random_tile(self):
        empties = []
        for r in range(4):
            for c in range(4):
                if self.board[r][c] == 0:
                    empties.append((r, c))

        if not empties:
            return

        r, c = random.choice(empties)
        new_val = 2 if random.random() < 0.1 else 1
        self.board[r][c] = new_val
        if new_val > self.max_tile_level:
            self.max_tile_level = new_val

    def can_move(self) -> bool:
        for r in range(4):
            for c in range(4):
                if self.board[r][c] == 0:
                    return True
                if c < 3 and self.board[r][c] == self.board[r][c + 1]:
                    return True
                if r < 3 and self.board[r][c] == self.board[r + 1][c]:
                    return True
        return False

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.max_tile_level = 1
        self.board = [[0 for _ in range(4)] for _ in range(4)]

        self.spawn_random_tile()
        self.spawn_random_tile()

    def _merge_line_left(self, line: List[int]) -> Tuple[List[int], int, int]:
        non_zeros = [x for x in line if x != 0]
        res = []
        score_gain = 0
        max_lvl = 0
        skip = False

        for i in range(len(non_zeros)):
            if skip:
                skip = False
                continue
            if i + 1 < len(non_zeros) and non_zeros[i] == non_zeros[i + 1]:
                merged_lvl = non_zeros[i] + 1
                res.append(merged_lvl)
                score_gain += (1 << merged_lvl)
                if merged_lvl > max_lvl:
                    max_lvl = merged_lvl
                skip = True
            else:
                res.append(non_zeros[i])
                if non_zeros[i] > max_lvl:
                    max_lvl = non_zeros[i]

        while len(res) < 4:
            res.append(0)

        return res, score_gain, max_lvl

    def slide(self, dx: int, dy: int) -> bool:
        moved = False
        total_score = 0
        max_seen = self.max_tile_level

        if dx != 0:
            for r in range(4):
                orig_line = list(self.board[r])
                line = orig_line if dx < 0 else list(reversed(orig_line))
                new_line, gain, lvl = self._merge_line_left(line)
                if dx > 0:
                    new_line = list(reversed(new_line))

                if new_line != orig_line:
                    moved = True
                    self.board[r] = new_line
                    total_score += gain
                    if lvl > max_seen:
                        max_seen = lvl

        elif dy != 0:
            for c in range(4):
                orig_line = [self.board[r][c] for r in range(4)]
                line = orig_line if dy < 0 else list(reversed(orig_line))
                new_line, gain, lvl = self._merge_line_left(line)
                if dy > 0:
                    new_line = list(reversed(new_line))

                if new_line != orig_line:
                    moved = True
                    for r in range(4):
                        self.board[r][c] = new_line[r]
                    total_score += gain
                    if lvl > max_seen:
                        max_seen = lvl

        self.score += total_score
        self.max_tile_level = max(self.max_tile_level, max_seen)
        if self.score > self.high_score:
            self.high_score = self.score

        if moved:
            self.spawn_random_tile()
            if self.max_tile_level >= 11:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
            elif not self.can_move():
                self.state = STATE_GAMEOVER
                self.state_timer = 0.0

        return moved

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)):
                self.reset()
            return

        if self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            if keys_pressed & KEY_UP:
                self.slide(0, -1)
            elif keys_pressed & KEY_DOWN:
                self.slide(0, 1)
            elif keys_pressed & KEY_LEFT:
                self.slide(-1, 0)
            elif keys_pressed & KEY_RIGHT:
                self.slide(1, 0)

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for r in range(4):
            y0 = r * 4
            for c in range(4):
                x0 = c * 4
                val = self.board[r][c]
                color = COLOR_MAP.get(val, (255, 255, 255))
                for dy in range(3):
                    y = y0 + dy
                    if y < 16:
                        for dx in range(3):
                            x = x0 + dx
                            if x < 16:
                                idx = (y * 16 + x) * 3
                                self.frame_buffer[idx:idx+3] = bytes(color)

        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "state": self.state,
            "max_tile_level": self.max_tile_level,
            "progress": int((self.max_tile_level * 100) / 11),
        }
