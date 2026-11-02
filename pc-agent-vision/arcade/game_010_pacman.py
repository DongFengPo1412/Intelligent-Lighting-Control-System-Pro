# -*- coding: utf-8 -*-
"""
game_010_pacman.py —— 像素吃豆人 1980 (Pac-Man 1980)
编号: #010
年代: 1980 (南梦宫 Namco / 岩谷彻 Toru Iwatani)
核心独占机制: 迷宫全豆漫游吞食 + 左右穿梭隧道 + 四向巡逻幽灵 + 大能量豆反噬逃跑态
手柄类型: CTRL_DPAD_4WAY (上下左右四向移动)
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_DPAD_4WAY,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

GHOST_CHASE = 0
GHOST_FRIGHTENED = 1
GHOST_EATEN = 2

WALL_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,1],
    [1,0,1,1,0,1,0,0,0,0,1,0,1,1,0,1],
    [1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,0,1,1,0,0,1,1,0,1,1,0,1],
    [1,0,0,1,0,1,0,0,0,0,1,0,1,0,0,1],
    [0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0], # 隧道
    [1,0,0,1,0,1,0,0,0,0,1,0,1,0,0,1],
    [1,0,1,1,0,1,1,1,1,1,1,0,1,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,0,1,1,0,0,1,1,0,1,1,0,1],
    [1,0,0,1,0,0,0,1,1,0,0,0,1,0,0,1],
    [1,1,0,1,0,1,0,0,0,0,1,0,1,0,1,1],
    [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

class Ghost:
    def __init__(self, x: float, y: float, dir_x: int, dir_y: int, r: int, g: int, b: int, speed: float):
        self.x = x
        self.y = y
        self.dir_x = dir_x
        self.dir_y = dir_y
        self.state = GHOST_CHASE
        self.r = r
        self.g = g
        self.b = b
        self.speed = speed

class Game010Pacman(BaseCartridge):
    def __init__(self):
        self._id = 10
        self._name = "像素吃豆人"
        self._english_name = "Pac-Man 1980"
        self._year = 1980
        self._control_type = CTRL_DPAD_4WAY
        self._core_mechanic = "迷宫全豆漫游吞食 + 左右穿梭隧道 + 四向巡逻幽灵 + 大能量豆反噬逃跑态"

        self.state = STATE_TITLE
        self.pac_x = 8.0
        self.pac_y = 10.0
        self.pac_dir_x = 0
        self.pac_dir_y = 0
        self.desired_dir_x = 0
        self.desired_dir_y = 0

        self.ghosts: List[Ghost] = []
        self.frightened_timer = 0.0

        self.grid: List[List[int]] = []
        self.remaining_dots = 0

        self.lives = 3
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)

        self.reset()

    @property
    def game_id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def english_name(self) -> str:
        return self._english_name

    @property
    def release_year(self) -> int:
        return self._year

    @property
    def control_type(self) -> int:
        return self._control_type

    @property
    def core_mechanic(self) -> str:
        return self._core_mechanic

    def is_wall(self, x: int, y: int) -> bool:
        if y == 7 and (x < 0 or x >= 16):
            return False
        if x < 0 or x >= 16 or y < 0 or y >= 16:
            return True
        return WALL_MAP[y][x] == 1

    def reset_positions(self):
        self.pac_x = 8.0
        self.pac_y = 10.0
        self.pac_dir_x = 0
        self.pac_dir_y = 0
        self.desired_dir_x = 0
        self.desired_dir_y = 0

        self.ghosts = [
            Ghost(7.0, 6.0, 1, 0, 231, 76, 60, 4.0),     # Blinky (红)
            Ghost(8.0, 7.0, -1, 0, 255, 105, 180, 3.8),  # Pinky (粉)
            Ghost(7.0, 8.0, 0, 1, 0, 255, 255, 3.6),     # Inky (青)
        ]
        self.frightened_timer = 0.0

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.remaining_dots = 0

        self.grid = []
        for y in range(16):
            row = []
            for x in range(16):
                if WALL_MAP[y][x] == 0:
                    if (6 <= x <= 9 and 6 <= y <= 8) or (x == 8 and y == 10):
                        row.append(0)
                    elif (x == 1 and y == 1) or (x == 14 and y == 1) or \
                         (x == 1 and y == 14) or (x == 14 and y == 14):
                        row.append(2) # 大力丸
                        self.remaining_dots += 1
                    else:
                        row.append(1) # 普通豆
                        self.remaining_dots += 1
                else:
                    row.append(0)
            self.grid.append(row)

        self.reset_positions()

    def move_ghost(self, g: Ghost, dt: float):
        move_step = g.speed * dt
        if g.state == GHOST_FRIGHTENED:
            move_step *= 0.55

        cur_gx = int(round(g.x))
        cur_gy = int(round(g.y))
        dist_to_center = abs(g.x - cur_gx) + abs(g.y - cur_gy)

        if dist_to_center < 0.12:
            g.x = float(cur_gx)
            g.y = float(cur_gy)

            dxs = [0, 0, -1, 1]
            dys = [-1, 1, 0, 0]
            best_dir = -1
            best_metric = -1e9 if g.state == GHOST_FRIGHTENED else 1e9

            for i in range(4):
                if dxs[i] == -g.dir_x and dys[i] == -g.dir_y and (g.dir_x != 0 or g.dir_y != 0):
                    continue

                nx = cur_gx + dxs[i]
                ny = cur_gy + dys[i]

                if not self.is_wall(nx, ny):
                    dist = (nx - self.pac_x) ** 2 + (ny - self.pac_y) ** 2
                    if g.state == GHOST_FRIGHTENED:
                        if dist > best_metric:
                            best_metric = dist
                            best_dir = i
                    else:
                        if dist < best_metric:
                            best_metric = dist
                            best_dir = i

            if best_dir != -1:
                g.dir_x = dxs[best_dir]
                g.dir_y = dys[best_dir]
            else:
                g.dir_x = -g.dir_x
                g.dir_y = -g.dir_y

        g.x += g.dir_x * move_step
        g.y += g.dir_y * move_step

        if g.x < 0.0:
            g.x = 15.0
        elif g.x > 15.0:
            g.x = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)):
                self.reset()
            return

        if self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            if keys_down & KEY_UP:
                self.desired_dir_x, self.desired_dir_y = 0, -1
            elif keys_down & KEY_DOWN:
                self.desired_dir_x, self.desired_dir_y = 0, 1
            elif keys_down & KEY_LEFT:
                self.desired_dir_x, self.desired_dir_y = -1, 0
            elif keys_down & KEY_RIGHT:
                self.desired_dir_x, self.desired_dir_y = 1, 0

            cur_px = int(round(self.pac_x))
            cur_py = int(round(self.pac_y))
            p_dist = abs(self.pac_x - cur_px) + abs(self.pac_y - cur_py)

            if (self.desired_dir_x == -self.pac_dir_x and self.desired_dir_y == -self.pac_dir_y and
                (self.desired_dir_x != 0 or self.desired_dir_y != 0)):
                self.pac_dir_x = self.desired_dir_x
                self.pac_dir_y = self.desired_dir_y
            elif p_dist < 0.2 and (self.desired_dir_x != self.pac_dir_x or self.desired_dir_y != self.pac_dir_y):
                next_x = cur_px + self.desired_dir_x
                next_y = cur_py + self.desired_dir_y
                if not self.is_wall(next_x, next_y):
                    self.pac_x = float(cur_px)
                    self.pac_y = float(cur_py)
                    self.pac_dir_x = self.desired_dir_x
                    self.pac_dir_y = self.desired_dir_y

            fwd_x = cur_px + self.pac_dir_x
            fwd_y = cur_py + self.pac_dir_y
            if self.is_wall(fwd_x, fwd_y) and p_dist < 0.1:
                self.pac_x = float(cur_px)
                self.pac_y = float(cur_py)
                self.pac_dir_x = 0
                self.pac_dir_y = 0

            pac_speed = 4.8
            self.pac_x += self.pac_dir_x * pac_speed * dt
            self.pac_y += self.pac_dir_y * pac_speed * dt

            if self.pac_x < 0.0:
                self.pac_x = 15.0
            elif self.pac_x > 15.0:
                self.pac_x = 0.0

            # 吞豆
            eat_x = int(round(self.pac_x))
            eat_y = int(round(self.pac_y))
            if 0 <= eat_x < 16 and 0 <= eat_y < 16:
                if self.grid[eat_y][eat_x] == 1:
                    self.grid[eat_y][eat_x] = 0
                    self.remaining_dots -= 1
                    self.score += 10
                    if self.score > self.high_score:
                        self.high_score = self.score
                elif self.grid[eat_y][eat_x] == 2:
                    self.grid[eat_y][eat_x] = 0
                    self.remaining_dots -= 1
                    self.score += 50
                    if self.score > self.high_score:
                        self.high_score = self.score
                    self.frightened_timer = 6.0
                    for g in self.ghosts:
                        g.state = GHOST_FRIGHTENED

            if self.remaining_dots <= 0:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                return

            if self.frightened_timer > 0.0:
                self.frightened_timer -= dt
                if self.frightened_timer <= 0.0:
                    self.frightened_timer = 0.0
                    for g in self.ghosts:
                        g.state = GHOST_CHASE

            # 幽灵
            for g in self.ghosts:
                self.move_ghost(g, dt)

                dist = abs(self.pac_x - g.x) + abs(self.pac_y - g.y)
                if dist < 0.75:
                    if g.state == GHOST_FRIGHTENED:
                        self.score += 200
                        if self.score > self.high_score:
                            self.high_score = self.score
                        g.x = 7.5
                        g.y = 7.0
                        g.state = GHOST_CHASE
                    else:
                        if self.lives > 0:
                            self.lives -= 1
                        if self.lives == 0:
                            self.state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        else:
                            self.reset_positions()
                            return

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        # 迷宫与豆子
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if WALL_MAP[y][x] == 1:
                    self.frame_buffer[idx:idx+3] = bytes([25, 42, 86])
                else:
                    val = self.grid[y][x]
                    if val == 1:
                        self.frame_buffer[idx:idx+3] = bytes([243, 156, 18])
                    elif val == 2:
                        self.frame_buffer[idx:idx+3] = bytes([255, 255, 220])

        # 幽灵
        for g in self.ghosts:
            gx = int(round(g.x))
            gy = int(round(g.y))
            if 0 <= gx < 16 and 0 <= gy < 16:
                idx = (gy * 16 + gx) * 3
                if g.state == GHOST_FRIGHTENED:
                    if self.frightened_timer < 1.5 and (int(self.frightened_timer * 6.0) % 2 == 0):
                        color = [236, 240, 241]
                    else:
                        color = [41, 128, 185]
                    self.frame_buffer[idx:idx+3] = bytes(color)
                else:
                    self.frame_buffer[idx:idx+3] = bytes([g.r, g.g, g.b])

        # 吃豆人
        px = int(round(self.pac_x))
        py = int(round(self.pac_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 242, 0])

        # 生命
        for i in range(self.lives):
            idx = (0 * 16 + (i * 2 + 1)) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 242, 0])

        # 胜负
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "remaining_dots": self.remaining_dots,
            "frightened_timer": self.frightened_timer,
        }
