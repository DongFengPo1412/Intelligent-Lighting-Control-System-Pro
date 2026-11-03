# -*- coding: utf-8 -*-
"""
Game #138: 索道探险家 (Roc'n Rope 1983 / Konami)
街机历史上第一部融合鱼叉索道搭桥攀登与强光手电眩晕的悬崖探险动作游戏：
按键A发射鱼叉射锚空中岩壁搭设斜拉缆绳、沿悬挂索道攀爬登高跨越高崖、
按键B强光手电眩晕史前巨兽与穴居人、登顶绝壁朝圣神圣金鸟。
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
STATE_FALLEN = 2
STATE_GAME_OVER = 3


class Game138RocnRope(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 2.0
        self.py = 14.0
        self.facing = 1  # 1: Right, -1: Left

        # Rope state
        self.rope_active = False
        self.rope_start_x = 0.0
        self.rope_start_y = 0.0
        self.rope_end_x = 0.0
        self.rope_end_y = 0.0
        self.on_rope = False
        self.rope_t = 0.0  # 0.0 (start) to 1.0 (end)

        # Flashlight state
        self.flashlight_timer = 0.0

        # Ledges
        self.ledges = [
            {"y": 14.0, "x1": 1.0, "x2": 6.0},
            {"y": 14.0, "x1": 9.0, "x2": 14.0},
            {"y": 10.0, "x1": 1.0, "x2": 6.0},
            {"y": 10.0, "x1": 9.0, "x2": 14.0},
            {"y": 6.0, "x1": 4.0, "x2": 11.0},
            {"y": 2.0, "x1": 6.0, "x2": 9.0},  # Peak with Golden Bird
        ]

        # Enemies (Cavemen & Dino)
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 138

    @property
    def name(self) -> str:
        return "索道探险家"

    @property
    def english_name(self) -> str:
        return "Roc'n Rope"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "鱼叉锚索射击搭桥、沿斜拉索道攀登绝壁、强光手电眩晕史前猛兽、登顶朝圣金鸟"

    def get_name(self) -> str:
        return "Roc'n Rope (1983)"

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

        self.rope_active = False
        self.on_rope = False
        self.rope_t = 0.0
        self.flashlight_timer = 0.0

        self.enemies = [
            {"x": 4.0, "y": 10.0, "vx": 1.5, "min_x": 1.0, "max_x": 6.0, "stun_timer": 0.0, "alive": True},
            {"x": 11.0, "y": 10.0, "vx": -1.5, "min_x": 9.0, "max_x": 14.0, "stun_timer": 0.0, "alive": True},
            {"x": 7.5, "y": 6.0, "vx": 1.8, "min_x": 4.0, "max_x": 11.0, "stun_timer": 0.0, "alive": True},
        ]

    def _get_current_ledge(self, px: float, py: float) -> Optional[Dict[str, Any]]:
        for ledge in self.ledges:
            if abs(py - ledge["y"]) < 0.3 and ledge["x1"] - 0.4 <= px <= ledge["x2"] + 0.4:
                return ledge
        return None

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_FALLEN):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_FALLEN:
                    if self.lives > 0:
                        self.px = 2.0
                        self.py = 14.0
                        self.facing = 1
                        self.rope_active = False
                        self.on_rope = False
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
        # Flashlight timer
        if self.flashlight_timer > 0.0:
            self.flashlight_timer -= dt
            if self.flashlight_timer < 0.0:
                self.flashlight_timer = 0.0

        # Flashlight stun action: Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.flashlight_timer = 0.4
            # Stun enemies in line of sight
            for e in self.enemies:
                if e["alive"]:
                    if abs(e["y"] - self.py) < 1.0:
                        if (self.facing > 0 and 0.0 <= e["x"] - self.px <= 5.0) or \
                           (self.facing < 0 and 0.0 <= self.px - e["x"] <= 5.0):
                            e["stun_timer"] = 3.0
                            self.score += 50

        # Harpoon fire action: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not self.on_rope:
                # Shoot harpoon at 45 degree angle towards facing direction
                target_ledge = None
                for ledge in self.ledges:
                    if ledge["y"] < self.py - 1.5:
                        dy = self.py - ledge["y"]
                        # Target x is px + facing * dy
                        tx = self.px + self.facing * dy
                        if ledge["x1"] <= tx <= ledge["x2"]:
                            target_ledge = ledge
                            self.rope_active = True
                            self.rope_start_x = self.px
                            self.rope_start_y = self.py
                            self.rope_end_x = tx
                            self.rope_end_y = ledge["y"]
                            self.on_rope = False
                            self.rope_t = 0.0
                            break

        # Movement:
        if self.on_rope:
            # Climb up or down rope
            climb_speed = 2.0  # t units per sec
            if (buttons & KEY_UP) or (self.facing > 0 and (buttons & KEY_RIGHT)) or (self.facing < 0 and (buttons & KEY_LEFT)):
                self.rope_t += climb_speed * dt
                if self.rope_t >= 1.0:
                    # Reached top plateau!
                    self.rope_t = 1.0
                    self.px = self.rope_end_x
                    self.py = self.rope_end_y
                    self.on_rope = False
                    self.rope_active = False
                    self.score += 100

                    # Check Golden Bird peak
                    if self.py <= 2.2:
                        self.score += 1000
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 0.0
                        return
            elif buttons & KEY_DOWN:
                self.rope_t -= climb_speed * dt
                if self.rope_t <= 0.0:
                    # Climbed back down to start
                    self.rope_t = 0.0
                    self.px = self.rope_start_x
                    self.py = self.rope_start_y
                    self.on_rope = False

            self.px = self.rope_start_x + (self.rope_end_x - self.rope_start_x) * self.rope_t
            self.py = self.rope_start_y + (self.rope_end_y - self.rope_start_y) * self.rope_t
        else:
            # Walking on current ledge
            move_speed = 5.0
            if buttons & KEY_LEFT:
                self.px = max(1.0, self.px - move_speed * dt)
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.px = min(14.0, self.px + move_speed * dt)
                self.facing = 1

            # Mount rope if near start and pressing UP
            if self.rope_active and (buttons & KEY_UP):
                if abs(self.px - self.rope_start_x) < 1.0 and abs(self.py - self.rope_start_y) < 0.6:
                    self.on_rope = True
                    self.rope_t = 0.05

            # Gravity check: if not on any ledge and not on rope, fall!
            current_ledge = self._get_current_ledge(self.px, self.py)
            if not current_ledge:
                # Falling downward
                self.py += 10.0 * dt
                # Check landing on lower ledge
                landed = False
                for ledge in self.ledges:
                    if abs(self.py - ledge["y"]) < 0.6 and ledge["x1"] <= self.px <= ledge["x2"]:
                        self.py = ledge["y"]
                        landed = True
                        break
                if not landed and self.py >= 15.0:
                    self._lose_life()
                    return

        # Update Enemies
        for e in self.enemies:
            if e["alive"]:
                if e["stun_timer"] > 0.0:
                    e["stun_timer"] -= dt
                    if e["stun_timer"] < 0.0:
                        e["stun_timer"] = 0.0
                else:
                    e["x"] += e["vx"] * dt
                    if e["x"] <= e["min_x"]:
                        e["x"] = e["min_x"]
                        e["vx"] = -e["vx"]
                    elif e["x"] >= e["max_x"]:
                        e["x"] = e["max_x"]
                        e["vx"] = -e["vx"]

                # Collision with explorer
                if abs(self.px - e["x"]) < 0.9 and abs(self.py - e["y"]) < 0.9:
                    if e["stun_timer"] <= 0.0:
                        self._lose_life()
                        return

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_FALLEN
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

        # 1. Render Cliff Ledges
        for ledge in self.ledges:
            ly = int(round(ledge["y"]))
            for x in range(int(round(ledge["x1"])), int(round(ledge["x2"])) + 1):
                set_pixel(x, ly, 140, 80, 40)
                set_pixel(x, ly + 1, 90, 50, 25)

        # 2. Render Golden Phoenix Bird at Peak (Tier 3)
        set_pixel(7, 1, 255, 230, 40)
        set_pixel(8, 1, 255, 230, 40)
        set_pixel(7, 2, 255, 180, 30)
        set_pixel(8, 2, 255, 180, 30)

        # 3. Render Tension Rope if active
        if self.rope_active:
            steps = 10
            for s in range(steps + 1):
                t = s / float(steps)
                rx = int(round(self.rope_start_x + (self.rope_end_x - self.rope_start_x) * t))
                ry = int(round(self.rope_start_y + (self.rope_end_y - self.rope_start_y) * t))
                set_pixel(rx, ry, 220, 200, 150)

        # 4. Render Flashlight Beam
        if self.flashlight_timer > 0.0:
            py = int(round(self.py))
            px = int(round(self.px))
            for dist in range(1, 5):
                fx = px + self.facing * dist
                set_pixel(fx, py, 255, 255, 160)

        # 5. Render Enemies (Cavemen & Dinosaurs)
        for e in self.enemies:
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                if e["stun_timer"] > 0.0:
                    # Flashing stunned stars
                    set_pixel(ex, ey, 255, 255, 50)
                    set_pixel(ex, ey - 1, 100, 200, 255)
                else:
                    # Caveman (Red / Brown)
                    set_pixel(ex, ey, 220, 50, 40)
                    set_pixel(ex, ey - 1, 255, 150, 100)

        # 6. Render Explorer Player
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            # Blue explorer suit with adventurer hat
            set_pixel(px, py, 40, 120, 240)
            set_pixel(px, py - 1, 240, 180, 60)
            set_pixel(px + self.facing, py, 200, 200, 200)  # Harpoon / hands
        elif self.state == STATE_FALLEN:
            set_pixel(px, py, 255, 60, 40)

        # 7. Lives indicator
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 40, 120, 240)

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
            "rope_active": self.rope_active,
            "on_rope": self.on_rope,
            "rope_t": self.rope_t,
            "is_flashing": self.flashlight_timer > 0.0,
        }
