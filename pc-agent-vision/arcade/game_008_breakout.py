# -*- coding: utf-8 -*-
"""
game_008_breakout.py —— 经典打砖块 1976 (Breakout 1976)
编号: #008
年代: 1976 (雅达利 Atari / 诺兰·布什内尔 & 史蒂夫·沃兹尼亚克)
核心独占机制: 移动挡板反弹折射 + 上方阵列砖块敲击碎裂 + 生命损耗 + 清屏通关
手柄类型: CTRL_TWO_BUTTON (左右移动挡板 + 开球/动作)
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_TWO_BUTTON,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

class Brick:
    def __init__(self, hp: int, r: int, g: int, b: int):
        self.hp = hp
        self.r = r
        self.g = g
        self.b = b

class Game008Breakout(BaseCartridge):
    def __init__(self):
        self._id = 8
        self._name = "经典打砖块"
        self._english_name = "Breakout 1976"
        self._year = 1976
        self._control_type = CTRL_TWO_BUTTON
        self._core_mechanic = "移动挡板反弹折射 + 上方阵列砖块敲击碎裂 + 生命损耗 + 清屏通关"

        self.k_rows = 4
        self.k_cols = 8

        self.state = STATE_TITLE
        self.paddle_x = 6.0
        self.paddle_w = 4.0

        self.ball_x = 8.0
        self.ball_y = 13.0
        self.ball_vx = 6.0
        self.ball_vy = -8.0
        self.ball_stuck = True

        self.bricks: List[List[Brick]] = []
        self.remaining_bricks = 0

        self.lives = 3
        self.score = 0
        self.high_score = 0
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

    def reset_ball_and_paddle(self):
        self.paddle_x = 6.0
        self.paddle_w = 4.0
        self.ball_stuck = True
        self.ball_x = self.paddle_x + self.paddle_w * 0.5
        self.ball_y = 13.0
        self.ball_vx = 6.5
        self.ball_vy = -8.5

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.remaining_bricks = self.k_rows * self.k_cols

        self.bricks = []
        for r in range(self.k_rows):
            row: List[Brick] = []
            if r == 0:
                cr, cg, cb, hp = 231, 76, 60, 2    # 红色耐久 2
            elif r == 1:
                cr, cg, cb, hp = 230, 126, 34, 1  # 橙色耐久 1
            elif r == 2:
                cr, cg, cb, hp = 46, 204, 113, 1  # 绿色耐久 1
            else:
                cr, cg, cb, hp = 241, 196, 15, 1  # 黄色耐久 1

            for c in range(self.k_cols):
                row.append(Brick(hp, cr, cg, cb))
            self.bricks.append(row)

        self.reset_ball_and_paddle()

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            self.paddle_x = self.ball_x - self.paddle_w * 0.5
            self.paddle_x = max(0.0, min(16.0 - self.paddle_w, self.paddle_x))

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt
            if self.ball_x <= 0.0 or self.ball_x >= 15.0:
                self.ball_vx = -self.ball_vx
            if self.ball_y <= 0.0 or self.ball_y >= 13.0:
                self.ball_vy = -self.ball_vy

            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
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

            paddle_speed = 12.0
            if keys_down & KEY_LEFT:
                self.paddle_x -= paddle_speed * dt
            elif keys_down & KEY_RIGHT:
                self.paddle_x += paddle_speed * dt
            self.paddle_x = max(0.0, min(16.0 - self.paddle_w, self.paddle_x))

            if self.ball_stuck:
                self.ball_x = self.paddle_x + self.paddle_w * 0.5
                self.ball_y = 13.0
                if keys_pressed & (KEY_A | KEY_B | KEY_UP | KEY_START):
                    self.ball_stuck = False
                    if keys_down & KEY_LEFT:
                        self.ball_vx = -6.0
                    elif keys_down & KEY_RIGHT:
                        self.ball_vx = 6.0
                    else:
                        self.ball_vx = 5.0
                    self.ball_vy = -8.5
                return

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt

            # 墙壁碰撞
            if self.ball_x <= 0.0:
                self.ball_x = 0.0
                self.ball_vx = abs(self.ball_vx)
            elif self.ball_x >= 15.0:
                self.ball_x = 15.0
                self.ball_vx = -abs(self.ball_vx)

            if self.ball_y <= 0.0:
                self.ball_y = 0.0
                self.ball_vy = abs(self.ball_vy)

            # 挡板反弹
            if self.ball_vy > 0.0 and 13.3 <= self.ball_y <= 14.5:
                if (self.paddle_x - 0.5) <= self.ball_x <= (self.paddle_x + self.paddle_w + 0.5):
                    self.ball_y = 13.2
                    speed = math.sqrt(self.ball_vx * self.ball_vx + self.ball_vy * self.ball_vy)
                    if speed < 15.0:
                        speed += 0.2
                    hit_offset = (self.ball_x - (self.paddle_x + self.paddle_w * 0.5)) / (self.paddle_w * 0.5)
                    self.ball_vx = hit_offset * 7.5
                    vy_sq = max(16.0, speed * speed - self.ball_vx * self.ball_vx)
                    self.ball_vy = -math.sqrt(vy_sq)

            # 砖块碰撞
            ball_row = int(round(self.ball_y)) - 2
            ball_col = int(round(self.ball_x)) // 2

            if 0 <= ball_row < self.k_rows and 0 <= ball_col < self.k_cols:
                target_brick = self.bricks[ball_row][ball_col]
                if target_brick.hp > 0:
                    target_brick.hp -= 1
                    if target_brick.hp == 0:
                        self.remaining_bricks -= 1
                        pts = (self.k_rows - ball_row) * 15
                        self.score += pts
                        if self.score > self.high_score:
                            self.high_score = self.score

                    self.ball_vy = -self.ball_vy

                    if self.remaining_bricks <= 0:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        return

            # 出底线
            if self.ball_y > 15.5:
                if self.lives > 0:
                    self.lives -= 1
                if self.lives == 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                else:
                    self.reset_ball_and_paddle()

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        # 绘制砖块
        for r in range(self.k_rows):
            y = r + 2
            for c in range(self.k_cols):
                brick = self.bricks[r][c]
                if brick.hp > 0:
                    x0 = c * 2
                    x1 = c * 2 + 1
                    cr, cg, cb = brick.r, brick.g, brick.b
                    if brick.hp == 1 and r == 0:
                        cr, cg, cb = 192, 57, 43

                    idx0 = (y * 16 + x0) * 3
                    idx1 = (y * 16 + x1) * 3
                    self.frame_buffer[idx0:idx0+3] = bytes([cr, cg, cb])
                    self.frame_buffer[idx1:idx1+3] = bytes([cr, cg, cb])

        # 绘制挡板
        px_start = int(round(self.paddle_x))
        px_end = int(round(self.paddle_x + self.paddle_w))
        for x in range(px_start, px_end):
            if 0 <= x < 16:
                idx = (14 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([52, 152, 219])

        # 绘制小球
        bx = int(round(self.ball_x))
        by = int(round(self.ball_y))
        if 0 <= bx < 16 and 0 <= by < 16:
            idx = (by * 16 + bx) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 255, 255])

        # 顶部生命
        for i in range(self.lives):
            idx = (0 * 16 + (i * 2)) * 3
            self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        # 特效
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
        progress = int(((self.k_rows * self.k_cols - self.remaining_bricks) * 100) / (self.k_rows * self.k_cols))
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": progress,
            "remaining_bricks": self.remaining_bricks,
        }
