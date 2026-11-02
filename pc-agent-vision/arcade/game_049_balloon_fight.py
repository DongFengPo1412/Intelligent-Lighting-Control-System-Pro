"""
Game #049: 气球大战 (Balloon Fight 1984 / Nintendo)
Buoyancy Flight Physics, Altitude-Differential Balloon Popping, Parachute Descents & Giant Piranha Fish.
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

MAX_ENEMIES = 3
MAX_SPARKS = 2


class Game049BalloonFight(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.player_balloons = 2
        self.enemies_defeated = 0
        self.total_wave_enemies = 4

        self.player_x = 7.5
        self.player_y = 9.0
        self.player_vx = 0.0
        self.player_vy = 0.0

        self.fish_timer = 0.0
        self.fish_leaping = False
        self.fish_x = 0.0

        self.enemies: List[Dict[str, Any]] = []
        self.sparks: List[Dict[str, Any]] = []
        self.platform_grid = [[False for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 49

    @property
    def name(self) -> str:
        return "气球大战"

    @property
    def english_name(self) -> str:
        return "Balloon Fight (1984)"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双气球浮力扑翼惯性物理 + 相对高度碰撞戳爆气球 + 降落伞与巨型食人鱼"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_balloons = 2
        self.enemies_defeated = 0
        self.total_wave_enemies = 4
        self.player_x = 7.5
        self.player_y = 9.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.fish_timer = 0.0
        self.fish_leaping = False
        self.fish_x = 0.0

        self.init_arena()

    def init_arena(self):
        self.platform_grid = [[False for _ in range(16)] for _ in range(16)]

        for x in range(2, 6):
            self.platform_grid[7][x] = True
        for x in range(10, 14):
            self.platform_grid[6][x] = True
        for x in range(6, 10):
            self.platform_grid[11][x] = True

        self.enemies = [
            {"x": 3.5, "y": 6.0, "vx": 2.0, "vy": 0.0, "balloons": 1, "on_parachute": False, "is_pumping": False, "pump_timer": 0.0, "active": True},
            {"x": 11.5, "y": 5.0, "vx": -2.2, "vy": 0.0, "balloons": 1, "on_parachute": False, "is_pumping": False, "pump_timer": 0.0, "active": True},
            {"x": 7.5, "y": 3.0, "vx": 2.4, "vy": 0.0, "balloons": 1, "on_parachute": False, "is_pumping": False, "pump_timer": 0.0, "active": True},
        ]

        self.sparks = [
            {"x": 1.0, "y": 2.0, "vx": 3.2, "vy": 2.8, "active": True},
            {"x": 14.0, "y": 4.0, "vx": -3.0, "vy": 3.0, "active": True},
        ]

    def get_enemies_remaining(self) -> int:
        return self.total_wave_enemies - self.enemies_defeated

    def flap_wings(self, strong: bool):
        impulse = -5.8 if strong else -4.2
        if self.player_balloons == 1:
            impulse *= 0.78
        self.player_vy = impulse

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        gravity = 8.5
        air_accel = 6.0

        if buttons & KEY_LEFT:
            self.player_vx -= air_accel * dt
        if buttons & KEY_RIGHT:
            self.player_vx += air_accel * dt

        self.player_vx *= max(0.0, 1.0 - 1.2 * dt)
        self.player_vx = max(-5.0, min(5.0, self.player_vx))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.flap_wings(True)
        elif buttons & KEY_B:
            self.player_vy -= 12.0 * dt

        self.player_vy += gravity * dt
        self.player_vy = max(-7.0, min(7.0, self.player_vy))

        self.player_x += self.player_vx * dt
        self.player_y += self.player_vy * dt

        if self.player_x < 0.0:
            self.player_x += 16.0
        if self.player_x >= 16.0:
            self.player_x -= 16.0

        if self.player_y < 0.5:
            self.player_y = 0.5
            self.player_vy = 0.5

        # Platform landing
        foot_x = int(round(self.player_x))
        foot_y = int(round(self.player_y + 0.6))
        if 0 <= foot_x < 16 and 0 <= foot_y < 16:
            if self.platform_grid[foot_y][foot_x] and self.player_vy > 0.0 and self.player_y <= foot_y - 0.4:
                self.player_y = float(foot_y - 0.6)
                self.player_vy = 0.0

        # Water splash
        if self.player_y >= 14.5:
            self.lives -= 1
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        # Giant fish
        if self.player_y >= 13.0:
            self.fish_timer += dt
            if self.fish_timer >= 0.8:
                self.fish_leaping = True
                self.fish_x = self.player_x
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return
        else:
            self.fish_timer = max(0.0, self.fish_timer - dt)

    def update_enemies(self, dt: float):
        gravity = 7.5

        for e in self.enemies:
            if not e["active"]:
                continue

            if e["is_pumping"]:
                e["pump_timer"] += dt
                if e["pump_timer"] >= 3.5:
                    e["is_pumping"] = False
                    e["balloons"] = 1
                    e["vy"] = -3.5
                continue

            if e["on_parachute"]:
                e["y"] += 1.8 * dt
                fx = int(round(e["x"]))
                fy = int(round(e["y"] + 0.6))
                if 0 <= fx < 16 and 0 <= fy < 16:
                    if self.platform_grid[fy][fx]:
                        e["y"] = float(fy - 0.6)
                        e["on_parachute"] = False
                        e["is_pumping"] = True
                        e["pump_timer"] = 0.0
                        continue

                if e["y"] >= 14.5:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 100
                    if self.score > self.high_score:
                        self.high_score = self.score
                continue

            e["vy"] += gravity * dt
            if e["y"] > self.player_y + 0.5 or e["vy"] > 2.0:
                e["vy"] = -4.5

            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["x"] < 0.0:
                e["x"] += 16.0
            if e["x"] >= 16.0:
                e["x"] -= 16.0

            if e["y"] < 0.5:
                e["y"] = 0.5
                e["vy"] = 1.0

    def update_sparks(self, dt: float):
        for s in self.sparks:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt

            if s["x"] <= 0.0:
                s["x"] = 0.0
                s["vx"] = abs(s["vx"])
            elif s["x"] >= 15.0:
                s["x"] = 15.0
                s["vx"] = -abs(s["vx"])

            if s["y"] <= 0.5:
                s["y"] = 0.5
                s["vy"] = abs(s["vy"])
            elif s["y"] >= 14.0:
                s["y"] = 14.0
                s["vy"] = -abs(s["vy"])

    def check_collisions(self):
        # 1. Player vs Enemies (Altitude Difference Rule)
        for e in self.enemies:
            if not e["active"]:
                continue

            dist_x = abs(self.player_x - e["x"])
            dist_y = self.player_y - e["y"]

            if dist_x <= 0.85 and abs(dist_y) <= 0.85:
                # Player is higher: pop enemy
                if dist_y < -0.2:
                    if e["balloons"] > 0:
                        e["balloons"] = 0
                        e["on_parachute"] = True
                        self.player_vy = -3.5
                        self.score += 100
                        if self.score > self.high_score:
                            self.high_score = self.score
                    elif e["on_parachute"] or e["is_pumping"]:
                        e["active"] = False
                        self.enemies_defeated += 1
                        self.player_vy = -3.5
                        self.score += 200
                        if self.score > self.high_score:
                            self.high_score = self.score

                        if self.enemies_defeated >= self.total_wave_enemies:
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                            self.score += 1000
                            if self.score > self.high_score:
                                self.high_score = self.score
                            return
                # Enemy is higher: pop player
                elif dist_y > 0.2:
                    self.player_balloons -= 1
                    e["vy"] = -3.5

                    if self.player_balloons <= 0:
                        self.lives -= 1
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

        # 2. Player vs Lightning Sparks
        for s in self.sparks:
            if not s["active"]:
                continue
            if abs(self.player_x - s["x"]) <= 0.75 and abs(self.player_y - s["y"]) <= 0.75:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_balloons = 2
                    self.player_x = 7.5
                    self.player_y = 9.0
                    self.player_vx = 0.0
                    self.player_vy = 0.0
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.update_sparks(dt)
        self.check_collisions()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for i in range(256):
            fb[i * 3 + 0] = 8
            fb[i * 3 + 1] = 8
            fb[i * 3 + 2] = 8

        # Platforms
        for y in range(16):
            for x in range(16):
                if self.platform_grid[y][x]:
                    idx = (y * 16 + x) * 3
                    fb[idx + 0] = 46
                    fb[idx + 1] = 204
                    fb[idx + 2] = 113

        # Water
        for x in range(16):
            idx = (15 * 16 + x) * 3
            fb[idx + 0] = 26
            fb[idx + 1] = 82
            fb[idx + 2] = 118

        # Sparks
        for s in self.sparks:
            if not s["active"]:
                continue
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            if 0 <= sx < 16 and 0 <= sy < 16:
                idx = (sy * 16 + sx) * 3
                fb[idx + 0] = 0
                fb[idx + 1] = 255
                fb[idx + 2] = 255

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if e["balloons"] > 0:
                    fb[idx + 0] = 241
                    fb[idx + 1] = 196
                    fb[idx + 2] = 15
                elif e["on_parachute"]:
                    fb[idx + 0] = 255
                    fb[idx + 1] = 255
                    fb[idx + 2] = 255
                else:
                    fb[idx + 0] = 155
                    fb[idx + 1] = 89
                    fb[idx + 2] = 182

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            if self.player_balloons >= 2:
                fb[idx + 0] = 231
                fb[idx + 1] = 76
                fb[idx + 2] = 60
            elif self.player_balloons == 1:
                fb[idx + 0] = 230
                fb[idx + 1] = 126
                fb[idx + 2] = 34
            else:
                fb[idx + 0] = 100
                fb[idx + 1] = 100
                fb[idx + 2] = 100

        # Giant fish snap
        if self.fish_leaping:
            fx = int(round(self.fish_x))
            if 0 <= fx < 16:
                idx = (14 * 16 + fx) * 3
                fb[idx + 0] = 243
                fb[idx + 1] = 156
                fb[idx + 2] = 18

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "player_balloons": self.player_balloons,
            "enemies_remaining": self.get_enemies_remaining(),
            "player_x": self.player_x,
            "player_y": self.player_y,
            "player_vy": self.player_vy,
            "fish_leaping": self.fish_leaping,
        }
