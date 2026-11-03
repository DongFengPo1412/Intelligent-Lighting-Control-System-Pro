# -*- coding: utf-8 -*-
"""
game_041_tetris.py —— 街机游戏 #041: 俄罗斯方块 (Tetris)
力学动词: 四联方块旋转、平移堆叠与满行消除
与 ESP32-S3 C++ arcade::Game041Tetris 规范 1:1 对齐
"""

import random
from typing import Dict, Any
from arcade.base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
)
from arcade.arcade_result_screen import render_result_screen

# 7 种俄罗斯方块的 4 种旋转姿态定义 (7, 4, 4, 2)
TETRIS_SHAPES = (
    # 0: O 型 (方块)
    (((0,0),(1,0),(0,1),(1,1)), ((0,0),(1,0),(0,1),(1,1)), ((0,0),(1,0),(0,1),(1,1)), ((0,0),(1,0),(0,1),(1,1))),
    # 1: I 型 (长条)
    (((0,1),(1,1),(2,1),(3,1)), ((2,0),(2,1),(2,2),(2,3)), ((0,2),(1,2),(2,2),(3,2)), ((1,0),(1,1),(1,2),(1,3))),
    # 2: T 型
    (((1,0),(0,1),(1,1),(2,1)), ((1,0),(1,1),(2,1),(1,2)), ((0,1),(1,1),(2,1),(1,2)), ((1,0),(0,1),(1,1),(1,2))),
    # 3: L 型
    (((0,1),(1,1),(2,1),(2,0)), ((1,0),(1,1),(1,2),(2,2)), ((0,2),(0,1),(1,1),(2,1)), ((0,0),(1,0),(1,1),(1,2))),
    # 4: J 型
    (((0,0),(0,1),(1,1),(2,1)), ((1,2),(1,1),(1,0),(2,0)), ((0,1),(1,1),(2,1),(2,2)), ((0,2),(1,2),(1,1),(1,0))),
    # 5: S 型
    (((1,0),(2,0),(0,1),(1,1)), ((1,0),(1,1),(2,1),(2,2)), ((1,1),(2,1),(0,2),(1,2)), ((0,0),(0,1),(1,1),(1,2))),
    # 6: Z 型
    (((0,0),(1,0),(1,1),(2,1)), ((2,0),(2,1),(1,1),(1,2)), ((0,1),(1,1),(1,2),(2,2)), ((1,0),(1,1),(0,1),(0,2)))
)

PIECE_COLORS = (
    (240, 220, 0),   # 0: O 黄色
    (0, 240, 240),   # 1: I 青色
    (170, 0, 240),   # 2: T 紫色
    (240, 140, 0),   # 3: L 橙色
    (0, 70, 240),    # 4: J 蓝色
    (0, 240, 0),     # 5: S 绿色
    (240, 0, 0)      # 6: Z 红色
)

BOARD_LEFT = 3
BOARD_RIGHT = 12


