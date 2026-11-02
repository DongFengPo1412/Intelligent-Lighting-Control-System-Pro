# -*- coding: utf-8 -*-
"""
game_015_tron.py —— 创战纪光轮摩托 1982 (Tron Light Cycles 1982)
编号: #015
年代: 1982 (Bally Midway / 迪士尼电影同名街机)
核心独占机制: 极速永久固体光痕堵路 + 90度瞬时折角 + 封闭竞技场智能诱导对决
手柄类型: CTRL_DPAD_4WAY (90度瞬时转向，不可后退逆行)
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    CTRL_DPAD_4WAY,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

TRON_NONE = 0
TRON_WALL = 1
TRON_P1 = 2
TRON_P2_AI = 3

class LightCycle:
    def __init__(self, x: int, y: int, dir_x: int, dir_y: int, r: int, g: int, b: int):
        self.x = x
        self.y = y
        self.dir_x = dir_x
        self.dir_y = dir_y
        self.alive = True
        self.r = r
        self.g = g
        self.b = b

class Game015Tron(BaseCartridge):
    def __init__(self):
        self._id = 15
        self._name = "创战纪光轮摩托"
        self._english_name = "Tron Light Cycles 1982"
        self._year = 1982
        self._control_type = CTRL_DPAD_4WAY
        self._core_mechanic = "极速永久固体光痕堵路 + 90度瞬时折角 + 封闭竞技场智能诱导对决"

        self.k_target_wins = 3
        self.state = STATE_TITLE
        self.p1_wins = 0
        self.p2_wins = 0
        self.step_timer = 0.0
        self.step_interval = 0.12
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0

        self.grid: List[List[int]] = []
        self.p1 = LightCycle(3, 8, 1, 0, 0, 255, 255)
        self.p2 = LightCycle(12, 8, -1, 0, 230, 126, 34)

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

    def reset_round(self):
        self.grid = [[TRON_NONE for _ in range(16)] for _ in range(16)]

        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    self.grid[y][x] = TRON_WALL

        self.p1 = LightCycle(3, 8, 1, 0, 0, 255, 255)
        self.grid[8][3] = TRON_P1

        self.p2 = LightCycle(12, 8, -1, 0, 230, 126, 34)
        self.grid[8][12] = TRON_P2_AI

        self.step_timer = 0.0

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.p1_wins = 0
        self.p2_wins = 0
        self.score = 0
        self.state_timer = 0.0
        self.step_interval = 0.12
        self.reset_round()

    def step_ai(self):
        fwd_x = self.p2.x + self.p2.dir_x
        fwd_y = self.p2.y + self.p2.dir_y
        forward_blocked = (self.grid[fwd_y][fwd_x] != TRON_NONE)

        cand_dx = [-self.p2.dir_y, self.p2.dir_y]
        cand_dy = [self.p2.dir_x, -self.p2.dir_x]

        if forward_blocked:
            best_dir = -1
            max_space = -1
            for i in range(2):
                test_x = self.p2.x + cand_dx[i]
                test_y = self.p2.y + cand_dy[i]
                if self.grid[test_y][test_x] == TRON_NONE:
                    space = 0
                    px, py = test_x, test_y
                    while self.grid[py][px] == TRON_NONE and space < 8:
                        space += 1
                        px += cand_dx[i]
                        py += cand_dy[i]
                    if space > max_space:
                        max_space = space
                        best_dir = i

            if best_dir != -1:
                self.p2.dir_x = cand_dx[best_dir]
                self.p2.dir_y = cand_dy[best_dir]
        else:
            cand_dir = 1 if self.p1.y > self.p2.y else 0
            test_x = self.p2.x + cand_dx[cand_dir]
            test_y = self.p2.y + cand_dy[cand_dir]
            if self.grid[test_y][test_x] == TRON_NONE and (self.p2.x % 4 == 0):
                self.p2.dir_x = cand_dx[cand_dir]
                self.p2.dir_y = cand_dy[cand_dir]

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)):
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

            if (keys_pressed & KEY_UP) and self.p1.dir_y != 1:
                self.p1.dir_x, self.p1.dir_y = 0, -1
            elif (keys_pressed & KEY_DOWN) and self.p1.dir_y != -1:
                self.p1.dir_x, self.p1.dir_y = 0, 1
            elif (keys_pressed & KEY_LEFT) and self.p1.dir_x != 1:
                self.p1.dir_x, self.p1.dir_y = -1, 0
            elif (keys_pressed & KEY_RIGHT) and self.p1.dir_x != -1:
                self.p1.dir_x, self.p1.dir_y = 1, 0

            self.step_timer += dt
            if self.step_timer >= self.step_interval:
                self.step_timer = 0.0

                self.step_ai()

                p1_nx = self.p1.x + self.p1.dir_x
                p1_ny = self.p1.y + self.p1.dir_y

                p2_nx = self.p2.x + self.p2.dir_x
                p2_ny = self.p2.y + self.p2.dir_y

                p1_crashed = (self.grid[p1_ny][p1_nx] != TRON_NONE)
                p2_crashed = (self.grid[p2_ny][p2_nx] != TRON_NONE)

                if p1_nx == p2_nx and p1_ny == p2_ny:
                    p1_crashed = True
                    p2_crashed = True

                if p1_crashed or p2_crashed:
                    if p1_crashed and p2_crashed:
                        self.reset_round()
                    elif p1_crashed:
                        self.p2_wins += 1
                        if self.p2_wins >= self.k_target_wins:
                            self.state = STATE_GAMEOVER
                            self.state_timer = 0.0
                        else:
                            self.reset_round()
                    else:
                        self.p1_wins += 1
                        self.score += 100
                        if self.score > self.high_score:
                            self.high_score = self.score
                        if self.p1_wins >= self.k_target_wins:
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                        else:
                            self.reset_round()
                    return

                self.p1.x, self.p1.y = p1_nx, p1_ny
                self.grid[self.p1.y][self.p1.x] = TRON_P1

                self.p2.x, self.p2.y = p2_nx, p2_ny
                self.grid[self.p2.y][self.p2.x] = TRON_P2_AI

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                cell = self.grid[y][x]
                if cell == TRON_WALL:
                    self.frame_buffer[idx:idx+3] = bytes([142, 68, 173])
                elif cell == TRON_P1:
                    self.frame_buffer[idx:idx+3] = bytes([0, 200, 255])
                elif cell == TRON_P2_AI:
                    self.frame_buffer[idx:idx+3] = bytes([230, 126, 34])

        idx_p1 = (self.p1.y * 16 + self.p1.x) * 3
        self.frame_buffer[idx_p1:idx_p1+3] = bytes([255, 255, 255])

        idx_p2 = (self.p2.y * 16 + self.p2.x) * 3
        self.frame_buffer[idx_p2:idx_p2+3] = bytes([255, 242, 0])

        for i in range(self.p1_wins):
            idx = (0 * 16 + (i + 1)) * 3
            self.frame_buffer[idx:idx+3] = bytes([0, 255, 255])
        for i in range(self.p2_wins):
            idx = (0 * 16 + (14 - i)) * 3
            self.frame_buffer[idx:idx+3] = bytes([230, 126, 34])

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
            "p1_wins": self.p1_wins,
            "p2_wins": self.p2_wins,
            "score": self.score,
            "state": self.state,
            "progress": int((self.p1_wins * 100) / self.k_target_wins),
        }
