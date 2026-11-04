# -*- coding: utf-8 -*-
"""game_022_pinball.py —— 目标 #022 迷你弹珠台 (Mini Pinball)
重力弹珠台 + 发光弹射蘑菇头(+25/+50) + 侧翼弹弓 + 左右独立挡板(A/LEFT 与 B/RIGHT)
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
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

PINBALL_GRAVITY = 16.5
MAX_BALL_SPEED = 16.5


class PinballBumper:
    def __init__(self, x: float, y: float, points: int):
        self.x = x
        self.y = y
        self.points = points
        self.flash_timer = 0.0


class Game022Pinball(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.ball_x = 11.5
        self.ball_y = 2.5
        self.ball_vx = -4.2
        self.ball_vy = 1.5
        self.left_flipper_up = False
        self.right_flipper_up = False
        self.left_swing_timer = 0.0
        self.right_swing_timer = 0.0
        self.sling_flash_l = 0.0
        self.sling_flash_r = 0.0
        self.bumpers: List[PinballBumper] = []
        self.balls_left = 3
        self._seed = 0x22197901
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 22

    @property
    def name(self) -> str:
        return "迷你弹珠台"

    @property
    def english_name(self) -> str:
        return "Mini Pinball"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "重力斜面滚球与左右双独立挡板抽射弹撞"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_bumpers(self) -> None:
        self.bumpers = [
            PinballBumper(4.5, 4.5, 25),
            PinballBumper(10.5, 4.5, 25),
            PinballBumper(7.5, 7.2, 50),
        ]

    def _spawn_ball(self) -> None:
        jitter = (float(self._next_rand() % 21) - 10.0) * 0.08
        self.ball_x = 11.5
        self.ball_y = 2.2
        self.ball_vx = -4.5 + jitter
        self.ball_vy = 1.2

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.left_flipper_up = False
        self.right_flipper_up = False
        self.left_swing_timer = 0.0
        self.right_swing_timer = 0.0
        self.sling_flash_l = 0.0
        self.sling_flash_r = 0.0
        self.balls_left = 3
        self._score = 0
        self._seed = 0x22197901
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._init_bumpers()
        self._spawn_ball()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.left_flipper_up = False
            self.right_flipper_up = False
            self.left_swing_timer = 0.0
            self.right_swing_timer = 0.0
            self.sling_flash_l = 0.0
            self.sling_flash_r = 0.0
            self.balls_left = 3
            self._score = 0
            self._seed = 0x22197901
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._init_bumpers()
            self._spawn_ball()

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
            self.ball_x = 7.5 + math.cos(self.anim_timer * 2.8) * 3.5
            self.ball_y = 6.0 + math.sin(self.anim_timer * 3.6) * 2.5
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
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

            self.left_flipper_up = (keys_down & (KEY_A | KEY_LEFT)) != 0
            self.right_flipper_up = (keys_down & (KEY_B | KEY_RIGHT)) != 0

            if keys_pressed & (KEY_A | KEY_LEFT):
                self.left_swing_timer = 0.22
            elif self.left_swing_timer > 0.0:
                self.left_swing_timer = max(0.0, self.left_swing_timer - dt)

            if keys_pressed & (KEY_B | KEY_RIGHT):
                self.right_swing_timer = 0.22
            elif self.right_swing_timer > 0.0:
                self.right_swing_timer = max(0.0, self.right_swing_timer - dt)

            if self.sling_flash_l > 0.0:
                self.sling_flash_l = max(0.0, self.sling_flash_l - dt)
            if self.sling_flash_r > 0.0:
                self.sling_flash_r = max(0.0, self.sling_flash_r - dt)
            for b in self.bumpers:
                if b.flash_timer > 0.0:
                    b.flash_timer = max(0.0, b.flash_timer - dt)

            self.ball_vy += PINBALL_GRAVITY * dt
            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt

            if self.ball_x < 1.2:
                self.ball_x = 1.2
                self.ball_vx = max(1.5, abs(self.ball_vx) * 0.85)
            elif self.ball_x > 13.8:
                self.ball_x = 13.8
                self.ball_vx = min(-1.5, -abs(self.ball_vx) * 0.85)
            if self.ball_y < 1.2:
                self.ball_y = 1.2
                self.ball_vy = abs(self.ball_vy) * 0.85

            if 10.5 <= self.ball_y <= 12.8:
                if self.ball_x <= 2.6:
                    self.ball_x = 2.8
                    self.ball_vx = 6.8
                    self.ball_vy = -8.5
                    self.sling_flash_l = 0.20
                    self._add_score(15)
                elif self.ball_x >= 12.4:
                    self.ball_x = 12.2
                    self.ball_vx = -6.8
                    self.ball_vy = -8.5
                    self.sling_flash_r = 0.20
                    self._add_score(15)

            for b in self.bumpers:
                dx = self.ball_x - b.x
                dy = self.ball_y - b.y
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1.45 * 1.45:
                    dist = math.sqrt(dist_sq)
                    nx = (dx / dist) if dist > 0.01 else 0.0
                    ny = (dy / dist) if dist > 0.01 else -1.0
                    self.ball_x = b.x + nx * 1.50
                    self.ball_y = b.y + ny * 1.50
                    self.ball_vx = nx * 10.5
                    self.ball_vy = ny * 10.5
                    b.flash_timer = 0.22
                    self._add_score(b.points)

            if 12.8 <= self.ball_y <= 14.6 and 2.6 <= self.ball_x <= 6.8 and self.ball_vy > -1.0:
                if self.left_flipper_up or self.left_swing_timer > 0.0:
                    self.ball_y = 12.6
                    self.ball_vy = -14.2 if self.left_swing_timer > 0.0 else -11.5
                    self.ball_vx = 2.0 + (self.ball_x - 3.0) * 2.2
                    self._add_score(10)
                elif self.ball_vy > 0.0:
                    self.ball_y = 12.8
                    self.ball_vy = -abs(self.ball_vy) * 0.35
                    self.ball_vx += 1.8

            if 12.8 <= self.ball_y <= 14.6 and 8.2 <= self.ball_x <= 12.4 and self.ball_vy > -1.0:
                if self.right_flipper_up or self.right_swing_timer > 0.0:
                    self.ball_y = 12.6
                    self.ball_vy = -14.2 if self.right_swing_timer > 0.0 else -11.5
                    self.ball_vx = -2.0 - (12.0 - self.ball_x) * 2.2
                    self._add_score(10)
                elif self.ball_vy > 0.0:
                    self.ball_y = 12.8
                    self.ball_vy = -abs(self.ball_vy) * 0.35
                    self.ball_vx -= 1.8

            spd = math.hypot(self.ball_vx, self.ball_vy)
            if spd > MAX_BALL_SPEED:
                sc = MAX_BALL_SPEED / spd
                self.ball_vx *= sc
                self.ball_vy *= sc

            if self.ball_y >= 16.0:
                if self.balls_left > 1:
                    self.balls_left -= 1
                    self._spawn_ball()
                else:
                    self.balls_left = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return

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
                if x in (0, 15) or y == 0:
                    self._set_px(fb, x, y, 150, 160, 190)
                else:
                    self._set_px(fb, x, y, 10, 14, 36)

        self._set_px(fb, 7, 15, 0, 0, 0)
        self._set_px(fb, 8, 15, 0, 0, 0)

        sl = (255, 255, 120) if self.sling_flash_l > 0.0 else (180, 60, 210)
        self._set_px(fb, 1, 11, *sl)
        self._set_px(fb, 2, 12, *sl)

        sr = (255, 255, 120) if self.sling_flash_r > 0.0 else (180, 60, 210)
        self._set_px(fb, 14, 11, *sr)
        self._set_px(fb, 13, 12, *sr)

        for b in self.bumpers:
            bx = int(round(b.x))
            by = int(round(b.y))
            if b.flash_timer > 0.0:
                self._set_px(fb, bx, by, 255, 255, 255)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._set_px(fb, bx + dx, by + dy, 255, 230, 40)
            elif b.points >= 50:
                self._set_px(fb, bx, by, 255, 190, 20)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._set_px(fb, bx + dx, by + dy, 210, 90, 20)
            else:
                self._set_px(fb, bx, by, 245, 50, 75)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._set_px(fb, bx + dx, by + dy, 160, 25, 45)

        self._set_px(fb, 3, 13, 0, 220, 255)
        self._set_px(fb, 4, 13, 0, 220, 255)
        self._set_px(fb, 5, 12 if self.left_flipper_up else 14, 80, 245, 255)
        self._set_px(fb, 6, 12 if self.left_flipper_up else 14, 200, 255, 255)

        self._set_px(fb, 12, 13, 255, 140, 25)
        self._set_px(fb, 11, 13, 255, 140, 25)
        self._set_px(fb, 10, 12 if self.right_flipper_up else 14, 255, 195, 50)
        self._set_px(fb, 9, 12 if self.right_flipper_up else 14, 255, 245, 160)

        if self._state != STATE_GAMEOVER:
            px = int(round(self.ball_x))
            py = int(round(self.ball_y))
            self._set_px(fb, px, py, 255, 255, 255)

        for b in range(min(self.balls_left, 3)):
            self._set_px(fb, 1 + b * 2, 0, 255, 215, 30)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.balls_left,
            "state": self._state,
            "progress": min(100, self._score // 10),
        }
