# -*- coding: utf-8 -*-
"""
Game #148: 拆迁队 (Wrecking Crew 1985 / Nintendo Vs. System)
街机历史上最具策略深度的无跳跃重锤拆迁动作解谜经典：
玩家化身拆迁工马力欧手持重型大锤敲碎砖墙与混凝土立柱、
敲击炸药桶引发整层连续爆破链式塌陷、穿梭多层脚手架梯子规避扳手怪与工头巡逻。
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
STATE_PLAYER_HIT = 2
STATE_GAME_OVER = 3

FLOOR_Y = [2, 6, 10, 14]


class Game148WreckingCrew(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 2.0
        self.py = 14.0
        self.facing = 1  # 1: right, -1: left
        self.hammer_timer = 0.0

        # Building components
        self.walls: List[Dict[str, Any]] = []      # {"x": int, "y": int, "hp": int, "type": "brick"|"pillar"}
        self.dynamite: List[Dict[str, Any]] = []   # {"x": int, "y": int, "active": bool}
        self.ladders: List[Dict[str, Any]] = []    # {"x": int, "y_top": int, "y_bot": int}
        self.enemies: List[Dict[str, Any]] = []    # {"x": float, "y": float, "floor_idx": int, "vx": float, "alive": bool}

        self.reset()

    @property
    def game_id(self) -> int:
        return 148

    @property
    def name(self) -> str:
        return "拆迁队"

    @property
    def english_name(self) -> str:
        return "Wrecking Crew"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "重型拆迁大锤敲碎砖墙与立柱、敲击炸药桶引发整行爆破链式塌陷、攀爬梯子规避巡逻扳手怪与工头斯派克"

    def get_name(self) -> str:
        return "Wrecking Crew (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 14.0
        self.facing = 1
        self.hammer_timer = 0.0

        # Define 3 ladders connecting the 4 floors
        self.ladders = [
            {"x": 4, "y_top": 10, "y_bot": 14},
            {"x": 11, "y_top": 6, "y_bot": 10},
            {"x": 6, "y_top": 2, "y_bot": 6},
        ]

        # Destructible walls and pillars
        self.walls = [
            # Floor 14 (bottom)
            {"x": 6, "y": 14, "hp": 1, "type": "brick"},
            {"x": 9, "y": 14, "hp": 2, "type": "pillar"},
            {"x": 12, "y": 14, "hp": 1, "type": "brick"},

            # Floor 10
            {"x": 2, "y": 10, "hp": 1, "type": "brick"},
            {"x": 7, "y": 10, "hp": 1, "type": "brick"},

            # Floor 6
            {"x": 3, "y": 6, "hp": 2, "type": "pillar"},
            {"x": 9, "y": 6, "hp": 1, "type": "brick"},
            {"x": 13, "y": 6, "hp": 1, "type": "brick"},

            # Floor 2 (top)
            {"x": 9, "y": 2, "hp": 1, "type": "brick"},
            {"x": 12, "y": 2, "hp": 2, "type": "pillar"},
        ]

        # Dynamite barrels
        self.dynamite = [
            {"x": 8, "y": 14, "active": True},
            {"x": 8, "y": 6, "active": True},
        ]

        # Enemies (Gotchawrench)
        self.enemies = [
            {"x": 13.0, "y": 14.0, "vx": -1.8, "alive": True},
            {"x": 2.0, "y": 6.0, "vx": 1.8, "alive": True},
        ]

    def _is_on_ladder(self, x: float, y: float) -> bool:
        for lad in self.ladders:
            if abs(x - lad["x"]) < 0.8 and (lad["y_top"] - 0.2 <= y <= lad["y_bot"] + 0.2):
                return True
        return False

    def _get_nearest_floor(self, y: float) -> int:
        closest = FLOOR_Y[0]
        min_d = abs(y - closest)
        for fy in FLOOR_Y:
            d = abs(y - fy)
            if d < min_d:
                min_d = d
                closest = fy
        return closest

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_PLAYER_HIT):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_PLAYER_HIT:
                    if self.lives > 0:
                        self.px = 2.0
                        self.py = 14.0
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
        if self.hammer_timer > 0.0:
            self.hammer_timer -= dt

        # 1. Climbing Ladders (Vertical)
        on_ladder = self._is_on_ladder(self.px, self.py)
        is_climbing = False

        if on_ladder:
            climb_speed = 3.5
            if buttons & KEY_UP:
                self.py = max(2.0, self.py - climb_speed * dt)
                is_climbing = True
            elif buttons & KEY_DOWN:
                self.py = min(14.0, self.py + climb_speed * dt)
                is_climbing = True

        # 2. Horizontal walking along nearest floor
        if not is_climbing:
            nearest_floor = self._get_nearest_floor(self.py)
            # Snap to floor if close
            if abs(self.py - nearest_floor) < 0.6:
                self.py = float(nearest_floor)

            walk_speed = 4.2
            dx = 0.0
            if buttons & KEY_LEFT:
                dx -= walk_speed
                self.facing = -1
            elif buttons & KEY_RIGHT:
                dx += walk_speed
                self.facing = 1

            self.px = max(1.0, min(14.0, self.px + dx * dt))

        # 3. Hammer Strike: Key A or Key B
        if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
            self.hammer_timer = 0.25
            self._strike_hammer()

        # 4. Check stage clear (all walls destroyed)
        if len(self.walls) == 0:
            self.score += 2000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            return

        # 5. Update Enemies
        for e in self.enemies:
            if not e["alive"]:
                continue

            e["x"] += e["vx"] * dt
            if e["x"] <= 1.5:
                e["x"] = 1.5
                e["vx"] = abs(e["vx"])
            elif e["x"] >= 13.5:
                e["x"] = 13.5
                e["vx"] = -abs(e["vx"])

            # Enemy touches player
            if abs(self.px - e["x"]) < 0.8 and abs(self.py - e["y"]) < 0.8:
                self._lose_life()
                return

    def _strike_hammer(self) -> None:
        target_x = int(round(self.px + self.facing * 0.8))
        target_y = int(round(self.py))

        # 1. Check if striking dynamite barrel
        for dyn in self.dynamite:
            if dyn["active"] and dyn["x"] == target_x and dyn["y"] == target_y:
                dyn["active"] = False
                self.score += 500
                self._detonate_dynamite(target_y)
                return

        # 2. Check if striking walls
        for w in self.walls:
            if w["x"] == target_x and w["y"] == target_y:
                w["hp"] -= 1
                if w["hp"] <= 0:
                    self.score += 100 if w["type"] == "brick" else 250
                break

        self.walls = [w for w in self.walls if w["hp"] > 0]

    def _detonate_dynamite(self, floor_y: int) -> None:
        """Detonates entire horizontal row of walls and stuns enemies on that floor"""
        self.walls = [w for w in self.walls if w["y"] != floor_y]
        for e in self.enemies:
            if int(round(e["y"])) == floor_y:
                e["alive"] = False
                self.score += 300

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_PLAYER_HIT
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

        # 1. Scaffolding Floors (Grey girders)
        for fy in FLOOR_Y:
            for x in range(16):
                set_pixel(x, fy + 1 if fy + 1 < 16 else 15, 70, 70, 80)

        # 2. Ladders (Yellow-White rungs)
        for lad in self.ladders:
            lx = lad["x"]
            for ly in range(lad["y_top"], lad["y_bot"] + 1):
                set_pixel(lx, ly, 180, 160, 40)

        # 3. Dynamite barrels (Red explosive barrels)
        for dyn in self.dynamite:
            if dyn["active"]:
                set_pixel(dyn["x"], dyn["y"], 255, 30, 30)

        # 4. Destructible walls
        for w in self.walls:
            if w["type"] == "brick":
                set_pixel(w["x"], w["y"], 200, 100, 40)  # Orange brick
            else:
                set_pixel(w["x"], w["y"], 130, 130, 150) # Grey pillar

        # 5. Enemies (Gotchawrench: Violet walking wrench)
        for e in self.enemies:
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                set_pixel(ex, ey, 180, 40, 200)

        # 6. Player (Mario Demolitionist: Red shirt, blue overalls, hammer)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 40, 90, 255)       # Overalls
            set_pixel(px, py - 1, 255, 40, 40)   # Cap & shirt
            if self.hammer_timer > 0.0:
                # Sledgehammer visual extension
                hx = px + self.facing
                set_pixel(hx, py, 220, 180, 50)
        elif self.state == STATE_PLAYER_HIT:
            set_pixel(px, py, 255, 60, 30)

        # 7. Lives display in top row
        for l in range(min(self.lives, 3)):
            set_pixel(1 + l * 2, 0, 255, 40, 40)

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
            "py": self.py,
            "facing": self.facing,
            "walls_count": len(self.walls),
            "dynamite_count": sum(1 for d in self.dynamite if d["active"]),
        }
