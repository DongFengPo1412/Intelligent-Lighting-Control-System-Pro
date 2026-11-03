# -*- coding: utf-8 -*-
"""
Game #129: 星际要塞 (Star Castle 1980 / Cinematronics)
街机历史上最具传奇色彩的多层同心回转护盾穿透射击游戏：
三层对向旋转同心护盾环、环隙对齐致命主炮直射、精准穿透射击爆破核心、拦截追踪电火花地雷。
"""

from typing import List, Dict, Any, Optional
import math
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

STATE_PLAYING = 0
STATE_CASTLE_EXPLODING = 1
STATE_PLAYER_EXPLODING = 2
STATE_GAME_OVER = 3

PI = 3.14159265
TWO_PI = 6.2831853
CENTER_X = 7.5
CENTER_Y = 7.5
RING_RADII = [5.4, 3.8, 2.4]
NUM_RINGS = 3
SEGMENTS_PER_RING = 8
MAX_BULLETS = 4
MAX_SPARKS = 3


class Game129StarCastle(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7.5
        self.py = 14.2
        self.pvx = 0.0
        self.pvy = 0.0
        self.p_angle = -PI * 0.5

        self.turret_angle = 0.0
        self.turret_fire_timer = 1.5
        self.blast = {
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "active": False,
        }

        self.shield_alive = [[True] * SEGMENTS_PER_RING for _ in range(NUM_RINGS)]
        self.ring_angles = [0.0, 0.2, 0.5]
        self.ring_speeds = [0.8, -1.1, 1.4]

        self.bullets: List[Dict[str, Any]] = []
        self.sparks: List[Dict[str, Any]] = []
        self.spark_spawn_timer = 1.2

        self.reset()

    @property
    def game_id(self) -> int:
        return 129

    @property
    def name(self) -> str:
        return "星际要塞"

    @property
    def english_name(self) -> str:
        return "Star Castle"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "三层对向旋转同心护盾穿透、环隙视线致命要塞主炮直射、精准核心爆破与追踪火花"

    def get_name(self) -> str:
        return "Star Castle (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_castle()

    def _init_castle(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0

        self.px = 7.5
        self.py = 14.2
        self.pvx = 0.0
        self.pvy = 0.0
        self.p_angle = -PI * 0.5

        self.turret_angle = 0.0
        self.turret_fire_timer = 1.5
        self.blast = {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False}

        self.ring_angles = [0.0, 0.2, 0.5]
        self.ring_speeds = [
            0.8 + self.level * 0.1,
            -(1.1 + self.level * 0.15),
            1.4 + self.level * 0.2,
        ]

        self.shield_alive = [[True] * SEGMENTS_PER_RING for _ in range(NUM_RINGS)]

        self.bullets = []
        for _ in range(MAX_BULLETS):
            self.bullets.append({"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False})

        self.sparks = []
        for _ in range(MAX_SPARKS):
            self.sparks.append({"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False})

        self.spark_spawn_timer = 1.2

    def has_direct_line_of_sight(self, angle: float) -> bool:
        while angle < 0.0:
            angle += TWO_PI
        while angle >= TWO_PI:
            angle -= TWO_PI

        for r in range(NUM_RINGS):
            rel_ang = angle - self.ring_angles[r]
            while rel_ang < 0.0:
                rel_ang += TWO_PI
            while rel_ang >= TWO_PI:
                rel_ang -= TWO_PI

            seg = int(rel_ang / (TWO_PI / 8.0)) % 8
            if self.shield_alive[r][seg]:
                return False
        return True

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PLAYER_EXPLODING:
            if self.state_timer > 1.3:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 14.2
                    self.pvx = 0.0
                    self.pvy = 0.0
                    self.p_angle = -PI * 0.5
            return

        if self.state == STATE_CASTLE_EXPLODING:
            if self.state_timer > 1.8:
                self.level += 1
                self.score += 1000
                self._init_castle()
            return

        # Button A: Fire Torpedo
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            for b in self.bullets:
                if not b["active"]:
                    b["active"] = True
                    b["x"] = self.px
                    b["y"] = self.py
                    b["vx"] = math.cos(self.p_angle) * 16.0 + self.pvx * 0.5
                    b["vy"] = math.sin(self.p_angle) * 16.0 + self.pvy * 0.5
                    break

        # Button B: Retro brake
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.pvx *= 0.2
            self.pvy *= 0.2

        self._update_ship(dt, buttons)
        self._update_shields(dt)
        self._update_bullets(dt)
        self._update_sparks(dt)
        self._update_boss_turret(dt)
        self._check_collisions()

    def _update_ship(self, dt: float, buttons: int) -> None:
        turn_speed = 4.5
        if buttons & KEY_LEFT:
            self.p_angle -= turn_speed * dt
        if buttons & KEY_RIGHT:
            self.p_angle += turn_speed * dt

        while self.p_angle < 0.0:
            self.p_angle += TWO_PI
        while self.p_angle >= TWO_PI:
            self.p_angle -= TWO_PI

        thrust = 10.0
        if buttons & KEY_UP:
            self.pvx += math.cos(self.p_angle) * thrust * dt
            self.pvy += math.sin(self.p_angle) * thrust * dt

        self.pvx *= 0.96
        self.pvy *= 0.96

        self.px = (self.px + self.pvx * dt) % 16.0
        self.py = (self.py + self.pvy * dt) % 16.0

    def _update_shields(self, dt: float) -> None:
        for r in range(NUM_RINGS):
            self.ring_angles[r] = (self.ring_angles[r] + self.ring_speeds[r] * dt) % TWO_PI

            if r == 0 and not any(self.shield_alive[0]):
                for s in range(SEGMENTS_PER_RING):
                    self.shield_alive[0][s] = True

    def _update_bullets(self, dt: float) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < 0.0 or b["x"] >= 16.0 or b["y"] < 0.0 or b["y"] >= 16.0:
                b["active"] = False

        if self.blast["active"]:
            self.blast["x"] += self.blast["vx"] * dt
            self.blast["y"] += self.blast["vy"] * dt
            if (
                self.blast["x"] < 0.0
                or self.blast["x"] >= 16.0
                or self.blast["y"] < 0.0
                or self.blast["y"] >= 16.0
            ):
                self.blast["active"] = False

    def _update_sparks(self, dt: float) -> None:
        self.spark_spawn_timer -= dt
        if self.spark_spawn_timer <= 0.0:
            self.spark_spawn_timer = max(1.5, 3.5 - self.level * 0.2)
            for spark in self.sparks:
                if not spark["active"]:
                    spark["active"] = True
                    spark["x"] = CENTER_X
                    spark["y"] = CENTER_Y
                    spark["vx"] = 0.0
                    spark["vy"] = 0.0
                    break

        spark_speed = 3.2 + self.level * 0.25
        for spark in self.sparks:
            if not spark["active"]:
                continue
            dx = self.px - spark["x"]
            dy = self.py - spark["y"]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0.1:
                spark["vx"] = (dx / dist) * spark_speed
                spark["vy"] = (dy / dist) * spark_speed
            spark["x"] += spark["vx"] * dt
            spark["y"] += spark["vy"] * dt

    def _update_boss_turret(self, dt: float) -> None:
        self.turret_angle = math.atan2(self.py - CENTER_Y, self.px - CENTER_X)

        self.turret_fire_timer -= dt
        if self.turret_fire_timer <= 0.0:
            self.turret_fire_timer = 0.8
            if self.has_direct_line_of_sight(self.turret_angle) and not self.blast["active"]:
                self.blast["active"] = True
                self.blast["x"] = CENTER_X
                self.blast["y"] = CENTER_Y
                blast_speed = 18.0
                self.blast["vx"] = math.cos(self.turret_angle) * blast_speed
                self.blast["vy"] = math.sin(self.turret_angle) * blast_speed

    def _check_collisions(self) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue

            # vs Sparks
            for spark in self.sparks:
                if not spark["active"]:
                    continue
                if abs(b["x"] - spark["x"]) < 0.8 and abs(b["y"] - spark["y"]) < 0.8:
                    b["active"] = False
                    spark["active"] = False
                    self.score += 50
                    break
            if not b["active"]:
                continue

            cdx = b["x"] - CENTER_X
            cdy = b["y"] - CENTER_Y
            b_dist = math.sqrt(cdx * cdx + cdy * cdy)
            b_angle = math.atan2(cdy, cdx)

            if b_dist < 1.2:
                b["active"] = False
                self.state = STATE_CASTLE_EXPLODING
                self.state_timer = 0.0
                continue

            for r in range(NUM_RINGS):
                if abs(b_dist - RING_RADII[r]) < 0.55:
                    rel_ang = b_angle - self.ring_angles[r]
                    while rel_ang < 0.0:
                        rel_ang += TWO_PI
                    while rel_ang >= TWO_PI:
                        rel_ang -= TWO_PI

                    seg = int(rel_ang / (TWO_PI / 8.0)) % 8
                    if self.shield_alive[r][seg]:
                        self.shield_alive[r][seg] = False
                        b["active"] = False
                        self.score += 20
                        break

        if self.blast["active"]:
            if abs(self.px - self.blast["x"]) < 0.85 and abs(self.py - self.blast["y"]) < 0.85:
                self.blast["active"] = False
                self.state = STATE_PLAYER_EXPLODING
                self.state_timer = 0.0

        for spark in self.sparks:
            if not spark["active"]:
                continue
            if abs(self.px - spark["x"]) < 0.75 and abs(self.py - spark["y"]) < 0.75:
                spark["active"] = False
                self.state = STATE_PLAYER_EXPLODING
                self.state_timer = 0.0
                break

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        elif len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        ring_colors = [
            (255, 60, 40),
            (255, 200, 30),
            (40, 200, 255),
        ]
        for r in range(NUM_RINGS):
            radius = RING_RADII[r]
            for s in range(SEGMENTS_PER_RING):
                if not self.shield_alive[r][s]:
                    continue
                ang_start = self.ring_angles[r] + float(s) * (TWO_PI / 8.0)
                ang_mid = ang_start + (TWO_PI / 16.0)
                sx = int(round(CENTER_X + radius * math.cos(ang_mid)))
                sy = int(round(CENTER_Y + radius * math.sin(ang_mid)))
                set_pixel(sx, sy, ring_colors[r][0], ring_colors[r][1], ring_colors[r][2])

        if self.state == STATE_CASTLE_EXPLODING:
            set_pixel(7, 7, 255, 220, 50)
            set_pixel(8, 7, 255, 80, 20)
            set_pixel(7, 8, 255, 80, 20)
            set_pixel(8, 8, 255, 220, 50)
        else:
            set_pixel(7, 7, 200, 50, 220)
            set_pixel(8, 7, 200, 50, 220)
            set_pixel(7, 8, 200, 50, 220)
            set_pixel(8, 8, 255, 255, 255)

        if self.blast["active"]:
            bx = int(round(self.blast["x"]))
            by = int(round(self.blast["y"]))
            set_pixel(bx, by, 255, 30, 20)

        for spark in self.sparks:
            if not spark["active"]:
                continue
            sx = int(round(spark["x"]))
            sy = int(round(spark["y"]))
            flash = (int(self.state_timer * 12.0) % 2) == 0
            set_pixel(sx, sy, 255 if flash else 200, 255 if flash else 100, 0)

        for b in self.bullets:
            if b["active"]:
                set_pixel(int(round(b["x"])), int(round(b["y"])), 80, 255, 120)

        px_s = int(round(self.px))
        py_s = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_CASTLE_EXPLODING):
            set_pixel(px_s, py_s, 255, 255, 255)
            nx = px_s + int(round(math.cos(self.p_angle)))
            ny = py_s + int(round(math.sin(self.p_angle)))
            set_pixel(nx, ny, 0, 220, 255)
        elif self.state == STATE_PLAYER_EXPLODING:
            set_pixel(px_s, py_s, 255, 200, 50)
            set_pixel(px_s - 1, py_s, 255, 40, 20)
            set_pixel(px_s + 1, py_s, 255, 40, 20)
            set_pixel(px_s, py_s - 1, 255, 40, 20)
            set_pixel(px_s, py_s + 1, 255, 40, 20)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 0, 230, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "px": self.px,
            "py": self.py,
        }
