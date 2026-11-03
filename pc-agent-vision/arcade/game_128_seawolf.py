# -*- coding: utf-8 -*-
"""
Game #128: 潜艇潜望镜猎杀 (Sea Wolf 1976 / Midway)
街机历史上第一人称潜望镜鱼雷猎杀模拟鼻祖：
潜望镜准星全景扫视、多层深度不同航速战舰编队、水面漂雷阻挡弹道、四联装鱼雷管序列齐射与限时猎杀。
"""

from typing import List, Dict, Any, Optional
import random
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

STATE_HUNTING = 0
STATE_PATROL_CLEAR = 1
STATE_GAME_OVER = 2

LANE_Y = [2.5, 4.5, 6.5]
MINE_Y = 9.0
MAX_SHIPS = 4
MAX_MINES = 3
MAX_TORPEDOES = 4


class Game128SeaWolf(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_HUNTING
        self.state_timer = 0.0
        self.score = 0
        self.time_remaining = 60.0
        self.patrol_round = 1
        self.ships_sunk = 0

        self.periscope_x = 7.5

        self.torpedoes: List[Dict[str, Any]] = []
        self.tube_reload_timers = [0.0] * MAX_TORPEDOES

        self.ships: List[Dict[str, Any]] = []
        self.ship_spawn_timer = 0.5

        self.mines: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 128

    @property
    def name(self) -> str:
        return "潜艇潜望镜猎杀"

    @property
    def english_name(self) -> str:
        return "Sea Wolf"

    @property
    def release_year(self) -> int:
        return 1976

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "潜望镜准星全景横移、多层深度不同航速舰队、水面漂雷阻断与四联鱼雷序列齐射"

    def get_name(self) -> str:
        return "Sea Wolf (1976)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.patrol_round = 1
        self._init_patrol()

    def _init_patrol(self) -> None:
        self.state = STATE_HUNTING
        self.state_timer = 0.0
        self.time_remaining = 60.0
        self.ships_sunk = 0
        self.periscope_x = 7.5

        self.torpedoes = []
        for _ in range(MAX_TORPEDOES):
            self.torpedoes.append({
                "x": 0.0,
                "y": 0.0,
                "vy": 0.0,
                "active": False,
            })
        self.tube_reload_timers = [0.0] * MAX_TORPEDOES

        self.ships = []
        for _ in range(MAX_SHIPS):
            self.ships.append({
                "x": 0.0,
                "y": 0.0,
                "vx": 0.0,
                "type": 0,
                "active": False,
            })
        self.ship_spawn_timer = 0.5

        self.mines = [
            {"x": 3.0, "y": MINE_Y, "vx": 1.0, "active": True},
            {"x": 9.0, "y": MINE_Y, "vx": -1.2, "active": True},
            {"x": 14.0, "y": MINE_Y, "vx": 0.8, "active": (self.patrol_round >= 2)},
        ]

    def get_available_tubes(self) -> int:
        count = 0
        for i in range(MAX_TORPEDOES):
            if not self.torpedoes[i]["active"] and self.tube_reload_timers[i] <= 0.0:
                count += 1
        return count

    def spawn_ship(self) -> None:
        for ship in self.ships:
            if not ship["active"]:
                s_type = random.randint(0, 2)
                from_left = random.random() < 0.5
                ship["type"] = s_type
                ship["y"] = LANE_Y[s_type]
                ship["x"] = -2.0 if from_left else 17.5

                base_spd = 4.5 if (s_type == 0) else (2.8 if s_type == 1 else 1.6)
                base_spd += self.patrol_round * 0.2
                ship["vx"] = base_spd if from_left else -base_spd
                ship["active"] = True
                break

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PATROL_CLEAR:
            if self.state_timer > 1.8:
                self.patrol_round += 1
                self.score += 1500
                self._init_patrol()
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            if self.ships_sunk >= 8:
                self.state = STATE_PATROL_CLEAR
                self.state_timer = 0.0
            else:
                self.state = STATE_GAME_OVER
            return

        # Button A: Fire Torpedo
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            for i in range(MAX_TORPEDOES):
                if not self.torpedoes[i]["active"] and self.tube_reload_timers[i] <= 0.0:
                    self.torpedoes[i]["active"] = True
                    self.torpedoes[i]["x"] = self.periscope_x
                    self.torpedoes[i]["y"] = 13.5
                    self.torpedoes[i]["vy"] = -12.0
                    self.tube_reload_timers[i] = 2.2
                    break

        self._update_periscope(dt, buttons)
        self._update_torpedoes(dt)
        self._update_ships(dt)
        self._update_mines(dt)
        self._check_collisions()

    def _update_periscope(self, dt: float, buttons: int) -> None:
        pan_speed = 10.0
        if buttons & KEY_LEFT:
            self.periscope_x -= pan_speed * dt
        if buttons & KEY_RIGHT:
            self.periscope_x += pan_speed * dt

        if self.periscope_x < 0.5:
            self.periscope_x = 0.5
        elif self.periscope_x > 15.5:
            self.periscope_x = 15.5

    def _update_torpedoes(self, dt: float) -> None:
        for i in range(MAX_TORPEDOES):
            if self.tube_reload_timers[i] > 0.0:
                self.tube_reload_timers[i] -= dt

            if not self.torpedoes[i]["active"]:
                continue
            self.torpedoes[i]["y"] += self.torpedoes[i]["vy"] * dt
            if self.torpedoes[i]["y"] < 1.5:
                self.torpedoes[i]["active"] = False

    def _update_ships(self, dt: float) -> None:
        self.ship_spawn_timer -= dt
        if self.ship_spawn_timer <= 0.0:
            self.ship_spawn_timer = max(0.9, 2.0 - self.patrol_round * 0.1)
            self.spawn_ship()

        for ship in self.ships:
            if not ship["active"]:
                continue
            ship["x"] += ship["vx"] * dt
            if ship["x"] < -3.0 or ship["x"] > 18.5:
                ship["active"] = False

    def _update_mines(self, dt: float) -> None:
        for mine in self.mines:
            if not mine["active"]:
                continue
            mine["x"] += mine["vx"] * dt
            if mine["x"] < 0.5:
                mine["x"] = 0.5
                mine["vx"] = -mine["vx"]
            elif mine["x"] > 15.5:
                mine["x"] = 15.5
                mine["vx"] = -mine["vx"]

    def _check_collisions(self) -> None:
        for torp in self.torpedoes:
            if not torp["active"]:
                continue

            # Mines
            for mine in self.mines:
                if not mine["active"]:
                    continue
                if abs(torp["y"] - mine["y"]) < 0.8 and abs(torp["x"] - mine["x"]) < 0.85:
                    torp["active"] = False
                    mine["active"] = False
                    self.score += 20
                    break
            if not torp["active"]:
                continue

            # Ships
            for ship in self.ships:
                if not ship["active"]:
                    continue
                if abs(torp["y"] - ship["y"]) < 0.8:
                    hit_w = 0.9 if (ship["type"] == 0) else 1.4
                    if abs(torp["x"] - ship["x"]) < hit_w:
                        torp["active"] = False
                        ship["active"] = False
                        self.ships_sunk += 1
                        if ship["type"] == 0:
                            self.score += 500
                            self.time_remaining += 5.0
                        elif ship["type"] == 1:
                            self.score += 200
                        else:
                            self.score += 100
                        break

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        elif len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Sky & Horizon
        for x in range(16):
            set_pixel(x, 0, 20, 30, 60)
            set_pixel(x, 1, 40, 70, 110)

        # 2. Water
        for y in range(2, 15):
            blue = min(255, 40 + y * 8)
            for x in range(16):
                set_pixel(x, y, 10, 25, blue)

        # 3. Ships
        for ship in self.ships:
            if not ship["active"]:
                continue
            sx = int(round(ship["x"]))
            sy = int(round(ship["y"]))
            if ship["type"] == 0:
                set_pixel(sx, sy, 255, 220, 40)
                set_pixel(sx - (1 if ship["vx"] > 0 else -1), sy, 255, 120, 20)
            elif ship["type"] == 1:
                set_pixel(sx, sy, 220, 220, 240)
                set_pixel(sx - 1, sy, 160, 170, 190)
                set_pixel(sx + 1, sy, 160, 170, 190)
                set_pixel(sx, sy - 1, 255, 60, 40)
            else:
                set_pixel(sx, sy, 180, 50, 40)
                set_pixel(sx - 1, sy, 140, 40, 30)
                set_pixel(sx + 1, sy, 140, 40, 30)
                set_pixel(sx + 2, sy, 120, 30, 20)

        # 4. Mines
        for mine in self.mines:
            if not mine["active"]:
                continue
            mx = int(round(mine["x"]))
            my = int(round(mine["y"]))
            flash = (int(self.state_timer * 6.0) % 2) == 0
            set_pixel(mx, my, 255 if flash else 180, 40 if flash else 20, 30)

        # 5. Torpedoes
        for torp in self.torpedoes:
            if not torp["active"]:
                continue
            tx = int(round(torp["x"]))
            ty = int(round(torp["y"]))
            set_pixel(tx, ty, 255, 255, 255)
            set_pixel(tx, ty + 1, 100, 220, 255)

        # 6. Periscope crosshair
        px = int(round(self.periscope_x))
        set_pixel(px, 14, 255, 220, 30)
        set_pixel(px - 1, 14, 0, 200, 255)
        set_pixel(px + 1, 14, 0, 200, 255)
        set_pixel(px, 13, 0, 200, 255)

        # 7. Torpedo Tubes
        for i in range(MAX_TORPEDOES):
            x_pos = 2 + i * 3
            if not self.torpedoes[i]["active"] and self.tube_reload_timers[i] <= 0.0:
                set_pixel(x_pos, 15, 0, 255, 180)
                set_pixel(x_pos + 1, 15, 0, 255, 180)
            else:
                set_pixel(x_pos, 15, 120, 30, 20)
                set_pixel(x_pos + 1, 15, 60, 20, 10)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "time_remaining": self.time_remaining,
            "patrol_round": self.patrol_round,
            "ships_sunk": self.ships_sunk,
            "available_tubes": self.get_available_tubes(),
            "periscope_x": self.periscope_x,
        }
