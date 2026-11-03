# -*- coding: utf-8 -*-
"""
Game #123: 碰碰激光车 (Targ 1980 / Exidy)
街机历史上开创性的网格街道追逐射击游戏：
9x9街区交叉路口高速机动、定向激光炮击破走私车、狂暴变身Spectar黄色突击领航车、氮气紧急加速冲刺。
"""

from typing import List, Dict, Any, Optional
import math
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

STATE_PLAYING = 0
STATE_DYING = 1
STATE_SECTOR_CLEAR = 2
STATE_GAME_OVER = 3

STREETS = [1.5, 4.5, 7.5, 10.5, 13.5]
GRID_MIN = 1.5
GRID_MAX = 13.5
MAX_ENEMIES = 5


class Game123Targ(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.sector = 1
        self.enemies_remaining = 10

        self.px = 7.5
        self.py = 13.5
        self.p_dir_x = 0
        self.p_dir_y = -1
        self.next_dir_x = 0
        self.next_dir_y = -1
        self.turbo_timer = 0.0
        self.turbo_cooldown = 0.0

        self.laser = {
            "x": 0.0,
            "y": 0.0,
            "dir_x": 0,
            "dir_y": 0,
            "active": False,
        }

        self.enemies: List[Dict[str, Any]] = []
        self.spawn_timer = 0.5
        self.reset()

    @property
    def game_id(self) -> int:
        return 123

    @property
    def name(self) -> str:
        return "碰碰激光车"

    @property
    def english_name(self) -> str:
        return "Targ"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "网格交叉路口追逐、正交定向激光炮迎头痛击、变身狂暴黄色Spectar领航战车"

    def get_name(self) -> str:
        return "Targ (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.sector = 1
        self._init_sector()

    def _init_sector(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.enemies_remaining = 10
        self.spawn_timer = 0.5

        self.px = 7.5
        self.py = 13.5
        self.p_dir_x = 0
        self.p_dir_y = -1
        self.next_dir_x = 0
        self.next_dir_y = -1
        self.turbo_timer = 0.0
        self.turbo_cooldown = 0.0

        self.laser = {
            "x": 0.0,
            "y": 0.0,
            "dir_x": 0,
            "dir_y": 0,
            "active": False,
        }

        self.enemies = []
        for _ in range(MAX_ENEMIES):
            self.enemies.append({
                "x": 0.0,
                "y": 0.0,
                "dir_x": 0,
                "dir_y": 0,
                "is_spectar": False,
                "active": False,
            })

    def spawn_enemy(self) -> None:
        for enemy in self.enemies:
            if not enemy["active"]:
                corner = random.randint(0, 4)
                enemy["x"] = STREETS[corner]
                enemy["y"] = GRID_MIN
                enemy["dir_x"] = 1 if random.random() < 0.5 else -1
                enemy["dir_y"] = 1
                enemy["is_spectar"] = (self.enemies_remaining <= 3) or (random.random() < 0.25)
                enemy["active"] = True
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

        if self.state == STATE_DYING:
            if self.state_timer > 1.2:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.5
                    self.p_dir_x = 0
                    self.p_dir_y = -1
                    self.next_dir_x = 0
                    self.next_dir_y = -1
                    self.laser["active"] = False
            return

        if self.state == STATE_SECTOR_CLEAR:
            if self.state_timer > 1.5:
                self.sector += 1
                self.score += 1500
                self._init_sector()
            return

        # Controls
        # Button A: Laser Cannon
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not self.laser["active"]:
                self.laser["active"] = True
                self.laser["x"] = self.px + self.p_dir_x * 0.8
                self.laser["y"] = self.py + self.p_dir_y * 0.8
                self.laser["dir_x"] = self.p_dir_x
                self.laser["dir_y"] = self.p_dir_y

        # Button B: Nitro Turbo
        if self.turbo_cooldown > 0.0:
            self.turbo_cooldown -= dt
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.turbo_cooldown <= 0.0:
                self.turbo_timer = 0.8
                self.turbo_cooldown = 2.5
        if self.turbo_timer > 0.0:
            self.turbo_timer -= dt

        self._update_player(dt, buttons)
        self._update_laser(dt)
        self._update_enemies(dt)
        self._check_collisions()

        # Check sector victory
        if self.enemies_remaining == 0:
            any_alive = any(e["active"] for e in self.enemies)
            if not any_alive:
                self.state = STATE_SECTOR_CLEAR
                self.state_timer = 0.0

    def _update_player(self, dt: float, buttons: int) -> None:
        if buttons & KEY_UP:
            self.next_dir_x = 0
            self.next_dir_y = -1
        elif buttons & KEY_DOWN:
            self.next_dir_x = 0
            self.next_dir_y = 1
        elif buttons & KEY_LEFT:
            self.next_dir_x = -1
            self.next_dir_y = 0
        elif buttons & KEY_RIGHT:
            self.next_dir_x = 1
            self.next_dir_y = 0

        speed = 10.0 if (self.turbo_timer > 0.0) else 5.5

        # Turning logic
        if self.next_dir_x != self.p_dir_x or self.next_dir_y != self.p_dir_y:
            if self.next_dir_x == -self.p_dir_x and self.next_dir_y == -self.p_dir_y:
                self.p_dir_x = self.next_dir_x
                self.p_dir_y = self.next_dir_y
            else:
                for s in STREETS:
                    if self.next_dir_x != 0 and abs(self.py - s) < 0.35:
                        self.py = s
                        self.p_dir_x = self.next_dir_x
                        self.p_dir_y = self.next_dir_y
                        break
                    if self.next_dir_y != 0 and abs(self.px - s) < 0.35:
                        self.px = s
                        self.p_dir_x = self.next_dir_x
                        self.p_dir_y = self.next_dir_y
                        break

        self.px += self.p_dir_x * speed * dt
        self.py += self.p_dir_y * speed * dt

        if self.px < GRID_MIN:
            self.px = GRID_MIN
            self.p_dir_x = 0
        elif self.px > GRID_MAX:
            self.px = GRID_MAX
            self.p_dir_x = 0

        if self.py < GRID_MIN:
            self.py = GRID_MIN
            self.p_dir_y = 0
        elif self.py > GRID_MAX:
            self.py = GRID_MAX
            self.p_dir_y = 0

    def _update_laser(self, dt: float) -> None:
        if not self.laser["active"]:
            return
        laser_speed = 28.0
        self.laser["x"] += self.laser["dir_x"] * laser_speed * dt
        self.laser["y"] += self.laser["dir_y"] * laser_speed * dt

        if (
            self.laser["x"] < GRID_MIN - 0.5
            or self.laser["x"] > GRID_MAX + 0.5
            or self.laser["y"] < GRID_MIN - 0.5
            or self.laser["y"] > GRID_MAX + 0.5
        ):
            self.laser["active"] = False

    def _update_enemies(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0 and self.enemies_remaining > 0:
            self.spawn_timer = max(0.8, 1.8 - self.sector * 0.1)
            self.spawn_enemy()

        for enemy in self.enemies:
            if not enemy["active"]:
                continue

            base_speed = (6.0 + self.sector * 0.4) if enemy["is_spectar"] else (4.0 + self.sector * 0.25)
            enemy["x"] += enemy["dir_x"] * base_speed * dt
            enemy["y"] += enemy["dir_y"] * base_speed * dt

            # Turn at intersections
            for sx in STREETS:
                for sy in STREETS:
                    if abs(enemy["x"] - sx) < 0.25 and abs(enemy["y"] - sy) < 0.25:
                        enemy["x"] = sx
                        enemy["y"] = sy

                        if enemy["is_spectar"]:
                            # Aggressive player tracking
                            dx = self.px - enemy["x"]
                            dy = self.py - enemy["y"]
                            if abs(dx) > abs(dy):
                                enemy["dir_x"] = 1 if dx > 0 else -1
                                enemy["dir_y"] = 0
                            else:
                                enemy["dir_x"] = 0
                                enemy["dir_y"] = 1 if dy > 0 else -1
                        else:
                            if random.random() < 0.5:
                                d = random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
                                enemy["dir_x"] = d[0]
                                enemy["dir_y"] = d[1]

            # Bounce boundaries
            if enemy["x"] <= GRID_MIN:
                enemy["x"] = GRID_MIN
                enemy["dir_x"] = 1
            elif enemy["x"] >= GRID_MAX:
                enemy["x"] = GRID_MAX
                enemy["dir_x"] = -1

            if enemy["y"] <= GRID_MIN:
                enemy["y"] = GRID_MIN
                enemy["dir_y"] = 1
            elif enemy["y"] >= GRID_MAX:
                enemy["y"] = GRID_MAX
                enemy["dir_y"] = -1

    def _check_collisions(self) -> None:
        # Laser vs Enemies
        if self.laser["active"]:
            for enemy in self.enemies:
                if not enemy["active"]:
                    continue

                dx = abs(self.laser["x"] - enemy["x"])
                dy = abs(self.laser["y"] - enemy["y"])
                if dx < 0.9 and dy < 0.9:
                    self.laser["active"] = False
                    enemy["active"] = False
                    if self.enemies_remaining > 0:
                        self.enemies_remaining -= 1
                    if enemy["is_spectar"]:
                        self.score += 500
                    else:
                        self.score += 100
                    break

        # Enemies vs Player
        for enemy in self.enemies:
            if not enemy["active"]:
                continue

            dx = abs(self.px - enemy["x"])
            dy = abs(self.py - enemy["y"])
            if dx < 0.75 and dy < 0.75:
                self.state = STATE_DYING
                self.state_timer = 0.0
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

        # 1. Blocks / buildings
        for by in range(4):
            for bx in range(4):
                x1 = int(STREETS[bx]) + 1
                x2 = int(STREETS[bx + 1]) - 1
                y1 = int(STREETS[by]) + 1
                y2 = int(STREETS[by + 1]) - 1
                for cy in range(y1, y2 + 1):
                    for cx in range(x1, x2 + 1):
                        set_pixel(cx, cy, 15, 25, 45)

        # 2. Streets
        for s in STREETS:
            is_s = int(round(s))
            for p in range(16):
                set_pixel(is_s, p, 30, 35, 55)
                set_pixel(p, is_s, 30, 35, 55)

        # 3. Enemies
        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            ex = int(round(enemy["x"]))
            ey = int(round(enemy["y"]))
            if enemy["is_spectar"]:
                flash = (int(self.state_timer * 10.0) % 2) == 0
                if flash:
                    set_pixel(ex, ey, 255, 255, 0)
                else:
                    set_pixel(ex, ey, 255, 140, 0)
            else:
                set_pixel(ex, ey, 255, 40, 70)

        # 4. Laser
        if self.laser["active"]:
            lx = int(round(self.laser["x"]))
            ly = int(round(self.laser["y"]))
            set_pixel(lx, ly, 80, 255, 100)
            set_pixel(lx - self.laser["dir_x"], ly - self.laser["dir_y"], 40, 200, 60)

        # 5. Player
        px_s = int(round(self.px))
        py_s = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_SECTOR_CLEAR):
            if self.turbo_timer > 0.0:
                set_pixel(px_s, py_s, 255, 255, 255)
                set_pixel(px_s - self.p_dir_x, py_s - self.p_dir_y, 0, 220, 255)
            else:
                set_pixel(px_s, py_s, 0, 230, 255)
                set_pixel(px_s - self.p_dir_x, py_s - self.p_dir_y, 0, 120, 180)
        elif self.state == STATE_DYING:
            set_pixel(px_s, py_s, 255, 220, 50)
            set_pixel(px_s - 1, py_s, 255, 60, 20)
            set_pixel(px_s + 1, py_s, 255, 60, 20)
            set_pixel(px_s, py_s - 1, 255, 60, 20)
            set_pixel(px_s, py_s + 1, 255, 60, 20)

        # 6. HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 0, 230, 255)
        for rem in range(min(self.enemies_remaining, 5)):
            set_pixel(15 - rem * 2, 0, 255, 40, 70)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "sector": self.sector,
            "enemies_remaining": self.enemies_remaining,
            "px": self.px,
            "py": self.py,
            "turbo_active": self.turbo_timer > 0.0,
        }
