# -*- coding: utf-8 -*-
"""
game_033_snake.py —— 街机游戏 #033: 经典贪吃蛇 (Classic Snake)
力学动词: 网格转向、进食生长与自噬检测
与 ESP32-S3 C++ arcade::Game033Snake 规范 1:1 对齐
"""

import random
from typing import Dict, Any
from arcade.base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
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
    KEY_START,
)


class Game033Snake(BaseCartridge):
    """经典贪吃蛇 16x16 标准卡带封装"""

    def __init__(self):
        self._snake = []
        self._dir = (1, 0)
        self._next_dir = (1, 0)
        self._food = (0, 0)
        self._score = 0
        self._state = STATE_PLAYING
        self._tick_timer = 0.0
        self._tick_interval = 0.35
        self.reset()

    @property
    def game_id(self) -> int:
        return 33

    @property
    def name(self) -> str:
        return "经典贪吃蛇"

    @property
    def english_name(self) -> str:
        return "Classic Snake"

    @property
    def release_year(self) -> int:
        return 1976

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "网格转向、进食生长与自噬检测"

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._snake = [(5, 7), (4, 7), (3, 7)]
        self._dir = (1, 0)
        self._next_dir = (1, 0)
        self._score = 0
        self._state = STATE_PLAYING
        self._tick_timer = 0.0
        self._tick_interval = 0.35
        self._place_food()

    def _place_food(self) -> None:
        free_cells = [
            (x, y)
            for y in range(16)
            for x in range(16)
            if (x, y) not in self._snake
        ]
        if free_cells:
            self._food = random.choice(free_cells)

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if self._state == STATE_GAMEOVER:
            if keys_pressed & (KEY_A | KEY_START):
                self.reset()
            return

        if keys_pressed & KEY_START:
            self._state = STATE_PAUSED if self._state == STATE_PLAYING else STATE_PLAYING
            return

        if self._state == STATE_PAUSED:
            return

        # 4向输入，严格防 180 度直接掉头自咬
        dx, dy = self._dir
        if (keys_pressed & KEY_UP) and dy != 1:
            self._next_dir = (0, -1)
        elif (keys_pressed & KEY_DOWN) and dy != -1:
            self._next_dir = (0, 1)
        elif (keys_pressed & KEY_LEFT) and dx != 1:
            self._next_dir = (-1, 0)
        elif (keys_pressed & KEY_RIGHT) and dx != -1:
            self._next_dir = (1, 0)

        self._tick_timer += dt
        if self._tick_timer >= self._tick_interval:
            self._tick_timer -= self._tick_interval
            self._step()

    def _step(self) -> None:
        self._dir = self._next_dir
        hx, hy = self._snake[0]
        dx, dy = self._dir
        new_hx = (hx + dx) % 16
        new_hy = (hy + dy) % 16

        # 自噬碰撞检测
        if (new_hx, new_hy) in self._snake[1:]:
            self._state = STATE_GAMEOVER
            return

        # 移动蛇身
        self._snake.insert(0, (new_hx, new_hy))

        # 进食检测
        if (new_hx, new_hy) == self._food:
            self._score += 10
            # 动态难度提速
            self._tick_interval = max(0.08, 0.35 - (len(self._snake) - 3) * 0.012)
            self._place_food()
        else:
            self._snake.pop()

    def render(self) -> bytearray:
        buf = bytearray(16 * 16 * 3)

        # 绘制食物 (红色)
        fx, fy = self._food
        f_idx = (fy * 16 + fx) * 3
        buf[f_idx + 0] = 255
        buf[f_idx + 1] = 20
        buf[f_idx + 2] = 20

        # 绘制蛇身
        for i, (sx, sy) in enumerate(self._snake):
            idx = (sy * 16 + sx) * 3
            if i == 0:
                # 蛇头高亮
                buf[idx + 0] = 30
                buf[idx + 1] = 255
                buf[idx + 2] = 80
            else:
                buf[idx + 0] = 0
                buf[idx + 1] = 180
                buf[idx + 2] = 20

        return buf

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self._score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (len(self._snake) * 100) // 64),
        }
