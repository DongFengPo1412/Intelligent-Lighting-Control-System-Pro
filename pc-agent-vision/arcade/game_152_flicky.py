# -*- coding: utf-8 -*-
"""
Game #152: 救难小鸟 (Flicky 1984 / Sega)
街机历史上首款雏鸟长龙护航救援与杂物投掷动作经典：
蓝鸟弗利基扑翼穿梭多层悬空跳台寻回走失雏鸟组建跟随长队、
投掷电话茶杯击退巡逻恶猫、护送全员归巢大门结算递增巨额连携得分。
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
STATE_FLICKY_DOWN = 2
STATE_GAME_OVER = 3


class Game152Flicky(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 8.0
        self.py = 13.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.facing = 1  # 1: right, -1: left
        self.is_grounded = True

        # Chicks (Piopio)
        self.chicks: List[Dict[str, Any]] = []

        # Position history for trailing convoy
        self.trail_history: List[tuple] = []

        # Enemy Cats (Nyanyan)
        self.cats: List[Dict[str, Any]] = []

        # Throwables (Telephones / Teacups)
        self.throwables: List[Dict[str, Any]] = []
        self.flying_items: List[Dict[str, Any]] = []

        # Nest door
        self.door_x = 1.5
        self.door_y = 13.0
        self.rescued_count = 0

        self.reset()

    @property
    def game_id(self) -> int:
        return 152

    @property
    def name(self) -> str:
        return "救难小鸟"

    @property
    def english_name(self) -> str:
        return "Flicky"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "扑翼浮空跳跃搜寻雏鸟组建长队跟随车队、投掷电话茶杯击倒恶猫巡逻、护航全员归巢大门完成撤离"

    def get_name(self) -> str:
        return "Flicky (1984)"

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
        self.px = 8.0
        self.py = 13.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.facing = 1
        self.is_grounded = True
        self.rescued_count = 0
        self.trail_history.clear()
        self.flying_items.clear()

        # 6 Chicks scattered on platforms
        self.chicks = [
            {"x": 3.0, "y": 13.0, "state": "idle", "order": -1},
            {"x": 12.0, "y": 13.0, "state": "idle", "order": -1},
            {"x": 4.0, "y": 9.0, "state": "idle", "order": -1},
            {"x": 11.0, "y": 9.0, "state": "idle", "order": -1},
            {"x": 5.0, "y": 5.0, "state": "idle", "order": -1},
            {"x": 10.0, "y": 5.0, "state": "idle", "order": -1},
        ]

        # 2 Cats patrolling
        self.cats = [
            {"x": 13.0, "y": 13.0, "vx": -2.2, "alive": True},
            {"x": 2.0, "y": 9.0, "vx": 2.0, "alive": True},
        ]

        # Throwables on platforms
        self.throwables = [
            {"x": 6.0, "y": 13.0, "active": True},
            {"x": 8.0, "y": 9.0, "active": True},
        ]

    def _get_platform_y(self, x: float, y: float) -> Optional[float]:
        # Platforms:
        # Ground: y=13 across x in [0, 15]
        # Tier 1: y=9 across x in [2, 13]
        # Tier 2: y=5 across x in [4, 11]
        if y >= 13.0:
            return 13.0
        if 8.5 <= y <= 9.5 and 2.0 <= x <= 13.0:
            return 9.0
        if 4.5 <= y <= 5.5 and 4.0 <= x <= 11.0:
            return 5.0
        return None

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_FLICKY_DOWN):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_FLICKY_DOWN:
                    if self.lives > 0:
                        self.px = 8.0
                        self.py = 13.0
                        self.pvx = 0.0
                        self.pvy = 0.0
                        self.trail_history.clear()
                        # Unlink chicks
                        for c in self.chicks:
                            if c["state"] == "following":
                                c["state"] = "idle"
                                c["order"] = -1
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
        # 1. Flap Jump: Key A or Key UP
        if ((buttons & (KEY_A | KEY_UP)) and not (prev_buttons & (KEY_A | KEY_UP))) or \
           ((buttons & KEY_A) and self.is_grounded):
            self.pvy = -6.2
            self.is_grounded = False

        # 2. Horizontal Running
        speed = 5.0
        if buttons & KEY_LEFT:
            self.pvx = -speed
            self.facing = -1
        elif buttons & KEY_RIGHT:
            self.pvx = speed
            self.facing = 1
        else:
            self.pvx = 0.0

        # Apply gravity
        self.pvy += 12.0 * dt
        self.px += self.pvx * dt
        self.py += self.pvy * dt

        # Screen boundaries
        self.px = max(1.0, min(14.5, self.px))

        # Platform landing
        plat_y = self._get_platform_y(self.px, self.py)
        if plat_y is not None and self.pvy >= 0.0 and self.py >= plat_y:
            self.py = plat_y
            self.pvy = 0.0
            self.is_grounded = True
        else:
            self.is_grounded = False

        # 3. Record Trail History for Chaining Convoy
        self.trail_history.append((self.px, self.py))
        if len(self.trail_history) > 120:
            self.trail_history.pop(0)

        # 4. Chick Pickup & Trailing Follow
        following_chicks = [c for c in self.chicks if c["state"] == "following"]
        following_chicks.sort(key=lambda c: c["order"])

        for c in self.chicks:
            if c["state"] == "idle":
                if abs(self.px - c["x"]) < 0.9 and abs(self.py - c["y"]) < 0.9:
                    c["state"] = "following"
                    c["order"] = len(following_chicks)
                    following_chicks.append(c)
                    self.score += 50

        # Update following positions along trail
        for i, c in enumerate(following_chicks):
            lag = (i + 1) * 8
            if len(self.trail_history) > lag:
                hist_x, hist_y = self.trail_history[-lag]
                c["x"] = hist_x
                c["y"] = hist_y

        # 5. Throw Item: Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            # Check if near a throwable
            for t in self.throwables:
                if t["active"] and abs(self.px - t["x"]) < 1.2 and abs(self.py - t["y"]) < 1.2:
                    t["active"] = False
                    self.flying_items.append({
                        "x": self.px + self.facing * 0.8,
                        "y": self.py - 0.2,
                        "vx": self.facing * 10.0,
                    })
                    break

        # 6. Update Flying Thrown Items
        for item in self.flying_items:
            item["x"] += item["vx"] * dt

            # Hit cat
            for cat in self.cats:
                if cat["alive"] and abs(item["x"] - cat["x"]) < 1.0 and abs(item["y"] - cat["y"]) < 1.0:
                    cat["alive"] = False
                    item["x"] = -100.0
                    self.score += 300

        self.flying_items = [it for it in self.flying_items if 0.0 <= it["x"] <= 15.5]

        # 7. Update Cats & Train Cutting
        for cat in self.cats:
            if not cat["alive"]:
                continue
            cat["x"] += cat["vx"] * dt
            if cat["x"] <= 1.5 or cat["x"] >= 14.0:
                cat["vx"] = -cat["vx"]

            # Cat touches Flicky
            if abs(self.px - cat["x"]) < 0.8 and abs(self.py - cat["y"]) < 0.8:
                self._lose_life()
                return

            # Cat intersects trailing chicks -> cuts train!
            for c in following_chicks:
                if abs(c["x"] - cat["x"]) < 0.7 and abs(c["y"] - cat["y"]) < 0.7:
                    # Break trail from this chick backwards
                    cut_order = c["order"]
                    for fc in self.chicks:
                        if fc["state"] == "following" and fc["order"] >= cut_order:
                            fc["state"] = "idle"
                            fc["order"] = -1
                    break

        # 8. Nest Door Delivery
        if abs(self.px - self.door_x) < 1.2 and abs(self.py - self.door_y) < 1.2:
            current_following = [c for c in self.chicks if c["state"] == "following"]
            if current_following:
                mult = 1
                for c in current_following:
                    c["state"] = "rescued"
                    self.rescued_count += 1
                    self.score += 100 * mult
                    mult *= 2

        # Check stage clear
        if self.rescued_count >= len(self.chicks):
            self.score += 2500
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_FLICKY_DOWN
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

        # 1. Platforms (Pink/Beige checkerboard bricks)
        for x in range(16):
            set_pixel(x, 14, 180, 100, 120)  # Ground floor
        for x in range(2, 14):
            set_pixel(x, 10, 180, 100, 120)  # Tier 1
        for x in range(4, 12):
            set_pixel(x, 6, 180, 100, 120)   # Tier 2

        # 2. Nest Door (Exit Home) at (1, 13)
        set_pixel(1, 13, 220, 140, 40)
        set_pixel(1, 12, 160, 90, 20)

        # 3. Throwables (Teacups/Telephones: Green)
        for t in self.throwables:
            if t["active"]:
                tx = int(round(t["x"]))
                ty = int(round(t["y"]))
                set_pixel(tx, ty, 60, 220, 120)

        # 4. Flying Throwables
        for it in self.flying_items:
            ix = int(round(it["x"]))
            iy = int(round(it["y"]))
            set_pixel(ix, iy, 100, 255, 180)

        # 5. Chicks (Piopio: Bright Yellow)
        for c in self.chicks:
            if c["state"] in ("idle", "following"):
                cx = int(round(c["x"]))
                cy = int(round(c["y"]))
                set_pixel(cx, cy, 255, 230, 30)

        # 6. Enemy Cats (Nyanyan: Orange Tiger stripes)
        for cat in self.cats:
            if cat["alive"]:
                cx = int(round(cat["x"]))
                cy = int(round(cat["y"]))
                set_pixel(cx, cy, 240, 80, 40)
                set_pixel(cx, cy - 1, 255, 150, 60)

        # 7. Flicky (Bluebird with red beak)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 40, 120, 255)       # Blue body
            set_pixel(px, py - 1, 60, 160, 255)   # Head
            # Red/Orange beak in facing direction
            bx = px + self.facing
            set_pixel(bx, py - 1, 255, 80, 30)
        elif self.state == STATE_FLICKY_DOWN:
            set_pixel(px, py, 255, 60, 60)

        # 8. Lives & Rescued chicks count in top row
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 40, 120, 255)

        for r in range(min(self.rescued_count, 6)):
            set_pixel(15 - r, 0, 255, 230, 30)

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
            "rescued_count": self.rescued_count,
            "following_count": sum(1 for c in self.chicks if c["state"] == "following"),
        }

