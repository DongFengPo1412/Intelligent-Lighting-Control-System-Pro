"""game_021_breakout.py —— 目标 #021 经典打砖块 (Breakout 1976)
底部挡板 + 多彩耐久砖块阵列 + 3条命清屏决胜
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TWO_BUTTON,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen


class Brick:
    def __init__(self, hp: int, r: int, g: int, b: int):
        self.hp = hp
        self.r = r
        self.g = g
        self.b = b


class Game021Breakout(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.paddle_x = 6.0
        self.paddle_w = 4.0
        self.ball_x = 8.0
        self.ball_y = 13.0
        self.ball_vx = 6.5
        self.ball_vy = -8.5
        self.ball_stuck = True
        self.bricks: List[List[Brick]] = []
        self.remaining_bricks = 32
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 21

    @property
    def name(self) -> str:
        return "经典打砖块"

    @property
    def english_name(self) -> str:
        return "Breakout 1976"

    @property
    def release_year(self) -> int:
        return 1976

    @property
    def control_type(self) -> int:
        return CTRL_TWO_BUTTON

    @property
    def core_mechanic(self) -> str:
        return "底部挡板反弹与多彩砖块粉碎"

    def init(self) -> None:
        self.reset()

    def _reset_ball_and_paddle(self):
        self.paddle_x = 6.0
        self.paddle_w = 4.0
        self.ball_stuck = True
        self.ball_x = self.paddle_x + self.paddle_w * 0.5
        self.ball_y = 13.0
        self.ball_vx = 6.5
        self.ball_vy = -8.5

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.remaining_bricks = 32

        colors = [
            (231, 76, 60, 2),   # 红 (hp=2)
            (230, 126, 34, 1),  # 橙 (hp=1)
            (46, 204, 113, 1),  # 绿 (hp=1)
            (241, 196, 15, 1),  # 黄 (hp=1)
        ]
        self.bricks = []
        for r in range(4):
            cr, cg, cb, hp = colors[r]
            row = [Brick(hp, cr, cg, cb) for _ in range(8)]
            self.bricks.append(row)

        self._reset_ball_and_paddle()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.remaining_bricks = 32
            colors = [
                (231, 76, 60, 2),
                (230, 126, 34, 1),
                (46, 204, 113, 1),
                (241, 196, 15, 1),
            ]
            self.bricks = []
            for r in range(4):
                cr, cg, cb, hp = colors[r]
                row = [Brick(hp, cr, cg, cb) for _ in range(8)]
                self.bricks.append(row)
            self._reset_ball_and_paddle()

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
            self.paddle_x = max(0.0, min(16.0 - self.paddle_w, self.ball_x - self.paddle_w * 0.5))
            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt
            if self.ball_x <= 0.0 or self.ball_x >= 15.0:
                self.ball_vx = -self.ball_vx
            if self.ball_y <= 0.0 or self.ball_y >= 13.0:
                self.ball_vy = -self.ball_vy

            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
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
                return

            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt

            if self.ball_x <= 0.0:
                self.ball_x = 0.0
                self.ball_vx = abs(self.ball_vx)
            elif self.ball_x >= 15.0:
                self.ball_x = 15.0
                self.ball_vx = -abs(self.ball_vx)

            if self.ball_y <= 0.0:
                self.ball_y = 0.0
                self.ball_vy = abs(self.ball_vy)

            if self.ball_vy > 0.0 and 13.2 <= self.ball_y <= 14.8:
                if (self.paddle_x - 0.5) <= self.ball_x <= (self.paddle_x + self.paddle_w + 0.5):
                    self.ball_y = 13.1
                    self.ball_vy = -abs(self.ball_vy)
                    hit_offset = (self.ball_x - (self.paddle_x + self.paddle_w * 0.5)) / (self.paddle_w * 0.5)
                    self.ball_vx = hit_offset * 9.0

            brick_y_start = 2
            check_r = int(round(self.ball_y)) - brick_y_start
            check_c = int(round(self.ball_x)) // 2

            if 0 <= check_r < 4 and 0 <= check_c < 8:
                b = self.bricks[check_r][check_c]
                if b.hp > 0:
                    b.hp -= 1
                    self.ball_vy = -self.ball_vy
                    if b.hp == 0:
                        self.remaining_bricks -= 1
                        self._score += 10
                        if self._score > self._high_score:
                            self._high_score = self._score
                        if self.remaining_bricks <= 0:
                            self._state = STATE_VICTORY
                            self.state_timer = 0.0
                            return
                    else:
                        b.r, b.g, b.b = 255, 255, 255

            if self.ball_y > 15.5:
                if self.lives > 1:
                    self.lives -= 1
                    self._reset_ball_and_paddle()
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for r in range(4):
            y = 2 + r
            for c in range(8):
                b = self.bricks[r][c]
                if b.hp > 0:
                    for x in (c * 2, c * 2 + 1):
                        idx = (y * 16 + x) * 3
                        fb[idx : idx + 3] = bytes([b.r, b.g, b.b])

        px = int(round(self.paddle_x))
        pw = int(self.paddle_w)
        for x in range(px, min(16, px + pw)):
            if x >= 0:
                idx = (14 * 16 + x) * 3
                fb[idx : idx + 3] = bytes([52, 152, 219])

        bx = int(round(self.ball_x))
        by = int(round(self.ball_y))
        if 0 <= bx < 16 and 0 <= by < 16:
            idx = (by * 16 + bx) * 3
            fb[idx : idx + 3] = bytes([255, 255, 255])

        for i in range(min(3, self.lives)):
            idx = (i * 2) * 3
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
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (32 - self.remaining_bricks) * 100 // 32),
        }
