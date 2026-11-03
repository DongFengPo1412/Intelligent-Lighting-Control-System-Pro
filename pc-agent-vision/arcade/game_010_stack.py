"""game_010_stack.py —— 目标 #010 堆叠大师 16 (Stack Master 16)
单键切削堆叠 + 悬空截断 + 彩虹色环递进
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TAP_SINGLE,
    KEY_A,
    KEY_UP,
    KEY_B,
    KEY_SELECT,
    KEY_START,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_DOWN,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)
from .arcade_result_screen import ArcadeResultScreen


def hsv_to_rgb(h: float, s: float, v: float):
    c = v * s
    h_prime = (h / 60.0) % 6.0
    x = c * (1.0 - abs((h_prime % 2.0) - 1.0))
    m = v - c
    if 0 <= h_prime < 1:
        r1, g1, b1 = c, x, 0
    elif 1 <= h_prime < 2:
        r1, g1, b1 = x, c, 0
    elif 2 <= h_prime < 3:
        r1, g1, b1 = 0, c, x
    elif 3 <= h_prime < 4:
        r1, g1, b1 = 0, x, c
    elif 4 <= h_prime < 5:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x
    return int((r1 + m) * 255), int((g1 + m) * 255), int((b1 + m) * 255)


class StackLayer:
    def __init__(self, x: float, w: float, r: int, g: int, b: int):
        self.x = x
        self.w = w
        self.r = r
        self.g = g
        self.b = b


class FallingDebris:
    def __init__(self, x: float, y: float, w: float, vy: float, r: int, g: int, b: int):
        self.x = x
        self.y = y
        self.w = w
        self.vy = vy
        self.r = r
        self.g = g
        self.b = b
        self.active = True


class Game010Stack(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.current_row = 14
        self.active_x = 0.0
        self.active_w = 9.0
        self.active_vx = 7.5
        self.layers: List[StackLayer] = []
        self.debris: List[FallingDebris] = []
        self.perfect_combo = 0
        self.perfect_flash = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 10

    @property
    def name(self) -> str:
        return "堆叠大师"

    @property
    def english_name(self) -> str:
        return "Stack Master"

    @property
    def release_year(self) -> int:
        return 2016

    @property
    def control_type(self) -> int:
        return CTRL_TAP_SINGLE

    @property
    def core_mechanic(self) -> str:
        return "单键切削堆叠与悬空截断"

    def init(self) -> None:
        self.reset()

    def _get_layer_color(self, idx: int):
        hue = (idx * 14.0) % 360.0
        return hsv_to_rgb(hue, 0.85, 0.95)

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.perfect_combo = 0
        self.perfect_flash = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.current_row = 14
        self.debris = []

        r, g, b = self._get_layer_color(0)
        self.layers = [StackLayer(3.5, 9.0, r, g, b)]
        self.active_x = 0.0
        self.active_w = 9.0
        self.active_vx = 7.5

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER):
            self._state = STATE_PLAYING
            self._score = 0
            self.perfect_combo = 0
            self.perfect_flash = 0.0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.current_row = 14
            self.debris = []
            r, g, b = self._get_layer_color(0)
            self.layers = [StackLayer(3.5, 9.0, r, g, b)]
            self.active_x = 0.0
            self.active_w = 9.0
            self.active_vx = 7.5

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _place_block(self):
        base = self.layers[-1]
        act_left = self.active_x
        act_right = self.active_x + self.active_w
        base_left = base.x
        base_right = base.x + base.w

        if abs(act_left - base_left) < 0.42:
            self.active_x = base.x
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

            if overlap_w <= 0.3:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                if self._score > self._high_score:
                    self._high_score = self._score
                return

            cut_x = act_left if act_left < base_left else base_right
            cut_w = (base_left - act_left) if act_left < base_left else (act_right - base_right)
            r, g, b = self._get_layer_color(len(self.layers))
            self.debris.append(FallingDebris(cut_x, float(self.current_row), cut_w, 2.0, r, g, b))

            self.active_x = overlap_left
            self.active_w = overlap_w

        self._score += 1
        if self._score > self._high_score:
            self._high_score = self._score

        r, g, b = self._get_layer_color(len(self.layers))
        if len(self.layers) < 16:
            self.layers.append(StackLayer(self.active_x, self.active_w, r, g, b))
        else:
            self.layers.pop(0)
            self.layers.append(StackLayer(self.active_x, self.active_w, r, g, b))

        if self.current_row > 2:
            self.current_row -= 1

        speed = 7.5 + self._score * 0.28
        if self.active_vx > 0:
            self.active_x = 16.0 - self.active_w
            self.active_vx = -min(16.0, speed)
        else:
            self.active_x = 0.0
            self.active_vx = min(16.0, speed)

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self.perfect_flash > 0.0:
            self.perfect_flash -= dt

        for d in self.debris:
            if d.active:
                d.vy += 30.0 * dt
                d.y += d.vy * dt
                if d.y > 16.0:
                    d.active = False
        self.debris = [d for d in self.debris if d.active]

        if self._state == STATE_TITLE:
            self.active_x += self.active_vx * dt
            if self.active_x + self.active_w >= 16.0:
                self.active_x = 16.0 - self.active_w
                self.active_vx = -abs(self.active_vx)
            elif self.active_x <= 0.0:
                self.active_x = 0.0
                self.active_vx = abs(self.active_vx)
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN):
                self.start()
            return

        if self._state == STATE_GAMEOVER:
            if self.state_timer > 0.6 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP)):
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

            self.active_x += self.active_vx * dt
            if self.active_x + self.active_w >= 16.0:
                self.active_x = 16.0 - self.active_w
                self.active_vx = -abs(self.active_vx)
            elif self.active_x <= 0.0:
                self.active_x = 0.0
                self.active_vx = abs(self.active_vx)

            tap_mask = KEY_A | KEY_UP | KEY_B | KEY_SELECT | KEY_LEFT | KEY_RIGHT | KEY_DOWN
            if keys_pressed & tap_mask:
                self._place_block()

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state == STATE_GAMEOVER and self.state_timer > 0.8:
            return ArcadeResultScreen.render(False, self._score, self._high_score, self.anim_timer)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx : idx + 3] = bytes([12, 12, 20])

        for i, lyr in enumerate(self.layers):
            screen_y = 15 - i
            if screen_y < 0:
                continue
            lx1 = max(0, int(round(lyr.x)))
            lx2 = min(16, int(round(lyr.x + lyr.w)))
            for x in range(lx1, lx2):
                idx = (screen_y * 16 + x) * 3
                fb[idx : idx + 3] = bytes([lyr.r, lyr.g, lyr.b])

        if self._state in (STATE_PLAYING, STATE_TITLE, STATE_PAUSED):
            ax1 = max(0, int(round(self.active_x)))
            ax2 = min(16, int(round(self.active_x + self.active_w)))
            ar, ag, ab = self._get_layer_color(len(self.layers))
            if self.perfect_flash > 0.0:
                ar, ag, ab = 255, 255, 255
            for x in range(ax1, ax2):
                idx = (self.current_row * 16 + x) * 3
                fb[idx : idx + 3] = bytes([ar, ag, ab])

        for d in self.debris:
            if d.active:
                dy = int(round(d.y))
                if 0 <= dy < 16:
                    dx1 = max(0, int(round(d.x)))
                    dx2 = min(16, int(round(d.x + d.w)))
                    for x in range(dx1, dx2):
                        idx = (dy * 16 + x) * 3
                        fb[idx : idx + 3] = bytes([d.r // 2, d.g // 2, d.b // 2])

        if self._state == STATE_PAUSED:
            for y in range(6, 10):
                for col in (6, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([250, 250, 250])

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, self._score * 4),
        }
