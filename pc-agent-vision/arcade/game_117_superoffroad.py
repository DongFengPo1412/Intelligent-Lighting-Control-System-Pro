"""
Game #117: 超级越野赛车 (Super Off Road 1989 / Leland Corp)
Top-down stadium dirt track racing, 360-degree drifting inertia,
nitro booster turbo bursts, airborne mud mound jumps, and trophy laps.
"""

from typing import List, Dict, Any
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

STATE_RACING = 0
STATE_LAP_COMPLETE = 1
STATE_RACE_FINISHED = 2
STATE_GAME_OVER = 3

TOTAL_LAPS = 3
NUM_WAYPOINTS = 4
PI = math.pi


class Game117SuperOffRoad(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_RACING
        self.state_timer = 0.0
        self.score = 0
        self.nitro_charges = 3
        self.nitro_timer = 0.0

        self.player: Dict[str, Any] = {
            "x": 3.0, "y": 13.0, "angle": 0.0, "speed": 0.0,
            "jump_z": 0.0, "jump_vz": 0.0, "is_airborne": False,
            "current_waypoint": 0, "laps_completed": 0,
        }
        self.rival: Dict[str, Any] = {
            "x": 2.0, "y": 12.0, "angle": 0.0, "speed": 0.0,
            "jump_z": 0.0, "jump_vz": 0.0, "is_airborne": False,
            "current_waypoint": 0, "laps_completed": 0,
        }

        self.waypoints = [
            (13.0, 13.0),
            (13.0, 2.5),
            (2.5, 2.5),
            (2.5, 13.0),
        ]
        self.items: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 117

    @property
    def name(self) -> str:
        return "超级越野赛车"

    @property
    def english_name(self) -> str:
        return "Super Off Road"

    @property
    def release_year(self) -> int:
        return 1989

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "360度俯视泥地弯道漂移、氮气爆发喷射、土丘坡道腾空飞跃与竞速套圈"

    def get_name(self) -> str:
        return "Super Off Road (1989)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.nitro_charges = 3
        self.nitro_timer = 0.0
        self._init_race()

    def _init_race(self) -> None:
        self.state = STATE_RACING
        self.state_timer = 0.0

        self.player = {
            "x": 3.0, "y": 13.0, "angle": 0.0, "speed": 0.0,
            "jump_z": 0.0, "jump_vz": 0.0, "is_airborne": False,
            "current_waypoint": 0, "laps_completed": 0,
        }
        self.rival = {
            "x": 2.0, "y": 12.0, "angle": 0.0, "speed": 0.0,
            "jump_z": 0.0, "jump_vz": 0.0, "is_airborne": False,
            "current_waypoint": 0, "laps_completed": 0,
        }

        self.items = [
            {"x": 8.0, "y": 2.0, "type": 0, "active": True},  # Nitro
            {"x": 2.0, "y": 7.5, "type": 1, "active": True},  # Cash
            {"x": 13.0, "y": 8.0, "type": 1, "active": True}, # Cash
        ]

    def activate_nitro(self) -> None:
        if self.nitro_charges <= 0 or self.state != STATE_RACING:
            return
        self.nitro_charges -= 1
        self.player["speed"] = 10.5
        self.nitro_timer = 1.0

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state in (STATE_GAME_OVER, STATE_RACE_FINISHED):
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.nitro_timer > 0.0:
            self.nitro_timer -= dt

        self._update_player_truck(dt, buttons, prev_buttons)
        self._update_rival_truck(dt)
        self._update_jumps(self.player, dt)
        self._update_jumps(self.rival, dt)
        self._check_ramps_and_mud(self.player)
        self._check_ramps_and_mud(self.rival)
        self._check_waypoints(self.player, True)
        self._check_waypoints(self.rival, False)
        self._check_collisions()

    def _update_player_truck(self, dt: float, buttons: int, prev_buttons: int) -> None:
        rot_speed = 3.8
        if buttons & KEY_LEFT:
            self.player["angle"] -= rot_speed * dt
        if buttons & KEY_RIGHT:
            self.player["angle"] += rot_speed * dt

        if buttons & KEY_UP:
            self.player["speed"] += 12.0 * dt
            max_spd = 10.5 if (self.nitro_timer > 0.0) else 6.2
            if self.player["speed"] > max_spd:
                self.player["speed"] = max_spd
        elif buttons & KEY_DOWN:
            self.player["speed"] -= 8.0 * dt
            if self.player["speed"] < -2.0:
                self.player["speed"] = -2.0
        else:
            self.player["speed"] *= (1.0 - 0.75 * dt)

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.activate_nitro()

        self.player["x"] += math.cos(self.player["angle"]) * self.player["speed"] * dt
        self.player["y"] += math.sin(self.player["angle"]) * self.player["speed"] * dt

        # Outer track barrier bounce
        if self.player["x"] < 1.2:
            self.player["x"] = 1.2
            self.player["speed"] *= -0.3
        if self.player["x"] > 13.8:
            self.player["x"] = 13.8
            self.player["speed"] *= -0.3
        if self.player["y"] < 1.2:
            self.player["y"] = 1.2
            self.player["speed"] *= -0.3
        if self.player["y"] > 13.8:
            self.player["y"] = 13.8
            self.player["speed"] *= -0.3

        # Infield barrier bounce
        if 5.0 <= self.player["x"] <= 10.0 and 5.0 <= self.player["y"] <= 10.0:
            d_left = self.player["x"] - 5.0
            d_right = 10.0 - self.player["x"]
            d_top = self.player["y"] - 5.0
            d_bottom = 10.0 - self.player["y"]
            min_d = min(d_left, d_right, d_top, d_bottom)
            if min_d == d_left:
                self.player["x"] = 4.8
            elif min_d == d_right:
                self.player["x"] = 10.2
            elif min_d == d_top:
                self.player["y"] = 4.8
            else:
                self.player["y"] = 10.2
            self.player["speed"] *= -0.3

    def _update_rival_truck(self, dt: float) -> None:
        wp = self.waypoints[self.rival["current_waypoint"]]
        dx = wp[0] - self.rival["x"]
        dy = wp[1] - self.rival["y"]
        target_angle = math.atan2(dy, dx)

        diff = target_angle - self.rival["angle"]
        while diff > PI:
            diff -= 2.0 * PI
        while diff < -PI:
            diff += 2.0 * PI

        self.rival["angle"] += diff * 4.0 * dt
        self.rival["speed"] = 4.6

        self.rival["x"] += math.cos(self.rival["angle"]) * self.rival["speed"] * dt
        self.rival["y"] += math.sin(self.rival["angle"]) * self.rival["speed"] * dt

    def _update_jumps(self, t: Dict[str, Any], dt: float) -> None:
        if t["is_airborne"]:
            t["jump_vz"] -= 14.0 * dt
            t["jump_z"] += t["jump_vz"] * dt
            if t["jump_z"] <= 0.0:
                t["jump_z"] = 0.0
                t["jump_vz"] = 0.0
                t["is_airborne"] = False

    def _check_ramps_and_mud(self, t: Dict[str, Any]) -> None:
        if t["is_airborne"]:
            return

        if abs(t["x"] - 8.0) < 0.9 and abs(t["y"] - 13.0) < 0.9 and t["speed"] > 2.0:
            t["is_airborne"] = True
            t["jump_vz"] = 5.0
            t["jump_z"] = 0.2

        if abs(t["x"] - 13.0) < 0.9 and abs(t["y"] - 7.5) < 0.9 and t["speed"] > 2.0:
            t["is_airborne"] = True
            t["jump_vz"] = 5.0
            t["jump_z"] = 0.2

    def _check_waypoints(self, t: Dict[str, Any], is_player: bool) -> None:
        wp = self.waypoints[t["current_waypoint"]]
        dx = t["x"] - wp[0]
        dy = t["y"] - wp[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 2.5:
            if t["current_waypoint"] == NUM_WAYPOINTS - 1:
                t["laps_completed"] += 1
                t["current_waypoint"] = 0
                if is_player:
                    self.score += 300
                    if t["laps_completed"] >= TOTAL_LAPS:
                        self.state = STATE_RACE_FINISHED
                        self.score += 1000
            else:
                t["current_waypoint"] += 1

    def _check_collisions(self) -> None:
        for item in self.items:
            if not item["active"]:
                continue
            dx = abs(self.player["x"] - item["x"])
            dy = abs(self.player["y"] - item["y"])
            if dx < 1.0 and dy < 1.0:
                item["active"] = False
                if item["type"] == 0:
                    self.nitro_charges += 1
                    self.score += 50
                else:
                    self.score += 200

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Dirt track and walls
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    set_pixel(x, y, 100, 100, 110)
                elif 5 <= x <= 10 and 5 <= y <= 10:
                    set_pixel(x, y, 40, 120, 50)
                else:
                    dirt = 180 if ((x + y) % 2 == 0) else 160
                    set_pixel(x, y, dirt, dirt - 50, 40)

        # Finish line
        set_pixel(3, 12, 255, 255, 255)
        set_pixel(3, 13, 30, 30, 30)
        set_pixel(3, 14, 255, 255, 255)

        # Ramps
        set_pixel(8, 13, 230, 140, 20)
        set_pixel(8, 12, 210, 120, 20)
        set_pixel(13, 7, 230, 140, 20)
        set_pixel(14, 7, 210, 120, 20)

        # Items
        for item in self.items:
            if not item["active"]:
                continue
            ix = int(round(item["x"]))
            iy = int(round(item["y"]))
            if item["type"] == 0:
                set_pixel(ix, iy, 40, 200, 255)
            else:
                set_pixel(ix, iy, 255, 220, 0)

        # Rival truck
        rx = int(round(self.rival["x"]))
        ry = int(round(self.rival["y"]))
        set_pixel(rx, ry, 255, 40, 30)

        # Player truck
        px = int(round(self.player["x"]))
        py = int(round(self.player["y"]))

        if self.player["is_airborne"]:
            set_pixel(px, py, 60, 40, 20)
            elev_y = max(1, py - int(self.player["jump_z"] * 2.0))
            set_pixel(px, elev_y, 255, 255, 255)
            set_pixel(px, elev_y + 1, 40, 120, 255)
        else:
            set_pixel(px, py, 255, 255, 255)
            nose_x = px + int(round(math.cos(self.player["angle"])))
            nose_y = py + int(round(math.sin(self.player["angle"])))
            set_pixel(nose_x, nose_y, 40, 140, 255)

            if self.nitro_timer > 0.0:
                tail_x = px - int(round(math.cos(self.player["angle"])))
                tail_y = py - int(round(math.sin(self.player["angle"])))
                set_pixel(tail_x, tail_y, 255, 140, 0)

        # HUD
        for n in range(min(self.nitro_charges, 5)):
            set_pixel(1 + n, 0, 0, 240, 255)
        for l in range(self.player["laps_completed"]):
            set_pixel(14 - l, 0, 40, 255, 80)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "nitro_charges": self.nitro_charges,
            "player_x": self.player["x"],
            "player_y": self.player["y"],
            "player_speed": self.player["speed"],
            "player_angle": self.player["angle"],
            "is_airborne": self.player["is_airborne"],
            "laps_completed": self.player["laps_completed"],
        }
