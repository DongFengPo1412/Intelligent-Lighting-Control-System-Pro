"""
Game #060: 极速疯狂弹球 (Marble Madness 1984 / Atari / Mark Cerny)
Isometric True Physics Marble Rolling, Downhill Slope Gravity, Cliff Edge Fractures & Ice Gliding.
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
STATE_PLAYING = 1
STATE_SHATTERED = 2
STATE_DEAD = 3
STATE_VICTORY = 4


class Game060MarbleMadness(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 3500
        self.time_remaining = 35.0

        self.marble_x = 2.5
        self.marble_y = 2.0
        self.marble_vx = 0.0
        self.marble_vy = 0.0
        self.is_on_ice = False

        self.evil_x = 8.0
        self.evil_y = 8.5
        self.evil_vx = -2.0
        self.evil_vy = 1.0

        self.acid_x = 8.5
        self.acid_y = 11.5
        self.goal_x = 12.5
        self.goal_y = 14.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 60

    @property
    def name(self) -> str:
        return "极速疯狂弹球"

    @property
    def english_name(self) -> str:
        return "Marble Madness"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "轨迹球物理斜向立体迷宫滚球 + 离心力弯道贴壁 + 冰面惯性滑行与吸食怪规避"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.time_remaining = 35.0
        self.init_course()

    def init_course(self):
        self.marble_x = 2.5
        self.marble_y = 2.0
        self.marble_vx = 0.0
        self.marble_vy = 0.0
        self.is_on_ice = False

        self.evil_x = 8.0
        self.evil_y = 8.5
        self.evil_vx = -2.0
        self.evil_vy = 1.0

        self.acid_x = 8.5
        self.acid_y = 11.5
        self.goal_x = 12.5
        self.goal_y = 14.0

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 2.0:
                self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_course()
            return

        if self.state == STATE_SHATTERED:
            if self.state_timer > 1.2:
                if self.time_remaining > 0.0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.marble_x = 2.5
                    self.marble_y = 2.0
                    self.marble_vx = 0.0
                    self.marble_vy = 0.0
                else:
                    self.state = STATE_DEAD
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        # Ice check
        self.is_on_ice = (5.5 <= self.marble_y <= 9.5 and 4.0 <= self.marble_x <= 10.5)

        # Physics
        ax = 0.0
        ay = 0.0
        torque = 6.0 if self.is_on_ice else 14.0

        if buttons & KEY_LEFT:  ax -= torque
        if buttons & KEY_RIGHT: ax += torque
        if buttons & KEY_UP:    ay -= torque
        if buttons & KEY_DOWN:  ay += torque

        # Slope downhill gravity
        ax += 1.8
        ay += 3.0

        self.marble_vx += ax * dt
        self.marble_vy += ay * dt

        friction = 0.3 if self.is_on_ice else 2.8
        self.marble_vx *= (1.0 - friction * dt)
        self.marble_vy *= (1.0 - friction * dt)

        self.marble_x += self.marble_vx * dt
        self.marble_y += self.marble_vy * dt

        self.score += int((abs(self.marble_vx) + abs(self.marble_vy)) * dt * 1.5)

        # Update Evil Marble
        self.evil_x += self.evil_vx * dt
        self.evil_y += self.evil_vy * dt
        if self.evil_x < 5.0:
            self.evil_x = 5.0
            self.evil_vx = abs(self.evil_vx)
        elif self.evil_x > 10.5:
            self.evil_x = 10.5
            self.evil_vx = -abs(self.evil_vx)

        if self.evil_y < 6.0:
            self.evil_y = 6.0
            self.evil_vy = abs(self.evil_vy)
        elif self.evil_y > 9.5:
            self.evil_y = 9.5
            self.evil_vy = -abs(self.evil_vy)

        dx = self.marble_x - self.evil_x
        dy = self.marble_y - self.evil_y
        dist = math.hypot(dx, dy)
        if 0.05 < dist < 1.2:
            self.marble_vx += (dx / dist) * 12.0
            self.marble_vy += (dy / dist) * 12.0

        # Acid hazard
        if abs(self.marble_x - self.acid_x) < 0.9 and abs(self.marble_y - self.acid_y) < 0.9:
            self.state = STATE_SHATTERED
            self.state_timer = 0.0
            self.time_remaining = max(0.0, self.time_remaining - 5.0)
            return

        # Track boundary check
        on_track = False
        if 0.5 <= self.marble_y <= 5.5 and 1.0 <= self.marble_x <= 8.0:
            on_track = True
        elif 5.0 <= self.marble_y <= 10.5 and 3.5 <= self.marble_x <= 11.5:
            on_track = True
        elif 10.0 <= self.marble_y <= 15.5 and 6.5 <= self.marble_x <= 15.0:
            on_track = True

        if not on_track:
            self.state = STATE_SHATTERED
            self.state_timer = 0.0
            self.time_remaining = max(0.0, self.time_remaining - 5.0)
            return

        # Goal check
        if abs(self.marble_x - self.goal_x) < 1.4 and abs(self.marble_y - self.goal_y) < 1.4:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000 + int(self.time_remaining * 100.0)
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Void abyss
        for i in range(0, 16 * 16 * 3, 3):
            fb[i] = 10; fb[i + 1] = 10; fb[i + 2] = 20

        # Course track
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if 1 <= y <= 5 and 1 <= x <= 7:
                    fb[idx] = 40; fb[idx + 1] = 80; fb[idx + 2] = 180
                    if (x + y) % 2 == 0:
                        fb[idx] += 20; fb[idx + 1] += 20; fb[idx + 2] += 20
                elif 6 <= y <= 10 and 4 <= x <= 11:
                    fb[idx] = 150; fb[idx + 1] = 220; fb[idx + 2] = 255
                elif 11 <= y <= 15 and 7 <= x <= 14:
                    fb[idx] = 180; fb[idx + 1] = 110; fb[idx + 2] = 40
                    if (x + y) % 2 == 0:
                        fb[idx] -= 30; fb[idx + 1] -= 20

        # Acid puddle
        ax = int(round(self.acid_x))
        ay = int(round(self.acid_y))
        if 0 <= ax < 16 and 0 <= ay < 16:
            idx = (ay * 16 + ax) * 3
            fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 50

        # Checkered finish
        for gx in (12, 13):
            idx = (14 * 16 + gx) * 3
            if gx % 2 == 0:
                fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255
            else:
                fb[idx] = 0;   fb[idx + 1] = 0;   fb[idx + 2] = 0

        # Evil marble
        ex = int(round(self.evil_x))
        ey = int(round(self.evil_y))
        if 0 <= ex < 16 and 0 <= ey < 16:
            idx = (ey * 16 + ex) * 3
            fb[idx] = 40; fb[idx + 1] = 10; fb[idx + 2] = 10

        # Player marble
        mx = int(round(self.marble_x))
        my = int(round(self.marble_y))
        if 0 <= mx < 16 and 0 <= my < 16:
            idx = (my * 16 + mx) * 3
            if self.state == STATE_SHATTERED:
                fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 0
            else:
                fb[idx] = 255; fb[idx + 1] = 30;  fb[idx + 2] = 60

        # HUD
        time_bars = int((self.time_remaining / 35.0) * 16.0)
        for t in range(min(time_bars, 16)):
            idx = t * 3
            if self.time_remaining < 10.0:
                fb[idx] = 255; fb[idx + 1] = 0;   fb[idx + 2] = 0
            else:
                fb[idx] = 0;   fb[idx + 1] = 255; fb[idx + 2] = 100

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "time_remaining": self.time_remaining,
            "marble_x": self.marble_x,
            "marble_y": self.marble_y,
            "marble_vx": self.marble_vx,
            "marble_vy": self.marble_vy,
            "is_on_ice": self.is_on_ice,
        }
