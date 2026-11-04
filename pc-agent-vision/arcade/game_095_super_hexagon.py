# -*- coding: utf-8 -*-
"""game_095_super_hexagon.py —— 目标 #095 旋转避壁 (Super Hexagon)
脉冲核心与6扇区几何背景 + 向心收缩缺口多边形壁垒 + 双键顺逆时针轨道闪避
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TWO_BUTTON,
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

TWO_PI_095 = 2.0 * math.pi
SECTOR_SPAN_095 = TWO_PI_095 / 6.0
PLAYER_RADIUS_095 = 2.2


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class HexWall:
    def __init__(self, radius: float, solid_mask: int):
        self.radius = radius
        self.solid_mask = solid_mask
        self.passed = False


class Game095SuperHexagon(BaseCartridge):
    difficulty_supported = True
    NUM_WALLS = 3

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.rng_seed = 0x2012BEEF
        self.player_angle = 0.52
        self.survival_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.walls_passed = 0
        self.last_gap = 0
        self.walls: List[HexWall] = []
        self.reset()

    @staticmethod
    def angle_to_sector(angle: float) -> int:
        a = math.fmod(angle, TWO_PI_095)
        if a < 0.0:
            a += TWO_PI_095
        sec = int(a / SECTOR_SPAN_095)
        return max(0, min(5, sec))

    @property
    def game_id(self) -> int:
        return 95

    @property
    def name(self) -> str:
        return "旋转避壁"

    @property
    def english_name(self) -> str:
        return "Super Hexagon"

    @property
    def release_year(self) -> int:
        return 2012

    @property
    def control_type(self) -> int:
        return CTRL_TWO_BUTTON

    @property
    def core_mechanic(self) -> str:
        return "六扇区向心收缩多边形缺口壁垒与顺逆时针高速轨道闪避"

    def _next_rand(self) -> int:
        self.rng_seed = (self.rng_seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self.rng_seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _make_wall_mask(self) -> int:
        gap0 = (self.last_gap + 1 + (self._next_rand() % 5)) % 6
        self.last_gap = gap0
        mask = 0x3F & ~(1 << gap0)
        if (self._next_rand() & 1) == 0:
            gap1 = (gap0 + 3) % 6
            mask &= ~(1 << gap1)
        return mask

    def _setup_arena(self) -> None:
        self._score = 0
        self.rng_seed = 0x2012BEEF
        self.player_angle = 0.52
        self.survival_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.walls_passed = 0
        self.last_gap = 0
        self.walls = [
            HexWall(9.0 + float(i) * 5.5, self._make_wall_mask())
            for i in range(self.NUM_WALLS)
        ]

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._setup_arena()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_arena()
            self._state = STATE_PLAYING

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
            self.player_angle = (self.player_angle + 1.8 * dt) % TWO_PI_095
            if keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B | KEY_UP | KEY_DOWN):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B)):
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

            self.survival_timer += dt

            ctrl = keys_down | keys_pressed
            rot_speed = 7.4
            if ctrl & (KEY_LEFT | KEY_A):
                self.player_angle -= rot_speed * dt
            if ctrl & (KEY_RIGHT | KEY_B):
                self.player_angle += rot_speed * dt
            self.player_angle %= TWO_PI_095

            player_sec = self.angle_to_sector(self.player_angle)
            shrink_speed = min((4.,5.,5.5)[self.difficulty], (3.,3.8,4.3)[self.difficulty] + float(self.walls_passed) * 0.04)

            for i, w in enumerate(self.walls):
                w.radius -= shrink_speed * dt

                if 1.90 <= w.radius <= 2.50:
                    if (w.solid_mask & (1 << player_sec)) != 0:
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

                if not w.passed and w.radius < 1.90:
                    w.passed = True
                    self.walls_passed += 1
                    self._add_score(25)
                    if self.walls_passed >= 30 or self.survival_timer >= 45.0:
                        self._add_score(100)
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
                        return

                if w.radius < 1.3:
                    max_r = max(
                        [9.0] + [other.radius for j, other in enumerate(self.walls) if j != i]
                    )
                    w.radius = max_r + 5.5
                    w.solid_mask = self._make_wall_mask()
                    w.passed = False

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        pulse = 0.5 + 0.5 * math.sin(self.anim_timer * 6.0)
        hue_phase = int(self.anim_timer * 0.7) % 3

        for y in range(16):
            for x in range(16):
                dx = (float(x) + 0.5) - 7.5
                dy = (float(y) + 0.5) - 7.5
                ang = math.atan2(dy, dx)
                if ang < 0.0:
                    ang += TWO_PI_095
                sec = self.angle_to_sector(ang)

                bisector = (float(sec) + 0.5) * SECTOR_SPAN_095
                r_hex = (dx * math.cos(bisector) + dy * math.sin(bisector)) / 0.8660254

                even_sec = (sec & 1) == 0
                if hue_phase == 0:
                    br = int(42 + 16 * pulse) if even_sec else 22
                    bg = 8
                    bb = 32 if even_sec else 18
                elif hue_phase == 1:
                    br = 12
                    bg = 28 if even_sec else 14
                    bb = int(52 + 16 * pulse) if even_sec else 30
                else:
                    br = 38 if even_sec else 20
                    bg = int(24 + 12 * pulse) if even_sec else 12
                    bb = 8

                on_wall = any(
                    (w.solid_mask & (1 << sec)) != 0
                    and abs(r_hex - w.radius) <= 0.52
                    and w.radius <= 9.6
                    for w in self.walls
                )

                if on_wall:
                    if hue_phase == 0:
                        _set_px(fb, x, y, 255, 70, 95)
                    elif hue_phase == 1:
                        _set_px(fb, x, y, 60, 225, 255)
                    else:
                        _set_px(fb, x, y, 255, 185, 35)
                else:
                    _set_px(fb, x, y, br, bg, bb)

        cr = int(180.0 + 75.0 * pulse)
        cg = 245 if hue_phase == 1 else int(60.0 + 90.0 * pulse)
        cb = 60 if hue_phase == 2 else 255
        for cy in (7, 8):
            for cx in (7, 8):
                _set_px(fb, cx, cy, cr, cg, cb)

        px = int(math.floor(7.5 + PLAYER_RADIUS_095 * math.cos(self.player_angle)))
        py = int(math.floor(7.5 + PLAYER_RADIUS_095 * math.sin(self.player_angle)))
        if self._state == STATE_GAMEOVER:
            _set_px(fb, px, py, 255, 40, 40)
        else:
            _set_px(fb, px, py, 255, 255, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (self.walls_passed * 100) // 30),
        }
