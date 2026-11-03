"""
Game #176: 高山滑雪 (Alpine Ski - 1982 Taito)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Taito in 1982, Alpine Ski was one of the earliest and most influential winter
sports arcade games. Players race a downhill skier through three specialized mountain stages:
the Downhill Course, the Slalom Course, and the Ski Jump Competition.

Unique Core Mechanic (Strict Zero-Redundancy):
- High-Speed Downhill Ski Racing & Tuck Acceleration: Button A tucks the skier into aerodynamic
  tuck position to double downhill velocity for higher score rates.
- Slalom Gate Traversal: Weave through red and blue slalom gate pairs to rack up gate bonus streaks.
- Ski Jump Leap (Button B & Jump Ramps): Leap into the air to fly over rocks, pine trees, and snow drifts.
- Time Attack & Checkpoint Extensions: Race against a strict countdown clock; passing distance markers
  awards bonus seconds to reach the bottom lodge.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_WIPEOUT = 2
STATE_GAME_OVER = 3

class Game176AlpineSki(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Skier
        self.px = 7.5
        self.py = 12.0
        self.steer_speed = 7.0
        self.base_speed = 8.0
        self.speed = 8.0
        self.in_air = False
        self.jump_timer = 0.0

        # Race Timer & Distance
        self.time_left = 60.0
        self.distance = 0.0
        self.target_distance = 300.0

        # Track Obstacles & Gates [{y, type: "gate"|"rock"|"tree"|"ramp", x, x2, cleared}]
        self.elements: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 176

    @property
    def name(self) -> str:
        return "高山滑雪"

    @property
    def english_name(self) -> str:
        return "Alpine Ski"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "高山雪道极速俯冲、红蓝旗门回转穿梭加分、飞跃跳台腾空跨越树丛巨石与限时冲线"

    def get_name(self) -> str:
        return "Alpine Ski (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 12.0
        self.in_air = False
        self.jump_timer = 0.0
        self.time_left = 60.0 + self.stage * 5.0
        self.distance = 0.0
        self.target_distance = 250.0 + self.stage * 50.0

        self.elements.clear()
        # Seed initial track elements scrolling downwards
        # Slalom gates, pine trees, rocks, jump ramps
        self._spawn_track()

    def _spawn_track(self):
        # Place rhythmic gates and obstacles ahead from y = -5 to y = -250
        y = -4.0
        while y > -self.target_distance:
            # Alternate between slalom gate, obstacle pair, and jump ramp
            idx = int(abs(y) / 6.0) % 4
            if idx == 0:
                # Slalom Gate: Red flag at gate_x - 1.5, Blue flag at gate_x + 1.5
                gx = 5.0 + (int(abs(y) * 3) % 6)
                self.elements.append({"y": y, "type": "gate", "x": gx - 1.5, "x2": gx + 1.5, "cleared": False})
            elif idx == 1:
                # Tree obstacle
                tx = 3.0 + (int(abs(y) * 5) % 10)
                self.elements.append({"y": y, "type": "tree", "x": tx, "cleared": False})
            elif idx == 2:
                # Jump Ramp
                rx = 6.0 + (int(abs(y) * 2) % 4)
                self.elements.append({"y": y, "type": "ramp", "x": rx, "cleared": False})
            else:
                # Rock obstacle
                ox = 4.0 + (int(abs(y) * 7) % 8)
                self.elements.append({"y": y, "type": "rock", "x": ox, "cleared": False})

            y -= 7.0

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_WIPEOUT:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.in_air = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Countdown Timer
        self.time_left -= dt
        if self.time_left <= 0.0:
            self.lives -= 1
            self.state = STATE_WIPEOUT
            self.state_timer = 1.0
            return

        # Player Steering
        if keys_down & KEY_LEFT:  self.px -= self.steer_speed * dt
        if keys_down & KEY_RIGHT: self.px += self.steer_speed * dt
        self.px = max(2.0, min(13.0, self.px))

        # Tuck / Accelerate (Button A)
        if keys_down & KEY_A:
            self.speed = self.base_speed * 1.6
            self.score += int(10 * dt * 10)
        else:
            self.speed = self.base_speed
            self.score += int(5 * dt * 10)

        # Ski Jump Leap (Button B)
        if (keys_pressed & KEY_B) and not self.in_air:
            self.in_air = True
            self.jump_timer = 0.6 # In air for 0.6 seconds

        # Update Jump state
        if self.in_air:
            self.jump_timer -= dt
            if self.jump_timer <= 0.0:
                self.in_air = False

        # Advance Track & Check Collisions
        scroll_dist = self.speed * dt
        self.distance += scroll_dist

        for elem in self.elements:
            elem["y"] += scroll_dist

            # Interaction when passing near skier row (y ~ 12.0)
            if not elem["cleared"] and abs(elem["y"] - self.py) < 0.8:
                el_type = elem["type"]

                if el_type == "gate":
                    # Passing between gate flags (elem["x"] <= px <= elem["x2"])
                    if elem["x"] <= self.px <= elem["x2"]:
                        elem["cleared"] = True
                        self.score += 200
                        self.time_left += 2.0 # Slalom bonus time!
                    elif abs(self.px - elem["x"]) < 0.6 or abs(self.px - elem["x2"]) < 0.6:
                        # Clipped flagpole
                        elem["cleared"] = True
                        if not self.in_air:
                            self._wipeout()
                            return

                elif el_type == "ramp":
                    # Hitting jump ramp launches skier automatically!
                    if abs(self.px - elem["x"]) < 1.0:
                        elem["cleared"] = True
                        self.in_air = True
                        self.jump_timer = 0.8
                        self.score += 300

                elif el_type in ("rock", "tree"):
                    # Obstacle collision (only damages if not in air!)
                    if abs(self.px - elem["x"]) < 0.8:
                        elem["cleared"] = True
                        if not self.in_air:
                            self._wipeout()
                            return

        # Check finish line reached
        if self.distance >= self.target_distance:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 2000 + int(self.time_left * 50)

    def _wipeout(self):
        self.lives -= 1
        self.state = STATE_WIPEOUT
        self.state_timer = 1.0

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(16 * 16 * 3):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Snow Slope Surface (White with ice blue shimmer)
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 1 or x == 14 or x == 15:
                    set_pixel(x, y, 10, 80, 20) # Side pine forests
                else:
                    set_pixel(x, y, 220, 235, 255) # Clean powder snow

        # 2. Track Elements (Gates, Trees, Rocks, Ramps)
        for elem in self.elements:
            ey = int(round(elem["y"]))
            if 0 <= ey < 16:
                el_type = elem["type"]
                if el_type == "gate":
                    # Red flag left, Blue flag right
                    x1 = int(round(elem["x"]))
                    x2 = int(round(elem["x2"]))
                    set_pixel(x1, ey, 255, 30, 30) # Red flag
                    set_pixel(x2, ey, 30, 80, 255) # Blue flag
                elif el_type == "tree":
                    tx = int(round(elem["x"]))
                    set_pixel(tx, ey, 20, 140, 30) # Green pine
                    set_pixel(tx, ey + 1, 100, 60, 20)
                elif el_type == "rock":
                    rx = int(round(elem["x"]))
                    set_pixel(rx, ey, 120, 120, 130) # Gray boulder
                elif el_type == "ramp":
                    rx = int(round(elem["x"]))
                    set_pixel(rx, ey, 255, 200, 0) # Gold jump ramp
                    set_pixel(rx + 1, ey, 255, 160, 0)

        # 3. Player Skier
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.in_air:
                # Skier in air (elevated, shadow below)
                set_pixel(px, py, 255, 80, 0) # Orange speed suit
                set_pixel(px, py - 1, 255, 255, 0) # Helmet
                set_pixel(px - 1, py + 1, 200, 200, 200) # Left ski
                set_pixel(px + 1, py + 1, 200, 200, 200) # Right ski
                set_pixel(px, py + 2, 160, 180, 200) # Shadow on snow
            else:
                set_pixel(px, py, 220, 40, 30) # Red ski parka
                set_pixel(px, py - 1, 255, 220, 40) # Yellow helmet
                set_pixel(px - 1, py, 200, 200, 200) # Left ski
                set_pixel(px + 1, py, 200, 200, 200) # Right ski
        elif self.state == STATE_WIPEOUT:
            set_pixel(px, py, 255, 80, 0)
            set_pixel(px - 1, py, 255, 0, 0)
            set_pixel(px + 1, py, 255, 0, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "stage": self.stage,
            "px": self.px,
            "time_left": self.time_left,
            "distance": self.distance,
            "in_air": self.in_air,
        }

