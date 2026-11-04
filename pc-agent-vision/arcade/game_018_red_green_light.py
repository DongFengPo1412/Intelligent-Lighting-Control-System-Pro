# -*- coding: utf-8 -*-
"""game_018_red_green_light.py —— 目标 #018 红灯绿灯 (Red Light Green)
顶部绿/黄闪烁/红信号灯与监察木偶 + 按住A/UP冲刺松开急刹 + 红灯移动激光淘汰
"""

from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_TAP_SINGLE,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

SIGNAL_GREEN = 0
SIGNAL_YELLOW = 1
SIGNAL_RED = 2

YELLOW_DURATION = 0.55
RED_GRACE_TIME = 0.08
FINISH_LINE_Y = 3.0
START_LINE_Y = 15.0
ROUND_TIME_LIMIT = 18.0
TOTAL_ROUNDS = 3


class Game018RedGreenLight(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.signal = SIGNAL_GREEN
        self.signal_timer = 1.5
        self.red_elapsed = 0.0
        self.player_x = 7.5
        self.player_y = START_LINE_Y
        self.round = 1
        self.round_timer = ROUND_TIME_LIMIT
        self.laser_eliminated = False
        self._seed = 0x18202101
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 18

    @property
    def name(self) -> str:
        return "红灯绿灯"

    @property
    def english_name(self) -> str:
        return "Red Light Green"

    @property
    def release_year(self) -> int:
        return 2021

    @property
    def control_type(self) -> int:
        return CTRL_TAP_SINGLE

    @property
    def core_mechanic(self) -> str:
        return "绿灯长按冲刺与黄灯预警急刹止步"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _next_green_duration(self) -> float:
        base = max(0.85, 1.55 - float(self.round - 1) * 0.22)
        return base + float(self._next_rand() % 5) * 0.10

    def _next_red_duration(self) -> float:
        return 1.05 + float(self._next_rand() % 5) * 0.12

    def _start_round(self, round_num: int) -> None:
        self.round = round_num
        self.player_x = 7.5
        self.player_y = START_LINE_Y
        self.round_timer = ROUND_TIME_LIMIT
        self.signal = SIGNAL_GREEN
        self.signal_timer = self._next_green_duration()
        self.red_elapsed = 0.0
        self.laser_eliminated = False

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self._seed = 0x18202101
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._start_round(1)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self._seed = 0x18202101
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._start_round(1)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt < 0.0:
            dt = 0.0
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.signal = int(self.anim_timer * 1.5) % 3
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP)):
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

            self.round_timer -= dt
            if self.round_timer <= 0.0:
                self.round_timer = 0.0
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

            self.signal_timer -= dt
            if self.signal == SIGNAL_RED:
                self.red_elapsed += dt
            if self.signal_timer <= 0.0:
                if self.signal == SIGNAL_GREEN:
                    self.signal = SIGNAL_YELLOW
                    self.signal_timer = YELLOW_DURATION
                elif self.signal == SIGNAL_YELLOW:
                    self.signal = SIGNAL_RED
                    self.signal_timer = self._next_red_duration()
                    self.red_elapsed = 0.0
                else:
                    self.signal = SIGNAL_GREEN
                    self.signal_timer = self._next_green_duration()
                    self.red_elapsed = 0.0

            move_mask = KEY_A | KEY_UP
            moving = (keys_down & move_mask) != 0

            if self.signal == SIGNAL_RED and self.red_elapsed > RED_GRACE_TIME and moving:
                self.laser_eliminated = True
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

            if moving:
                run_speed = 4.6 + float(self.round - 1) * 0.7
                self.player_y -= run_speed * dt
                if self.player_y <= FINISH_LINE_Y:
                    self.player_y = FINISH_LINE_Y
                    time_bonus = int(self.round_timer * 5.0)
                    self._add_score(100 + time_bonus)
                    if self.round >= TOTAL_ROUNDS:
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
                        return
                    self._start_round(self.round + 1)

    @staticmethod
    def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < 16 and 0 <= y < 16:
            idx = (y * 16 + x) * 3
            fb[idx] = r
            fb[idx + 1] = g
            fb[idx + 2] = b

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)
        for y in range(16):
            for x in range(16):
                if y <= 2:
                    self._set_px(fb, x, y, 16, 18, 28)
                elif y == 3:
                    alt = (x % 2) == 0
                    self._set_px(fb, x, y, 255 if alt else 40, 215 if alt else 40, 40 if alt else 50)
                else:
                    shade = 0 if ((x + y) % 2 == 0) else 8
                    self._set_px(fb, x, y, 138 + shade, 106 + shade, 62)

        sr, sg, sb = 30, 230, 85
        if self.signal == SIGNAL_YELLOW:
            blink_on = (int(self.anim_timer * 14.0) % 2) == 0
            sr = 255 if blink_on else 110
            sg = 205 if blink_on else 85
            sb = 15
        elif self.signal == SIGNAL_RED:
            sr, sg, sb = 245, 30, 35

        for y in range(2):
            for x in range(11):
                self._set_px(fb, x, y, sr, sg, sb)

        for y in range(3):
            for x in range(12, 15):
                if y == 0:
                    self._set_px(fb, x, y, 60, 40, 25)
                elif y == 1:
                    if self.signal == SIGNAL_RED and x in (12, 14):
                        self._set_px(fb, x, y, 255, 25, 25)
                    else:
                        self._set_px(fb, x, y, 235, 190, 145)
                else:
                    self._set_px(fb, x, y, 240, 130, 30)

        for r in range(min(self.round, TOTAL_ROUNDS)):
            self._set_px(fb, r * 2, 2, 0, 230, 255)

        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if self.laser_eliminated and self._state == STATE_GAMEOVER:
            for s in range(13):
                t = s / 12.0
                lx = int(round(13.0 + (self.player_x - 13.0) * t))
                ly = int(round(1.0 + (self.player_y - 1.0) * t))
                self._set_px(fb, lx, ly, 255, 40, 80)

        if self._state == STATE_GAMEOVER and self.laser_eliminated:
            self._set_px(fb, px, py, 255, 80, 20)
            self._set_px(fb, px + 1, py, 255, 200, 40)
        else:
            self._set_px(fb, px, py - 1, 245, 205, 165)
            self._set_px(fb, px, py, 25, 195, 145)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        round_frac = max(0.0, min(1.0, (START_LINE_Y - self.player_y) / (START_LINE_Y - FINISH_LINE_Y)))
        prog = 100 if self._state == STATE_VICTORY else int(((self.round - 1 + round_frac) / TOTAL_ROUNDS) * 100.0)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, prog),
        }
