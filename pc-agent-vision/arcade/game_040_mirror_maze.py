# -*- coding: utf-8 -*-
"""game_040_mirror_maze.py —— 目标 #040 镜像双人迷宫 (Mirror Twins)
左右对称双生角色同步反向移动 + 不对称墙壁卡位对齐 + 陷阱躲避与双终点同时抵达
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
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

MIRROR_LEVELS = [
    [
        "################",
        "################",
        "#......##......#",
        "#....G.##..H...#",
        "#......##......#",
        "#......##......#",
        "#.X....##....X.#",
        "#......##......#",
        "#......##.#....#",
        "#......##......#",
        "#X.....##.....X#",
        "#......##......#",
        "#......##......#",
        "#.A....##....B.#",
        "#......##......#",
        "################",
    ],
    [
        "################",
        "################",
        "#......##......#",
        "#.G....##......#",
        "#......##...H..#",
        "#......##......#",
        "#X.....##.....X#",
        "#......##......#",
        "#......##..#...#",
        "#......##....#.#",
        "#......##......#",
        "#.....X##X.....#",
        "#......##......#",
        "#.A....##....B.#",
        "#......##......#",
        "################",
    ],
    [
        "################",
        "################",
        "#......##......#",
        "#......##.H....#",
        "#.G....##......#",
        "#......##......#",
        "#.....X##...X..#",
        "#......##......#",
        "#..#...##..#...#",
        "#....X.##....X.#",
        "#......##......#",
        "#......##......#",
        "#......##......#",
        "#....A.##.B#...#",
        "#......##......#",
        "################",
    ],
    [
        "################",
        "################",
        "#A.....##..#..B#",
        "#......##......#",
        "#......##......#",
        "#.X....##.X....#",
        "#......##......#",
        "#......##....#.#",
        "#......##......#",
        "#......##......#",
        "#..X...##.....X#",
        "#......##......#",
        "#......##...H..#",
        "#.X..G.##.....X#",
        "#......##......#",
        "################",
    ],
]


class Game040MirrorMaze(BaseCartridge):
    TOTAL_LEVELS = 4

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.map = [[0 for _ in range(16)] for _ in range(16)]
        self.level = 0
        self.ax = 2
        self.ay = 13
        self.bx = 13
        self.by = 13
        self.goal_ax = 5
        self.goal_ay = 3
        self.goal_bx = 11
        self.goal_by = 3
        self.moves = 0
        self.lives = 1
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 40

    @property
    def name(self) -> str:
        return "镜像双人迷宫"

    @property
    def english_name(self) -> str:
        return "Mirror Twins"

    @property
    def release_year(self) -> int:
        return 2012

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "左右对称双生角色反向同步移动 + 不对称墙壁卡位对齐 + 陷阱躲避"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def load_level(self, lvl: int) -> None:
        lvl = max(0, min(self.TOTAL_LEVELS - 1, lvl))
        self.level = lvl
        self.moves = 0
        self.map = [[0 for _ in range(16)] for _ in range(16)]
        for y in range(16):
            row_str = MIRROR_LEVELS[lvl][y]
            for x in range(16):
                ch = row_str[x]
                if ch == "#":
                    self.map[y][x] = 1
                elif ch == "X":
                    self.map[y][x] = 2
                elif ch == "G":
                    self.map[y][x] = 3
                    self.goal_ax = x
                    self.goal_ay = y
                elif ch == "H":
                    self.map[y][x] = 4
                    self.goal_bx = x
                    self.goal_by = y
                elif ch == "A":
                    self.map[y][x] = 0
                    self.ax = x
                    self.ay = y
                elif ch == "B":
                    self.map[y][x] = 0
                    self.bx = x
                    self.by = y
                else:
                    self.map[y][x] = 0

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 1
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.load_level(0)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.lives = 1
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.load_level(0)
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _step_move(self, dx: int, dy: int) -> None:
        nax, nay = self.ax + dx, self.ay + dy
        nbx, nby = self.bx - dx, self.by + dy

        if 0 <= nax < 16 and 0 <= nay < 16 and self.map[nay][nax] != 1:
            self.ax, self.ay = nax, nay
        if 0 <= nbx < 16 and 0 <= nby < 16 and self.map[nby][nbx] != 1:
            self.bx, self.by = nbx, nby

        self.moves += 1

        if self.map[self.ay][self.ax] == 2 or self.map[self.by][self.bx] == 2:
            self.lives = 0
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            if self._score > self._high_score:
                self._high_score = self._score
            return

        if (
            self.ax == self.goal_ax
            and self.ay == self.goal_ay
            and self.bx == self.goal_bx
            and self.by == self.goal_by
        ):
            bonus = max(0, (30 - self.moves) * 2)
            self._add_score(150 + bonus)
            if self.level + 1 >= self.TOTAL_LEVELS:
                self._state = STATE_VICTORY
                self.state_timer = 0.0
            else:
                self.load_level(self.level + 1)

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
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

            if keys_pressed & KEY_LEFT:
                self._step_move(-1, 0)
            elif keys_pressed & KEY_RIGHT:
                self._step_move(1, 0)
            elif keys_pressed & KEY_UP:
                self._step_move(0, -1)
            elif keys_pressed & KEY_DOWN:
                self._step_move(0, 1)

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

        pulse = 0.5 + 0.5 * math.sin(self.anim_timer * 6.0)

        for y in range(16):
            for x in range(16):
                cell = self.map[y][x]
                if y == 0:
                    set_px(x, y, 16, 18, 28)
                elif cell == 1:
                    if x in (7, 8):
                        set_px(x, y, 75, 55, 140)
                    else:
                        set_px(x, y, 42, 58, 86)
                elif cell == 2:
                    set_px(x, y, int(185 + pulse * 65.0), 28, 32)
                elif cell in (3, 4):
                    set_px(x, y, 35, int(165 + pulse * 80.0), int(90 + pulse * 50.0))
                else:
                    set_px(x, y, 12, 16, 26)

        for i in range(self.TOTAL_LEVELS):
            if i < self.level:
                set_px(1 + i, 0, 50, 230, 120)
            elif i == self.level:
                set_px(1 + i, 0, 255, 215, 40)
            else:
                set_px(1 + i, 0, 45, 50, 68)

        if self.lives > 0:
            set_px(14, 0, 245, 65, 95)

        a_on_goal = self.ax == self.goal_ax and self.ay == self.goal_ay
        b_on_goal = self.bx == self.goal_bx and self.by == self.goal_by

        if a_on_goal:
            set_px(self.ax, self.ay, 220, 255, 255)
        else:
            set_px(self.ax, self.ay, 0, 235, 255)

        if b_on_goal:
            set_px(self.bx, self.by, 255, 230, 255)
        else:
            set_px(self.bx, self.by, 255, 75, 215)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                set_px(x, 0, 235, 50, 50)
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
            "lives": self.lives,
            "state": self._state,
            "level": self.level,
            "progress": 100 if self._state == STATE_VICTORY else self.level * 25,
        }
