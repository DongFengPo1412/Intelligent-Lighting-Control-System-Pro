# -*- coding: utf-8 -*-
"""
Game #159: 间谍大战 (Spy vs Spy 1984 / First Star & Sega Arcade)
街机与家用机历史上最负盛名的双雄谍战与机关陷阱暗算开山名作：
穿梭使馆多房间搜寻文件柜与壁画保密箱、集齐护照美钞钥匙机密文件与公文包、
在家具暗藏炸药弹簧陷阱阴击宿敌黑间谍、突破封锁赶赴机场大门登机撤离。
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
STATE_SPY_BLOWN_UP = 2
STATE_GAME_OVER = 3


class Game159SpyVsSpy(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        # Current room of White Spy (0..1, 0..1)
        self.rx = 0
        self.ry = 0
        self.px = 7.5
        self.py = 7.5
        self.facing_x = 0.0
        self.facing_y = 1.0

        # Inventory
        self.has_briefcase = False
        self.items_found = set()  # "plans", "passport", "money", "key"

        # Furniture & Hidden items: key by room "(rx, ry)" -> list of furniture
        # {"id": str, "x": float, "y": float, "item": Optional[str], "trap": Optional[str], "searched": bool}
        self.furniture: Dict[str, List[Dict[str, Any]]] = {}

        # Rival Black Spy AI
        self.rival_rx = 1
        self.rival_ry = 1
        self.rival_x = 7.5
        self.rival_y = 7.5
        self.rival_alive = True
        self.rival_respawn_timer = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 159

    @property
    def name(self) -> str:
        return "间谍大战"

    @property
    def english_name(self) -> str:
        return "Spy vs Spy"

    @property
    def release_year(self) -> 1984:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "使馆多房间密道穿梭、搜寻家具翻找护照机密公文包、布置定时炸弹弹簧陷阱阴敌与登机逃生"

    def get_name(self) -> str:
        return "Spy vs Spy (1984)"

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
        self.rx = 0
        self.ry = 0
        self.px = 7.5
        self.py = 7.5
        self.facing_x = 0.0
        self.facing_y = 1.0

        self.has_briefcase = False
        self.items_found = set()

        # Distribute 4 items + briefcase across rooms
        # Room (0, 0): Briefcase in desk, Money in coat rack
        # Room (1, 0): Passport in safe
        # Room (0, 1): Plans in file cabinet
        # Room (1, 1): Key in table, Airport Gate
        self.furniture = {
            "0_0": [
                {"name": "desk", "x": 4.0, "y": 5.0, "item": "briefcase", "trap": None, "searched": False},
                {"name": "coat", "x": 11.0, "y": 11.0, "item": "money", "trap": None, "searched": False},
            ],
            "1_0": [
                {"name": "safe", "x": 11.0, "y": 5.0, "item": "passport", "trap": None, "searched": False},
                {"name": "table", "x": 4.0, "y": 11.0, "item": None, "trap": None, "searched": False},
            ],
            "0_1": [
                {"name": "cabinet", "x": 4.0, "y": 5.0, "item": "plans", "trap": None, "searched": False},
                {"name": "painting", "x": 11.0, "y": 11.0, "item": None, "trap": None, "searched": False},
            ],
            "1_1": [
                {"name": "box", "x": 4.0, "y": 5.0, "item": "key", "trap": None, "searched": False},
                # Airport Exit is at (11.0, 11.0)
            ],
        }

        self.rival_rx = 1
        self.rival_ry = 0
        self.rival_x = 7.5
        self.rival_y = 7.5
        self.rival_alive = True
        self.rival_respawn_timer = 0.0

    def _get_current_key(self) -> str:
        return f"{self.rx}_{self.ry}"

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_SPY_BLOWN_UP):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_SPY_BLOWN_UP:
                    if self.lives > 0:
                        self.px = 7.5
                        self.py = 7.5
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
        # 1. White Spy Navigation
        speed = 5.0
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

        # 2. Doorways between 2x2 Rooms
        # Top Door
        if self.py <= 0.8:
            if 6.0 <= self.px <= 9.0 and self.ry > 0:
                self.ry -= 1
                self.py = 14.2
            else:
                self.py = 1.5
        # Bottom Door
        elif self.py >= 14.5:
            if 6.0 <= self.px <= 9.0 and self.ry < 1:
                self.ry += 1
                self.py = 1.5
            else:
                self.py = 14.0
        # Left Door
        if self.px <= 0.8:
            if 6.0 <= self.py <= 9.0 and self.rx > 0:
                self.rx -= 1
                self.px = 14.2
            else:
                self.px = 1.5
        # Right Door
        elif self.px >= 14.5:
            if 6.0 <= self.py <= 9.0 and self.rx < 1:
                self.rx += 1
                self.px = 1.5
            else:
                self.px = 14.0

        # 3. Search Furniture: Key A
        cur_key = self._get_current_key()
        cur_furn = self.furniture.get(cur_key, [])

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            # Check airport door in room (1, 1)
            if self.rx == 1 and self.ry == 1:
                if abs(self.px - 12.0) < 1.8 and abs(self.py - 12.0) < 1.8:
                    if self.has_briefcase and len(self.items_found) >= 4:
                        self.score += 3000
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 0.0
                        return

            # Check furniture search
            for f in cur_furn:
                if abs(self.px - f["x"]) < 1.4 and abs(self.py - f["y"]) < 1.4:
                    # Check if trapped!
                    if f["trap"] == "bomb":
                        f["trap"] = None
                        self._lose_life()
                        return

                    # Search item
                    if not f["searched"]:
                        f["searched"] = True
                        if f["item"] == "briefcase":
                            self.has_briefcase = True
                            self.score += 500
                        elif f["item"] in ("plans", "passport", "money", "key"):
                            self.items_found.add(f["item"])
                            self.score += 250
                    break

        # 4. Lay Booby Trap: Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            for f in cur_furn:
                if abs(self.px - f["x"]) < 1.4 and abs(self.py - f["y"]) < 1.4:
                    if f["trap"] is None:
                        f["trap"] = "bomb"
                        self.score += 100
                    break

        # 5. Black Spy AI
        if not self.rival_alive:
            self.rival_respawn_timer -= dt
            if self.rival_respawn_timer <= 0.0:
                self.rival_alive = True
                self.rival_rx = (self.rx + 1) % 2
                self.rival_ry = (self.ry + 1) % 2
                self.rival_x = 7.5
                self.rival_y = 7.5

        if self.rival_alive:
            # If in current room: fight player or search furniture
            if self.rival_rx == self.rx and self.rival_ry == self.ry:
                # Approach player or furniture
                rdx = self.px - self.rival_x
                rdy = self.py - self.rival_y
                dist = math.hypot(rdx, rdy)
                if dist > 0.8:
                    self.rival_x += (rdx / dist) * 2.8 * dt
                    self.rival_y += (rdy / dist) * 2.8 * dt

                # Check if Black Spy opens a trapped furniture
                for f in cur_furn:
                    if abs(self.rival_x - f["x"]) < 1.2 and abs(self.rival_y - f["y"]) < 1.2:
                        if f["trap"] == "bomb":
                            f["trap"] = None
                            self.rival_alive = False
                            self.rival_respawn_timer = 3.0
                            self.score += 1000
                            break

                # Melee combat with player
                if dist < 0.9:
                    if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                        # Player punches rival!
                        self.rival_alive = False
                        self.rival_respawn_timer = 3.0
                        self.score += 500

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_SPY_BLOWN_UP
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

        # 1. Embassy Room Walls & Door Openings
        for x in range(16):
            if not (6 <= x <= 9 and self.ry > 0): set_pixel(x, 0, 90, 80, 110)
            if not (6 <= x <= 9 and self.ry < 1): set_pixel(x, 15, 90, 80, 110)
        for y in range(16):
            if not (6 <= y <= 9 and self.rx > 0): set_pixel(0, y, 90, 80, 110)
            if not (6 <= y <= 9 and self.rx < 1): set_pixel(15, y, 90, 80, 110)

        # 2. Airport Gate in Room (1, 1)
        if self.rx == 1 and self.ry == 1:
            set_pixel(12, 12, 60, 200, 255)
            set_pixel(12, 11, 240, 240, 40)
            set_pixel(13, 12, 60, 200, 255)

        # 3. Furniture
        cur_key = self._get_current_key()
        for f in self.furniture.get(cur_key, []):
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            # Furniture base
            set_pixel(fx, fy, 160, 100, 50)
            set_pixel(fx + 1, fy, 160, 100, 50)
            set_pixel(fx, fy - 1, 130, 80, 40)
            if f["trap"] == "bomb":
                # Subtle red wire indicator
                set_pixel(fx + 1, fy - 1, 255, 40, 40)

        # 4. Black Spy (Rival: Black trenchcoat, pointed hat)
        if self.rival_alive and self.rival_rx == self.rx and self.rival_ry == self.ry:
            rx = int(round(self.rival_x))
            ry = int(round(self.rival_y))
            set_pixel(rx, ry, 30, 30, 30)          # Black coat
            set_pixel(rx, ry - 1, 240, 200, 160)  # Face
            set_pixel(rx, ry - 2, 20, 20, 20)     # Pointed hat

        # 5. White Spy (Player: White trenchcoat, long pointed nose)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 240, 240, 240)      # White coat
            set_pixel(px, py - 1, 240, 200, 160)  # Face
            set_pixel(px, py - 2, 230, 230, 230)  # Hat
            if self.has_briefcase:
                set_pixel(px + 1, py, 140, 70, 30) # Holding briefcase
        elif self.state == STATE_SPY_BLOWN_UP:
            set_pixel(px, py, 255, 60, 30)

        # 6. Inventory Icons in top row
        if self.has_briefcase:
            set_pixel(0, 0, 140, 70, 30)
        items_list = ["plans", "passport", "money", "key"]
        for i, item in enumerate(items_list):
            if item in self.items_found:
                set_pixel(2 + i, 0, 40, 220, 120)

        for l in range(min(self.lives, 3)):
            set_pixel(15 - l * 2, 0, 240, 240, 240)

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
            "has_briefcase": self.has_briefcase,
            "items_count": len(self.items_found),
        }
