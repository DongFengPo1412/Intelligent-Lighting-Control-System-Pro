# -*- coding: utf-8 -*-
"""
game_005_flappy_bird.py —— 飞翔小鸟 16 (Flappy Bird 16)
编号: #005
年代: 2013 (阮哈东 / .GEARS)
核心独占机制: 持续重力下坠 + 单键轻触瞬时拍翅脉冲 + 管道上下窄缝穿行
手柄类型: CTRL_TAP_SINGLE (全屏单键轻触)
"""

import math
import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    KEY_SELECT,
    CTRL_TAP_SINGLE,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)

class PipeObstacle:
    def __init__(self, x: float, gap_y: int, gap_height: int = 5):
        self.x = x
        self.gap_y = gap_y
        self.gap_height = gap_height
        self.scored = False

class Game005FlappyBird(BaseCartridge):
    def __init__(self):
        self._id = 5
        self._name = "飞翔小鸟"
        self._english_name = "Flappy Bird 16"
        self._year = 2013
        self._control_type = CTRL_TAP_SINGLE
        self._core_mechanic = "持续重力下坠 + 单键轻触瞬时拍翅脉冲 + 管道上下窄缝穿行"

        self.state = STATE_TITLE
        self.bird_x = 3.0
        self.bird_y = 6.0
        self.bird_vy = -6.0
        self.flap_anim = False
        self.flap_timer = 0.0

        self.pipes: List[PipeObstacle] = []
        self.score = 0
        self.high_score = 0
        self.ground_scroll = 0.0
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

    def _spawn_pipe(self, start_x: float) -> PipeObstacle:
        gap_h = 4 if self.score > 10 else 5
        max_top = 13 - gap_h
        gap_y = random.randint(2, max_top)
        return PipeObstacle(start_x, gap_y, gap_h)

    def reset(self) -> None:
        self.state = STATE_PLAYING
        self.bird_x = 3.0
        self.bird_y = 6.0
        self.bird_vy = -6.0
        self.flap_anim = False
        self.flap_timer = 0.0
        self.score = 0
        self.ground_scroll = 0.0
        self.state_timer = 0.0

        self.pipes = [
            self._spawn_pipe(16.0),
            self._spawn_pipe(26.0),
        ]

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            self.bird_y = 6.5 + math.sin(self.state_timer * 4.0) * 1.5
            self.ground_scroll += 4.0 * dt
            if self.ground_scroll >= 16.0:
                self.ground_scroll -= 16.0
            if keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_DOWN | KEY_B):
                self.reset()
            return

        if self.state == STATE_GAMEOVER:
            if self.bird_y < 13.0:
                self.bird_vy += 35.0 * dt
                self.bird_y = min(13.0, self.bird_y + self.bird_vy * dt)
            if self.state_timer > 0.4 and (keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_B)):
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

            # 全屏单键轻拍
            tap_mask = KEY_A | KEY_UP | KEY_B | KEY_SELECT | KEY_LEFT | KEY_RIGHT
            if keys_pressed & tap_mask:
                self.bird_vy = -11.0
                self.flap_anim = True
                self.flap_timer = 0.15

            if self.flap_timer > 0.0:
                self.flap_timer -= dt
                if self.flap_timer <= 0.0:
                    self.flap_anim = False

            gravity = 32.0
            self.bird_vy = min(14.0, self.bird_vy + gravity * dt)
            self.bird_y += self.bird_vy * dt

            pipe_speed = 5.0
            self.ground_scroll += pipe_speed * dt
            if self.ground_scroll >= 16.0:
                self.ground_scroll -= 16.0

            for i, p in enumerate(self.pipes):
                p.x -= pipe_speed * dt

                # 穿越计分
                if not p.scored and (p.x + 2.0 < self.bird_x):
                    p.scored = True
                    self.score += 1
                    if self.score > self.high_score:
                        self.high_score = self.score

                # 左出右进循环
                if p.x < -3.0:
                    other_idx = 1 if i == 0 else 0
                    new_x = max(16.0, self.pipes[other_idx].x + 10.5)
                    new_p = self._spawn_pipe(new_x)
                    p.x = new_p.x
                    p.gap_y = new_p.gap_y
                    p.gap_height = new_p.gap_height
                    p.scored = False

            # 碰撞检测
            bx1 = self.bird_x
            bx2 = self.bird_x + 1.8
            by1 = self.bird_y
            by2 = self.bird_y + 1.8

            # 天花板与地面碰撞
            if by1 < 0.0 or by2 >= 13.5:
                self.state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

            # 管道碰撞
            for p in self.pipes:
                px1 = p.x
                px2 = p.x + 2.0
                if bx2 >= px1 and bx1 <= px2:
                    gap_top = float(p.gap_y)
                    gap_bottom = gap_top + float(p.gap_height)
                    if by1 < gap_top or by2 > gap_bottom:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

    def render(self) -> bytearray:
        fb = self.frame_buffer

        # 1. 天蓝色背景渐变
        for y in range(14):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx + 0] = 52
                fb[idx + 1] = 152 + (y * 3)
                fb[idx + 2] = 219

        # 2. 地面草坪层
        for x in range(16):
            idx14 = (14 * 16 + x) * 3
            idx15 = (15 * 16 + x) * 3
            fb[idx14 + 0], fb[idx14 + 1], fb[idx14 + 2] = 46, 204, 113
            fb[idx15 + 0], fb[idx15 + 1], fb[idx15 + 2] = 211, 84, 0

        # 3. 翡翠绿双段管道
        for p in self.pipes:
            px = int(round(p.x))
            gap_y = p.gap_y
            gap_h = p.gap_height

            for dx in range(2):
                x = px + dx
                if 0 <= x < 16:
                    # 上截管道
                    for y in range(gap_y):
                        idx = (y * 16 + x) * 3
                        if y == gap_y - 1:
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 39, 174, 96
                        else:
                            color = (46, 204, 113) if dx == 0 else (34, 153, 84)
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = color

                    # 下截管道
                    for y in range(gap_y + gap_h, 14):
                        idx = (y * 16 + x) * 3
                        if y == gap_y + gap_h:
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 39, 174, 96
                        else:
                            color = (46, 204, 113) if dx == 0 else (34, 153, 84)
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = color

        # 4. 亮黄小鸟 (2x2)
        bx = int(round(self.bird_x))
        by = int(round(self.bird_y))
        for dy in range(2):
            for dx in range(2):
                x = bx + dx
                y = by + dy
                if 0 <= x < 16 and 0 <= y < 16:
                    idx = (y * 16 + x) * 3
                    if dy == 0:
                        if dx == 0:
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 241, 196, 15
                        else:
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 255, 255, 255
                    else:
                        if dx == 0:
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = (243, 156, 18) if self.flap_anim else (230, 126, 34)
                        else:
                            fb[idx + 0], fb[idx + 1], fb[idx + 2] = 231, 76, 60

        # 5. 警示与暂停
        if self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (0 * 16 + x) * 3
                fb[idx + 0], fb[idx + 1], fb[idx + 2] = 231, 76, 60
        elif self.state == STATE_PAUSED:
            for y in range(5, 9):
                idx1 = (y * 16 + 6) * 3
                idx2 = (y * 16 + 9) * 3
                fb[idx1 + 0] = fb[idx1 + 1] = fb[idx1 + 2] = 250
                fb[idx2 + 0] = fb[idx2 + 1] = fb[idx2 + 2] = 250

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self._id,
            "name": self._name,
            "score": self.score,
            "high_score": self.high_score,
            "lives": 0 if self.state == STATE_GAMEOVER else 1,
            "state": self.state,
            "progress": min(100, self.score * 5),
        }

