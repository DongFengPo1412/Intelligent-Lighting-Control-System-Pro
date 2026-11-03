# -*- coding: utf-8 -*-
"""
Game #145: 吸尘器大冒险 (Tumblepop 1991 / Data East)
街机历史上最著名的人气吸入式平台动作消除游戏：
按键A吸尘器强力抽吸幽灵怪兽打包收纳进背包、
按键B喷射巨型滚动怪兽肉球横向穿梭墙壁反弹、如保龄球般连锁碾碎全图小怪。
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
STATE_PLAYER_DOWN = 2
STATE_GAME_OVER = 3

PLATFORMS_Y = [14.0, 10.0, 6.0, 2.0]


class Game145Tumblepop(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 2.0
        self.py = 14.0
        self.pvy = 0.0
        self.facing = 1  # 1: Right, -1: Left
        self.is_jumping = False

        # Suction state
        self.is_vacuuming = False
        self.monsters_in_pack = 0
        self.max_pack = 4

        # Ejected rolling monster ball
        self.rolling_ball: Optional[Dict[str, Any]] = None

        # Enemies (Ghosts / Goblins)
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 145

    @property
    def name(self) -> str:
        return "吸尘器大冒险"

    @property
    def english_name(self) -> str:
        return "Tumblepop"

    @property
    def release_year(self) -> int:
        return 1991

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "吸尘器流体吸入怪兽背包打包、喷射巨型肉球墙壁反弹、保龄球级联碾碎全屏幽灵"

    def get_name(self) -> str:
        return "Tumblepop (1991)"

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
        self.pvy = 0.0
        self.facing = 1
        self.is_jumping = False
        self.is_vacuuming = False
        self.monsters_in_pack = 0
        self.rolling_ball = None

        self.enemies = [
            {"x": 6.0, "y": 14.0, "vx": 2.0, "type": 0, "being_sucked": False, "alive": True},
            {"x": 12.0, "y": 10.0, "vx": -2.0, "type": 1, "being_sucked": False, "alive": True},
            {"x": 4.0, "y": 6.0, "vx": 2.2, "type": 0, "being_sucked": False, "alive": True},
            {"x": 10.0, "y": 2.0, "vx": -1.8, "type": 1, "being_sucked": False, "alive": True},
        ]

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_PLAYER_DOWN):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_PLAYER_DOWN:
                    if self.lives > 0:
                        self.px = 2.0
                        self.py = 14.0
                        self.pvy = 0.0
                        self.monsters_in_pack = 0
                        self.rolling_ball = None
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
        # 1. Horizontal Walking
        move_speed = 5.5
        if buttons & KEY_LEFT:
            self.px = max(1.0, self.px - move_speed * dt)
            self.facing = -1
        if buttons & KEY_RIGHT:
            self.px = min(14.0, self.px + move_speed * dt)
            self.facing = 1

        # 2. Jump (UP or KEY_B when pack is empty)
        if not self.is_jumping:
            if (buttons & KEY_UP) or ((buttons & KEY_B) and not (prev_buttons & KEY_B) and self.monsters_in_pack == 0):
                self.is_jumping = True
                self.pvy = -9.0

        # Jump & Gravity
        if self.is_jumping:
            self.pvy += 20.0 * dt
            self.py += self.pvy * dt
            # Landing on platforms
            if self.pvy >= 0.0:
                for plat_y in PLATFORMS_Y:
                    if abs(self.py - plat_y) < 0.5:
                        self.py = plat_y
                        self.pvy = 0.0
                        self.is_jumping = False
                        break
            if self.py >= 14.0:
                self.py = 14.0
                self.pvy = 0.0
                self.is_jumping = False

        # Drop down platform with KEY_DOWN
        if not self.is_jumping and (buttons & KEY_DOWN):
            if self.py < 14.0:
                self.py += 1.0
                self.is_jumping = True
                self.pvy = 2.0

        # 3. Suction Vacuum: Key A
        self.is_vacuuming = bool(buttons & KEY_A)

        # 4. Eject Monster Ball: Key B (when monsters in pack)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.monsters_in_pack > 0 and self.rolling_ball is None:
                # Launch monster ball with high momentum!
                ball_power = self.monsters_in_pack
                self.rolling_ball = {
                    "x": self.px + self.facing * 1.2,
                    "y": self.py,
                    "vx": float(self.facing * (10.0 + ball_power * 2.0)),
                    "bounces": 4,
                    "power": ball_power,
                    "active": True,
                }
                self.monsters_in_pack = 0

        # 5. Update Enemies & Suction
        cone_dist = 4.5
        all_dead = True
        for e in self.enemies:
            if not e["alive"]:
                continue
            all_dead = False

            if self.is_vacuuming and abs(e["y"] - self.py) < 1.0:
                # Check if in suction cone
                in_cone = False
                if self.facing > 0 and 0.0 <= e["x"] - self.px <= cone_dist:
                    in_cone = True
                elif self.facing < 0 and 0.0 <= self.px - e["x"] <= cone_dist:
                    in_cone = True

                if in_cone:
                    e["being_sucked"] = True
                    # Pull enemy towards player nozzle
                    pull_speed = 7.0
                    if e["x"] > self.px:
                        e["x"] -= pull_speed * dt
                    else:
                        e["x"] += pull_speed * dt

                    # Check capture into pack
                    if abs(e["x"] - self.px) < 1.1:
                        if self.monsters_in_pack < self.max_pack:
                            e["alive"] = False
                            self.monsters_in_pack += 1
                            self.score += 100
                            continue
                else:
                    e["being_sucked"] = False
            else:
                e["being_sucked"] = False

            # Normal patrol walk
            if not e["being_sucked"]:
                e["x"] += e["vx"] * dt
                if e["x"] <= 1.5 or e["x"] >= 14.0:
                    e["vx"] = -e["vx"]

            # Monster collision with player
            if abs(self.px - e["x"]) < 0.9 and abs(self.py - e["y"]) < 0.8:
                if not e["being_sucked"]:
                    self._lose_life()
                    return

        # 6. Update Rolling Monster Ball
        if self.rolling_ball and self.rolling_ball["active"]:
            rb = self.rolling_ball
            rb["x"] += rb["vx"] * dt

            # Bounce off side walls
            if rb["x"] <= 1.0:
                rb["x"] = 1.0
                rb["vx"] = -rb["vx"]
                rb["bounces"] -= 1
            elif rb["x"] >= 14.5:
                rb["x"] = 14.5
                rb["vx"] = -rb["vx"]
                rb["bounces"] -= 1

            if rb["bounces"] <= 0:
                rb["active"] = False
                self.rolling_ball = None

            # Check collision with live enemies -> Bowling strike!
            if self.rolling_ball and rb["active"]:
                for e in self.enemies:
                    if e["alive"]:
                        if abs(rb["x"] - e["x"]) < 1.2 and abs(rb["y"] - e["y"]) < 1.0:
                            e["alive"] = False
                            self.score += 250

        # Stage clear check
        if all_dead and self.monsters_in_pack == 0 and self.rolling_ball is None:
            self.score += 1000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_PLAYER_DOWN
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

        # 1. Platforms
        for plat_y in PLATFORMS_Y:
            py_i = int(round(plat_y))
            for x in range(1, 15):
                set_pixel(x, py_i + 1, 120, 80, 50)
                set_pixel(x, py_i, 160, 110, 70)

        # 2. Suction Cone (Bright animated cyan vortex rays)
        if self.is_vacuuming:
            py_i = int(round(self.py))
            px_i = int(round(self.px))
            for d in range(1, 5):
                sx = px_i + self.facing * d
                set_pixel(sx, py_i, 80, 240, 255)
                set_pixel(sx, py_i - 1, 40, 180, 220)

        # 3. Rolling Monster Ball
        if self.rolling_ball and self.rolling_ball["active"]:
            rx = int(round(self.rolling_ball["x"]))
            ry = int(round(self.rolling_ball["y"]))
            set_pixel(rx, ry, 255, 60, 200)
            set_pixel(rx - 1, ry, 220, 40, 160)
            set_pixel(rx + 1, ry, 220, 40, 160)
            set_pixel(rx, ry - 1, 255, 200, 255)

        # 4. Enemies
        for e in self.enemies:
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                if e["being_sucked"]:
                    # Flashing white/cyan struggling
                    set_pixel(ex, ey, 255, 255, 255)
                    set_pixel(ex, ey - 1, 100, 200, 255)
                else:
                    if e["type"] == 0:
                        set_pixel(ex, ey, 240, 60, 60)
                        set_pixel(ex, ey - 1, 255, 140, 80)
                    else:
                        set_pixel(ex, ey, 180, 60, 220)
                        set_pixel(ex, ey - 1, 220, 100, 255)

        # 5. Player (Tumblepop Ghostbuster Suit)
        px_i = int(round(self.px))
        py_i = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            # Blue jumpsuit
            set_pixel(px_i, py_i, 50, 120, 240)
            set_pixel(px_i, py_i - 1, 255, 220, 160)  # Face
            # Backpack behind player
            set_pixel(px_i - self.facing, py_i - 1, 240, 160, 40)
            # Vacuum nozzle in front
            set_pixel(px_i + self.facing, py_i, 200, 200, 220)
        elif self.state == STATE_PLAYER_DOWN:
            set_pixel(px_i, py_i, 255, 60, 40)

        # 6. Backpack Capacity Gauge (Bottom Left)
        for b in range(self.monsters_in_pack):
            set_pixel(b * 2, 15, 255, 220, 40)

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
            "monsters_in_pack": self.monsters_in_pack,
            "is_vacuuming": self.is_vacuuming,
            "ball_active": self.rolling_ball is not None,
        }

