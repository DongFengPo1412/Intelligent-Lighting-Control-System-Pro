"""
Game #059: 经典田径赛 / 奥运百米与标枪 (Track & Field 1983 / Konami)
Olympic Athletics with High-Frequency Alternating Sprinting, Launch Angle Calibration & Foul Line Deciding Throws.
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)

STATE_START = 0
STATE_RUNNING = 1
STATE_ANGLE_AIM = 2
STATE_FLIGHT = 3
STATE_FOUL = 4
STATE_RESULT = 5
STATE_DEAD = 6
STATE_VICTORY = 7

DEG2RAD = math.pi / 180.0


class Game059TrackField(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 3000

        self.attempt = 1
        self.athlete_x = 1.0
        self.athlete_y = 13.0
        self.speed = 0.0
        self.last_button_pressed = 0

        self.throw_angle = 0.0
        self.javelin_x = 0.0
        self.javelin_y = 0.0
        self.javelin_vx = 0.0
        self.javelin_vy = 0.0
        self.throw_distance = 0.0
        self.best_distance = 0.0
        self.qualify_distance = 65.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 59

    @property
    def name(self) -> str:
        return "经典田径赛"

    @property
    def english_name(self) -> str:
        return "Track & Field"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "极限双键狂暴交替高频奔跑 + 最佳仰角投掷标枪与起跳踏板绝杀"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_RUNNING
        self.state_timer = 0.0
        self.score = 0
        self.attempt = 1
        self.best_distance = 0.0
        self.init_attempt()

    def init_attempt(self):
        self.athlete_x = 1.0
        self.athlete_y = 13.0
        self.speed = 0.0
        self.last_button_pressed = 0
        self.throw_angle = 0.0
        self.throw_distance = 0.0
        self.state = STATE_RUNNING
        self.state_timer = 0.0

    def trigger_release(self, angle: float):
        self.throw_angle = angle
        self.state = STATE_FLIGHT
        self.state_timer = 0.0

        v0 = max(6.0, self.speed) * 2.8
        rad = self.throw_angle * DEG2RAD
        self.javelin_x = self.athlete_x
        self.javelin_y = self.athlete_y - 1.0
        self.javelin_vx = v0 * math.cos(rad)
        self.javelin_vy = -v0 * math.sin(rad)

        self.throw_distance = (v0 * v0 * math.sin(2.0 * rad)) / 9.8
        if self.throw_distance > self.best_distance:
            self.best_distance = self.throw_distance

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 2.0:
                self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_RUNNING
                self.state_timer = 0.0
                self.attempt = 1
                self.init_attempt()
            return

        if self.state in (STATE_FOUL, STATE_RESULT):
            if self.state_timer > 1.8:
                if self.throw_distance >= self.qualify_distance:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += int(self.throw_distance * 50.0)
                    if self.score > self.high_score:
                        self.high_score = self.score
                else:
                    self.attempt += 1
                    if self.attempt > 3:
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                    else:
                        self.init_attempt()
            return

        if self.state == STATE_RUNNING:
            btn_a = bool((buttons & KEY_A) and not (prev_buttons & KEY_A))
            btn_b = bool((buttons & KEY_B) and not (prev_buttons & KEY_B))

            if btn_a:
                if self.last_button_pressed == 2:
                    self.speed = min(12.0, self.speed + 2.0)
                else:
                    self.speed = max(0.0, self.speed - 0.4)
                self.last_button_pressed = 1
            elif btn_b:
                if self.last_button_pressed == 1:
                    self.speed = min(12.0, self.speed + 2.0)
                else:
                    self.speed = max(0.0, self.speed - 0.4)
                self.last_button_pressed = 2

            self.speed = max(0.0, self.speed - 3.5 * dt)
            self.athlete_x += self.speed * dt

            if buttons & KEY_UP:
                self.state = STATE_ANGLE_AIM
                self.throw_angle = 10.0

            if self.athlete_x >= 11.5:
                self.state = STATE_FOUL
                self.state_timer = 0.0
                self.throw_distance = 0.0
                self.speed = 0.0

        elif self.state == STATE_ANGLE_AIM:
            self.throw_angle += 95.0 * dt
            if self.throw_angle > 80.0:
                self.throw_angle = 80.0

            self.athlete_x += self.speed * dt

            if self.athlete_x >= 11.5:
                self.state = STATE_FOUL
                self.state_timer = 0.0
                self.throw_distance = 0.0
                self.speed = 0.0
                return

            if not (buttons & KEY_UP) or ((buttons & KEY_A) and not (prev_buttons & KEY_A)):
                self.trigger_release(self.throw_angle)

        elif self.state == STATE_FLIGHT:
            self.javelin_x += self.javelin_vx * dt
            self.javelin_y += self.javelin_vy * dt
            self.javelin_vy += 20.0 * dt

            if self.javelin_y >= 13.0:
                self.javelin_y = 13.0
                self.state = STATE_RESULT
                self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Spectators y=0..4
        for y in range(5):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = (60 + (x * 17 + y * 23) % 180)
                fb[idx + 1] = (40 + (x * 11 + y * 31) % 150)
                fb[idx + 2] = (80 + (x * 7 + y * 13) % 150)

        # Field y=5..11
        for y in range(5, 12):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 30
                fb[idx + 1] = 160 + (y % 2) * 20
                fb[idx + 2] = 30

        # Track y=12..14
        for y in range(12, 15):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 200
                fb[idx + 1] = 60
                fb[idx + 2] = 40
                if y == 12 or y == 14:
                    fb[idx] = 240; fb[idx + 1] = 240; fb[idx + 2] = 240
                if x == 11:
                    fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255

        # Athlete
        ax = int(round(self.athlete_x))
        ay = int(round(self.athlete_y))
        if 0 <= ax < 16 and 0 <= ay < 16:
            idx = (ay * 16 + ax) * 3
            fb[idx] = 40; fb[idx + 1] = 80; fb[idx + 2] = 220
            if ay > 0:
                body_idx = ((ay - 1) * 16 + ax) * 3
                fb[body_idx] = 255; fb[body_idx + 1] = 255; fb[body_idx + 2] = 255

        # Javelin
        if self.state in (STATE_FLIGHT, STATE_RESULT):
            jx = int(round(self.javelin_x))
            jy = int(round(self.javelin_y))
            if 0 <= jx < 16 and 0 <= jy < 16:
                idx = (jy * 16 + jx) * 3
                fb[idx] = 255; fb[idx + 1] = 240; fb[idx + 2] = 0

        # Foul banner
        if self.state == STATE_FOUL:
            idx = (11 * 16 + 11) * 3
            fb[idx] = 255; fb[idx + 1] = 0; fb[idx + 2] = 0

        # Speed Gauge
        speed_bars = int((self.speed / 12.0) * 8.0)
        for s in range(min(speed_bars, 8)):
            idx = s * 3
            fb[idx] = 255 if s > 5 else 0
            fb[idx + 1] = 100 if s > 5 else 255
            fb[idx + 2] = 0

        # Attempt counter
        for a in range(3):
            idx = (15 - a) * 3
            if a < self.attempt:
                fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255
            else:
                fb[idx] = 60;  fb[idx + 1] = 60;  fb[idx + 2] = 60

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "attempt": self.attempt,
            "speed": self.speed,
            "throw_angle": self.throw_angle,
            "throw_distance": self.throw_distance,
            "best_distance": self.best_distance,
        }
