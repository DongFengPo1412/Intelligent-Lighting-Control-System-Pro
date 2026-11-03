# -*- coding: utf-8 -*-
"""
Game #151: 空间地牢 (Space Dungeon 1981 / Taito & Rex Battenberg)
街机历史上首款双摇杆多房间地牢探索与战利品撤离开山鼻祖：
穿梭3x3九宫格星际地牢各舱室收集稀世财宝放入背包、
阻击游荡神偷抢夺宝物、规避尖刺无人机并将战利品运抵升降机舱结算撤离。
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


class Game151SpaceDungeon(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        # Current room coordinates in 3x3 grid (0..2, 0..2)
        self.rx = 1
        self.ry = 1

        # Player ship
        self.px = 7.5
        self.py = 7.5
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.treasures_carried = 0
        self.treasures_banked = 0

        # Projectiles
        self.lasers: List[Dict[str, Any]] = []

        # Room treasures: keyed by (rx, ry) -> list of {"x": float, "y": float, "collected": bool}
        self.room_treasures: Dict[str, List[Dict[str, Any]]] = {}

        # Room enemies: keyed by (rx, ry) -> list of {"x": float, "y": float, "vx": float, "vy": float, "alive": bool}
        self.room_enemies: Dict[str, List[Dict[str, Any]]] = {}

        # Thief state
        self.thief: Optional[Dict[str, Any]] = None

        self.reset()

    @property
    def game_id(self) -> int:
        return 151

    @property
    def name(self) -> str:
        return "空间地牢"

    @property
    def english_name(self) -> str:
        return "Space Dungeon"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多房间地牢穿梭寻宝、背包负重物资收集、防范游荡神偷盗窃财宝并前往升降舱结算逃生"

    def get_name(self) -> str:
        return "Space Dungeon (1981)"

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
        self.rx = 1
        self.ry = 1
        self.px = 7.5
        self.py = 7.5
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.treasures_carried = 0
        self.treasures_banked = 0
        self.lasers.clear()

        # Initialize treasures and enemies across 3x3 rooms
        self.room_treasures.clear()
        self.room_enemies.clear()

        for gy in range(3):
            for gx in range(3):
                key = f"{gx}_{gy}"
                # Collect-o-matic room is at (2, 2)
                if gx == 2 and gy == 2:
                    self.room_treasures[key] = []
                    self.room_enemies[key] = []
                    continue

                # Normal room has 1 or 2 treasures
                t_list = []
                t_list.append({"x": 4.0, "y": 4.0, "collected": False})
                if (gx + gy) % 2 == 1:
                    t_list.append({"x": 11.0, "y": 11.0, "collected": False})
                self.room_treasures[key] = t_list

                # Normal room has 2 patrolling drones
                e_list = [
                    {"x": 4.0, "y": 11.0, "vx": 2.0, "vy": 1.5, "alive": True},
                    {"x": 11.0, "y": 4.0, "vx": -1.8, "vy": 2.2, "alive": True},
                ]
                self.room_enemies[key] = e_list

        # Thief at room (0, 0)
        self.thief = {
            "rx": 0, "ry": 0, "x": 7.5, "y": 7.5, "vx": 2.5, "vy": 0.0,
            "stolen_loot": 0, "alive": True, "cooldown": 0.0
        }

    def _get_current_key(self) -> str:
        return f"{self.rx}_{self.ry}"

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
                        self.py = 7.5
                        self.lasers.clear()
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
        # 1. Player Navigation & Facing
        speed = 5.5
        dx = 0.0
        dy = 0.0
        if buttons & KEY_LEFT:
            dx -= speed
            self.facing_x = -1.0
            self.facing_y = 0.0
        elif buttons & KEY_RIGHT:
            dx += speed
            self.facing_x = 1.0
            self.facing_y = 0.0
        elif buttons & KEY_UP:
            dy -= speed
            self.facing_x = 0.0
            self.facing_y = -1.0
        elif buttons & KEY_DOWN:
            dy += speed
            self.facing_x = 0.0
            self.facing_y = 1.0

        self.px += dx * dt
        self.py += dy * dt

        # 2. Doorway Room Transitions
        # Top Door (x in [6.5, 8.5], y <= 0.5)
        if self.py <= 0.5:
            if 6.0 <= self.px <= 9.0 and self.ry > 0:
                self.ry -= 1
                self.py = 14.5
            else:
                self.py = 1.2
        # Bottom Door
        elif self.py >= 14.5:
            if 6.0 <= self.px <= 9.0 and self.ry < 2:
                self.ry += 1
                self.py = 1.2
            else:
                self.py = 14.2
        # Left Door
        if self.px <= 0.5:
            if 6.0 <= self.py <= 9.0 and self.rx > 0:
                self.rx -= 1
                self.px = 14.5
            else:
                self.px = 1.2
        # Right Door
        elif self.px >= 14.5:
            if 6.0 <= self.py <= 9.0 and self.rx < 2:
                self.rx += 1
                self.px = 1.2
            else:
                self.px = 14.2

        # 3. Fire Laser: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.lasers) < 5:
                self.lasers.append({
                    "x": self.px + self.facing_x * 0.8,
                    "y": self.py + self.facing_y * 0.8,
                    "vx": self.facing_x * 14.0,
                    "vy": self.facing_y * 14.0,
                })

        # 4. Update Lasers
        for l in self.lasers:
            l["x"] += l["vx"] * dt
            l["y"] += l["vy"] * dt

        # Check laser hits with current room enemies
        cur_key = self._get_current_key()
        cur_enemies = self.room_enemies.get(cur_key, [])
        for l in self.lasers:
            for e in cur_enemies:
                if e["alive"]:
                    if abs(l["x"] - e["x"]) < 1.0 and abs(l["y"] - e["y"]) < 1.0:
                        e["alive"] = False
                        l["x"] = -100.0  # de-spawn laser
                        self.score += 150
                        break

            # Check laser hit with thief
            if self.thief and self.thief["alive"] and self.thief["rx"] == self.rx and self.thief["ry"] == self.ry:
                if abs(l["x"] - self.thief["x"]) < 1.0 and abs(l["y"] - self.thief["y"]) < 1.0:
                    self.thief["alive"] = False
                    l["x"] = -100.0
                    self.score += 500
                    # Drop stolen loot
                    for _ in range(self.thief["stolen_loot"]):
                        self.room_treasures[cur_key].append({
                            "x": self.thief["x"], "y": self.thief["y"], "collected": False
                        })
                    self.thief["stolen_loot"] = 0

        self.lasers = [l for l in self.lasers if 0.5 <= l["x"] <= 14.5 and 0.5 <= l["y"] <= 14.5]

        # 5. Collect-o-matic Elevator Room Check (Room 2, 2)
        if self.rx == 2 and self.ry == 2:
            # Elevator pad at center (7.5, 7.5)
            if abs(self.px - 7.5) < 1.8 and abs(self.py - 7.5) < 1.8:
                if self.treasures_carried > 0:
                    self.score += self.treasures_carried * 500
                    self.treasures_banked += self.treasures_carried
                    self.treasures_carried = 0

                # If banked >= 4 treasures, stage clear escape!
                if self.treasures_banked >= 4:
                    self.score += 2000
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 0.0
                    return

        # 6. Treasure pickups in current room
        cur_treasures = self.room_treasures.get(cur_key, [])
        for t in cur_treasures:
            if not t["collected"]:
                if abs(self.px - t["x"]) < 1.0 and abs(self.py - t["y"]) < 1.0:
                    t["collected"] = True
                    self.treasures_carried += 1
                    self.score += 100

        # 7. Update Room Enemies
        for e in cur_enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["x"] <= 1.5 or e["x"] >= 13.5:
                e["vx"] = -e["vx"]
            if e["y"] <= 1.5 or e["y"] >= 13.5:
                e["vy"] = -e["vy"]

            # Enemy touches player
            if abs(self.px - e["x"]) < 0.9 and abs(self.py - e["y"]) < 0.9:
                self._lose_life()
                return

        # 8. Update Roaming Thief AI
        if self.thief and self.thief["alive"]:
            if self.thief["rx"] == self.rx and self.thief["ry"] == self.ry:
                # In current room: seek nearest treasure or steal from player
                self.thief["x"] += self.thief["vx"] * dt
                self.thief["y"] += self.thief["vy"] * dt
                if self.thief["x"] <= 1.5 or self.thief["x"] >= 13.5:
                    self.thief["vx"] = -self.thief["vx"]

                # Thief touches player -> pickpockets 1 carried treasure!
                if self.treasures_carried > 0:
                    if abs(self.px - self.thief["x"]) < 1.0 and abs(self.py - self.thief["y"]) < 1.0:
                        self.treasures_carried -= 1
                        self.thief["stolen_loot"] += 1
                        # Thief scampers away
                        self.thief["vx"] = 4.0 if self.px < 7.5 else -4.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_PLAYER_HIT
        self.state_timer = 0.0

        # Drop carried treasures on death
        cur_key = self._get_current_key()
        for i in range(self.treasures_carried):
            ox = (i % 2) * 1.5 - 0.75
            self.room_treasures[cur_key].append({
                "x": max(2.0, min(13.0, self.px + ox)),
                "y": max(2.0, min(13.0, self.py)),
                "collected": False
            })
        self.treasures_carried = 0

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

        # 1. Chamber Walls with 4 door openings
        for x in range(16):
            if not (6 <= x <= 9 and self.ry > 0):
                set_pixel(x, 0, 70, 70, 90)
            if not (6 <= x <= 9 and self.ry < 2):
                set_pixel(x, 15, 70, 70, 90)
        for y in range(16):
            if not (6 <= y <= 9 and self.rx > 0):
                set_pixel(0, y, 70, 70, 90)
            if not (6 <= y <= 9 and self.rx < 2):
                set_pixel(15, y, 70, 70, 90)

        # 2. Collect-o-matic Elevator Pad in Room (2, 2)
        if self.rx == 2 and self.ry == 2:
            for ey in range(6, 10):
                for ex in range(6, 10):
                    set_pixel(ex, ey, 220, 200, 40)
            set_pixel(7, 7, 255, 255, 255)
            set_pixel(8, 8, 255, 255, 255)

        # 3. Treasures in current room (Sparkling Golden Chalices/Chests)
        cur_key = self._get_current_key()
        for t in self.room_treasures.get(cur_key, []):
            if not t["collected"]:
                tx = int(round(t["x"]))
                ty = int(round(t["y"]))
                set_pixel(tx, ty, 255, 215, 0)
                set_pixel(tx, ty - 1, 255, 240, 100)

        # 4. Roaming Thief (Green sneaky sprite)
        if self.thief and self.thief["alive"] and self.thief["rx"] == self.rx and self.thief["ry"] == self.ry:
            thx = int(round(self.thief["x"]))
            thy = int(round(self.thief["y"]))
            set_pixel(thx, thy, 50, 220, 60)
            set_pixel(thx, thy - 1, 30, 160, 40)

        # 5. Enemies (Red Spikers)
        for e in self.room_enemies.get(cur_key, []):
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                set_pixel(ex, ey, 255, 50, 50)
                set_pixel(ex - 1, ey, 200, 30, 30)
                set_pixel(ex + 1, ey, 200, 30, 30)

        # 6. Lasers
        for l in self.lasers:
            lx = int(round(l["x"]))
            ly = int(round(l["y"]))
            set_pixel(lx, ly, 100, 230, 255)

        # 7. Player Ship (Cyan / Yellow Fighter)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 40, 180, 255)
            # Nose in facing direction
            fx = int(round(px + self.facing_x))
            fy = int(round(py + self.facing_y))
            set_pixel(fx, fy, 255, 220, 40)
        elif self.state == STATE_PLAYER_HIT:
            set_pixel(px, py, 255, 80, 40)

        # 8. Mini-map & Inventory in top row
        # Mini-map 3x3 indicator at top-left
        set_pixel(self.rx, self.ry, 255, 255, 255)

        # Carried treasures dots
        for c in range(min(self.treasures_carried, 4)):
            set_pixel(11 + c, 0, 255, 215, 0)

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
            "rx": self.rx,
            "ry": self.ry,
            "px": self.px,
            "py": self.py,
            "treasures_carried": self.treasures_carried,
            "treasures_banked": self.treasures_banked,
        }

