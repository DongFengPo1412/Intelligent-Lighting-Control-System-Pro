# -*- coding: utf-8 -*-
"""
Game #147: 疯狂气球 (Crazy Balloon 1980 / Taito)
街机历史上首款谐振摆动物理穿梭与尖刺迷宫避险经典：
悬臂小车支撑浮空摆动气球无休止左右摆荡、按键A开启阻尼减摆进行缝隙微操、
按键B喷气突进逆转摆向、抗衡风道横向推挤偏航穿行通关。
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
STATE_BALLOON_POPPED = 2
STATE_GAME_OVER = 3


class Game147CrazyBalloon(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        # Cart / Trolley position
        self.cx = 2.0
        self.cy = 13.0

        # Balloon pendulum state
        self.swing_angle = 0.0
        self.swing_speed = 3.5
        self.swing_amp = 0.75  # radians (~43 degrees)
        self.arm_length = 2.0

        # Balloon actual position
        self.bx = 2.0
        self.by = 11.0

        # Pop particles
        self.particles: List[Dict[str, Any]] = []

        # Moving hazards (roaming spike faces)
        self.hazards: List[Dict[str, Any]] = []

        # Goal position
        self.gx = 13.5
        self.gy = 2.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 147

    @property
    def name(self) -> str:
        return "疯狂气球"

    @property
    def english_name(self) -> str:
        return "Crazy Balloon"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "摆锤式谐振摆动气球穿行尖刺迷宫、按键调节摆幅阻尼与前进微操、风力风洞偏航吹袭与气球防爆破"

    def get_name(self) -> str:
        return "Crazy Balloon (1980)"

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
        self.cx = 2.0
        self.cy = 13.0
        self.swing_angle = 0.0
        self.swing_amp = 0.75
        self.particles = []

        # Spawn hazards depending on level
        self.hazards = [
            {"x": 7.0, "y": 7.0, "vx": 2.2, "vy": 0.0, "min_x": 4.0, "max_x": 11.0},
            {"x": 10.0, "y": 10.0, "vx": 0.0, "vy": 1.8, "min_y": 7.0, "max_y": 12.0},
        ]

    def _is_spike_wall(self, x: int, y: int) -> bool:
        """Define the spiked maze borders and interior walls"""
        if x <= 0 or x >= 15 or y <= 0 or y >= 15:
            return True

        # Maze interior spike barriers
        # Barrier 1: Vertical spike wall at x=4, y in [4..12] leaving gap at bottom
        if x == 4 and 3 <= y <= 11:
            return True
        # Barrier 2: Vertical spike wall at x=8, y in [1..9] leaving gap at top
        if x == 8 and 3 <= y <= 11:
            return True
        # Barrier 3: Vertical spike wall at x=12, y in [5..14]
        if x == 12 and 5 <= y <= 13:
            return True

        return False

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_BALLOON_POPPED):
            self.state_timer += dt
            # Update burst particles
            for p in self.particles:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["life"] -= dt
            self.particles = [p for p in self.particles if p["life"] > 0]

            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_BALLOON_POPPED:
                    if self.lives > 0:
                        self.cx = 2.0
                        self.cy = 13.0
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
        # 1. Trolley Navigation
        # Button A: Stabilizer / Dampener (reduces swing amplitude, slows speed for micro-maneuver)
        is_stabilized = bool(buttons & KEY_A)
        base_speed = 2.2 if is_stabilized else 4.2
        target_amp = 0.25 if is_stabilized else 0.75

        # Button B: Quick Burst Thruster / Swing flip impulse
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.swing_angle = -self.swing_angle  # Reverse oscillation phase instantly!

        # Smoothly adapt amplitude
        self.swing_amp += (target_amp - self.swing_amp) * min(1.0, dt * 6.0)

        dx = 0.0
        dy = 0.0
        if buttons & KEY_LEFT:
            dx -= base_speed
        if buttons & KEY_RIGHT:
            dx += base_speed
        if buttons & KEY_UP:
            dy -= base_speed
        if buttons & KEY_DOWN:
            dy += base_speed

        # Wind corridor: between y=5 and y=8, wind blows eastward (+x)
        if 5.0 <= self.cy <= 8.0:
            dx += 1.5

        # Move trolley with collision check
        new_cx = self.cx + dx * dt
        new_cy = self.cy + dy * dt

        if not self._is_spike_wall(int(round(new_cx)), int(round(self.cy))):
            self.cx = max(1.0, min(14.0, new_cx))
        if not self._is_spike_wall(int(round(self.cx)), int(round(new_cy))):
            self.cy = max(1.0, min(14.0, new_cy))

        # 2. Pendulum Harmonic Oscillation
        self.swing_angle += self.swing_speed * dt
        actual_theta = self.swing_amp * math.sin(self.swing_angle)

        # Balloon position floating above the cart
        self.bx = self.cx + self.arm_length * math.sin(actual_theta)
        self.by = self.cy - self.arm_length * math.cos(actual_theta)

        # 3. Check Spike Wall Collisions for both Balloon & Cart
        # Balloon check
        b_tile_x = int(round(self.bx))
        b_tile_y = int(round(self.by))
        c_tile_x = int(round(self.cx))
        c_tile_y = int(round(self.cy))

        if self._is_spike_wall(b_tile_x, b_tile_y) or self._is_spike_wall(c_tile_x, c_tile_y):
            self._pop_balloon()
            return

        # 4. Check Moving Hazards
        for h in self.hazards:
            h["x"] += h["vx"] * dt
            h["y"] += h["vy"] * dt
            if "min_x" in h and (h["x"] <= h["min_x"] or h["x"] >= h["max_x"]):
                h["vx"] = -h["vx"]
            if "min_y" in h and (h["y"] <= h["min_y"] or h["y"] >= h["max_y"]):
                h["vy"] = -h["vy"]

            # Hazard vs Balloon collision
            if math.hypot(self.bx - h["x"], self.by - h["y"]) < 1.0:
                self._pop_balloon()
                return

        # 5. Goal Check
        if math.hypot(self.bx - self.gx, self.by - self.gy) < 1.4:
            self.score += 1500
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _pop_balloon(self) -> None:
        self.lives -= 1
        self.state = STATE_BALLOON_POPPED
        self.state_timer = 0.0
        # Spawn bursting particles
        for i in range(8):
            ang = i * (math.pi / 4.0)
            self.particles.append({
                "x": self.bx,
                "y": self.by,
                "vx": math.cos(ang) * 6.0,
                "vy": math.sin(ang) * 6.0,
                "life": 0.8,
            })

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

        # 1. Render Spiked Maze Walls (Sharp Green / Purple thorns)
        for y in range(16):
            for x in range(16):
                if self._is_spike_wall(x, y):
                    set_pixel(x, y, 40, 160, 40)

        # 2. Render Goal (Golden flashing star / pad)
        gx = int(round(self.gx))
        gy = int(round(self.gy))
        set_pixel(gx, gy, 255, 220, 30)

        # 3. Render Wind Corridor indicator (gentle blue tint at edges)
        for wy in range(5, 9):
            set_pixel(1, wy, 20, 60, 120)

        # 4. Render Moving Hazards (Menacing Red spiked faces)
        for h in self.hazards:
            hx = int(round(h["x"]))
            hy = int(round(h["y"]))
            set_pixel(hx, hy, 255, 30, 30)

        # 5. Render Trolley & Stick
        cx = int(round(self.cx))
        cy = int(round(self.cy))
        set_pixel(cx, cy, 140, 140, 160)  # Trolley base

        bx = int(round(self.bx))
        by = int(round(self.by))

        # Connecting arm/stick
        mid_x = int(round((self.cx + self.bx) * 0.5))
        mid_y = int(round((self.cy + self.by) * 0.5))
        set_pixel(mid_x, mid_y, 180, 180, 100)

        # 6. Render Balloon
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            # Cute Red/Cyan balloon with smiling highlight
            set_pixel(bx, by, 255, 40, 60)
            if 0 <= bx + 1 < 16:
                set_pixel(bx + 1, by, 255, 120, 120)  # Highlight
        elif self.state == STATE_BALLOON_POPPED:
            # Bursting particle embers
            for p in self.particles:
                px = int(round(p["x"]))
                py = int(round(p["y"]))
                set_pixel(px, py, 255, 200, 50)

        # 7. Render Lives in top margin
        for l in range(min(self.lives, 3)):
            set_pixel(1 + l, 0, 255, 60, 80)

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
            "cx": self.cx,
            "cy": self.cy,
            "bx": self.bx,
            "by": self.by,
            "swing_angle": self.swing_angle,
            "swing_amp": self.swing_amp,
            "hazards_count": len(self.hazards),
        }
