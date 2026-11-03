"""game_020_pong.py —— 目标 #020 双人乒乓 (Pong 1972)
双向挡板碰撞反弹 + 智能 AI 伴奏 / 双人同屏 + 5分决胜
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_VERSUS_DUAL,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen


class Game020Pong(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.p1_y = 6.0
        self.p2_y = 6.0
        self.paddle_h = 4.0
        self.ball_x = 7.5
        self.ball_y = 7.5
        self.ball_vx = 7.0
        self.ball_vy = 3.0
        self.p1_score = 0
        self.p2_score = 0
        self.p2_is_ai = True
        self.serve_delay = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 20

    @property
    def name(self) -> str:
        return "双人乒乓"

    @property
    def english_name(self) -> str:
        return "Pong 1972"

    @property
    def release_year(self) -> int:
        return 1972

    @property
    def control_type(self) -> int:
        return CTRL_VERSUS_DUAL

    @property
    def core_mechanic(self) -> str:
        return "双向挡板碰撞反弹与决胜对决"

    def init(self) -> None:
        self.reset()

    def _reset_ball(self, serve_to_right: bool):
        self.ball_x = 7.5
        self.ball_y = 7.5
        base_speed = 7.5
        self.ball_vx = base_speed if serve_to_right else -base_speed
        self.ball_vy = -2.5 if self.ball_y > 7.5 else 2.5
        self.serve_delay = 0.6

    def reset(self):
        self._state = STATE_TITLE
        self.p1_y = 6.0
        self.p2_y = 6.0
        self.paddle_h = 4.0
        self.p1_score = 0
        self.p2_score = 0
        self.p2_is_ai = True
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._score = 0
        self._reset_ball(True)

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.p1_y = 6.0
            self.p2_y = 6.0
            self.paddle_h = 4.0
            self.p1_score = 0
            self.p2_score = 0
            self.p2_is_ai = True
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._score = 0
            self._reset_ball(True)

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            paddle_speed = 6.0 * dt
            if self.ball_y < self.p1_y + 1.5 and self.p1_y > 0:
                self.p1_y -= paddle_speed
            elif self.ball_y > self.p1_y + 2.5 and self.p1_y < 16.0 - self.paddle_h:
                self.p1_y += paddle_speed

            if self.ball_y < self.p2_y + 1.5 and self.p2_y > 0:
                self.p2_y -= paddle_speed
            elif self.ball_y > self.p2_y + 2.5 and self.p2_y < 16.0 - self.paddle_h:
                self.p2_y += paddle_speed

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt
            if self.ball_y <= 0.0 or self.ball_y >= 15.0:
                self.ball_vy = -self.ball_vy
            if self.ball_x <= 2.0 or self.ball_x >= 13.0:
                self.ball_vx = -self.ball_vx

            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN)):
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

            paddle_speed = 9.5
            if keys_down & KEY_UP:
                self.p1_y -= paddle_speed * dt
            elif keys_down & KEY_DOWN:
                self.p1_y += paddle_speed * dt
            self.p1_y = max(0.0, min(16.0 - self.paddle_h, self.p1_y))

            if keys_down & KEY_A:
                self.p2_is_ai = False
                self.p2_y -= paddle_speed * dt
            elif keys_down & KEY_B:
                self.p2_is_ai = False
                self.p2_y += paddle_speed * dt
            elif self.p2_is_ai:
                ai_target_y = self.ball_y - (self.paddle_h * 0.5)
                ai_speed = 7.0 * dt
                if self.p2_y < ai_target_y - 0.5:
                    self.p2_y += ai_speed
                elif self.p2_y > ai_target_y + 0.5:
                    self.p2_y -= ai_speed
            self.p2_y = max(0.0, min(16.0 - self.paddle_h, self.p2_y))

            if self.serve_delay > 0.0:
                self.serve_delay -= dt
                return

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt

            if self.ball_y <= 0.0:
                self.ball_y = 0.0
                self.ball_vy = abs(self.ball_vy)
            elif self.ball_y >= 15.0:
                self.ball_y = 15.0
                self.ball_vy = -abs(self.ball_vy)

            if self.ball_vx < 0.0 and 0.5 <= self.ball_x <= 1.8:
                if (self.p1_y - 0.5) <= self.ball_y <= (self.p1_y + self.paddle_h + 0.5):
                    self.ball_x = 1.9
                    speed = min(16.0, abs(self.ball_vx) * 1.05)
                    self.ball_vx = speed
                    hit_offset = (self.ball_y - (self.p1_y + self.paddle_h * 0.5)) / (self.paddle_h * 0.5)
                    self.ball_vy = hit_offset * 7.5

            if self.ball_vx > 0.0 and 13.2 <= self.ball_x <= 14.8:
                if (self.p2_y - 0.5) <= self.ball_y <= (self.p2_y + self.paddle_h + 0.5):
                    self.ball_x = 13.1
                    speed = min(16.0, abs(self.ball_vx) * 1.05)
                    self.ball_vx = -speed
                    hit_offset = (self.ball_y - (self.p2_y + self.paddle_h * 0.5)) / (self.paddle_h * 0.5)
                    self.ball_vy = hit_offset * 7.5

            if self.ball_x < 0.0:
                self.p2_score += 1
                if self.p2_score >= 5:
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                else:
                    self._reset_ball(False)
            elif self.ball_x > 15.0:
                self.p1_score += 1
                self._score = self.p1_score * 10
                if self._score > self._high_score:
                    self._high_score = self._score
                if self.p1_score >= 5:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                else:
                    self._reset_ball(True)

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self.p1_score * 10, self._high_score, self.anim_timer
            )

        for y in range(0, 16, 2):
            idx = (y * 16 + 7) * 3
            fb[idx : idx + 3] = bytes([40, 40, 40])

        p1_top = int(round(self.p1_y))
        p1_bot = p1_top + int(self.paddle_h)
        for y in range(p1_top, min(16, p1_bot)):
            if y >= 0:
                idx = (y * 16 + 1) * 3
                fb[idx : idx + 3] = bytes([52, 152, 219])

        p2_top = int(round(self.p2_y))
        p2_bot = p2_top + int(self.paddle_h)
        for y in range(p2_top, min(16, p2_bot)):
            if y >= 0:
                idx = (y * 16 + 14) * 3
                fb[idx : idx + 3] = bytes([231, 76, 60])

        bx = int(round(self.ball_x))
        by = int(round(self.ball_y))
        if 0 <= bx < 16 and 0 <= by < 16:
            idx = (by * 16 + bx) * 3
            fb[idx : idx + 3] = bytes([241, 196, 15])

        for i in range(min(5, self.p1_score)):
            idx = (3 + i) * 3
            fb[idx : idx + 3] = bytes([52, 152, 219])
        for i in range(min(5, self.p2_score)):
            idx = (12 - i) * 3
            fb[idx : idx + 3] = bytes([231, 76, 60])

        if self._state == STATE_PAUSED:
            for y in range(6, 10):
                for col in (6, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([250, 250, 250])

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self.p1_score,
            "high_score": max(self.p1_score, self.p2_score),
            "lives": 1,
            "state": self._state,
            "progress": min(100, (self.p1_score + self.p2_score) * 10),
        }
