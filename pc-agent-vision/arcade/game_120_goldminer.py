"""
Game #120: 黄金矿工 (Gold Miner 2003 / Dan Russell-Pinson)
Harmonic pendulum mechanical winch angle aiming, mass-dependent reel retraction,
dynamite detachment of unwanted rocks, and subterranean depth target quotas.
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

STATE_MINING = 0
STATE_ROUND_CLEAR = 1
STATE_TIME_UP = 2
STATE_GAME_OVER = 3

CLAW_SWINGING = 0
CLAW_EXTENDING = 1
CLAW_RETRACTING = 2

ITEM_SMALL_GOLD = 0
ITEM_LARGE_GOLD = 1
ITEM_DIAMOND = 2
ITEM_ROCK = 3
ITEM_TNT_BARREL = 4

MAX_ITEMS = 8


class Game120GoldMiner(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_MINING
        self.state_timer = 0.0
        self.score = 0
        self.round = 1
        self.target_quota = 600
        self.dynamite_count = 2
        self.time_remaining = 45.0

        self.winch_x = 7.5
        self.winch_y = 1.5
        self.winch_angle = 0.0
        self.swing_time = 0.0
        self.claw_state = CLAW_SWINGING

        self.claw_dist = 1.2
        self.claw_dir_x = 0.0
        self.claw_dir_y = 1.0
        self.claw_x = 7.5
        self.claw_y = 2.7
        self.hooked_item_idx = -1

        self.items: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 120

    @property
    def name(self) -> str:
        return "黄金矿工"

    @property
    def english_name(self) -> str:
        return "Gold Miner"

    @property
    def release_year(self) -> int:
        return 2003

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "180度简谐摆动绞盘瞄准、质量阻力卷收、炸药定点爆破与矿层目标配额"

    def get_name(self) -> str:
        return "Gold Miner (2003)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.round = 1
        self.target_quota = 600
        self.dynamite_count = 2
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_MINING
        self.state_timer = 0.0
        self.time_remaining = 45.0

        self.winch_x = 7.5
        self.winch_y = 1.5
        self.winch_angle = 0.0
        self.swing_time = 0.0
        self.claw_state = CLAW_SWINGING

        self.claw_dist = 1.2
        self.claw_dir_x = 0.0
        self.claw_dir_y = 1.0
        self.claw_x = self.winch_x
        self.claw_y = self.winch_y + self.claw_dist
        self.hooked_item_idx = -1

        self._spawn_items()

    def _spawn_items(self) -> None:
        self.items = [
            {"x": 3.0, "y": 5.0, "type": ITEM_SMALL_GOLD, "value": 100, "mass": 1.0, "radius": 0.7, "active": True},
            {"x": 12.0, "y": 6.0, "type": ITEM_SMALL_GOLD, "value": 100, "mass": 1.0, "radius": 0.7, "active": True},
            {"x": 7.5, "y": 9.0, "type": ITEM_LARGE_GOLD, "value": 500, "mass": 3.8, "radius": 1.2, "active": True},
            {"x": 2.5, "y": 11.0, "type": ITEM_DIAMOND, "value": 600, "mass": 0.4, "radius": 0.6, "active": True},
            {"x": 13.0, "y": 12.0, "type": ITEM_DIAMOND, "value": 600, "mass": 0.4, "radius": 0.6, "active": True},
            {"x": 5.0, "y": 7.5, "type": ITEM_ROCK, "value": 20, "mass": 5.0, "radius": 0.9, "active": True},
            {"x": 10.5, "y": 8.0, "type": ITEM_ROCK, "value": 20, "mass": 5.0, "radius": 0.9, "active": True},
            {"x": 8.0, "y": 13.0, "type": ITEM_TNT_BARREL, "value": 0, "mass": 1.0, "radius": 0.8, "active": True},
        ]

    def launch_claw(self) -> None:
        if self.claw_state != CLAW_SWINGING or self.state != STATE_MINING:
            return
        self.claw_state = CLAW_EXTENDING
        self.claw_dist = 1.2
        self.claw_dir_x = math.sin(self.winch_angle)
        self.claw_dir_y = math.cos(self.winch_angle)
        self.hooked_item_idx = -1

    def use_dynamite(self) -> None:
        if self.dynamite_count <= 0 or self.claw_state != CLAW_RETRACTING or self.hooked_item_idx < 0:
            return
        self.dynamite_count -= 1
        self.items[self.hooked_item_idx]["active"] = False
        self.hooked_item_idx = -1

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

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 1.8:
                self.round += 1
                self.target_quota += 700
                if self.dynamite_count < 3:
                    self.dynamite_count += 1
                self._init_level()
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            if self.score >= self.target_quota:
                self.state = STATE_ROUND_CLEAR
                self.state_timer = 0.0
            else:
                self.state = STATE_GAME_OVER
                self.state_timer = 0.0
            return

        self._update_winch(dt, buttons, prev_buttons)

    def _update_winch(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.claw_state == CLAW_SWINGING:
            self.swing_time += dt
            self.winch_angle = math.sin(self.swing_time * 2.2) * 1.22

            self.claw_dir_x = math.sin(self.winch_angle)
            self.claw_dir_y = math.cos(self.winch_angle)
            self.claw_dist = 1.2
            self.claw_x = self.winch_x + self.claw_dir_x * self.claw_dist
            self.claw_y = self.winch_y + self.claw_dir_y * self.claw_dist

            if (buttons & (KEY_A | KEY_DOWN)) and not (prev_buttons & (KEY_A | KEY_DOWN)):
                self.launch_claw()

        elif self.claw_state == CLAW_EXTENDING:
            extend_speed = 13.0
            self.claw_dist += extend_speed * dt
            self.claw_x = self.winch_x + self.claw_dir_x * self.claw_dist
            self.claw_y = self.winch_y + self.claw_dir_y * self.claw_dist

            if self.claw_x <= 0.8 or self.claw_x >= 14.8 or self.claw_y >= 15.0:
                self.claw_state = CLAW_RETRACTING
            else:
                self._check_claw_collisions()

        elif self.claw_state == CLAW_RETRACTING:
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.use_dynamite()

            retract_speed = 12.0
            if self.hooked_item_idx >= 0:
                mass = self.items[self.hooked_item_idx]["mass"]
                retract_speed = 12.0 / (1.0 + mass * 0.8)
                self.items[self.hooked_item_idx]["x"] = self.claw_x
                self.items[self.hooked_item_idx]["y"] = self.claw_y

            self.claw_dist -= retract_speed * dt
            self.claw_x = self.winch_x + self.claw_dir_x * self.claw_dist
            self.claw_y = self.winch_y + self.claw_dir_y * self.claw_dist

            if self.claw_dist <= 1.2:
                self.claw_dist = 1.2
                self.claw_x = self.winch_x + self.claw_dir_x * self.claw_dist
                self.claw_y = self.winch_y + self.claw_dir_y * self.claw_dist

                if self.hooked_item_idx >= 0:
                    self.score += self.items[self.hooked_item_idx]["value"]
                    self.items[self.hooked_item_idx]["active"] = False
                    self.hooked_item_idx = -1
                self.claw_state = CLAW_SWINGING

    def _check_claw_collisions(self) -> None:
        for i, item in enumerate(self.items):
            if not item["active"]:
                continue

            dx = abs(self.claw_x - item["x"])
            dy = abs(self.claw_y - item["y"])
            hit_r = item["radius"]

            if dx < hit_r and dy < hit_r:
                if item["type"] == ITEM_TNT_BARREL:
                    item["active"] = False
                    for other in self.items:
                        if other["active"]:
                            ndx = abs(item["x"] - other["x"])
                            ndy = abs(item["y"] - other["y"])
                            if ndx < 2.8 and ndy < 2.8:
                                other["active"] = False
                    self.claw_state = CLAW_RETRACTING
                    self.hooked_item_idx = -1
                else:
                    self.hooked_item_idx = i
                    self.claw_state = CLAW_RETRACTING
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

        # 1. Earth & dirt
        for y in range(3, 16):
            for x in range(16):
                dirt = 60 if ((x + y) % 2 == 0) else 50
                set_pixel(x, y, dirt, dirt - 15, 20)

        for x in range(16):
            set_pixel(x, 2, 80, 140, 50)

        # 2. Items
        for item in self.items:
            if not item["active"]:
                continue
            ix = int(round(item["x"]))
            iy = int(round(item["y"]))

            if item["type"] == ITEM_SMALL_GOLD:
                set_pixel(ix, iy, 255, 210, 20)
            elif item["type"] == ITEM_LARGE_GOLD:
                set_pixel(ix, iy, 255, 220, 30)
                set_pixel((ix + 1) % 16, iy, 240, 180, 20)
                set_pixel(ix, (iy + 1) % 16, 240, 180, 20)
                set_pixel((ix + 1) % 16, (iy + 1) % 16, 210, 150, 10)
            elif item["type"] == ITEM_DIAMOND:
                set_pixel(ix, iy, 120, 240, 255)
            elif item["type"] == ITEM_ROCK:
                set_pixel(ix, iy, 140, 130, 120)
                set_pixel((ix + 1) % 16, iy, 100, 95, 90)
            elif item["type"] == ITEM_TNT_BARREL:
                set_pixel(ix, iy, 255, 40, 20)
                set_pixel(ix, iy - 1, 255, 220, 0)

        # 3. Cable line
        steps = int(self.claw_dist * 2.0) + 1
        for s in range(steps + 1):
            t = float(s) / float(steps)
            lx = int(round(self.winch_x + (self.claw_x - self.winch_x) * t))
            ly = int(round(self.winch_y + (self.claw_y - self.winch_y) * t))
            set_pixel(lx, ly, 180, 180, 180)

        # 4. Claw
        cx = int(round(self.claw_x))
        cy = int(round(self.claw_y))
        set_pixel(cx, cy, 240, 240, 255)
        set_pixel(cx - 1, cy, 180, 180, 200)
        set_pixel(cx + 1, cy, 180, 180, 200)

        # 5. Cart
        set_pixel(7, 1, 220, 140, 40)
        set_pixel(8, 1, 220, 140, 40)
        set_pixel(7, 0, 255, 200, 140)
        set_pixel(8, 0, 255, 220, 0)

        # 6. HUD
        prog_bars = min(6, int((float(self.score) / float(self.target_quota)) * 6.0)) if self.target_quota > 0 else 6
        for p in range(prog_bars):
            set_pixel(p, 0, 40, 220, 80)

        for d in range(min(self.dynamite_count, 3)):
            set_pixel(15 - d, 0, 255, 40, 20)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "target_quota": self.target_quota,
            "dynamite_count": self.dynamite_count,
            "time_remaining": self.time_remaining,
            "claw_state": self.claw_state,
            "claw_x": self.claw_x,
            "claw_y": self.claw_y,
            "hooked_item_idx": self.hooked_item_idx,
        }
