"""
Game #079: 影子潜艇 / 潜望镜大战 (SubRoc-3D 1982 / Sega)
First 3D Stereoscopic Periscope Shooter, Dual-Weapon Torpedo / Air Missile Strikes & Depth Navigation.
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

STATE_PLAYING = 0
STATE_PLAYER_HIT = 1
STATE_GAME_OVER = 2
STATE_VICTORY = 3

ZONE_AIR = 0
ZONE_SURFACE = 1
ZONE_DEPTH = 2

MAX_TARGETS = 5
MAX_PROJECTILES = 4


class Game079SubRoc3D(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 12000
        self.lives = 3
        self.targets_destroyed = 0

        # Crosshair
        self.cx = 7.5
        self.cy = 7.5

        self.spawn_timer = 0.0
        self.targets: List[Dict[str, Any]] = []
        self.projectiles: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 79

    @property
    def name(self) -> str:
        return "影子潜艇"

    @property
    def english_name(self) -> str:
        return "SubRoc-3D"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "潜望镜伪3D立体纵深射击 + 空中战机飞弹拦截与水下鱼雷深海击沉"

    def get_name(self) -> str:
        return "SubRoc-3D (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.targets_destroyed = 0
        self.cx = 7.5
        self.cy = 7.5
        self.spawn_timer = 0.0
        self.targets = []
        self.projectiles = []

        self.spawn_target()
        self.spawn_target()

    def get_active_targets_count(self) -> int:
        return len([t for t in self.targets if t["active"]])

    def spawn_target(self):
        if len([t for t in self.targets if t["active"]]) >= MAX_TARGETS:
            return

        z_type = random.randint(0, 2)
        if z_type == 0:
            target = {
                "x": random.uniform(4.0, 12.0),
                "y": random.uniform(2.0, 5.0),
                "z": 10.0,
                "vx": random.uniform(-1.0, 1.0),
                "vy": 0.2,
                "vz": -1.8,
                "zone": ZONE_AIR,
                "active": True,
            }
        elif z_type == 1:
            start_x = 1.0 if random.choice([True, False]) else 14.0
            target = {
                "x": start_x,
                "y": 7.0,
                "z": 10.0,
                "vx": 0.8 if start_x < 7.5 else -0.8,
                "vy": 0.0,
                "vz": -1.3,
                "zone": ZONE_SURFACE,
                "active": True,
            }
        else:
            target = {
                "x": random.uniform(3.0, 13.0),
                "y": random.uniform(9.0, 13.0),
                "z": 10.0,
                "vx": random.uniform(-0.8, 0.8),
                "vy": 0.1,
                "vz": -1.5,
                "zone": ZONE_DEPTH,
                "active": True,
            }
        self.targets.append(target)

    def fire_torpedo(self):
        if len([p for p in self.projectiles if p["active"]]) < MAX_PROJECTILES:
            self.projectiles.append({
                "x": self.cx,
                "y": max(7.0, self.cy),
                "z": 1.0,
                "vz": 14.0,
                "is_air_missile": False,
                "active": True,
            })

    def fire_air_missile(self):
        if len([p for p in self.projectiles if p["active"]]) < MAX_PROJECTILES:
            self.projectiles.append({
                "x": self.cx,
                "y": min(7.0, self.cy),
                "z": 1.0,
                "vz": 14.0,
                "is_air_missile": True,
                "active": True,
            })

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_GAME_OVER, STATE_VICTORY):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PLAYER_HIT:
            if self.state_timer > 1.2:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                else:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
            return

        self.spawn_timer += dt
        if self.spawn_timer > 2.0:
            self.spawn_timer = 0.0
            self.spawn_target()

        # Update Crosshair
        spd = 7.5
        if buttons & KEY_LEFT:
            self.cx -= spd * dt
        if buttons & KEY_RIGHT:
            self.cx += spd * dt
        if buttons & KEY_UP:
            self.cy -= spd * dt
        if buttons & KEY_DOWN:
            self.cy += spd * dt

        self.cx = max(1.0, min(14.0, self.cx))
        self.cy = max(1.0, min(14.0, self.cy))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_torpedo()
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.fire_air_missile()

        self.update_targets(dt)
        self.update_projectiles(dt)
        self.check_hits()

    def update_targets(self, dt: float):
        for t in self.targets:
            if not t["active"]:
                continue
            t["x"] += t["vx"] * dt
            t["y"] += t["vy"] * dt
            t["z"] += t["vz"] * dt

            if t["z"] <= 1.2:
                t["active"] = False
                self.lives -= 1
                self.state = STATE_PLAYER_HIT
                self.state_timer = 0.0
                return

            if t["x"] < 1.0:
                t["x"] = 1.0
                t["vx"] = abs(t["vx"])
            elif t["x"] > 14.0:
                t["x"] = 14.0
                t["vx"] = -abs(t["vx"])

        self.targets = [t for t in self.targets if t["active"]]

    def update_projectiles(self, dt: float):
        for p in self.projectiles:
            if not p["active"]:
                continue
            p["z"] += p["vz"] * dt
            if p["z"] >= 10.0:
                p["active"] = False

        self.projectiles = [p for p in self.projectiles if p["active"]]

    def check_hits(self):
        for p in self.projectiles:
            if not p["active"]:
                continue

            for t in self.targets:
                if not t["active"]:
                    continue

                if p["is_air_missile"] and t["zone"] != ZONE_AIR:
                    continue
                if not p["is_air_missile"] and t["zone"] == ZONE_AIR:
                    continue

                dz = abs(p["z"] - t["z"])
                dx = abs(p["x"] - t["x"])
                dy = abs(p["y"] - t["y"])

                if dz < 1.5 and dx < 1.6 and dy < 1.6:
                    t["active"] = False
                    p["active"] = False
                    self.targets_destroyed += 1

                    pts = 300 if t["zone"] == ZONE_AIR else (500 if t["zone"] == ZONE_SURFACE else 400)
                    self.score += pts
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if self.targets_destroyed >= 15:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 5000
                    break

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Sky
        for y in range(7):
            for x in range(16):
                set_pixel(x, y, 10, 20, 50)

        # 2. Horizon
        for x in range(16):
            set_pixel(x, 7, 30, 80, 140)

        # 3. Ocean
        for y in range(8, 16):
            for x in range(16):
                set_pixel(x, y, 5, 25, 45)

        # Hit flash
        if self.state == STATE_PLAYER_HIT:
            for i in range(0, 16 * 16 * 3, 3):
                fb[i] = min(255, fb[i] + 120)

        # 4. Targets
        for t in self.targets:
            if not t["active"]:
                continue
            tx = int(round(t["x"]))
            ty = int(round(t["y"]))
            z = t["z"]

            if t["zone"] == ZONE_AIR:
                set_pixel(tx, ty, 255, 60, 40)
                if z < 5.0:
                    set_pixel(tx - 1, ty, 255, 180, 0)
                    set_pixel(tx + 1, ty, 255, 180, 0)
            elif t["zone"] == ZONE_SURFACE:
                set_pixel(tx, ty, 200, 200, 210)
                if z < 6.0:
                    set_pixel(tx - 1, ty, 150, 150, 160)
                    set_pixel(tx + 1, ty, 150, 150, 160)
                    set_pixel(tx, ty - 1, 255, 100, 0)
            else:
                set_pixel(tx, ty, 50, 255, 120)
                if z < 5.0:
                    set_pixel(tx, ty - 1, 255, 60, 20)
                    set_pixel(tx, ty + 1, 255, 60, 20)

        # 5. Projectiles
        for p in self.projectiles:
            if not p["active"]:
                continue
            px = int(round(p["x"]))
            py = int(round(p["y"]))
            if p["is_air_missile"]:
                set_pixel(px, py, 255, 255, 100)
                set_pixel(px, py + 1, 255, 100, 0)
            else:
                set_pixel(px, py, 80, 220, 255)
                set_pixel(px, py + 1, 40, 140, 255)

        # 6. Reticle
        cx = int(round(self.cx))
        cy = int(round(self.cy))
        set_pixel(cx - 1, cy, 50, 255, 50)
        set_pixel(cx + 1, cy, 50, 255, 50)
        set_pixel(cx, cy - 1, 50, 255, 50)
        set_pixel(cx, cy + 1, 50, 255, 50)
        set_pixel(cx, cy, 255, 255, 255)

        # 7. Lives HUD
        for l in range(self.lives):
            set_pixel(l * 2, 0, 40, 220, 255)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "targets_destroyed": self.targets_destroyed,
            "cx": self.cx,
            "cy": self.cy,
            "active_targets": self.get_active_targets_count(),
        }
