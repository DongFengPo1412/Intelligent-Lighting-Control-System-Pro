# -*- coding: utf-8 -*-
"""
game_033_snake.py —— 街机游戏 #033: 经典贪吃蛇 (Classic Snake)
力学动词: 网格转向、进食生长与自噬/死墙检测 (默认原汁原味街机硬死墙，可选循环穿墙)
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
from arcade.arcade_result_screen import render_result_screen


class Game033Snake(BaseCartridge):
    """经典贪吃蛇 16x16 标准卡带封装"""

    def __init__(self, wrap_walls: bool = False):
        self._snake = []
        self._dir = (1, 0)
        self._next_dir = (1, 0)
        self._food = (0, 0)
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self._tick_timer = 0.0
        self._tick_interval = 0.35
        self._anim_timer = 0.0
        self._wrap_walls = wrap_walls  # 默认死墙，符合原版街机挑战
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

    @property
    def wrap_walls(self) -> bool:
        return self._wrap_walls

    @wrap_walls.setter
    def wrap_walls(self, val: bool) -> None:
        self._wrap_walls = bool(val)

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._snake = [(5, 7), (4, 7), (3, 7)]
        self._dir = (1, 0)
        self._next_dir = (1, 0)
        self._score = 0
        self._state = STATE_TITLE
        self._tick_timer = 0.0
        self._anim_timer = 0.0
        self._tick_interval = 0.35
        self._place_food()

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
        new_hx = hx + dx
        new_hy = hy + dy

        # 防快速连击导致的 180 度掉头撞颈
        if len(self._snake) > 1 and (new_hx, new_hy) == self._snake[1]:
            self._next_dir = (self._snake[0][0] - self._snake[1][0], self._snake[0][1] - self._snake[1][1])
            self._dir = self._next_dir
            dx, dy = self._dir
            new_hx = hx + dx
            new_hy = hy + dy

        # 边界碰撞检测
        if self._wrap_walls:
            new_hx = (new_hx + 16) % 16
            new_hy = (new_hy + 16) % 16
        else:
            if new_hx < 0 or new_hx >= 16 or new_hy < 0 or new_hy >= 16:
                self._state = STATE_GAMEOVER
                if self._score > self._high_score:
                    self._high_score = self._score
                return

        # 自噬碰撞检测
        if (new_hx, new_hy) in self._snake[1:]:
            self._state = STATE_GAMEOVER
            if self._score > self._high_score:
                self._high_score = self._score
            return

        # 移动蛇身
        self._snake.insert(0, (new_hx, new_hy))

        # 进食检测
        if (new_hx, new_hy) == self._food:
            self._score += 10
            if self._score > self._high_score:
                self._high_score = self._score
            self._tick_interval = max(0.08, 0.35 - (len(self._snake) - 3) * 0.012)
            self._place_food()
        else:
            self._snake.pop()

    def render(self) -> bytearray:
        buf = bytearray(16 * 16 * 3)

        if self._state == STATE_GAMEOVER:
            render_result_screen(buf, False, self._score, self._high_score, self._anim_timer)
            return buf

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
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (len(self._snake) * 100) // 64),
        }
