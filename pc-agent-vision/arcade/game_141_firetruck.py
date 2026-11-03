# -*- coding: utf-8 -*-
"""
Game #141: 消防云梯车 (Fire Truck 1978 / Atari)
街机历史上第一部铰接式长轴消防挂车物理转向与急速出警模拟驾驶游戏：
车头牵引转向、后桥舵手铰链尾部摆荡惯性模拟、按键A/B联动后舵纠偏防甩尾擦碰、
穿越窄道油渍急弯赶赴火场救援。
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
STATE_CRASH = 2
STATE_GAME_OVER = 3


class Game141FireTruck(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.time_left = 40.0
        self.distance = 0.0
        self.target_distance = 100.0
        self.speed = 6.0  # Forward speed

        # Articulated vehicle state
        # Cab (Front Tractor): (cx, cy)
        self.cx = 7.5
        self.cy = 9.0
        self.cab_vx = 0.0

        # Trailer (Rear Ladder): (tx, ty)
        self.tx = 7.5
        self.ty = 12.0
        self.hitch_angle = 0.0  # Angle between cab and trailer

        # Road boundaries (16 vertical rows)
        self.road_center = [7.5 for _ in range(16)]
        self.road_width = 7.0  # half-width 3.5

        # Obstacles on road (parked cars, oil slicks)
        self.obstacles: List[Dict[str, Any]] = []

        self.siren_active = False

        self.reset()

    @property
    def game_id(self) -> int:
        return 141

    @property
    def name(self) -> str:
        return "消防云梯车"

    @property
    def english_name(self) -> str:
        return "Fire Truck"

    @property
    def release_year(self) -> int:
        return 1978

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双节铰接车身动力学、前后桥独立转向防甩尾折叠、油渍侧滑避险与限时极速赶赴火场"

    def get_name(self) -> str:
        return "Fire Truck (1978)"

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
        self.time_left = 40.0
        self.distance = 0.0
        self.speed = 6.0

        self.cx = 7.5
        self.cy = 9.0
        self.cab_vx = 0.0

        self.tx = 7.5
        self.ty = 12.0
        self.hitch_angle = 0.0
        self.siren_active = False

        self._init_road()

        self.obstacles = [
            {"x": 6.5, "y": -5.0, "type": "car", "alive": True},
            {"x": 9.0, "y": -15.0, "type": "oil", "alive": True},
            {"x": 7.0, "y": -25.0, "type": "car", "alive": True},
            {"x": 8.5, "y": -35.0, "type": "oil", "alive": True},
        ]

    def _init_road(self) -> None:
        for y in range(16):
            self.road_center[y] = 7.5 + math.sin((y + self.distance) * 0.3) * 2.5

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_CRASH):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_CRASH:
                    if self.lives > 0:
                        self.cx = 7.5
                        self.tx = 7.5
                        self.cab_vx = 0.0
                        self.hitch_angle = 0.0
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
        self.time_left -= dt
        if self.time_left <= 0.0:
            self.time_left = 0.0
            self._crash()
            return

        # 1. Acceleration & Braking
        target_speed = 7.0
        if buttons & KEY_UP:
            target_speed = 10.0  # Gas pedal
        elif buttons & KEY_DOWN:
            target_speed = 3.5   # Brake

        self.speed += (target_speed - self.speed) * 4.0 * dt
        self.distance += self.speed * dt
        self.score += int(self.speed * dt * 2.0)

        # Stage clear check
        if self.distance >= self.target_distance:
            self.score += 1000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            return

        # 2. Steer Front Cab (Left / Right)
        steer_rate = 6.0
        if buttons & KEY_LEFT:
            self.cab_vx = -steer_rate
        elif buttons & KEY_RIGHT:
            self.cab_vx = steer_rate
        else:
            self.cab_vx *= 0.85

        self.cx += self.cab_vx * dt

        # 3. Rear Tiller Steering (Key A: steer trailer left, Key B: steer trailer right)
        tiller_offset = 0.0
        if buttons & KEY_A:
            tiller_offset -= 3.5
        if buttons & KEY_B:
            tiller_offset += 3.5

        # 4. Articulated Trailer Physics
        # Trailer follows Cab with trailing distance L = 2.5
        # Trailer naturally lags behind cab x, creating hitch angle:
        dx = self.cx - self.tx
        # Trailer pulls towards cab x plus tiller steer influence
        trailer_follow_rate = 4.5
        self.tx += (dx * trailer_follow_rate + tiller_offset) * dt

        # Hitch angle calculation
        self.hitch_angle = (self.cx - self.tx) / 2.5

        # Jackknife check: if hitch angle is too severe (> 1.0 rad), vehicle spins out!
        if abs(self.hitch_angle) > 1.0:
            self._crash()
            return

        # 5. Update Road Curvature with distance scroll
        for y in range(16):
            self.road_center[y] = 7.5 + math.sin((y - self.distance * 0.8) * 0.25) * 3.0

        # Check Road Boundary Collisions
        # Cab boundary check (at y = 9)
        c_road_mid = self.road_center[9]
        if abs(self.cx - c_road_mid) > (self.road_width / 2.0 - 0.6):
            self._crash()
            return

        # Trailer boundary check (at y = 12)
        t_road_mid = self.road_center[12]
        if abs(self.tx - t_road_mid) > (self.road_width / 2.0 - 0.6):
            self._crash()
            return

        # 6. Obstacles Update & Collision
        for obs in self.obstacles:
            if obs["alive"]:
                obs["y"] += self.speed * dt
                if obs["y"] > 16.0:
                    # Respawn ahead
                    obs["y"] = -10.0 - (int(self.distance) % 20)
                    obs["x"] = self.road_center[0] + (1.0 if (int(obs["y"]) % 2 == 0) else -1.0)

                # Check collision with Cab or Trailer
                if abs(obs["y"] - self.cy) < 1.0 and abs(obs["x"] - self.cx) < 1.0:
                    if obs["type"] == "car":
                        self._crash()
                        return
                    elif obs["type"] == "oil":
                        # Oil slick triggers sudden violent trailer swing!
                        self.tx += (4.0 if self.cab_vx >= 0 else -4.0) * dt * 8.0

                if abs(obs["y"] - self.ty) < 1.0 and abs(obs["x"] - self.tx) < 1.0:
                    if obs["type"] == "car":
                        self._crash()
                        return
                    elif obs["type"] == "oil":
                        self.tx += 2.0

    def _crash(self) -> None:
        self.lives -= 1
        self.state = STATE_CRASH
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

        # 1. Render Road & Sidewalks
        for y in range(16):
            mid = self.road_center[y]
            left_edge = int(round(mid - self.road_width / 2.0))
            right_edge = int(round(mid + self.road_width / 2.0))

            # Sidewalks / Buildings
            for x in range(0, left_edge):
                set_pixel(x, y, 40, 50, 40)
            for x in range(right_edge + 1, 16):
                set_pixel(x, y, 40, 50, 40)

            # Curb line
            set_pixel(left_edge, y, 220, 220, 220)
            set_pixel(right_edge, y, 220, 220, 220)

            # Road surface
            for x in range(left_edge + 1, right_edge):
                set_pixel(x, y, 25, 25, 30)

            # Center dashed line
            if (int(self.distance + y) % 4) < 2:
                set_pixel(int(round(mid)), y, 240, 220, 60)

        # 2. Render Obstacles
        for obs in self.obstacles:
            if obs["alive"] and 0 <= obs["y"] < 16:
                ox = int(round(obs["x"]))
                oy = int(round(obs["y"]))
                if obs["type"] == "car":
                    set_pixel(ox, oy, 60, 140, 240)
                    set_pixel(ox, oy - 1, 200, 200, 255)
                elif obs["type"] == "oil":
                    set_pixel(ox, oy, 20, 20, 20)
                    set_pixel(ox + 1, oy, 40, 30, 20)

        # 3. Render Hitch Coupling Beam
        cx_i = int(round(self.cx))
        cy_i = int(round(self.cy))
        tx_i = int(round(self.tx))
        ty_i = int(round(self.ty))

        for step in range(1, 3):
            t = step / 3.0
            hx = int(round(self.cx + (self.tx - self.cx) * t))
            hy = int(round(self.cy + (self.ty - self.cy) * t))
            set_pixel(hx, hy, 180, 180, 190)

        # 4. Render Trailer (Rear Ladder Body: Red with Silver Ladder)
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(tx_i, ty_i, 230, 30, 30)
            set_pixel(tx_i - 1, ty_i, 180, 20, 20)
            set_pixel(tx_i, ty_i - 1, 220, 220, 240)  # Silver ladder rungs
            set_pixel(tx_i, ty_i + 1, 220, 30, 30)
            set_pixel(tx_i + 1, ty_i, 180, 20, 20)

            # 5. Render Cab (Front Tractor: Red with Emergency Siren Flashing)
            set_pixel(cx_i, cy_i, 240, 30, 30)
            set_pixel(cx_i - 1, cy_i, 200, 25, 25)
            set_pixel(cx_i + 1, cy_i, 200, 25, 25)
            set_pixel(cx_i, cy_i - 1, 255, 255, 255)  # Windshield
            # Flashing blue/red emergency beacon on cab roof
            flash = int(self.distance * 4) % 2
            if flash == 0:
                set_pixel(cx_i, cy_i - 1, 255, 30, 30)
            else:
                set_pixel(cx_i, cy_i - 1, 50, 150, 255)
        elif self.state == STATE_CRASH:
            set_pixel(cx_i, cy_i, 255, 120, 20)
            set_pixel(cx_i - 1, cy_i, 255, 40, 20)
            set_pixel(tx_i, ty_i, 255, 80, 20)

        # 6. Distance Progress Bar along Col 0
        progress_h = int(round((self.distance / self.target_distance) * 15.0))
        for y in range(min(16, progress_h + 1)):
            set_pixel(0, 15 - y, 240, 60, 40)

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
            "time_left": self.time_left,
            "distance": self.distance,
            "cx": self.cx,
            "tx": self.tx,
            "hitch_angle": self.hitch_angle,
            "speed": self.speed,
        }
