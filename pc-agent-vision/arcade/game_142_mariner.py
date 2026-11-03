# -*- coding: utf-8 -*-
"""
Game #142: 深海潜航者 (Mariner 1981 / Amenip)
街机历史上第一部具备双向水下/水面火控与深海海沟勘探的潜艇横版射击游戏：
平移推进与中性浮力潜浮、按键A前向重型鱼雷猎杀深海潜艇、
按键B垂直防空深水导弹轰击水面驱逐舰、捕获海底热泉氧气泡与打捞沉船黄金。
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
STATE_SUB_CRASH = 2
STATE_GAME_OVER = 3


class Game142Mariner(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.oxygen = 100.0

        # Submarine position
        self.px = 3.0
        self.py = 7.0
        self.vx = 0.0
        self.vy = 0.0

        # Projectiles
        self.torpedoes: List[Dict[str, Any]] = []      # Horizontal (Key A)
        self.vertical_missiles: List[Dict[str, Any]] = []  # Upward (Key B)

        # Enemies: Enemy subs (underwater) & Destroyers (surface y=1)
        self.enemies: List[Dict[str, Any]] = []

        # Surface depth charges dropped by destroyers
        self.depth_charges: List[Dict[str, Any]] = []

        # Seabed floor height array (16 columns)
        self.seabed = [14.0 for _ in range(16)]
        self.scroll_dist = 0.0

        # Oxygen bubbles from vents & Treasure chests
        self.bubbles: List[Dict[str, Any]] = []
        self.treasures: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 142

    @property
    def name(self) -> str:
        return "深海潜航者"

    @property
    def english_name(self) -> str:
        return "Mariner"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双向火控交火（前向鱼雷+垂直防空导弹）、深海热泉氧气补给、规避下沉深弹与打捞沉船金币"

    def get_name(self) -> str:
        return "Mariner (1981)"

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
        self.oxygen = 100.0
        self.px = 3.0
        self.py = 7.0
        self.vx = 0.0
        self.vy = 0.0
        self.scroll_dist = 0.0

        self.torpedoes = []
        self.vertical_missiles = []
        self.depth_charges = []

        # Seabed terrain
        for x in range(16):
            self.seabed[x] = 13.0 + math.sin(x * 0.4) * 1.5

        # Enemies
        self.enemies = [
            {"x": 14.0, "y": 1.0, "vx": -2.0, "type": "destroyer", "shoot_timer": 1.5, "alive": True},
            {"x": 13.0, "y": 6.0, "vx": -2.5, "type": "sub", "shoot_timer": 2.2, "alive": True},
            {"x": 15.0, "y": 10.0, "vx": -1.8, "type": "sub", "shoot_timer": 3.0, "alive": True},
        ]

        # Bubbles & Treasures
        self.bubbles = [
            {"x": 6.0, "y": 12.0, "vy": -2.0, "alive": True},
            {"x": 12.0, "y": 13.0, "vy": -2.0, "alive": True},
        ]
        self.treasures = [
            {"x": 9.0, "y": 13.0, "collected": False},
        ]

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_SUB_CRASH):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_SUB_CRASH:
                    if self.lives > 0:
                        self.px = 3.0
                        self.py = 7.0
                        self.oxygen = 100.0
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
        # Oxygen drain
        self.oxygen -= 3.0 * dt
        if self.oxygen <= 0.0:
            self.oxygen = 0.0
            self._crash()
            return

        # Neutral buoyancy movement
        move_speed = 6.0
        if buttons & KEY_LEFT:
            self.px = max(1.0, self.px - move_speed * dt)
        if buttons & KEY_RIGHT:
            self.px = min(14.0, self.px + move_speed * dt)
        if buttons & KEY_UP:
            self.py = max(2.0, self.py - move_speed * 0.8 * dt)  # Water surface is y=1.5
        if buttons & KEY_DOWN:
            self.py = min(14.5, self.py + move_speed * 0.8 * dt)

        # Seabed collision
        col_idx = max(0, min(15, int(round(self.px))))
        if self.py >= self.seabed[col_idx] - 0.4:
            self._crash()
            return

        # 1. Fire Torpedo (Horizontal: Key A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.torpedoes) < 2:
                self.torpedoes.append({"x": self.px + 1.0, "y": self.py, "active": True})

        # 2. Fire Vertical Depth Missile (Upward: Key B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if len(self.vertical_missiles) < 2:
                self.vertical_missiles.append({"x": self.px, "y": self.py - 1.0, "active": True})

        # Update Torpedoes
        for t in self.torpedoes:
            if t["active"]:
                t["x"] += 14.0 * dt
                if t["x"] > 15.5:
                    t["active"] = False
                    continue

                for e in self.enemies:
                    if e["alive"] and e["type"] == "sub":
                        if abs(t["x"] - e["x"]) < 1.1 and abs(t["y"] - e["y"]) < 0.9:
                            e["alive"] = False
                            t["active"] = False
                            self.score += 150
                            break

        self.torpedoes = [t for t in self.torpedoes if t["active"]]

        # Update Vertical Missiles
        for m in self.vertical_missiles:
            if m["active"]:
                m["y"] -= 12.0 * dt
                if m["y"] < 0.5:
                    m["active"] = False
                    continue

                # Intercept falling depth charges
                for dc in self.depth_charges:
                    if dc["active"]:
                        if abs(m["x"] - dc["x"]) < 1.0 and abs(m["y"] - dc["y"]) < 1.0:
                            dc["active"] = False
                            m["active"] = False
                            self.score += 80
                            break

                # Blast surface destroyer
                if m["active"]:
                    for e in self.enemies:
                        if e["alive"] and e["type"] == "destroyer":
                            if abs(m["x"] - e["x"]) < 1.4 and abs(m["y"] - e["y"]) < 1.0:
                                e["alive"] = False
                                m["active"] = False
                                self.score += 300
                                break

        self.vertical_missiles = [m for m in self.vertical_missiles if m["active"]]

        # Update Enemies & Depth Charges
        all_enemies_dead = True
        for e in self.enemies:
            if e["alive"]:
                all_enemies_dead = False
                e["x"] += e["vx"] * dt
                if e["x"] < -1.0:
                    e["x"] = 16.5

                e["shoot_timer"] -= dt
                if e["shoot_timer"] <= 0.0:
                    e["shoot_timer"] = 2.5
                    if e["type"] == "destroyer" and len(self.depth_charges) < 3:
                        # Drop depth charge
                        self.depth_charges.append({"x": e["x"], "y": 2.0, "vy": 3.5, "active": True})

                # Direct collision with submarine
                if abs(self.px - e["x"]) < 1.0 and abs(self.py - e["y"]) < 0.9:
                    self._crash()
                    return

        # Update Depth Charges
        for dc in self.depth_charges:
            if dc["active"]:
                dc["y"] += dc["vy"] * dt
                if dc["y"] > 15.0:
                    dc["active"] = False
                    continue

                if abs(self.px - dc["x"]) < 0.9 and abs(self.py - dc["y"]) < 0.9:
                    dc["active"] = False
                    self._crash()
                    return

        self.depth_charges = [dc for dc in self.depth_charges if dc["active"]]

        # Update Oxygen Bubbles
        for b in self.bubbles:
            if b["alive"]:
                b["y"] += b["vy"] * dt
                if b["y"] < 2.0:
                    b["y"] = 13.5
                    b["x"] = (b["x"] + 4.0) % 14.0 + 1.0

                if abs(self.px - b["x"]) < 1.0 and abs(self.py - b["y"]) < 1.0:
                    b["alive"] = False
                    self.oxygen = min(100.0, self.oxygen + 35.0)
                    self.score += 50

        # Update Treasures
        for tr in self.treasures:
            if not tr["collected"]:
                if abs(self.px - tr["x"]) < 1.1 and abs(self.py - tr["y"]) < 1.0:
                    tr["collected"] = True
                    self.score += 500

        # Stage Clear when enemies cleared
        if all_enemies_dead:
            self.score += 1000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _crash(self) -> None:
        self.lives -= 1
        self.state = STATE_SUB_CRASH
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

        # 1. Surface Water Line (Row 1: Light cyan waves)
        for x in range(16):
            set_pixel(x, 1, 50, 180, 240)

        # 2. Seabed Floor (Dark brown & coral)
        for x in range(16):
            floor_y = int(round(self.seabed[x]))
            for y in range(floor_y, 16):
                set_pixel(x, y, 60, 40, 25)
            set_pixel(x, floor_y, 110, 80, 40)

        # 3. Treasures (Gold Chest)
        for tr in self.treasures:
            if not tr["collected"]:
                tx = int(round(tr["x"]))
                ty = int(round(tr["y"]))
                set_pixel(tx, ty, 255, 215, 30)
                set_pixel(tx, ty - 1, 255, 255, 100)

        # 4. Oxygen Bubbles
        for b in self.bubbles:
            if b["alive"]:
                set_pixel(int(round(b["x"])), int(round(b["y"])), 180, 240, 255)

        # 5. Enemies (Destroyers at surface, subs in deep)
        for e in self.enemies:
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                if e["type"] == "destroyer":
                    # Grey warship
                    set_pixel(ex, ey, 180, 180, 190)
                    set_pixel(ex - 1, ey, 140, 140, 150)
                    set_pixel(ex + 1, ey, 140, 140, 150)
                    set_pixel(ex, ey - 1, 80, 80, 90)  # Smokestack
                else:
                    # Enemy Sub (Red)
                    set_pixel(ex, ey, 240, 40, 40)
                    set_pixel(ex + 1, ey, 180, 30, 30)
                    set_pixel(ex, ey - 1, 255, 100, 80)

        # 6. Depth Charges (Dropping bombs)
        for dc in self.depth_charges:
            set_pixel(int(round(dc["x"])), int(round(dc["y"])), 255, 120, 20)

        # 7. Torpedoes & Vertical Missiles
        for t in self.torpedoes:
            set_pixel(int(round(t["x"])), int(round(t["y"])), 255, 255, 255)
        for m in self.vertical_missiles:
            set_pixel(int(round(m["x"])), int(round(m["y"])), 255, 230, 50)

        # 8. Player Submarine (Yellow research submarine!)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 240, 200, 30)
            set_pixel(px - 1, py, 200, 160, 20)
            set_pixel(px + 1, py, 255, 240, 80)  # Nose
            set_pixel(px, py - 1, 240, 200, 30)  # Conning tower
            set_pixel(px, py + 1, 160, 140, 20)  # Landing skid
        elif self.state == STATE_SUB_CRASH:
            set_pixel(px, py, 255, 100, 30)
            set_pixel(px - 1, py, 255, 40, 20)
            set_pixel(px + 1, py, 255, 40, 20)

        # 9. Oxygen Gauge (Bottom Row 15)
        o2_pixels = int(round((self.oxygen / 100.0) * 15.0))
        for x in range(min(16, o2_pixels + 1)):
            set_pixel(x, 15, 60, 180, 255)

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
            "oxygen": self.oxygen,
            "px": self.px,
            "py": self.py,
            "torpedoes_count": len(self.torpedoes),
            "missiles_count": len(self.vertical_missiles),
        }
