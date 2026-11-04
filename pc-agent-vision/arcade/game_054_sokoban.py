"""game_054_sokoban.py —— 目标 #054 推箱子 (Sokoban 1982)
单向推移不可拉动 + 空间槽位逻辑归位 + 拓扑死锁与通关判定
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_SELECT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

SOKOBAN_FLOOR = 0
SOKOBAN_WALL = 1
SOKOBAN_GOAL = 2


class Box:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class Game054Sokoban(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.player_x = 7
        self.player_y = 8
        self.moves = 0
        self.boxes: List[Box] = []
        self.boxes_on_goal = 0
        self.map = [[SOKOBAN_FLOOR] * 16 for _ in range(16)]
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 54

    @property
    def name(self) -> str:
        return "推箱子"

    @property
    def english_name(self) -> str:
        return "Sokoban 1982"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "单向推移与空间槽位逻辑归位"

    def init(self) -> None:
        self.reset()

    def _is_goal(self, x: int, y: int) -> bool:
        if not (0 <= x < 16 and 0 <= y < 16):
            return False
        return self.map[y][x] == SOKOBAN_GOAL

    def _find_box_at(self, x: int, y: int) -> int:
        for i, b in enumerate(self.boxes):
            if b.x == x and b.y == y:
                return i
        return -1

    def _reset_level(self):
        self.map = [[SOKOBAN_FLOOR] * 16 for _ in range(16)]
        for y in range(16):
            for x in range(16):
                if x < 2 or x > 13 or y < 2 or y > 13:
                    self.map[y][x] = SOKOBAN_WALL

        for x in range(2, 14):
            self.map[2][x] = SOKOBAN_WALL
            self.map[13][x] = SOKOBAN_WALL
        for y in range(2, 14):
            self.map[y][2] = SOKOBAN_WALL
            self.map[y][13] = SOKOBAN_WALL

        self.map[5][8] = SOKOBAN_WALL
        self.map[6][8] = SOKOBAN_WALL
        self.map[9][7] = SOKOBAN_WALL
        self.map[10][7] = SOKOBAN_WALL

        self.map[4][4] = SOKOBAN_GOAL
        self.map[4][5] = SOKOBAN_GOAL
        self.map[11][10] = SOKOBAN_GOAL
        self.map[11][11] = SOKOBAN_GOAL

        self.boxes = [Box(5, 6), Box(6, 6), Box(9, 9), Box(10, 9)]
        self.player_x = 7
        self.player_y = 8
        self.moves = 0
        self._check_victory()

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._reset_level()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._reset_level()

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _check_victory(self):
        on_goal = sum(1 for b in self.boxes if self._is_goal(b.x, b.y))
        self.boxes_on_goal = on_goal
        if self.boxes_on_goal == 4:
            self._state = STATE_VICTORY
            self.state_timer = 0.0
            calc = 1000 - self.moves * 5
            self._score = max(100, calc)
            if self._score > self._high_score:
                self._high_score = self._score

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

            if keys_pressed & KEY_SELECT:
                self._reset_level()
                return

            dx, dy = 0, 0
            if keys_pressed & KEY_UP:
                dy = -1
            elif keys_pressed & KEY_DOWN:
                dy = 1
            elif keys_pressed & KEY_LEFT:
                dx = -1
            elif keys_pressed & KEY_RIGHT:
                dx = 1

            if dx != 0 or dy != 0:
                tx = self.player_x + dx
                ty = self.player_y + dy
                if self.map[ty][tx] != SOKOBAN_WALL:
                    box_idx = self._find_box_at(tx, ty)
                    if box_idx == -1:
                        self.player_x = tx
                        self.player_y = ty
                        self.moves += 1
                    else:
                        behind_x = tx + dx
                        behind_y = ty + dy
                        if self.map[behind_y][behind_x] != SOKOBAN_WALL and self._find_box_at(behind_x, behind_y) == -1:
                            self.boxes[box_idx].x = behind_x
                            self.boxes[box_idx].y = behind_y
                            self.player_x = tx
                            self.player_y = ty
                            self.moves += 1
                            self._check_victory()

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if self.map[y][x] == SOKOBAN_WALL:
                    fb[idx : idx + 3] = bytes([70, 80, 95])
                elif self.map[y][x] == SOKOBAN_GOAL:
                    fb[idx : idx + 3] = bytes([231, 76, 60])
                else:
                    if 2 <= x <= 13 and 2 <= y <= 13:
                        fb[idx : idx + 3] = bytes([25, 25, 28])

        for b in self.boxes:
            if 0 <= b.x < 16 and 0 <= b.y < 16:
                idx = (b.y * 16 + b.x) * 3
                if self._is_goal(b.x, b.y):
                    fb[idx : idx + 3] = bytes([46, 204, 113])
                else:
                    fb[idx : idx + 3] = bytes([241, 196, 15])

        px, py = self.player_x, self.player_y
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx : idx + 3] = bytes([52, 152, 219])

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
            "moves": self.moves,
            "high_score": self._high_score,
            "lives": 1,
            "state": self._state,
            "progress": min(100, (self.boxes_on_goal * 100 // max(1, len(self.boxes)))),
        }
