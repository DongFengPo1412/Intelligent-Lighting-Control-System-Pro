# -*- coding: utf-8 -*-
"""
game_007_pong.py —— 双人乒乓 1972 (Pong 1972)
编号: #007
年代: 1972 (雅达利 Atari / 诺兰·布什内尔 & 阿兰·奥尔康)
核心独占机制: 刚体小球双向反弹 + 挡板切角改变斜率 + 漏接失分 + 回合速度递增
手柄类型: CTRL_VERSUS_DUAL (双人对战 / 单人对机)
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_VERSUS_DUAL,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

class Game007Pong(BaseCartridge):
    def __init__(self):
        self._id = 7
        self._name = "双人乒乓"
        self._english_name = "Pong 1972"
        self._year = 1972
        self._control_type = CTRL_VERSUS_DUAL
        self._core_mechanic = "刚体小球双向反弹 + 挡板切角改变斜率 + 漏接失分 + 回合速度递增"

        self.state = STATE_TITLE
        self.p1_y = 6.0
        self.p2_y = 6.0
        self.paddle_h = 4.0
        self.ball_x = 7.5
        self.ball_y = 7.5
        self.ball_vx = 7.5
        self.ball_vy = 2.5

        self.p1_score = 0
        self.p2_score = 0
        self.winning_score = 5
        self.p2_is_ai = True
        self.serve_delay = 0.0
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

    def init(self) -> None:
        self.reset()

    def _reset_ball(self, serve_to_right: bool) -> None:
        self.ball_x = 7.5
        self.ball_y = 7.5
        base_speed = 7.5
        self.ball_vx = base_speed if serve_to_right else -base_speed
        self.ball_vy = 2.5 if self.ball_y <= 7.5 else -2.5
        self.serve_delay = 0.6

    def reset(self) -> None:
        self.state = STATE_PLAYING
        self.p1_y = 6.0
        self.p2_y = 6.0
        self.paddle_h = 4.0
        self.p1_score = 0
        self.p2_score = 0
        self.p2_is_ai = True
        self.state_timer = 0.0
        self._reset_ball(True)

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            speed = 6.0 * dt
            if self.ball_y < self.p1_y + 1.5 and self.p1_y > 0.0:
                self.p1_y -= speed
            elif self.ball_y > self.p1_y + 2.5 and self.p1_y < 16.0 - self.paddle_h:
                self.p1_y += speed

            if self.ball_y < self.p2_y + 1.5 and self.p2_y > 0.0:
                self.p2_y -= speed
            elif self.ball_y > self.p2_y + 2.5 and self.p2_y < 16.0 - self.paddle_h:
                self.p2_y += speed

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt
            if self.ball_y <= 0.0 or self.ball_y >= 15.0:
                self.ball_vy = -self.ball_vy
            if self.ball_x <= 2.0 or self.ball_x >= 13.0:
                self.ball_vx = -self.ball_vx

            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN)):
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

            paddle_speed = 9.5

            # P1 控制 (左侧)
            if keys_down & KEY_UP:
                self.p1_y -= paddle_speed * dt
            elif keys_down & KEY_DOWN:
                self.p1_y += paddle_speed * dt
            self.p1_y = max(0.0, min(16.0 - self.paddle_h, self.p1_y))

            # P2 控制 (右侧，按 A/B 接管为双人对战，否则智能 AI)
            if keys_down & KEY_A:
                self.p2_is_ai = False
                self.p2_y -= paddle_speed * dt
            elif keys_down & KEY_B:
                self.p2_is_ai = False
                self.p2_y += paddle_speed * dt
            elif self.p2_is_ai:
                target_y = self.ball_y - self.paddle_h * 0.5
                ai_speed = 7.0 * dt
                if self.p2_y < target_y - 0.5:
                    self.p2_y += ai_speed
                elif self.p2_y > target_y + 0.5:
                    self.p2_y -= ai_speed
            self.p2_y = max(0.0, min(16.0 - self.paddle_h, self.p2_y))

            if self.serve_delay > 0.0:
                self.serve_delay -= dt
                return

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt

            # 上下墙壁反弹
            if self.ball_y <= 0.0:
                self.ball_y = 0.0
                self.ball_vy = abs(self.ball_vy)
            elif self.ball_y >= 15.0:
                self.ball_y = 15.0
                self.ball_vy = -abs(self.ball_vy)

            # 左侧 P1 挡板碰撞 (x=1)
            if self.ball_vx < 0.0 and (0.5 <= self.ball_x <= 1.8):
                if self.p1_y - 0.5 <= self.ball_y <= self.p1_y + self.paddle_h + 0.5:
                    self.ball_x = 1.9
                    speed = min(16.0, abs(self.ball_vx) * 1.05)
                    self.ball_vx = speed
                    hit_offset = (self.ball_y - (self.p1_y + self.paddle_h * 0.5)) / (self.paddle_h * 0.5)
                    self.ball_vy = hit_offset * 7.5

            # 右侧 P2 挡板碰撞 (x=14)
            if self.ball_vx > 0.0 and (13.2 <= self.ball_x <= 14.8):
                if self.p2_y - 0.5 <= self.ball_y <= self.p2_y + self.paddle_h + 0.5:
                    self.ball_x = 13.1
                    speed = min(16.0, abs(self.ball_vx) * 1.05)
                    self.ball_vx = -speed
                    hit_offset = (self.ball_y - (self.p2_y + self.paddle_h * 0.5)) / (self.paddle_h * 0.5)
                    self.ball_vy = hit_offset * 7.5

            # 出界与计分
            if self.ball_x < 0.0:
                self.p2_score += 1
                if self.p2_score >= self.winning_score:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                else:
                    self._reset_ball(False)
            elif self.ball_x > 15.0:
                self.p1_score += 1
                if self.p1_score >= self.winning_score:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                else:
                    self._reset_ball(True)

    def render(self) -> bytearray:
        fb = self.frame_buffer
        for i in range(len(fb)):
            fb[i] = 0

        # 球网虚线 (x=7)
        for y in range(0, 16, 2):
            idx = (y * 16 + 7) * 3
            fb[idx] = fb[idx + 1] = fb[idx + 2] = 40

        # P1 挡板 (x=1, 青蓝)
        p1_top = int(round(self.p1_y))
        p1_bot = int(round(self.p1_y + self.paddle_h))
        for y in range(p1_top, p1_bot):
            if 0 <= y < 16:
                idx = (y * 16 + 1) * 3
                fb[idx + 0], fb[idx + 1], fb[idx + 2] = 0, 210, 255

        # P2 挡板 (x=14, 金黄)
        p2_top = int(round(self.p2_y))
        p2_bot = int(round(self.p2_y + self.paddle_h))
        for y in range(p2_top, p2_bot):
            if 0 <= y < 16:
                idx = (y * 16 + 14) * 3
                fb[idx + 0], fb[idx + 1], fb[idx + 2] = 255, 168, 0

        # 反弹小球 (纯白)
        bx = int(round(self.ball_x))
        by = int(round(self.ball_y))
        if 0 <= bx < 16 and 0 <= by < 16:
            idx = (by * 16 + bx) * 3
            fb[idx + 0] = fb[idx + 1] = fb[idx + 2] = 255

        # 计分点
        for i in range(self.p1_score):
            idx = (0 * 16 + (3 + i)) * 3
            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 0, 210, 255
        for i in range(self.p2_score):
            idx = (0 * 16 + (12 - i)) * 3
            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 255, 168, 0

        # 胜利 / 失败光效
        if self.state == STATE_VICTORY:
            for y in range(16):
                idx = (y * 16 + 0) * 3
                fb[idx + 0], fb[idx + 1], fb[idx + 2] = 46, 204, 113
        elif self.state == STATE_GAMEOVER:
            for y in range(16):
                idx = (y * 16 + 15) * 3
                fb[idx + 0], fb[idx + 1], fb[idx + 2] = 231, 76, 60

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self._id,
            "name": self._name,
            "p1_score": self.p1_score,
            "p2_score": self.p2_score,
            "score": self.p1_score,
            "lives": 1 if self.state != STATE_GAMEOVER else 0,
            "state": self.state,
            "progress": (self.p1_score + self.p2_score) * 10,
        }
