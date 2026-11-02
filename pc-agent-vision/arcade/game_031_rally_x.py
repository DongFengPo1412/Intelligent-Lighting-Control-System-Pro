"""
Game #031: 像素拉力赛车 (Rally-X 1980 / Namco)
Iconic Maze Radar Driving with Checkered Flags, Chasing Red Cars & Smoke Screen Stun Defense.
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

DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]


class Game031RallyX(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.fuel = 100.0
        self.player_x = 7.0
        self.player_y = 13.0
        self.player_dir = 0
        self.next_dir = 0
        self.smoke_cooldown = 0.0

        self.maze: List[List[int]] = [[0 for _ in range(16)] for _ in range(16)]
        self.flags: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.smokes: List[Dict[str, Any]] = []

        self.init_maze()
        self.reset_cars()

    @property
    def game_id(self) -> int:
        return 31

    @property
    def name(self) -> str:
        return "像素拉力赛车"

    @property
    def english_name(self) -> str:
        return "Rally-X 1980"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "雷达军旗迷宫收集 + 追击红车走位摆脱 + 尾部烟幕眩晕阻截 + 燃油动态损耗"

    def init(self) -> None:
        self.reset()

    def get_status(self) -> Dict[str, Any]:
        collected = sum(1 for f in self.flags if f["collected"])
        prog = (collected * 100) // 8
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "fuel": self.fuel,
            "flags_remaining": self.get_flags_remaining(),
            "progress_percent": min(100, prog),
        }

    def init_maze(self):
        self.maze = [[0 for _ in range(16)] for _ in range(16)]

        # Outer walls (Row 0 is HUD)
        for x in range(16):
            self.maze[1][x] = 1
            self.maze[15][x] = 1
        for y in range(1, 16):
            self.maze[y][0] = 1
            self.maze[y][15] = 1

        # Rocks inside arena
        rocks = [
            (3, 3), (4, 3), (7, 3), (8, 3), (11, 3), (12, 3),
            (3, 6), (3, 7), (12, 6), (12, 7),
            (7, 7), (8, 7),
            (3, 10), (4, 10), (7, 10), (8, 10), (11, 10), (12, 10)
        ]
        for rx, ry in rocks:
            self.maze[ry][rx] = 2

        # 8 Checkered Flags
        flag_coords = [
            (2, 2), (13, 2),
            (7, 5),
            (2, 8), (13, 8),
            (5, 12), (10, 12),
            (8, 8) # Lucky flag
        ]
        self.flags = []
        for i, (fx, fy) in enumerate(flag_coords):
            self.flags.append({
                "x": fx,
                "y": fy,
                "collected": False,
                "is_special": (i == 7)
            })

        self.smokes = []

    def reset_cars(self):
        self.player_x = 7.0
        self.player_y = 13.0
        self.player_dir = 0
        self.next_dir = 0

        self.enemies = [
            {"x": 2.0, "y": 4.0, "dir": 1, "stun_timer": 0.0, "active": True},
            {"x": 13.0, "y": 4.0, "dir": 3, "stun_timer": 0.0, "active": True},
            {"x": 7.0, "y": 2.0, "dir": 2, "stun_timer": 0.0, "active": True},
        ]

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.fuel = 100.0
        self.smoke_cooldown = 0.0
        self.init_maze()
        self.reset_cars()

    def is_wall_or_rock(self, x: int, y: int) -> bool:
        if x < 0 or x >= 16 or y < 1 or y >= 16:
            return True
        return self.maze[y][x] != 0

    def get_flags_remaining(self) -> int:
        return sum(1 for f in self.flags if not f["collected"])

    def deploy_smoke(self) -> bool:
        if self.fuel <= 0.0 or self.smoke_cooldown > 0.0:
            return False

        back_dir = (self.player_dir + 2) % 4
        sx = int(round(self.player_x)) + DX[back_dir]
        sy = int(round(self.player_y)) + DY[back_dir]
        sx = max(1, min(14, sx))
        sy = max(2, min(14, sy))

        self.smokes.append({
            "x": sx,
            "y": sy,
            "timer": 3.0,
            "active": True
        })
        self.fuel = max(0.0, self.fuel - 6.0)
        self.smoke_cooldown = 0.4
        return True

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.2:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.reset_cars()
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        # Playing state
        if self.smoke_cooldown > 0.0:
            self.smoke_cooldown -= dt

        if self.fuel > 0.0:
            self.fuel = max(0.0, self.fuel - 1.5 * dt)

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.deploy_smoke()

        self.update_player(dt, buttons)
        self.update_enemies(dt)
        self.update_smokes(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int):
        if buttons & KEY_UP:
            self.next_dir = 0
        elif buttons & KEY_RIGHT:
            self.next_dir = 1
        elif buttons & KEY_DOWN:
            self.next_dir = 2
        elif buttons & KEY_LEFT:
            self.next_dir = 3

        speed = 4.2 if self.fuel > 0.0 else 2.2

        gx = round(self.player_x)
        gy = round(self.player_y)
        dist_to_center = abs(self.player_x - gx) + abs(self.player_y - gy)

        if dist_to_center < 0.25 and self.next_dir != self.player_dir:
            nx = int(gx) + DX[self.next_dir]
            ny = int(gy) + DY[self.next_dir]
            if not self.is_wall_or_rock(nx, ny):
                self.player_x = float(gx)
                self.player_y = float(gy)
                self.player_dir = self.next_dir

        next_x = self.player_x + DX[self.player_dir] * speed * dt
        next_y = self.player_y + DY[self.player_dir] * speed * dt

        check_x = int(round(next_x + DX[self.player_dir] * 0.45))
        check_y = int(round(next_y + DY[self.player_dir] * 0.45))

        if not self.is_wall_or_rock(check_x, check_y):
            self.player_x = next_x
            self.player_y = next_y
        else:
            self.player_x = float(gx)
            self.player_y = float(gy)

        self.player_x = max(1.0, min(14.0, self.player_x))
        self.player_y = max(2.0, min(14.0, self.player_y))

    def update_enemies(self, dt: float):
        enemy_speed = 3.2

        for enemy in self.enemies:
            if not enemy["active"]:
                continue

            if enemy["stun_timer"] > 0.0:
                enemy["stun_timer"] -= dt
                continue

            egx = round(enemy["x"])
            egy = round(enemy["y"])
            dist_to_center = abs(enemy["x"] - egx) + abs(enemy["y"] - egy)

            if dist_to_center < 0.22:
                best_dir = enemy["dir"]
                best_dist = 99999.0
                opposite_dir = (enemy["dir"] + 2) % 4

                for d in range(4):
                    test_x = int(egx) + DX[d]
                    test_y = int(egy) + DY[d]

                    if not self.is_wall_or_rock(test_x, test_y):
                        penalty = 8.0 if d == opposite_dir else 0.0
                        d2 = (test_x - self.player_x) ** 2 + (test_y - self.player_y) ** 2 + penalty
                        if d2 < best_dist:
                            best_dist = d2
                            best_dir = d

                enemy["x"] = float(egx)
                enemy["y"] = float(egy)
                enemy["dir"] = best_dir

            enemy["x"] += DX[enemy["dir"]] * enemy_speed * dt
            enemy["y"] += DY[enemy["dir"]] * enemy_speed * dt

    def update_smokes(self, dt: float):
        for smoke in self.smokes:
            if not smoke["active"]:
                continue

            smoke["timer"] -= dt
            if smoke["timer"] <= 0.0:
                smoke["active"] = False
                continue

            for enemy in self.enemies:
                if enemy["active"] and enemy["stun_timer"] <= 0.0:
                    dist = abs(enemy["x"] - smoke["x"]) + abs(enemy["y"] - smoke["y"])
                    if dist < 0.85:
                        enemy["stun_timer"] = 2.8
                        self.score += 100
                        if self.score > self.high_score:
                            self.high_score = self.score

        self.smokes = [s for s in self.smokes if s["active"]]

    def check_collisions(self):
        # Flags
        for flag in self.flags:
            if not flag["collected"]:
                dist = abs(self.player_x - flag["x"]) + abs(self.player_y - flag["y"])
                if dist < 0.75:
                    flag["collected"] = True
                    if flag["is_special"]:
                        self.score += 400 + int(self.fuel) * 5
                    else:
                        self.score += 100
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if self.get_flags_remaining() == 0:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000 + int(self.fuel) * 10
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

        # Enemies
        for enemy in self.enemies:
            if enemy["active"] and enemy["stun_timer"] <= 0.0:
                dist = abs(self.player_x - enemy["x"]) + abs(self.player_y - enemy["y"])
                if dist < 0.72:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def render(self) -> bytes:
        fb = bytearray([16, 20, 24] * 256)

        # 1. Top HUD
        fuel_dots = int((self.fuel / 100.0) * 8.0)
        for x in range(8):
            idx = x * 3
            if x < fuel_dots:
                if self.fuel > 50.0:
                    fb[idx:idx + 3] = bytes([46, 204, 113])
                elif self.fuel > 20.0:
                    fb[idx:idx + 3] = bytes([241, 196, 15])
                else:
                    fb[idx:idx + 3] = bytes([231, 76, 60])
            else:
                fb[idx:idx + 3] = bytes([40, 40, 40])

        for l in range(min(self.lives, 3)):
            idx = (15 - l) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])

        # 2. Walls and Rocks
        for y in range(1, 16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if self.maze[y][x] == 1:
                    fb[idx:idx + 3] = bytes([100, 110, 120])
                elif self.maze[y][x] == 2:
                    fb[idx:idx + 3] = bytes([180, 90, 40])

        # 3. Flags
        for flag in self.flags:
            if not flag["collected"]:
                idx = (flag["y"] * 16 + flag["x"]) * 3
                if flag["is_special"]:
                    blink = (int(self.state_timer * 6.0) % 2 == 0)
                    if blink:
                        fb[idx:idx + 3] = bytes([255, 215, 0])
                    else:
                        fb[idx:idx + 3] = bytes([231, 76, 60])
                else:
                    fb[idx:idx + 3] = bytes([241, 196, 15])

        # 4. Smokes
        for smoke in self.smokes:
            if smoke["active"]:
                idx = (smoke["y"] * 16 + smoke["x"]) * 3
                fb[idx:idx + 3] = bytes([180, 190, 200])

        # 5. Enemies
        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            ex = int(round(enemy["x"]))
            ey = int(round(enemy["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if enemy["stun_timer"] > 0.0:
                    fb[idx:idx + 3] = bytes([155, 89, 182])
                else:
                    fb[idx:idx + 3] = bytes([231, 76, 60])

        # 6. Player
        if self.state != STATE_DEAD or (int(self.state_timer * 8.0) % 2 == 0):
            px = int(round(self.player_x))
            py = int(round(self.player_y))
            if 0 <= px < 16 and 0 <= py < 16:
                idx = (py * 16 + px) * 3
                fb[idx:idx + 3] = bytes([52, 152, 219])

        # 7. Victory
        if self.state == STATE_VICTORY:
            if int(self.state_timer * 4.0) % 2 == 0:
                for x in range(16):
                    top_idx = (1 * 16 + x) * 3
                    btm_idx = (15 * 16 + x) * 3
                    fb[top_idx:top_idx + 3] = bytes([255, 215, 0])
                    fb[btm_idx:btm_idx + 3] = bytes([255, 215, 0])

        return bytes(fb)
