# -*- coding: utf-8 -*-
"""
Game #126: 旋风巡航者 (Gyruss 1983 / Konami)
街机历史上最具代表性的360度圆周管状轨道向心射击游戏：
外环圆周轨道回旋航行、向心质点火炮齐射、深空中心向外扩散变轨敌机群、行星跃迁倒计时与螺旋机动。
"""

from typing import List, Dict, Any, Optional
import math
import random
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

STATE_FLYING = 0
STATE_WARPING = 1
STATE_PLAYER_EXPLODING = 2
STATE_GAME_OVER = 3

PI = 3.14159265
CENTER_X = 7.5
CENTER_Y = 7.5
ORBIT_RADIUS = 6.8
MAX_ENEMIES = 8
MAX_BULLETS = 6


class Game126Gyruss(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.warp_stage = 0
        self.remaining_dist = 20

        self.player_angle = -PI * 0.5
        self.roll_timer = 0.0
        self.roll_cooldown = 0.0

        self.bullets: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.wave_timer = 0.5

        self.reset()

    @property
    def game_id(self) -> int:
        return 126

    @property
    def name(self) -> str:
        return "旋风巡航者"

    @property
    def english_name(self) -> str:
        return "Gyruss"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "360度环状圆周轨道回旋、质心向心火炮齐射、中心放射扩散变轨敌群与螺旋翻滚"

    def get_name(self) -> str:
        return "Gyruss (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.warp_stage = 0
        self._init_stage()

    def _init_stage(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.remaining_dist = 20

        self.player_angle = -PI * 0.5
        self.roll_timer = 0.0
        self.roll_cooldown = 0.0

        self.bullets = []
        for _ in range(MAX_BULLETS):
            self.bullets.append({
                "radius": 0.0,
                "angle": 0.0,
                "active": False,
            })

        self.enemies = []
        for _ in range(MAX_ENEMIES):
            self.enemies.append({
                "radius": 0.0,
                "angle": 0.0,
                "speed_r": 0.0,
                "speed_a": 0.0,
                "is_asteroid": False,
                "active": False,
            })

        self.wave_timer = 0.5

    def spawn_wave(self) -> None:
        count = 2 + (self.warp_stage % 3)
        base_angle = random.random() * 2.0 * PI
        for enemy in self.enemies:
            if not enemy["active"] and count > 0:
                enemy["radius"] = 0.5
                enemy["angle"] = base_angle + count * 0.7
                enemy["speed_r"] = 2.8 + self.warp_stage * 0.3
                enemy["speed_a"] = 1.8 if (count % 2 == 0) else -1.8
                enemy["is_asteroid"] = (random.random() < 0.25)
                enemy["active"] = True
                count -= 1

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
                    self.state = STATE_FLYING
                    self.player_angle = -PI * 0.5
                    self.roll_timer = 0.0
            return

        if self.state == STATE_WARPING:
            if self.state_timer > 1.6:
                self.warp_stage += 1
                self.score += 1500
                self._init_stage()
            return

        # Fire Button A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            for b in self.bullets:
                if not b["active"]:
                    b["active"] = True
                    b["radius"] = ORBIT_RADIUS - 0.4
                    b["angle"] = self.player_angle
                    break

        # Roll Button B
        if self.roll_cooldown > 0.0:
            self.roll_cooldown -= dt
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.roll_cooldown <= 0.0:
                self.roll_timer = 0.4
                self.roll_cooldown = 1.8
        if self.roll_timer > 0.0:
            self.roll_timer -= dt

        self._update_ship(dt, buttons)
        self._update_bullets(dt)
        self._update_enemies(dt)
        self._check_collisions()

        if self.remaining_dist <= 0:
            any_active = any(e["active"] for e in self.enemies)
            if not any_active:
                self.state = STATE_WARPING
                self.state_timer = 0.0

    def _update_ship(self, dt: float, buttons: int) -> None:
        rot_speed = 10.0 if (self.roll_timer > 0.0) else 4.8
        if buttons & KEY_LEFT:
            self.player_angle -= rot_speed * dt
        if buttons & KEY_RIGHT:
            self.player_angle += rot_speed * dt

        while self.player_angle < 0.0:
            self.player_angle += 2.0 * PI
        while self.player_angle >= 2.0 * PI:
            self.player_angle -= 2.0 * PI

    def _update_bullets(self, dt: float) -> None:
        bullet_speed = 16.0
        for b in self.bullets:
            if not b["active"]:
                continue
            b["radius"] -= bullet_speed * dt
            if b["radius"] <= 0.4:
                b["active"] = False

    def _update_enemies(self, dt: float) -> None:
        self.wave_timer -= dt
        if self.wave_timer <= 0.0 and self.remaining_dist > 0:
            self.wave_timer = max(0.8, 2.2 - (self.warp_stage % 4) * 0.2)
            self.spawn_wave()
            self.remaining_dist -= 2

        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            enemy["radius"] += enemy["speed_r"] * dt
            enemy["angle"] += enemy["speed_a"] * dt
            while enemy["angle"] < 0.0:
                enemy["angle"] += 2.0 * PI
            while enemy["angle"] >= 2.0 * PI:
                enemy["angle"] -= 2.0 * PI

            if enemy["radius"] > 7.5:
                enemy["active"] = False

    def _check_collisions(self) -> None:
        # Bullets vs Enemies
        for b in self.bullets:
            if not b["active"]:
                continue
            for enemy in self.enemies:
                if not enemy["active"]:
                    continue

                r_diff = abs(b["radius"] - enemy["radius"])
                a_diff = abs(b["angle"] - enemy["angle"])
                while a_diff > PI:
                    a_diff = abs(a_diff - 2.0 * PI)

                if r_diff < 0.85 and a_diff < 0.38:
                    b["active"] = False
                    enemy["active"] = False
                    self.score += 200 if enemy["is_asteroid"] else 100
                    break

        # Enemies vs Player
        if self.roll_timer <= 0.0:
            for enemy in self.enemies:
                if not enemy["active"]:
                    continue
                if ORBIT_RADIUS - 0.7 <= enemy["radius"] <= ORBIT_RADIUS + 0.7:
                    a_diff = abs(self.player_angle - enemy["angle"])
                    while a_diff > PI:
                        a_diff = abs(a_diff - 2.0 * PI)

                    if a_diff < 0.38:
                        enemy["active"] = False
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

        # 1. Central galaxy / star vortex
        set_pixel(7, 7, 60, 60, 140)
        set_pixel(8, 7, 60, 60, 140)
        set_pixel(7, 8, 60, 60, 140)
        set_pixel(8, 8, 120, 120, 255)

        # 2. Planetary destination
        set_pixel(8, 8, 255, 200, 50)

        # 3. Enemies
        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            ex = int(round(CENTER_X + enemy["radius"] * math.cos(enemy["angle"])))
            ey = int(round(CENTER_Y + enemy["radius"] * math.sin(enemy["angle"])))
            if enemy["is_asteroid"]:
                set_pixel(ex, ey, 200, 140, 60)
            else:
                if enemy["radius"] < 3.5:
                    set_pixel(ex, ey, 180, 40, 255)
                else:
                    set_pixel(ex, ey, 255, 40, 120)

        # 4. Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(CENTER_X + b["radius"] * math.cos(b["angle"])))
            by = int(round(CENTER_Y + b["radius"] * math.sin(b["angle"])))
            set_pixel(bx, by, 80, 255, 120)

        # 5. Player
        px = int(round(CENTER_X + ORBIT_RADIUS * math.cos(self.player_angle)))
        py = int(round(CENTER_Y + ORBIT_RADIUS * math.sin(self.player_angle)))

        if self.state in (STATE_FLYING, STATE_WARPING):
            if self.roll_timer > 0.0:
                set_pixel(px, py, 255, 255, 255)
            else:
                set_pixel(px, py, 0, 230, 255)
            in_ang = self.player_angle + PI
            nx = px + int(round(math.cos(in_ang)))
            ny = py + int(round(math.sin(in_ang)))
            set_pixel(nx, ny, 255, 220, 0)
        elif self.state == STATE_PLAYER_EXPLODING:
            set_pixel(px, py, 255, 220, 40)
            set_pixel(px - 1, py, 255, 50, 20)
            set_pixel(px + 1, py, 255, 50, 20)
            set_pixel(px, py - 1, 255, 50, 20)
            set_pixel(px, py + 1, 255, 50, 20)

        # 6. Lives
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
            "warp_stage": self.warp_stage,
            "remaining_dist": self.remaining_dist,
            "player_angle": self.player_angle,
        }
