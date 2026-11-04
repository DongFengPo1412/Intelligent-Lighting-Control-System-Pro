# -*- coding: utf-8 -*-
"""game_027_asteroids.py —— 目标 #027 小行星 (Asteroids, 1979)
与 ESP32-S3 C++ Game027Asteroids 1:1 对齐实现
"""

import math
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

DIR_DX = (
    0.0, 0.70710678, 1.0, 0.70710678,
    0.0, -0.70710678, -1.0, -0.70710678,
)
DIR_DY = (
    -1.0, -0.70710678, 0.0, 0.70710678,
    1.0, 0.70710678, 0.0, -0.70710678,
)


def _wrap16(v: float) -> float:
    while v < 0.0:
        v += 16.0
    while v >= 16.0:
        v -= 16.0
    return v


def _torus_dist(x1: float, y1: float, x2: float, y2: float) -> float:
    dx = abs(x1 - x2)
    if dx > 8.0:
        dx = 16.0 - dx
    dy = abs(y1 - y2)
    if dy > 8.0:
        dy = 16.0 - dy
    return math.hypot(dx, dy)


class AsteroidRock027:
    def __init__(self, x: float = 0.0, y: float = 0.0, vx: float = 0.0, vy: float = 0.0, size: int = 2, active: bool = False):
        self.active = active
        self.size = size  # 2 = 2x2 large, 1 = 1x1 small
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


class SpaceBullet027:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.life = 0.0


