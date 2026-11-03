# -*- coding: utf-8 -*-
"""
Game #155: 公路争霸 (Road Fighter 1984 / Konami)
街机历史上最著名的极速飙车与打盘救车甩尾竞速经典：
高低双档极速升档轰油至400公里/小时、高速擦碰引发剧烈鱼尾侧滑、
极速反向打舵漂移救车回正、追赶超车彩虹奖励车补充燃油狂飙冲线。
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
STATE_CAR_CRASHED = 2
STATE_GAME_OVER = 3

ROAD_LEFT = 2.5
ROAD_RIGHT = 12.5
TOTAL_DISTANCE = 1000.0


class Game155RoadFighter(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7.5
        self.speed = 0.0  # km/h (0 to 400)
        self.distance = 0.0
        self.fuel = 100.0

        # Fish-tailing / Slip state
        self.is_slipping = False
        self.slip_dir = 0.0  # -1.0: left, 1.0: right
        self.slip_counter_steer_time = 0.0

        # Traffic & Hazards (y in [0..16], scrolling down relative to player speed)
        self.traffic: List[Dict[str, Any]] = []
        self.oil_slicks: List[Dict[str, Any]] = []
        self.rainbow_car: Optional[Dict[str, Any]] = None

        self.road_scroll = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 155

    @property
    def name(self) -> str:
        return "公路争霸"

    @property
    def english_name(self) -> str:
        return "Road Fighter"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "两档变速极速飙车、撞车侧滑反向打盘救车回正、碾过油渍防甩尾失控与追逐彩虹车燃油补给"

    def get_name(self) -> str:
        return "Road Fighter (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_race()

    def _init_race(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.speed = 100.0
        self.distance = 0.0
        self.fuel = 100.0
        self.is_slipping = False
        self.slip_dir = 0.0
        self.slip_counter_steer_time = 0.0
        self.road_scroll = 0.0

        # Spawn civilian cars ahead
        self.traffic = [
            {"x": 5.0, "y": 2.0, "speed": 140.0, "type": "sedan"},
            {"x": 10.0, "y": -4.0, "speed": 120.0, "type": "truck"},
            {"x": 7.0, "y": -12.0, "speed": 150.0, "type": "sedan"},
        ]

        # Oil slick
        self.oil_slicks = [
            {"x": 6.5, "y": -8.0},
        ]

        # Rainbow fuel car
        self.rainbow_car = {"x": 8.5, "y": -18.0, "speed": 160.0, "active": True}

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_CAR_CRASHED):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_race()
                elif self.state == STATE_CAR_CRASHED:
                    if self.lives > 0 and self.fuel > 5.0:
                        self.px = 7.5
                        self.speed = 80.0
                        self.is_slipping = False
                        self.slip_dir = 0.0
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
        # 1. 2-Speed Gear Throttle
        # Key B: Low Gear (up to 200 km/h)
        # Key A: High Gear (up to 400 km/h)
        target_max_speed = 0.0
        accel = 0.0

        if buttons & KEY_A:
            target_max_speed = 400.0
            accel = 120.0
        elif buttons & KEY_B:
            target_max_speed = 200.0
            accel = 150.0
        else:
            target_max_speed = 0.0
            accel = -80.0

        if self.speed < target_max_speed:
            self.speed = min(target_max_speed, self.speed + accel * dt)
        elif self.speed > target_max_speed:
            self.speed = max(0.0, self.speed - 90.0 * dt)

        # 2. Fuel Consumption & Distance
        fuel_rate = 1.2 + (self.speed / 400.0) * 3.5
        self.fuel = max(0.0, self.fuel - fuel_rate * dt)
        if self.fuel <= 0.0 and self.speed < 10.0:
            self.lives = 0
            self.state = STATE_CAR_CRASHED
            return

        # Distance advance
        dist_advance = (self.speed / 36.0) * dt
        self.distance += dist_advance
        self.road_scroll += (self.speed / 20.0) * dt

        # 3. Steering & Fish-tailing / Counter-Steering
        steer_speed = 6.0
        if not self.is_slipping:
            if buttons & KEY_LEFT:
                self.px -= steer_speed * dt
            elif buttons & KEY_RIGHT:
                self.px += steer_speed * dt
        else:
            # Slipping violently in slip_dir!
            self.px += self.slip_dir * 8.5 * dt

            # Counter-steering check! If player steers against slip_dir:
            counter_steer = False
            if self.slip_dir > 0 and (buttons & KEY_LEFT):
                counter_steer = True
            elif self.slip_dir < 0 and (buttons & KEY_RIGHT):
                counter_steer = True

            if counter_steer:
                self.slip_counter_steer_time += dt
                if self.slip_counter_steer_time >= 0.2:
                    # SAVED! Car straightens out!
                    self.is_slipping = False
                    self.slip_dir = 0.0
                    self.slip_counter_steer_time = 0.0
                    self.score += 200
            else:
                self.slip_counter_steer_time = max(0.0, self.slip_counter_steer_time - dt * 2.0)

        # Guardrail Crash check
        if self.px <= ROAD_LEFT or self.px >= ROAD_RIGHT:
            self._crash()
            return

        # 4. Update Traffic relative to player
        for car in self.traffic:
            rel_speed = (self.speed - car["speed"]) / 25.0
            car["y"] += rel_speed * dt

            # Collision with civilian car -> initiates fish-tail slip!
            if abs(car["y"] - 13.0) < 1.2 and abs(car["x"] - self.px) < 1.0:
                if not self.is_slipping:
                    self.is_slipping = True
                    self.slip_dir = 1.0 if self.px < car["x"] else -1.0
                    self.slip_counter_steer_time = 0.0
                    self.speed = max(60.0, self.speed - 50.0)

            # Respawn car ahead if passed
            if car["y"] > 18.0:
                car["y"] = -5.0 - (len(self.traffic) * 4.0)
                car["x"] = ROAD_LEFT + 1.0 + (int(self.distance) % 8)
                self.score += 50

        # 5. Update Oil Slicks
        for oil in self.oil_slicks:
            oil["y"] += (self.speed / 25.0) * dt
            if abs(oil["y"] - 13.0) < 0.9 and abs(oil["x"] - self.px) < 1.0:
                if not self.is_slipping:
                    self.is_slipping = True
                    self.slip_dir = 1.0 if self.px <= 7.5 else -1.0
                    self.slip_counter_steer_time = 0.0

            if oil["y"] > 18.0:
                oil["y"] = -15.0
                oil["x"] = ROAD_LEFT + 2.0 + (int(self.distance * 3) % 6)

        # 6. Update Rainbow Car
        if self.rainbow_car and self.rainbow_car["active"]:
            rel_speed = (self.speed - self.rainbow_car["speed"]) / 25.0
            self.rainbow_car["y"] += rel_speed * dt

            # Overlapping rainbow car gives massive fuel boost!
            if abs(self.rainbow_car["y"] - 13.0) < 1.2 and abs(self.rainbow_car["x"] - self.px) < 1.2:
                self.rainbow_car["active"] = False
                self.fuel = min(100.0, self.fuel + 30.0)
                self.score += 1000

            if self.rainbow_car["y"] > 18.0:
                self.rainbow_car["y"] = -25.0
                self.rainbow_car["active"] = True

        # 7. Check Finish Line
        if self.distance >= TOTAL_DISTANCE:
            self.score += 3000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _crash(self) -> None:
        self.lives -= 1
        self.fuel = max(0.0, self.fuel - 15.0)
        self.speed = 0.0
        self.state = STATE_CAR_CRASHED
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

        # 1. Road Surface (Dark Asphalt) & Guardrails
        for y in range(16):
            # Grass borders
            set_pixel(0, y, 40, 140, 40)
            set_pixel(1, y, 50, 160, 50)
            set_pixel(14, y, 50, 160, 50)
            set_pixel(15, y, 40, 140, 40)

            # Striped red/white curbs
            curb_color = (240, 40, 40) if int(y + self.road_scroll) % 2 == 0 else (240, 240, 240)
            set_pixel(2, y, curb_color[0], curb_color[1], curb_color[2])
            set_pixel(13, y, curb_color[0], curb_color[1], curb_color[2])

            # Asphalt
            for x in range(3, 13):
                set_pixel(x, y, 50, 50, 55)

            # Center dashed white lines
            if int(y + self.road_scroll * 1.5) % 4 < 2:
                set_pixel(7, y, 220, 220, 220)
                set_pixel(8, y, 220, 220, 220)

        # 2. Oil Slicks (Black sludge)
        for oil in self.oil_slicks:
            ox = int(round(oil["x"]))
            oy = int(round(oil["y"]))
            set_pixel(ox, oy, 20, 20, 25)
            set_pixel(ox + 1, oy, 20, 20, 25)

        # 3. Traffic Cars
        for car in self.traffic:
            cx = int(round(car["x"]))
            cy = int(round(car["y"]))
            if car["type"] == "sedan":
                set_pixel(cx, cy, 240, 200, 30)       # Yellow sedan
                set_pixel(cx, cy - 1, 200, 160, 20)
            else:
                set_pixel(cx, cy, 60, 140, 220)       # Blue truck
                set_pixel(cx, cy - 1, 40, 100, 180)

        # 4. Rainbow Bonus Car
        if self.rainbow_car and self.rainbow_car["active"]:
            rx = int(round(self.rainbow_car["x"]))
            ry = int(round(self.rainbow_car["y"]))
            set_pixel(rx, ry, 255, 60, 220)           # Flashing magenta
            set_pixel(rx, ry - 1, 80, 255, 200)

        # 5. Player Supercar (Red Speedster)
        px = int(round(self.px))
        py = 13
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 240, 30, 30)            # Red body
            set_pixel(px, py - 1, 255, 60, 60)        # Hood
            set_pixel(px - 1, py, 40, 40, 40)         # Rear left tire
            set_pixel(px + 1, py, 40, 40, 40)         # Rear right tire
            # Slip spin spark
            if self.is_slipping:
                set_pixel(px - 1, py + 1, 255, 200, 50)
                set_pixel(px + 1, py + 1, 255, 200, 50)
        elif self.state == STATE_CAR_CRASHED:
            # Explosion fire
            set_pixel(px, py, 255, 120, 30)
            set_pixel(px, py - 1, 255, 220, 50)

        # 6. Fuel Gauge on left edge
        fuel_h = int((self.fuel / 100.0) * 8.0)
        for fy in range(fuel_h):
            set_pixel(0, 15 - fy, 40, 220, 80)

        # 7. Speed Indicator / Progress on right edge
        dist_h = int((self.distance / TOTAL_DISTANCE) * 8.0)
        for dy in range(dist_h):
            set_pixel(15, 15 - dy, 255, 200, 40)

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
            "px": self.px,
            "speed": self.speed,
            "distance": self.distance,
            "fuel": self.fuel,
            "is_slipping": self.is_slipping,
        }
