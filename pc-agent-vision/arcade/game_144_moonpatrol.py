# -*- coding: utf-8 -*-
"""
Game #144: 月球巡逻车 (Moon Patrol 1982 / Irem & Williams)
街机历史上第一部开创视差多层背景卷轴与双向同步火力月面越野的里程碑神作：
三轮月面车高速奔驰与液压避震跳跃跨越环形陨石坑、
按键A同步齐射前向碎石激光与垂直防空导弹、按键B大跳避障、猎杀空投飞碟冲刺分段检查站。
"""

from typing import List, Dict, Any, Optional
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

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_BUGGY_CRASH = 2
STATE_GAME_OVER = 3

GROUND_Y = 13.0


class Game144MoonPatrol(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.distance = 0.0
        self.target_distance = 120.0
        self.checkpoint_letter = 'A'

        # Buggy physics
        self.bx = 3.5
        self.by = GROUND_Y
        self.bvy = 0.0
        self.is_jumping = False
        self.speed = 6.0  # Forward scroll speed

        # Projectiles: Forward lasers & Upward missiles
        self.forward_lasers: List[Dict[str, Any]] = []
        self.upward_missiles: List[Dict[str, Any]] = []

        # Ground hazards: Craters (gaps in ground), Boulders, Mines
        self.ground_hazards: List[Dict[str, Any]] = []

        # Aerial UFOs
        self.ufos: List[Dict[str, Any]] = []

        # Falling UFO bombs
        self.ufo_bombs: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 144

    @property
    def name(self) -> str:
        return "月球巡逻车"

    @property
    def english_name(self) -> str:
        return "Moon Patrol"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "视差卷轴月面奔驰、前向与垂直防空双激光同射、液压大跳越坑与检查站拉力推进"

    def get_name(self) -> str:
        return "Moon Patrol (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.distance = 0.0
        self.checkpoint_letter = 'A'
        self.speed = 6.0

        self.bx = 3.5
        self.by = GROUND_Y
        self.bvy = 0.0
        self.is_jumping = False

        self.forward_lasers = []
        self.upward_missiles = []
        self.ufo_bombs = []

        # Ground hazards (craters, boulders)
        self.ground_hazards = [
            {"x": 18.0, "type": "crater", "width": 2.0, "alive": True},
            {"x": 30.0, "type": "boulder", "hp": 1, "alive": True},
            {"x": 45.0, "type": "crater", "width": 2.5, "alive": True},
            {"x": 60.0, "type": "boulder", "hp": 1, "alive": True},
            {"x": 75.0, "type": "mine", "alive": True},
            {"x": 95.0, "type": "crater", "width": 2.0, "alive": True},
        ]

        # Flying UFOs
        self.ufos = [
            {"x": 12.0, "y": 2.5, "vx": -1.5, "shoot_timer": 1.2, "alive": True, "respawn_timer": 0.0},
            {"x": 15.0, "y": 4.0, "vx": -2.0, "shoot_timer": 2.5, "alive": True, "respawn_timer": 0.0},
        ]

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_BUGGY_CRASH):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_BUGGY_CRASH:
                    if self.lives > 0:
                        self.by = GROUND_Y
                        self.bvy = 0.0
                        self.is_jumping = False
                        self.state = STATE_PLAYING
                        self.state_timer = 0.0
                    else:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.state_timer += dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()

    def _update_playing(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # 1. Buggy Speed Control
        target_speed = 6.0
        if buttons & KEY_RIGHT:
            target_speed = 9.0  # Accelerate
            self.bx = min(5.5, self.bx + 2.0 * dt)
        elif buttons & KEY_LEFT:
            target_speed = 3.5  # Decelerate
            self.bx = max(2.0, self.bx - 2.0 * dt)

        self.speed += (target_speed - self.speed) * 4.0 * dt
        self.distance += self.speed * dt
        self.score += int(self.speed * dt * 2.0)

        # Checkpoint advancement
        cp_idx = min(25, int(self.distance / (self.target_distance / 5.0)))
        self.checkpoint_letter = chr(ord('A') + cp_idx)

        # Course Clear check
        if self.distance >= self.target_distance:
            self.score += 1000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            return

        # 2. Hydraulic Suspension Jump (Key B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if not self.is_jumping:
                self.is_jumping = True
                self.bvy = -11.0

        # Jump Gravity physics
        if self.is_jumping:
            self.bvy += 22.0 * dt
            self.by += self.bvy * dt
            if self.by >= GROUND_Y:
                self.by = GROUND_Y
                self.bvy = 0.0
                self.is_jumping = False

        # 3. Dual Simultaneous Fire (Key A): Horizontal + Vertical!
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.forward_lasers) < 2:
                self.forward_lasers.append({"x": self.bx + 1.2, "y": self.by - 0.2, "active": True})
            if len(self.upward_missiles) < 2:
                self.upward_missiles.append({"x": self.bx, "y": self.by - 1.2, "active": True})

        # 4. Update Forward Lasers
        for fl in self.forward_lasers:
            if fl["active"]:
                fl["x"] += 18.0 * dt
                if fl["x"] > 16.0:
                    fl["active"] = False
                    continue

                for h in self.ground_hazards:
                    if h["alive"] and h["type"] in ("boulder", "mine"):
                        hx = h["x"] - self.distance
                        if abs(fl["x"] - hx) < 1.4 and abs(fl["y"] - GROUND_Y) < 1.4:
                            h["alive"] = False
                            fl["active"] = False
                            self.score += 100
                            break

        self.forward_lasers = [fl for fl in self.forward_lasers if fl["active"]]

        # 5. Update Upward Missiles
        for um in self.upward_missiles:
            if um["active"]:
                um["y"] -= 16.0 * dt
                if um["y"] < 0.0:
                    um["active"] = False
                    continue

                # Intercept UFO bombs
                for b in self.ufo_bombs:
                    if b["active"]:
                        if abs(um["x"] - b["x"]) < 1.0 and abs(um["y"] - b["y"]) < 1.0:
                            b["active"] = False
                            um["active"] = False
                            self.score += 50
                            break

                # Destroy UFOs
                if um["active"]:
                    for u in self.ufos:
                        if u["alive"]:
                            if abs(um["x"] - u["x"]) < 1.2 and abs(um["y"] - u["y"]) < 1.0:
                                u["alive"] = False
                                u["respawn_timer"] = 3.0
                                um["active"] = False
                                self.score += 200
                                break

        self.upward_missiles = [um for um in self.upward_missiles if um["active"]]

        # 6. Update UFOs & Bombs
        for u in self.ufos:
            if u["alive"]:
                u["x"] += u["vx"] * dt
                if u["x"] < -1.0:
                    u["x"] = 16.5
                elif u["x"] > 16.5:
                    u["x"] = -1.0

                u["shoot_timer"] -= dt
                if u["shoot_timer"] <= 0.0:
                    u["shoot_timer"] = 2.2
                    if len(self.ufo_bombs) < 3:
                        self.ufo_bombs.append({"x": u["x"], "y": u["y"] + 0.5, "vy": 5.5, "active": True})

        for b in self.ufo_bombs:
            if b["active"]:
                b["y"] += b["vy"] * dt
                if abs(self.bx - b["x"]) < 1.0 and abs(self.by - b["y"]) < 1.0:
                    b["active"] = False
                    self._crash()
                    return

                if b["y"] >= GROUND_Y:
                    b["active"] = False
                    continue

        self.ufo_bombs = [b for b in self.ufo_bombs if b["active"]]

        # Respawn UFOs
        for u in self.ufos:
            if not u["alive"]:
                u["respawn_timer"] -= dt
                if u["respawn_timer"] <= 0.0:
                    u["x"] = 16.5
                    u["alive"] = True

        # 7. Ground Hazards Collision
        for h in self.ground_hazards:
            if h["alive"]:
                hx = h["x"] - self.distance
                # Crater check: if buggy on ground (by == GROUND_Y) and inside crater span
                if h["type"] == "crater":
                    if not self.is_jumping:
                        if abs(self.bx - hx) < (h["width"] / 2.0 + 0.2):
                            self._crash()
                            return
                elif h["type"] in ("boulder", "mine"):
                    if abs(self.bx - hx) < 0.9 and abs(self.by - GROUND_Y) < 0.6:
                        self._crash()
                        return

    def _crash(self) -> None:
        self.lives -= 1
        self.state = STATE_BUGGY_CRASH
        self.state_timer = 0.0

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

        # 1. Parallax Mountains in deep background (Row 7..9)
        for x in range(16):
            bg_h = int(8.0 + math.sin((x + self.distance * 0.15) * 0.5) * 1.5)
            for y in range(bg_h, 10):
                set_pixel(x, y, 40, 30, 60)

        # 2. Lunar Surface (Row 13..15: Slate Grey)
        for x in range(16):
            set_pixel(x, 13, 160, 160, 170)
            set_pixel(x, 14, 110, 110, 120)
            set_pixel(x, 15, 70, 70, 80)

        # 3. Ground Hazards (Craters carve holes in ground, Boulders sit on top)
        for h in self.ground_hazards:
            if h["alive"]:
                hx = int(round(h["x"] - self.distance))
                if -2 <= hx < 18:
                    if h["type"] == "crater":
                        w = int(round(h["width"]))
                        for cx in range(hx - w // 2, hx + w // 2 + 1):
                            set_pixel(cx, 13, 0, 0, 0)
                            set_pixel(cx, 14, 20, 20, 25)
                    elif h["type"] == "boulder":
                        set_pixel(hx, 12, 190, 130, 80)
                        set_pixel(hx, 13, 140, 90, 50)
                    elif h["type"] == "mine":
                        set_pixel(hx, 13, 255, 40, 30)

        # 4. Aerial UFOs
        for u in self.ufos:
            if u["alive"]:
                ux = int(round(u["x"]))
                uy = int(round(u["y"]))
                set_pixel(ux, uy, 60, 220, 255)
                set_pixel(ux - 1, uy, 40, 160, 200)
                set_pixel(ux + 1, uy, 40, 160, 200)
                set_pixel(ux, uy - 1, 255, 255, 255)  # Dome

        # 5. UFO Bombs
        for b in self.ufo_bombs:
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 100, 40)

        # 6. Lasers & Missiles
        for fl in self.forward_lasers:
            set_pixel(int(round(fl["x"])), int(round(fl["y"])), 255, 255, 80)
        for um in self.upward_missiles:
            set_pixel(int(round(um["x"])), int(round(um["y"])), 255, 60, 60)

        # 7. Lunar Buggy
        bx = int(round(self.bx))
        by = int(round(self.by))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            # Wheels
            set_pixel(bx - 1, by, 30, 30, 40)
            set_pixel(bx, by, 30, 30, 40)
            set_pixel(bx + 1, by, 30, 30, 40)
            # Chassis & Cannons
            set_pixel(bx - 1, by - 1, 50, 140, 240)
            set_pixel(bx, by - 1, 60, 180, 255)
            set_pixel(bx + 1, by - 1, 240, 240, 240)  # Cockpit canopy
            set_pixel(bx + 2, by - 1, 255, 200, 40)   # Forward cannon
            set_pixel(bx, by - 2, 255, 80, 80)        # Upward turret
        elif self.state == STATE_BUGGY_CRASH:
            set_pixel(bx, by, 255, 120, 20)
            set_pixel(bx - 1, by - 1, 255, 40, 20)
            set_pixel(bx + 1, by - 1, 255, 40, 20)

        # 8. Checkpoint Indicator (Col 0, Row 0)
        set_pixel(0, 0, 255, 255, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "distance": self.distance,
            "checkpoint": self.checkpoint_letter,
            "bx": self.bx,
            "by": self.by,
            "is_jumping": self.is_jumping,
            "speed": self.speed,
        }
