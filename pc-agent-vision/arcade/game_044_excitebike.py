"""
Game #044: 越野机车 (Excitebike 1984 / Nintendo)
Motocross Dirt Track Racing with Airborne Pitch Angle Balance, Turbo Overheating & Cooling Strips.
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
STATE_PLAYING = 1
STATE_CRASH = 2
STATE_OVERHEAT = 3
STATE_VICTORY = 4

TRACK_LENGTH = 120
NUM_OBSTACLES = 16

OBS_NONE = 0
OBS_SMALL_RAMP = 1
OBS_BIG_RAMP = 2
OBS_MUD_PUDDLE = 3
OBS_COOLING_STRIP = 4
OBS_HURDLE = 5


class Game044Excitebike(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0

        self.world_x = 0.0
        self.speed = 0.0
        self.lane = 1
        self.altitude = 0.0
        self.vertical_vy = 0.0
        self.pitch_angle = 0.0
        self.is_airborne = False

        self.engine_temp = 0.0
        self.crash_recovery_timer = 0.0

        self.obstacles: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 44

    @property
    def name(self) -> str:
        return "越野机车"

    @property
    def english_name(self) -> str:
        return "Excitebike (1984)"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "泥土坡道腾空飞跃 + 空中前后俯仰平衡姿态 + 涡轮增压过热与冷却水带"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.world_x = 0.0
        self.speed = 0.0
        self.lane = 1
        self.altitude = 0.0
        self.vertical_vy = 0.0
        self.pitch_angle = 0.0
        self.is_airborne = False
        self.engine_temp = 0.0
        self.crash_recovery_timer = 0.0

        self.init_track()

    def init_track(self):
        track_data = [
            (12.0, 1, OBS_SMALL_RAMP),
            (18.0, 2, OBS_MUD_PUDDLE),
            (25.0, 1, OBS_COOLING_STRIP),
            (32.0, 0, OBS_BIG_RAMP),
            (38.0, 3, OBS_MUD_PUDDLE),
            (45.0, 2, OBS_SMALL_RAMP),
            (52.0, 1, OBS_COOLING_STRIP),
            (58.0, 2, OBS_BIG_RAMP),
            (66.0, 0, OBS_MUD_PUDDLE),
            (74.0, 3, OBS_SMALL_RAMP),
            (80.0, 1, OBS_COOLING_STRIP),
            (88.0, 2, OBS_BIG_RAMP),
            (95.0, 0, OBS_MUD_PUDDLE),
            (102.0, 1, OBS_SMALL_RAMP),
            (108.0, 2, OBS_COOLING_STRIP),
            (114.0, 3, OBS_BIG_RAMP),
        ]
        self.obstacles = []
        for wx, ln, otype in track_data:
            self.obstacles.append({"world_x": wx, "lane": ln, "type": otype})

    def trigger_crash(self):
        self.state = STATE_CRASH
        self.speed = 0.0
        self.is_airborne = False
        self.altitude = 0.0
        self.vertical_vy = 0.0
        self.pitch_angle = 0.0
        self.crash_recovery_timer = 1.8

    def check_terrain_collisions(self):
        if self.is_airborne:
            return

        for obs in self.obstacles:
            if obs["lane"] != self.lane:
                continue

            dist = abs(self.world_x - obs["world_x"])
            if dist <= 0.65:
                otype = obs["type"]
                if otype == OBS_SMALL_RAMP:
                    self.is_airborne = True
                    self.altitude = 0.1
                    self.vertical_vy = 7.5
                    self.pitch_angle = -0.3
                elif otype == OBS_BIG_RAMP:
                    self.is_airborne = True
                    self.altitude = 0.1
                    self.vertical_vy = 11.5
                    self.pitch_angle = -0.45
                elif otype == OBS_MUD_PUDDLE:
                    self.speed *= 0.4
                elif otype == OBS_COOLING_STRIP:
                    self.engine_temp = 0.0
                    self.score += 20
                    if self.score > self.high_score:
                        self.high_score = self.score

    def update_bike(self, dt: float, buttons: int, prev_buttons: int):
        # 1. Lane switching on ground
        if not self.is_airborne:
            if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
                if self.lane > 0:
                    self.lane -= 1
            if (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
                if self.lane < 3:
                    self.lane += 1

        # 2. Throttle & Engine heat
        if not self.is_airborne:
            if buttons & KEY_B:
                target_speed = 18.0
                self.speed += (target_speed - self.speed) * 4.0 * dt
                self.engine_temp += 25.0 * dt
            elif buttons & KEY_A:
                target_speed = 11.0
                self.speed += (target_speed - self.speed) * 5.0 * dt
                self.engine_temp += 6.0 * dt
            else:
                self.speed = max(0.0, self.speed - 8.0 * dt)
                self.engine_temp = max(0.0, self.engine_temp - 15.0 * dt)
        else:
            self.engine_temp = max(0.0, self.engine_temp - 10.0 * dt)

        # Engine overheat
        if self.engine_temp >= 100.0:
            self.engine_temp = 100.0
            self.state = STATE_OVERHEAT
            self.speed = 0.0
            self.state_timer = 0.0
            return

        # 3. Distance advance
        self.world_x += self.speed * dt
        self.score += int(self.speed * dt * 5.0)
        if self.score > self.high_score:
            self.high_score = self.score

        # 4. Airborne dynamics & Pitch balance
        if self.is_airborne:
            gravity = 22.0
            self.vertical_vy -= gravity * dt
            self.altitude += self.vertical_vy * dt

            if buttons & KEY_LEFT:
                self.pitch_angle -= 2.6 * dt
            if buttons & KEY_RIGHT:
                self.pitch_angle += 2.6 * dt

            self.pitch_angle = max(-1.0, min(1.0, self.pitch_angle))

            if self.altitude <= 0.0:
                self.altitude = 0.0
                self.vertical_vy = 0.0
                self.is_airborne = False

                if abs(self.pitch_angle) > 0.42:
                    self.trigger_crash()
                    return
                else:
                    self.score += 50
                    if self.score > self.high_score:
                        self.high_score = self.score
                    self.pitch_angle = 0.0
        else:
            self.pitch_angle = 0.0

        self.check_terrain_collisions()

        if self.world_x >= TRACK_LENGTH:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 2000
            if self.score > self.high_score:
                self.high_score = self.score

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_CRASH:
            self.crash_recovery_timer -= dt
            if self.crash_recovery_timer <= 0.0:
                self.state = STATE_PLAYING
                self.speed = 3.0
            return

        if self.state == STATE_OVERHEAT:
            self.engine_temp = max(0.0, self.engine_temp - 35.0 * dt)
            if self.engine_temp <= 0.0:
                self.state = STATE_PLAYING
                self.speed = 2.0
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_bike(dt, buttons, prev_buttons)

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # 1. Sky & Bleachers
        for y in range(7):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx + 0] = 20
                fb[idx + 1] = 30
                fb[idx + 2] = 55

        # HUD Row 0: Temp Gauge (x: 0..7)
        temp_bars = int(round((self.engine_temp / 100.0) * 7.0))
        for x in range(8):
            idx = (0 * 16 + x) * 3
            if x < temp_bars:
                if self.engine_temp > 80.0:
                    fb[idx + 0] = 231
                    fb[idx + 1] = 76
                    fb[idx + 2] = 60
                elif self.engine_temp > 50.0:
                    fb[idx + 0] = 241
                    fb[idx + 1] = 196
                    fb[idx + 2] = 15
                else:
                    fb[idx + 0] = 46
                    fb[idx + 1] = 204
                    fb[idx + 2] = 113

        # Track progress marker
        prog_x = 9 + int(round((self.world_x / TRACK_LENGTH) * 6.0))
        prog_x = min(15, max(9, prog_x))
        p_idx = (0 * 16 + prog_x) * 3
        fb[p_idx + 0] = 255
        fb[p_idx + 1] = 255
        fb[p_idx + 2] = 255

        # 2. Dirt Lanes (8..11) & Grass
        for y in range(7, 16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if 8 <= y <= 11:
                    fb[idx + 0] = 120
                    fb[idx + 1] = 66
                    fb[idx + 2] = 18
                else:
                    fb[idx + 0] = 30
                    fb[idx + 1] = 100
                    fb[idx + 2] = 40

        # 3. Obstacles relative to Camera (Player at x=3)
        cam_left = self.world_x - 3.0
        for obs in self.obstacles:
            rel_x = obs["world_x"] - cam_left
            sx = int(round(rel_x))
            sy = 8 + obs["lane"]
            if 0 <= sx < 16 and 8 <= sy <= 11:
                idx = (sy * 16 + sx) * 3
                otype = obs["type"]
                if otype in (OBS_SMALL_RAMP, OBS_BIG_RAMP):
                    fb[idx + 0] = 243
                    fb[idx + 1] = 156
                    fb[idx + 2] = 18
                elif otype == OBS_MUD_PUDDLE:
                    fb[idx + 0] = 52
                    fb[idx + 1] = 73
                    fb[idx + 2] = 94
                elif otype == OBS_COOLING_STRIP:
                    fb[idx + 0] = 41
                    fb[idx + 1] = 128
                    fb[idx + 2] = 185

        # 4. Motocross Bike
        px = 3
        py = 8 + self.lane - int(round(self.altitude))
        py = max(1, min(15, py))
        b_idx = (py * 16 + px) * 3

        if self.state == STATE_CRASH:
            fb[b_idx + 0] = 255
            fb[b_idx + 1] = 80
            fb[b_idx + 2] = 0
        elif self.state == STATE_OVERHEAT:
            fb[b_idx + 0] = 180
            fb[b_idx + 1] = 180
            fb[b_idx + 2] = 180
        else:
            fb[b_idx + 0] = 231
            fb[b_idx + 1] = 76
            fb[b_idx + 2] = 60

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "world_x": self.world_x,
            "speed": self.speed,
            "lane": self.lane,
            "altitude": self.altitude,
            "pitch_angle": self.pitch_angle,
            "is_airborne": self.is_airborne,
            "engine_temp": self.engine_temp,
        }
