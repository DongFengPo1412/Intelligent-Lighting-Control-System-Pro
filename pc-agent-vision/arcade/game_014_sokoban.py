# -*- coding: utf-8 -*-
"""
game_014_sokoban.py —— 经典推箱子 1982 (Sokoban 1982)
编号: #014
年代: 1982 (Thinking Rabbit / 今林宏行 Hiroyuki Imabayashi)
核心独占机制: 空间槽位单向推移不可拉动 + 死角死锁状态不可逆 + 逻辑闭环归位
手柄类型: CTRL_DPAD_4WAY (上下左右离散步进)
"""

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

SOKOBAN_FLOOR = 0
SOKOBAN_WALL = 1
SOKOBAN_GOAL = 2

class SokobanBox:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

class Game014Sokoban(BaseCartridge):
    def __init__(self):
        self._id = 14
        self._name = "经典推箱子"
        self._english_name = "Sokoban 1982"
        self._year = 1982
        self._control_type = CTRL_DPAD_4WAY
        self._core_mechanic = "空间槽位单向推移不可拉动 + 死角死锁状态不可逆 + 逻辑闭环归位"

        self.k_num_boxes = 4
        self.state = STATE_TITLE
        self.player_x = 7
        self.player_y = 8
        self.moves = 0
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0

        self.map: List[List[int]] = []
        self.boxes: List[SokobanBox] = []
        self.boxes_on_goal = 0

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

    def find_box_at(self, x: int, y: int) -> int:
        for i, b in enumerate(self.boxes):
            if b.x == x and b.y == y:
                return i
        return -1

    def is_goal(self, x: int, y: int) -> bool:
        if x < 0 or x >= 16 or y < 0 or y >= 16:
            return False
        return self.map[y][x] == SOKOBAN_GOAL

    def reset_level(self):
        self.map = [[SOKOBAN_FLOOR for _ in range(16)] for _ in range(16)]

        # 外围
        for y in range(16):
            for x in range(16):
                if x < 2 or x > 13 or y < 2 or y > 13:
                    self.map[y][x] = SOKOBAN_WALL

        # 仓库四壁
        for x in range(2, 14):
            self.map[2][x] = SOKOBAN_WALL
            self.map[13][x] = SOKOBAN_WALL
        for y in range(2, 14):
            self.map[y][2] = SOKOBAN_WALL
            self.map[y][13] = SOKOBAN_WALL

        # 结构柱
        self.map[5][8] = SOKOBAN_WALL
        self.map[6][8] = SOKOBAN_WALL
        self.map[9][7] = SOKOBAN_WALL
        self.map[10][7] = SOKOBAN_WALL

        # 目标槽位
        self.map[4][4] = SOKOBAN_GOAL
        self.map[4][5] = SOKOBAN_GOAL
        self.map[11][10] = SOKOBAN_GOAL
        self.map[11][11] = SOKOBAN_GOAL

        # 箱子
        self.boxes = [
            SokobanBox(5, 6),
            SokobanBox(6, 6),
            SokobanBox(9, 9),
            SokobanBox(10, 9),
        ]

        self.player_x = 7
        self.player_y = 8
        self.moves = 0
        self.check_victory()

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.reset_level()

    def check_victory(self):
        on_goal = 0
        for b in self.boxes:
            if self.is_goal(b.x, b.y):
                on_goal += 1
        self.boxes_on_goal = on_goal

        if self.boxes_on_goal == self.k_num_boxes:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score = max(100, 1000 - (self.moves * 5))
            if self.score > self.high_score:
                self.high_score = self.score

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

            if keys_pressed & (KEY_A | KEY_B):
                self.reset_level()
                return

            dx, dy = 0, 0
            if keys_pressed & KEY_UP: dy = -1
            elif keys_pressed & KEY_DOWN: dy = 1
            elif keys_pressed & KEY_LEFT: dx = -1
            elif keys_pressed & KEY_RIGHT: dx = 1

            if dx != 0 or dy != 0:
                nx = self.player_x + dx
                ny = self.player_y + dy

                box_idx = self.find_box_at(nx, ny)
                if box_idx != -1:
                    bx2 = nx + dx
                    by2 = ny + dy
                    if self.map[by2][bx2] != SOKOBAN_WALL and self.find_box_at(bx2, by2) == -1:
                        self.boxes[box_idx].x = bx2
                        self.boxes[box_idx].y = by2
                        self.player_x = nx
                        self.player_y = ny
                        self.moves += 1
                        self.check_victory()
                elif self.map[ny][nx] != SOKOBAN_WALL:
                    self.player_x = nx
                    self.player_y = ny
                    self.moves += 1

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                tile = self.map[y][x]
                if tile == SOKOBAN_WALL:
                    self.frame_buffer[idx:idx+3] = bytes([52, 73, 94])
                elif tile == SOKOBAN_GOAL:
                    self.frame_buffer[idx:idx+3] = bytes([241, 196, 15])
                elif 2 <= x <= 13 and 2 <= y <= 13:
                    self.frame_buffer[idx:idx+3] = bytes([30, 30, 30])

        for b in self.boxes:
            if 0 <= b.x < 16 and 0 <= b.y < 16:
                idx = (b.y * 16 + b.x) * 3
                if self.is_goal(b.x, b.y):
                    self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
                else:
                    self.frame_buffer[idx:idx+3] = bytes([230, 126, 34])

        px, py = self.player_x, self.player_y
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            self.frame_buffer[idx:idx+3] = bytes([0, 255, 255])

        for i in range(self.boxes_on_goal):
            idx = (0 * 16 + (i * 2 + 1)) * 3
            self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])

        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        return {
            "moves": self.moves,
            "score": self.score,
            "state": self.state,
            "boxes_on_goal": self.boxes_on_goal,
            "progress": int((self.boxes_on_goal * 100) / self.k_num_boxes),
        }