class Game027Asteroids(BaseCartridge):
    MAX_ASTEROIDS = 16
    MAX_BULLETS = 4

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.lives = 3
        self.wave = 1
        self.ship_x = 8.0
        self.ship_y = 8.0
        self.ship_vx = 0.0
        self.ship_vy = 0.0
        self.ship_dir = 0
        self.thrusting = False
        self.rot_timer = 0.0
        self.fire_cooldown = 0.0
        self.invuln_timer = 0.0
        self.asteroids: List[AsteroidRock027] = [AsteroidRock027() for _ in range(self.MAX_ASTEROIDS)]
        self.bullets: List[SpaceBullet027] = [SpaceBullet027() for _ in range(self.MAX_BULLETS)]
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x027A57E1
        self.reset()

    @property
    def game_id(self) -> int:
        return 27

    @property
    def name(self) -> str:
        return "小行星"

    @property
    def english_name(self) -> str:
        return "Asteroids"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "8方向旋转牛顿惯性推进与大陨石分裂射击"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _spawn_asteroid(self, x: float, y: float, vx: float, vy: float, size: int) -> None:
        for a in self.asteroids:
            if not a.active:
                a.active = True
                a.size = size
                a.x = _wrap16(x)
                a.y = _wrap16(y)
                a.vx = vx
                a.vy = vy
                return

    def _init_wave(self) -> None:
        for a in self.asteroids:
            a.active = False
        for b in self.bullets:
            b.active = False

        self.ship_x = 8.0
        self.ship_y = 8.0
        self.ship_vx = 0.0
        self.ship_vy = 0.0
        self.ship_dir = 0
        self.thrusting = False
        self.invuln_timer = 1.0

        spawn_pos = (
            (2.0, 2.0),
            (13.0, 2.0),
            (2.0, 13.0),
            (13.0, 13.0),
            (8.0, 1.5),
        )
        count = min(5, 2 + self.wave)
        base_speed = 1.9 + (self.wave - 1) * 0.45
        for i in range(count):
            r = self._next_rand()
            ang = i * 1.35 + (r % 100) * 0.01 + 0.35
            self._spawn_asteroid(
                spawn_pos[i][0],
                spawn_pos[i][1],
                math.cos(ang) * base_speed,
                math.sin(ang) * base_speed,
                2,
            )

    def _setup_new_game(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.lives = 3
        self.wave = 1
        self.rot_timer = 0.0
        self.fire_cooldown = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x027A57E1
        self._init_wave()

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

    def _split_asteroid(self, idx: int) -> None:
        if idx < 0 or idx >= self.MAX_ASTEROIDS or not self.asteroids[idx].active:
            return
        a = self.asteroids[idx]
        old_size = a.size
        ox, oy, ovx, ovy = a.x, a.y, a.vx, a.vy
        a.active = False

        if old_size >= 2:
            self._add_score(50)
            spd = max(2.6, math.hypot(ovx, ovy) * 1.35)
            ang = math.atan2(ovy, ovx)
            self._spawn_asteroid(ox, oy, math.cos(ang + 0.85) * spd, math.sin(ang + 0.85) * spd, 1)
            self._spawn_asteroid(ox, oy, math.cos(ang - 0.85) * spd, math.sin(ang - 0.85) * spd, 1)
        else:
            self._add_score(100)

    def _fire_bullet(self) -> None:
        for b in self.bullets:
            if not b.active:
                dx = DIR_DX[self.ship_dir]
                dy = DIR_DY[self.ship_dir]
                b.active = True
                b.x = _wrap16(self.ship_x + dx * 1.0)
                b.y = _wrap16(self.ship_y + dy * 1.0)
                b.vx = self.ship_vx * 0.35 + dx * 18.0
                b.vy = self.ship_vy * 0.35 + dy * 18.0
                b.life = 0.72
                self.fire_cooldown = 0.16
                return

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
            for a in self.asteroids:
                if a.active:
                    a.x = _wrap16(a.x + a.vx * dt * 0.6)
                    a.y = _wrap16(a.y + a.vy * dt * 0.6)
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

            if self.rot_timer > 0.0:
                self.rot_timer -= dt
            if self.fire_cooldown > 0.0:
                self.fire_cooldown -= dt
            if self.invuln_timer > 0.0:
                self.invuln_timer -= dt

            if keys_pressed & KEY_LEFT:
                self.ship_dir = (self.ship_dir + 7) & 7
                self.rot_timer = 0.14
            elif keys_pressed & KEY_RIGHT:
                self.ship_dir = (self.ship_dir + 1) & 7
                self.rot_timer = 0.14
            elif (keys_down & KEY_LEFT) and self.rot_timer <= 0.0:
                self.ship_dir = (self.ship_dir + 7) & 7
                self.rot_timer = 0.14
            elif (keys_down & KEY_RIGHT) and self.rot_timer <= 0.0:
                self.ship_dir = (self.ship_dir + 1) & 7
                self.rot_timer = 0.14

            self.thrusting = bool(keys_down & (KEY_A | KEY_UP))
            if self.thrusting:
                accel = 14.0
                self.ship_vx += DIR_DX[self.ship_dir] * accel * dt
                self.ship_vy += DIR_DY[self.ship_dir] * accel * dt
                spd = math.hypot(self.ship_vx, self.ship_vy)
                if spd > 9.0:
                    self.ship_vx = (self.ship_vx / spd) * 9.0
                    self.ship_vy = (self.ship_vy / spd) * 9.0

            self.ship_vx *= (1.0 - 0.35 * dt)
            self.ship_vy *= (1.0 - 0.35 * dt)
            self.ship_x = _wrap16(self.ship_x + self.ship_vx * dt)
            self.ship_y = _wrap16(self.ship_y + self.ship_vy * dt)

            want_shoot = (
                bool(keys_pressed & KEY_B)
                or (bool(keys_down & KEY_B) and self.fire_cooldown <= 0.0)
                or (bool(keys_down & KEY_UP) and bool(keys_pressed & KEY_A))
            )
            if want_shoot and self.fire_cooldown <= 0.0:
                self._fire_bullet()

            for b in self.bullets:
                if not b.active:
                    continue
                b.life -= dt
                if b.life <= 0.0:
                    b.active = False
                    continue
                b.x = _wrap16(b.x + b.vx * dt)
                b.y = _wrap16(b.y + b.vy * dt)

            for a in self.asteroids:
                if a.active:
                    a.x = _wrap16(a.x + a.vx * dt)
                    a.y = _wrap16(a.y + a.vy * dt)

            for b in self.bullets:
                if not b.active:
                    continue
                for idx, a in enumerate(self.asteroids):
                    if not a.active:
                        continue
                    hit_r = 1.35 if a.size >= 2 else 0.85
                    cx = _wrap16(a.x + 0.5) if a.size >= 2 else a.x
                    cy = _wrap16(a.y + 0.5) if a.size >= 2 else a.y
                    if _torus_dist(b.x, b.y, cx, cy) <= hit_r:
                        b.active = False
                        self._split_asteroid(idx)
                        break

            if self.invuln_timer <= 0.0:
                for idx, a in enumerate(self.asteroids):
                    if not a.active:
                        continue
                    hit_r = 1.25 if a.size >= 2 else 0.75
                    cx = _wrap16(a.x + 0.5) if a.size >= 2 else a.x
                    cy = _wrap16(a.y + 0.5) if a.size >= 2 else a.y
                    if _torus_dist(self.ship_x, self.ship_y, cx, cy) <= hit_r:
                        self._split_asteroid(idx)
                        if self.lives > 1:
                            self.lives -= 1
                            self.ship_x = 8.0
                            self.ship_y = 8.0
                            self.ship_vx = 0.0
                            self.ship_vy = 0.0
                            self.invuln_timer = 1.5
                        else:
                            self.lives = 0
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        break

            if not any(a.active for a in self.asteroids):
                self._add_score(200)
                if self.wave >= 3:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                else:
                    self.wave += 1
                    self._init_wave()

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

        for y in range(16):
            for x in range(16):
                set_px(x, y, 4, 6, 14)
        set_px(3, 5, 25, 30, 55)
        set_px(12, 3, 30, 35, 60)
        set_px(5, 12, 25, 30, 55)
        set_px(11, 10, 30, 35, 60)

        for a in self.asteroids:
            if not a.active:
                continue
            if a.size >= 2:
                ax = int(math.floor(a.x)) & 15
                ay = int(math.floor(a.y)) & 15
                set_px(ax, ay, 185, 175, 160)
                set_px((ax + 1) & 15, ay, 145, 135, 125)
                set_px(ax, (ay + 1) & 15, 130, 120, 110)
                set_px((ax + 1) & 15, (ay + 1) & 15, 165, 155, 140)
            else:
                ax = int(round(a.x)) & 15
                ay = int(round(a.y)) & 15
                set_px(ax, ay, 225, 210, 180)

        for b in self.bullets:
            if b.active:
                bx = int(round(b.x)) & 15
                by = int(round(b.y)) & 15
                set_px(bx, by, 255, 240, 80)

        blink_hide = (self.invuln_timer > 0.0) and ((int(self.anim_timer * 12.0) & 1) == 1)
        if not blink_hide and self._state != STATE_GAMEOVER:
            sx = int(round(self.ship_x)) & 15
            sy = int(round(self.ship_y)) & 15
            nx = int(round(self.ship_x + DIR_DX[self.ship_dir])) & 15
            ny = int(round(self.ship_y + DIR_DY[self.ship_dir])) & 15
            if self.thrusting:
                tx = int(round(self.ship_x - DIR_DX[self.ship_dir])) & 15
                ty = int(round(self.ship_y - DIR_DY[self.ship_dir])) & 15
                set_px(tx, ty, 255, 120, 20)
            set_px(sx, sy, 52, 172, 255)
            set_px(nx, ny, 255, 255, 255)

        for i in range(min(3, self.lives)):
            set_px(i * 2, 0, 0, 230, 255)
        for w in range(min(3, self.wave)):
            set_px(15 - w * 2, 0, 255, 215, 0)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                set_px(x, 0, 231, 76, 60)
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_px(6, y, 250, 250, 250)
                set_px(9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": 100 if self._state == STATE_VICTORY else (self.wave - 1) * 33,
        }
