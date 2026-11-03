# -*- coding: utf-8 -*-
"""
Game #153: 马戏团 (Circus Charlie 1984 / Konami)
街机历史上最经典的马戏特技杂技与火圈跳跃传世名作：
骑乘驯狮纵马奔腾控速进退、精准起跳跨越地表火盆与移动烈火双环、
凌空穿透小火圈夺取悬空金币钱袋、飞跃登顶马戏团终点领奖台。
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
STATE_CHARLIE_DOWN = 2
STATE_GAME_OVER = 3

COURSE_LENGTH = 85.0
GROUND_Y = 13.0


class Game153CircusCharlie(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        # Lion & Charlie position
        self.track_pos = 0.0
        self.y = GROUND_Y
        self.vy = 0.0
        self.is_jumping = False

        # Fire pots (stationary on ground)
        self.fire_pots: List[float] = []

        # Fire hoops (moving left along track)
        self.fire_hoops: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 153

    @property
    def name(self) -> str:
        return "马戏团"

    @property
    def english_name(self) -> str:
        return "Circus Charlie"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "驯狮奔腾控速勒缰进退、跃过烈焰火圈与火盆、凌空穿心叼取钱袋并精准登顶马戏领奖台"

    def get_name(self) -> str:
        return "Circus Charlie (1984)"

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
        self.track_pos = 0.0
        self.y = GROUND_Y
        self.vy = 0.0
        self.is_jumping = False

        # Fire pots at fixed track locations
        self.fire_pots = [16.0, 32.0, 48.0, 64.0]

        # Fire hoops: position along track, with height, size, money bag
        self.fire_hoops = [
            {"track_pos": 10.0, "speed": 1.2, "has_money": True, "money_taken": False},
            {"track_pos": 24.0, "speed": 1.5, "has_money": False, "money_taken": False},
            {"track_pos": 40.0, "speed": 1.2, "has_money": True, "money_taken": False},
            {"track_pos": 56.0, "speed": 1.6, "has_money": False, "money_taken": False},
            {"track_pos": 72.0, "speed": 1.4, "has_money": True, "money_taken": False},
        ]

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_CHARLIE_DOWN):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_CHARLIE_DOWN:
                    if self.lives > 0:
                        # Respawn slightly back on track
                        self.track_pos = max(0.0, self.track_pos - 6.0)
                        self.y = GROUND_Y
                        self.vy = 0.0
                        self.is_jumping = False
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
        # 1. Lion Gallop & Reins Control
        gallop_speed = 3.2
        if buttons & KEY_LEFT:
            gallop_speed = -1.2  # Pull back reins!
        elif buttons & KEY_RIGHT:
            gallop_speed = 5.2   # Gallop forward at high speed!

        self.track_pos += gallop_speed * dt
        self.track_pos = max(0.0, min(COURSE_LENGTH, self.track_pos))

        # 2. Leaping / Jumping: Key A or Key UP
        if ((buttons & (KEY_A | KEY_UP)) and not (prev_buttons & (KEY_A | KEY_UP))) or \
           ((buttons & KEY_A) and not self.is_jumping):
            self.vy = -6.4
            self.is_jumping = True

        # Apply gravity
        if self.is_jumping:
            self.vy += 13.0 * dt
            self.y += self.vy * dt
            if self.y >= GROUND_Y:
                self.y = GROUND_Y
                self.vy = 0.0
                self.is_jumping = False

        # 3. Update Fire Hoops (moving toward Charlie)
        for h in self.fire_hoops:
            h["track_pos"] -= h["speed"] * dt
            # Re-spawn hoop further right if it travels behind Charlie
            if h["track_pos"] < self.track_pos - 10.0:
                h["track_pos"] = self.track_pos + 18.0
                h["money_taken"] = False

        # 4. Check Fire Pot Collisions (stationary on ground)
        for pot_pos in self.fire_pots:
            dist = abs(self.track_pos - pot_pos)
            # If Charlie is on ground and overlapping pot
            if dist < 1.0 and self.y > GROUND_Y - 1.2:
                self._lose_life()
                return

        # 5. Check Fire Hoop Collisions & Money Bag Catch
        for h in self.fire_hoops:
            dist = abs(self.track_pos - h["track_pos"])
            if dist < 0.9:
                # If Charlie is jumping through the center (y in [9.5, 11.5])
                if 9.0 <= self.y <= 12.0:
                    # Clean leap through hoop!
                    if h["has_money"] and not h["money_taken"]:
                        h["money_taken"] = True
                        self.score += 500  # Bonus money bag!
                    else:
                        self.score += 10
                else:
                    # Caught on the fiery ring rim!
                    self._lose_life()
                    return

        # 6. Check Podium Finish
        if self.track_pos >= COURSE_LENGTH - 1.5:
            self.score += 2000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_CHARLIE_DOWN
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

        screen_charlie_x = 4  # Fixed horizontal screen anchor for Charlie

        # 1. Circus Tent Background Wall & Sawdust Floor
        for x in range(16):
            set_pixel(x, 14, 210, 160, 60)   # Sawdust arena track
            set_pixel(x, 15, 120, 80, 30)

        # 2. Audience Tents / Bunting at top
        for x in range(16):
            if x % 2 == 0:
                set_pixel(x, 1, 220, 40, 40)
            else:
                set_pixel(x, 1, 240, 240, 240)

        # 3. Victory Podium at end of track
        podium_screen_x = int(round(screen_charlie_x + (COURSE_LENGTH - self.track_pos)))
        if 0 <= podium_screen_x < 16:
            set_pixel(podium_screen_x, 13, 60, 180, 255)
            set_pixel(podium_screen_x, 12, 255, 220, 40)

        # 4. Fire Pots (Red/Yellow flames in cauldron)
        for pot_pos in self.fire_pots:
            sx = int(round(screen_charlie_x + (pot_pos - self.track_pos)))
            if 0 <= sx < 16:
                set_pixel(sx, 13, 60, 60, 60)   # Pot
                set_pixel(sx, 12, 255, 60, 20)  # Fire
                set_pixel(sx, 11, 255, 200, 30)

        # 5. Fire Hoops (Fiery Ovals)
        for h in self.fire_hoops:
            sx = int(round(screen_charlie_x + (h["track_pos"] - self.track_pos)))
            if 0 <= sx < 16:
                set_pixel(sx, 13, 255, 40, 20)
                set_pixel(sx, 9, 255, 40, 20)
                set_pixel(sx - 1, 11, 255, 140, 30)
                set_pixel(sx + 1, 11, 255, 140, 30)
                # Money Bag in center
                if h["has_money"] and not h["money_taken"]:
                    set_pixel(sx, 11, 255, 230, 40)

        # 6. Charlie riding the Lion
        cx = screen_charlie_x
        cy = int(round(self.y))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            # Lion (Tawny Orange Body & Mane)
            set_pixel(cx, cy, 230, 140, 30)
            set_pixel(cx + 1, cy, 230, 140, 30)  # Lion head
            set_pixel(cx - 1, cy, 180, 100, 20)  # Tail/hind
            # Charlie (Red/White Circus Clown acrobat on top)
            set_pixel(cx, cy - 1, 40, 120, 255)  # Charlie body
            set_pixel(cx, cy - 2, 255, 230, 200) # Face / hat
        elif self.state == STATE_CHARLIE_DOWN:
            set_pixel(cx, cy, 255, 40, 20)

        # 7. Progress Bar / Lives
        prog_dots = int((self.track_pos / COURSE_LENGTH) * 8)
        for i in range(prog_dots):
            set_pixel(8 + i, 0, 40, 220, 120)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 240, 60, 60)

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
            "track_pos": self.track_pos,
            "y": self.y,
            "is_jumping": self.is_jumping,
        }

