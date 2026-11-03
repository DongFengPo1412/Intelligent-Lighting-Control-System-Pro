# -*- coding: utf-8 -*-
"""
Game #154: 魔法泡泡破裂者 (Pang / Buster Bros 1989 / Mitchell & Capcom)
街机历史上最受欢迎的铁锚射天与抛物线巨球二分分裂射击经典：
地面左右敏捷穿梭、按键A垂直发射上升铁锚抓钩搭接天花板形成刺绳切线、
触碰巨型弹跳球引发级联两极分裂、在微型弹球密集轰炸中缝隙求生全歼清屏。
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

FLOOR_Y = 13.5
CEILING_Y = 1.0


class Game154Pang(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7.5
        self.py = FLOOR_Y
        self.facing = 1

        # Harpoon wire state
        self.harpoon_active = False
        self.harpoon_x = 0.0
        self.harpoon_tip_y = 0.0
        self.harpoon_anchored = False
        self.harpoon_anchor_timer = 0.0

        # Bouncing balls
        self.balls: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 154

    @property
    def name(self) -> str:
        return "魔法泡泡破裂者"

    @property
    def english_name(self) -> str:
        return "Pang"

    @property
    def release_year(self) -> int:
        return 1989

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "发射垂直上升铁锚抓钩射向天花板、绳索锚刺触碰悬空巨型弹跳球引发级联二分分裂、穿梭微小弹球缝隙闪避并全歼清屏"

    def get_name(self) -> str:
        return "Pang (1989)"

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
        self.px = 7.5
        self.py = FLOOR_Y
        self.facing = 1
        self.harpoon_active = False
        self.harpoon_anchored = False
        self.harpoon_anchor_timer = 0.0

        # Spawn initial balls depending on level:
        # e.g. 1 huge ball (size 3) at top left
        self.balls = [
            {"x": 4.0, "y": 4.0, "vx": 2.2, "vy": 0.0, "size": 3},
        ]
        if self.level > 1:
            self.balls.append({"x": 11.0, "y": 4.0, "vx": -2.2, "vy": 0.0, "size": 2})

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
                        self.px = 7.5
                        self.py = FLOOR_Y
                        self.harpoon_active = False
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
        # 1. Player horizontal movement
        speed = 5.5
        dx = 0.0
        if buttons & KEY_LEFT:
            dx -= speed
            self.facing = -1
        elif buttons & KEY_RIGHT:
            dx += speed
            self.facing = 1

        self.px = max(1.0, min(14.5, self.px + dx * dt))

        # 2. Fire Harpoon: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not self.harpoon_active:
                self.harpoon_active = True
                self.harpoon_x = self.px
                self.harpoon_tip_y = FLOOR_Y - 0.5
                self.harpoon_anchored = False
                self.harpoon_anchor_timer = 0.0

        # 3. Update Harpoon
        if self.harpoon_active:
            if not self.harpoon_anchored:
                self.harpoon_tip_y -= 16.0 * dt
                if self.harpoon_tip_y <= CEILING_Y:
                    self.harpoon_tip_y = CEILING_Y
                    self.harpoon_anchored = True
                    self.harpoon_anchor_timer = 0.8
            else:
                self.harpoon_anchor_timer -= dt
                if self.harpoon_anchor_timer <= 0.0:
                    self.harpoon_active = False

        # 4. Update Bouncing Balls Physics
        gravity = 14.0
        bounce_speeds = {3: -8.8, 2: -7.0, 1: -5.4}
        radii = {3: 1.4, 2: 1.0, 1: 0.6}

        new_balls: List[Dict[str, Any]] = []
        balls_to_remove: List[Dict[str, Any]] = []

        for b in self.balls:
            b["vy"] += gravity * dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            r = radii[b["size"]]

            # Bounce off side walls
            if b["x"] <= 1.0 + r:
                b["x"] = 1.0 + r
                b["vx"] = abs(b["vx"])
            elif b["x"] >= 15.0 - r:
                b["x"] = 15.0 - r
                b["vx"] = -abs(b["vx"])

            # Bounce off floor
            if b["y"] >= FLOOR_Y - r:
                b["y"] = FLOOR_Y - r
                b["vy"] = bounce_speeds[b["size"]]

            # Check collision with harpoon wire
            if self.harpoon_active:
                # Harpoon is a vertical segment from harpoon_tip_y to FLOOR_Y at harpoon_x
                if self.harpoon_tip_y <= b["y"] <= FLOOR_Y:
                    if abs(b["x"] - self.harpoon_x) < r + 0.3:
                        # POP! Split the ball!
                        self.harpoon_active = False
                        balls_to_remove.append(b)

                        # Scoring
                        if b["size"] == 3:
                            self.score += 100
                        elif b["size"] == 2:
                            self.score += 200
                        else:
                            self.score += 400

                        # Split into 2 smaller balls if size > 1
                        if b["size"] > 1:
                            new_size = b["size"] - 1
                            new_balls.append({
                                "x": b["x"] - 0.4,
                                "y": b["y"],
                                "vx": -2.2,
                                "vy": -4.0,
                                "size": new_size,
                            })
                            new_balls.append({
                                "x": b["x"] + 0.4,
                                "y": b["y"],
                                "vx": 2.2,
                                "vy": -4.0,
                                "size": new_size,
                            })
                        break

            # Check collision with Player
            dist_to_player = math.hypot(b["x"] - self.px, b["y"] - self.py)
            if dist_to_player < r + 0.6:
                self._lose_life()
                return

        # Apply splits and removals
        self.balls = [b for b in self.balls if b not in balls_to_remove]
        self.balls.extend(new_balls)

        # 5. Check Stage Clear
        if len(self.balls) == 0:
            self.score += 2000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

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

        # 1. Floor & Ceiling Bricks (Ancient Temple Ruins)
        for x in range(16):
            set_pixel(x, 15, 100, 100, 110)
            set_pixel(x, 0, 70, 70, 80)
        for y in range(16):
            set_pixel(0, y, 70, 70, 80)
            set_pixel(15, y, 70, 70, 80)

        # 2. Harpoon Wire & Hook Head
        if self.harpoon_active:
            hx = int(round(self.harpoon_x))
            tip_y = int(round(self.harpoon_tip_y))
            # Hook spear tip
            set_pixel(hx, tip_y, 255, 230, 80)
            if hx - 1 >= 0: set_pixel(hx - 1, tip_y + 1, 255, 200, 50)
            if hx + 1 < 16: set_pixel(hx + 1, tip_y + 1, 255, 200, 50)
            # Trailing wire
            for wy in range(tip_y + 1, int(FLOOR_Y) + 1):
                set_pixel(hx, wy, 200, 200, 220)

        # 3. Bouncing Balls (Red / Orange Spheres with shading)
        for b in self.balls:
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["size"] == 3:
                # Huge ball (3x3 core)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        set_pixel(bx + dx, by + dy, 240, 40, 40)
                set_pixel(bx - 1, by - 1, 255, 140, 140)  # Highlight
            elif b["size"] == 2:
                # Medium ball (2x2)
                set_pixel(bx, by, 255, 90, 30)
                set_pixel(bx + 1, by, 240, 70, 30)
                set_pixel(bx, by - 1, 255, 160, 80)
            else:
                # Small ball (single pixel)
                set_pixel(bx, by, 255, 220, 40)

        # 4. Buster Buster Explorer Player
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 30, 80, 220)       # Blue trousers
            set_pixel(px, py - 1, 255, 60, 40)   # Red shirt
            set_pixel(px, py - 2, 240, 200, 150) # Explorer cap
        elif self.state == STATE_PLAYER_HIT:
            set_pixel(px, py, 255, 50, 50)

        # 5. Lives in top row
        for l in range(min(self.lives, 3)):
            set_pixel(1 + l * 2, 0, 255, 60, 40)

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
            "harpoon_active": self.harpoon_active,
            "balls_count": len(self.balls),
        }

