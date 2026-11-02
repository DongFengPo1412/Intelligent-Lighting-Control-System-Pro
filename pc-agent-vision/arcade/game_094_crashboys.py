"""
Game #094: 热血新纪录 / 撑杆跳与楼顶跨越 (Crash 'n' the Boys: Street Challenge 1992 / Technos)
Rooftop sprint, flexible vaulting pole launch, mid-air dropkicks & knocking rivals off building edges.
"""

from typing import List, Dict, Any
import math
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

STATE_RUNNING = 0
STATE_VAULTING = 1
STATE_AIRBORNE = 2
STATE_HERO_FALL = 3
STATE_STAGE_CLEAR = 4
STATE_GAME_OVER = 5

MAX_RIVALS = 2


class Game094CrashBoys(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_RUNNING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.rivals_defeated = 0

        # Kunio / Crash
        self.px = 3.0
        self.py = 13.0
        self.run_speed = 6.0
        self.pole_flex = 0.0
        self.air_vx = 0.0
        self.air_vy = 0.0
        self.is_dropkicking = False

        # Distance & Gaps
        self.distance = 0.0
        self.stage_length = 300.0
        self.next_gap_dist = 50.0
        self.gap_width = 18.0

        self.rivals: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 94

    @property
    def name(self) -> str:
        return "热血新纪录"

    @property
    def english_name(self) -> str:
        return "Crash 'n' the Boys"

    @property
    def release_year(self) -> int:
        return 1992

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "大楼楼顶撑杆弯曲弹射跳跃与空中飞踢摔敌"

    def get_name(self) -> str:
        return "Crash 'n' the Boys (1992)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._reset_event(hard_reset=True)

    def _reset_event(self, hard_reset: bool = False) -> None:
        self.state = STATE_RUNNING
        self.state_timer = 0.0
        self.rivals_defeated = 0

        self.px = 3.0
        self.py = 13.0
        self.run_speed = 6.0
        self.pole_flex = 0.0
        self.air_vx = 0.0
        self.air_vy = 0.0
        self.is_dropkicking = False

        self.distance = 0.0
        self.stage_length = 300.0 + self.round * 80.0
        self.next_gap_dist = 50.0
        self.gap_width = 18.0

        self.rivals = []
        for i in range(MAX_RIVALS):
            self.rivals.append({
                "x": 6.0 + i * 4.0,
                "y": 13.0,
                "vx": 5.2 + i * 0.8,
                "knocked_down": False,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_HERO_FALL:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_event(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.round += 1
                self._reset_event(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_rivals(dt)
        self._check_air_combat()

        if self.distance >= self.stage_length:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1500

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_RUNNING:
            if buttons & KEY_RIGHT:
                self.run_speed = min(10.5, self.run_speed + 12.0 * dt)
            elif buttons & KEY_LEFT:
                self.run_speed = max(4.0, self.run_speed - 8.0 * dt)

            self.distance += self.run_speed * dt

            if self.next_gap_dist <= self.distance <= self.next_gap_dist + self.gap_width:
                self.state = STATE_HERO_FALL
                self.state_timer = 0.0
                return

            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.state = STATE_VAULTING
                self.pole_flex = 0.1

        elif self.state == STATE_VAULTING:
            if buttons & KEY_B:
                self.pole_flex = min(1.0, self.pole_flex + 2.4 * dt)
                self.distance += (self.run_speed * 0.4) * dt

            if not (buttons & KEY_B) or ((buttons & KEY_A) and not (prev_buttons & KEY_A)):
                self.state = STATE_AIRBORNE
                self.air_vx = self.run_speed * (0.8 + self.pole_flex * 0.7)
                self.air_vy = -(6.5 + self.pole_flex * 7.5)
                self.score += int(self.pole_flex * 100)
                self.is_dropkicking = False

        elif self.state == STATE_AIRBORNE:
            self.air_vy += 14.5 * dt
            self.py += self.air_vy * dt
            self.distance += self.air_vx * dt

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.is_dropkicking = True
                self.air_vx += 1.8

            if self.air_vy >= 0.0 and self.py >= 13.0:
                self.py = 13.0
                if self.next_gap_dist <= self.distance <= self.next_gap_dist + self.gap_width:
                    self.state = STATE_HERO_FALL
                    self.state_timer = 0.0
                else:
                    self.state = STATE_RUNNING
                    self.score += 200
                    self.is_dropkicking = False
                    self.next_gap_dist = self.distance + 70.0

    def _update_rivals(self, dt: float) -> None:
        for r in self.rivals:
            if not r["active"]:
                continue
            if r["knocked_down"]:
                r["y"] += 12.0 * dt
                if r["y"] > 18.0:
                    r["active"] = False
                continue

            r["x"] += (r["vx"] - self.run_speed) * dt
            if r["x"] < -3.0:
                r["x"] = 18.0
            elif r["x"] > 18.0:
                r["x"] = -2.0

    def _check_air_combat(self) -> None:
        for r in self.rivals:
            if not r["active"] or r["knocked_down"]:
                continue
            dx = abs(r["x"] - self.px)
            dy = abs(r["y"] - self.py)

            if dx < 1.3 and dy < 1.4:
                if self.is_dropkicking or self.state == STATE_AIRBORNE:
                    r["knocked_down"] = True
                    self.score += 300
                    self.rivals_defeated += 1

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(len(fb)):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # Sunset skyline
        for y in range(10):
            for x in range(16):
                set_pixel(x, y, 160 + y * 6, 70 + y * 4, 30)

        # Distant skyscrapers
        for x in range(16):
            if (x % 4) != 0:
                set_pixel(x, 7, 50, 40, 60)
                set_pixel(x, 8, 50, 40, 60)
                set_pixel(x, 9, 50, 40, 60)

        # Rooftop
        is_in_gap = (self.next_gap_dist <= self.distance <= self.next_gap_dist + self.gap_width)
        for y in range(14, 16):
            for x in range(16):
                if is_in_gap and 4 <= x <= 12:
                    set_pixel(x, y, 10, 10, 15)
                else:
                    set_pixel(x, y, 70, 75, 80)

        set_pixel(1, 13, 140, 140, 140)
        set_pixel(14, 13, 180, 80, 40)

        # Rivals
        for r in self.rivals:
            if not r["active"]:
                continue
            rx = int(round(r["x"]))
            ry = int(round(r["y"]))
            if r["knocked_down"]:
                set_pixel(rx, ry, 40, 80, 220)
                set_pixel(rx, ry - 1, 255, 200, 140)
            else:
                set_pixel(rx, ry, 40, 80, 220)
                set_pixel(rx, ry - 1, 255, 200, 140)
                set_pixel(rx - 1, ry - 1, 40, 80, 220)

        # Hero
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_HERO_FALL:
            set_pixel(px, py, 255, 50, 50)
            set_pixel(px, py - 1, 255, 220, 0)
        elif self.state == STATE_VAULTING:
            bend_x = px + 1 + int(round(self.pole_flex * 2.0))
            set_pixel(bend_x, py, 220, 180, 80)
            set_pixel(px, py - 1, 255, 255, 255)
            set_pixel(px, py - 2, 255, 200, 140)
            set_pixel(px, py, 220, 40, 40)
        elif self.state == STATE_AIRBORNE:
            if self.is_dropkicking:
                set_pixel(px, py, 255, 255, 255)
                set_pixel(px + 1, py, 220, 40, 40)
                set_pixel(px + 2, py, 255, 220, 0)
                set_pixel(px - 1, py - 1, 255, 200, 140)
            else:
                set_pixel(px, py, 220, 40, 40)
                set_pixel(px, py - 1, 255, 255, 255)
                set_pixel(px, py - 2, 255, 200, 140)
        else:
            set_pixel(px, py, 220, 40, 40)
            set_pixel(px, py - 1, 255, 255, 255)
            set_pixel(px, py - 2, 255, 200, 140)
            set_pixel(px + 1, py - 1, 220, 180, 80)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 60, 60)
        flex_bars = int(self.pole_flex * 4.0)
        for f in range(flex_bars):
            set_pixel(15 - f, 0, 255, 220, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "round": self.round,
            "run_speed": self.run_speed,
            "pole_flex": self.pole_flex,
            "distance": self.distance,
            "is_dropkicking": self.is_dropkicking,
            "rivals_defeated": self.rivals_defeated,
            "player_x": self.px,
            "player_y": self.py,
        }
