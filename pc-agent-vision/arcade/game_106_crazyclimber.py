"""
Game #106: 疯狂攀爬者 (Crazy Climber 1980 / Nichibutsu)
Vertical skyscraper facade ascent: alternating hand grip climbing, slamming window finger pinches,
falling condor eggs and flowerpot evasion, and rooftop helicopter extraction.
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

STATE_CLIMBING = 0
STATE_SLIPPED_ONE_HAND = 1
STATE_FALL_OFF = 2
STATE_ROOFTOP_CLEAR = 3
STATE_GAME_OVER = 4

WINDOW_X = [3, 6, 9, 12]
WINDOW_Y = [2, 4, 6, 8, 10, 12]
NUM_WINDOW_COLS = 4
NUM_WINDOW_ROWS = 6
MAX_HAZARDS = 3


class Game106CrazyClimber(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_CLIMBING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.altitude = 0

        self.climber_col = 1
        self.climber_y = 13.0
        self.left_hand_grip = True
        self.right_hand_grip = True
        self.slip_recovery_timer = 0.0
        self.last_pull_hand = 0

        self.condor_x = 2.0
        self.condor_vx = 3.2
        self.condor_egg_timer = 1.5

        self.windows: List[List[Dict[str, Any]]] = []
        self.hazards: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 106

    @property
    def name(self) -> str:
        return "疯狂攀爬者"

    @property
    def english_name(self) -> str:
        return "Crazy Climber"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双手交替攀附摩天大楼、关窗夹手脱手失足自救、秃鹰落物规避与天台直升机接应"

    def get_name(self) -> str:
        return "Crazy Climber (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.altitude = 0
        self._init_building()

    def _init_building(self) -> None:
        self.state = STATE_CLIMBING
        self.state_timer = 0.0
        self.climber_col = 1
        self.climber_y = 13.0
        self.left_hand_grip = True
        self.right_hand_grip = True
        self.slip_recovery_timer = 0.0
        self.last_pull_hand = 0

        self.condor_x = 2.0
        self.condor_vx = 3.2
        self.condor_egg_timer = 1.5

        self.windows = []
        for r in range(NUM_WINDOW_ROWS):
            row = []
            for c in range(NUM_WINDOW_COLS):
                row.append({
                    "is_open": ((r + c) % 3 != 0),
                    "toggle_timer": 1.5 + float((r * 2 + c) % 3) * 0.8,
                    "has_hazard": (r == 1 and c == 2),
                })
            self.windows.append(row)

        self.hazards = [
            {"x": 0.0, "y": 0.0, "vy": 6.5, "is_condor_egg": False, "active": False}
            for _ in range(MAX_HAZARDS)
        ]

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_FALL_OFF:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._init_building()
            return

        if self.state == STATE_ROOFTOP_CLEAR:
            if self.state_timer > 2.2:
                self.altitude = 0
                self._init_building()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_climber(dt, buttons, prev_buttons)
        self._update_windows(dt)
        self._update_condor_and_hazards(dt)
        self._check_collisions()

        if self.altitude >= 80 and self.climber_y <= 2.2 and self.state != STATE_ROOFTOP_CLEAR:
            self.state = STATE_ROOFTOP_CLEAR
            self.state_timer = 0.0
            self.score += 3000

    def _update_climber(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_SLIPPED_ONE_HAND:
            self.slip_recovery_timer -= dt
            if not self.left_hand_grip and (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.left_hand_grip = True
                self.state = STATE_CLIMBING
                self.score += 50
            elif not self.right_hand_grip and (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.right_hand_grip = True
                self.state = STATE_CLIMBING
                self.score += 50

            if self.slip_recovery_timer <= 0.0:
                self.state = STATE_FALL_OFF
                self.state_timer = 0.0
            return

        if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
            if self.climber_col > 0:
                self.climber_col -= 1
        elif (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
            if self.climber_col < NUM_WINDOW_COLS - 1:
                self.climber_col += 1

        pull_left = (buttons & KEY_A) and not (prev_buttons & KEY_A)
        pull_right = (buttons & KEY_B) and not (prev_buttons & KEY_B)

        if pull_left or pull_right:
            ascend = 0.4
            if (pull_left and self.last_pull_hand == 2) or (pull_right and self.last_pull_hand == 1):
                ascend = 0.75
                self.score += 20
            else:
                self.score += 5

            self.last_pull_hand = 1 if pull_left else 2
            self.climber_y -= ascend

            if self.climber_y <= 3.0 and self.altitude < 80:
                self.climber_y += 4.0
                self.altitude += 10
                self.score += 200

                for r in range(NUM_WINDOW_ROWS - 1, 1, -1):
                    for c in range(NUM_WINDOW_COLS):
                        self.windows[r][c] = dict(self.windows[r - 2][c])

                for r in range(2):
                    for c in range(NUM_WINDOW_COLS):
                        self.windows[r][c] = {
                            "is_open": ((self.altitude + r + c) % 2 == 0),
                            "toggle_timer": 1.0 + float(c) * 0.5,
                            "has_hazard": ((r + c + self.altitude) % 5 == 0),
                        }

    def _update_windows(self, dt: float) -> None:
        for r in range(NUM_WINDOW_ROWS):
            for c in range(NUM_WINDOW_COLS):
                w = self.windows[r][c]
                w["toggle_timer"] -= dt
                if w["toggle_timer"] <= 0.0:
                    w["is_open"] = not w["is_open"]
                    w["toggle_timer"] = 2.0 + float((r * 3 + c) % 4) * 0.6

                    if not w["is_open"] and c == self.climber_col:
                        wy = float(WINDOW_Y[r])
                        if abs(self.climber_y - wy) < 0.9 and self.state == STATE_CLIMBING:
                            self.state = STATE_SLIPPED_ONE_HAND
                            self.slip_recovery_timer = 1.6
                            if self.last_pull_hand == 1:
                                self.left_hand_grip = False
                            else:
                                self.right_hand_grip = False

                    if w["is_open"] and w["has_hazard"]:
                        for h in self.hazards:
                            if not h["active"]:
                                h["active"] = True
                                h["x"] = float(WINDOW_X[c])
                                h["y"] = float(WINDOW_Y[r] + 1)
                                h["vy"] = 6.5
                                h["is_condor_egg"] = False
                                break

    def _update_condor_and_hazards(self, dt: float) -> None:
        self.condor_x += self.condor_vx * dt
        if self.condor_x <= 1.0:
            self.condor_x = 1.0
            self.condor_vx = abs(self.condor_vx)
        elif self.condor_x >= 14.0:
            self.condor_x = 14.0
            self.condor_vx = -abs(self.condor_vx)

        self.condor_egg_timer -= dt
        if self.condor_egg_timer <= 0.0:
            self.condor_egg_timer = 2.2
            for h in self.hazards:
                if not h["active"]:
                    h["active"] = True
                    h["x"] = self.condor_x
                    h["y"] = 2.0
                    h["vy"] = 5.5
                    h["is_condor_egg"] = True
                    break

        for h in self.hazards:
            if not h["active"]:
                continue
            h["y"] += h["vy"] * dt
            if h["y"] > 15.5:
                h["active"] = False

    def _check_collisions(self) -> None:
        cx = float(WINDOW_X[self.climber_col])
        cy = self.climber_y

        for h in self.hazards:
            if not h["active"]:
                continue
            dx = abs(cx - h["x"])
            dy = abs(cy - h["y"])
            if dx < 0.9 and dy < 1.1:
                h["active"] = False
                if self.state == STATE_CLIMBING:
                    self.state = STATE_SLIPPED_ONE_HAND
                    self.slip_recovery_timer = 1.6
                    self.left_hand_grip = False
                elif self.state == STATE_SLIPPED_ONE_HAND:
                    self.state = STATE_FALL_OFF
                    self.state_timer = 0.0
                return

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
            for x in range(1, 15):
                b_col = 60 if ((x + y) % 2 == 0) else 45
                set_pixel(x, y, b_col + 10, b_col, b_col - 5)

        for r in range(NUM_WINDOW_ROWS):
            wy = WINDOW_Y[r]
            for c in range(NUM_WINDOW_COLS):
                wx = WINDOW_X[c]
                if self.windows[r][c]["is_open"]:
                    set_pixel(wx, wy, 15, 20, 35)
                    set_pixel(wx + 1, wy, 15, 20, 35)
                    set_pixel(wx, wy + 1, 100, 180, 240)
                    set_pixel(wx + 1, wy + 1, 100, 180, 240)
                    if self.windows[r][c]["has_hazard"]:
                        set_pixel(wx, wy, 255, 140, 20)
                else:
                    set_pixel(wx, wy, 220, 200, 120)
                    set_pixel(wx + 1, wy, 200, 180, 100)
                    set_pixel(wx, wy + 1, 180, 160, 90)
                    set_pixel(wx + 1, wy + 1, 180, 160, 90)

        if self.altitude >= 80:
            for x in range(1, 15):
                set_pixel(x, 1, 200, 40, 30)
            set_pixel(7, 0, 255, 255, 255)
            set_pixel(8, 0, 255, 220, 0)
            set_pixel(9, 0, 255, 255, 255)
            set_pixel(8, 1, 255, 200, 50)
        else:
            cx = int(round(self.condor_x))
            set_pixel(cx, 1, 180, 120, 40)
            set_pixel(cx - 1, 0, 220, 160, 60)
            set_pixel(cx + 1, 0, 220, 160, 60)

        for h in self.hazards:
            if not h["active"]:
                continue
            hx = int(round(h["x"]))
            hy = int(round(h["y"]))
            if h["is_condor_egg"]:
                set_pixel(hx, hy, 255, 255, 240)
            else:
                set_pixel(hx, hy, 200, 80, 20)

        px = WINDOW_X[self.climber_col]
        py = int(round(self.climber_y))

        if self.state == STATE_FALL_OFF:
            set_pixel(px, py, 255, 40, 30)
            set_pixel(px, py + 1, 255, 180, 0)
        elif self.state == STATE_SLIPPED_ONE_HAND:
            set_pixel(px, py, 255, 200, 40)
            set_pixel(px, py + 1, 40, 80, 240)
            if self.left_hand_grip:
                set_pixel(px - 1, py - 1, 255, 255, 255)
            if self.right_hand_grip:
                set_pixel(px + 1, py - 1, 255, 255, 255)
        else:
            set_pixel(px, py, 255, 220, 40)
            set_pixel(px, py + 1, 40, 80, 240)
            set_pixel(px - 1, py - 1, 255, 255, 255)
            set_pixel(px + 1, py - 1, 255, 255, 255)

        alt_bar = self.altitude // 10
        for a in range(min(alt_bar, 8)):
            set_pixel(0, 15 - a * 2, 0, 220, 255)

        for l in range(min(self.lives, 3)):
            set_pixel(15, l * 2, 255, 200, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "altitude": self.altitude,
            "climber_col": self.climber_col,
            "climber_y": self.climber_y,
            "left_hand_grip": self.left_hand_grip,
            "right_hand_grip": self.right_hand_grip,
        }
