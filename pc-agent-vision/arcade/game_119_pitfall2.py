"""
Game #119: 黄金城之谜 (Pitfall II: Lost Caverns 1984 / Sega Arcade & Activision)
Non-linear subterranean cavern platforming, swinging vines over crocodile lakes,
vertical floating hot-air balloons, ancient golden relics, and checkpoint cross resurrection.
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

STATE_EXPLORING = 0
STATE_CHECKPOINT_RESPAWN = 1
STATE_EXPEDITION_CLEAR = 2
STATE_GAME_OVER = 3

NUM_TREASURES = 3
NUM_HAZARDS = 3


class Game119Pitfall2(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_EXPLORING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.treasures_collected = 0

        self.px = 2.0
        self.py = 3.0
        self.vy = 0.0
        self.on_ground = True
        self.on_ladder = False
        self.on_vine = False
        self.on_balloon = False

        self.checkpoint_x = 2.0
        self.checkpoint_y = 3.0
        self.checkpoint_active = False

        self.balloon_x = 10.5
        self.balloon_y = 13.0
        self.balloon_dir = -1.0
        self.vine_angle = 0.0
        self.vine_pivot_x = 8.0
        self.vine_pivot_y = 1.0

        self.treasures: List[Dict[str, Any]] = []
        self.hazards: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 119

    @property
    def name(self) -> str:
        return "黄金城之谜"

    @property
    def english_name(self) -> str:
        return "Pitfall II: Lost Caverns"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "非线性地下溶洞探险、漂浮气球升降、鳄鱼潭荡藤与检查点十字架复活"

    def get_name(self) -> str:
        return "Pitfall II: Lost Caverns (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self._init_cavern()

    def _init_cavern(self) -> None:
        self.state = STATE_EXPLORING
        self.state_timer = 0.0
        self.treasures_collected = 0

        self.px = 2.0
        self.py = 3.0
        self.vy = 0.0
        self.on_ground = True
        self.on_ladder = False
        self.on_vine = False
        self.on_balloon = False

        self.checkpoint_x = 2.0
        self.checkpoint_y = 3.0
        self.checkpoint_active = False

        self.balloon_x = 10.5
        self.balloon_y = 13.0
        self.balloon_dir = -1.0
        self.vine_angle = 0.0

        self.treasures = [
            {"x": 13.0, "y": 3.0, "value": 200, "collected": False},
            {"x": 1.5, "y": 7.0, "value": 300, "collected": False},
            {"x": 14.0, "y": 12.0, "value": 500, "collected": False},
        ]
        self.hazards = [
            {"x": 7.5, "y": 4.0, "vx": 0.0, "type": 2, "active": True},
            {"x": 7.0, "y": 7.0, "vx": 1.8, "type": 0, "active": True},
            {"x": 10.0, "y": 10.5, "vx": -2.5, "type": 1, "active": True},
        ]

    def set_player_pos(self, x: float, y: float) -> None:
        self.px = x
        self.py = y

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

        if self.state == STATE_EXPEDITION_CLEAR:
            if self.state_timer > 1.8:
                self._init_cavern()
            return

        if self.state == STATE_CHECKPOINT_RESPAWN:
            if self.state_timer > 0.8:
                self.state = STATE_EXPLORING
                self.px = self.checkpoint_x
                self.py = self.checkpoint_y
                self.vy = 0.0
                self.on_vine = False
                self.on_balloon = False
            return

        self._update_mechanisms(dt)
        self._update_hazards(dt)
        self._update_player(dt, buttons, prev_buttons)
        self._check_interactions()

    def _update_mechanisms(self, dt: float) -> None:
        self.vine_angle = math.sin(self.state_timer * 2.6) * 0.65

        self.balloon_y += self.balloon_dir * 2.2 * dt
        if self.balloon_y <= 5.0:
            self.balloon_y = 5.0
            self.balloon_dir = 1.0
        elif self.balloon_y >= 13.0:
            self.balloon_y = 13.0
            self.balloon_dir = -1.0

    def _update_hazards(self, dt: float) -> None:
        # Scorpion
        self.hazards[1]["x"] += self.hazards[1]["vx"] * dt
        if self.hazards[1]["x"] <= 4.0:
            self.hazards[1]["x"] = 4.0
            self.hazards[1]["vx"] = abs(self.hazards[1]["vx"])
        elif self.hazards[1]["x"] >= 11.5:
            self.hazards[1]["x"] = 11.5
            self.hazards[1]["vx"] = -abs(self.hazards[1]["vx"])

        # Bat
        self.hazards[2]["x"] += self.hazards[2]["vx"] * dt
        self.hazards[2]["y"] = 10.5 + math.sin(self.state_timer * 4.0) * 0.8
        if self.hazards[2]["x"] <= 1.0:
            self.hazards[2]["x"] = 1.0
            self.hazards[2]["vx"] = abs(self.hazards[2]["vx"])
        elif self.hazards[2]["x"] >= 14.5:
            self.hazards[2]["x"] = 14.5
            self.hazards[2]["vx"] = -abs(self.hazards[2]["vx"])

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        move_spd = 4.2

        if self.on_balloon:
            self.px = self.balloon_x
            self.py = self.balloon_y + 0.6
            if (buttons & (KEY_DOWN | KEY_B)) and not (prev_buttons & (KEY_DOWN | KEY_B)):
                self.on_balloon = False
            return

        if self.on_vine:
            vine_len = 2.8
            self.px = self.vine_pivot_x + math.sin(self.vine_angle) * vine_len
            self.py = self.vine_pivot_y + math.cos(self.vine_angle) * vine_len
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.on_vine = False
                self.vy = -2.5
            return

        near_ladder_0 = (abs(self.px - 13.0) < 0.7 and 2.5 <= self.py <= 8.5)
        near_ladder_1 = (abs(self.px - 3.5) < 0.7 and 7.5 <= self.py <= 13.5)

        if near_ladder_0 or near_ladder_1:
            if buttons & KEY_UP:
                self.on_ladder = True
                self.py -= move_spd * dt
            elif buttons & KEY_DOWN:
                self.on_ladder = True
                self.py += move_spd * dt
            elif self.on_ladder:
                self.vy = 0.0
        else:
            self.on_ladder = False

        if not self.on_ladder:
            if buttons & KEY_LEFT:
                self.px -= move_spd * dt
            if buttons & KEY_RIGHT:
                self.px += move_spd * dt

            if (buttons & KEY_A) and not (prev_buttons & KEY_A) and self.on_ground:
                self.vy = -4.5
                self.on_ground = False

            self.vy += 14.0 * dt
            self.py += self.vy * dt

            if 3.0 <= self.py <= 3.6 and self.vy >= 0.0 and not (6.0 <= self.px <= 9.0):
                self.py = 3.0
                self.vy = 0.0
                self.on_ground = True
            elif 7.0 <= self.py <= 7.6 and self.vy >= 0.0 and not (12.0 <= self.px <= 14.0):
                self.py = 7.0
                self.vy = 0.0
                self.on_ground = True
            elif self.py >= 12.0 and self.vy >= 0.0:
                self.py = 12.0
                self.vy = 0.0
                self.on_ground = True
            else:
                self.on_ground = False

        self.px = max(1.0, min(15.0, self.px))

        # Catch vine
        if not self.on_vine and self.py <= 4.0 and 5.5 <= self.px <= 9.5:
            vx = self.vine_pivot_x + math.sin(self.vine_angle) * 2.8
            vy_coord = self.vine_pivot_y + math.cos(self.vine_angle) * 2.8
            if abs(self.px - vx) < 1.0 and abs(self.py - vy_coord) < 1.0:
                self.on_vine = True
                self.on_ground = False

        # Catch balloon
        if not self.on_balloon and abs(self.px - self.balloon_x) < 1.0 and abs(self.py - self.balloon_y) < 1.0:
            if buttons & KEY_UP:
                self.on_balloon = True
                self.on_ground = False

    def _check_interactions(self) -> None:
        for t in self.treasures:
            if not t["collected"]:
                dx = abs(self.px - t["x"])
                dy = abs(self.py - t["y"])
                if dx < 0.9 and dy < 0.9:
                    t["collected"] = True
                    self.score += t["value"]
                    self.treasures_collected += 1
                    if self.treasures_collected >= NUM_TREASURES:
                        self.state = STATE_EXPEDITION_CLEAR
                        self.state_timer = 0.0
                        self.score += 1000

        # Checkpoint Cross at (5.0, 12.0)
        if abs(self.px - 5.0) < 0.9 and abs(self.py - 12.0) < 0.9 and not self.checkpoint_active:
            self.checkpoint_active = True
            self.checkpoint_x = 5.0
            self.checkpoint_y = 12.0
            self.score += 100

        # Hazards
        for h in self.hazards:
            if not h["active"]:
                continue
            if h["type"] == 2 and self.on_vine:
                continue  # Vine safely clears the crocodile pit!
            dx = abs(self.px - h["x"])
            dy = abs(self.py - h["y"])
            if dx < 0.8 and dy < 0.8:
                self.state = STATE_CHECKPOINT_RESPAWN
                self.state_timer = 0.0
                self.score = max(0, self.score - 100)
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                break

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Floors
        for x in range(16):
            if 6 <= x <= 9:
                set_pixel(x, 4, 30, 80, 220)
            else:
                set_pixel(x, 4, 40, 140, 50)

        for x in range(16):
            if x < 12 or x > 14:
                set_pixel(x, 8, 140, 90, 40)

        for x in range(16):
            set_pixel(x, 13, 90, 60, 40)
            set_pixel(x, 14, 50, 30, 20)
            set_pixel(x, 15, 30, 20, 10)

        for y in range(4, 9):
            set_pixel(13, y, 220, 180, 60)
        for y in range(8, 14):
            set_pixel(3, y, 220, 180, 60)

        # 2. Vine
        vx = self.vine_pivot_x + math.sin(self.vine_angle) * 2.8
        vy = self.vine_pivot_y + math.cos(self.vine_angle) * 2.8
        set_pixel(int(round(self.vine_pivot_x)), int(round(self.vine_pivot_y)), 80, 180, 60)
        set_pixel(int(round(vx)), int(round(vy)), 60, 220, 40)

        # 3. Balloon
        bx = int(round(self.balloon_x))
        by = int(round(self.balloon_y))
        set_pixel(bx, by - 1, 255, 60, 40)
        set_pixel(bx - 1, by - 1, 255, 200, 30)
        set_pixel(bx + 1, by - 1, 255, 200, 30)
        set_pixel(bx, by, 180, 120, 60)

        # 4. Treasures
        for i, t in enumerate(self.treasures):
            if t["collected"]:
                continue
            tx = int(round(t["x"]))
            ty = int(round(t["y"]))
            if i == 0:
                set_pixel(tx, ty, 255, 220, 0)
            elif i == 1:
                set_pixel(tx, ty, 220, 220, 255)
            else:
                set_pixel(tx, ty, 255, 140, 20)

        # 5. Checkpoint Cross
        if self.checkpoint_active:
            set_pixel(5, 12, 255, 240, 80)
            set_pixel(5, 11, 255, 240, 80)
        else:
            set_pixel(5, 12, 255, 40, 30)
            set_pixel(5, 11, 255, 40, 30)

        # 6. Hazards
        set_pixel(7, 4, 30, 160, 40)
        set_pixel(8, 4, 30, 160, 40)
        sx = int(round(self.hazards[1]["x"]))
        set_pixel(sx, 7, 255, 80, 0)
        btx = int(round(self.hazards[2]["x"]))
        bty = int(round(self.hazards[2]["y"]))
        set_pixel(btx, bty, 200, 60, 255)

        # 7. Harry
        px = int(round(self.px))
        py_int = int(round(self.py))
        if self.state == STATE_CHECKPOINT_RESPAWN:
            set_pixel(px, py_int, 255, 255, 255)
            set_pixel(px, py_int - 1, 255, 220, 80)
        else:
            set_pixel(px, py_int, 40, 120, 240)
            set_pixel(px, py_int - 1, 255, 200, 140)
            set_pixel(px, py_int - 2, 180, 140, 60)

        # 8. Lives HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 40, 220, 80)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "px": self.px,
            "py": self.py,
            "on_vine": self.on_vine,
            "on_balloon": self.on_balloon,
            "treasures_collected": self.treasures_collected,
            "checkpoint_active": self.checkpoint_active,
        }
