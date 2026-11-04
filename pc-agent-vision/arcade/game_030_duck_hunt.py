# -*- coding: utf-8 -*-
"""game_030_duck_hunt.py —— 目标 #030 打鸭子 (Duck Hunt, 1984)
与 ESP32-S3 C++ Game030DuckHunt 1:1 对齐实现
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
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

DUCK_FLYING = 0
DUCK_STUNNED = 1
DUCK_FALLING = 2
DUCK_ESCAPING = 3


class Game030DuckHunt(BaseCartridge):
    DUCKS_PER_ROUND = 6
    ROUND_QUOTA = 4
    TOTAL_ROUNDS = 3

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.round = 1
        self.duck_index = 0
        self.round_hits = 0
        self.round_misses = 0
        self.shells = 3
        self.duck_results: List[int] = [0] * self.DUCKS_PER_ROUND
        self.duck_state = DUCK_FLYING
        self.duck_x = 7.5
        self.duck_y = 12.2
        self.duck_vx = 4.0
        self.duck_vy = -3.5
        self.escape_timer = 4.5
        self.phase_timer = 0.0
        self.weave_timer = 0.85
        self.reticle_x = 7.5
        self.reticle_y = 6.5
        self.muzzle_flash = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x030D0C84
        self.reset()

    @property
    def game_id(self) -> int:
        return 30

    @property
    def name(self) -> str:
        return "打鸭子"

    @property
    def english_name(self) -> str:
        return "Duck Hunt"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "草丛惊飞野鸭准星射击与3发弹药限时配额晋级"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _spawn_duck(self) -> None:
        self.shells = 3
        self.duck_state = DUCK_FLYING
        self.escape_timer = 4.5
        self.phase_timer = 0.0
        self.weave_timer = 0.85

        r1 = self._next_rand()
        r2 = self._next_rand()
        self.duck_x = 3.0 + float(r1 % 10)
        self.duck_y = 12.2

        base_spd = 4.2 + (self.round - 1) * 1.15
        dir_sign = 1.0 if ((r2 & 1) == 0) else -1.0
        if self.duck_x > 9.0:
            dir_sign = -1.0
        elif self.duck_x < 6.0:
            dir_sign = 1.0

        self.duck_vx = dir_sign * base_spd * 0.82
        self.duck_vy = -base_spd * 0.68

    def _start_round(self) -> None:
        self.duck_index = 0
        self.round_hits = 0
        self.round_misses = 0
        self.duck_results = [0] * self.DUCKS_PER_ROUND
        self._spawn_duck()

    def _setup_new_game(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.round = 1
        self.reticle_x = 7.5
        self.reticle_y = 6.5
        self.muzzle_flash = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x030D0C84
        self._start_round()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._setup_new_game(STATE_TITLE)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_new_game(STATE_PLAYING)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _finish_current_duck(self, was_hit: bool) -> None:
        if self.duck_index < self.DUCKS_PER_ROUND:
            self.duck_results[self.duck_index] = 1 if was_hit else 2
        if was_hit:
            self.round_hits += 1
        else:
            self.round_misses += 1
        self.duck_index += 1

        if self.duck_index >= self.DUCKS_PER_ROUND:
            if self.round_hits >= self.ROUND_QUOTA:
                self._add_score(500 if self.round_hits == self.DUCKS_PER_ROUND else 200)
                if self.round >= self.TOTAL_ROUNDS:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                else:
                    self.round += 1
                    self._start_round()
            else:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
        else:
            self._spawn_duck()

    def _pull_trigger(self) -> bool:
        if self.shells <= 0 or self.duck_state != DUCK_FLYING:
            return False

        self.shells -= 1
        self.muzzle_flash = 0.08

        if abs(self.reticle_x - self.duck_x) <= 1.4 and abs(self.reticle_y - self.duck_y) <= 1.4:
            self.duck_state = DUCK_STUNNED
            self.phase_timer = 0.32
            self._add_score(100)
            return True

        if self.shells == 0:
            self.duck_state = DUCK_ESCAPING
            self.duck_vx *= 0.3
            self.duck_vy = -10.5
        return False

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt < 0.0:
            dt = 0.0
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.duck_x += self.duck_vx * dt * 0.6
            self.duck_y += self.duck_vy * dt * 0.6
            if self.duck_x < 1.5 or self.duck_x > 13.5:
                self.duck_vx = -self.duck_vx
            if self.duck_y < 2.0 or self.duck_y > 10.5:
                self.duck_vy = -self.duck_vy
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
                self.start()
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            if self.muzzle_flash > 0.0:
                self.muzzle_flash -= dt

            aim_speed = 13.5
            if keys_down & KEY_LEFT:
                self.reticle_x -= aim_speed * dt
            if keys_down & KEY_RIGHT:
                self.reticle_x += aim_speed * dt
            if keys_down & KEY_UP:
                self.reticle_y -= aim_speed * dt
            if keys_down & KEY_DOWN:
                self.reticle_y += aim_speed * dt

            self.reticle_x = max(0.0, min(15.0, self.reticle_x))
            self.reticle_y = max(0.0, min(12.0, self.reticle_y))

            if keys_pressed & (KEY_A | KEY_B):
                self._pull_trigger()

            if self.duck_state == DUCK_FLYING:
                self.escape_timer -= dt
                if self.escape_timer <= 0.0:
                    self.duck_state = DUCK_ESCAPING
                    self.duck_vx *= 0.3
                    self.duck_vy = -10.5
                    return

                self.weave_timer -= dt
                if self.weave_timer <= 0.0:
                    self.weave_timer = 0.75
                    r = self._next_rand()
                    if (r & 3) == 0:
                        self.duck_vx = -self.duck_vx
                    if (r & 4) != 0:
                        self.duck_vy = -self.duck_vy

                self.duck_x += self.duck_vx * dt
                self.duck_y += self.duck_vy * dt

                if self.duck_x <= 1.0:
                    self.duck_x = 1.0
                    self.duck_vx = abs(self.duck_vx)
                elif self.duck_x >= 14.0:
                    self.duck_x = 14.0
                    self.duck_vx = -abs(self.duck_vx)

                if self.duck_y <= 1.2:
                    self.duck_y = 1.2
                    self.duck_vy = abs(self.duck_vy)
                elif self.duck_y >= 11.2:
                    self.duck_y = 11.2
                    self.duck_vy = -abs(self.duck_vy)
            elif self.duck_state == DUCK_STUNNED:
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    self.duck_state = DUCK_FALLING
            elif self.duck_state == DUCK_FALLING:
                self.duck_y += 11.5 * dt
                if self.duck_y >= 13.2:
                    self._finish_current_duck(True)
            elif self.duck_state == DUCK_ESCAPING:
                self.duck_x += self.duck_vx * dt
                self.duck_y += self.duck_vy * dt
                if self.duck_y < -0.6:
                    self._finish_current_duck(False)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)

        def set_px(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        escaping_sky = (self.duck_state == DUCK_ESCAPING)
        for y in range(13):
            for x in range(16):
                if self.muzzle_flash > 0.0:
                    set_px(x, y, 220, 235, 255)
                elif escaping_sky:
                    set_px(x, y, 235, 130, 120)
                else:
                    set_px(x, y, 64, 168, 245)

        for x in range(16):
            blade = ((x * 3) % 2 == 0)
            set_px(x, 13, 72 if blade else 46, 215 if blade else 185, 65)
            set_px(x, 14, 38, 155, 52)
            set_px(x, 15, 45, 32, 20)

        dx = int(round(self.duck_x))
        dy = int(round(self.duck_y))
        if dy <= 13:
            if self.duck_state == DUCK_STUNNED:
                set_px(dx, dy, 255, 255, 255)
                set_px(dx - 1, dy, 231, 76, 60)
                set_px(dx + 1, dy, 241, 196, 15)
            elif self.duck_state == DUCK_FALLING:
                spin = ((int(self.anim_timer * 16.0) & 1) == 0)
                set_px(dx, dy, 165, 95, 45)
                set_px(dx, dy - 1, 39 if spin else 241, 190 if spin else 196, 96 if spin else 15)
            else:
                head_dir = 1 if self.duck_vx >= 0.0 else -1
                wing_up = ((int(self.anim_timer * 10.0) & 1) == 0)
                set_px(dx, dy, 165, 95, 45)
                set_px(dx + head_dir, dy, 25, 195, 90)
                if wing_up:
                    set_px(dx, dy - 1, 245, 245, 250)
                else:
                    set_px(dx - head_dir, dy + 1, 225, 180, 70)

        rx = int(round(self.reticle_x))
        ry = int(round(self.reticle_y))
        cg = 255 if self.muzzle_flash > 0.0 else 50
        cb = 255 if self.muzzle_flash > 0.0 else 50
        set_px(rx - 1, ry, 255, cg, cb)
        set_px(rx + 1, ry, 255, cg, cb)
        set_px(rx, ry - 1, 255, cg, cb)
        set_px(rx, ry + 1, 255, cg, cb)

        for s in range(min(3, self.shells)):
            set_px(s, 15, 255, 195, 20)
        for i in range(self.DUCKS_PER_ROUND):
            if self.duck_results[i] == 1:
                set_px(5 + i, 15, 46, 230, 90)
            elif self.duck_results[i] == 2:
                set_px(5 + i, 15, 235, 60, 50)
            else:
                set_px(5 + i, 15, 180, 180, 190)
        for r in range(min(3, self.round)):
            set_px(15 - r, 15, 0, 225, 255)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                set_px(x, 0, 231, 76, 60)
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_px(6, y, 250, 250, 250)
                set_px(9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        margin = (self.DUCKS_PER_ROUND - self.ROUND_QUOTA + 1) - self.round_misses
        lives = 0 if self._state == STATE_GAMEOVER else max(1, margin)
        progress = 100 if self._state == STATE_VICTORY else (
            ((self.round - 1) * self.DUCKS_PER_ROUND + self.duck_index) * 100
            // (self.TOTAL_ROUNDS * self.DUCKS_PER_ROUND)
        )
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": lives,
            "state": self._state,
            "progress": progress,
        }
