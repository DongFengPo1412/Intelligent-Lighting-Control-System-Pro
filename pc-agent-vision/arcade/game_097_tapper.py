"""
Game #097: 快打酒保 (Root Beer Tapper 1983 / Bally Midway)
Multi-lane root beer drafting & sliding, catching returning empty mugs, tip pickups & avoiding floor shatters.
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

STATE_SERVING = 0
STATE_MUG_CRASHED = 1
STATE_PATRON_OVERRUN = 2
STATE_ROUND_CLEAR = 3
STATE_GAME_OVER = 4

NUM_LANES = 4
MAX_MUGS = 6
MAX_PATRONS = 4
LANE_YS = [3, 6, 9, 12]


class Game097Tapper(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_SERVING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.patrons_satisfied = 0

        # Bartender
        self.current_lane = 0
        self.bx = 13.0
        self.is_filling_mug = False
        self.fill_timer = 0.0

        self.tips = [False] * NUM_LANES
        self.tip_x = [6.0] * NUM_LANES

        self.mugs: List[Dict[str, Any]] = []
        self.patrons: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 97

    @property
    def name(self) -> str:
        return "快打酒保"

    @property
    def english_name(self) -> str:
        return "Root Beer Tapper"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多轨道吧台倒酒滑杯推退顾客、接住滑回空杯防碎与收集吧台小费"

    def get_name(self) -> str:
        return "Root Beer Tapper (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._reset_bar(hard_reset=True)

    def _reset_bar(self, hard_reset: bool = False) -> None:
        self.state = STATE_SERVING
        self.state_timer = 0.0
        self.patrons_satisfied = 0

        self.current_lane = 0
        self.bx = 13.0
        self.is_filling_mug = False
        self.fill_timer = 0.0

        self.tips = [False] * NUM_LANES
        self.tip_x = [6.0] * NUM_LANES

        self.mugs = [
            {"lane": 0, "x": 12.0, "vx": -9.0, "is_empty": False, "active": False}
            for _ in range(MAX_MUGS)
        ]

        self.patrons = []
        for i in range(MAX_PATRONS):
            self.patrons.append({
                "lane": i % NUM_LANES,
                "x": 1.0 + (i % 2) * 2.0,
                "speed": 1.0 + (i % 3) * 0.3,
                "is_drinking": False,
                "drink_timer": 0.0,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state in (STATE_MUG_CRASHED, STATE_PATRON_OVERRUN):
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_bar(hard_reset=False)
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 2.0:
                self.round += 1
                self._reset_bar(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_bartender(dt, buttons, prev_buttons)
        self._update_mugs(dt)
        self._update_patrons(dt)
        self._check_collisions()

        if self.patrons_satisfied >= 6:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0
            self.score += 1500

    def _update_bartender(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            if self.current_lane > 0:
                self.current_lane -= 1
                self.bx = 13.0
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            if self.current_lane < NUM_LANES - 1:
                self.current_lane += 1
                self.bx = 13.0

        move_speed = 6.0
        if buttons & KEY_LEFT:
            self.bx -= move_speed * dt
        elif buttons & KEY_RIGHT:
            self.bx += move_speed * dt
        self.bx = max(7.5, min(13.5, self.bx))

        # Tip collection
        if self.tips[self.current_lane]:
            if abs(self.bx - self.tip_x[self.current_lane]) < 1.0:
                self.tips[self.current_lane] = False
                self.score += 100

        # Button A: Pour / Release
        if buttons & KEY_A:
            self.is_filling_mug = True
            self.fill_timer += dt
        else:
            if self.is_filling_mug:
                self.is_filling_mug = False
                self.fill_timer = 0.0
                for m in self.mugs:
                    if not m["active"]:
                        m["active"] = True
                        m["lane"] = self.current_lane
                        m["x"] = min(12.5, self.bx - 0.5)
                        m["vx"] = -9.0
                        m["is_empty"] = False
                        self.score += 10
                        break

    def _update_mugs(self, dt: float) -> None:
        for m in self.mugs:
            if not m["active"]:
                continue
            m["x"] += m["vx"] * dt

            # 1. Full beer slide off left end
            if not m["is_empty"] and m["x"] <= 0.5:
                m["active"] = False
                self.state = STATE_MUG_CRASHED
                self.state_timer = 0.0
                return

            # 2. Empty mug sliding right
            if m["is_empty"]:
                if m["lane"] == self.current_lane and abs(m["x"] - self.bx) < 0.8:
                    m["active"] = False
                    self.score += 100
                    continue

                if m["x"] >= 14.2:
                    m["active"] = False
                    self.state = STATE_MUG_CRASHED
                    self.state_timer = 0.0
                    return

    def _update_patrons(self, dt: float) -> None:
        for idx, p in enumerate(self.patrons):
            if not p["active"]:
                if p["respawn_timer"] > 0.0:
                    p["respawn_timer"] -= dt
                else:
                    p["active"] = True
                    p["lane"] = (idx * 2 + self.round) % NUM_LANES
                    p["x"] = 1.0
                    p["speed"] = 1.0 + (idx * 0.4) % 0.8
                    p["is_drinking"] = False
                    p["drink_timer"] = 0.0
                continue

            if p["is_drinking"]:
                p["drink_timer"] -= dt
                if p["drink_timer"] <= 0.0:
                    p["is_drinking"] = False
                    for m in self.mugs:
                        if not m["active"]:
                            m["active"] = True
                            m["lane"] = p["lane"]
                            m["x"] = p["x"] + 0.8
                            m["vx"] = 7.5
                            m["is_empty"] = True
                            break

                    self.tips[p["lane"]] = True
                    self.tip_x[p["lane"]] = p["x"]

                    p["active"] = False
                    p["respawn_timer"] = 2.5
                    self.patrons_satisfied += 1
                continue

            p["x"] += p["speed"] * dt
            if p["x"] >= 13.0:
                self.state = STATE_PATRON_OVERRUN
                self.state_timer = 0.0
                return

    def _check_collisions(self) -> None:
        for m in self.mugs:
            if not m["active"] or m["is_empty"]:
                continue
            for p in self.patrons:
                if not p["active"] or p["is_drinking"]:
                    continue
                if m["lane"] == p["lane"] and abs(m["x"] - p["x"]) < 1.1:
                    m["active"] = False
                    p["is_drinking"] = True
                    p["drink_timer"] = 1.0
                    p["x"] = max(1.0, p["x"] - 3.0)
                    self.score += 50
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

        for l in range(NUM_LANES):
            by = LANE_YS[l]
            for x in range(1, 15):
                set_pixel(x, by, 160, 85, 30)
            set_pixel(14, by - 1, 230, 200, 40)
            for x in range(1, 15):
                set_pixel(x, by + 1, 80, 50, 20)

            if self.tips[l]:
                tx = int(round(self.tip_x[l]))
                set_pixel(tx, by - 1, 50, 220, 50)

        # Patrons
        for p in self.patrons:
            if not p["active"]:
                continue
            px = int(round(p["x"]))
            py = LANE_YS[p["lane"]]
            if p["is_drinking"]:
                set_pixel(px, py - 1, 255, 200, 50)
                set_pixel(px - 1, py - 1, 200, 150, 100)
                set_pixel(px, py, 40, 80, 200)
            else:
                set_pixel(px, py - 1, 220, 160, 120)
                set_pixel(px, py - 2, 140, 70, 20)
                set_pixel(px, py, 180, 40, 40)
                set_pixel(px + 1, py, 220, 160, 120)

        # Mugs
        for m in self.mugs:
            if not m["active"]:
                continue
            mx = int(round(m["x"]))
            my = LANE_YS[m["lane"]] - 1
            if m["is_empty"]:
                set_pixel(mx, my, 200, 230, 255)
            else:
                set_pixel(mx, my, 180, 100, 20)
                set_pixel(mx, my - 1, 255, 255, 255)

        # Bartender
        b_lane_y = LANE_YS[self.current_lane]
        bx = int(round(self.bx))

        if self.state in (STATE_MUG_CRASHED, STATE_PATRON_OVERRUN):
            set_pixel(bx, b_lane_y - 1, 255, 50, 50)
            set_pixel(bx + 1, b_lane_y, 255, 255, 255)
            set_pixel(bx - 1, b_lane_y, 255, 255, 255)
        else:
            set_pixel(bx, b_lane_y, 30, 30, 30)
            set_pixel(bx, b_lane_y - 1, 255, 255, 255)
            set_pixel(bx - 1, b_lane_y - 1, 240, 50, 50)
            set_pixel(bx, b_lane_y - 2, 240, 190, 140)

            if self.is_filling_mug:
                set_pixel(bx - 1, b_lane_y - 2, 255, 220, 40)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 240, 180, 50)

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
            "current_lane": self.current_lane,
            "bartender_x": self.bx,
            "is_filling_mug": self.is_filling_mug,
            "patrons_satisfied": self.patrons_satisfied,
        }
