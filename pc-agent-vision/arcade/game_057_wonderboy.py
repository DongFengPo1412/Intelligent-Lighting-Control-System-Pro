"""
Game #057: 原始人冒险 / 冒险岛街机版 (Wonder Boy 1986 / Escape / Sega)
Prehistoric Island Adventure with Skateboard Momentum, Parabolic Stone Axes & Vitality Fruit Consumption.
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

MAX_AXES = 3
MAX_MONSTERS = 4
MAX_FRUITS = 3


class Game057WonderBoy(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 3000
        self.lives = 3

        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_jumping = False

        self.vitality = 14
        self.vitality_timer = 0.0
        self.has_skateboard = False
        self.has_fairy = False
        self.fairy_timer = 0.0
        self.stage_progress = 0.0

        self.axes: List[Dict[str, Any]] = []
        self.monsters: List[Dict[str, Any]] = []
        self.fruits: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 57

    @property
    def name(self) -> str:
        return "原始人冒险"

    @property
    def english_name(self) -> str:
        return "Wonder Boy"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "滑板极速冲刺惯性漂移 + 投掷石斧破怪 + 体力衰减水果补充与精灵护体"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_stage()

    def init_stage(self):
        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_jumping = False
        self.vitality = 14
        self.vitality_timer = 0.0
        self.has_skateboard = False
        self.has_fairy = False
        self.fairy_timer = 0.0
        self.stage_progress = 0.0

        self.axes = []
        self.monsters = [
            {"x": 12.0, "y": 13.0, "vx": -2.0, "type": 0, "health": 1, "active": True},
            {"x": 18.0, "y": 13.0, "vx": -2.5, "type": 1, "health": 1, "active": True},
            {"x": 26.0, "y": 13.0, "vx": -3.0, "type": 2, "health": 1, "active": True},
            {"x": 34.0, "y": 13.0, "vx": -2.0, "type": 0, "health": 1, "active": True},
        ]
        self.fruits = [
            {"x": 8.0, "y": 12.0, "type": 0, "active": True},
            {"x": 15.0, "y": 12.0, "type": 2, "active": True},  # Skateboard egg
            {"x": 22.0, "y": 12.0, "type": 1, "active": True},
        ]

    def throw_axe(self):
        if len(self.axes) < MAX_AXES:
            self.axes.append({
                "x": self.player_x + (1.0 if self.player_facing > 0 else -1.0),
                "y": self.player_y - 0.5,
                "vx": self.player_facing * 10.0,
                "vy": -7.0,
                "active": True
            })

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.init_stage()
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        # Vitality timer
        self.vitality_timer += dt
        if self.vitality_timer >= 1.2:
            self.vitality_timer = 0.0
            self.vitality -= 1
            if self.vitality <= 0:
                self.vitality = 0
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        # Fairy timer
        if self.has_fairy:
            self.fairy_timer -= dt
            if self.fairy_timer <= 0.0:
                self.has_fairy = False

        # Player Movement
        speed = 9.0 if self.has_skateboard else 6.0
        if self.has_skateboard:
            self.player_vx = speed
            self.player_facing = 1
            if buttons & KEY_LEFT:  self.player_vx = speed * 0.4
            if buttons & KEY_RIGHT: self.player_vx = speed * 1.3
        else:
            self.player_vx = 0.0
            if buttons & KEY_LEFT:  self.player_vx = -speed; self.player_facing = -1
            if buttons & KEY_RIGHT: self.player_vx = speed;  self.player_facing = 1

        self.player_x += self.player_vx * dt

        # Jump
        if self.is_jumping:
            self.player_y += self.player_vy * dt
            self.player_vy += 35.0 * dt
            if self.player_y >= 13.0:
                self.player_y = 13.0
                self.player_vy = 0.0
                self.is_jumping = False
        else:
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.is_jumping = True
                self.player_vy = -13.0 if self.has_skateboard else -11.0

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.throw_axe()

        if self.player_x > 8.0:
            overflow = self.player_x - 8.0
            self.player_x = 8.0
            self.stage_progress += overflow * 1.5
        if self.player_x < 1.0:
            self.player_x = 1.0

        self.score += int(self.player_vx * dt * 2.0)

        # Update axes
        for a in self.axes:
            if not a["active"]:
                continue
            a["x"] += a["vx"] * dt
            a["y"] += a["vy"] * dt
            a["vy"] += 22.0 * dt
            if a["x"] < 0.0 or a["x"] > 16.0 or a["y"] > 15.0:
                a["active"] = False

        self.axes = [a for a in self.axes if a["active"]]

        # Update monsters
        scroll_eff = (9.0 if self.has_skateboard else 5.0) * dt
        for i, m in enumerate(self.monsters):
            if not m["active"]:
                continue
            m["x"] += (m["vx"] * dt) - scroll_eff * 0.4
            if m["x"] < -2.0:
                m["x"] = 18.0 + (i * 6.0)
                m["health"] = 1

        for i, f in enumerate(self.fruits):
            if not f["active"]:
                continue
            f["x"] -= scroll_eff * 0.6
            if f["x"] < -2.0:
                f["x"] = 16.0 + (i * 10.0)

        # Collisions: Axes on monsters
        for a in self.axes:
            if not a["active"]:
                continue
            for m in self.monsters:
                if not m["active"]:
                    continue
                if abs(a["x"] - m["x"]) < 1.2 and abs(a["y"] - m["y"]) < 1.2:
                    a["active"] = False
                    m["health"] -= 1
                    if m["health"] <= 0:
                        m["active"] = False
                        self.score += 100
                    break

        # Collisions: Fruits on player
        for f in self.fruits:
            if not f["active"]:
                continue
            if abs(self.player_x - f["x"]) < 1.1 and abs(self.player_y - f["y"]) < 1.2:
                f["active"] = False
                if f["type"] == 2:
                    self.has_skateboard = True
                    self.score += 300
                else:
                    self.vitality = min(16, self.vitality + 3)
                    self.score += 100

        # Collisions: Monsters on player
        for m in self.monsters:
            if not m["active"]:
                continue
            if abs(self.player_x - m["x"]) < 0.9 and abs(self.player_y - m["y"]) < 0.9:
                if self.has_fairy:
                    m["active"] = False
                    self.score += 200
                elif self.has_skateboard:
                    self.has_skateboard = False
                    m["active"] = False
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # Stage victory
        if self.stage_progress >= 50.0:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1500 + self.vitality * 50
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Sky y=0..13
        for y in range(14):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 40
                fb[idx + 1] = min(255, 160 + y * 5)
                fb[idx + 2] = 240

        # Ground y=14..15
        for x in range(16):
            idx_g = (14 * 16 + x) * 3
            fb[idx_g] = 50
            fb[idx_g + 1] = 200
            fb[idx_g + 2] = 40

            idx_d = (15 * 16 + x) * 3
            fb[idx_d] = 140
            fb[idx_d + 1] = 80
            fb[idx_d + 2] = 30

        # Fruits
        for f in self.fruits:
            if f["active"]:
                fx = int(round(f["x"]))
                fy = int(round(f["y"]))
                if 0 <= fx < 16 and 0 <= fy < 16:
                    idx = (fy * 16 + fx) * 3
                    if f["type"] == 0:
                        fb[idx] = 255; fb[idx + 1] = 230; fb[idx + 2] = 0
                    elif f["type"] == 1:
                        fb[idx] = 255; fb[idx + 1] = 30;  fb[idx + 2] = 30
                    else:
                        fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255

        # Monsters
        for m in self.monsters:
            if m["active"]:
                mx = int(round(m["x"]))
                my = int(round(m["y"]))
                if 0 <= mx < 16 and 0 <= my < 16:
                    idx = (my * 16 + mx) * 3
                    if m["type"] == 0:
                        fb[idx] = 160; fb[idx + 1] = 60;  fb[idx + 2] = 180
                    elif m["type"] == 1:
                        fb[idx] = 255; fb[idx + 1] = 80;  fb[idx + 2] = 0
                    else:
                        fb[idx] = 120; fb[idx + 1] = 120; fb[idx + 2] = 120

        # Axes
        for a in self.axes:
            if a["active"]:
                ax = int(round(a["x"]))
                ay = int(round(a["y"]))
                if 0 <= ax < 16 and 0 <= ay < 16:
                    idx = (ay * 16 + ax) * 3
                    fb[idx] = 240
                    fb[idx + 1] = 240
                    fb[idx + 2] = 240

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx] = 255
            fb[idx + 1] = 180
            fb[idx + 2] = 120

            if self.has_skateboard and py < 15:
                s_idx = ((py + 1) * 16 + px) * 3
                fb[s_idx] = 255
                fb[s_idx + 1] = 50
                fb[s_idx + 2] = 50

            if self.has_fairy and py > 0:
                f_idx = ((py - 1) * 16 + px) * 3
                fb[f_idx] = 0
                fb[f_idx + 1] = 255
                fb[f_idx + 2] = 255

        # HUD vitality
        for v in range(min(self.vitality, 16)):
            idx = v * 3
            if self.vitality <= 4:
                fb[idx] = 255; fb[idx + 1] = 0;   fb[idx + 2] = 0
            else:
                fb[idx] = 0;   fb[idx + 1] = 255; fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "vitality": self.vitality,
            "has_skateboard": self.has_skateboard,
            "has_fairy": self.has_fairy,
            "stage_progress": self.stage_progress,
        }
