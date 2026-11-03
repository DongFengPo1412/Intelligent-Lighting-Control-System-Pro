# -*- coding: utf-8 -*-
"""
Game #124: 狂欢节射击场 (Carnival 1980 / Sega)
街机历史上最具代表性的游乐园旋转打靶游戏：
有限弹药库存管控、三层双向对开旋转靶标传送带、俯冲偷吃子弹的野鸭、转轮弹药补给与飞行奖励。
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

STATE_PLAYING = 0
STATE_DUCK_ATTACK = 1
STATE_ROUND_CLEAR = 2
STATE_GAME_OVER = 3

NUM_ROWS = 3
TARGETS_PER_ROW = 6
MAX_BULLETS = 3


class Game124Carnival(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.ammo = 40
        self.round = 1

        self.gun_x = 7.5
        self.bullets: List[Dict[str, Any]] = []
        self.rows: List[List[Dict[str, Any]]] = []
        self.row_offsets = [0.0, 0.0, 0.0]
        self.row_speeds = [-2.0, 2.5, -2.2]

        self.diving_duck = {
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "active": False,
        }
        self.duck_dive_timer = 4.0
        self.bonus_wheel_x = 0.0
        self.bonus_wheel_alive = True

        self.reset()

    @property
    def game_id(self) -> int:
        return 124

    @property
    def name(self) -> str:
        return "狂欢节射击场"

    @property
    def english_name(self) -> str:
        return "Carnival"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "有限弹药库存管控、三层双向对开旋转靶标传送带、俯冲偷吃子弹的野鸭、转轮弹药补给与飞行奖励"

    def get_name(self) -> str:
        return "Carnival (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.round = 1
        self._init_round()

    def _init_round(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.ammo = 40 + (self.round - 1) * 5
        self.gun_x = 7.5

        self.bullets = []
        for _ in range(MAX_BULLETS):
            self.bullets.append({"x": 0.0, "y": 0.0, "active": False})

        self.row_speeds = [
            -(1.8 + self.round * 0.2),
            (2.4 + self.round * 0.2),
            -(2.0 + self.round * 0.2),
        ]
        self.row_offsets = [0.0, 3.0, 6.0]

        self.rows = []
        for r in range(NUM_ROWS):
            row_targets = []
            for i in range(TARGETS_PER_ROW):
                if r == 0:
                    t_type = 3 if i == 2 else 2  # Ammo box or Owl
                elif r == 1:
                    t_type = 0  # Rabbit
                else:
                    t_type = 1  # Duck
                row_targets.append({
                    "x": float(i) * (16.0 / float(TARGETS_PER_ROW)),
                    "type": t_type,
                    "alive": True,
                })
            self.rows.append(row_targets)

        self.diving_duck = {
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "active": False,
        }
        self.duck_dive_timer = 4.0
        self.bonus_wheel_x = 0.0
        self.bonus_wheel_alive = True

    def get_remaining_targets(self) -> int:
        count = 0
        for r in range(NUM_ROWS):
            for t in self.rows[r]:
                if t["alive"] and t["type"] != 3:
                    count += 1
        return count

    def trigger_diving_duck(self) -> None:
        if self.diving_duck["active"]:
            return
        for t in self.rows[2]:
            if t["alive"] and t["type"] == 1:
                duck_x = (t["x"] + self.row_offsets[2]) % 16.0
                t["alive"] = False
                self.diving_duck["active"] = True
                self.diving_duck["x"] = duck_x
                self.diving_duck["y"] = 7.0
                self.diving_duck["vy"] = 4.5
                self.diving_duck["vx"] = 1.5 if self.gun_x > duck_x else -1.5
                break

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

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 1.8:
                self.round += 1
                self.score += self.ammo * 50
                self._init_round()
            return

        # Fire bullet (Button A or B)
        if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
            if self.ammo > 0:
                for b in self.bullets:
                    if not b["active"]:
                        b["active"] = True
                        b["x"] = self.gun_x
                        b["y"] = 13.0
                        self.ammo -= 1
                        break

        self._update_gun(dt, buttons)
        self._update_bullets(dt)
        self._update_carousels(dt)
        self._update_diving_ducks(dt)
        self._check_collisions()

        if self.get_remaining_targets() == 0 and not self.diving_duck["active"]:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0

        if self.ammo <= 0:
            any_active_bullet = any(b["active"] for b in self.bullets)
            if not any_active_bullet and self.get_remaining_targets() > 0:
                self.state = STATE_GAME_OVER

    def _update_gun(self, dt: float, buttons: int) -> None:
        move_speed = 9.0
        if buttons & KEY_LEFT:
            self.gun_x -= move_speed * dt
        if buttons & KEY_RIGHT:
            self.gun_x += move_speed * dt
        if self.gun_x < 0.5:
            self.gun_x = 0.5
        elif self.gun_x > 15.5:
            self.gun_x = 15.5

    def _update_bullets(self, dt: float) -> None:
        bullet_speed = 22.0
        for b in self.bullets:
            if not b["active"]:
                continue
            b["y"] -= bullet_speed * dt
            if b["y"] < 0.0:
                b["active"] = False

    def _update_carousels(self, dt: float) -> None:
        for r in range(NUM_ROWS):
            self.row_offsets[r] = (self.row_offsets[r] + self.row_speeds[r] * dt) % 16.0

        if self.bonus_wheel_alive:
            self.bonus_wheel_x = (self.bonus_wheel_x + 3.5 * dt) % 16.0

        self.duck_dive_timer -= dt
        if self.duck_dive_timer <= 0.0:
            self.duck_dive_timer = 3.5 + random.random() * 3.0
            self.trigger_diving_duck()

    def _update_diving_ducks(self, dt: float) -> None:
        if not self.diving_duck["active"]:
            return
        self.diving_duck["x"] += self.diving_duck["vx"] * dt
        self.diving_duck["y"] += self.diving_duck["vy"] * dt

        if self.diving_duck["y"] >= 14.0:
            if abs(self.diving_duck["x"] - self.gun_x) < 1.6:
                self.ammo = max(0, self.ammo - 5)
            self.diving_duck["active"] = False

    def _check_collisions(self) -> None:
        row_y = [3.0, 5.0, 7.0]
        for b in self.bullets:
            if not b["active"]:
                continue

            # Collision with diving duck
            if self.diving_duck["active"]:
                dx = abs(b["x"] - self.diving_duck["x"])
                dy = abs(b["y"] - self.diving_duck["y"])
                if dx < 0.9 and dy < 0.9:
                    b["active"] = False
                    self.diving_duck["active"] = False
                    self.score += 50
                    continue

            # Collision with bonus wheel
            if self.bonus_wheel_alive and abs(b["y"] - 1.0) < 0.8:
                if abs(b["x"] - self.bonus_wheel_x) < 1.0:
                    b["active"] = False
                    self.bonus_wheel_alive = False
                    self.ammo += 10
                    self.score += 150
                    continue

            # Collision with carousel targets
            for r in range(NUM_ROWS):
                if abs(b["y"] - row_y[r]) < 0.8:
                    for t in self.rows[r]:
                        if not t["alive"]:
                            continue
                        tx = (t["x"] + self.row_offsets[r]) % 16.0
                        if abs(b["x"] - tx) < 0.85:
                            b["active"] = False
                            t["alive"] = False
                            if t["type"] == 3:
                                self.ammo += 5
                                self.score += 25
                            elif t["type"] == 0:
                                self.score += 10
                            elif t["type"] == 1:
                                self.score += 20
                            elif t["type"] == 2:
                                self.score += 30
                            break
                    if not b["active"]:
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

        # Tracks
        for x in range(16):
            set_pixel(x, 2, 20, 20, 35)
            set_pixel(x, 4, 20, 20, 35)
            set_pixel(x, 6, 20, 20, 35)

        # Bonus top wheel
        if self.bonus_wheel_alive:
            bx = int(round(self.bonus_wheel_x)) % 16
            set_pixel(bx, 1, 255, 215, 0)
            set_pixel((bx + 1) % 16, 1, 255, 140, 0)

        # Carousel targets
        row_y = [3, 5, 7]
        for r in range(NUM_ROWS):
            for t in self.rows[r]:
                if not t["alive"]:
                    continue
                tx = int(round((t["x"] + self.row_offsets[r]) % 16.0))
                if t["type"] == 0:
                    set_pixel(tx, row_y[r], 40, 200, 255)
                elif t["type"] == 1:
                    set_pixel(tx, row_y[r], 255, 220, 30)
                elif t["type"] == 2:
                    set_pixel(tx, row_y[r], 200, 60, 255)
                elif t["type"] == 3:
                    set_pixel(tx, row_y[r], 30, 255, 80)

        # Diving duck
        if self.diving_duck["active"]:
            dx = int(round(self.diving_duck["x"]))
            dy = int(round(self.diving_duck["y"]))
            set_pixel(dx, dy, 255, 60, 30)
            set_pixel(dx, dy - 1, 255, 200, 0)

        # Bullets
        for b in self.bullets:
            if b["active"]:
                set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 255)

        # Gun
        gx = int(round(self.gun_x))
        set_pixel(gx, 13, 0, 255, 200)
        set_pixel(gx - 1, 14, 0, 180, 255)
        set_pixel(gx, 14, 255, 255, 255)
        set_pixel(gx + 1, 14, 0, 180, 255)

        # Ammunition bar
        ammo_pips = min(16, self.ammo // 3)
        for a in range(16):
            if a < ammo_pips:
                if self.ammo <= 5:
                    set_pixel(a, 15, 255, 30, 20)
                else:
                    set_pixel(a, 15, 255, 220, 50)
            else:
                set_pixel(a, 15, 20, 20, 20)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "ammo": self.ammo,
            "round": self.round,
            "gun_x": self.gun_x,
            "remaining_targets": self.get_remaining_targets(),
        }
