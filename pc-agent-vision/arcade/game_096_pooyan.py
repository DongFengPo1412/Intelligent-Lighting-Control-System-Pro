"""
Game #096: 经典猪小弟 (Pooyan 1982 / Konami)
Mama Pig in cliff rope elevator basket shooting arrows at wolf balloons & lobbing parabolic meat slabs.
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

STATE_DEFENDING = 0
STATE_MAMA_HIT = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3

MAX_ARROWS = 4
MAX_WOLVES = 3


class Game096Pooyan(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_DEFENDING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.wolves_defeated = 0

        # Mama Pig
        self.basket_y = 8.0
        self.shoot_cooldown = 0.0

        # Meat Slab
        self.meat_available = True
        self.meat_active = False
        self.meat_x = 0.0
        self.meat_y = 0.0
        self.meat_vx = 0.0
        self.meat_vy = 0.0
        self.meat_reload_timer = 0.0

        self.arrows: List[Dict[str, Any]] = []
        self.wolves: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 96

    @property
    def name(self) -> str:
        return "经典猪小弟"

    @property
    def english_name(self) -> str:
        return "Pooyan"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "悬崖升降吊篮滑行、弓箭直射气球与抛投肉块弧线群秒"

    def get_name(self) -> str:
        return "Pooyan (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._reset_canyon(hard_reset=True)

    def _reset_canyon(self, hard_reset: bool = False) -> None:
        self.state = STATE_DEFENDING
        self.state_timer = 0.0
        self.wolves_defeated = 0

        self.basket_y = 8.0
        self.shoot_cooldown = 0.0
        self.meat_available = True
        self.meat_active = False
        self.meat_reload_timer = 0.0

        self.arrows = [
            {"x": 0.0, "y": 0.0, "vx": -14.0, "active": False}
            for _ in range(MAX_ARROWS)
        ]

        self.wolves = []
        for i in range(MAX_WOLVES):
            self.wolves.append({
                "x": 3.0 + i * 3.5,
                "y": 1.0 + i * 1.5,
                "vy": 1.2 + i * 0.4,
                "balloon_hp": 2 if i == 1 else 1,
                "is_falling": False,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_MAMA_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_canyon(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.round += 1
                self._reset_canyon(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_arrows(dt)
        self._update_meat(dt)
        self._update_wolves(dt)
        self._check_combat()

        if self.wolves_defeated >= 6:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.shoot_cooldown > 0.0:
            self.shoot_cooldown -= dt

        if not self.meat_available and not self.meat_active:
            self.meat_reload_timer -= dt
            if self.meat_reload_timer <= 0.0:
                self.meat_available = True

        elevator_speed = 7.5
        if buttons & KEY_UP:
            self.basket_y -= elevator_speed * dt
        elif buttons & KEY_DOWN:
            self.basket_y += elevator_speed * dt

        self.basket_y = max(2.0, min(13.5, self.basket_y))

        # Button A: Arrow
        if (buttons & KEY_A) and not (prev_buttons & KEY_A) and self.shoot_cooldown <= 0.0:
            self.shoot_cooldown = 0.22
            for a in self.arrows:
                if not a["active"]:
                    a["active"] = True
                    a["x"] = 13.0
                    a["y"] = self.basket_y
                    a["vx"] = -14.0
                    self.score += 10
                    break

        # Button B: Meat Chunk (Parabolic Arc)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.meat_available and not self.meat_active:
                self.meat_available = False
                self.meat_active = True
                self.meat_reload_timer = 5.0
                self.meat_x = 13.0
                self.meat_y = self.basket_y
                self.meat_vx = -8.5
                self.meat_vy = -3.5
                self.score += 20

    def _update_arrows(self, dt: float) -> None:
        for a in self.arrows:
            if not a["active"]:
                continue
            a["x"] += a["vx"] * dt
            if a["x"] < 0.0:
                a["active"] = False

    def _update_meat(self, dt: float) -> None:
        if not self.meat_active:
            return
        self.meat_x += self.meat_vx * dt
        self.meat_y += self.meat_vy * dt
        self.meat_vy += 9.5 * dt

        if self.meat_x < 0.0 or self.meat_y > 16.0:
            self.meat_active = False

    def _update_wolves(self, dt: float) -> None:
        for idx, w in enumerate(self.wolves):
            if not w["active"]:
                if w["respawn_timer"] > 0.0:
                    w["respawn_timer"] -= dt
                else:
                    w["active"] = True
                    w["is_falling"] = False
                    w["balloon_hp"] = 2 if idx == 1 else 1
                    w["x"] = 2.5 + (idx * 2.7) % 8.0
                    w["y"] = 0.5
                    w["vy"] = 1.2 + (idx * 0.3) % 1.0
                continue

            if w["is_falling"]:
                w["y"] += 12.0 * dt
                if w["y"] > 17.0:
                    w["active"] = False
                    w["is_falling"] = False
                    w["respawn_timer"] = 2.0
                continue

            w["y"] += w["vy"] * dt
            if w["y"] >= 13.5:
                w["y"] = 13.5
                w["x"] += 2.0 * dt

    def _check_combat(self) -> None:
        # Arrows vs Balloons
        for a in self.arrows:
            if not a["active"]:
                continue
            for w in self.wolves:
                if not w["active"] or w["is_falling"]:
                    continue
                dx = abs(a["x"] - w["x"])
                dy = abs(a["y"] - (w["y"] - 1.0))
                if dx < 1.1 and dy < 1.1:
                    a["active"] = False
                    w["balloon_hp"] -= 1
                    self.score += 50
                    if w["balloon_hp"] <= 0:
                        w["is_falling"] = True
                        self.score += 200
                        self.wolves_defeated += 1
                    break

        # Meat vs Wolves
        if self.meat_active:
            for w in self.wolves:
                if not w["active"] or w["is_falling"]:
                    continue
                dx = abs(self.meat_x - w["x"])
                dy = abs(self.meat_y - w["y"])
                if dx < 1.4 and dy < 1.4:
                    w["is_falling"] = True
                    self.score += 400
                    self.wolves_defeated += 1

        # Wolves vs Mama Pig Basket (x=14)
        for w in self.wolves:
            if not w["active"] or w["is_falling"]:
                continue
            dx = abs(14.0 - w["x"])
            dy = abs(self.basket_y - w["y"])
            if dx < 1.1 and dy < 1.1:
                self.state = STATE_MAMA_HIT
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

        # Sky
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 70, 150, 240)

        # Trees
        for y in range(16):
            set_pixel(0, y, 120, 70, 30)
            if y % 3 == 0:
                set_pixel(1, y, 30, 160, 40)
                set_pixel(2, y, 30, 160, 40)

        # Right Cliff & Cable
        for y in range(16):
            set_pixel(15, y, 140, 80, 40)
            set_pixel(14, y, 220, 220, 220)

        set_pixel(14, 0, 100, 100, 100)
        set_pixel(13, 0, 100, 100, 100)

        # Wolves
        for w in self.wolves:
            if not w["active"]:
                continue
            wx = int(round(w["x"]))
            wy = int(round(w["y"]))
            if not w["is_falling"]:
                br, bg, bb = (255, 120, 220) if w["balloon_hp"] >= 2 else (255, 50, 50)
                set_pixel(wx, wy - 1, br, bg, bb)
                set_pixel(wx, wy - 2, br, bg, bb)
                set_pixel(wx - 1, wy - 2, br, bg, bb)
                set_pixel(wx + 1, wy - 2, br, bg, bb)

            set_pixel(wx, wy, 120, 120, 130)
            set_pixel(wx, wy + 1, 120, 120, 130)
            set_pixel(wx - 1, wy, 255, 200, 140)

        # Arrows
        for a in self.arrows:
            if not a["active"]:
                continue
            ax = int(round(a["x"]))
            ay = int(round(a["y"]))
            set_pixel(ax, ay, 255, 255, 255)
            set_pixel(ax + 1, ay, 240, 40, 40)

        # Meat
        if self.meat_active:
            mx = int(round(self.meat_x))
            my = int(round(self.meat_y))
            set_pixel(mx, my, 220, 40, 40)
            set_pixel(mx + 1, my, 255, 255, 255)
            set_pixel(mx, my - 1, 200, 30, 30)

        # Basket & Mama Pig
        by = int(round(self.basket_y))
        if self.state == STATE_MAMA_HIT:
            set_pixel(14, by, 255, 50, 50)
            set_pixel(13, by, 255, 200, 0)
        else:
            set_pixel(14, by + 1, 150, 90, 40)
            set_pixel(13, by + 1, 150, 90, 40)
            set_pixel(14, by, 255, 170, 190)
            set_pixel(13, by, 255, 170, 190)
            set_pixel(14, by - 1, 255, 240, 50)
            set_pixel(12, by, 220, 180, 80)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 100, 150)
        if self.meat_available:
            set_pixel(12, 0, 240, 50, 50)

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
            "basket_y": self.basket_y,
            "meat_available": self.meat_available,
            "meat_active": self.meat_active,
            "wolves_defeated": self.wolves_defeated,
        }
