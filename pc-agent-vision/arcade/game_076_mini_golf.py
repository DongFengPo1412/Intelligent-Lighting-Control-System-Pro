# -*- coding: utf-8 -*-
"""game_076_mini_golf.py —— 目标 #076 迷你高尔夫 (Mini Golf, 1987)
4洞16x16球场 + 16向瞄准线与3档力度推杆 + 木墙反弹/沙坑高阻尼/水障罚杆复位
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

GOLF_FAIRWAY = 0
GOLF_WALL = 1
GOLF_SAND = 2
GOLF_WATER = 3

POWER_SPEEDS = (6.5, 10.5, 14.5)


class Game076MiniGolf(BaseCartridge):
    TOTAL_HOLES = 4
    MAX_TOTAL_STROKES = 18

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.tiles = [[GOLF_FAIRWAY] * 16 for _ in range(16)]
        self.hole_index = 0
        self.hole_strokes = 0
        self.total_strokes = 0
        self.ball_x = 3.5
        self.ball_y = 12.5
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.saved_x = 3.5
        self.saved_y = 12.5
        self.cup_x = 12.5
        self.cup_y = 3.5
        self.ball_moving = False
        self.aim_angle = 14
        self.power_level = 1
        self.splash_timer = 0.0
        self.sink_flash_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 76

    @property
    def name(self) -> str:
        return "迷你高尔夫"

    @property
    def english_name(self) -> str:
        return "Mini Golf"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "16向3档推杆反弹与沙坑阻尼水障罚杆进洞"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def load_hole(self, idx: int) -> None:
        self.tiles = [
            [GOLF_WALL if (x in (0, 15) or y in (0, 15)) else GOLF_FAIRWAY for x in range(16)]
            for y in range(16)
        ]
        self.hole_strokes = 0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_moving = False

        if idx == 0:
            self.ball_x, self.ball_y = 3.5, 12.5
            self.cup_x, self.cup_y = 12.5, 3.5
            self.aim_angle = 14
            for y in range(11, 14):
                for x in range(8, 12):
                    self.tiles[y][x] = GOLF_SAND
            for y in range(4, 7):
                for x in range(3, 6):
                    self.tiles[y][x] = GOLF_WATER
        elif idx == 1:
            self.ball_x, self.ball_y = 3.5, 12.5
            self.cup_x, self.cup_y = 12.5, 12.5
            self.aim_angle = 12
            for y in range(6, 15):
                self.tiles[y][7] = GOLF_WALL
                self.tiles[y][8] = GOLF_WALL
            self.tiles[2][7] = GOLF_SAND
            self.tiles[2][8] = GOLF_SAND
            self.tiles[13][6] = GOLF_WATER
            self.tiles[14][6] = GOLF_WATER
            self.tiles[13][9] = GOLF_WATER
            self.tiles[14][9] = GOLF_WATER
        elif idx == 2:
            self.ball_x, self.ball_y = 7.5, 13.5
            self.cup_x, self.cup_y = 7.5, 2.5
            self.aim_angle = 12
            for y in range(5, 11):
                for x in range(2, 5):
                    self.tiles[y][x] = GOLF_WATER
                for x in range(11, 14):
                    self.tiles[y][x] = GOLF_WATER
            self.tiles[8][7] = GOLF_SAND
            self.tiles[8][8] = GOLF_SAND
        else:
            self.ball_x, self.ball_y = 3.5, 13.5
            self.cup_x, self.cup_y = 12.5, 2.5
            self.aim_angle = 0
            for x in range(1, 10):
                self.tiles[9][x] = GOLF_WALL
            for x in range(6, 15):
                self.tiles[5][x] = GOLF_WALL
            for y in range(11, 13):
                for x in range(12, 14):
                    self.tiles[y][x] = GOLF_SAND
            for y in range(2, 4):
                for x in range(2, 4):
                    self.tiles[y][x] = GOLF_WATER

        self.saved_x = self.ball_x
        self.saved_y = self.ball_y

    def _init_game_data(self) -> None:
        self.hole_index = 0
        self.hole_strokes = 0
        self.total_strokes = 0
        self.power_level = 1
        self.splash_timer = 0.0
        self.sink_flash_timer = 0.0
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.load_hole(0)

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._init_game_data()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._init_game_data()
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _is_wall_at(self, px: float, py: float) -> bool:
        gx = int(math.floor(px))
        gy = int(math.floor(py))
        if gx < 0 or gx >= 16 or gy < 0 or gy >= 16:
            return True
        return self.tiles[gy][gx] == GOLF_WALL

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt
        if self.splash_timer > 0.0:
            self.splash_timer = max(0.0, self.splash_timer - dt)
        if self.sink_flash_timer > 0.0:
            self.sink_flash_timer = max(0.0, self.sink_flash_timer - dt)

        if self._state == STATE_TITLE:
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

            if not self.ball_moving:
                if keys_pressed & KEY_LEFT:
                    self.aim_angle = (self.aim_angle + 15) % 16
                if keys_pressed & KEY_RIGHT:
                    self.aim_angle = (self.aim_angle + 1) % 16
                if keys_pressed & (KEY_UP | KEY_B):
                    self.power_level = (self.power_level + 1) % 3
                if keys_pressed & KEY_DOWN:
                    self.power_level = (self.power_level + 2) % 3

                if keys_pressed & KEY_A:
                    self.saved_x = self.ball_x
                    self.saved_y = self.ball_y
                    self.hole_strokes += 1
                    self.total_strokes += 1
                    rad = float(self.aim_angle) * (math.pi / 8.0)
                    spd = POWER_SPEEDS[self.power_level]
                    self.ball_vx = math.cos(rad) * spd
                    self.ball_vy = math.sin(rad) * spd
                    self.ball_moving = True
            else:
                sub_steps = 4
                sub_dt = dt / float(sub_steps)

                for _ in range(sub_steps):
                    nx = self.ball_x + self.ball_vx * sub_dt
                    if self._is_wall_at(nx, self.ball_y):
                        self.ball_vx = -self.ball_vx * 0.82
                    else:
                        self.ball_x = nx

                    ny = self.ball_y + self.ball_vy * sub_dt
                    if self._is_wall_at(self.ball_x, ny):
                        self.ball_vy = -self.ball_vy * 0.82
                    else:
                        self.ball_y = ny

                    gx = max(0, min(15, int(math.floor(self.ball_x))))
                    gy = max(0, min(15, int(math.floor(self.ball_y))))

                    if self.tiles[gy][gx] == GOLF_WATER:
                        self.hole_strokes += 1
                        self.total_strokes += 1
                        self.ball_x = self.saved_x
                        self.ball_y = self.saved_y
                        self.ball_vx = 0.0
                        self.ball_vy = 0.0
                        self.ball_moving = False
                        self.splash_timer = 0.30
                        if self.total_strokes >= self.MAX_TOTAL_STROKES:
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                        return

                    dist_cup = math.hypot(self.ball_x - self.cup_x, self.ball_y - self.cup_y)
                    spd = math.hypot(self.ball_vx, self.ball_vy)

                    if dist_cup < 0.72:
                        if spd <= 12.8:
                            pts = max(20, 150 - self.hole_strokes * 20)
                            self._add_score(pts)
                            self.sink_flash_timer = 0.30
                            self.ball_moving = False
                            self.ball_vx = 0.0
                            self.ball_vy = 0.0
                            self.hole_index += 1

                            if self.hole_index >= self.TOTAL_HOLES:
                                self._state = (
                                    STATE_VICTORY
                                    if self.total_strokes <= self.MAX_TOTAL_STROKES
                                    else STATE_GAMEOVER
                                )
                                self.state_timer = 0.0
                                return

                            if self.total_strokes >= self.MAX_TOTAL_STROKES:
                                self._state = STATE_GAMEOVER
                                self.state_timer = 0.0
                                return

                            self.load_hole(self.hole_index)
                            return
                        else:
                            self.ball_vx *= 0.55
                            self.ball_vy *= 0.55

                    decel = 22.0 if self.tiles[gy][gx] == GOLF_SAND else 6.0
                    if spd > 0.0:
                        new_spd = spd - decel * sub_dt
                        if new_spd <= 0.30:
                            self.ball_vx = 0.0
                            self.ball_vy = 0.0
                            self.ball_moving = False
                            if self.total_strokes >= self.MAX_TOTAL_STROKES:
                                self._state = STATE_GAMEOVER
                                self.state_timer = 0.0
                            return
                        ratio = new_spd / spd
                        self.ball_vx *= ratio
                        self.ball_vy *= ratio

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

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                t = self.tiles[y][x]
                if t == GOLF_WALL:
                    wr = 145 if ((x + y) % 2 == 0) else 120
                    self._set_px(fb, x, y, wr, 78, 32)
                elif t == GOLF_SAND:
                    self._set_px(fb, x, y, 235, 200, 85)
                elif t == GOLF_WATER:
                    wb = 235 if ((int(self.anim_timer * 4.0) + x + y) % 2 == 0) else 195
                    self._set_px(fb, x, y, 25, 115, wb)
                else:
                    fg = 155 if ((x + y) % 2 == 0) else 138
                    if self.sink_flash_timer > 0.0:
                        fg = 210
                    self._set_px(fb, x, y, 32, fg, 55)

        cx = int(math.floor(self.cup_x))
        cy = int(math.floor(self.cup_y))
        self._set_px(fb, cx, cy, 15, 20, 15)
        self._set_px(fb, cx, cy - 1, 245, 45, 45)

        if self._state == STATE_PLAYING and not self.ball_moving:
            rad = float(self.aim_angle) * (math.pi / 8.0)
            dots = 2 + self.power_level
            colors = ((80, 230, 255), (255, 220, 40), (255, 85, 30))
            ar, ag, ab = colors[self.power_level]
            for d in range(1, dots + 1):
                ax = int(math.floor(self.ball_x + math.cos(rad) * float(d) * 1.15))
                ay = int(math.floor(self.ball_y + math.sin(rad) * float(d) * 1.15))
                if 0 < ax < 15 and 0 < ay < 15 and self.tiles[ay][ax] != GOLF_WALL:
                    self._set_px(fb, ax, ay, ar, ag, ab)
                else:
                    break

        bx = int(math.floor(self.ball_x))
        by = int(math.floor(self.ball_y))
        if self.splash_timer > 0.0:
            self._set_px(fb, bx, by, 140, 220, 255)
        else:
            self._set_px(fb, bx, by, 255, 255, 255)

        for h in range(self.TOTAL_HOLES):
            if h < self.hole_index:
                self._set_px(fb, 1 + h, 0, 46, 230, 113)
            elif h == self.hole_index:
                self._set_px(fb, 1 + h, 0, 255, 215, 0)

        rem = max(0, self.MAX_TOTAL_STROKES - self.total_strokes)
        bars = (rem + 2) // 3
        for b in range(min(6, bars)):
            self._set_px(fb, 14 - b, 0, 0, 215, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        rem = max(0, self.MAX_TOTAL_STROKES - self.total_strokes)
        lives = 0 if (self._state == STATE_GAMEOVER or rem <= 0) else rem
        prog = min(100, (self.hole_index * 100) // self.TOTAL_HOLES)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": lives,
            "state": self._state,
            "progress": prog,
        }
