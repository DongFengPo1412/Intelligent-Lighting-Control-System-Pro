"""
Game #091: 棒球杀手 / 忍者棒球 (Ninja Baseball Bat Man 1993 / Irem)
Baseball bat bunts popping enemies airborne, home-run smash out of the park & base-stealing slides.
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

STATE_INNING = 0
STATE_HERO_HIT = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3

ACTION_IDLE = 0
ACTION_SWING = 1
ACTION_BUNT = 2
ACTION_HOMERUN = 3
ACTION_SLIDE = 4

MAX_THUGS = 3


class Game091NinjaBaseball(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_INNING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.inning = 1
        self.home_runs = 0
        self.thugs_defeated = 0

        # Ninja Batter (Jose)
        self.px = 3.0
        self.py = 12.0
        self.facing = 1
        self.action_state = ACTION_IDLE
        self.action_timer = 0.0

        self.thugs: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 91

    @property
    def name(self) -> str:
        return "棒球杀手"

    @property
    def english_name(self) -> str:
        return "Ninja Baseball Bat Man"

    @property
    def release_year(self) -> int:
        return 1993

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "棒球短打挑空接全垒暴击与盗垒铲摔"

    def get_name(self) -> str:
        return "Ninja Baseball Bat Man (1993)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.inning = 1
        self.home_runs = 0
        self._reset_inning(hard_reset=True)

    def _reset_inning(self, hard_reset: bool = False) -> None:
        self.state = STATE_INNING
        self.state_timer = 0.0
        self.thugs_defeated = 0

        self.px = 3.0
        self.py = 12.0
        self.facing = 1
        self.action_state = ACTION_IDLE
        self.action_timer = 0.0

        self.thugs = []
        for i in range(MAX_THUGS):
            self.thugs.append({
                "x": 11.0 + i * 2.0,
                "y": 9.0 + (i * 2.0),
                "vx": -1.6,
                "vy": 0.0,
                "hp": 2,
                "is_airborne": False,
                "is_homerun_flying": False,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_HERO_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_inning(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.inning += 1
                self._reset_inning(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_thugs(dt)
        self._check_bat_combat()

        if self.thugs_defeated >= 6:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.action_timer > 0.0:
            self.action_timer -= dt
            if self.action_state == ACTION_SLIDE:
                self.px += self.facing * 8.5 * dt
            if self.action_timer <= 0.0:
                self.action_state = ACTION_IDLE

        if self.action_state == ACTION_IDLE:
            move_speed = 5.5
            if buttons & KEY_LEFT:
                self.px -= move_speed * dt
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.px += move_speed * dt
                self.facing = 1
            if buttons & KEY_UP:
                self.py -= move_speed * 0.7 * dt
            if buttons & KEY_DOWN:
                self.py += move_speed * 0.7 * dt

            self.px = max(1.0, min(14.5, self.px))
            self.py = max(8.0, min(14.0, self.py))

            # 1. Bunt (Up + Button A)
            if (buttons & KEY_UP) and (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.action_state = ACTION_BUNT
                self.action_timer = 0.25
            # 2. Swing / Home Run (Button A)
            elif (buttons & KEY_A) and not (prev_buttons & KEY_A):
                found_airborne = False
                for t in self.thugs:
                    if t["active"] and t["is_airborne"] and not t["is_homerun_flying"]:
                        dx = (t["x"] - self.px) * self.facing
                        dy = abs(t["y"] - self.py)
                        if 0.0 < dx < 2.0 and dy < 2.5:
                            found_airborne = True
                            break

                if found_airborne:
                    self.action_state = ACTION_HOMERUN
                    self.action_timer = 0.35
                else:
                    self.action_state = ACTION_SWING
                    self.action_timer = 0.22
            # 3. Slide Tackle (Button B)
            elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.action_state = ACTION_SLIDE
                self.action_timer = 0.35
                self.px += self.facing * 8.5 * dt

    def _update_thugs(self, dt: float) -> None:
        for idx, t in enumerate(self.thugs):
            if not t["active"]:
                if t["respawn_timer"] > 0.0:
                    t["respawn_timer"] -= dt
                else:
                    t["active"] = True
                    t["hp"] = 2
                    t["x"] = 14.0 + (idx * 1.5) % 3.0
                    t["y"] = 8.5 + (idx * 1.7) % 5.0
                    t["vx"] = -1.6
                    t["vy"] = 0.0
                    t["is_airborne"] = False
                    t["is_homerun_flying"] = False
                continue

            if t["is_homerun_flying"]:
                t["x"] += t["vx"] * dt
                t["y"] += t["vy"] * dt
                t["vy"] += 8.0 * dt
                if t["x"] < -3.0 or t["x"] > 18.0 or t["y"] < -3.0:
                    t["active"] = False
                    t["is_homerun_flying"] = False
                    t["respawn_timer"] = 2.0
                continue

            if t["is_airborne"]:
                t["y"] += t["vy"] * dt
                t["vy"] += 14.0 * dt
                if t["vy"] >= 0.0 and t["y"] >= 12.0:
                    t["y"] = 12.0
                    t["vy"] = 0.0
                    t["is_airborne"] = False
                continue

            # Walking AI
            dx = self.px - t["x"]
            dy = self.py - t["y"]
            t["x"] += (1.0 if dx > 0.0 else -1.0) * 1.5 * dt
            t["y"] += (1.0 if dy > 0.0 else -1.0) * 0.8 * dt

    def _check_bat_combat(self) -> None:
        for t in self.thugs:
            if not t["active"] or t["is_homerun_flying"]:
                continue

            dx = (t["x"] - self.px) * self.facing
            dy = abs(t["y"] - self.py)

            if self.action_state == ACTION_HOMERUN:
                if 0.0 < dx < 2.0 and dy < 2.5 and t["is_airborne"]:
                    t["is_airborne"] = False
                    t["is_homerun_flying"] = True
                    t["vx"] = self.facing * 16.0
                    t["vy"] = -7.5
                    t["hp"] = 0
                    self.score += 500
                    self.home_runs += 1
                    self.thugs_defeated += 1
                    continue

            if self.action_state == ACTION_BUNT:
                if 0.0 < dx < 1.6 and dy < 1.3 and not t["is_airborne"]:
                    t["is_airborne"] = True
                    t["vy"] = -6.5
                    t["vx"] = self.facing * 0.8
                    self.score += 50
                    continue

            if self.action_state == ACTION_SWING:
                if 0.0 < dx < 1.8 and dy < 1.2 and not t["is_airborne"]:
                    t["hp"] -= 1
                    t["x"] += self.facing * 2.0
                    self.score += 100
                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
                    continue

            if self.action_state == ACTION_SLIDE:
                if -0.5 < dx < 1.5 and dy < 1.0:
                    t["hp"] -= 1
                    t["x"] += self.facing * 1.5
                    self.score += 120
                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
                    continue

            if self.action_state == ACTION_IDLE:
                dist = abs(t["x"] - self.px)
                if dist < 0.9 and dy < 0.8:
                    self.state = STATE_HERO_HIT
                    self.state_timer = 0.0
                    break

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

        # Green turf
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 25, 95, 30)

        # Infield dirt
        for y in range(7, 16):
            for x in range(1, 15):
                if (x + y >= 11) and (y - x <= 11):
                    set_pixel(x, y, 165, 115, 60)

        # Home base
        set_pixel(3, 13, 255, 255, 255)
        set_pixel(2, 13, 240, 240, 240)

        # Thugs
        for t in self.thugs:
            if not t["active"]:
                continue
            tx = int(round(t["x"]))
            ty = int(round(t["y"]))
            if t["is_homerun_flying"]:
                set_pixel(tx, ty, 255, 255, 255)
                set_pixel(tx + 1, ty, 255, 60, 60)
                set_pixel(tx, ty - 1, 255, 220, 0)
            elif t["is_airborne"]:
                set_pixel(tx, ty, 40, 100, 180)
                set_pixel(tx, ty - 1, 255, 255, 255)
            else:
                set_pixel(tx, ty, 40, 90, 160)
                set_pixel(tx, ty - 1, 240, 240, 240)
                set_pixel(tx - 1, ty - 1, 160, 90, 30)

        # Batter
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_HERO_HIT:
            set_pixel(px, py, 255, 50, 0)
            set_pixel(px, py - 1, 255, 220, 0)
        else:
            if self.action_state == ACTION_SLIDE:
                set_pixel(px, py, 220, 30, 30)
                set_pixel(px + self.facing, py, 240, 190, 140)
                set_pixel(px - self.facing, py, 200, 150, 80)
            elif self.action_state == ACTION_HOMERUN:
                set_pixel(px, py, 220, 30, 30)
                set_pixel(px, py - 1, 240, 190, 140)
                set_pixel(px + self.facing, py - 1, 255, 230, 0)
                set_pixel(px + self.facing * 2, py - 1, 255, 255, 180)
                set_pixel(px + self.facing, py - 2, 255, 200, 0)
            elif self.action_state == ACTION_BUNT:
                set_pixel(px, py, 220, 30, 30)
                set_pixel(px, py - 1, 240, 190, 140)
                set_pixel(px + self.facing, py - 1, 200, 140, 50)
            elif self.action_state == ACTION_SWING:
                set_pixel(px, py, 220, 30, 30)
                set_pixel(px, py - 1, 240, 190, 140)
                set_pixel(px + self.facing, py - 1, 220, 160, 60)
            else:
                set_pixel(px, py, 220, 30, 30)
                set_pixel(px, py - 1, 240, 190, 140)
                set_pixel(px, py - 2, 200, 20, 20)
                set_pixel(px - self.facing, py - 2, 200, 140, 50)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 50, 50)
        for hr in range(min(self.home_runs, 4)):
            set_pixel(15 - hr, 0, 255, 220, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "inning": self.inning,
            "action_state": self.action_state,
            "home_runs": self.home_runs,
            "thugs_defeated": self.thugs_defeated,
            "player_x": self.px,
            "player_y": self.py,
        }
