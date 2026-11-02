# -*- coding: utf-8 -*-
"""
game_006_stack.py —— 堆叠大师 16 (Stack It Up 16)
编号: #006
年代: 2016 (Ketchapp / Stacker 街机)
核心独占机制: 左右平移方块 + 任意时刻单点下落 + 超出基座边缘瞬间切除并掉落 + 面积递减收缩
手柄类型: CTRL_TAP_SINGLE (全屏单键轻点)
"""

import math
from typing import Dict, Any, List, Tuple
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

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    c = v * s
    h_prime = (h / 60.0) % 6.0
    x = c * (1.0 - abs((h_prime % 2.0) - 1.0))
    m = v - c
    if 0 <= h_prime < 1:
        r, g, b = c, x, 0
    elif 1 <= h_prime < 2:
        r, g, b = x, c, 0
    elif 2 <= h_prime < 3:
        r, g, b = 0, c, x
    elif 3 <= h_prime < 4:
        r, g, b = 0, x, c
    elif 4 <= h_prime < 5:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

class StackLayer:
    def __init__(self, x: float, w: float, r: int, g: int, b: int):
        self.x = x
        self.w = w
        self.r = r
        self.g = g
        self.b = b

class FallingDebris:
    def __init__(self, x: float, y: float, w: float, r: int, g: int, b: int):
        self.x = x
        self.y = y
        self.w = w
        self.vy = 2.0
        self.r = r
        self.g = g
        self.b = b
        self.active = True

