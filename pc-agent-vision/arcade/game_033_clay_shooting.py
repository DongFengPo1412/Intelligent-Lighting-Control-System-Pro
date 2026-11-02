"""
Game #033: 经典打飞碟 (Clay Shooting 1978 / Nintendo / Sega)
Olympic Double Trap Skeet Shooting with Parabolic Gravity Ballistics, Shotgun Trigger & Double Shatter Bonus.
"""

import math
import random
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
STATE_LAUNCHING = 1
STATE_ROUND_CLEAR = 2
STATE_GAMEOVER = 3

MAX_CLAYS = 2
MAX_ROUNDS = 5


class Game033ClayShooting(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.current_round = 1
        self.total_hits = 0
        self.round_hits = 0
        self.ammo = 2

        self.crosshair_x = 7.5
        self.crosshair_y = 7.5
        self.muzzle_flash = 0.0

        self.clays: List[Dict[str, Any]] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 33

    @property
    def name(self) -> str:
        return "经典打飞碟"

    @property
    def english_name(self) -> str:
        return "Clay Shooting 1978"

    @property
    def release_year(self) -> int:
        return 1978

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双向抛靶抛物线疾速掠空 + 猎枪引前量准星瞬杀 + 双中破靶加成"

    def init(self) -> None:
        self.reset()

    def launch_double_trap(self):
        self.ammo = 2
        self.round_hits = 0

        self.clays = [
            {
                "active": True,
                "shattered": False,
                "shatter_timer": 0.0,
                "x": 1.0,
                "y": 14.0,
                "vx": 4.2 + random.uniform(0.0, 1.5),
                "vy": -(11.5 + random.uniform(0.0, 2.0)),
            },
            {
                "active": True,
                "shattered": False,
                "shatter_timer": 0.0,
                "x": 14.0,
                "y": 14.0,
                "vx": -(4.2 + random.uniform(0.0, 1.5)),
                "vy": -(11.5 + random.uniform(0.0, 2.0)),
            },
        ]

    def reset(self):
        self.state = STATE_LAUNCHING
        self.state_timer = 0.0
        self.score = 0
        self.current_round = 1
        self.total_hits = 0
        self.crosshair_x = 7.5
        self.crosshair_y = 7.5
        self.muzzle_flash = 0.0
        self.launch_double_trap()

    def pull_trigger(self) -> bool:
        if self.ammo <= 0:
            return False

        self.ammo -= 1
        self.muzzle_flash = 0.08

        for clay in self.clays:
            if clay["active"] and not clay["shattered"]:
                dist = abs(self.crosshair_x - clay["x"]) + abs(self.crosshair_y - clay["y"])
                if dist <= 1.45:
                    clay["shattered"] = True
                    clay["shatter_timer"] = 0.35
                    self.round_hits += 1
                    self.total_hits += 1

                    pts = 100 if clay["y"] <= 5.0 else 50
                    self.score += pts

                    if self.round_hits == 2:
                        self.score += 200

                    if self.score > self.high_score:
                        self.high_score = self.score
                    return True
        return False

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_GAMEOVER:
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer >= 1.2:
                if self.current_round < MAX_ROUNDS:
                    self.current_round += 1
                    self.state = STATE_LAUNCHING
                    self.state_timer = 0.0
                    self.launch_double_trap()
                else:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
            return

        if self.muzzle_flash > 0.0:
            self.muzzle_flash -= dt

        speed = 12.0
        if buttons & KEY_LEFT:
            self.crosshair_x = max(0.5, self.crosshair_x - speed * dt)
        if buttons & KEY_RIGHT:
            self.crosshair_x = min(14.5, self.crosshair_x + speed * dt)
        if buttons & KEY_UP:
            self.crosshair_y = max(1.0, self.crosshair_y - speed * dt)
        if buttons & KEY_DOWN:
            self.crosshair_y = min(14.5, self.crosshair_y + speed * dt)

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.pull_trigger()

        self.update_clays(dt)
        self.check_round_progression()

    def update_clays(self, dt: float):
        gravity = 9.8

        for clay in self.clays:
            if not clay["active"]:
                continue

            if clay["shattered"]:
                clay["shatter_timer"] -= dt
                if clay["shatter_timer"] <= 0.0:
                    clay["active"] = False
                continue

            clay["x"] += clay["vx"] * dt
            clay["y"] += clay["vy"] * dt
            clay["vy"] += gravity * dt

            if clay["y"] > 15.0 and clay["vy"] > 0.0:
                clay["active"] = False
            if clay["x"] < -1.0 or clay["x"] > 16.5:
                clay["active"] = False

    def check_round_progression(self):
        any_active = any(c["active"] for c in self.clays)
        if not any_active:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Sky & Grass
        for y in range(13):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx:idx + 3] = bytes([52, 152, 219])
        for y in range(13, 16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx:idx + 3] = bytes([39, 174, 96])

        # Traps
        fb[(14 * 16 + 0) * 3:(14 * 16 + 0) * 3 + 3] = bytes([80, 80, 80])
        fb[(14 * 16 + 15) * 3:(14 * 16 + 15) * 3 + 3] = bytes([80, 80, 80])

        # HUD Ammo
        for a in range(self.ammo):
            idx = (0 * 16 + a) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])

        # HUD Hits
        for h in range(min(self.total_hits, 5)):
            idx = (0 * 16 + (15 - h)) * 3
            fb[idx:idx + 3] = bytes([241, 196, 15])

        # Clays
        for clay in self.clays:
            if not clay["active"]:
                continue
            cx = int(round(clay["x"]))
            cy = int(round(clay["y"]))
            if 0 <= cx < 16 and 0 <= cy < 16:
                idx = (cy * 16 + cx) * 3
                if clay["shattered"]:
                    fb[idx:idx + 3] = bytes([255, 255, 255])
                    if cx > 0:
                        fb[(cy * 16 + (cx - 1)) * 3:(cy * 16 + (cx - 1)) * 3 + 3] = bytes([241, 196, 15])
                    if cx < 15:
                        fb[(cy * 16 + (cx + 1)) * 3:(cy * 16 + (cx + 1)) * 3 + 3] = bytes([230, 126, 34])
                else:
                    fb[idx:idx + 3] = bytes([230, 126, 34])

        # Crosshair
        hx = int(round(self.crosshair_x))
        hy = int(round(self.crosshair_y))
        cr, cg, cb = (255, 255, 255) if self.muzzle_flash > 0.0 else (46, 204, 113)

        if 0 <= hx < 16 and 0 <= hy < 16:
            fb[(hy * 16 + hx) * 3:(hy * 16 + hx) * 3 + 3] = bytes([cr, cg, cb])
            if hx > 0:
                fb[(hy * 16 + (hx - 1)) * 3:(hy * 16 + (hx - 1)) * 3 + 3] = bytes([cr, cg, cb])
            if hx < 15:
                fb[(hy * 16 + (hx + 1)) * 3:(hy * 16 + (hx + 1)) * 3 + 3] = bytes([cr, cg, cb])
            if hy > 0:
                fb[((hy - 1) * 16 + hx) * 3:((hy - 1) * 16 + hx) * 3 + 3] = bytes([cr, cg, cb])
            if hy < 15:
                fb[((hy + 1) * 16 + hx) * 3:((hy + 1) * 16 + hx) * 3 + 3] = bytes([cr, cg, cb])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "round": self.current_round,
            "ammo": self.ammo,
            "total_hits": self.total_hits,
            "crosshair": (self.crosshair_x, self.crosshair_y),
        }
