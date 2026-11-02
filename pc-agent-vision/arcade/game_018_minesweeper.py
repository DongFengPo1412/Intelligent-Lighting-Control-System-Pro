# -*- coding: utf-8 -*-
"""
game_018_minesweeper.py —— 像素扫雷 1990 (Minesweeper 1990)
编号: #018
年代: 1990 (微软 Microsoft / Robert Donner & Curt Johnson)
核心独占机制: 网格光标探测 + 首按防爆生成 + 洪水填充零区翻开 + 八邻域计数与插旗
手柄类型: CTRL_ARCADE_AB (四向移动光标 + A 翻开 / B 插旗)
"""

import random
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
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

class MineCell:
    def __init__(self):
        self.has_mine = False
        self.revealed = False
        self.flagged = False
        self.neighbor_mines = 0

class Game018Minesweeper(BaseCartridge):
    def __init__(self):
        self._id = 18
        self._name = "像素扫雷"
        self._english_name = "Minesweeper 1990"
        self._year = 1990
        self._control_type = CTRL_ARCADE_AB
        self._core_mechanic = "网格光标探测 + 首按防爆生成 + 洪水填充零区翻开 + 八邻域计数与插旗"

        self.k_total_mines = 25
        self.state = STATE_TITLE
        self.cursor_x = 7
        self.cursor_y = 7
        self.first_click = True
        self.remaining_hidden_safe = 256 - self.k_total_mines
        self.flags_placed = 0

        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0
        self.cursor_blink_timer = 0.0

        self.grid: List[List[MineCell]] = []
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

    def generate_mines(self, safe_x: int, safe_y: int):
        placed = 0
        while placed < self.k_total_mines:
            rx = random.randint(0, 15)
            ry = random.randint(0, 15)
            if abs(rx - safe_x) <= 1 and abs(ry - safe_y) <= 1:
                continue
            if not self.grid[ry][rx].has_mine:
                self.grid[ry][rx].has_mine = True
                placed += 1

        for y in range(16):
            for x in range(16):
                if self.grid[y][x].has_mine:
                    continue
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < 16 and 0 <= ny < 16:
                            if self.grid[ny][nx].has_mine:
                                cnt += 1
                self.grid[y][x].neighbor_mines = cnt

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.cursor_x = 7
        self.cursor_y = 7
        self.first_click = True
        self.flags_placed = 0
        self.remaining_hidden_safe = 256 - self.k_total_mines
        self.cursor_blink_timer = 0.0

        self.grid = [[MineCell() for _ in range(16)] for _ in range(16)]

    def reveal(self, x: int, y: int):
        if not (0 <= x < 16 and 0 <= y < 16):
            return
        cell = self.grid[y][x]
        if cell.revealed or cell.flagged:
            return

        if cell.has_mine:
            self.state = STATE_GAMEOVER
            self.state_timer = 0.0
            for ry in range(16):
                for rx in range(16):
                    if self.grid[ry][rx].has_mine:
                        self.grid[ry][rx].revealed = True
            return

        cell.revealed = True
        self.remaining_hidden_safe -= 1
        self.score += 10
        if self.score > self.high_score:
            self.high_score = self.score

        if cell.neighbor_mines == 0:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx != 0 or dy != 0:
                        self.reveal(x + dx, y + dy)

        if self.remaining_hidden_safe <= 0:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 500
            if self.score > self.high_score:
                self.high_score = self.score

    def toggle_flag(self, x: int, y: int):
        if not (0 <= x < 16 and 0 <= y < 16):
            return
        cell = self.grid[y][x]
        if cell.revealed:
            return
        cell.flagged = not cell.flagged
        if cell.flagged:
            self.flags_placed += 1
        else:
            self.flags_placed -= 1

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.cursor_blink_timer += dt
        if self.cursor_blink_timer >= 0.6:
            self.cursor_blink_timer -= 0.6

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

            if keys_pressed & KEY_UP:
                self.cursor_y = max(0, self.cursor_y - 1)
            elif keys_pressed & KEY_DOWN:
                self.cursor_y = min(15, self.cursor_y + 1)
            elif keys_pressed & KEY_LEFT:
                self.cursor_x = max(0, self.cursor_x - 1)
            elif keys_pressed & KEY_RIGHT:
                self.cursor_x = min(15, self.cursor_x + 1)

            if keys_pressed & KEY_A:
                if self.first_click:
                    self.generate_mines(self.cursor_x, self.cursor_y)
                    self.first_click = False
                self.reveal(self.cursor_x, self.cursor_y)

            if keys_pressed & KEY_B:
                self.toggle_flag(self.cursor_x, self.cursor_y)

    def render(self) -> bytes:
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                cell = self.grid[y][x]
                if not cell.revealed:
                    if cell.flagged:
                        color = (241, 196, 15) # 插旗黄
                    else:
                        color = (70, 80, 95)   # 蓝灰未翻开
                else:
                    if cell.has_mine:
                        color = (231, 76, 60)  # 地雷红
                    else:
                        c_map = {
                            0: (35, 35, 40),
                            1: (52, 152, 219),
                            2: (46, 204, 113),
                            3: (231, 76, 60),
                            4: (155, 89, 182),
                        }
                        color = c_map.get(cell.neighbor_mines, (243, 156, 18))
                self.frame_buffer[idx:idx+3] = bytes(color)

        if self.cursor_blink_timer < 0.35 and self.state == STATE_PLAYING:
            idx = (self.cursor_y * 16 + self.cursor_x) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 255, 255])

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
        total_safe = 256 - self.k_total_mines
        return {
            "score": self.score,
            "state": self.state,
            "cursor": (self.cursor_x, self.cursor_y),
            "flags_placed": self.flags_placed,
            "progress": int(((total_safe - self.remaining_hidden_safe) * 100) / total_safe),
        }
