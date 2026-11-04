# -*- coding: utf-8 -*-
"""game_073_ludo_race.py —— 目标 #073 飞行棋 (Ludo Race, 1986)
24步外环赛道 + 3步安全终点走廊 + 双棋子起飞/选子/吃子/掷6奖励回合
"""

import math
from typing import Dict, Any, Tuple
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

LUDO_WAIT_ROLL = 0
LUDO_ROLL_ANIM = 1
LUDO_SELECT_TOKEN = 2
LUDO_PASS_DELAY = 3
LUDO_AI_THINK = 4
LUDO_AI_MOVE = 5

OUTER_LOOP = (
    (4, 10), (4, 9), (4, 8), (4, 7), (4, 6), (4, 5),
    (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4),
    (11, 5), (11, 6), (11, 7), (11, 8), (11, 9), (11, 10),
    (10, 11), (9, 11), (8, 11), (7, 11), (6, 11), (5, 11),
)

PLAYER_HOME_STRETCH = ((5, 10), (6, 9), (6, 8))
AI_HOME_STRETCH = ((10, 5), (9, 6), (9, 7))


class Game073LudoRace(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.phase = LUDO_WAIT_ROLL
        self.p_step = [-1, -1]
        self.ai_step = [-1, -1]
        self.dice = 6
        self.anim_die = 1
        self.selected_token = 0
        self.phase_timer = 0.0
        self.capture_flash_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_state = 0x73731986
        self.reset()

    @property
    def game_id(self) -> int:
        return 73

    @property
    def name(self) -> str:
        return "飞行棋"

    @property
    def english_name(self) -> str:
        return "Ludo Race"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "掷骰起飞选子与环道撞子奖励回合竞速"

    def _next_rand(self) -> int:
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._rng_state >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _init_game_data(self) -> None:
        self.phase = LUDO_WAIT_ROLL
        self.p_step = [-1, -1]
        self.ai_step = [-1, -1]
        self.dice = 6
        self.anim_die = 1
        self.selected_token = 0
        self.phase_timer = 0.0
        self.capture_flash_timer = 0.0
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_state = 0x73731986

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

    @staticmethod
    def can_move_token(step: int, die_val: int) -> bool:
        if step == -1:
            return die_val >= 5
        return 0 <= step < 27

    def apply_move(self, is_player: bool, tok_idx: int) -> None:
        my_steps = self.p_step if is_player else self.ai_step
        opp_steps = self.ai_step if is_player else self.p_step

        cur = my_steps[tok_idx]
        if cur == -1:
            nxt = 0
            if is_player:
                self._add_score(15)
        else:
            nxt = min(27, cur + self.dice)
            if is_player:
                self._add_score(60 if nxt == 27 else 10)

        my_steps[tok_idx] = nxt

        # Outer-track capture on opponent's lone token
        if 0 <= nxt <= 23:
            my_outer = nxt if is_player else ((12 + nxt) % 24)
            opp_at_cell = 0
            victim_idx = -1
            for j in range(2):
                if 0 <= opp_steps[j] <= 23:
                    opp_outer = ((12 + opp_steps[j]) % 24) if is_player else opp_steps[j]
                    if opp_outer == my_outer:
                        opp_at_cell += 1
                        victim_idx = j
            if opp_at_cell == 1 and victim_idx >= 0:
                opp_steps[victim_idx] = -1
                self.capture_flash_timer = 0.35
                if is_player:
                    self._add_score(80)

        if self.p_step[0] == 27 and self.p_step[1] == 27:
            self._add_score(400)
            self._state = STATE_VICTORY
            self.state_timer = 0.0
            return

        if self.ai_step[0] == 27 and self.ai_step[1] == 27:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return

        if is_player:
            if self.dice == 6:
                self.phase = LUDO_WAIT_ROLL
            else:
                self.phase = LUDO_AI_THINK
                self.phase_timer = 0.22
        else:
            if self.dice == 6:
                self.phase = LUDO_AI_THINK
                self.phase_timer = 0.22
            else:
                self.phase = LUDO_WAIT_ROLL

    def choose_ai_token(self) -> int:
        best_tok = -1
        best_val = -9999
        for t in range(2):
            cur = self.ai_step[t]
            if not self.can_move_token(cur, self.dice):
                continue
            nxt = 0 if cur == -1 else min(27, cur + self.dice)
            val = nxt * 3

            if 0 <= nxt <= 23:
                ai_outer = (12 + nxt) % 24
                pl_count = sum(1 for j in range(2) if self.p_step[j] == ai_outer)
                if pl_count == 1:
                    val += 500
            if nxt == 27:
                val += 300
            if cur == -1:
                val += 140
            if cur < 24 <= nxt:
                val += 90

            if val > best_val:
                best_val = val
                best_tok = t
        return best_tok

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt
        if self.capture_flash_timer > 0.0:
            self.capture_flash_timer = max(0.0, self.capture_flash_timer - dt)

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

            if self.phase == LUDO_WAIT_ROLL:
                if keys_pressed & KEY_A:
                    self.dice = 1 + (self._next_rand() % 6)
                    self.anim_die = 1 + (self._next_rand() % 6)
                    self.phase = LUDO_ROLL_ANIM
                    self.phase_timer = 0.16
            elif self.phase == LUDO_ROLL_ANIM:
                self.phase_timer -= dt
                self.anim_die = 1 + (int(self.anim_timer * 30.0) % 6)
                if self.phase_timer <= 0.0:
                    m0 = self.can_move_token(self.p_step[0], self.dice)
                    m1 = self.can_move_token(self.p_step[1], self.dice)
                    if not m0 and not m1:
                        self.phase = LUDO_PASS_DELAY
                        self.phase_timer = 0.22
                    else:
                        self.selected_token = 0 if m0 else 1
                        self.phase = LUDO_SELECT_TOKEN
            elif self.phase == LUDO_SELECT_TOKEN:
                m0 = self.can_move_token(self.p_step[0], self.dice)
                m1 = self.can_move_token(self.p_step[1], self.dice)
                if m0 and m1 and (keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN | KEY_B)):
                    self.selected_token = 1 - self.selected_token
                elif m0 and not m1:
                    self.selected_token = 0
                elif not m0 and m1:
                    self.selected_token = 1

                if keys_pressed & KEY_A:
                    if self.can_move_token(self.p_step[self.selected_token], self.dice):
                        self.apply_move(True, self.selected_token)
            elif self.phase == LUDO_PASS_DELAY:
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    self.phase = LUDO_AI_THINK
                    self.phase_timer = 0.22
            elif self.phase == LUDO_AI_THINK:
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    self.dice = 1 + (self._next_rand() % 6)
                    self.phase = LUDO_AI_MOVE
                    self.phase_timer = 0.18
            elif self.phase == LUDO_AI_MOVE:
                self.phase_timer -= dt
                if self.phase_timer <= 0.0:
                    tok = self.choose_ai_token()
                    if tok >= 0:
                        self.apply_move(False, tok)
                    else:
                        if self.dice == 6:
                            self.phase = LUDO_AI_THINK
                            self.phase_timer = 0.22
                        else:
                            self.phase = LUDO_WAIT_ROLL

    def get_token_pixel(self, is_player: bool, tok_idx: int) -> Tuple[int, int]:
        step = self.p_step[tok_idx] if is_player else self.ai_step[tok_idx]
        if step == -1:
            if is_player:
                return (1, 13) if tok_idx == 0 else (2, 14)
            return (13, 1) if tok_idx == 0 else (14, 2)
        if step <= 23:
            outer = step if is_player else ((12 + step) % 24)
            return OUTER_LOOP[outer]
        if step <= 26:
            h = step - 24
            return PLAYER_HOME_STRETCH[h] if is_player else AI_HOME_STRETCH[h]
        if is_player:
            return (7 if tok_idx == 0 else 8, 8)
        return (8 if tok_idx == 0 else 7, 7)

    @staticmethod
    def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < 16 and 0 <= y < 16:
            idx = (y * 16 + x) * 3
            fb[idx] = r
            fb[idx + 1] = g
            fb[idx + 2] = b

    def _draw_die_3x3(self, fb: bytearray, val: int, is_player_turn: bool) -> None:
        bg_r, bg_g, bg_b = (20, 45, 55) if is_player_turn else (45, 20, 25)
        for y in range(3):
            for x in range(3):
                self._set_px(fb, x, y, bg_r, bg_g, bg_b)

        pr, pg, pb = (255, 190, 0) if val == 6 else (255, 235, 120)
        if val in (1, 3, 5):
            self._set_px(fb, 1, 1, pr, pg, pb)
        if val >= 2:
            self._set_px(fb, 0, 0, pr, pg, pb)
            self._set_px(fb, 2, 2, pr, pg, pb)
        if val >= 4:
            self._set_px(fb, 2, 0, pr, pg, pb)
            self._set_px(fb, 0, 2, pr, pg, pb)
        if val == 6:
            self._set_px(fb, 0, 1, pr, pg, pb)
            self._set_px(fb, 2, 1, pr, pg, pb)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        bg = (55, 25, 10) if self.capture_flash_timer > 0.0 else (10, 14, 22)
        for y in range(16):
            for x in range(16):
                self._set_px(fb, x, y, *bg)

        for dy in range(2):
            for dx in range(2):
                self._set_px(fb, 1 + dx, 13 + dy, 12, 60, 80)
                self._set_px(fb, 13 + dx, 1 + dy, 80, 20, 25)

        for i, (tx, ty) in enumerate(OUTER_LOOP):
            if i == 0:
                self._set_px(fb, tx, ty, 20, 100, 125)
            elif i == 12:
                self._set_px(fb, tx, ty, 125, 35, 35)
            else:
                v = 55 if (i % 2 == 0) else 42
                self._set_px(fb, tx, ty, v, v + 4, v + 12)

        for h in range(3):
            self._set_px(fb, PLAYER_HOME_STRETCH[h][0], PLAYER_HOME_STRETCH[h][1], 18, 95, 120)
            self._set_px(fb, AI_HOME_STRETCH[h][0], AI_HOME_STRETCH[h][1], 120, 30, 35)

        for y in (7, 8):
            for x in (7, 8):
                self._set_px(fb, x, y, 110, 90, 20)

        p_turn = self.phase in (LUDO_WAIT_ROLL, LUDO_ROLL_ANIM, LUDO_SELECT_TOKEN)
        shown_die = self.anim_die if self.phase == LUDO_ROLL_ANIM else self.dice
        self._draw_die_3x3(fb, shown_die, p_turn)

        for t in range(2):
            tx, ty = self.get_token_pixel(False, t)
            if self.ai_step[t] == 27:
                self._set_px(fb, tx, ty, 255, 95, 50)
            else:
                self._set_px(fb, tx, ty, 240, 50, 50)

        blink_bright = math.fmod(self.anim_timer, 0.36) < 0.20
        for t in range(2):
            tx, ty = self.get_token_pixel(True, t)
            if self._state == STATE_PLAYING and self.phase == LUDO_SELECT_TOKEN and t == self.selected_token:
                if blink_bright:
                    self._set_px(fb, tx, ty, 255, 255, 255)
                else:
                    self._set_px(fb, tx, ty, 0, 230, 255)
            elif self.p_step[t] == 27:
                self._set_px(fb, tx, ty, 120, 255, 210)
            else:
                self._set_px(fb, tx, ty, 0, 215, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        p0 = 0 if self.p_step[0] < 0 else (self.p_step[0] + 1)
        p1 = 0 if self.p_step[1] < 0 else (self.p_step[1] + 1)
        prog = min(100, ((p0 + p1) * 100) // 56)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": prog,
        }
