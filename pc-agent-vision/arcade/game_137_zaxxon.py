# -*- coding: utf-8 -*-
"""
Game #137: 扎克松立体战机 (Zaxxon 1982 / Sega)
街机历史上第一部采用轴测伪3D投影与高度差判定的里程碑太空战机游戏：
投射地面阴影指示真实坐标、按键调节飞行海拔高度穿梭城墙狭缝、
低空轰炸地面燃油罐补给、规避防空导弹并发射激光击破要塞机器人。
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
STATE_SHIP_CRASH = 2
STATE_GAME_OVER = 3

MAX_ALTITUDE = 4.0
MIN_ALTITUDE = 0.0


class Game137Zaxxon(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.fuel = 100.0

        # Ship position: ground coordinates (x, y) and altitude z
        self.px = 7.5
        self.py = 12.0
        self.pz = 2.0  # Current altitude in [0.0, 4.0]

        # Fortress Walls: each wall has y, gate_z (altitude of gap), gate_x
        self.walls: List[Dict[str, Any]] = []

        # Ground targets: fuel tanks, turrets
        self.targets: List[Dict[str, Any]] = []

        # Lasers fired by ship
        self.bullets: List[Dict[str, Any]] = []

        # Boss Zaxxon state
        self.boss_active = False
        self.boss_y = -5.0
        self.boss_hp = 3
        self.boss_missile: Optional[Dict[str, Any]] = None

        self.distance_traveled = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 137

    @property
    def name(self) -> str:
        return "扎克松立体战机"

    @property
    def english_name(self) -> str:
        return "Zaxxon"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "高度差轴测飞行、阴影投影定位、穿梭城墙高度孔隙、低空轰炸油罐补给与机甲BOSS决战"

    def get_name(self) -> str:
        return "Zaxxon (1982)"

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
        self.fuel = 100.0
        self.px = 7.5
        self.py = 12.0
        self.pz = 2.0
        self.distance_traveled = 0.0

        self.bullets = []
        self.boss_active = False
        self.boss_y = -10.0
        self.boss_hp = 3
        self.boss_missile = None

        # Generate fortress walls
        self.walls = [
            {"y": -4.0, "gate_z": 2.0, "cleared": False},
            {"y": -16.0, "gate_z": 3.0, "cleared": False},
            {"y": -28.0, "gate_z": 1.0, "cleared": False},
        ]

        # Generate ground targets (fuel tanks & missile silos)
        self.targets = [
            {"x": 4.0, "y": -2.0, "type": "fuel", "alive": True},
            {"x": 11.0, "y": -8.0, "type": "turret", "alive": True},
            {"x": 5.0, "y": -14.0, "type": "fuel", "alive": True},
            {"x": 10.0, "y": -22.0, "type": "turret", "alive": True},
            {"x": 6.0, "y": -26.0, "type": "fuel", "alive": True},
        ]

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_SHIP_CRASH):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_SHIP_CRASH:
                    if self.lives > 0:
                        self.fuel = 100.0
                        self.px = 7.5
                        self.py = 12.0
                        self.pz = 2.0
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
        # 1. Fuel drain
        self.fuel -= 3.0 * dt
        if self.fuel <= 0.0:
            self.fuel = 0.0
            self._crash_ship()
            return

        # 2. Controls:
        # LEFT / RIGHT: change x ground position
        move_speed_x = 7.5
        if buttons & KEY_LEFT:
            self.px = max(1.5, self.px - move_speed_x * dt)
        if buttons & KEY_RIGHT:
            self.px = min(13.5, self.px + move_speed_x * dt)

        # UP / DOWN: change flight altitude (pz)
        altitude_speed = 3.5
        if buttons & KEY_UP:  # Pull up / climb
            self.pz = min(MAX_ALTITUDE, self.pz + altitude_speed * dt)
        if buttons & KEY_DOWN:  # Dive / descend
            self.pz = max(MIN_ALTITUDE, self.pz - altitude_speed * dt)

        # Forward scrolling speed (Key B gives airbrake or thrust)
        scroll_speed = 4.0
        if buttons & KEY_B:
            scroll_speed = 2.0  # Air-brake for precision maneuvering
        self.distance_traveled += scroll_speed * dt

        # 3. Fire Blaster: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.bullets) < 2:
                self.bullets.append({
                    "x": self.px,
                    "y": self.py - 1.0,
                    "z": self.pz,
                    "active": True,
                })

        # 4. Update bullets
        for b in self.bullets:
            if b["active"]:
                b["y"] -= 14.0 * dt
                if b["y"] < -2.0:
                    b["active"] = False
                    continue

                # Check hit on ground targets
                # Target is at ground level z = 0, bullet must be at low altitude z <= 1.2
                if b["z"] <= 1.2:
                    for t in self.targets:
                        if t["alive"] and abs(b["x"] - t["x"]) < 1.1 and abs(b["y"] - t["y"]) < 1.1:
                            t["alive"] = False
                            b["active"] = False
                            if t["type"] == "fuel":
                                self.fuel = min(100.0, self.fuel + 30.0)
                                self.score += 150
                            else:
                                self.score += 200
                            break

                # Check hit on Boss Zaxxon
                if self.boss_active and self.boss_hp > 0:
                    if abs(b["x"] - 7.5) < 1.8 and abs(b["y"] - self.boss_y) < 1.5:
                        # Must match boss altitude (around z=2.0)
                        if abs(b["z"] - 2.0) < 1.2:
                            b["active"] = False
                            self.boss_hp -= 1
                            self.score += 300
                            if self.boss_hp <= 0:
                                self.score += 1000
                                self.state = STATE_STAGE_CLEAR
                                self.state_timer = 0.0
                                return

        self.bullets = [b for b in self.bullets if b["active"]]

        # 5. Scroll walls towards player
        for wall in self.walls:
            wall["y"] += scroll_speed * dt
            # Check collision when wall reaches player y coordinate
            if not wall["cleared"] and abs(wall["y"] - self.py) < 0.6:
                # Check if player altitude matches gate_z
                if abs(self.pz - wall["gate_z"]) > 0.6:
                    # Crashed into fortress wall!
                    self._crash_ship()
                    return
                else:
                    # Cleanly navigated through the wall gap!
                    wall["cleared"] = True
                    self.score += 100

        # 6. Scroll ground targets
        for t in self.targets:
            t["y"] += scroll_speed * dt

        # 7. Boss Zaxxon approach
        if self.distance_traveled >= 35.0 and not self.boss_active:
            self.boss_active = True
            self.boss_y = 1.0

        if self.boss_active:
            self.boss_y = min(3.5, self.boss_y + 1.0 * dt)
            # Boss fires homing missile
            if self.boss_missile is None and self.boss_hp > 0:
                self.boss_missile = {"x": 7.5, "y": self.boss_y + 1.0, "active": True}
            elif self.boss_missile and self.boss_missile["active"]:
                self.boss_missile["y"] += 6.0 * dt
                if self.boss_missile["x"] < self.px:
                    self.boss_missile["x"] += 1.5 * dt
                else:
                    self.boss_missile["x"] -= 1.5 * dt

                if abs(self.boss_missile["x"] - self.px) < 0.9 and abs(self.boss_missile["y"] - self.py) < 0.9:
                    self.boss_missile["active"] = False
                    self._crash_ship()
                    return
                if self.boss_missile["y"] > 16.0:
                    self.boss_missile = None

    def _crash_ship(self) -> None:
        self.lives -= 1
        self.state = STATE_SHIP_CRASH
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

        # 1. Render Fortress Grid lines (deep navy/slate ground)
        for y in range(0, 16, 4):
            offset_y = int((self.distance_traveled + y) % 16)
            for x in range(16):
                set_pixel(x, offset_y, 10, 20, 40)

        # 2. Render Ground Targets (Fuel tanks & turrets)
        for t in self.targets:
            if t["alive"] and 0 <= t["y"] < 16:
                tx = int(round(t["x"]))
                ty = int(round(t["y"]))
                if t["type"] == "fuel":
                    # Yellow-orange fuel canister
                    set_pixel(tx, ty, 255, 180, 20)
                    set_pixel(tx, ty - 1, 255, 60, 20)
                else:
                    # Red gun turret
                    set_pixel(tx, ty, 220, 40, 40)
                    set_pixel(tx + 1, ty, 180, 20, 20)

        # 3. Render Fortress Walls with altitude gap
        for wall in self.walls:
            wy = int(round(wall["y"]))
            if 0 <= wy < 16:
                for x in range(16):
                    # Brick wall color
                    set_pixel(x, wy, 160, 80, 180)
                # Gate slot indicator
                gz = int(round(wall["gate_z"]))
                set_pixel(7, wy, 60, 240, 255)
                set_pixel(8, wy, 60, 240, 255)

        # 4. Render Boss Zaxxon
        if self.boss_active and 0 <= self.boss_y < 16:
            by = int(round(self.boss_y))
            for ox in range(-2, 3):
                set_pixel(7 + ox, by, 220, 40, 60)
            set_pixel(7, by - 1, 255, 255, 255)
            set_pixel(8, by - 1, 255, 255, 255)

            if self.boss_missile and self.boss_missile["active"]:
                mx = int(round(self.boss_missile["x"]))
                my = int(round(self.boss_missile["y"]))
                set_pixel(mx, my, 255, 120, 40)

        # 5. Render Bullets
        for b in self.bullets:
            by_screen = int(round(b["y"] - b["z"] * 0.7))
            set_pixel(int(round(b["x"])), by_screen, 255, 255, 200)

        # 6. Render Player Ship and Altitude Shadow!
        px = int(round(self.px))
        py_ground = int(round(self.py))
        py_ship = int(round(self.py - self.pz * 0.7))

        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            # Ground shadow (Dark grey-blue)
            set_pixel(px, py_ground, 30, 45, 65)
            set_pixel(px - 1, py_ground, 20, 30, 50)
            set_pixel(px + 1, py_ground, 20, 30, 50)

            # Ship in air (Bright cyan & white)
            set_pixel(px, py_ship, 255, 255, 255)
            set_pixel(px - 1, py_ship, 60, 200, 255)
            set_pixel(px + 1, py_ship, 60, 200, 255)
            set_pixel(px, py_ship + 1, 255, 140, 40)  # Thruster flame
        elif self.state == STATE_SHIP_CRASH:
            set_pixel(px, py_ground, 255, 100, 30)
            set_pixel(px - 1, py_ground, 255, 40, 20)
            set_pixel(px + 1, py_ground, 255, 40, 20)

        # 7. Altitude gauge on Col 0 (left edge)
        alt_bar = int(round((self.pz / MAX_ALTITUDE) * 6.0))
        for h in range(alt_bar + 1):
            set_pixel(0, 15 - h, 60, 220, 255)

        # 8. Fuel gauge on bottom row (Col 2..15)
        fuel_pixels = int(round((self.fuel / 100.0) * 13.0))
        for x in range(fuel_pixels + 1):
            set_pixel(2 + x, 15, 240, 180, 40)

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
            "fuel": self.fuel,
            "px": self.px,
            "py": self.py,
            "pz": self.pz,
            "distance_traveled": self.distance_traveled,
            "boss_active": self.boss_active,
            "boss_hp": self.boss_hp,
        }
