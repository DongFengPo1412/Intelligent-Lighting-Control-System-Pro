# -*- coding: utf-8 -*-
"""game_028_missile_command.py —— 目标 #028 导弹指挥官 (Missile Command, 1980)
与 ESP32-S3 C++ Game028MissileCommand 1:1 对齐实现
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

CITY_X = (2, 5, 10, 13)
SILO_X = (0, 8, 15)


class EnemyBallistic028:
    def __init__(self):
        self.active = False
        self.start_x = 0.0
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.target_x = 0.0


class CounterMissile028:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.target_x = 0.0
        self.target_y = 0.0


class ShockwaveBlast028:
    def __init__(self):
        self.active = False
        self.expanding = True
        self.x = 0.0
        self.y = 0.0
        self.radius = 0.0
        self.max_radius = 2.5


class Game028MissileCommand(BaseCartridge):
    NUM_CITIES = 4
    MAX_ENEMY_MISSILES = 8
    MAX_COUNTER_MISSILES = 4
    MAX_BLASTS = 6

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.wave = 1
        self.ammo = 16
        self.spawn_remaining = 8
        self.cross_x = 7.5
        self.cross_y = 7.0
        self.fire_cooldown = 0.0
        self.spawn_timer = 0.35
        self.city_alive: List[bool] = [True] * self.NUM_CITIES
        self.enemies: List[EnemyBallistic028] = [EnemyBallistic028() for _ in range(self.MAX_ENEMY_MISSILES)]
        self.counters: List[CounterMissile028] = [CounterMissile028() for _ in range(self.MAX_COUNTER_MISSILES)]
        self.blasts: List[ShockwaveBlast028] = [ShockwaveBlast028() for _ in range(self.MAX_BLASTS)]
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x028C0DE1
        self.reset()

    @property
    def game_id(self) -> int:
        return 28

    @property
    def name(self) -> str:
        return "导弹指挥官"

    @property
    def english_name(self) -> str:
        return "Missile Command"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "准星发射拦截弹与圆形冲击波AoE保卫底部城市"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def count_cities(self) -> int:
        return sum(1 for c in self.city_alive if c)

    def _init_wave(self) -> None:
        self.ammo = 16
        self.spawn_remaining = 6 + self.wave * 2
        self.spawn_timer = 0.35
        for e in self.enemies:
            e.active = False
        for c in self.counters:
            c.active = False
        for b in self.blasts:
            b.active = False

    def _setup_new_game(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.wave = 1
        self.cross_x = 7.5
        self.cross_y = 7.0
        self.fire_cooldown = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x028C0DE1
        self.city_alive = [True] * self.NUM_CITIES
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

    def _spawn_enemy_missile(self) -> None:
        if self.spawn_remaining <= 0:
            return
        for e in self.enemies:
            if not e.active:
                alive_targets = [CITY_X[i] for i in range(self.NUM_CITIES) if self.city_alive[i]]
                sx = 1.0 + float(self._next_rand() % 14)
                if alive_targets:
                    tx = float(alive_targets[self._next_rand() % len(alive_targets)])
                else:
                    tx = float(SILO_X[self._next_rand() % 3])
                speed = 2.1 + (self.wave - 1) * 0.45
                dx = tx - sx
                dy = 15.0
                dist = max(0.1, math.hypot(dx, dy))
                e.active = True
                e.start_x = sx
                e.x = sx
                e.y = 0.0
                e.target_x = tx
                e.vx = (dx / dist) * speed
                e.vy = (dy / dist) * speed
                self.spawn_remaining -= 1
                return

    def _fire_counter_missile(self) -> bool:
        if self.ammo <= 0 or self.fire_cooldown > 0.0:
            return False
        for c in self.counters:
            if not c.active:
                best_silo = min(SILO_X, key=lambda sx: abs(self.cross_x - sx))
                sx = float(best_silo)
                sy = 14.5
                dx = self.cross_x - sx
                dy = self.cross_y - sy
                dist = max(0.1, math.hypot(dx, dy))
                speed = 22.0
                c.active = True
                c.x = sx
                c.y = sy
                c.target_x = self.cross_x
                c.target_y = self.cross_y
                c.vx = (dx / dist) * speed
                c.vy = (dy / dist) * speed
                self.ammo -= 1
                self.fire_cooldown = 0.12
                return True
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
            self.cross_x = 7.5 + math.sin(self.anim_timer * 2.5) * 4.0
            self.cross_y = 6.5 + math.cos(self.anim_timer * 1.8) * 2.5
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

            if self.fire_cooldown > 0.0:
                self.fire_cooldown -= dt

            aim_speed = 12.0
            if keys_down & KEY_LEFT:
                self.cross_x -= aim_speed * dt
            if keys_down & KEY_RIGHT:
                self.cross_x += aim_speed * dt
            if keys_down & KEY_UP:
                self.cross_y -= aim_speed * dt
            if keys_down & KEY_DOWN:
                self.cross_y += aim_speed * dt

            self.cross_x = max(1.0, min(14.0, self.cross_x))
            self.cross_y = max(1.0, min(13.0, self.cross_y))

            if keys_pressed & (KEY_A | KEY_B):
                self._fire_counter_missile()

            if self.spawn_remaining > 0:
                self.spawn_timer -= dt
                if self.spawn_timer <= 0.0:
                    self.spawn_timer = max(0.55, 1.05 - (self.wave - 1) * 0.15)
                    self._spawn_enemy_missile()

            for c in self.counters:
                if not c.active:
                    continue
                c.x += c.vx * dt
                c.y += c.vy * dt
                dist = math.hypot(c.target_x - c.x, c.target_y - c.y)
                if dist <= 0.85 or c.y <= c.target_y:
                    bx, by = c.target_x, c.target_y
                    c.active = False
                    for b in self.blasts:
                        if not b.active:
                            b.active = True
                            b.expanding = True
                            b.x = bx
                            b.y = by
                            b.radius = 0.4
                            b.max_radius = 2.5
                            break

            for b in self.blasts:
                if not b.active:
                    continue
                if b.expanding:
                    b.radius += 6.2 * dt
                    if b.radius >= b.max_radius:
                        b.radius = b.max_radius
                        b.expanding = False
                else:
                    b.radius -= 4.2 * dt
                    if b.radius <= 0.0:
                        b.active = False
                        continue

                for e in self.enemies:
                    if e.active and math.hypot(e.x - b.x, e.y - b.y) <= b.radius + 0.35:
                        e.active = False
                        self._add_score(100)

            for e in self.enemies:
                if not e.active:
                    continue
                e.x += e.vx * dt
                e.y += e.vy * dt

                intercepted = False
                for b in self.blasts:
                    if b.active and math.hypot(e.x - b.x, e.y - b.y) <= b.radius + 0.35:
                        e.active = False
                        self._add_score(100)
                        intercepted = True
                        break
                if intercepted:
                    continue

                if e.y >= 15.0:
                    e.active = False
                    for idx, cx in enumerate(CITY_X):
                        if self.city_alive[idx] and abs(e.x - cx) <= 0.95:
                            self.city_alive[idx] = False
                            break
                    if self.count_cities() == 0:
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

            if self.spawn_remaining == 0 and not any(e.active for e in self.enemies):
                self._add_score(self.count_cities() * 100 + self.ammo * 10)
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

        for y in range(15):
            for x in range(16):
                set_px(x, y, 5, 8, 18)
        for x in range(16):
            set_px(x, 15, 140, 95, 40)

        for sx in SILO_X:
            set_px(sx, 15, 60, 150, 230)
            if self.ammo > 0:
                set_px(sx, 14, 210, 235, 255)

        for idx, cx in enumerate(CITY_X):
            if self.city_alive[idx]:
                set_px(cx, 15, 46, 224, 150)
                set_px(cx, 14, 30, 170, 210)
            else:
                set_px(cx, 15, 65, 45, 35)

        for e in self.enemies:
            if not e.active:
                continue
            for step in (1, 2, 3):
                tx = int(round(e.x - e.vx * 0.12 * step))
                ty = int(round(e.y - e.vy * 0.12 * step))
                set_px(tx, ty, 120, 30, 30)
            set_px(int(round(e.x)), int(round(e.y)), 255, 65, 55)

        for c in self.counters:
            if c.active:
                set_px(int(round(c.x)), int(round(c.y)), 255, 255, 255)

        for b in self.blasts:
            if not b.active:
                continue
            cx = int(round(b.x))
            cy = int(round(b.y))
            r2 = b.radius * b.radius
            ir = int(math.ceil(b.radius))
            for dy in range(-ir, ir + 1):
                for dx in range(-ir, ir + 1):
                    d2 = float(dx * dx + dy * dy)
                    if d2 <= r2:
                        core = d2 <= r2 * 0.35
                        set_px(cx + dx, cy + dy, 255, 245 if core else 175, 180 if core else 25)

        hx = int(round(self.cross_x))
        hy = int(round(self.cross_y))
        set_px(hx - 1, hy, 46, 204, 113)
        set_px(hx + 1, hy, 46, 204, 113)
        set_px(hx, hy - 1, 46, 204, 113)
        set_px(hx, hy + 1, 46, 204, 113)
        set_px(hx, hy, 220, 255, 220)

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
            "lives": self.count_cities(),
            "state": self._state,
            "progress": 100 if self._state == STATE_VICTORY else (self.wave - 1) * 33,
        }
