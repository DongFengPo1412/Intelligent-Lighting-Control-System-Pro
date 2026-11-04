# -*- coding: utf-8 -*-
"""game_004_gravity_flip.py —— 目标 #004 重力翻转 (VVVVVV Flip)
严禁常规跳跃! 仅在接触地面或天花板时反转重力方向穿梭尖刺回廊
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

FLIP_AIR   = 0
FLIP_SOLID = 1
FLIP_SPIKE = 2


class GravityOrb:
    def __init__(self, x: int = 0, y: int = 0, collected: bool = False):
        self.x = x
        self.y = y
        self.collected = collected


class Game004GravityFlip(BaseCartridge):
    NUM_STAGES = 3

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self.stage_idx = 0
        self.lives = 3
        self.player_x = 1.0
        self.player_y = 14.0
        self.player_vy = 0.0
        self.gravity_dir = 1
        self.grounded = True
        self.drone_x = 8.0
        self.drone_y = 7.0
        self.drone_vx = 0.0
        self.drone_vy = 5.0
        self.drone_min = 4.5
        self.drone_max = 10.5
        self.exit_x = 14
        self.exit_y = 14
        self._score = 0
        self._high_score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.grid: List[List[int]] = [[FLIP_AIR] * 16 for _ in range(16)]
        self.orbs: List[GravityOrb] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 4

    @property
    def name(self) -> str:
        return "重力翻转"

    @property
    def english_name(self) -> str:
        return "VVVVVV Flip"

    @property
    def release_year(self) -> int:
        return 2010

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "无跳跃键纯天花板/地面重力反转穿梭"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _respawn_player(self) -> None:
        self.player_x = 1.0
        self.player_y = 14.0
        self.player_vy = 0.0
        self.gravity_dir = 1
        self.grounded = True

    def load_stage(self, stage_idx: int) -> None:
        self.stage_idx = stage_idx
        self.grid = [[FLIP_AIR] * 16 for _ in range(16)]
        for x in range(16):
            self.grid[0][x] = FLIP_SOLID
            self.grid[15][x] = FLIP_SOLID

        if stage_idx == 0:
            for x in range(5, 8):
                self.grid[14][x] = FLIP_SPIKE
            for x in range(10, 13):
                self.grid[1][x] = FLIP_SPIKE
            self.orbs = [GravityOrb(6, 1, False), GravityOrb(11, 14, False)]
            self.drone_x, self.drone_y = 8.0, 7.0
            self.drone_vx, self.drone_vy = 0.0, 5.0
            self.drone_min, self.drone_max = 4.5, 10.5
            self.exit_x, self.exit_y = 14, 14
        elif stage_idx == 1:
            for x in range(4, 7):
                self.grid[14][x] = FLIP_SPIKE
            for x in range(11, 13):
                self.grid[14][x] = FLIP_SPIKE
            for x in range(7, 10):
                self.grid[1][x] = FLIP_SPIKE
            for x in range(6, 9):
                self.grid[8][x] = FLIP_SOLID
            self.orbs = [GravityOrb(5, 1, False), GravityOrb(7, 7, False)]
            self.drone_x, self.drone_y = 10.0, 6.0
            self.drone_vx, self.drone_vy = 0.0, 6.0
            self.drone_min, self.drone_max = 4.0, 11.0
            self.exit_x, self.exit_y = 14, 1
        else:
            for x in range(3, 6):
                self.grid[14][x] = FLIP_SPIKE
            for x in range(9, 12):
                self.grid[14][x] = FLIP_SPIKE
            for x in range(6, 9):
                self.grid[1][x] = FLIP_SPIKE
            for x in range(12, 14):
                self.grid[1][x] = FLIP_SPIKE
            self.orbs = [GravityOrb(4, 1, False), GravityOrb(10, 1, False)]
            self.drone_x, self.drone_y = 5.0, 7.5
            self.drone_vx, self.drone_vy = 6.5, 0.0
            self.drone_min, self.drone_max = 3.0, 12.0
            self.exit_x, self.exit_y = 14, 14

        self._respawn_player()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.load_stage(0)
        self._state = STATE_TITLE

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.load_stage(0)
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _is_solid(self, tx: int, ty: int) -> bool:
        return 0 <= tx < 16 and 0 <= ty < 16 and self.grid[ty][tx] == FLIP_SOLID

    def _is_spike(self, tx: int, ty: int) -> bool:
        return 0 <= tx < 16 and 0 <= ty < 16 and self.grid[ty][tx] == FLIP_SPIKE

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
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

            if self.drone_vx != 0.0:
                self.drone_x += self.drone_vx * dt
                if self.drone_x <= self.drone_min:
                    self.drone_x = self.drone_min
                    self.drone_vx = abs(self.drone_vx)
                elif self.drone_x >= self.drone_max:
                    self.drone_x = self.drone_max
                    self.drone_vx = -abs(self.drone_vx)

            if self.drone_vy != 0.0:
                self.drone_y += self.drone_vy * dt
                if self.drone_y <= self.drone_min:
                    self.drone_y = self.drone_min
                    self.drone_vy = abs(self.drone_vy)
                elif self.drone_y >= self.drone_max:
                    self.drone_y = self.drone_max
                    self.drone_vy = -abs(self.drone_vy)

            # Strictly NO normal jump! Flip gravity ONLY when standing on floor or ceiling.
            flip_mask = KEY_A | KEY_B | KEY_UP | KEY_DOWN
            if self.grounded and (keys_pressed & flip_mask):
                self.gravity_dir = -self.gravity_dir
                self.grounded = False
                self.player_vy = float(self.gravity_dir) * 2.5

            move_speed = 7.5
            vx = 0.0
            if keys_down & KEY_LEFT:
                vx = -move_speed
            elif keys_down & KEY_RIGHT:
                vx = move_speed

            next_x = max(0.0, min(15.0, self.player_x + vx * dt))
            cur_ty = int(round(self.player_y))
            if vx > 0.0 and self._is_solid(int(math.floor(next_x + 0.85)), cur_ty):
                next_x = math.floor(next_x + 0.85) - 0.86
            elif vx < 0.0 and self._is_solid(int(math.floor(next_x + 0.1)), cur_ty):
                next_x = math.floor(next_x + 0.1) + 1.0
            self.player_x = next_x

            left_tx = int(math.floor(self.player_x + 0.15))
            right_tx = int(math.floor(self.player_x + 0.80))

            if self.grounded:
                support_ty = (int(round(self.player_y)) + 1) if self.gravity_dir > 0 else (int(round(self.player_y)) - 1)
                if not self._is_solid(left_tx, support_ty) and not self._is_solid(right_tx, support_ty):
                    self.grounded = False

            if not self.grounded:
                grav_accel = 38.0
                self.player_vy = max(-14.0, min(14.0, self.player_vy + float(self.gravity_dir) * grav_accel * dt))
                next_y = self.player_y + self.player_vy * dt

                if self.gravity_dir > 0 and self.player_vy >= 0.0:
                    foot_ty = int(math.floor(next_y + 0.95))
                    if self._is_solid(left_tx, foot_ty) or self._is_solid(right_tx, foot_ty):
                        next_y = float(foot_ty) - 1.0
                        self.player_vy = 0.0
                        self.grounded = True
                elif self.gravity_dir < 0 and self.player_vy <= 0.0:
                    head_ty = int(math.floor(next_y + 0.05))
                    if self._is_solid(left_tx, head_ty) or self._is_solid(right_tx, head_ty):
                        next_y = float(head_ty + 1)
                        self.player_vy = 0.0
                        self.grounded = True
                self.player_y = next_y

            for orb in self.orbs:
                if not orb.collected:
                    odx = (self.player_x + 0.5) - (float(orb.x) + 0.5)
                    ody = (self.player_y + 0.5) - (float(orb.y) + 0.5)
                    if odx * odx + ody * ody <= 1.2:
                        orb.collected = True
                        self._add_score(50)

            cx = int(round(self.player_x))
            cy = int(round(self.player_y))
            ddx = self.player_x - self.drone_x
            ddy = self.player_y - self.drone_y
            hit_drone = (ddx * ddx + ddy * ddy <= 0.65)
            hit_spike = self._is_spike(cx, cy) or self._is_spike(left_tx, cy) or self._is_spike(right_tx, cy)

            if hit_spike or hit_drone:
                if self.lives > 1:
                    self.lives -= 1
                    self._respawn_player()
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                return

            edx = (self.player_x + 0.5) - (float(self.exit_x) + 0.5)
            edy = (self.player_y + 0.5) - (float(self.exit_y) + 0.5)
            if edx * edx + edy * edy <= 1.6:
                self._add_score(100)
                if self.stage_idx + 1 < self.NUM_STAGES:
                    self.load_stage(self.stage_idx + 1)
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
                bg_b = 24 + ((x + y) & 1) * 6
                set_pixel(fb, x, y, 8, 12, bg_b)

        for y in range(16):
            for x in range(16):
                if self.grid[y][x] == FLIP_SOLID:
                    set_pixel(fb, x, y, 45, 110, 175)
                elif self.grid[y][x] == FLIP_SPIKE:
                    set_pixel(fb, x, y, 235, 50, 55)

        for orb in self.orbs:
            if not orb.collected:
                set_pixel(fb, orb.x, orb.y, 255, 230, 40)

        set_pixel(fb, int(round(self.drone_x)), int(round(self.drone_y)), 255, 90, 210)

        beam_y2 = (self.exit_y + 1) if self.exit_y <= 2 else (self.exit_y - 1)
        set_pixel(fb, self.exit_x, self.exit_y, 46, 255, 130)
        set_pixel(fb, self.exit_x, beam_y2, 20, 180, 95)

        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if self.gravity_dir > 0:
            set_pixel(fb, px, py, 90, 245, 255)
        else:
            set_pixel(fb, px, py, 160, 255, 220)

        for i in range(min(3, self.lives)):
            set_pixel(fb, i, 0, 255, 255, 255)

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
            "progress": 100 if self._state == STATE_VICTORY else (self.stage_idx * 100) // self.NUM_STAGES,
        }