class Game006Stack(BaseCartridge):
    def __init__(self):
        self._id = 6
        self._name = "堆叠大师"
        self._english_name = "Stack It Up 16"
        self._year = 2016
        self._control_type = CTRL_TAP_SINGLE
        self._core_mechanic = "左右平移方块 + 任意时刻单点下落 + 超出基座边缘瞬间切除 + 面积递减收缩"

        self.state = STATE_TITLE
        self.current_row = 14
        self.active_x = 0.0
        self.active_w = 9.0
        self.active_vx = 7.5

        self.layers: List[StackLayer] = []
        self.debris: List[FallingDebris] = []
        self.score = 0
        self.high_score = 0
        self.perfect_combo = 0
        self.perfect_flash = 0.0
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

    def _get_layer_color(self, idx: int) -> Tuple[int, int, int]:
        hue = (idx * 14.0) % 360.0
        return hsv_to_rgb(hue, 0.85, 0.95)

    def reset(self) -> None:
        self.state = STATE_PLAYING
        self.score = 0
        self.perfect_combo = 0
        self.perfect_flash = 0.0
        self.state_timer = 0.0
        self.current_row = 14
        self.debris = []

        r, g, b = self._get_layer_color(0)
        self.layers = [StackLayer(3.5, 9.0, r, g, b)]

        self.active_x = 0.0
        self.active_w = 9.0
        self.active_vx = 7.5

    def place_block(self) -> None:
        base = self.layers[-1]
        base_left = base.x
        base_right = base.x + base.w
        act_left = self.active_x
        act_right = self.active_x + self.active_w

        # 完美对齐判定
        if abs(act_left - base_left) < 0.42:
            self.active_x = base_left
            self.perfect_combo += 1
            self.perfect_flash = 0.2
            if self.perfect_combo >= 3 and self.active_w < 9.0:
                self.active_w += 1.0
                if self.active_x > 0.0:
                    self.active_x -= 0.5
        else:
            self.perfect_combo = 0
            overlap_left = max(act_left, base_left)
            overlap_right = min(act_right, base_right)
            overlap_w = overlap_right - overlap_left

            # 完全未重叠 -> 坠落 Game Over
            if overlap_w <= 0.0:
                self.state = STATE_GAMEOVER
                self.state_timer = 0.0
                r, g, b = self._get_layer_color(self.score + 1)
                self.debris.append(FallingDebris(self.active_x, float(self.current_row), self.active_w, r, g, b))
                return

            # 切除多余部分并掉落
            r, g, b = self._get_layer_color(self.score + 1)
            if act_left < base_left:
                cut_x = act_left
                cut_w = base_left - act_left
                self.debris.append(FallingDebris(cut_x, float(self.current_row), cut_w, r, g, b))
            elif act_right > base_right:
                cut_x = base_right
                cut_w = act_right - base_right
                self.debris.append(FallingDebris(cut_x, float(self.current_row), cut_w, r, g, b))

            self.active_x = overlap_left
            self.active_w = overlap_w

        self.score += 1
        if self.score > self.high_score:
            self.high_score = self.score

        r, g, b = self._get_layer_color(self.score)
        self.layers.append(StackLayer(self.active_x, self.active_w, r, g, b))

        # 摄像机向下卷轴
        if self.current_row > 5:
            self.current_row -= 1
        else:
            self.layers.pop(0)

        # 调整下一层速度与方向
        speed = 7.5 + self.score * 0.15
        speed = min(14.0, speed)
        self.active_vx = -speed if self.active_vx > 0.0 else speed
        self.active_x = -self.active_w if self.active_vx > 0.0 else 16.0

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.perfect_flash > 0.0:
            self.perfect_flash = max(0.0, self.perfect_flash - dt)

        # 碎片物理
        for d in self.debris:
            if d.active:
                d.vy += 32.0 * dt
                d.y += d.vy * dt
                if d.y > 16.5:
                    d.active = False
        self.debris = [d for d in self.debris if d.active]

        if self.state == STATE_TITLE:
            self.active_x += 7.0 * dt
            if self.active_x > 16.0:
                self.active_x = -6.0
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state == STATE_GAMEOVER:
            if self.state_timer > 0.4 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_SELECT)):
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

            tap_mask = KEY_A | KEY_UP | KEY_B | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_SELECT
            if keys_pressed & tap_mask:
                self.place_block()
                return

            self.active_x += self.active_vx * dt
            if self.active_vx > 0.0 and self.active_x > 16.0:
                self.active_vx = -self.active_vx
                self.active_x = 16.0
            elif self.active_vx < 0.0 and (self.active_x + self.active_w) < 0.0:
                self.active_vx = -self.active_vx
                self.active_x = -self.active_w

    def render(self) -> bytearray:
        fb = self.frame_buffer
        bg_flash = int(self.perfect_flash * 180.0)

        for i in range(256):
            fb[i * 3 + 0] = min(255, 12 + bg_flash)
            fb[i * 3 + 1] = min(255, 15 + bg_flash)
            fb[i * 3 + 2] = min(255, 22 + bg_flash)

        # 绘制历史基座层
        for i, layer in enumerate(self.layers):
            row = 15 - i
            if 0 <= row < 16:
                start_x = int(round(layer.x))
                end_x = int(round(layer.x + layer.w))
                for x in range(start_x, end_x):
                    if 0 <= x < 16:
                        idx = (row * 16 + x) * 3
                        fb[idx + 0] = layer.r
                        fb[idx + 1] = layer.g
                        fb[idx + 2] = layer.b

        # 绘制平移中的活动方块
        if self.state in (STATE_PLAYING, STATE_TITLE):
            ar, ag, ab = self._get_layer_color(self.score + 1)
            row = self.current_row
            if 0 <= row < 16:
                start_x = int(round(self.active_x))
                end_x = int(round(self.active_x + self.active_w))
                for x in range(start_x, end_x):
                    if 0 <= x < 16:
                        idx = (row * 16 + x) * 3
                        fb[idx + 0] = ar
                        fb[idx + 1] = ag
                        fb[idx + 2] = ab

        # 绘制掉落碎片
        for d in self.debris:
            dy = int(round(d.y))
            if 0 <= dy < 16:
                start_x = int(round(d.x))
                end_x = int(round(d.x + d.w))
                for x in range(start_x, end_x):
                    if 0 <= x < 16:
                        idx = (dy * 16 + x) * 3
                        fb[idx + 0] = d.r >> 1
                        fb[idx + 1] = d.g >> 1
                        fb[idx + 2] = d.b >> 1

        # 状态边缘
        if self.state == STATE_GAMEOVER:
            for x in range(16):
                top = (0 * 16 + x) * 3
                bot = (15 * 16 + x) * 3
                fb[top + 0], fb[top + 1], fb[top + 2] = 231, 76, 60
                fb[bot + 0], fb[bot + 1], fb[bot + 2] = 231, 76, 60
        elif self.state == STATE_PAUSED:
            for y in range(5, 9):
                idx1 = (y * 16 + 6) * 3
                idx2 = (y * 16 + 9) * 3
                fb[idx1 + 0] = fb[idx1 + 1] = fb[idx1 + 2] = 245
                fb[idx2 + 0] = fb[idx2 + 1] = fb[idx2 + 2] = 245

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self._id,
            "name": self._name,
            "score": self.score,
            "high_score": self.high_score,
            "lives": 0 if self.state == STATE_GAMEOVER else 1,
            "state": self.state,
            "combo": self.perfect_combo,
            "width": round(self.active_w, 1),
            "progress": min(100, self.score * 4),
        }
