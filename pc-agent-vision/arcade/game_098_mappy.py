"""
Game #098: 快乐小猫警 / 猫狗大厦 (Mappy 1983 / Namco)
Police mouse Mappy bouncing on trampolines across multi-story mansion, microwave sonic door cat blasts & recovering loot.
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

STATE_IN_MANSION = 0
STATE_MAPPY_HIT = 1
STATE_ROUND_CLEAR = 2
STATE_GAME_OVER = 3

MAX_LOOT = 6
MAX_CATS = 3
FLOORS = [3, 6, 9, 13]


class Game098Mappy(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_IN_MANSION
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.loot_collected = 0

        # Mappy
        self.px = 5.0
        self.py = 13.0
        self.vy = 0.0
        self.facing = 1
        self.is_on_trampoline = False
        self.active_tramp_idx = -1
        self.continuous_bounces = 0

        self.tramp_wear_left = 0
        self.tramp_wear_right = 0

        self.door_floor = 6
        self.door_x = 7
        self.door_opened = False

        self.wave_active = False
        self.wave_x = 0.0
        self.wave_floor_y = 6
        self.wave_vx = 0.0

        self.loot: List[Dict[str, Any]] = []
        self.cats: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 98

    @property
    def name(self) -> str:
        return "快乐小猫警"

    @property
    def english_name(self) -> str:
        return "Mappy"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "蹦床多段弹跳蹦高进层、微波声波门震飞猫盗与双数赃物连收"

    def get_name(self) -> str:
        return "Mappy (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._reset_mansion(hard_reset=True)

    def _reset_mansion(self, hard_reset: bool = False) -> None:
        self.state = STATE_IN_MANSION
        self.state_timer = 0.0
        self.loot_collected = 0

        self.px = 5.0
        self.py = 13.0
        self.vy = 0.0
        self.facing = 1
        self.is_on_trampoline = False
        self.active_tramp_idx = -1
        self.continuous_bounces = 0

        self.tramp_wear_left = 0
        self.tramp_wear_right = 0

        self.door_floor = 6
        self.door_x = 7
        self.door_opened = False
        self.wave_active = False

        # 6 Stolen Treasures Setup
        self.loot = [
            {"x": 4, "floor_y": 3, "type": 0, "collected": False},
            {"x": 10, "floor_y": 3, "type": 0, "collected": False},
            {"x": 5, "floor_y": 6, "type": 1, "collected": False},
            {"x": 11, "floor_y": 6, "type": 1, "collected": False},
            {"x": 4, "floor_y": 9, "type": 2, "collected": False},
            {"x": 10, "floor_y": 9, "type": 2, "collected": False},
        ]

        self.cats = []
        for i in range(MAX_CATS):
            self.cats.append({
                "x": 4.0 if i % 2 == 0 else 10.0,
                "floor_y": 3 if i == 0 else (6 if i == 1 else 9),
                "vx": 1.2 if i % 2 == 0 else -1.2,
                "is_blasted": False,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_MAPPY_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_mansion(hard_reset=False)
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 2.0:
                self.round += 1
                self._reset_mansion(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_microwave_wave(dt)
        self._update_cats(dt)
        self._check_loot_and_combat()

        if self.loot_collected >= MAX_LOOT:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.is_on_trampoline:
            self.vy += 13.5 * dt
            self.py += self.vy * dt

            # Base bounce
            if self.py >= 14.0:
                self.py = 14.0
                if self.active_tramp_idx == 0:
                    self.tramp_wear_left += 1
                    wear = self.tramp_wear_left
                else:
                    self.tramp_wear_right += 1
                    wear = self.tramp_wear_right

                if wear >= 4:
                    self.state = STATE_MAPPY_HIT
                    self.state_timer = 0.0
                    return

                self.vy = -8.8
                self.continuous_bounces += 1
                self.score += 10

            # Step off trampoline onto floor
            for fy in FLOORS:
                if abs(self.py - float(fy)) < 0.65:
                    if self.active_tramp_idx == 0 and (buttons & KEY_RIGHT):
                        self.is_on_trampoline = False
                        self.px = 3.2
                        self.py = float(fy)
                        self.vy = 0.0
                        self.tramp_wear_left = 0
                        break
                    elif self.active_tramp_idx == 1 and (buttons & KEY_LEFT):
                        self.is_on_trampoline = False
                        self.px = 11.8
                        self.py = float(fy)
                        self.vy = 0.0
                        self.tramp_wear_right = 0
                        break
        else:
            move_speed = 5.5
            if buttons & KEY_LEFT:
                self.px -= move_speed * dt
                self.facing = -1
            elif buttons & KEY_RIGHT:
                self.px += move_speed * dt
                self.facing = 1

            if self.px <= 2.2:
                self.px = 2.0
                self.is_on_trampoline = True
                self.active_tramp_idx = 0
                self.vy = 0.0
            elif self.px >= 12.8:
                self.px = 13.0
                self.is_on_trampoline = True
                self.active_tramp_idx = 1
                self.vy = 0.0

            # Button A: Microwave Door
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                if int(round(self.py)) == self.door_floor:
                    dx = abs(self.px - float(self.door_x))
                    if dx < 1.2 and not self.door_opened:
                        self.door_opened = True
                        self.wave_active = True
                        self.wave_floor_y = self.door_floor
                        self.wave_x = float(self.door_x)
                        self.wave_vx = float(self.facing) * 11.0
                        self.score += 50

    def _update_microwave_wave(self, dt: float) -> None:
        if not self.wave_active:
            return
        self.wave_x += self.wave_vx * dt
        if self.wave_x < 1.0 or self.wave_x > 15.0:
            self.wave_active = False

    def _update_cats(self, dt: float) -> None:
        for idx, c in enumerate(self.cats):
            if not c["active"]:
                if c["respawn_timer"] > 0.0:
                    c["respawn_timer"] -= dt
                else:
                    c["active"] = True
                    c["is_blasted"] = False
                    c["floor_y"] = FLOORS[idx % 3]
                    c["x"] = 7.0
                    c["vx"] = 1.2 if idx % 2 == 0 else -1.2
                continue

            if c["is_blasted"]:
                c["x"] += c["vx"] * dt
                if c["x"] < -2.0 or c["x"] > 18.0:
                    c["active"] = False
                    c["is_blasted"] = False
                    c["respawn_timer"] = 2.5
                continue

            c["x"] += c["vx"] * dt
            if c["x"] <= 3.0:
                c["x"] = 3.0
                c["vx"] = abs(c["vx"])
            elif c["x"] >= 12.0:
                c["x"] = 12.0
                c["vx"] = -abs(c["vx"])

    def _check_loot_and_combat(self) -> None:
        # Wave vs Cats
        if self.wave_active:
            for c in self.cats:
                if not c["active"] or c["is_blasted"]:
                    continue
                if c["floor_y"] == self.wave_floor_y:
                    if abs(c["x"] - self.wave_x) < 1.4:
                        c["is_blasted"] = True
                        c["vx"] = 14.0 if self.wave_vx > 0.0 else -14.0
                        self.score += 400

        # Mappy collects Loot
        if not self.is_on_trampoline:
            cur_y = int(round(self.py))
            for item in self.loot:
                if not item["collected"] and item["floor_y"] == cur_y:
                    if abs(self.px - float(item["x"])) < 0.9:
                        item["collected"] = True
                        self.loot_collected += 1
                        pts = 100 if item["type"] == 0 else (200 if item["type"] == 1 else 500)
                        self.score += pts

        # Cats vs Mappy (Invulnerable on trampolines!)
        if not self.is_on_trampoline:
            cur_y = int(round(self.py))
            for c in self.cats:
                if not c["active"] or c["is_blasted"]:
                    continue
                if c["floor_y"] == cur_y:
                    if abs(self.px - c["x"]) < 0.9:
                        self.state = STATE_MAPPY_HIT
                        self.state_timer = 0.0
                        break

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

        # Floors
        for fy in (4, 7, 10, 14):
            for x in range(3, 13):
                set_pixel(x, fy, 40, 150, 200)

        # Trampolines
        def draw_tramp(tx: int, wear: int):
            r, g, b = 50, 230, 50
            if wear == 1:
                r, g, b = 40, 120, 255
            elif wear == 2:
                r, g, b = 240, 220, 30
            elif wear >= 3:
                r, g, b = 255, 50, 50
            set_pixel(tx, 15, r, g, b)
            set_pixel(tx - 1, 15, 120, 120, 120)
            set_pixel(tx + 1, 15, 120, 120, 120)

        draw_tramp(2, self.tramp_wear_left)
        draw_tramp(13, self.tramp_wear_right)

        # Door
        if not self.door_opened:
            set_pixel(self.door_x, self.door_floor, 240, 50, 180)
            set_pixel(self.door_x, self.door_floor - 1, 240, 50, 180)
        else:
            set_pixel(self.door_x + 1, self.door_floor, 180, 180, 180)

        # Microwave wave
        if self.wave_active:
            wx = int(round(self.wave_x))
            wy = self.wave_floor_y
            set_pixel(wx, wy, 255, 255, 100)
            set_pixel(wx, wy - 1, 255, 200, 50)
            offset = 1 if self.wave_vx > 0 else -1
            set_pixel(wx + offset, wy, 255, 100, 255)

        # Loot
        for item in self.loot:
            if item["collected"]:
                continue
            if item["type"] == 0:
                set_pixel(item["x"], item["floor_y"], 255, 180, 30)
            elif item["type"] == 1:
                set_pixel(item["x"], item["floor_y"], 40, 220, 255)
                set_pixel(item["x"], item["floor_y"] - 1, 100, 100, 100)
            else:
                set_pixel(item["x"], item["floor_y"], 255, 215, 0)
                set_pixel(item["x"] + 1, item["floor_y"], 200, 160, 0)

        # Cats
        for idx, c in enumerate(self.cats):
            if not c["active"]:
                continue
            cx = int(round(c["x"]))
            cy = c["floor_y"]
            if c["is_blasted"]:
                set_pixel(cx, cy, 255, 200, 0)
                set_pixel(cx, cy - 1, 255, 50, 50)
            else:
                if idx == 0:
                    set_pixel(cx, cy, 220, 30, 30)
                    set_pixel(cx, cy - 1, 255, 60, 60)
                    set_pixel(cx - 1, cy - 1, 240, 200, 120)
                    set_pixel(cx + 1, cy - 1, 240, 200, 120)
                else:
                    set_pixel(cx, cy, 255, 120, 180)
                    set_pixel(cx, cy - 1, 255, 150, 200)

        # Mappy
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_MAPPY_HIT:
            set_pixel(px, py, 255, 50, 50)
            set_pixel(px, py - 1, 255, 220, 0)
        else:
            set_pixel(px, py, 30, 90, 220)
            set_pixel(px, py - 1, 240, 240, 240)
            set_pixel(px, py - 2, 40, 120, 240)
            set_pixel(px - 1, py - 2, 255, 180, 180)
            set_pixel(px + 1, py - 2, 255, 180, 180)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 50, 120, 255)

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
            "is_on_trampoline": self.is_on_trampoline,
            "tramp_wear_left": self.tramp_wear_left,
            "tramp_wear_right": self.tramp_wear_right,
            "loot_collected": self.loot_collected,
            "player_x": self.px,
            "player_y": self.py,
        }
