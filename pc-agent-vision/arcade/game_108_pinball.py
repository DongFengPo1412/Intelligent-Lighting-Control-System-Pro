"""
Game #108: 经典街机弹珠台 (Pinball 1984 / Nintendo)
Kinetic table physics: Left & Right flippers, spring plunger launch lane,
neon repelling bumpers, top rollover lane score multipliers, and bottom drain avoidance.
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

STATE_PLUNGER_READY = 0
STATE_BALL_IN_PLAY = 1
STATE_BALL_DRAINED = 2
STATE_GAME_OVER = 3

NUM_BUMPERS = 3
NUM_ROLLOVERS = 3


class Game108Pinball(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLUNGER_READY
        self.state_timer = 0.0
        self.score = 0
        self.balls_left = 3
        self.multiplier = 1

        self.plunger_charge = 0.0

        self.ball_x = 14.5
        self.ball_y = 14.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0

        self.left_flipper_up = False
        self.right_flipper_up = False

        self.bumpers: List[Dict[str, Any]] = []
        self.rollovers: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 108

    @property
    def name(self) -> str:
        return "街机弹珠台"

    @property
    def english_name(self) -> str:
        return "Pinball"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "左右双挡板重力反弹、弹簧柱蓄能发射、圆顶撞击器与落球回卷倍率"

    def get_name(self) -> str:
        return "Pinball (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.balls_left = 3
        self.multiplier = 1
        self._init_table()
        self._reset_ball_to_plunger()

    def _init_table(self) -> None:
        self.state = STATE_PLUNGER_READY
        self.state_timer = 0.0
        self.plunger_charge = 0.0
        self.left_flipper_up = False
        self.right_flipper_up = False

        self.bumpers = [
            {"x": 5.0, "y": 5.0, "flash_timer": 0.0},
            {"x": 9.0, "y": 5.0, "flash_timer": 0.0},
            {"x": 7.0, "y": 8.0, "flash_timer": 0.0},
        ]

        self.rollovers = [
            {"x": 4, "y": 3, "lit": False},
            {"x": 7, "y": 3, "lit": False},
            {"x": 10, "y": 3, "lit": False},
        ]

    def _reset_ball_to_plunger(self) -> None:
        self.state = STATE_PLUNGER_READY
        self.state_timer = 0.0
        self.ball_x = 14.5
        self.ball_y = 14.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.plunger_charge = 0.0

    def launch_ball(self, power: float) -> None:
        if self.state == STATE_PLUNGER_READY:
            self.state = STATE_BALL_IN_PLAY
            self.ball_vx = 0.0
            self.ball_vy = -max(10.0, min(18.0, power))

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_BALL_DRAINED:
            if self.state_timer > 1.8:
                self.balls_left -= 1
                if self.balls_left <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_ball_to_plunger()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_flippers_and_plunger(dt, buttons, prev_buttons)

        if self.state == STATE_BALL_IN_PLAY:
            self._update_ball_physics(dt)
            self._check_bumper_collisions()
            self._check_flipper_collisions()
            self._check_rollovers()

        for b in self.bumpers:
            if b["flash_timer"] > 0.0:
                b["flash_timer"] -= dt

    def _update_flippers_and_plunger(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.left_flipper_up = (buttons & KEY_A) != 0
        self.right_flipper_up = (buttons & KEY_B) != 0

        if self.state == STATE_PLUNGER_READY:
            if buttons & KEY_DOWN:
                self.plunger_charge = min(18.0, self.plunger_charge + 14.0 * dt)
            elif prev_buttons & KEY_DOWN:
                self.launch_ball(self.plunger_charge)
            elif (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
                self.launch_ball(15.0)

    def _update_ball_physics(self, dt: float) -> None:
        self.ball_vy += 14.0 * dt
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        if self.ball_x >= 13.5:
            if self.ball_y <= 1.5 and self.ball_vy < 0.0:
                self.ball_x = 12.5
                self.ball_vx = -4.5
                self.ball_vy = 2.0
        else:
            if self.ball_x <= 1.0:
                self.ball_x = 1.0
                self.ball_vx = abs(self.ball_vx) * 0.8
            elif self.ball_x >= 13.0:
                self.ball_x = 13.0
                self.ball_vx = -abs(self.ball_vx) * 0.8

            if self.ball_y <= 1.0:
                self.ball_y = 1.0
                self.ball_vy = abs(self.ball_vy) * 0.8

        if self.ball_y >= 15.5:
            self.state = STATE_BALL_DRAINED
            self.state_timer = 0.0

    def _check_bumper_collisions(self) -> None:
        for b in self.bumpers:
            dx = self.ball_x - b["x"]
            dy = self.ball_y - b["y"]
            dist = math.hypot(dx, dy)
            if 0.01 < dist < 1.3:
                nx = dx / dist
                ny = dy / dist
                self.ball_vx = nx * 10.0
                self.ball_vy = ny * 10.0
                b["flash_timer"] = 0.25
                self.score += 100 * self.multiplier

    def _check_flipper_collisions(self) -> None:
        if 13.2 <= self.ball_y <= 14.6 and self.ball_vy > 0.0:
            # Left Flipper
            if 3.8 <= self.ball_x <= 7.0:
                if self.left_flipper_up:
                    self.ball_vy = -13.0
                    self.ball_vx = 3.5 + (self.ball_x - 3.8) * 2.0
                    self.score += 20 * self.multiplier
                else:
                    self.ball_vy = -abs(self.ball_vy) * 0.5
                    self.ball_vx = 2.0
                return

            # Right Flipper
            if 8.5 <= self.ball_x <= 11.8:
                if self.right_flipper_up:
                    self.ball_vy = -13.0
                    self.ball_vx = -3.5 - (11.8 - self.ball_x) * 2.0
                    self.score += 20 * self.multiplier
                else:
                    self.ball_vy = -abs(self.ball_vy) * 0.5
                    self.ball_vx = -2.0
                return

    def _check_rollovers(self) -> None:
        for r in self.rollovers:
            if abs(self.ball_x - float(r["x"])) < 1.0 and abs(self.ball_y - float(r["y"])) < 1.0:
                if not r["lit"]:
                    r["lit"] = True
                    self.score += 200
                    if all(item["lit"] for item in self.rollovers):
                        self.score += 1000
                        self.multiplier = min(4, self.multiplier + 1)
                        for item in self.rollovers:
                            item["lit"] = False

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

        for y in range(16):
            for x in range(1, 14):
                set_pixel(x, y, 10, 15, 40)

        for y in range(16):
            set_pixel(0, y, 180, 180, 200)
            set_pixel(13, y, 180, 180, 200)
            set_pixel(15, y, 180, 180, 200)
        for x in range(16):
            set_pixel(x, 0, 180, 180, 200)

        for r in self.rollovers:
            if r["lit"]:
                set_pixel(r["x"], r["y"], 255, 220, 0)
            else:
                set_pixel(r["x"], r["y"], 80, 80, 120)

        for b in self.bumpers:
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["flash_timer"] > 0.0:
                set_pixel(bx, by, 255, 255, 255)
                set_pixel(bx - 1, by, 255, 220, 0)
                set_pixel(bx + 1, by, 255, 220, 0)
                set_pixel(bx, by - 1, 255, 220, 0)
                set_pixel(bx, by + 1, 255, 220, 0)
            else:
                set_pixel(bx, by, 240, 40, 40)
                set_pixel(bx - 1, by, 200, 20, 20)
                set_pixel(bx + 1, by, 200, 20, 20)
                set_pixel(bx, by - 1, 200, 20, 20)
                set_pixel(bx, by + 1, 200, 20, 20)

        l_tip_y = 13 if self.left_flipper_up else 14
        set_pixel(4, 14, 255, 140, 20)
        set_pixel(5, 14, 255, 140, 20)
        set_pixel(6, l_tip_y, 255, 200, 40)

        r_tip_y = 13 if self.right_flipper_up else 14
        set_pixel(9, r_tip_y, 255, 200, 40)
        set_pixel(10, 14, 255, 140, 20)
        set_pixel(11, 14, 255, 140, 20)

        set_pixel(7, 15, 0, 0, 0)
        set_pixel(8, 15, 0, 0, 0)

        if self.state == STATE_PLUNGER_READY:
            compress = int(self.plunger_charge / 6.0)
            set_pixel(14, 15, 255, 60, 20)
            set_pixel(14, 15 - compress, 255, 200, 0)

        px = int(round(self.ball_x))
        py = int(round(self.ball_y))
        if self.state != STATE_BALL_DRAINED:
            set_pixel(px, py, 255, 255, 255)

        if self.multiplier > 1:
            for m in range(self.multiplier):
                set_pixel(0, m * 2, 0, 255, 150)

        for b in range(min(self.balls_left, 3)):
            set_pixel(15, b * 2, 255, 220, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "balls_left": self.balls_left,
            "multiplier": self.multiplier,
            "ball_x": self.ball_x,
            "ball_y": self.ball_y,
            "left_flipper_up": self.left_flipper_up,
            "right_flipper_up": self.right_flipper_up,
        }
