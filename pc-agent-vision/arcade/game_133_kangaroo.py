# -*- coding: utf-8 -*-
"""
Game #133: 袋鼠妈妈大冒险 (Kangaroo 1982 / Sun Electronics & Atari)
街机历史上第一部融合拳击手套格击与铃铛重置水果的树冠平台攀登动作游戏：
拳击手套直拳击昏顽猴与凌空截击飞苹果、跳跃撞响吊钟刷新全树水果、多层树梢爬梯营救小袋鼠。
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
STATE_LEVEL_CLEAR = 1
STATE_MOM_DOWN = 2
STATE_GAME_OVER = 3

PLATFORM_Y = [14.0, 10.0, 6.0, 2.0]
NUM_MONKEYS = 3
MAX_APPLES = 3
NUM_FRUITS = 4


class Game133Kangaroo(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 2.0
        self.py = 14.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.p_facing = 1
        self.is_jumping = False
        self.is_ducking = False
        self.on_ladder = False
        self.punch_timer = 0.0

        self.bell_rung = False
        self.bell_ring_anim = 0.0

        self.fruits: List[Dict[str, Any]] = []
        self.monkeys: List[Dict[str, Any]] = []
        self.apples: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 133

    @property
    def name(self) -> str:
        return "袋鼠妈妈大冒险"

    @property
    def english_name(self) -> str:
        return "Kangaroo"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "拳击手套击昏顽猴与凌空截击飞苹果、跳跃撞响吊钟刷新水果、爬梯攀爬营救小袋鼠"

    def get_name(self) -> str:
        return "Kangaroo (1982)"

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
        self.pvx = 0.0
        self.pvy = 0.0
        self.p_facing = 1
        self.is_jumping = False
        self.is_ducking = False
        self.on_ladder = False
        self.punch_timer = 0.0

        self.bell_rung = False
        self.bell_ring_anim = 0.0

        self.fruits = [
            {"x": 5.0, "y": 13.0, "collected": False},
            {"x": 9.0, "y": 9.0, "collected": False},
            {"x": 6.0, "y": 5.0, "collected": False},
            {"x": 11.0, "y": 5.0, "collected": False},
        ]

        self.monkeys = [
            {"x": 8.0, "y": 10.0, "throw_timer": 2.0, "alive": True},
            {"x": 8.0, "y": 6.0, "throw_timer": 3.2, "alive": True},
            {"x": 10.0, "y": 2.0, "throw_timer": 1.5, "alive": True},
        ]

        self.apples = []
        for _ in range(MAX_APPLES):
            self.apples.append({"x": 0.0, "y": 0.0, "vy": 0.0, "active": False})

    def ring_bell(self) -> None:
        self.bell_rung = True
        self.bell_ring_anim = 0.6
        self.score += 100
        for f in self.fruits:
            f["collected"] = False

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

        if self.state == STATE_MOM_DOWN:
            if self.state_timer > 1.3:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_PLAYING
                    self.px = 2.0
                    self.py = 14.0
                    self.pvx = 0.0
                    self.pvy = 0.0
                    self.p_facing = 1
                    self.is_jumping = False
                    self.on_ladder = False
                    self.punch_timer = 0.0
            return

        if self.state == STATE_LEVEL_CLEAR:
            if self.state_timer > 1.6:
                self.level += 1
                self.score += 2000
                self._init_level()
            return

        if self.bell_ring_anim > 0.0:
            self.bell_ring_anim -= dt

        self._update_player(dt, buttons, prev_buttons)
        self._update_monkeys(dt)
        self._update_apples(dt)
        self._check_collisions()

        if self.py <= 2.5 and self.px <= 3.5:
            self.state = STATE_LEVEL_CLEAR
            self.state_timer = 0.0

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Punch (Button A)
        if self.punch_timer > 0.0:
            self.punch_timer -= dt
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.punch_timer = 0.35

        # Jump (Button B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if not self.is_jumping and not self.on_ladder:
                self.is_jumping = True
                self.pvy = -7.5

        near_ladder = False
        if abs(self.px - 12.0) < 0.8 and 9.8 <= self.py <= 14.2:
            near_ladder = True
        if abs(self.px - 3.0) < 0.8 and 5.8 <= self.py <= 10.2:
            near_ladder = True
        if abs(self.px - 5.0) < 0.8 and 1.8 <= self.py <= 6.2:
            near_ladder = True

        if near_ladder and (buttons & (KEY_UP | KEY_DOWN)):
            self.on_ladder = True
            self.is_jumping = False
            self.pvy = 0.0

        if self.on_ladder:
            climb_spd = 3.5
            if buttons & KEY_UP:
                self.py -= climb_spd * dt
            if buttons & KEY_DOWN:
                self.py += climb_spd * dt

            for plat in PLATFORM_Y:
                if abs(self.py - plat) < 0.3 and not (buttons & (KEY_UP | KEY_DOWN)):
                    self.py = plat
                    self.on_ladder = False
                    break

            if not near_ladder:
                self.on_ladder = False
            return

        walk_spd = 4.2
        if buttons & KEY_LEFT:
            self.px -= walk_spd * dt
            self.p_facing = -1
        if buttons & KEY_RIGHT:
            self.px += walk_spd * dt
            self.p_facing = 1

        if self.px < 1.0:
            self.px = 1.0
        elif self.px > 14.5:
            self.px = 14.5

        if self.is_jumping:
            self.pvy += 16.0 * dt
            self.py += self.pvy * dt
            if self.pvy > 0.0:
                for plat in PLATFORM_Y:
                    if abs(self.py - plat) < 0.45:
                        self.py = plat
                        self.pvy = 0.0
                        self.is_jumping = False
                        break

        # Bell ring
        if abs(self.px - 11.0) < 1.0 and abs(self.py - 4.5) < 1.0 and self.is_jumping:
            self.ring_bell()

    def _update_monkeys(self, dt: float) -> None:
        for m in self.monkeys:
            if not m["alive"]:
                continue
            m["throw_timer"] -= dt
            if m["throw_timer"] <= 0.0:
                m["throw_timer"] = max(1.2, 3.5 - self.level * 0.2)
                for a in self.apples:
                    if not a["active"]:
                        a["active"] = True
                        a["x"] = m["x"]
                        a["y"] = m["y"] + 0.8
                        a["vy"] = 4.0 + self.level * 0.3
                        break

    def _update_apples(self, dt: float) -> None:
        for a in self.apples:
            if not a["active"]:
                continue
            a["y"] += a["vy"] * dt
            if a["y"] > 15.0:
                a["active"] = False

    def _check_collisions(self) -> None:
        # Fruits
        for f in self.fruits:
            if not f["collected"]:
                if abs(self.px - f["x"]) < 0.85 and abs(self.py - f["y"]) < 1.0:
                    f["collected"] = True
                    self.score += 150

        # Punch
        if self.punch_timer > 0.0:
            punch_x = self.px + self.p_facing * 1.1
            punch_y = self.py

            for a in self.apples:
                if a["active"]:
                    if abs(punch_x - a["x"]) < 0.9 and abs(punch_y - a["y"]) < 0.9:
                        a["active"] = False
                        self.score += 100

            for m in self.monkeys:
                if m["alive"]:
                    if abs(punch_x - m["x"]) < 1.0 and abs(punch_y - m["y"]) < 1.0:
                        m["alive"] = False
                        self.score += 200

        # Damage vs Apples
        for a in self.apples:
            if a["active"]:
                if abs(self.px - a["x"]) < 0.75 and abs(self.py - a["y"]) < 0.85:
                    a["active"] = False
                    self.state = STATE_MOM_DOWN
                    self.state_timer = 0.0
                    break

        # Damage vs Monkeys
        for m in self.monkeys:
            if m["alive"]:
                if abs(self.px - m["x"]) < 0.75 and abs(self.py - m["y"]) < 0.85:
                    self.state = STATE_MOM_DOWN
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

        # Platforms
        for x in range(16):
            set_pixel(x, 15, 60, 140, 40)
        for x in range(2, 14):
            set_pixel(x, 11, 140, 80, 30)
            set_pixel(x, 7, 140, 80, 30)
        for x in range(1, 7):
            set_pixel(x, 3, 30, 160, 40)

        # Ladders
        for y in range(11, 15):
            set_pixel(12, y, 220, 200, 50)
        for y in range(7, 11):
            set_pixel(3, y, 220, 200, 50)
        for y in range(3, 7):
            set_pixel(5, y, 220, 200, 50)

        # Bell
        if self.bell_ring_anim > 0.0:
            set_pixel(11, 4, 255, 255, 255)
        else:
            set_pixel(11, 4, 255, 215, 0)

        # Fruits
        for f in self.fruits:
            if not f["collected"]:
                set_pixel(int(f["x"]), int(f["y"]), 255, 40, 50)

        # Monkeys
        for m in self.monkeys:
            if not m["alive"]:
                continue
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            set_pixel(mx, my, 160, 90, 40)
            set_pixel(mx, my - 1, 200, 130, 60)

        # Apples
        for a in self.apples:
            if a["active"]:
                ax = int(round(a["x"]))
                ay = int(round(a["y"]))
                set_pixel(ax, ay, 255, 50, 40)

        # Joey
        set_pixel(2, 2, 255, 180, 80)
        set_pixel(2, 1, 255, 255, 255)

        # Kangaroo
        kx = int(round(self.px))
        ky = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_LEVEL_CLEAR):
            set_pixel(kx, ky, 220, 140, 40)
            set_pixel(kx, ky - 1, 240, 160, 60)
            set_pixel(kx - self.p_facing, ky, 180, 100, 30)
            if self.punch_timer > 0.0:
                set_pixel(kx + self.p_facing * 2, ky - 1, 255, 20, 20)
            else:
                set_pixel(kx + self.p_facing, ky - 1, 220, 30, 30)
        elif self.state == STATE_MOM_DOWN:
            set_pixel(kx, ky, 255, 200, 50)
            set_pixel(kx - 1, ky, 255, 40, 20)
            set_pixel(kx + 1, ky, 255, 40, 20)

        # Lives
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 220, 140, 40)

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
            "is_punching": self.punch_timer > 0.0,
        }
