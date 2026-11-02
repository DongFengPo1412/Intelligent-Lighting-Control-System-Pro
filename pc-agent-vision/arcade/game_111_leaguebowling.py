"""
Game #111: 街机保龄球 (League Bowling 1990 / SNK Neo-Geo)
Authentic 10-pin alley physics, hook/straight spin selection,
oscillating power gauge bar, gutter detection, kinetic domino chain scatter,
and Strike/Spare celebratory frame sequences.
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

STATE_AIMING = 0
STATE_POWER_GAUGE = 1
STATE_BALL_ROLLING = 2
STATE_FRAME_RESULT = 3
STATE_GAME_OVER = 4

NUM_PINS = 10
TOTAL_FRAMES = 5


class Game111LeagueBowling(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_AIMING
        self.state_timer = 0.0
        self.score = 0
        self.current_frame = 1
        self.current_roll = 1
        self.pins_knocked_down = 0

        self.bowler_x = 7.5
        self.gauge_val = 0.0
        self.gauge_dir = 1.0
        self.throw_power = 10.0
        self.hook_spin = 0  # -1 = Left hook, 0 = Straight, 1 = Right hook

        self.ball_x = 7.5
        self.ball_y = 13.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.in_gutter = False

        self.pins: List[Dict[str, Any]] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 111

    @property
    def name(self) -> str:
        return "街机保龄球"

    @property
    def english_name(self) -> str:
        return "League Bowling"

    @property
    def release_year(self) -> int:
        return 1990

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "球道瞄准横移、旋球弧线控制、能量游标出球与十瓶连环多米诺碰撞"

    def get_name(self) -> str:
        return "League Bowling (1990)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.current_frame = 1
        self.current_roll = 1
        self._init_frame()

    def _init_frame(self) -> None:
        self.state = STATE_AIMING
        self.state_timer = 0.0
        self.bowler_x = 7.5
        self.gauge_val = 0.0
        self.gauge_dir = 1.0
        self.hook_spin = 0
        self.pins_knocked_down = 0

        self.ball_x = 7.5
        self.ball_y = 13.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.in_gutter = False

        if self.current_roll == 1:
            self._reset_pins()

    def _reset_pins(self) -> None:
        # Standard 10-pin triangle coordinates
        self.pins = [
            # Headpin
            {"x": 7.5, "y": 5.0, "standing": True},
            # Row 2
            {"x": 6.5, "y": 4.0, "standing": True},
            {"x": 8.5, "y": 4.0, "standing": True},
            # Row 3
            {"x": 5.5, "y": 3.0, "standing": True},
            {"x": 7.5, "y": 3.0, "standing": True},
            {"x": 9.5, "y": 3.0, "standing": True},
            # Row 4 (Back row)
            {"x": 4.5, "y": 2.0, "standing": True},
            {"x": 6.5, "y": 2.0, "standing": True},
            {"x": 8.5, "y": 2.0, "standing": True},
            {"x": 10.5, "y": 2.0, "standing": True},
        ]

    def force_throw(self, power: float, hook: int) -> None:
        self.throw_power = power
        self.hook_spin = hook
        self.ball_x = self.bowler_x
        self.ball_y = 13.0
        self.ball_vy = -self.throw_power
        self.ball_vx = float(self.hook_spin) * 0.5
        self.state = STATE_BALL_ROLLING

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_FRAME_RESULT:
            if self.state_timer > 1.8:
                if self.current_roll == 1 and self.pins_knocked_down < 10:
                    # Roll 2: Spare attempt
                    self.current_roll = 2
                    self._init_frame()
                else:
                    # Advance to next frame
                    self.current_frame += 1
                    self.current_roll = 1
                    if self.current_frame > TOTAL_FRAMES:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
                    else:
                        self._init_frame()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_AIMING or self.state == STATE_POWER_GAUGE:
            self._update_aiming_and_gauge(dt, buttons, prev_buttons)
        elif self.state == STATE_BALL_ROLLING:
            self._update_ball_roll(dt)
            self._check_pin_collisions()

    def _update_aiming_and_gauge(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_AIMING:
            move_spd = 5.0
            if buttons & KEY_LEFT:
                self.bowler_x = max(4.0, self.bowler_x - move_spd * dt)
            if buttons & KEY_RIGHT:
                self.bowler_x = min(11.0, self.bowler_x + move_spd * dt)

            # Button B cycles hook spin
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                if self.hook_spin == 0:
                    self.hook_spin = -1
                elif self.hook_spin == -1:
                    self.hook_spin = 1
                else:
                    self.hook_spin = 0

            # Button A locks aim and starts power gauge
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.state = STATE_POWER_GAUGE
                self.gauge_val = 0.2
                self.gauge_dir = 1.0

        elif self.state == STATE_POWER_GAUGE:
            self.gauge_val += self.gauge_dir * 2.8 * dt
            if self.gauge_val >= 1.0:
                self.gauge_val = 1.0
                self.gauge_dir = -1.0
            elif self.gauge_val <= 0.1:
                self.gauge_val = 0.1
                self.gauge_dir = 1.0

            # Button A releases the ball
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.throw_power = 8.0 + self.gauge_val * 10.0
                self.force_throw(self.throw_power, self.hook_spin)

    def _update_ball_roll(self, dt: float) -> None:
        if not self.in_gutter:
            self.ball_vx += float(self.hook_spin) * 3.8 * dt

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        # Gutter collision checks
        if self.ball_x <= 2.8:
            self.ball_x = 2.4
            self.ball_vx = 0.0
            self.in_gutter = True
        elif self.ball_x >= 12.2:
            self.ball_x = 12.6
            self.ball_vx = 0.0
            self.in_gutter = True

        # Ball reaches pit
        if self.ball_y <= 1.0:
            self._conclude_roll()

    def _check_pin_collisions(self) -> None:
        if self.in_gutter:
            return

        for i, pin in enumerate(self.pins):
            if not pin["standing"]:
                continue

            dx = abs(self.ball_x - pin["x"])
            dy = abs(self.ball_y - pin["y"])

            if dx < 0.9 and dy < 0.9:
                pin["standing"] = False
                self.pins_knocked_down += 1
                self.score += 10

                # Domino chain reaction to nearby standing pins
                for j, n_pin in enumerate(self.pins):
                    if n_pin["standing"]:
                        ndx = abs(pin["x"] - n_pin["x"])
                        ndy = abs(pin["y"] - n_pin["y"])
                        if ndx <= 1.4 and ndy <= 1.4:
                            n_pin["standing"] = False
                            self.pins_knocked_down += 1
                            self.score += 10

    def _conclude_roll(self) -> None:
        self.state = STATE_FRAME_RESULT
        self.state_timer = 0.0

        if self.current_roll == 1 and self.pins_knocked_down == 10:
            # STRIKE!
            self.score += 300
        elif self.current_roll == 2 and self.pins_knocked_down == 10:
            # SPARE!
            self.score += 150

    def render(self, fb: bytearray) -> None:
        if not fb or len(fb) < 16 * 16 * 3:
            return

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # Alley Architecture
        for y in range(16):
            # Gutters
            set_pixel(1, y, 40, 40, 45)
            set_pixel(2, y, 25, 25, 30)
            set_pixel(13, y, 25, 25, 30)
            set_pixel(14, y, 40, 40, 45)

            # Hardwood Lane
            for x in range(3, 13):
                plank = 220 if (x % 2 == 0) else 200
                set_pixel(x, y, plank, plank - 40, 80)

        # Range finder arrows at y=8
        set_pixel(5, 8, 120, 60, 20)
        set_pixel(7, 8, 120, 60, 20)
        set_pixel(8, 8, 120, 60, 20)
        set_pixel(10, 8, 120, 60, 20)

        # Pins
        for pin in self.pins:
            if not pin["standing"]:
                continue
            px = int(round(pin["x"]))
            py = int(round(pin["y"]))
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px, py - 1, 255, 30, 30)

        # Ball
        if self.state == STATE_BALL_ROLLING:
            bx = int(round(self.ball_x))
            by = int(round(self.ball_y))
            set_pixel(bx, by, 30, 60, 200)
            set_pixel(bx, by - 1, 200, 220, 255)

        # Bowler stance
        if self.state in (STATE_AIMING, STATE_POWER_GAUGE):
            bx = int(round(self.bowler_x))
            set_pixel(bx, 14, 230, 40, 30)
            set_pixel(bx, 15, 40, 80, 220)
            set_pixel(bx, 13, 255, 220, 160)

            hand_x = (bx - 1) if self.hook_spin <= 0 else (bx + 1)
            set_pixel(hand_x, 14, 30, 60, 200)

            # Power Gauge on left border
            if self.state == STATE_POWER_GAUGE:
                bars = int(self.gauge_val * 8.0)
                for b in range(bars):
                    set_pixel(0, 15 - b * 2, 255, 220, 0)

        # Splash result
        if self.state == STATE_FRAME_RESULT and self.pins_knocked_down == 10:
            for x in range(3, 13):
                set_pixel(x, 1, 255, 220, 0)

        # Hook indicator
        if self.hook_spin == -1:
            set_pixel(4, 0, 0, 255, 255)
        elif self.hook_spin == 1:
            set_pixel(11, 0, 0, 255, 255)

        # Frame counter
        for f in range(self.current_frame):
            set_pixel(0, f * 3, 255, 100, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "current_frame": self.current_frame,
            "current_roll": self.current_roll,
            "pins_knocked_down": self.pins_knocked_down,
            "bowler_x": self.bowler_x,
            "ball_x": self.ball_x,
            "ball_y": self.ball_y,
            "hook_spin": self.hook_spin,
            "throw_power": self.throw_power,
            "in_gutter": self.in_gutter,
        }