class Game041Tetris(BaseCartridge):
    """俄罗斯方块 16x16 标准卡带封装"""

    def __init__(self):
        self._field = [[0] * 16 for _ in range(16)]
        self._piece_type = 0
        self._piece_rot = 0
        self._piece_x = 0
        self._piece_y = 0
        self._drop_timer = 0.0
        self._drop_interval = 0.60
        self._anim_timer = 0.0
        self._score = 0
        self._high_score = 0
        self._lines_cleared = 0
        self._state = STATE_TITLE
        self.reset()

    @property
    def game_id(self) -> int:
        return 41

    @property
    def name(self) -> str:
        return "俄罗斯方块"

    @property
    def english_name(self) -> str:
        return "Tetris"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "四联方块旋转、平移堆叠与满行消除"

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._field = [[0] * 16 for _ in range(16)]
        self._score = 0
        self._lines_cleared = 0
        self._drop_interval = 0.60
        self._drop_timer = 0.0
        self._anim_timer = 0.0
        self._state = STATE_TITLE
        self._spawn_piece()

    def start(self) -> None:
        """从待命或结算状态启动游戏 (幂等)"""
        if self._state in (STATE_TITLE, STATE_GAMEOVER):
            if self._state == STATE_GAMEOVER:
                self.reset()
            self._state = STATE_PLAYING
        elif self._state == STATE_PAUSED:
            self.resume()

    def pause(self) -> None:
        """安全暂停 (幂等)"""
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        """从暂停恢复游玩 (幂等)"""
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _check_collision(self, piece_type: int, rot: int, x: int, y: int) -> bool:
        for ox, oy in TETRIS_SHAPES[piece_type][rot]:
            px = x + ox
            py = y + oy
            if px < BOARD_LEFT or px > BOARD_RIGHT or py >= 16:
                return True
            if py >= 0 and self._field[py][px] != 0:
                return True
        return False

    def _spawn_piece(self) -> None:
        self._piece_type = random.randint(0, 6)
        self._piece_rot = 0
        self._piece_x = BOARD_LEFT + 3
        self._piece_y = 0

        if self._check_collision(self._piece_type, self._piece_rot, self._piece_x, self._piece_y):
            self._state = STATE_GAMEOVER
            if self._score > self._high_score:
                self._high_score = self._score

    def _lock_piece(self) -> None:
        for ox, oy in TETRIS_SHAPES[self._piece_type][self._piece_rot]:
            px = self._piece_x + ox
            py = self._piece_y + oy
            if 0 <= py < 16 and 0 <= px < 16:
                self._field[py][px] = self._piece_type + 1
        self._clear_lines()
        self._spawn_piece()

    def _clear_lines(self) -> None:
        cleared = 0
        y = 15
        while y >= 0:
            full = all(self._field[y][x] != 0 for x in range(BOARD_LEFT, BOARD_RIGHT + 1))
            if full:
                cleared += 1
                for ty in range(y, 0, -1):
                    for tx in range(BOARD_LEFT, BOARD_RIGHT + 1):
                        self._field[ty][tx] = self._field[ty - 1][tx]
                for tx in range(BOARD_LEFT, BOARD_RIGHT + 1):
                    self._field[0][tx] = 0
            else:
                y -= 1

        if cleared > 0:
            self._lines_cleared += cleared
            self._score += cleared * cleared * 100
            if self._score > self._high_score:
                self._high_score = self._score
            self._drop_interval = max(0.10, 0.60 - self._lines_cleared * 0.03)

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        self._anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_A | KEY_START):
                self.start()
            return

        if self._state == STATE_GAMEOVER:
            if keys_pressed & (KEY_A | KEY_START):
                self.start()
            return

        if keys_pressed & KEY_START:
            if self._state == STATE_PLAYING:
                self.pause()
            elif self._state == STATE_PAUSED:
                self.resume()
            return

        if self._state == STATE_PAUSED:
            return

        # 左右移动
        if (keys_pressed & KEY_LEFT) and not self._check_collision(
            self._piece_type, self._piece_rot, self._piece_x - 1, self._piece_y
        ):
            self._piece_x -= 1
        if (keys_pressed & KEY_RIGHT) and not self._check_collision(
            self._piece_type, self._piece_rot, self._piece_x + 1, self._piece_y
        ):
            self._piece_x += 1

        # 旋转 (带踢墙容错)
        if keys_pressed & (KEY_A | KEY_UP):
            next_rot = (self._piece_rot + 1) % 4
            if not self._check_collision(self._piece_type, next_rot, self._piece_x, self._piece_y):
                self._piece_rot = next_rot
            elif not self._check_collision(self._piece_type, next_rot, self._piece_x - 1, self._piece_y):
                self._piece_x -= 1
                self._piece_rot = next_rot
            elif not self._check_collision(self._piece_type, next_rot, self._piece_x + 1, self._piece_y):
                self._piece_x += 1
                self._piece_rot = next_rot

        # 软降 / 快降
        interval = 0.05 if (keys_down & (KEY_DOWN | KEY_B)) else self._drop_interval

        self._drop_timer += dt
        if self._drop_timer >= interval:
            self._drop_timer = 0.0
            if not self._check_collision(self._piece_type, self._piece_rot, self._piece_x, self._piece_y + 1):
                self._piece_y += 1
                if keys_down & (KEY_DOWN | KEY_B):
                    self._score += 1
                    if self._score > self._high_score:
                        self._high_score = self._score
            else:
                self._lock_piece()

    def render(self) -> bytearray:
        buf = bytearray(16 * 16 * 3)

        if self._state == STATE_GAMEOVER:
            render_result_screen(buf, False, self._score, self._high_score, self._anim_timer)
            return buf

        # 左右边界线 (灰冷色)
        for y in range(16):
            idx_l = (y * 16 + (BOARD_LEFT - 1)) * 3
            idx_r = (y * 16 + (BOARD_RIGHT + 1)) * 3
            buf[idx_l : idx_l + 3] = bytearray([40, 40, 50])
            buf[idx_r : idx_r + 3] = bytearray([40, 40, 50])

        # 锁定方块
        for y in range(16):
            for x in range(BOARD_LEFT, BOARD_RIGHT + 1):
                cid = self._field[y][x]
                if cid > 0:
                    r, g, b = PIECE_COLORS[cid - 1]
                    idx = (y * 16 + x) * 3
                    buf[idx : idx + 3] = bytearray([r, g, b])

        # 下落方块
        r, g, b = PIECE_COLORS[self._piece_type]
        for ox, oy in TETRIS_SHAPES[self._piece_type][self._piece_rot]:
            px = self._piece_x + ox
            py = self._piece_y + oy
            if 0 <= py < 16 and 0 <= px < 16:
                idx = (py * 16 + px) * 3
                buf[idx : idx + 3] = bytearray([r, g, b])

        return buf

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self._score,
            "high_score": self._high_score,
            "lines": self._lines_cleared,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, self._lines_cleared * 10),
        }
