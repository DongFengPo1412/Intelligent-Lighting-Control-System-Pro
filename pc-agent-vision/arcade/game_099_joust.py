"""
Game #099: 鸵鸟骑士 / 扑翼角斗 (Joust 1982 / Williams)
Flapping flight physics, altitude-dominance lance jousting collisions, egg harvesting & lava troll hand escapes.
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

STATE_JOUSTING = 0
STATE_KNIGHT_DOWN = 1
STATE_WAVE_CLEAR = 2
STATE_GAME_OVER = 3

MAX_ENEMIES = 3
MAX_EGGS = 3


class Game099Joust(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_JOUSTING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.wave = 1
        self.knights_defeated = 0

        # Ostrich Knight
        self.px = 3.0
        self.py = 12.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_platform = True
        self.grabbed_by_lava = False
        self.lava_escape_flaps = 0

        self.eggs: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 99

    @property
    def name(self) -> str:
        return "鸵鸟骑士"

    @property
    def english_name(self) -> str:
        return "Joust"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "连点扑翼升空惯性滑翔、高度优势长枪角斗与收缴鸟蛋"

    def get_name(self) -> str:
        return "Joust (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.wave = 1
        self._reset_arena(hard_reset=True)

    def _reset_arena(self, hard_reset: bool = False) -> None:
        self.state = STATE_JOUSTING
        self.state_timer = 0.0
        self.knights_defeated = 0

        self.px = 3.0
        self.py = 12.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_platform = True
        self.grabbed_by_lava = False
        self.lava_escape_flaps = 0

        self.eggs = [
            {"x": 0.0, "y": 0.0, "hatch_timer": 0.0, "active": False}
            for _ in range(MAX_EGGS)
        ]

        self.enemies = []
        for i in range(MAX_ENEMIES):
            self.enemies.append({
                "x": 7.0 + float(i) * 3.0,
                "y": 7.0 if i == 0 else (3.0 if i == 1 else 11.0),
                "vx": 2.2 if i % 2 == 0 else -2.2,
                "vy": 0.0,
                "flap_timer": 0.5 + float(i) * 0.3,
                "rank": 1 if i == 2 else 0,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_KNIGHT_DOWN:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_arena(hard_reset=False)
            return

        if self.state == STATE_WAVE_CLEAR:
            if self.state_timer > 2.0:
                self.wave += 1
                self._reset_arena(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_enemies(dt)
        self._update_eggs(dt)
        self._check_joust_collisions()

        if self.knights_defeated >= 4:
            self.state = STATE_WAVE_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        accel = 8.0
        if buttons & KEY_LEFT:
            self.vx = max(-5.5, self.vx - accel * dt)
            self.facing = -1
        elif buttons & KEY_RIGHT:
            self.vx = min(5.5, self.vx + accel * dt)
            self.facing = 1
        else:
            self.vx *= max(0.0, 1.0 - 3.5 * dt)

        # Button A: Flap Wings!
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.grabbed_by_lava:
                self.lava_escape_flaps += 1
                if self.lava_escape_flaps >= 3:
                    self.grabbed_by_lava = False
                    self.vy = -6.5
                    self.py = 13.8
            else:
                self.vy = -5.8
                self.on_platform = False
                self.score += 5

        if not self.on_platform and not self.grabbed_by_lava:
            self.vy += 11.5 * dt
            self.py += self.vy * dt

        if not self.grabbed_by_lava:
            self.px += self.vx * dt

        # Wraparound
        if self.px < 0.0:
            self.px += 16.0
        elif self.px >= 16.0:
            self.px -= 16.0

        # Platforms (landing when descending)
        if self.vy >= 0.0 and not self.grabbed_by_lava:
            if 7.6 <= self.py <= 8.2 and 3.8 <= self.px <= 11.8:
                self.py = 8.0
                self.vy = 0.0
                self.on_platform = True
            elif 11.6 <= self.py <= 12.2 and (self.px <= 5.5 or self.px >= 15.0):
                self.py = 12.0
                self.vy = 0.0
                self.on_platform = True
            elif 11.6 <= self.py <= 12.2 and self.px >= 10.0:
                self.py = 12.0
                self.vy = 0.0
                self.on_platform = True
            elif 3.6 <= self.py <= 4.2 and 5.8 <= self.px <= 9.8:
                self.py = 4.0
                self.vy = 0.0
                self.on_platform = True

        # Lava pit
        if self.py >= 14.5 and 5.5 <= self.px <= 10.0:
            if not self.grabbed_by_lava:
                self.grabbed_by_lava = True
                self.lava_escape_flaps = 0
                self.vy = 0.0
            else:
                self.py += 2.0 * dt
                if self.py >= 15.5:
                    self.state = STATE_KNIGHT_DOWN
                    self.state_timer = 0.0

        if self.py < 1.0:
            self.py = 1.0
            self.vy = 0.5

    def _update_enemies(self, dt: float) -> None:
        for idx, e in enumerate(self.enemies):
            if not e["active"]:
                if e["respawn_timer"] > 0.0:
                    e["respawn_timer"] -= dt
                else:
                    e["active"] = True
                    e["x"] = 2.0 + (idx * 4.3) % 12.0
                    e["y"] = 4.0
                    e["vx"] = 2.5 if idx % 2 == 0 else -2.5
                    e["vy"] = 0.0
                    e["flap_timer"] = 0.5
                continue

            e["flap_timer"] -= dt
            if e["flap_timer"] <= 0.0:
                e["flap_timer"] = 0.6 + (idx * 0.1) % 0.4
                e["vy"] = -5.0

            e["vy"] += 11.0 * dt
            e["y"] += e["vy"] * dt
            e["x"] += e["vx"] * dt

            if e["x"] < 0.0:
                e["x"] += 16.0
            elif e["x"] >= 16.0:
                e["x"] -= 16.0

            if e["y"] < 2.0:
                e["y"] = 2.0
                e["vy"] = 1.0
            elif e["y"] > 13.5:
                e["y"] = 13.5
                e["vy"] = -4.5

    def _update_eggs(self, dt: float) -> None:
        for egg in self.eggs:
            if not egg["active"]:
                continue
            egg["hatch_timer"] -= dt
            if egg["hatch_timer"] <= 0.0:
                egg["active"] = False
                for e in self.enemies:
                    if not e["active"]:
                        e["active"] = True
                        e["x"] = egg["x"]
                        e["y"] = egg["y"] - 1.0
                        e["vx"] = 3.0
                        e["vy"] = -5.0
                        e["rank"] = 1
                        break

    def _check_joust_collisions(self) -> None:
        # Eggs
        for egg in self.eggs:
            if not egg["active"]:
                continue
            dx = abs(self.px - egg["x"])
            dy = abs(self.py - egg["y"])
            if dx < 1.2 and dy < 1.2:
                egg["active"] = False
                self.score += 250

        # Jousting
        for e in self.enemies:
            if not e["active"]:
                continue
            dx = abs(self.px - e["x"])
            dy = self.py - e["y"]

            if dx < 1.2 and abs(dy) < 1.2:
                if dy < -0.2:
                    # Hero is HIGHER in altitude! Wins!
                    e["active"] = False
                    e["respawn_timer"] = 3.0
                    self.score += 500
                    self.knights_defeated += 1

                    for egg in self.eggs:
                        if not egg["active"]:
                            egg["active"] = True
                            egg["x"] = e["x"]
                            egg["y"] = min(12.0, e["y"] + 1.0)
                            egg["hatch_timer"] = 5.0
                            break

                    self.vy = -4.0
                elif dy > 0.2:
                    # Enemy is HIGHER!
                    self.state = STATE_KNIGHT_DOWN
                    self.state_timer = 0.0
                    break
                else:
                    # Equal height: CLANG!
                    self.vx = -self.vx
                    e["vx"] = -e["vx"]
                    self.score += 20

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(len(fb)):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # Platforms
        for x in range(4, 12):
            set_pixel(x, 8, 120, 120, 130)
        for x in range(0, 6):
            set_pixel(x, 12, 120, 120, 130)
        for x in range(10, 16):
            set_pixel(x, 12, 120, 120, 130)
        for x in range(6, 10):
            set_pixel(x, 4, 120, 120, 130)

        # Lava
        for x in range(6, 10):
            set_pixel(x, 15, 255, 60, 20)

        if self.grabbed_by_lava:
            set_pixel(int(round(self.px)), 14, 255, 200, 0)

        # Eggs
        for egg in self.eggs:
            if not egg["active"]:
                continue
            ex = int(round(egg["x"]))
            ey = int(round(egg["y"]))
            set_pixel(ex, ey, 255, 230, 80)
            set_pixel(ex, ey - 1, 255, 255, 180)

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["rank"] == 0:
                set_pixel(ex, ey, 180, 50, 40)
                set_pixel(ex, ey - 1, 200, 80, 80)
                set_pixel(ex + (1 if e["vx"] > 0 else -1), ey - 1, 255, 255, 255)
            else:
                set_pixel(ex, ey, 100, 30, 160)
                set_pixel(ex, ey - 1, 140, 60, 220)
                set_pixel(ex + (1 if e["vx"] > 0 else -1), ey - 1, 255, 255, 255)

        # Hero
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_KNIGHT_DOWN:
            set_pixel(px, py, 255, 50, 50)
            set_pixel(px, py - 1, 255, 200, 0)
        else:
            set_pixel(px, py, 240, 200, 40)
            set_pixel(px, py - 1, 40, 120, 240)
            set_pixel(px, py - 2, 220, 220, 220)
            set_pixel(px + self.facing, py - 1, 255, 255, 255)
            set_pixel(px + self.facing * 2, py - 1, 255, 255, 255)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 200, 50)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "wave": self.wave,
            "vy": self.vy,
            "on_platform": self.on_platform,
            "grabbed_by_lava": self.grabbed_by_lava,
            "knights_defeated": self.knights_defeated,
            "player_x": self.px,
            "player_y": self.py,
        }
