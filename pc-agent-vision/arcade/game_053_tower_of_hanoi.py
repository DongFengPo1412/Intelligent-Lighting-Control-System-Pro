# -*- coding: utf-8 -*-
"""game_053_tower_of_hanoi.py —— 目标 #053 汉诺塔 (Tower of Hanoi 1983)
三柱递归盘片搬运 + 小盘压大盘尺寸约束校验 + 4盘进阶5盘双关挑战
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    KEY_SELECT,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

NUM_PEGS = 3
MAX_DISKS = 5
NUM_STAGES = 2
PEG_X = [2, 7, 12]

DISK_RGB = [
    (0, 0, 0),
    (255, 65, 60),    # Size 1: Red
    (255, 160, 25),   # Size 2: Orange
    (50, 225, 95),    # Size 3: Green
    (55, 175, 255),   # Size 4: Blue
    (195, 85, 255),   # Size 5: Violet
]


class Game053TowerOfHanoi(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.stage = 0
        self.num_disks = 4
        self.cursor_peg = 0
        self.held_disk = 0
        self.held_from_peg = -1
        self.moves = 0
        self.error_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.pegs: List[List[int]] = [[], [], []]
        self.reset()

    @property
    def game_id(self) -> int:
        return 53

    @property
    def name(self) -> str:
        return "汉诺塔"

    @property
    def english_name(self) -> str:
        return "Tower of Hanoi"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "三柱递归移盘与严格大小阶梯压叠约束"

    def init(self) -> None:
        self.reset()

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _load_stage(self, stage_idx: int) -> None:
        if not (0 <= stage_idx < NUM_STAGES):
            stage_idx = 0
        self.stage = stage_idx
        self.num_disks = 4 if self.stage == 0 else 5
        self.pegs = [
            [self.num_disks - i for i in range(self.num_disks)],
            [],
            [],
        ]
        self.cursor_peg = 0
        self.held_disk = 0
        self.held_from_peg = -1
        self.moves = 0
        self.error_timer = 0.0

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._load_stage(0)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._load_stage(0)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

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

            if self.error_timer > 0.0:
                self.error_timer = max(0.0, self.error_timer - dt)

            if keys_pressed & KEY_SELECT:
                self._load_stage(self.stage)
                return

            if keys_pressed & KEY_LEFT:
                if self.cursor_peg > 0:
                    self.cursor_peg -= 1
            elif keys_pressed & KEY_RIGHT:
                if self.cursor_peg < NUM_PEGS - 1:
                    self.cursor_peg += 1

            if self.held_disk == 0:
                if keys_pressed & KEY_A:
                    if len(self.pegs[self.cursor_peg]) > 0:
                        self.held_disk = self.pegs[self.cursor_peg].pop()
                        self.held_from_peg = self.cursor_peg
            else:
                if keys_pressed & (KEY_A | KEY_B):
                    stack = self.pegs[self.cursor_peg]
                    can_drop = (len(stack) == 0) or (self.held_disk < stack[-1])
                    if not can_drop:
                        self.error_timer = 0.30
                    else:
                        stack.append(self.held_disk)
                        if self.cursor_peg != self.held_from_peg:
                            self.moves += 1
                        self.held_disk = 0
                        self.held_from_peg = -1

                        if len(self.pegs[2]) == self.num_disks:
                            optimal = (1 << self.num_disks) - 1
                            extra = max(0, self.moves - optimal)
                            stage_pts = max(100, 500 - extra * 5)
                            self._add_score(stage_pts)

                            if self.stage + 1 < NUM_STAGES:
                                self._load_stage(self.stage + 1)
                            else:
                                self._state = STATE_VICTORY
                                self.state_timer = 0.0

    @staticmethod
    def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < 16 and 0 <= y < 16:
            idx = (y * 16 + x) * 3
            fb[idx] = r
            fb[idx + 1] = g
            fb[idx + 2] = b

    def _draw_disk(self, fb: bytearray, cx: int, y: int, disk_size: int, highlight_err: bool) -> None:
        if not (1 <= disk_size <= MAX_DISKS):
            return
        r, g, b = (255, 35, 35) if highlight_err else DISK_RGB[disk_size]
        if disk_size == 1:
            self._set_px(fb, cx, y, r, g, b)
        elif disk_size == 2:
            self._set_px(fb, cx - 1, y, r // 2, g // 2, b // 2)
            self._set_px(fb, cx, y, r, g, b)
            self._set_px(fb, cx + 1, y, r // 2, g // 2, b // 2)
        elif disk_size == 3:
            for dx in range(-1, 2):
                self._set_px(fb, cx + dx, y, r, g, b)
        elif disk_size == 4:
            self._set_px(fb, cx - 2, y, r // 2, g // 2, b // 2)
            for dx in range(-1, 2):
                self._set_px(fb, cx + dx, y, r, g, b)
            self._set_px(fb, cx + 2, y, r // 2, g // 2, b // 2)
        else:
            for dx in range(-2, 3):
                self._set_px(fb, cx + dx, y, r, g, b)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                self._set_px(fb, x, y, 12, 16 + y, 30 + y)

        if self.error_timer > 0.0:
            for x in range(16):
                self._set_px(fb, x, 0, 245, 30, 30)
        else:
            self._set_px(fb, 15, 0, 46 if self.stage >= 1 else 255, 215, 60)
            self._set_px(fb, 15, 1, 255 if self.stage >= 1 else 50, 215 if self.stage >= 1 else 55, 65)

        for x in range(15):
            self._set_px(fb, x, 14, 155, 105, 55)
            self._set_px(fb, x, 15, 110, 72, 36)

        for p in range(NUM_PEGS):
            px = PEG_X[p]
            for y in range(6, 14):
                if p == 2:
                    self._set_px(fb, px, y, 175, 155, 90)
                else:
                    self._set_px(fb, px, y, 110, 120, 138)

        for p in range(NUM_PEGS):
            cx = PEG_X[p]
            for i, d_size in enumerate(self.pegs[p]):
                self._draw_disk(fb, cx, 13 - i, d_size, False)

        sel_x = PEG_X[self.cursor_peg]
        err_flash = self.error_timer > 0.0
        self._set_px(fb, sel_x, 0, 255, 245, 180)
        self._set_px(fb, sel_x - 1, 0, 180, 175, 120)
        self._set_px(fb, sel_x + 1, 0, 180, 175, 120)
        self._set_px(fb, sel_x, 1, 255, 255, 255)

        if self.held_disk > 0:
            self._draw_disk(fb, sel_x, 2, self.held_disk, err_flash)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = self.stage * 50 + (len(self.pegs[2]) * 50) // max(1, self.num_disks)
        if self._state == STATE_VICTORY:
            prog = 100
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 1,
            "state": self._state,
            "progress": min(100, prog),
        }
