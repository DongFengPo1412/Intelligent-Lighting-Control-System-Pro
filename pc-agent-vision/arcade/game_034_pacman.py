"""game_034_pacman.py —— 目标 #034 吃豆人 (Pac-Man 1980)
16x16 迷宫全豆漫游吞食 + 左右穿梭隧道 + 三色巡逻幽灵 + 大能量豆反噬逃跑态
"""

import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
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

WALL_MAP = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1],
    [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1],
    [1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1],
    [1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]


class Ghost:
    def __init__(self, x: float, y: float, r: int, g: int, b: int, speed: float):
        self.x = x
        self.y = y
        self.dir_x = 1
        self.dir_y = 0
        self.is_frightened = False
        self.r = r
        self.g = g
        self.b = b
        self.speed = speed


class Game034Pacman(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.pac_x = 8.0
        self.pac_y = 10.0
        self.pac_dir_x = 0
        self.pac_dir_y = 0
        self.desired_dir_x = 0
        self.desired_dir_y = 0
        self.ghosts: List[Ghost] = []
        self.frightened_timer = 0.0
        self.grid = [[0] * 16 for _ in range(16)]
        self.remaining_dots = 0
        self.total_dots = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 34

    @property
    def name(self) -> str:
        return "吃豆人"

    @property
    def english_name(self) -> str:
        return "Pac-Man 1980"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "迷宫巡航吞豆与幽灵能量反噬"

    def init(self) -> None:
        self.reset()

    def _is_wall(self, x: int, y: int) -> bool:
        if y == 7 and (x < 0 or x >= 16):
            return False
        if x < 0 or x >= 16 or y < 0 or y >= 16:
            return True
        return WALL_MAP[y][x] == 1

    def _reset_positions(self):
        self.pac_x = 8.0
        self.pac_y = 10.0
        self.pac_dir_x = 0
        self.pac_dir_y = 0
        self.desired_dir_x = 0
        self.desired_dir_y = 0
        self.ghosts = [
            Ghost(7.0, 6.0, 231, 76, 60, 4.0),
            Ghost(8.0, 7.0, 255, 105, 180, 3.8),
            Ghost(7.0, 8.0, 0, 255, 255, 3.6),
        ]
        self.frightened_timer = 0.0

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.remaining_dots = 0

        self.grid = [[0] * 16 for _ in range(16)]
        for y in range(16):
            for x in range(16):
                if WALL_MAP[y][x] == 0:
                    if (6 <= x <= 9 and 6 <= y <= 8) or (x == 8 and y == 10):
                        self.grid[y][x] = 0
                    elif (x, y) in ((1, 1), (14, 1), (1, 14), (14, 14)):
                        self.grid[y][x] = 2
                        self.remaining_dots += 1
                    else:
                        self.grid[y][x] = 1
                        self.remaining_dots += 1
        self.total_dots = self.remaining_dots
        self._reset_positions()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.remaining_dots = 0
            self.grid = [[0] * 16 for _ in range(16)]
            for y in range(16):
                for x in range(16):
                    if WALL_MAP[y][x] == 0:
                        if (6 <= x <= 9 and 6 <= y <= 8) or (x == 8 and y == 10):
                            self.grid[y][x] = 0
                        elif (x, y) in ((1, 1), (14, 1), (1, 14), (14, 14)):
                            self.grid[y][x] = 2
                            self.remaining_dots += 1
                        else:
                            self.grid[y][x] = 1
                            self.remaining_dots += 1
            self.total_dots = self.remaining_dots
            self._reset_positions()

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _move_ghost(self, g: Ghost, dt: float):
        move_step = g.speed * dt * (0.55 if g.is_frightened else 1.0)
        cur_gx = int(round(g.x))
        cur_gy = int(round(g.y))

        if abs(g.x - cur_gx) < move_step and abs(g.y - cur_gy) < move_step:
            g.x = float(cur_gx)
            g.y = float(cur_gy)
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            valid = []
            for ndx, ndy in dirs:
                if ndx == -g.dir_x and ndy == -g.dir_y:
                    continue
                if not self._is_wall(cur_gx + ndx, cur_gy + ndy):
                    valid.append((ndx, ndy))
            if valid:
                g.dir_x, g.dir_y = random.choice(valid)
            else:
                g.dir_x, g.dir_y = -g.dir_x, -g.dir_y

        g.x += g.dir_x * move_step
        g.y += g.dir_y * move_step

        if cur_gy == 7:
            if g.x < -0.5:
                g.x = 15.5
            elif g.x > 15.5:
                g.x = -0.5

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
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

            if keys_down & KEY_UP:
                self.desired_dir_x, self.desired_dir_y = 0, -1
            elif keys_down & KEY_DOWN:
                self.desired_dir_x, self.desired_dir_y = 0, 1
            elif keys_down & KEY_LEFT:
                self.desired_dir_x, self.desired_dir_y = -1, 0
            elif keys_down & KEY_RIGHT:
                self.desired_dir_x, self.desired_dir_y = 1, 0

            gx, gy = int(round(self.pac_x)), int(round(self.pac_y))
            if self.desired_dir_x != self.pac_dir_x or self.desired_dir_y != self.pac_dir_y:
                if self.desired_dir_x == -self.pac_dir_x and self.desired_dir_y == -self.pac_dir_y and (self.pac_dir_x != 0 or self.pac_dir_y != 0):
                    self.pac_dir_x = self.desired_dir_x
                    self.pac_dir_y = self.desired_dir_y
                elif abs(self.pac_x - gx) < 0.25 and abs(self.pac_y - gy) < 0.25:
                    if not self._is_wall(gx + self.desired_dir_x, gy + self.desired_dir_y):
                        self.pac_x = float(gx)
                        self.pac_y = float(gy)
                        self.pac_dir_x = self.desired_dir_x
                        self.pac_dir_y = self.desired_dir_y

            pac_speed = 4.8
            move_step = pac_speed * dt
            if not self._is_wall(gx + self.pac_dir_x, gy + self.pac_dir_y) or (
                (self.pac_dir_x > 0 and self.pac_x < gx)
                or (self.pac_dir_x < 0 and self.pac_x > gx)
                or (self.pac_dir_y > 0 and self.pac_y < gy)
                or (self.pac_dir_y < 0 and self.pac_y > gy)
            ):
                self.pac_x += self.pac_dir_x * move_step
                self.pac_y += self.pac_dir_y * move_step
            else:
                self.pac_x = float(gx)
                self.pac_y = float(gy)

            if gy == 7:
                if self.pac_x < -0.5:
                    self.pac_x = 15.5
                elif self.pac_x > 15.5:
                    self.pac_x = -0.5

            cur_x, cur_y = int(round(self.pac_x)), int(round(self.pac_y))
            if 0 <= cur_x < 16 and 0 <= cur_y < 16:
                if self.grid[cur_y][cur_x] == 1:
                    self.grid[cur_y][cur_x] = 0
                    self._score += 10
                    self.remaining_dots -= 1
                elif self.grid[cur_y][cur_x] == 2:
                    self.grid[cur_y][cur_x] = 0
                    self._score += 50
                    self.remaining_dots -= 1
                    self.frightened_timer = 6.0
                    for g in self.ghosts:
                        g.is_frightened = True

                if self._score > self._high_score:
                    self._high_score = self._score

                if self.remaining_dots <= 0:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                    return

            if self.frightened_timer > 0.0:
                self.frightened_timer -= dt
                if self.frightened_timer <= 0.0:
                    for g in self.ghosts:
                        g.is_frightened = False

            for g in self.ghosts:
                self._move_ghost(g, dt)
                if abs(g.x - self.pac_x) < 0.8 and abs(g.y - self.pac_y) < 0.8:
                    if g.is_frightened:
                        g.x = 7.0
                        g.y = 7.0
                        g.is_frightened = False
                        self._score += 200
                        if self._score > self._high_score:
                            self._high_score = self._score
                    else:
                        if self.lives > 1:
                            self.lives -= 1
                            self._reset_positions()
                        else:
                            self.lives = 0
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if WALL_MAP[y][x] == 1:
                    fb[idx : idx + 3] = bytes([33, 66, 180])
                elif self.grid[y][x] == 1:
                    fb[idx : idx + 3] = bytes([255, 184, 151])
                elif self.grid[y][x] == 2:
                    fb[idx : idx + 3] = bytes([255, 255, 255])

        px, py = int(round(self.pac_x)), int(round(self.pac_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx : idx + 3] = bytes([255, 255, 0])

        for g in self.ghosts:
            gx, gy = int(round(g.x)), int(round(g.y))
            if 0 <= gx < 16 and 0 <= gy < 16:
                idx = (gy * 16 + gx) * 3
                if g.is_frightened:
                    fb[idx : idx + 3] = bytes([30, 60, 220])
                else:
                    fb[idx : idx + 3] = bytes([g.r, g.g, g.b])

        if self._state == STATE_PAUSED:
            for y in range(6, 10):
                for col in (6, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([250, 250, 250])

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (self.total_dots - self.remaining_dots) * 100 // max(1, self.total_dots)),
        }
