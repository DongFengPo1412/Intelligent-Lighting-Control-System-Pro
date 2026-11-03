# -*- coding: utf-8 -*-
"""
Game #125: 碰碰车大乱斗 (Bumping Buggies 1981 / Sanritsu & Sega)
街机历史上经典的游乐场碰碰车冲撞竞技：
弹性碰撞动量转移、油渍漂移失控打滑、高压电网围栏边缘处决、蓄力猛撞与手刹甩尾。
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
STATE_PLAYER_CRASHED = 1
STATE_ROUND_CLEAR = 2
STATE_GAME_OVER = 3

ARENA_MIN = 1.2
ARENA_MAX = 13.8
PI = 3.14159265
MAX_OPPONENTS = 3
MAX_OIL_SLICKS = 3


class Game125BumpingBuggies(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1

        self.player = {
            "x": 7.5,
            "y": 11.5,
            "vx": 0.0,
            "vy": 0.0,
            "angle": -PI * 0.5,
            "spin_timer": 0.0,
            "is_ramming": False,
            "active": True,
        }
        self.ram_cooldown = 0.0
        self.drift_timer = 0.0

        self.opponents: List[Dict[str, Any]] = []
        self.slicks: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 125

    @property
    def name(self) -> str:
        return "碰碰车大乱斗"

    @property
    def english_name(self) -> str:
        return "Bumping Buggies"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "弹性碰撞动量转移、油渍失控打滑、电网围栏边缘冲撞处决与蓄力猛撞"

    def get_name(self) -> str:
        return "Bumping Buggies (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._init_round()

    def _init_round(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0

        self.player = {
            "x": 7.5,
            "y": 11.5,
            "vx": 0.0,
            "vy": 0.0,
            "angle": -PI * 0.5,
            "spin_timer": 0.0,
            "is_ramming": False,
            "active": True,
        }
        self.ram_cooldown = 0.0
        self.drift_timer = 0.0

        opp_coords = [
            (3.5, 3.5),
            (11.5, 3.5),
            (7.5, 5.0),
        ]
        self.opponents = []
        for i in range(MAX_OPPONENTS):
            self.opponents.append({
                "x": opp_coords[i][0],
                "y": opp_coords[i][1],
                "vx": 0.0,
                "vy": 0.0,
                "angle": PI * 0.5,
                "spin_timer": 0.0,
                "is_ramming": False,
                "active": True,
            })

        self.slicks = [
            {"x": 4.5, "y": 8.0, "active": True},
            {"x": 10.5, "y": 8.0, "active": True},
            {"x": 7.5, "y": 3.5, "active": (self.round >= 2)},
        ]

    def get_active_opponents(self) -> int:
        return sum(1 for o in self.opponents if o["active"])

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

        if self.state == STATE_PLAYER_CRASHED:
            if self.state_timer > 1.4:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_PLAYING
                    self.player["x"] = 7.5
                    self.player["y"] = 11.5
                    self.player["vx"] = 0.0
                    self.player["vy"] = 0.0
                    self.player["angle"] = -PI * 0.5
                    self.player["spin_timer"] = 0.0
                    self.player["is_ramming"] = False
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 1.6:
                self.round += 1
                self.score += 1000
                self._init_round()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_opponents(dt)

        # Buggy-to-buggy collisions
        for opp in self.opponents:
            if opp["active"]:
                self._handle_buggy_collision(self.player, opp)

        for i in range(MAX_OPPONENTS):
            for j in range(i + 1, MAX_OPPONENTS):
                if self.opponents[i]["active"] and self.opponents[j]["active"]:
                    self._handle_buggy_collision(self.opponents[i], self.opponents[j])

        self._check_wall_and_hazards()

        if self.get_active_opponents() == 0:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.ram_cooldown > 0.0:
            self.ram_cooldown -= dt
        if self.drift_timer > 0.0:
            self.drift_timer -= dt

        if self.player["spin_timer"] > 0.0:
            self.player["spin_timer"] -= dt
            self.player["angle"] += 14.0 * dt
            self.player["vx"] *= 0.96
            self.player["vy"] *= 0.96
            self.player["x"] += self.player["vx"] * dt
            self.player["y"] += self.player["vy"] * dt
            return

        turn_speed = 8.0 if (self.drift_timer > 0.0) else 4.5
        if buttons & KEY_LEFT:
            self.player["angle"] -= turn_speed * dt
        if buttons & KEY_RIGHT:
            self.player["angle"] += turn_speed * dt

        accel = 8.5
        if buttons & KEY_UP:
            self.player["vx"] += math.cos(self.player["angle"]) * accel * dt
            self.player["vy"] += math.sin(self.player["angle"]) * accel * dt
        if buttons & KEY_DOWN:
            self.player["vx"] -= math.cos(self.player["angle"]) * (accel * 0.5) * dt
            self.player["vy"] -= math.sin(self.player["angle"]) * (accel * 0.5) * dt

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.ram_cooldown <= 0.0:
                self.player["is_ramming"] = True
                self.ram_cooldown = 1.6
                self.player["vx"] += math.cos(self.player["angle"]) * 11.0
                self.player["vy"] += math.sin(self.player["angle"]) * 11.0

        if self.ram_cooldown < 1.1:
            self.player["is_ramming"] = False

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.drift_timer = 0.5

        friction = 0.97 if (self.drift_timer > 0.0) else 0.92
        self.player["vx"] *= friction
        self.player["vy"] *= friction

        self.player["x"] += self.player["vx"] * dt
        self.player["y"] += self.player["vy"] * dt

    def _update_opponents(self, dt: float) -> None:
        for opp in self.opponents:
            if not opp["active"]:
                continue

            if opp["spin_timer"] > 0.0:
                opp["spin_timer"] -= dt
                opp["angle"] += 12.0 * dt
                opp["vx"] *= 0.96
                opp["vy"] *= 0.96
                opp["x"] += opp["vx"] * dt
                opp["y"] += opp["vy"] * dt
                continue

            dx = self.player["x"] - opp["x"]
            dy = self.player["y"] - opp["y"]
            target_angle = math.atan2(dy, dx)

            angle_diff = target_angle - opp["angle"]
            while angle_diff > PI:
                angle_diff -= 2.0 * PI
            while angle_diff < -PI:
                angle_diff += 2.0 * PI

            opp_turn = 3.2 + self.round * 0.3
            if angle_diff > 0.1:
                opp["angle"] += opp_turn * dt
            elif angle_diff < -0.1:
                opp["angle"] -= opp_turn * dt

            opp_speed = 5.5 + self.round * 0.4
            opp["vx"] += math.cos(opp["angle"]) * opp_speed * dt
            opp["vy"] += math.sin(opp["angle"]) * opp_speed * dt

            opp["vx"] *= 0.92
            opp["vy"] *= 0.92

            opp["x"] += opp["vx"] * dt
            opp["y"] += opp["vy"] * dt

    def _handle_buggy_collision(self, a: Dict[str, Any], b: Dict[str, Any]) -> None:
        dx = b["x"] - a["x"]
        dy = b["y"] - a["y"]
        dist = math.sqrt(dx * dx + dy * dy)
        min_dist = 1.35

        if 0.001 < dist < min_dist:
            nx = dx / dist
            ny = dy / dist

            rvx = b["vx"] - a["vx"]
            rvy = b["vy"] - a["vy"]
            vel_along_normal = rvx * nx + rvy * ny

            if vel_along_normal < 0.0:
                restitution = 1.4
                if a.get("is_ramming") or b.get("is_ramming"):
                    restitution = 2.4

                impulse = -(1.0 + restitution) * vel_along_normal * 0.5

                a["vx"] -= impulse * nx
                a["vy"] -= impulse * ny
                b["vx"] += impulse * nx
                b["vy"] += impulse * ny

                overlap = (min_dist - dist) * 0.5
                a["x"] -= nx * overlap
                a["y"] -= ny * overlap
                b["x"] += nx * overlap
                b["y"] += ny * overlap

    def _check_wall_and_hazards(self) -> None:
        # Oil slicks
        for slick in self.slicks:
            if not slick["active"]:
                continue
            if abs(self.player["x"] - slick["x"]) < 0.9 and abs(self.player["y"] - slick["y"]) < 0.9:
                self.player["spin_timer"] = 0.8

            for opp in self.opponents:
                if not opp["active"]:
                    continue
                if abs(opp["x"] - slick["x"]) < 0.9 and abs(opp["y"] - slick["y"]) < 0.9:
                    opp["spin_timer"] = 0.8

        # Electrified perimeter
        for opp in self.opponents:
            if not opp["active"]:
                continue
            speed = math.sqrt(opp["vx"] * opp["vx"] + opp["vy"] * opp["vy"])
            if (
                opp["x"] <= ARENA_MIN
                or opp["x"] >= ARENA_MAX
                or opp["y"] <= ARENA_MIN
                or opp["y"] >= ARENA_MAX
            ):
                if speed > 2.5:
                    opp["active"] = False
                    self.score += 500
                else:
                    if opp["x"] <= ARENA_MIN:
                        opp["x"] = ARENA_MIN
                        opp["vx"] = -opp["vx"] * 0.8
                    if opp["x"] >= ARENA_MAX:
                        opp["x"] = ARENA_MAX
                        opp["vx"] = -opp["vx"] * 0.8
                    if opp["y"] <= ARENA_MIN:
                        opp["y"] = ARENA_MIN
                        opp["vy"] = -opp["vy"] * 0.8
                    if opp["y"] >= ARENA_MAX:
                        opp["y"] = ARENA_MAX
                        opp["vy"] = -opp["vy"] * 0.8

        p_speed = math.sqrt(self.player["vx"] * self.player["vx"] + self.player["vy"] * self.player["vy"])
        if (
            self.player["x"] <= ARENA_MIN
            or self.player["x"] >= ARENA_MAX
            or self.player["y"] <= ARENA_MIN
            or self.player["y"] >= ARENA_MAX
        ):
            if p_speed > 5.5:
                self.state = STATE_PLAYER_CRASHED
                self.state_timer = 0.0
            else:
                if self.player["x"] <= ARENA_MIN:
                    self.player["x"] = ARENA_MIN
                    self.player["vx"] = -self.player["vx"] * 0.8
                if self.player["x"] >= ARENA_MAX:
                    self.player["x"] = ARENA_MAX
                    self.player["vx"] = -self.player["vx"] * 0.8
                if self.player["y"] <= ARENA_MIN:
                    self.player["y"] = ARENA_MIN
                    self.player["vy"] = -self.player["vy"] * 0.8
                if self.player["y"] >= ARENA_MAX:
                    self.player["y"] = ARENA_MAX
                    self.player["vy"] = -self.player["vy"] * 0.8

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

        # 1. Electric fence
        spark = (int(self.state_timer * 8.0) % 2) == 0
        fr = 255 if spark else 40
        fg = 220 if spark else 160
        fb_val = 50 if spark else 255
        for p in range(16):
            set_pixel(p, 0, fr, fg, fb_val)
            set_pixel(p, 15, fr, fg, fb_val)
            set_pixel(0, p, fr, fg, fb_val)
            set_pixel(15, p, fr, fg, fb_val)

        # 2. Oil slicks
        for slick in self.slicks:
            if not slick["active"]:
                continue
            sx = int(round(slick["x"]))
            sy = int(round(slick["y"]))
            set_pixel(sx, sy, 30, 20, 50)
            set_pixel(sx + 1, sy, 40, 10, 60)
            set_pixel(sx, sy + 1, 20, 30, 45)

        # 3. Opponent buggies
        opp_colors = [
            (40, 255, 60),
            (220, 40, 255),
            (255, 120, 20),
        ]
        for i, opp in enumerate(self.opponents):
            if not opp["active"]:
                continue
            ox = int(round(opp["x"]))
            oy = int(round(opp["y"]))
            set_pixel(ox, oy, opp_colors[i][0], opp_colors[i][1], opp_colors[i][2])
            hx = ox + int(round(math.cos(opp["angle"])))
            hy = oy + int(round(math.sin(opp["angle"])))
            set_pixel(hx, hy, 255, 255, 255)

        # 4. Player buggy
        px_s = int(round(self.player["x"]))
        py_s = int(round(self.player["y"]))
        if self.state in (STATE_PLAYING, STATE_ROUND_CLEAR):
            if self.player["is_ramming"]:
                set_pixel(px_s, py_s, 255, 255, 255)
            else:
                set_pixel(px_s, py_s, 0, 230, 255)
            hx = px_s + int(round(math.cos(self.player["angle"])))
            hy = py_s + int(round(math.sin(self.player["angle"])))
            set_pixel(hx, hy, 255, 220, 40)
        elif self.state == STATE_PLAYER_CRASHED:
            set_pixel(px_s, py_s, 255, 255, 255)
            set_pixel(px_s - 1, py_s, 0, 200, 255)
            set_pixel(px_s + 1, py_s, 255, 100, 0)
            set_pixel(px_s, py_s - 1, 255, 220, 0)
            set_pixel(px_s, py_s + 1, 0, 200, 255)

        # 5. Lives
        for l in range(min(self.lives, 3)):
            set_pixel(1 + l * 2, 1, 0, 230, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "round": self.round,
            "active_opponents": self.get_active_opponents(),
            "player_x": self.player["x"],
            "player_y": self.player["y"],
            "is_ramming": self.player["is_ramming"],
        }
