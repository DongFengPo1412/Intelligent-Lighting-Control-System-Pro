# -*- coding: utf-8 -*-
"""
Game #157: 酒吧侍应生 (Tapper / Root Beer Tapper 1983 / Bally Midway)
街机历史上最经典的吧台管理与滑杯斟酒接空杯名作：
上下穿梭四排平行吧台拉动酒阀滑行推酒款待蜂拥而至的酒客、
疾速反向接住酒客饮毕滑回的空酒杯防摔碎、拾取台面小费维持酒吧运转清场。
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
STATE_MUG_SHATTERED = 2
STATE_GAME_OVER = 3

BAR_Y = [3.5, 6.5, 9.5, 12.5]
BAR_LEFT = 2.0
BAR_RIGHT = 13.5


class Game157Tapper(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.bar_idx = 1  # 0 to 3
        self.bx = BAR_RIGHT

        # Sliding Mugs: {"bar": int, "x": float, "vx": float, "empty": bool, "active": bool}
        self.mugs: List[Dict[str, Any]] = []

        # Patrons: {"bar": int, "x": float, "speed": float, "drinking": bool, "active": bool}
        self.patrons: List[Dict[str, Any]] = []

        # Tips on bar: {"bar": int, "x": float, "active": bool}
        self.tips: List[Dict[str, Any]] = []

        self.total_patrons_spawned = 0
        self.total_patrons_required = 8
        self.spawn_timer = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 157

    @property
    def name(self) -> str:
        return "酒吧侍应生"

    @property
    def english_name(self) -> str:
        return "Tapper"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "四排吧台快速穿梭、拉动酒保酒阀滑行斟酒滑杯、反向接回喝空滑行空酒杯防碎与收取小费清场"

    def get_name(self) -> str:
        return "Tapper (1983)"

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
        self.bar_idx = 1
        self.bx = BAR_RIGHT
        self.mugs.clear()
        self.patrons.clear()
        self.tips.clear()
        self.total_patrons_spawned = 0
        self.total_patrons_required = 6 + self.level * 2
        self.spawn_timer = 0.0

        # Spawn initial wave of patrons (1 on bar 0, 1 on bar 2)
        self.patrons.append({"bar": 0, "x": BAR_LEFT + 0.5, "speed": 1.2, "drinking": False, "active": True})
        self.patrons.append({"bar": 2, "x": BAR_LEFT + 1.0, "speed": 1.0, "drinking": False, "active": True})
        self.total_patrons_spawned = 2

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_MUG_SHATTERED):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_MUG_SHATTERED:
                    if self.lives > 0:
                        self.mugs.clear()
                        self.bx = BAR_RIGHT
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
        # 1. Bartender Movement between 4 bars
        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            if self.bar_idx > 0:
                self.bar_idx -= 1
                self.bx = BAR_RIGHT
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            if self.bar_idx < 3:
                self.bar_idx += 1
                self.bx = BAR_RIGHT

        # Walk left/right along active counter
        speed = 5.0
        if buttons & KEY_LEFT:
            self.bx = max(7.0, self.bx - speed * dt)
        elif buttons & KEY_RIGHT:
            self.bx = min(BAR_RIGHT, self.bx + speed * dt)

        # 2. Pour and Slide Beer: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            # Bartender must be at tap (near BAR_RIGHT)
            if self.bx >= BAR_RIGHT - 1.0:
                self.mugs.append({
                    "bar": self.bar_idx,
                    "x": self.bx - 0.5,
                    "vx": -7.0,  # Slide left
                    "empty": False,
                    "active": True,
                })

        # 3. Patron Spawning
        if self.total_patrons_spawned < self.total_patrons_required:
            self.spawn_timer += dt
            if self.spawn_timer >= 2.5:
                self.spawn_timer = 0.0
                bar = (self.total_patrons_spawned * 3) % 4
                self.patrons.append({
                    "bar": bar,
                    "x": BAR_LEFT,
                    "speed": 1.2 + (self.level * 0.2),
                    "drinking": False,
                    "active": True,
                })
                self.total_patrons_spawned += 1

        # 4. Update Mugs
        for m in self.mugs:
            if not m["active"]:
                continue
            m["x"] += m["vx"] * dt

            # Over-poured full mug slides off left end of counter!
            if not m["empty"] and m["x"] < BAR_LEFT - 0.5:
                m["active"] = False
                self._lose_life()
                return

            # Returning empty mug caught by Bartender
            if m["empty"] and m["bar"] == self.bar_idx:
                if abs(m["x"] - self.bx) < 1.0:
                    m["active"] = False
                    self.score += 100
                    continue

            # Returning empty mug drops off right end of counter!
            if m["empty"] and m["x"] > BAR_RIGHT + 0.5:
                m["active"] = False
                self._lose_life()
                return

        # 5. Check Mug vs Patron Collisions
        for m in self.mugs:
            if not m["active"] or m["empty"]:
                continue

            # Check patrons on the same bar
            for p in self.patrons:
                if p["active"] and p["bar"] == m["bar"] and not p["drinking"]:
                    if abs(m["x"] - p["x"]) < 1.0:
                        # Patron catches full mug!
                        m["active"] = False
                        p["drinking"] = True
                        p["x"] -= 2.5  # Pushed back by beverage momentum
                        self.score += 150

                        # Spawn empty mug sliding back right
                        self.mugs.append({
                            "bar": p["bar"],
                            "x": p["x"] + 0.5,
                            "vx": 5.5,  # Slide right
                            "empty": True,
                            "active": True,
                        })

                        # Leave tip on bar
                        if len(self.tips) < 3:
                            self.tips.append({"bar": p["bar"], "x": p["x"], "active": True})

                        # If pushed out the front door, patron is satisfied!
                        if p["x"] <= BAR_LEFT:
                            p["active"] = False
                        else:
                            p["drinking"] = False
                        break

        self.mugs = [m for m in self.mugs if m["active"]]

        # 6. Update Patrons
        for p in self.patrons:
            if not p["active"]:
                continue

            if not p["drinking"]:
                p["x"] += p["speed"] * dt

            # Patron reaches end of bar without getting served!
            if p["x"] >= BAR_RIGHT - 0.2:
                self._lose_life()
                return

        # 7. Collect Tips
        for t in self.tips:
            if t["active"] and t["bar"] == self.bar_idx and abs(self.bx - t["x"]) < 1.0:
                t["active"] = False
                self.score += 250

        self.tips = [t for t in self.tips if t["active"]]

        # 8. Check Stage Clear
        active_patrons = sum(1 for p in self.patrons if p["active"])
        if self.total_patrons_spawned >= self.total_patrons_required and active_patrons == 0 and len(self.mugs) == 0:
            self.score += 2500
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_MUG_SHATTERED
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

        # 1. 4 Polished Wooden Bar Counters
        for by in BAR_Y:
            iy = int(by)
            for x in range(2, 15):
                set_pixel(x, iy, 140, 80, 40)      # Bar surface
                set_pixel(x, iy + 1, 90, 50, 25)   # Bar counter shadow

            # Beer Tap Dispenser on right end
            set_pixel(14, iy - 1, 220, 200, 50)

        # 2. Doorways on left edge
        for by in BAR_Y:
            iy = int(by)
            set_pixel(1, iy, 70, 70, 70)
            set_pixel(1, iy - 1, 100, 60, 40)

        # 3. Tips on Counter
        for t in self.tips:
            tx = int(round(t["x"]))
            ty = int(BAR_Y[t["bar"]])
            set_pixel(tx, ty - 1, 255, 230, 40)

        # 4. Sliding Mugs
        for m in self.mugs:
            mx = int(round(m["x"]))
            my = int(BAR_Y[m["bar"]])
            if not m["empty"]:
                # Amber Foamy Beer Mug
                set_pixel(mx, my - 1, 240, 180, 40)
                set_pixel(mx, my - 2, 255, 255, 255)  # White froth
            else:
                # Clear Glass Empty Mug
                set_pixel(mx, my - 1, 180, 220, 240)

        # 5. Patrons
        for p in self.patrons:
            if p["active"]:
                px = int(round(p["x"]))
                py = int(BAR_Y[p["bar"]])
                set_pixel(px, py - 1, 220, 60, 50)       # Shirt
                set_pixel(px, py - 2, 240, 180, 140)     # Face / Cowboy hat

        # 6. Bartender (White apron, black vest, bowtie)
        bx = int(round(self.bx))
        by = int(BAR_Y[self.bar_idx])
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(bx, by - 1, 255, 255, 255)  # White apron
            set_pixel(bx, by - 2, 240, 190, 150)  # Bartender mustache face
            set_pixel(bx + 1, by - 1, 40, 40, 40) # Vest
        elif self.state == STATE_MUG_SHATTERED:
            # Shattered glass shards
            set_pixel(bx, by, 255, 60, 40)
            set_pixel(bx - 1, by, 220, 220, 240)
            set_pixel(bx + 1, by, 220, 220, 240)

        # 7. Lives in top row
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 240, 180, 40)

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
            "bar_idx": self.bar_idx,
            "bx": self.bx,
            "mugs_count": len(self.mugs),
            "patrons_active": sum(1 for p in self.patrons if p["active"]),
        }
