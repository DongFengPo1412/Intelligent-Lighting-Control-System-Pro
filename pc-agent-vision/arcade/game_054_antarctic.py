"""
Game #054: 极速企鹅 / 南极探险 (Antarctic Adventure 1983 / Konami)
Pseudo-3D Rear Perspective Ice Skating Odyssey with Crevasse Leaps, Popping Seals & Leaping Fish.
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
STATE_DEAD = 2
STATE_VICTORY = 3

MAX_CREVASSES = 3
MAX_SEALS = 2
MAX_FISH = 2


class Game054Antarctic(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 2500

        self.penguin_lane = 0.0
        self.speed = 12.0
        self.is_jumping = False
        self.jump_timer = 0.0
        self.trip_stun_timer = 0.0

        self.distance_remaining = 100.0
        self.time_remaining = 45.0
        self.fish_collected = 0

        self.crevasses: List[Dict[str, Any]] = []
        self.seals: List[Dict[str, Any]] = []
        self.fishes: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 54

    @property
    def name(self) -> str:
        return "南极探险"

    @property
    def english_name(self) -> str:
        return "Antarctic Adventure"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "伪3D纵深向远极速滑行 + 裂隙冰坑起跳横跨 + 钻出冰洞的海豹避让与鱼类收集"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.init_stage()

    def init_stage(self):
        self.penguin_lane = 0.0
        self.speed = 14.0
        self.is_jumping = False
        self.jump_timer = 0.0
        self.trip_stun_timer = 0.0
        self.distance_remaining = 100.0
        self.time_remaining = 45.0
        self.fish_collected = 0

        self.crevasses = [
            {"z": 30.0, "lane": -0.4, "active": True},
            {"z": 65.0, "lane": 0.3, "active": True},
            {"z": 95.0, "lane": -0.2, "active": True},
        ]
        self.seals = [
            {"z": 45.0, "lane": 0.4, "active": True},
            {"z": 80.0, "lane": -0.5, "active": True},
        ]
        self.fishes = [
            {"z": 20.0, "lane": 0.0, "active": True},
            {"z": 75.0, "lane": 0.2, "active": True},
        ]

    def trigger_jump(self):
        if not self.is_jumping and self.trip_stun_timer <= 0.0:
            self.is_jumping = True
            self.jump_timer = 0.55

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 2.0:
                self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        # Stun decay
        if self.trip_stun_timer > 0.0:
            self.trip_stun_timer -= dt
            self.speed = max(0.0, self.speed - 20.0 * dt)
        else:
            # Acceleration
            if buttons & KEY_UP:
                self.speed = min(24.0, self.speed + 10.0 * dt)
            elif buttons & KEY_DOWN:
                self.speed = max(8.0, self.speed - 15.0 * dt)
            else:
                if self.speed < 14.0:
                    self.speed += 5.0 * dt

            # Steering
            if buttons & KEY_LEFT:
                self.penguin_lane -= 2.2 * dt
            elif buttons & KEY_RIGHT:
                self.penguin_lane += 2.2 * dt
            self.penguin_lane = max(-1.0, min(1.0, self.penguin_lane))

            # Jump
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.trigger_jump()

            if self.is_jumping:
                self.jump_timer -= dt
                if self.jump_timer <= 0.0:
                    self.is_jumping = False

            # Distance
            self.distance_remaining -= (self.speed * 0.15) * dt
            self.score += int(self.speed * dt * 2.0)

        # Hazard approach
        dz = self.speed * dt * 2.5

        for i, c in enumerate(self.crevasses):
            if not c["active"]:
                continue
            c["z"] -= dz
            if c["z"] < -5.0:
                c["z"] = 100.0 + (i * 20.0)
                c["lane"] = -0.4 if (i % 2 == 0) else 0.4

        for i, s in enumerate(self.seals):
            if not s["active"]:
                continue
            s["z"] -= dz
            if s["z"] < -5.0:
                s["z"] = 90.0 + (i * 35.0)
                s["lane"] = 0.5 if (i % 2 == 0) else -0.5

        for i, f in enumerate(self.fishes):
            if not f["active"]:
                continue
            f["z"] -= dz
            if f["z"] < -5.0:
                f["z"] = 80.0 + (i * 40.0)
                f["lane"] = -0.1 if (i == 0) else 0.1

        # Check collisions
        for c in self.crevasses:
            if not c["active"]:
                continue
            if -1.0 <= c["z"] <= 3.0:
                if abs(self.penguin_lane - c["lane"]) < 0.6:
                    if not self.is_jumping:
                        self.trip_stun_timer = 1.2
                        self.speed = 0.0
                        c["z"] = -6.0
                        break

        for s in self.seals:
            if not s["active"]:
                continue
            if -1.0 <= s["z"] <= 3.0:
                if abs(self.penguin_lane - s["lane"]) < 0.5:
                    self.trip_stun_timer = 1.0
                    self.speed = 0.0
                    s["z"] = -6.0
                    break

        for f in self.fishes:
            if not f["active"]:
                continue
            if -1.5 <= f["z"] <= 3.5:
                if abs(self.penguin_lane - f["lane"]) < 0.55:
                    f["active"] = False
                    self.fish_collected += 1
                    self.score += 200
                    self.time_remaining = min(60.0, self.time_remaining + 3.0)
                    self.speed = min(26.0, self.speed + 4.0)

        # Check victory
        if self.distance_remaining <= 0.0:
            self.distance_remaining = 0.0
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000 + int(self.time_remaining * 30.0)
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Sky y=0..3
        for y in range(4):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 10
                fb[idx + 1] = 20
                fb[idx + 2] = 50 + y * 15

        # Ice plain y=4..15
        for y in range(4, 16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = min(255, 180 + y * 5)
                fb[idx + 1] = min(255, 210 + y * 3)
                fb[idx + 2] = 245

                road_w = 2.0 + (y - 4.0) * 1.0
                if abs(x - 7.5) > road_w:
                    fb[idx] = 140
                    fb[idx + 1] = 170
                    fb[idx + 2] = 200

        # Crevasses
        for c in self.crevasses:
            if c["active"] and 0.0 < c["z"] < 100.0:
                t = (100.0 - c["z"]) / 100.0
                cy = 4 + int(t * 10.0)
                road_w = 2.0 + (cy - 4.0) * 1.0
                cx = int(round(7.5 + c["lane"] * road_w))
                if 4 <= cy < 16:
                    for dx in (-1, 0, 1):
                        px = cx + dx
                        if 0 <= px < 16:
                            idx = (cy * 16 + px) * 3
                            fb[idx] = 0
                            fb[idx + 1] = 30
                            fb[idx + 2] = 80

        # Seals
        for s in self.seals:
            if s["active"] and 0.0 < s["z"] < 100.0:
                t = (100.0 - s["z"]) / 100.0
                sy = 4 + int(t * 10.0)
                road_w = 2.0 + (sy - 4.0) * 1.0
                sx = int(round(7.5 + s["lane"] * road_w))
                if 0 <= sx < 16 and 4 <= sy < 16:
                    idx = (sy * 16 + sx) * 3
                    fb[idx] = 120
                    fb[idx + 1] = 130
                    fb[idx + 2] = 140

        # Fish
        for f in self.fishes:
            if f["active"] and 0.0 < f["z"] < 100.0:
                t = (100.0 - f["z"]) / 100.0
                fy = 4 + int(t * 10.0)
                road_w = 2.0 + (fy - 4.0) * 1.0
                fx = int(round(7.5 + f["lane"] * road_w))
                if 0 <= fx < 16 and 4 <= fy < 16:
                    idx = (fy * 16 + fx) * 3
                    fb[idx] = 255
                    fb[idx + 1] = 140
                    fb[idx + 2] = 0

        # Penguin
        py = 11 if self.is_jumping else 13
        road_w = 2.0 + (13.0 - 4.0) * 1.0
        px = int(round(7.5 + self.penguin_lane * road_w))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            if self.trip_stun_timer > 0.0:
                fb[idx] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 0
            else:
                fb[idx] = 20
                fb[idx + 1] = 20
                fb[idx + 2] = 25
                if py > 0:
                    belly_idx = ((py - 1) * 16 + px) * 3
                    fb[belly_idx] = 255
                    fb[belly_idx + 1] = 255
                    fb[belly_idx + 2] = 255

        # HUD
        time_bars = int((self.time_remaining / 45.0) * 8.0)
        for t in range(min(time_bars, 8)):
            idx = t * 3
            fb[idx] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 0

        dist_bars = int((1.0 - self.distance_remaining / 100.0) * 7.0)
        for d in range(min(dist_bars, 7)):
            idx = (15 - d) * 3
            fb[idx] = 255
            fb[idx + 1] = 100
            fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "speed": self.speed,
            "penguin_lane": self.penguin_lane,
            "distance_remaining": self.distance_remaining,
            "time_remaining": self.time_remaining,
            "is_jumping": self.is_jumping,
            "is_stunned": self.trip_stun_timer > 0.0,
        }
