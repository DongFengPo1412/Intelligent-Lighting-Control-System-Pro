"""game_009_flappy_bird.py —— 目标 #009 飞翔小鸟 16 (Flappy Bird 16)
单键脉冲拍翅 + 持续重力 + 管道空隙穿越
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
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)
from .arcade_result_screen import ArcadeResultScreen


class PipeObstacle:
    def __init__(self, x: float, gap_y: int, gap_height: int):
        self.x = x
        self.gap_y = gap_y
        self.gap_height = gap_height
        self.scored = False


class Game009FlappyBird(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.bird_x = 3.0
        self.bird_y = 6.0
        self.bird_vy = -6.0
        self.flap_anim = False
        self.flap_timer = 0.0
        self.pipes: List[PipeObstacle] = []
        self.ground_scroll = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x87654321
        self.reset()

    @property
    def game_id(self) -> int:
        return 9

    @property
    def name(self) -> str:
        return "飞翔小鸟"

    @property
    def english_name(self) -> str:
        return "Flappy Bird 16"

    @property
    def release_year(self) -> int:
        return 2013

    @property
    def control_type(self) -> int:
        return CTRL_TAP_SINGLE

    @property
    def core_mechanic(self) -> str:
        return "单键脉冲拍翅与重力管道穿行"

    def init(self) -> None:
        self.reset()

    def _rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _spawn_pipe(self, start_x: float) -> PipeObstacle:
        gap_h = 4 if self._score > 10 else 5
        max_top = 13 - gap_h
        r = self._rand()
        gap_y = 2 + (r % (max_top - 2 + 1))
        return PipeObstacle(start_x, gap_y, gap_h)

    def reset(self):
        self._state = STATE_TITLE
        self.bird_x = 3.0
        self.bird_y = 6.0
        self.bird_vy = 0.0
        self.flap_anim = False
        self.flap_timer = 0.0
        self._score = 0
        self.ground_scroll = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.pipes = [self._spawn_pipe(16.0), self._spawn_pipe(26.0)]

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER):
            self._state = STATE_PLAYING
            self.bird_x = 3.0
            self.bird_y = 6.0
            self.bird_vy = 0.0
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.pipes = [self._spawn_pipe(16.0), self._spawn_pipe(26.0)]

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
            self.bird_y = 6.5 + math.sin(self.state_timer * 4.0) * 1.5
            self.ground_scroll = (self.ground_scroll + 4.0 * dt) % 16.0
            if keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_DOWN | KEY_B):
                self.start()
            return

        if self._state == STATE_GAMEOVER:
            if self.bird_y < 13.0:
                self.bird_vy += 35.0 * dt
                self.bird_y = min(13.0, self.bird_y + self.bird_vy * dt)
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_B)):
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
            self.ground_scroll = (self.ground_scroll + pipe_speed * dt) % 16.0

            for i, p in enumerate(self.pipes):
                p.x -= pipe_speed * dt
                if not p.scored and p.x + 2.0 < self.bird_x:
                    p.scored = True
                    self._score += 1
                    if self._score > self._high_score:
                        self._high_score = self._score

                if p.x < -3.0:
                    other = 1 if i == 0 else 0
                    new_x = max(16.0, self.pipes[other].x + 10.5)
                    self.pipes[i] = self._spawn_pipe(new_x)

            bx1, bx2 = self.bird_x, self.bird_x + 1.8
            by1, by2 = self.bird_y, self.bird_y + 1.8

            if by1 < 0.0 or by2 >= 13.5:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                if self._score > self._high_score:
                    self._high_score = self._score
                return

            for p in self.pipes:
                px1, px2 = p.x, p.x + 2.0
                if bx2 >= px1 and bx1 <= px2:
                    gap_top = float(p.gap_y)
                    gap_bottom = gap_top + float(p.gap_height)
                    if by1 < gap_top or by2 > gap_bottom:
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        if self._score > self._high_score:
                            self._high_score = self._score
                        return

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state == STATE_GAMEOVER and self.state_timer > 0.8:
            return ArcadeResultScreen.render(False, self._score, self._high_score, self.anim_timer)

        for y in range(14):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 52
                fb[idx + 1] = min(255, 152 + y * 3)
                fb[idx + 2] = 219

        for x in range(16):
            idx14 = (14 * 16 + x) * 3
            idx15 = (15 * 16 + x) * 3
            fb[idx14 : idx14 + 3] = bytes([46, 204, 113])
            fb[idx15 : idx15 + 3] = bytes([211, 84, 0])

        for p in self.pipes:
            px = int(round(p.x))
            gap_y = p.gap_y
            gap_h = p.gap_height

            for dx in range(2):
                x = px + dx
                if 0 <= x < 16:
                    for y in range(gap_y):
                        idx = (y * 16 + x) * 3
                        if y == gap_y - 1:
                            fb[idx : idx + 3] = bytes([39, 174, 96])
                        else:
                            fb[idx : idx + 3] = bytes([46, 204, 113]) if dx == 0 else bytes([34, 153, 84])

                    for y in range(gap_y + gap_h, 14):
                        idx = (y * 16 + x) * 3
                        if y == gap_y + gap_h:
                            fb[idx : idx + 3] = bytes([39, 174, 96])
                        else:
                            fb[idx : idx + 3] = bytes([46, 204, 113]) if dx == 0 else bytes([34, 153, 84])

        bx = int(round(self.bird_x))
        by = int(round(self.bird_y))
        for dy in range(2):
            for dx in range(2):
                x, y = bx + dx, by + dy
                if 0 <= x < 16 and 0 <= y < 16:
                    idx = (y * 16 + x) * 3
                    if dy == 0:
                        fb[idx : idx + 3] = bytes([241, 196, 15]) if dx == 0 else bytes([255, 255, 255])
                    else:
                        if dx == 0:
                            fb[idx : idx + 3] = bytes([243, 156, 18]) if self.flap_anim else bytes([230, 126, 34])
                        else:
                            fb[idx : idx + 3] = bytes([231, 76, 60])

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                idx = x * 3
                fb[idx : idx + 3] = bytes([231, 76, 60])
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
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
            "progress": min(100, self._score * 5),
        }
