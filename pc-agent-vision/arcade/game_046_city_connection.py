"""
Game #046: 城市快车 (City Connection 1985 / Jaleco)
Multi-tiered Highway Pavement Painting, Oil Canister Attacks, Cop Spinning & Overpass Leap Physics.
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

NUM_POLICE = 3
MAX_OIL_CANS = 3
NUM_TIERS = 4
TIER_Y = [3, 7, 11, 15]


class Game046CityConnection(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.oil_ammo = 6
        self.unpainted_tiles = NUM_TIERS * 16

        self.player_x = 1.0
        self.player_tier = 3
        self.player_vx = 0.0
        self.player_dir = 1
        self.is_jumping = False
        self.jump_vy = 0.0
        self.jump_y_offset = 0.0

        self.police: List[Dict[str, Any]] = []
        self.oil_shots: List[Dict[str, Any]] = []
        self.painted = [[False for _ in range(16)] for _ in range(NUM_TIERS)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 46

    @property
    def name(self) -> str:
        return "城市快车"

    @property
    def english_name(self) -> str:
        return "City Connection (1985)"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多层立交公路油漆喷涂 + 投掷机油罐击晕警车 + 跃层跳跃与撞飞旋转警车"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.oil_ammo = 6
        self.unpainted_tiles = NUM_TIERS * 16
        self.player_x = 1.0
        self.player_tier = 3
        self.player_vx = 0.0
        self.player_dir = 1
        self.is_jumping = False
        self.jump_vy = 0.0
        self.jump_y_offset = 0.0

        self.oil_shots = []
        self.init_highways()

        self.police = [
            {"x": 14.0, "tier": 0, "vx": -3.5, "active": True, "is_dizzy": False, "dizzy_timer": 0.0},
            {"x": 12.0, "tier": 1, "vx": -4.0, "active": True, "is_dizzy": False, "dizzy_timer": 0.0},
            {"x": 15.0, "tier": 2, "vx": -3.8, "active": True, "is_dizzy": False, "dizzy_timer": 0.0},
        ]

    def init_highways(self):
        self.unpainted_tiles = 0
        self.painted = [[False for _ in range(16)] for _ in range(NUM_TIERS)]
        for t in range(NUM_TIERS):
            for c in range(16):
                self.unpainted_tiles += 1

    def fire_oil_can(self):
        if self.oil_ammo <= 0:
            return
        active_shots = sum(1 for o in self.oil_shots if o["active"])
        if active_shots < MAX_OIL_CANS:
            self.oil_shots.append({
                "x": self.player_x + self.player_dir * 0.8,
                "tier": self.player_tier,
                "vx": self.player_dir * 12.0,
                "active": True,
            })
            self.oil_ammo -= 1

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        max_speed = 7.0

        if buttons & KEY_LEFT:
            self.player_dir = -1
            self.player_vx = -max_speed
        elif buttons & KEY_RIGHT:
            self.player_dir = 1
            self.player_vx = max_speed
        else:
            if self.player_vx > 0.0:
                self.player_vx = max(0.0, self.player_vx - 10.0 * dt)
            if self.player_vx < 0.0:
                self.player_vx = min(0.0, self.player_vx + 10.0 * dt)

        self.player_x += self.player_vx * dt
        if self.player_x < 0.0:
            self.player_x += 16.0
        if self.player_x >= 16.0:
            self.player_x -= 16.0

        # Paint road
        if not self.is_jumping:
            col = int(round(self.player_x))
            if 0 <= col < 16:
                if not self.painted[self.player_tier][col]:
                    self.painted[self.player_tier][col] = True
                    self.unpainted_tiles -= 1
                    self.score += 10
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if self.unpainted_tiles <= 0:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

        # Jump (KEY_A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A) and not self.is_jumping:
            self.is_jumping = True
            self.jump_vy = 9.5
            self.jump_y_offset = 0.0

        # Vertical jumping physics
        if self.is_jumping:
            gravity = 22.0
            self.jump_vy -= gravity * dt
            self.jump_y_offset += self.jump_vy * dt

            # Leap to upper tier
            if (buttons & KEY_UP) and self.player_tier > 0 and self.jump_y_offset >= 3.8 and self.jump_vy > 0.0:
                self.player_tier -= 1
                self.jump_y_offset = 0.0
                self.jump_vy = 0.0
                self.is_jumping = False
            elif self.jump_y_offset <= 0.0:
                self.jump_y_offset = 0.0
                self.jump_vy = 0.0
                self.is_jumping = False
        else:
            # Drop down to lower tier
            if (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN) and self.player_tier < 3:
                self.player_tier += 1

        # Fire oil can (KEY_B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.fire_oil_can()

    def update_police(self, dt: float):
        for p in self.police:
            if not p["active"]:
                continue
            if p["is_dizzy"]:
                p["dizzy_timer"] -= dt
                if p["dizzy_timer"] <= 0.0:
                    p["is_dizzy"] = False
                continue

            p["x"] += p["vx"] * dt
            if p["x"] < 0.0:
                p["x"] += 16.0
            if p["x"] >= 16.0:
                p["x"] -= 16.0

    def update_oil_cans(self, dt: float):
        for o in self.oil_shots:
            if not o["active"]:
                continue
            o["x"] += o["vx"] * dt
            if o["x"] < 0.0 or o["x"] > 16.0:
                o["active"] = False

    def check_collisions(self):
        # 1. Oil cans vs Police
        for o in self.oil_shots:
            if not o["active"]:
                continue
            for p in self.police:
                if not p["active"] or p["tier"] != o["tier"]:
                    continue
                if abs(o["x"] - p["x"]) <= 0.85:
                    o["active"] = False
                    p["is_dizzy"] = True
                    p["dizzy_timer"] = 4.5
                    self.score += 50
                    if self.score > self.high_score:
                        self.high_score = self.score
                    break

        # 2. Player vs Police
        for p in self.police:
            if not p["active"] or p["tier"] != self.player_tier:
                continue

            if self.is_jumping and self.jump_y_offset >= 1.2:
                continue

            if abs(self.player_x - p["x"]) <= 0.82:
                if p["is_dizzy"]:
                    p["active"] = False
                    self.score += 100
                    if self.score > self.high_score:
                        self.high_score = self.score
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 1.0
                    self.player_tier = 3
                    self.player_vx = 0.0
                    self.is_jumping = False
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_police(dt)
        self.update_oil_cans(dt)
        self.check_collisions()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # 1. City Night Skyline
        for i in range(256):
            fb[i * 3 + 0] = 5
            fb[i * 3 + 1] = 5
            fb[i * 3 + 2] = 5

        # 2. Highway Tiers
        for t in range(NUM_TIERS):
            y = TIER_Y[t]
            for x in range(16):
                idx = (y * 16 + x) * 3
                if self.painted[t][x]:
                    fb[idx + 0] = 46
                    fb[idx + 1] = 204
                    fb[idx + 2] = 113
                else:
                    fb[idx + 0] = 52
                    fb[idx + 1] = 73
                    fb[idx + 2] = 94

        # 3. Oil Can Shots
        for o in self.oil_shots:
            if not o["active"]:
                continue
            ox = int(round(o["x"]))
            oy = TIER_Y[o["tier"]] - 1
            if 0 <= ox < 16 and 0 <= oy < 16:
                idx = (oy * 16 + ox) * 3
                fb[idx + 0] = 241
                fb[idx + 1] = 196
                fb[idx + 2] = 15

        # 4. Police Cruisers
        for p in self.police:
            if not p["active"]:
                continue
            px = int(round(p["x"]))
            py = TIER_Y[p["tier"]] - 1
            if 0 <= px < 16 and 0 <= py < 16:
                idx = (py * 16 + px) * 3
                if p["is_dizzy"]:
                    fb[idx + 0] = 0
                    fb[idx + 1] = 255
                    fb[idx + 2] = 255
                else:
                    fb[idx + 0] = 52
                    fb[idx + 1] = 152
                    fb[idx + 2] = 219

        # 5. Player Honda City
        cx = int(round(self.player_x))
        cy = TIER_Y[self.player_tier] - 1 - int(round(self.jump_y_offset))
        if 0 <= cx < 16 and 0 <= cy < 16:
            idx = (cy * 16 + cx) * 3
            fb[idx + 0] = 231
            fb[idx + 1] = 76
            fb[idx + 2] = 60

        # 6. HUD Oil Ammo
        for a in range(min(self.oil_ammo, 6)):
            idx = (0 * 16 + a) * 3
            fb[idx + 0] = 241
            fb[idx + 1] = 196
            fb[idx + 2] = 15

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "oil_ammo": self.oil_ammo,
            "unpainted_tiles": self.unpainted_tiles,
            "player_x": self.player_x,
            "player_tier": self.player_tier,
            "is_jumping": self.is_jumping,
        }
