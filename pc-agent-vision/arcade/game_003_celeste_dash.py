# -*- coding: utf-8 -*-
"""game_003_celeste_dash.py —— 目标 #003 空中冲刺 (Celeste Dash)
精密平台跳跃 + 8方向零重力空中冲刺 + 落地/水晶充能 + 多房间攀登
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
from .arcade_result_screen import ArcadeResultScreen, set_pixel

CELESTE_AIR   = 0
CELESTE_SOLID = 1
CELESTE_SPIKE = 2


class CelesteTrail:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.timer = 0.0
        self.pink = True
        self.active = False


class Game003CelesteDash(BaseCartridge):
    NUM_ROOMS = 3
    MAX_TRAIL = 6

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self.room_idx = 0
        self.lives = 3
        self.player_x = 1.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.facing_x = 1
        self.on_ground = True
        self.coyote_timer = 0.0
        self.dash_ready = True
        self.dash_timer = 0.0
        self.dash_vx = 0.0
        self.dash_vy = 0.0
        self.trail_spawn_acc = 0.0
        self.crystal_x = -1
        self.crystal_y = -1
        self.crystal_present = False
        self.crystal_cooldown = 0.0
        self.crystal_scored = False
        self.goal_x = 14
        self.goal_y = 6
        self._score = 0
        self._high_score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.grid: List[List[int]] = [[CELESTE_AIR] * 16 for _ in range(16)]
        self.trails: List[CelesteTrail] = [CelesteTrail() for _ in range(self.MAX_TRAIL)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 3

    @property
    def name(self) -> str:
        return "空中冲刺"

    @property
    def english_name(self) -> str:
        return "Celeste Dash"

    @property
    def release_year(self) -> int:
        return 2018

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "8方向零重力空中冲刺与水晶充能平台攀登"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _respawn_in_room(self) -> None:
        self.player_x = 1.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.facing_x = 1
        self.on_ground = True
        self.coyote_timer = 0.08
        self.dash_ready = True
        self.dash_timer = 0.0
        self.dash_vx = 0.0
        self.dash_vy = 0.0
        self.trail_spawn_acc = 0.0
        self.crystal_cooldown = 0.0
        for t in self.trails:
            t.active = False

    def load_room(self, room_idx: int) -> None:
        self.room_idx = room_idx
        self.grid = [[CELESTE_AIR] * 16 for _ in range(16)]
        self.crystal_present = False
        self.crystal_scored = False
        self.crystal_x = -1
        self.crystal_y = -1

        for x in range(4):
            self.grid[14][x] = CELESTE_SOLID
            self.grid[15][x] = CELESTE_SOLID
        for x in range(4, 16):
            self.grid[15][x] = CELESTE_SPIKE

        if room_idx == 0:
            for x in range(6, 10):
                self.grid[11][x] = CELESTE_SOLID
            for x in range(12, 16):
                self.grid[7][x] = CELESTE_SOLID
            self.goal_x, self.goal_y = 14, 6
        elif room_idx == 1:
            self.crystal_present = True
            self.crystal_x, self.crystal_y = 7, 9
            for x in range(10, 16):
                self.grid[6][x] = CELESTE_SOLID
            self.goal_x, self.goal_y = 13, 5
        else:
            for x in range(6, 11):
                self.grid[0][x] = CELESTE_SPIKE
            for x in range(7, 11):
                self.grid[11][x] = CELESTE_SOLID
            self.crystal_present = True
            self.crystal_x, self.crystal_y = 12, 7
            for x in range(7, 11):
                self.grid[5][x] = CELESTE_SOLID
            for x in range(1, 5):
                self.grid[3][x] = CELESTE_SOLID
            self.goal_x, self.goal_y = 2, 2

        self._respawn_in_room()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.load_room(0)
        self._state = STATE_TITLE

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.load_room(0)
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _is_solid(self, tx: int, ty: int) -> bool:
        return 0 <= tx < 16 and 0 <= ty < 16 and self.grid[ty][tx] == CELESTE_SOLID

    def _is_spike(self, tx: int, ty: int) -> bool:
        return 0 <= tx < 16 and 0 <= ty < 16 and self.grid[ty][tx] == CELESTE_SPIKE

    def _spawn_trail(self, pink: bool) -> None:
        for t in self.trails:
            if not t.active:
                t.active = True
                t.x = self.player_x
                t.y = self.player_y
                t.timer = 0.22
                t.pink = pink
                return
        t = self.trails[0]
        t.active = True
        t.x = self.player_x
        t.y = self.player_y
        t.timer = 0.22
        t.pink = pink

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        for t in self.trails:
            if t.active:
                t.timer -= dt
                if t.timer <= 0.0:
                    t.active = False

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
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

            if self.crystal_cooldown > 0.0:
                self.crystal_cooldown = max(0.0, self.crystal_cooldown - dt)

            if keys_down & KEY_LEFT:
                self.facing_x = -1
            elif keys_down & KEY_RIGHT:
                self.facing_x = 1

            if self.on_ground:
                self.coyote_timer = 0.08
                if self.dash_timer <= 0.0:
                    self.dash_ready = True
            elif self.coyote_timer > 0.0:
                self.coyote_timer -= dt

            if (keys_pressed & KEY_A) and (self.on_ground or self.coyote_timer > 0.0) and self.dash_timer <= 0.0:
                self.player_vy = -11.5
                self.on_ground = False
                self.coyote_timer = 0.0

            if (keys_pressed & KEY_B) and self.dash_ready and self.dash_timer <= 0.0:
                ix = (1 if (keys_down & KEY_RIGHT) else 0) - (1 if (keys_down & KEY_LEFT) else 0)
                iy = (1 if (keys_down & KEY_DOWN) else 0) - (1 if (keys_down & KEY_UP) else 0)
                if ix == 0 and iy == 0:
                    ix = self.facing_x
                    iy = -1
                norm = 0.70710678 if (ix != 0 and iy != 0) else 1.0
                dash_speed = 28.0
                self.dash_vx = float(ix) * norm * dash_speed
                self.dash_vy = float(iy) * norm * dash_speed
                self.dash_timer = 0.14
                self.dash_ready = False
                self.on_ground = False
                self.coyote_timer = 0.0
                self.trail_spawn_acc = 0.0
                self._spawn_trail(True)

            if self.dash_timer > 0.0:
                self.dash_timer -= dt
                self.trail_spawn_acc += dt
                if self.trail_spawn_acc >= 0.035:
                    self.trail_spawn_acc -= 0.035
                    self._spawn_trail(self.dash_timer > 0.07)
                self.player_vx = self.dash_vx
                self.player_vy = self.dash_vy
                if self.dash_timer <= 0.0:
                    self.dash_timer = 0.0
                    self.player_vx = self.dash_vx * 0.35
                    self.player_vy = self.dash_vy * 0.35
            else:
                move_speed = 7.5
                if keys_down & KEY_LEFT:
                    self.player_vx = -move_speed
                elif keys_down & KEY_RIGHT:
                    self.player_vx = move_speed
                else:
                    self.player_vx = 0.0

                gravity = 32.0
                self.player_vy = min(14.0, self.player_vy + gravity * dt)

            next_x = self.player_x + self.player_vx * dt
            if next_x < 0.0:
                next_x = 0.0
                self.player_vx = 0.0
            elif next_x > 15.0:
                next_x = 15.0
                self.player_vx = 0.0

            check_y = int(round(self.player_y))
            if self.player_vx > 0.0 and self._is_solid(int(math.floor(next_x + 0.85)), check_y):
                next_x = math.floor(next_x + 0.85) - 0.86
                self.player_vx = 0.0
            elif self.player_vx < 0.0 and self._is_solid(int(math.floor(next_x + 0.1)), check_y):
                next_x = math.floor(next_x + 0.1) + 1.0
                self.player_vx = 0.0
            self.player_x = next_x

            old_y = self.player_y
            next_y = self.player_y + self.player_vy * dt
            self.on_ground = False

            left_tx = int(math.floor(self.player_x + 0.15))
            right_tx = int(math.floor(self.player_x + 0.80))

            if self.player_vy >= 0.0:
                foot_ty = int(math.floor(next_y + 0.95))
                if (self._is_solid(left_tx, foot_ty) or self._is_solid(right_tx, foot_ty)) and (
                    old_y + 0.95 <= float(foot_ty) + 0.35
                ):
                    next_y = float(foot_ty) - 1.0
                    self.player_vy = 0.0
                    self.on_ground = True
                    if self.dash_timer <= 0.0:
                        self.dash_ready = True
            else:
                head_ty = int(math.floor(next_y + 0.05))
                if next_y < 0.0:
                    next_y = 0.0
                    self.player_vy = 0.0
                elif self._is_solid(left_tx, head_ty) or self._is_solid(right_tx, head_ty):
                    next_y = float(head_ty + 1)
                    self.player_vy = 0.0
            self.player_y = next_y

            if self.crystal_present and self.crystal_cooldown <= 0.0:
                dx = (self.player_x + 0.5) - (float(self.crystal_x) + 0.5)
                dy = (self.player_y + 0.5) - (float(self.crystal_y) + 0.5)
                if dx * dx + dy * dy <= 1.85:
                    self.dash_ready = True
                    self.crystal_cooldown = 2.5
                    if not self.crystal_scored:
                        self.crystal_scored = True
                        self._add_score(25)

            cx = int(round(self.player_x))
            cy = int(round(self.player_y))
            foot_haz_y = int(math.floor(self.player_y + 0.85))
            if (
                self.player_y > 15.1
                or self._is_spike(cx, cy)
                or self._is_spike(left_tx, foot_haz_y)
                or self._is_spike(right_tx, foot_haz_y)
            ):
                if self.lives > 1:
                    self.lives -= 1
                    self._respawn_in_room()
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                return

            gdx = (self.player_x + 0.5) - (float(self.goal_x) + 0.5)
            gdy = (self.player_y + 0.5) - (float(self.goal_y) + 0.5)
            if gdx * gdx + gdy * gdy <= 1.5:
                self._add_score(100)
                if self.room_idx + 1 < self.NUM_ROOMS:
                    self.load_room(self.room_idx + 1)
                else:
                    self._add_score(200)
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                set_pixel(fb, x, y, 14, 18, 38)

        for y in range(16):
            for x in range(16):
                if self.grid[y][x] == CELESTE_SOLID:
                    snow_top = y > 0 and self.grid[y - 1][x] == CELESTE_AIR
                    if snow_top:
                        set_pixel(fb, x, y, 190, 225, 255)
                    else:
                        set_pixel(fb, x, y, 68, 88, 128)
                elif self.grid[y][x] == CELESTE_SPIKE:
                    set_pixel(fb, x, y, 235, 55, 65)

        if self.crystal_present:
            if self.crystal_cooldown <= 0.0:
                set_pixel(fb, self.crystal_x, self.crystal_y, 80, 255, 160)
            else:
                set_pixel(fb, self.crystal_x, self.crystal_y, 35, 70, 60)

        pulse = int(200 + math.sin(self.anim_timer * 8.0) * 45.0)
        set_pixel(fb, self.goal_x, self.goal_y, 255, max(0, min(255, pulse)), 20)

        for t in self.trails:
            if t.active:
                tx = int(round(t.x))
                ty = int(round(t.y))
                if t.pink:
                    set_pixel(fb, tx, ty, 255, 105, 180)
                else:
                    set_pixel(fb, tx, ty, 0, 220, 255)

        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if self.dash_ready:
            set_pixel(fb, px, py, 0, 245, 255)
        else:
            set_pixel(fb, px, py, 65, 115, 200)

        for i in range(min(3, self.lives)):
            set_pixel(fb, i, 0, 255, 90, 120)
        for r in range(min(self.NUM_ROOMS, self.room_idx + 1)):
            set_pixel(fb, 15 - r, 0, 255, 215, 0)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": 100 if self._state == STATE_VICTORY else (self.room_idx * 100) // self.NUM_ROOMS,
        }
