# -*- coding: utf-8 -*-
"""
Game #130: 丛林探险 (Jungle Hunt 1982 / Taito)
街机历史上开创多阶段连续野外探险的传奇冒险动作鼻祖：
树冠摇摆藤条跳跃、鳄鱼狂澜潜水刺杀与氧气管理、滚石坡道翻跳规避、土著部落绳索大营救。
"""

from typing import List, Dict, Any, Optional
import math
import random
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)

STAGE_VINES = 0
STAGE_RIVER = 1
STAGE_BOULDERS = 2
STAGE_RESCUE = 3

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_PLAYER_DYING = 2
STATE_GAME_OVER = 3


class Game130JungleHunt(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.stage = STAGE_VINES
        self.expedition_round = 1
        self.progress = 0.0

        self.px = 2.0
        self.py = 8.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.is_jumping = False
        self.is_ducking = False

        self.vine_angle = [0.0, 0.5]
        self.vine_x = [5.0, 11.0]
        self.current_vine = 0
        self.in_air = False

        self.oxygen = 30.0
        self.croc_x = [16.0, 22.0, 28.0]
        self.croc_y = [5.0, 8.0, 11.0]
        self.croc_vx = [-2.0, -2.4, -2.8]
        self.croc_mouth_open = [True, False, True]
        self.is_stabbing = False
        self.stab_timer = 0.0

        self.boulder_x = [16.0, 23.0, 30.0]
        self.boulder_y = [13.0, 10.5, 13.0]
        self.boulder_vx = [-3.2, -3.2, -3.2]
        self.boulder_is_high = [False, True, False]

        self.native_x = 8.0
        self.native_vx = 2.2
        self.maiden_y = 5.0
        self.maiden_rescued = False

        self.reset()

    @property
    def game_id(self) -> int:
        return 130

    @property
    def name(self) -> str:
        return "丛林探险"

    @property
    def english_name(self) -> str:
        return "Jungle Hunt"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "四阶段连续野外铁人三项：树冠摆藤跳跃、鳄鱼河潜水刺杀、滚石坡道翻跳与营救"

    def get_name(self) -> str:
        return "Jungle Hunt (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.expedition_round = 1
        self.stage = STAGE_VINES
        self._init_stage(self.stage)

    def _init_stage(self, stage: int) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.stage = stage
        self.progress = 0.0

        self.px = 2.0
        self.py = 8.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.is_jumping = False
        self.is_ducking = False

        if self.stage == STAGE_VINES:
            self.vine_x = [5.0, 11.0]
            self.vine_angle = [0.0, 0.5]
            self.current_vine = 0
            self.in_air = False
        elif self.stage == STAGE_RIVER:
            self.py = 4.0
            self.oxygen = 30.0
            self.is_stabbing = False
            self.stab_timer = 0.0
            self.croc_x = [16.0, 22.0, 28.0]
            self.croc_y = [5.0, 8.0, 11.0]
            self.croc_vx = [-(2.0 + self.expedition_round * 0.2), -(2.4 + self.expedition_round * 0.2), -(2.8 + self.expedition_round * 0.2)]
            self.croc_mouth_open = [True, False, True]
        elif self.stage == STAGE_BOULDERS:
            self.py = 13.0
            self.boulder_x = [16.0, 23.0, 30.0]
            self.boulder_vx = [-(3.2 + self.expedition_round * 0.3)] * 3
            self.boulder_is_high = [False, True, False]
        elif self.stage == STAGE_RESCUE:
            self.px = 1.5
            self.py = 13.0
            self.native_x = 8.0
            self.native_vx = 2.2
            self.maiden_y = 5.0
            self.maiden_rescued = False

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PLAYER_DYING:
            if self.state_timer > 1.3:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self._init_stage(self.stage)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 1.5:
                if self.stage < STAGE_RESCUE:
                    self._init_stage(self.stage + 1)
                else:
                    self.expedition_round += 1
                    self.score += 2000
                    self._init_stage(STAGE_VINES)
            return

        if self.stage == STAGE_VINES:
            self._update_vines(dt, buttons, prev_buttons)
        elif self.stage == STAGE_RIVER:
            self._update_river(dt, buttons, prev_buttons)
        elif self.stage == STAGE_BOULDERS:
            self._update_boulders(dt, buttons, prev_buttons)
        elif self.stage == STAGE_RESCUE:
            self._update_rescue(dt, buttons, prev_buttons)

    def _update_vines(self, dt: float, buttons: int, prev_buttons: int) -> None:
        sway_spd = 3.5 + self.expedition_round * 0.2
        self.vine_angle[0] = math.sin(self.state_timer * sway_spd) * 0.7
        self.vine_angle[1] = math.sin(self.state_timer * sway_spd + 1.6) * 0.7

        v_len = 7.0
        if not self.in_air:
            cur = self.current_vine
            self.px = self.vine_x[cur] + math.sin(self.vine_angle[cur]) * v_len
            self.py = 2.0 + math.cos(self.vine_angle[cur]) * v_len

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.in_air = True
                self.pvx = math.cos(self.vine_angle[cur]) * 7.5
                self.pvy = -math.sin(self.vine_angle[cur]) * 7.5 - 2.0
        else:
            self.pvy += 12.0 * dt
            self.px += self.pvx * dt
            self.py += self.pvy * dt

            next_v = 1 - self.current_vine
            v_tip_x = self.vine_x[next_v] + math.sin(self.vine_angle[next_v]) * v_len
            v_tip_y = 2.0 + math.cos(self.vine_angle[next_v]) * v_len

            dist = math.sqrt((self.px - v_tip_x) ** 2 + (self.py - v_tip_y) ** 2)
            if dist < 1.4 and self.pvy > -1.0:
                self.in_air = False
                self.current_vine = next_v
                self.progress += 25.0
                self.score += 100
                if self.progress >= 100.0:
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 0.0

            if self.py >= 15.0:
                self.state = STATE_PLAYER_DYING
                self.state_timer = 0.0

    def _update_river(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.oxygen -= dt
        if self.py <= 2.5:
            self.oxygen = 30.0
        if self.oxygen <= 0.0:
            self.state = STATE_PLAYER_DYING
            self.state_timer = 0.0
            return

        swim_spd = 4.5
        if buttons & KEY_UP:
            self.py -= swim_spd * dt
        if buttons & KEY_DOWN:
            self.py += swim_spd * dt
        if buttons & KEY_LEFT:
            self.px -= swim_spd * dt
        if buttons & KEY_RIGHT:
            self.px += swim_spd * dt
            self.progress += 5.0 * dt

        if self.px < 1.0:
            self.px = 1.0
        elif self.px > 14.5:
            self.px = 2.0
            self.progress += 35.0

        if self.py < 2.0:
            self.py = 2.0
        elif self.py > 14.0:
            self.py = 14.0

        if self.stab_timer > 0.0:
            self.stab_timer -= dt
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.stab_timer <= 0.0:
                self.is_stabbing = True
                self.stab_timer = 0.4
        if self.stab_timer <= 0.0:
            self.is_stabbing = False

        for i in range(3):
            self.croc_x[i] += self.croc_vx[i] * dt
            if self.croc_x[i] < -2.0:
                self.croc_x[i] = 17.5
                self.croc_mouth_open[i] = (random.random() < 0.5)

            dx = abs(self.px - self.croc_x[i])
            dy = abs(self.py - self.croc_y[i])
            if dx < 1.2 and dy < 0.9:
                if self.is_stabbing and not self.croc_mouth_open[i]:
                    self.croc_x[i] = -5.0
                    self.score += 200
                else:
                    self.state = STATE_PLAYER_DYING
                    self.state_timer = 0.0
                    break

        if self.progress >= 100.0:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _update_boulders(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.is_ducking = (buttons & KEY_DOWN) != 0

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not self.is_jumping:
                self.is_jumping = True
                self.pvy = -8.5

        if self.is_jumping:
            self.pvy += 18.0 * dt
            self.py += self.pvy * dt
            if self.py >= 13.0:
                self.py = 13.0
                self.pvy = 0.0
                self.is_jumping = False

        if buttons & KEY_RIGHT:
            self.px += 4.0 * dt
            self.progress += 8.0 * dt
        if buttons & KEY_LEFT:
            self.px -= 4.0 * dt

        if self.px < 1.5:
            self.px = 1.5
        elif self.px > 14.0:
            self.px = 2.0
            self.progress += 35.0

        for i in range(3):
            self.boulder_x[i] += self.boulder_vx[i] * dt
            if self.boulder_x[i] < -2.0:
                self.boulder_x[i] = 17.5
                self.boulder_is_high[i] = (random.random() < 0.5)

            b_y = 10.5 if self.boulder_is_high[i] else 13.0
            dx = abs(self.px - self.boulder_x[i])
            dy = abs(self.py - b_y)

            if dx < 0.9:
                if self.boulder_is_high[i]:
                    if not self.is_ducking:
                        self.state = STATE_PLAYER_DYING
                        self.state_timer = 0.0
                        break
                else:
                    if dy < 0.8:
                        self.state = STATE_PLAYER_DYING
                        self.state_timer = 0.0
                        break

        if self.progress >= 100.0:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _update_rescue(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.native_x += self.native_vx * dt
        if self.native_x < 6.0:
            self.native_x = 6.0
            self.native_vx = -self.native_vx
        elif self.native_x > 11.0:
            self.native_x = 11.0
            self.native_vx = -self.native_vx

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not self.is_jumping:
                self.is_jumping = True
                self.pvy = -9.0
                self.pvx = 4.5

        if self.is_jumping:
            self.pvy += 16.0 * dt
            self.px += self.pvx * dt
            self.py += self.pvy * dt
            if self.py >= 13.0:
                self.py = 13.0
                self.pvx = 0.0
                self.pvy = 0.0
                self.is_jumping = False

        if buttons & KEY_LEFT:
            self.px -= 3.5 * dt
        if buttons & KEY_RIGHT:
            self.px += 3.5 * dt

        if self.px < 1.0:
            self.px = 1.0

        if abs(self.px - self.native_x) < 0.85 and self.py >= 12.0:
            self.state = STATE_PLAYER_DYING
            self.state_timer = 0.0
            return

        if self.px >= 12.0 and self.py <= 8.5 and self.is_jumping:
            self.maiden_rescued = True
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        elif len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        if self.stage == STAGE_VINES:
            for x in range(16):
                set_pixel(x, 1, 30, 120, 40)
            for v in range(2):
                vx = int(round(self.vine_x[v] + math.sin(self.vine_angle[v]) * 7.0))
                vy = int(round(2.0 + math.cos(self.vine_angle[v]) * 7.0))
                set_pixel(int(self.vine_x[v]), 2, 60, 160, 40)
                set_pixel(vx, vy, 120, 220, 60)
            for x in range(16):
                set_pixel(x, 15, 15, 40, 20)
        elif self.stage == STAGE_RIVER:
            for y in range(2, 15):
                for x in range(16):
                    set_pixel(x, y, 10, 40, 140)
            for c in range(3):
                cx = int(round(self.croc_x[c]))
                cy = int(round(self.croc_y[c]))
                set_pixel(cx, cy, 40, 160, 60)
                set_pixel(cx - 1, cy, 30, 120, 40)
                if self.croc_mouth_open[c]:
                    set_pixel(cx + 1, cy, 255, 60, 40)
            ox_pips = int(self.oxygen / 2.0)
            for o in range(min(16, ox_pips)):
                set_pixel(o, 0, 0, 220, 255)
        elif self.stage == STAGE_BOULDERS:
            for x in range(16):
                set_pixel(x, 14, 140, 90, 40)
                set_pixel(x, 15, 100, 60, 30)
            for b in range(3):
                bx = int(round(self.boulder_x[b]))
                by = int(round(10.5 if self.boulder_is_high[b] else 13.0))
                set_pixel(bx, by, 180, 160, 140)
        elif self.stage == STAGE_RESCUE:
            for x in range(16):
                set_pixel(x, 14, 100, 60, 30)
            set_pixel(13, 13, 255, 60, 20)
            set_pixel(13, 12, 60, 60, 60)
            set_pixel(13, int(round(self.maiden_y)), 255, 200, 220)
            nx = int(round(self.native_x))
            set_pixel(nx, 13, 200, 120, 40)
            set_pixel(nx - 1, 13, 255, 255, 255)

        px_s = int(round(self.px))
        py_s = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px_s, py_s, 240, 210, 160)
            set_pixel(px_s, py_s - 1, 255, 220, 40)
            if self.stage == STAGE_RIVER and self.is_stabbing:
                set_pixel(px_s + 1, py_s, 255, 255, 255)
        elif self.state == STATE_PLAYER_DYING:
            set_pixel(px_s, py_s, 255, 60, 40)
            set_pixel(px_s - 1, py_s, 255, 200, 0)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 255, 220, 40)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "stage": self.stage,
            "score": self.score,
            "lives": self.lives,
            "progress": self.progress,
            "oxygen": self.oxygen,
        }
