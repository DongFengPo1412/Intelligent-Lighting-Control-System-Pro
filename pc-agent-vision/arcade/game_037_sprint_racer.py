"""
Game #037: 经典赛道漂移 (Sprint 2 1976 / Atari)
Closed Circuit Top-Down Racing with Continuous Steering Angle, Oil Slick Spinouts & Checkpoint Laps.
"""

import math
from typing import List, Dict, Any
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

STATE_START = 0
STATE_RACING = 1
STATE_VICTORY = 2
STATE_TIMEOUT = 3

NUM_CHECKPOINTS = 4
MAX_LAPS = 3
MAX_OIL_SLICKS = 3
PI = 3.1415926535


class Game037SprintRacer(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.race_time = 0.0
        self.time_limit = 60.0

        self.player = {
            "x": 8.0,
            "y": 13.0,
            "angle": 0.0,
            "speed": 0.0,
            "next_checkpoint": 1,
            "laps": 0,
            "spin_timer": 0.0,
        }

        self.ai = {
            "x": 7.0,
            "y": 12.0,
            "angle": 0.0,
            "speed": 0.0,
            "next_checkpoint": 1,
            "laps": 0,
            "spin_timer": 0.0,
        }

        self.oil_slicks: List[Dict[str, Any]] = []
        self.track_map: List[List[int]] = [[0 for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 37

    @property
    def name(self) -> str:
        return "经典赛道漂移"

    @property
    def english_name(self) -> str:
        return "Sprint 2 1976"

    @property
    def release_year(self) -> int:
        return 1976

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "封闭环形赛道动力学竞速 + 连续角动量转向 + 弯道地面油污打滑失控 + 检查点计圈"

    def init(self) -> None:
        self.reset()

    def init_track(self):
        self.track_map = [[0 for _ in range(16)] for _ in range(16)]
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    self.track_map[y][x] = 1 # Outer wall
                elif 5 <= x <= 10 and 5 <= y <= 10:
                    self.track_map[y][x] = 1 # Infield barrier
                else:
                    self.track_map[y][x] = 0 # Driveable asphalt

        self.oil_slicks = [
            {"x": 12.5, "y": 12.5, "active": True},
            {"x": 12.5, "y": 2.5, "active": True},
            {"x": 2.5, "y": 2.5, "active": True},
        ]

    def reset(self):
        self.state = STATE_RACING
        self.state_timer = 0.0
        self.score = 0
        self.race_time = 0.0
        self.time_limit = 60.0

        self.init_track()

        self.player = {
            "x": 8.0,
            "y": 13.0,
            "angle": 0.0,
            "speed": 0.0,
            "next_checkpoint": 1,
            "laps": 0,
            "spin_timer": 0.0,
        }

        self.ai = {
            "x": 7.0,
            "y": 12.0,
            "angle": 0.0,
            "speed": 0.0,
            "next_checkpoint": 1,
            "laps": 0,
            "spin_timer": 0.0,
        }

    def is_on_track(self, x: float, y: float) -> bool:
        ix = int(round(x))
        iy = int(round(y))
        if not (0 <= ix < 16 and 0 <= iy < 16):
            return False
        return self.track_map[iy][ix] == 0

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_VICTORY, STATE_TIMEOUT):
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.race_time += dt
        if self.race_time >= self.time_limit:
            self.state = STATE_TIMEOUT
            self.state_timer = 0.0
            return

        self.update_player(dt, buttons)
        self.update_ai(dt)

    def update_player(self, dt: float, buttons: int):
        p = self.player

        if p["spin_timer"] > 0.0:
            p["spin_timer"] -= dt
            p["angle"] += 14.0 * dt
            p["speed"] *= 0.95
        else:
            steer_speed = 3.8
            if buttons & KEY_LEFT:
                p["angle"] -= steer_speed * dt
            if buttons & KEY_RIGHT:
                p["angle"] += steer_speed * dt

            while p["angle"] < 0.0:
                p["angle"] += 2.0 * PI
            while p["angle"] >= 2.0 * PI:
                p["angle"] -= 2.0 * PI

            if buttons & KEY_A:
                p["speed"] = min(7.5, p["speed"] + 12.0 * dt)
            elif buttons & KEY_B:
                p["speed"] = max(0.0, p["speed"] - 16.0 * dt)
            else:
                p["speed"] = max(0.0, p["speed"] - 3.5 * dt)

        next_x = p["x"] + math.cos(p["angle"]) * p["speed"] * dt
        next_y = p["y"] + math.sin(p["angle"]) * p["speed"] * dt

        if self.is_on_track(next_x, next_y):
            p["x"] = next_x
            p["y"] = next_y
        else:
            p["speed"] = -p["speed"] * 0.35

        self.check_checkpoints(p, is_player=True)
        self.check_oil_collisions(p)

    def update_ai(self, dt: float):
        ai = self.ai

        if ai["spin_timer"] > 0.0:
            ai["spin_timer"] -= dt
            ai["angle"] += 12.0 * dt
            ai["speed"] *= 0.95
        else:
            target_x, target_y = 8.0, 12.5
            if ai["next_checkpoint"] == 1:
                target_x, target_y = 12.5, 8.0
            elif ai["next_checkpoint"] == 2:
                target_x, target_y = 8.0, 2.5
            elif ai["next_checkpoint"] == 3:
                target_x, target_y = 2.5, 8.0

            target_angle = math.atan2(target_y - ai["y"], target_x - ai["x"])
            diff = target_angle - ai["angle"]
            while diff < -PI:
                diff += 2.0 * PI
            while diff > PI:
                diff -= 2.0 * PI

            ai["angle"] += diff * 4.0 * dt
            ai["speed"] = 5.2

        next_x = ai["x"] + math.cos(ai["angle"]) * ai["speed"] * dt
        next_y = ai["y"] + math.sin(ai["angle"]) * ai["speed"] * dt

        if self.is_on_track(next_x, next_y):
            ai["x"] = next_x
            ai["y"] = next_y
        else:
            ai["speed"] = 1.0

        self.check_checkpoints(ai, is_player=False)
        self.check_oil_collisions(ai)

    def check_checkpoints(self, car: Dict[str, Any], is_player: bool):
        if car["next_checkpoint"] == 1:
            if car["x"] >= 11.0 and 6.0 <= car["y"] <= 10.0:
                car["next_checkpoint"] = 2
        elif car["next_checkpoint"] == 2:
            if car["y"] <= 4.0 and 6.0 <= car["x"] <= 10.0:
                car["next_checkpoint"] = 3
        elif car["next_checkpoint"] == 3:
            if car["x"] <= 4.0 and 6.0 <= car["y"] <= 10.0:
                car["next_checkpoint"] = 0
        elif car["next_checkpoint"] == 0:
            if car["y"] >= 11.0 and 7.0 <= car["x"] <= 10.0:
                car["laps"] += 1
                car["next_checkpoint"] = 1

                if is_player:
                    self.score += 500
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if car["laps"] >= MAX_LAPS:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        time_bonus = int(max(0.0, self.time_limit - self.race_time)) * 20
                        self.score += 1000 + time_bonus
                        if self.score > self.high_score:
                            self.high_score = self.score

    def check_oil_collisions(self, car: Dict[str, Any]):
        for oil in self.oil_slicks:
            if oil["active"]:
                dx = car["x"] - oil["x"]
                dy = car["y"] - oil["y"]
                if dx * dx + dy * dy <= 1.0:
                    if car["spin_timer"] <= 0.0:
                        car["spin_timer"] = 0.75

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if self.track_map[y][x] == 1:
                    if x == 0 or x == 15 or y == 0 or y == 15:
                        fb[idx:idx + 3] = bytes([120, 120, 120])
                    else:
                        fb[idx:idx + 3] = bytes([39, 174, 96])
                else:
                    fb[idx:idx + 3] = bytes([35, 40, 45])

        # Finish line
        for y in range(11, 15):
            idx = (y * 16 + 8) * 3
            if y % 2 == 0:
                fb[idx:idx + 3] = bytes([255, 255, 255])
            else:
                fb[idx:idx + 3] = bytes([20, 20, 20])

        # Oil Slicks
        for oil in self.oil_slicks:
            ox = int(round(oil["x"]))
            oy = int(round(oil["y"]))
            if 0 <= ox < 16 and 0 <= oy < 16:
                idx = (oy * 16 + ox) * 3
                fb[idx:idx + 3] = bytes([10, 10, 20])

        # AI
        ax = int(round(self.ai["x"]))
        ay = int(round(self.ai["y"]))
        if 0 <= ax < 16 and 0 <= ay < 16:
            idx = (ay * 16 + ax) * 3
            fb[idx:idx + 3] = bytes([236, 240, 241])

        # Player
        px = int(round(self.player["x"]))
        py = int(round(self.player["y"]))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx:idx + 3] = bytes([241, 196, 15])

        # HUD Lap dots
        for l in range(min(self.player["laps"], MAX_LAPS)):
            idx = (0 * 16 + (l + 1)) * 3
            fb[idx:idx + 3] = bytes([46, 204, 113])

        if self.state == STATE_VICTORY:
            if int(self.state_timer * 6.0) % 2 == 0:
                for x in range(16):
                    fb[(0 * 16 + x) * 3:(0 * 16 + x) * 3 + 3] = bytes([241, 196, 15])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "player_laps": self.player["laps"],
            "ai_laps": self.ai["laps"],
            "player_speed": self.player["speed"],
            "race_time": self.race_time,
        }
