# -*- coding: utf-8 -*-
"""game_014_orbit_hop.py —— 目标 #014 轨道跃迁 (Orbit Hop)
三层同心环形轨道自动公转 + 单键相邻轨道跃迁切换 + 躲避逆向红雷收集金星
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TAP_SINGLE,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_SELECT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

CENTER_X = 7.5
CENTER_Y = 7.5
ORBIT_RADII = (2.8, 4.8, 6.8)
TWO_PI = 6.2831853
NUM_ORBITS = 3
MAX_STARS = 6
MAX_MINES = 4
TARGET_WAVES = 5


class OrbitStar:
    def __init__(self, orbit: int = 0, angle: float = 0.0, active: bool = False):
        self.orbit = orbit
        self.angle = angle
        self.active = active


class OrbitMine:
    def __init__(self, orbit: int = 0, angle: float = 0.0, speed: float = 0.0, active: bool = False):
        self.orbit = orbit
        self.angle = angle
        self.speed = speed
        self.active = active


class Game014OrbitHop(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.orbit_idx = 1
        self.hop_dir = 1
        self.player_angle = 0.0
        self.hop_flash_timer = 0.0
        self.stars: List[OrbitStar] = [OrbitStar() for _ in range(MAX_STARS)]
        self.mines: List[OrbitMine] = [OrbitMine() for _ in range(MAX_MINES)]
        self.stars_remaining = 0
        self.waves_cleared = 0
        self._seed = 0x14201601
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 14

    @property
    def name(self) -> str:
        return "轨道跃迁"

    @property
    def english_name(self) -> str:
        return "Orbit Hop"

    @property
    def release_year(self) -> int:
        return 2016

    @property
    def control_type(self) -> int:
        return CTRL_TAP_SINGLE

    @property
    def core_mechanic(self) -> str:
        return "同心多环公转与相邻轨道跃迁闪避"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _spawn_wave(self) -> None:
        self.stars_remaining = MAX_STARS
        self.stars = []
        for i in range(MAX_STARS):
            orb = i % NUM_ORBITS
            base_a = float(i // NUM_ORBITS) * 3.1415926 + float(self._next_rand() % 100) * 0.025 + 0.8
            while base_a >= TWO_PI:
                base_a -= TWO_PI
            self.stars.append(OrbitStar(orb, base_a, True))

        active_mines = 4 if self.waves_cleared >= 2 else 3
        self.mines = []
        for i in range(MAX_MINES):
            if i < active_mines:
                orb = i % NUM_ORBITS
                offset = 2.4 + float(self._next_rand() % 150) * 0.01
                ma = self.player_angle + offset
                while ma >= TWO_PI:
                    ma -= TWO_PI
                spd = 1.15 + float(i % 3) * 0.18 + float(self.waves_cleared) * 0.08
                self.mines.append(OrbitMine(orb, ma, spd, True))
            else:
                self.mines.append(OrbitMine(0, 0.0, 0.0, False))

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.orbit_idx = 1
        self.hop_dir = 1
        self.player_angle = 0.0
        self.hop_flash_timer = 0.0
        self.stars_remaining = 0
        self.waves_cleared = 0
        self._score = 0
        self._seed = 0x14201601
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._spawn_wave()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.orbit_idx = 1
            self.hop_dir = 1
            self.player_angle = 0.0
            self.hop_flash_timer = 0.0
            self.waves_cleared = 0
            self._score = 0
            self._seed = 0x14201601
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._spawn_wave()

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
            self.player_angle += 1.6 * dt
            if self.player_angle >= TWO_PI:
                self.player_angle -= TWO_PI
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

            tap_mask = KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_SELECT
            if keys_pressed & tap_mask:
                if self.orbit_idx == 0:
                    self.orbit_idx = 1
                    self.hop_dir = 1
                elif self.orbit_idx == 2:
                    self.orbit_idx = 1
                    self.hop_dir = -1
                else:
                    self.orbit_idx += self.hop_dir
                    if self.orbit_idx >= 2:
                        self.hop_dir = -1
                    if self.orbit_idx <= 0:
                        self.hop_dir = 1
                self.hop_flash_timer = 0.16

            if self.hop_flash_timer > 0.0:
                self.hop_flash_timer = max(0.0, self.hop_flash_timer - dt)

            player_omega = 1.95 + float(self.waves_cleared) * 0.12
            self.player_angle += player_omega * dt
            while self.player_angle >= TWO_PI:
                self.player_angle -= TWO_PI

            for m in self.mines:
                if not m.active:
                    continue
                m.angle -= m.speed * dt
                while m.angle < 0.0:
                    m.angle += TWO_PI

            r = ORBIT_RADII[self.orbit_idx]
            px = CENTER_X + math.cos(self.player_angle) * r
            py = CENTER_Y + math.sin(self.player_angle) * r

            for m in self.mines:
                if not m.active or m.orbit != self.orbit_idx:
                    continue
                mr = ORBIT_RADII[m.orbit]
                mx = CENTER_X + math.cos(m.angle) * mr
                my = CENTER_Y + math.sin(m.angle) * mr
                dx = px - mx
                dy = py - my
                if dx * dx + dy * dy < 0.90:
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return

            for s in self.stars:
                if not s.active or s.orbit != self.orbit_idx:
                    continue
                sr = ORBIT_RADII[s.orbit]
                sx = CENTER_X + math.cos(s.angle) * sr
                sy = CENTER_Y + math.sin(s.angle) * sr
                dx = px - sx
                dy = py - sy
                if dx * dx + dy * dy < 1.35:
                    s.active = False
                    self.stars_remaining -= 1
                    self._add_score(20)
                    if self.stars_remaining <= 0:
                        self._add_score(50)
                        self.waves_cleared += 1
                        if self.waves_cleared >= TARGET_WAVES:
                            self._state = STATE_VICTORY
                            self.state_timer = 0.0
                            return
                        self._spawn_wave()
                        break

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
                self._set_px(fb, x, y, 6, 8, 20)

        for orb in range(NUM_ORBITS):
            rad = ORBIT_RADII[orb]
            is_cur = orb == self.orbit_idx
            rr, rg, rb = (35, 65, 115) if is_cur else (18, 32, 62)
            for step in range(48):
                a = step * (TWO_PI / 48.0)
                ox = int(round(CENTER_X + math.cos(a) * rad))
                oy = int(round(CENTER_Y + math.sin(a) * rad))
                self._set_px(fb, ox, oy, rr, rg, rb)

        self._set_px(fb, 7, 7, 255, 180, 40)
        self._set_px(fb, 8, 7, 255, 140, 30)
        self._set_px(fb, 7, 8, 255, 140, 30)
        self._set_px(fb, 8, 8, 255, 180, 40)

        for s in self.stars:
            if not s.active:
                continue
            sr = ORBIT_RADII[s.orbit]
            sx = int(round(CENTER_X + math.cos(s.angle) * sr))
            sy = int(round(CENTER_Y + math.sin(s.angle) * sr))
            self._set_px(fb, sx, sy, 255, 220, 30)

        for m in self.mines:
            if not m.active:
                continue
            mr = ORBIT_RADII[m.orbit]
            mx = int(round(CENTER_X + math.cos(m.angle) * mr))
            my = int(round(CENTER_Y + math.sin(m.angle) * mr))
            self._set_px(fb, mx, my, 245, 40, 55)

        pr = ORBIT_RADII[self.orbit_idx]
        px = int(round(CENTER_X + math.cos(self.player_angle) * pr))
        py = int(round(CENTER_Y + math.sin(self.player_angle) * pr))
        if self._state == STATE_GAMEOVER:
            self._set_px(fb, px, py, 255, 80, 30)
        elif self.hop_flash_timer > 0.0:
            self._set_px(fb, px, py, 255, 255, 255)
        else:
            self._set_px(fb, px, py, 0, 245, 255)

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
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (self.waves_cleared * 100) // TARGET_WAVES),
        }
