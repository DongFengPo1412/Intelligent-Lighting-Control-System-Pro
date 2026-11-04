# -*- coding: utf-8 -*-
"""game_086_tiny_farm.py —— 目标 #086 小农场 (Tiny Harvest)
机制: 5x5农田地块(播种->浇水发芽->生长->金黄成熟->逾期枯萎) + 水井补给 + 季节营收配额
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

PLOT_BARREN = 0
PLOT_SEED = 1
PLOT_SPROUT = 2
PLOT_GROWING = 3
PLOT_RIPE = 4
PLOT_WITHERED = 5


class FarmPlot:
    def __init__(self):
        self.state = PLOT_BARREN
        self.premium = False
        self.boost_watered = False
        self.timer = 0.0


class Game086TinyFarm(BaseCartridge):
    GRID_SIZE = 5
    MAX_WATER = 6
    TARGET_QUOTA = 500

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.season_timer = 60.0
        self.cursor_col = 2
        self.cursor_row = 2
        self.water = self.MAX_WATER
        self.combo = 0
        self.combo_timer = 0.0
        self.move_cooldown = 0.0
        self.plots: List[List[FarmPlot]] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 86

    @property
    def name(self) -> str:
        return "小农场"

    @property
    def english_name(self) -> str:
        return "Tiny Harvest"

    @property
    def release_year(self) -> int:
        return 1996

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "5x5农田播种灌溉成熟防枯萎与季节配额经营"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _setup_match(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.season_timer = 60.0
        self.cursor_col = 2
        self.cursor_row = 2
        self.water = self.MAX_WATER
        self.combo = 0
        self.combo_timer = 0.0
        self.move_cooldown = 0.0
        self.plots = [[FarmPlot() for _ in range(self.GRID_SIZE)] for _ in range(self.GRID_SIZE)]

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._setup_match(STATE_TITLE)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_match(STATE_PLAYING)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _handle_smart_action_a(self) -> None:
        p = self.plots[self.cursor_row][self.cursor_col]
        if p.state == PLOT_BARREN:
            p.state = PLOT_SEED
            p.premium = False
            p.boost_watered = False
            p.timer = 0.0
        elif p.state == PLOT_SEED:
            if self.water > 0:
                self.water -= 1
                p.state = PLOT_SPROUT
                p.timer = 0.0
        elif p.state in (PLOT_SPROUT, PLOT_GROWING):
            if self.water > 0 and not p.boost_watered:
                self.water -= 1
                p.boost_watered = True
                p.timer += 1.2
        elif p.state == PLOT_RIPE:
            base_val = 90 if p.premium else 50
            bonus = self.combo * 10 if self.combo_timer > 0.0 else 0
            self._add_score(base_val + bonus)
            if self.combo_timer > 0.0:
                self.combo = min(5, self.combo + 1)
            else:
                self.combo = 1
            self.combo_timer = 4.0
            p.state = PLOT_BARREN
            p.premium = False
            p.boost_watered = False
            p.timer = 0.0
        elif p.state == PLOT_WITHERED:
            p.state = PLOT_BARREN
            p.premium = False
            p.boost_watered = False
            p.timer = 0.0

    def _handle_action_b(self) -> None:
        p = self.plots[self.cursor_row][self.cursor_col]
        if p.state == PLOT_BARREN and self.water > 0:
            p.state = PLOT_SEED
            p.premium = True
            p.boost_watered = False
            p.timer = 0.0
        else:
            self.water = self.MAX_WATER

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

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

        if keys_pressed & KEY_START:
            self._state = STATE_PAUSED
            return

        if self.combo_timer > 0.0:
            self.combo_timer -= dt
            if self.combo_timer <= 0.0:
                self.combo_timer = 0.0
                self.combo = 0

        if self.move_cooldown > 0.0:
            self.move_cooldown -= dt
        dpad_mask = KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN
        dpad_trig = keys_pressed & dpad_mask
        if not dpad_trig and self.move_cooldown <= 0.0 and (keys_down & dpad_mask):
            dpad_trig = keys_down & dpad_mask
            self.move_cooldown = 0.14
        elif dpad_trig:
            self.move_cooldown = 0.18

        if dpad_trig & KEY_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
        elif dpad_trig & KEY_RIGHT:
            if self.cursor_col < self.GRID_SIZE - 1:
                self.cursor_col += 1
        elif dpad_trig & KEY_UP:
            if self.cursor_row > 0:
                self.cursor_row -= 1
        elif dpad_trig & KEY_DOWN:
            if self.cursor_row < self.GRID_SIZE - 1:
                self.cursor_row += 1

        if keys_pressed & KEY_A:
            self._handle_smart_action_a()
        if keys_pressed & KEY_B:
            self._handle_action_b()

        if self._score >= self.TARGET_QUOTA:
            self._state = STATE_VICTORY
            self.state_timer = 0.0
            return

        for r in range(self.GRID_SIZE):
            for c in range(self.GRID_SIZE):
                p = self.plots[r][c]
                if p.state == PLOT_SPROUT:
                    p.timer += dt
                    sprout_dur = 1.6 if p.premium else 2.5
                    if p.timer >= sprout_dur:
                        p.state = PLOT_GROWING
                        p.timer = 0.0
                elif p.state == PLOT_GROWING:
                    p.timer += dt
                    grow_dur = 2.0 if p.premium else 3.0
                    if p.timer >= grow_dur:
                        p.state = PLOT_RIPE
                        p.timer = 0.0
                elif p.state == PLOT_RIPE:
                    p.timer += dt
                    if p.timer > 10.0:
                        p.state = PLOT_WITHERED
                        p.timer = 0.0

        self.season_timer -= dt
        if self.season_timer <= 0.0:
            self.season_timer = 0.0
            self._state = STATE_VICTORY if self._score >= self.TARGET_QUOTA else STATE_GAMEOVER
            self.state_timer = 0.0

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)

        for y in range(16):
            for x in range(16):
                set_pixel(fb, x, y, 28, 48, 22)
        for x in range(16):
            set_pixel(fb, x, 0, 12, 14, 18)
            set_pixel(fb, x, 1, 20, 34, 18)

        set_pixel(fb, 15, 1, 30, 175, 255)
        set_pixel(fb, 0, 1, 30, 175, 255)

        gold_blink = (int(self.anim_timer * 6.0) % 2) == 0
        for r in range(self.GRID_SIZE):
            for c in range(self.GRID_SIZE):
                px = 1 + c * 3
                py = 2 + r * 3
                p = self.plots[r][c]
                for dy in range(2):
                    for dx in range(2):
                        cr, cg, cb = 75, 48, 26
                        if p.state == PLOT_SEED:
                            if dx == 0 and dy == 0:
                                cr, cg, cb = (255, 140, 210) if p.premium else (225, 190, 65)
                            else:
                                cr, cg, cb = 85, 55, 30
                        elif p.state == PLOT_SPROUT:
                            cr, cg, cb = 35, 205, 165
                        elif p.state == PLOT_GROWING:
                            cr, cg, cb = 45, 215, 65
                        elif p.state == PLOT_RIPE:
                            if gold_blink:
                                cr, cg, cb = 255, (175 if p.premium else 215), 25
                            else:
                                cr, cg, cb = 255, 240, 110
                        elif p.state == PLOT_WITHERED:
                            cr, cg, cb = 95, 95, 100
                        set_pixel(fb, px + dx, py + dy, cr, cg, cb)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            cx = 1 + self.cursor_col * 3
            cy = 2 + self.cursor_row * 3
            if (int(self.anim_timer * 7.0) % 2) == 0:
                set_pixel(fb, cx, cy, 255, 255, 255)
                set_pixel(fb, cx + 1, cy + 1, 255, 255, 255)

        time_pips = max(0, min(8, int(math.ceil((self.season_timer / 60.0) * 8.0))))
        for i in range(8):
            if i < time_pips:
                set_pixel(fb, i, 0, 245, 175, 35)
            else:
                set_pixel(fb, i, 0, 45, 30, 12)

        for w in range(self.MAX_WATER):
            if w < self.water:
                set_pixel(fb, 9 + w, 0, 35, 195, 255)
            else:
                set_pixel(fb, 9 + w, 0, 15, 40, 60)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = min(100, (self._score * 100) // self.TARGET_QUOTA)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": prog,
        }
