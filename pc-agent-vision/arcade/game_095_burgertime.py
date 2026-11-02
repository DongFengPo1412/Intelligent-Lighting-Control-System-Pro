"""
Game #095: 汉堡时代 (BurgerTime 1982 / Data East)
Chef Peter Pepper trampling burger layers dropping down onto plates, squishing hotdogs & pepper shaker sneeze-stuns.
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

STATE_COOKING = 0
STATE_CHEF_HIT = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3

ING_BUN_TOP = 0
ING_LETTUCE = 1
ING_PATTY = 2
ING_BUN_BOTTOM = 3

MAX_LAYERS = 6
MAX_ENEMIES = 3


class Game095BurgerTime(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_COOKING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.peppers_left = 5
        self.burgers_completed = 0

        # Chef Peter Pepper
        self.px = 4.0
        self.py = 13.0
        self.facing = 1
        self.pepper_spray_timer = 0.0

        self.layers: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 95

    @property
    def name(self) -> str:
        return "汉堡时代"

    @property
    def english_name(self) -> str:
        return "BurgerTime"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "踩踏巨型汉堡分层下落拼接压怪与胡椒粉喷射眩晕"

    def get_name(self) -> str:
        return "BurgerTime (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.peppers_left = 5
        self._reset_kitchen(hard_reset=True)

    def _reset_kitchen(self, hard_reset: bool = False) -> None:
        self.state = STATE_COOKING
        self.state_timer = 0.0
        self.burgers_completed = 0

        self.px = 4.0
        self.py = 13.0
        self.facing = 1
        self.pepper_spray_timer = 0.0

        # 2 Burgers: Left (col 0: x=2..5), Right (col 1: x=10..13)
        self.layers = [
            {"col": 0, "type": ING_BUN_TOP, "y": 3.0, "target_y": 3.0, "is_falling": False, "on_plate": False, "stepped_mask": 0},
            {"col": 0, "type": ING_PATTY, "y": 6.0, "target_y": 6.0, "is_falling": False, "on_plate": False, "stepped_mask": 0},
            {"col": 0, "type": ING_BUN_BOTTOM, "y": 9.0, "target_y": 9.0, "is_falling": False, "on_plate": False, "stepped_mask": 0},
            {"col": 1, "type": ING_BUN_TOP, "y": 3.0, "target_y": 3.0, "is_falling": False, "on_plate": False, "stepped_mask": 0},
            {"col": 1, "type": ING_PATTY, "y": 6.0, "target_y": 6.0, "is_falling": False, "on_plate": False, "stepped_mask": 0},
            {"col": 1, "type": ING_BUN_BOTTOM, "y": 9.0, "target_y": 9.0, "is_falling": False, "on_plate": False, "stepped_mask": 0},
        ]

        self.enemies = []
        for i in range(MAX_ENEMIES):
            self.enemies.append({
                "x": 1.0 if i == 0 else (14.0 if i == 1 else 8.0),
                "y": 6.0 if i == 2 else 3.0,
                "vx": 1.4 if i % 2 == 0 else -1.4,
                "stun_timer": 0.0,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_CHEF_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_kitchen(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.stage += 1
                self.peppers_left = min(5, self.peppers_left + 2)
                self._reset_kitchen(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_burger_layers(dt)
        self._update_enemies(dt)
        self._check_collisions()

        if all(l["on_plate"] for l in self.layers):
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1000
            self.burgers_completed = 2

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.pepper_spray_timer > 0.0:
            self.pepper_spray_timer -= dt

        # Pepper Shaker (Button A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.peppers_left > 0 and self.pepper_spray_timer <= 0.0:
                self.peppers_left -= 1
                self.pepper_spray_timer = 0.45
                self.score += 10
                spray_x = self.px + self.facing * 1.5
                for e in self.enemies:
                    if e["active"]:
                        dx = abs(e["x"] - spray_x)
                        dy = abs(e["y"] - self.py)
                        if dx < 1.6 and dy < 1.2:
                            e["stun_timer"] = 4.0

        move_speed = 5.0
        cur_floor_y = -1
        for fy in (3, 6, 9, 13):
            if abs(self.py - float(fy)) < 0.35:
                cur_floor_y = fy
                break

        on_ladder = False
        for lx in (1, 4, 8, 11, 14):
            if abs(self.px - float(lx)) < 0.45:
                on_ladder = True
                break

        if buttons & KEY_LEFT:
            if cur_floor_y != -1:
                self.px -= move_speed * dt
                self.facing = -1
                self.py = float(cur_floor_y)
        elif buttons & KEY_RIGHT:
            if cur_floor_y != -1:
                self.px += move_speed * dt
                self.facing = 1
                self.py = float(cur_floor_y)

        if buttons & KEY_UP:
            if on_ladder:
                self.py -= move_speed * dt
        elif buttons & KEY_DOWN:
            if on_ladder:
                self.py += move_speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(3.0, min(13.0, self.py))

        # Trample Layers
        for layer in self.layers:
            if layer["is_falling"] or layer["on_plate"]:
                continue
            if abs(self.py - layer["y"]) < 0.4:
                start_x = 2 if layer["col"] == 0 else 10
                if start_x <= self.px <= start_x + 3:
                    seg = int(self.px - float(start_x))
                    if 0 <= seg < 4:
                        layer["stepped_mask"] |= (1 << seg)

                    if layer["stepped_mask"] == 0x0F:
                        layer["is_falling"] = True
                        layer["target_y"] = min(13.0, layer["y"] + 3.0)
                        layer["stepped_mask"] = 0
                        self.score += 50

    def _update_burger_layers(self, dt: float) -> None:
        for idx, layer in enumerate(self.layers):
            if not layer["is_falling"]:
                continue
            layer["y"] += 8.0 * dt

            start_x = 2 if layer["col"] == 0 else 10
            for e in self.enemies:
                if e["active"] and start_x <= e["x"] <= start_x + 3:
                    if abs(e["y"] - layer["y"]) < 0.8:
                        e["active"] = False
                        e["respawn_timer"] = 2.5
                        self.score += 500

            if layer["y"] >= layer["target_y"]:
                layer["y"] = layer["target_y"]
                layer["is_falling"] = False
                if layer["y"] >= 13.0:
                    layer["on_plate"] = True

                for k, other in enumerate(self.layers):
                    if k != idx and other["col"] == layer["col"] and not other["is_falling"]:
                        if abs(other["y"] - layer["y"]) < 0.5:
                            other["is_falling"] = True
                            other["target_y"] = min(13.0, other["y"] + 3.0)
                            self.score += 50

    def _update_enemies(self, dt: float) -> None:
        for e in self.enemies:
            if not e["active"]:
                if e["respawn_timer"] > 0.0:
                    e["respawn_timer"] -= dt
                else:
                    e["active"] = True
                    e["stun_timer"] = 0.0
                    e["x"] = 1.0
                    e["y"] = 3.0
                    e["vx"] = 1.4
                continue

            if e["stun_timer"] > 0.0:
                e["stun_timer"] -= dt
                continue

            e["x"] += e["vx"] * dt
            if e["x"] <= 1.0:
                e["x"] = 1.0
                e["vx"] = abs(e["vx"])
            elif e["x"] >= 14.0:
                e["x"] = 14.0
                e["vx"] = -abs(e["vx"])

    def _check_collisions(self) -> None:
        for e in self.enemies:
            if not e["active"] or e["stun_timer"] > 0.0:
                continue
            dx = abs(self.px - e["x"])
            dy = abs(self.py - e["y"])
            if dx < 0.9 and dy < 0.8:
                self.state = STATE_CHEF_HIT
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
        for fy in (3, 6, 9, 13):
            for x in range(1, 15):
                set_pixel(x, fy, 40, 60, 140)

        # Ladders
        for lx in (1, 4, 8, 11, 14):
            for y in range(3, 14):
                if y % 2 == 0:
                    set_pixel(lx, y, 220, 220, 40)

        # Plates
        for x in range(2, 6):
            set_pixel(x, 14, 230, 230, 230)
        for x in range(10, 14):
            set_pixel(x, 14, 230, 230, 230)

        # Layers
        for layer in self.layers:
            ly = int(round(layer["y"]))
            start_x = 2 if layer["col"] == 0 else 10
            r, g, b = 200, 120, 40
            if layer["type"] == ING_PATTY:
                r, g, b = 130, 60, 30
            elif layer["type"] == ING_BUN_BOTTOM:
                r, g, b = 210, 135, 50

            for seg in range(4):
                bx = start_x + seg
                stepped = (layer["stepped_mask"] & (1 << seg)) != 0
                seg_y = ly + 1 if stepped else ly
                set_pixel(bx, seg_y, r, g, b)

        # Pepper cloud
        if self.pepper_spray_timer > 0.0:
            sx = int(round(self.px + self.facing * 1.5))
            sy = int(round(self.py))
            set_pixel(sx, sy, 255, 255, 255)
            set_pixel(sx, sy - 1, 255, 240, 180)
            set_pixel(sx + self.facing, sy, 240, 240, 220)

        # Enemies
        for idx, e in enumerate(self.enemies):
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["stun_timer"] > 0.0:
                set_pixel(ex, ey, 40, 160, 255)
                set_pixel(ex, ey - 1, 255, 255, 0)
            else:
                if idx == 0:
                    set_pixel(ex, ey, 220, 50, 40)
                    set_pixel(ex, ey - 1, 240, 200, 20)
                else:
                    set_pixel(ex, ey, 40, 180, 50)
                    set_pixel(ex, ey - 1, 80, 220, 70)

        # Chef
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_CHEF_HIT:
            set_pixel(px, py, 255, 50, 50)
            set_pixel(px, py - 1, 255, 220, 0)
        else:
            set_pixel(px, py, 40, 60, 180)
            set_pixel(px, py - 1, 255, 255, 255)
            set_pixel(px, py - 2, 255, 255, 255)
            set_pixel(px + self.facing, py - 1, 255, 50, 50)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 80, 80)
        for p in range(min(self.peppers_left, 5)):
            set_pixel(15 - p, 0, 255, 255, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "stage": self.stage,
            "peppers_left": self.peppers_left,
            "burgers_completed": self.burgers_completed,
            "player_x": self.px,
            "player_y": self.py,
        }
