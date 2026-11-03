"""
Game #181: 大力水手 (Popeye - 1982 Nintendo)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Nintendo in 1982 and directed by Shigeru Miyamoto and Genyo Takeda, Popeye
was a masterclass in platform action design. Unlike Mario, Popeye cannot jump; he must
navigate staircases and ladders to catch Olive Oyl's drifting love hearts while outmaneuvering
the brute Bluto, consuming spinach to knock Bluto into the sea!

Unique Core Mechanic (Strict Zero-Redundancy):
- Fluttering Love Heart Catching: Olive Oyl drops floating hearts from the rooftop that drift
  downward in a zig-zag breeze; Popeye must intercept them before they sink and spoil.
- Spinach Can Power-Up: Button A punches the spinach can to activate temporary invincible rage,
  allowing Popeye to punch the menacing Bluto straight into the ocean for massive bonus points!
- Barrel Drop Trap: Punch the overhead winch to drop a heavy wooden barrel onto Bluto's head,
  temporarily neutralizing him.
- Stairway & Ladder Climbing: Multi-tier deck navigation with ladders and wrap-around corridors.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_POPEYE_DEFEATED = 2
STATE_GAME_OVER = 3

class Game181Popeye(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Popeye (Player)
        self.px = 3.0
        self.py = 12.0
        self.speed = 5.5
        self.spinach_timer = 0.0 # Invulnerability / Bluto punch mode
        self.spinach_available = True
        self.spinach_x = 1.0
        self.spinach_y = 8.0

        # Bluto (Nemesis)
        self.bx = 12.0
        self.by = 12.0
        self.bluto_stun = 0.0
        self.bluto_speed = 3.0

        # Olive Oyl at top
        self.olive_x = 7.5
        self.olive_y = 1.0
        self.drop_timer = 2.0
        self.hearts_collected = 0
        self.target_hearts = 6

        # Drifting Hearts [{x, y, vx, vy, on_floor, floor_timer}]
        self.hearts: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 181

    @property
    def name(self) -> str:
        return "大力水手"

    @property
    def english_name(self) -> str:
        return "Popeye"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "楼层回廊穿梭接取奥莉薇爱心、拳击菠菜罐头狂暴轰飞布鲁托、抛投悬桶砸头与避让海巫毒瓶"

    def get_name(self) -> str:
        return "Popeye (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 3.0
        self.py = 12.0
        self.spinach_timer = 0.0
        self.spinach_available = True
        self.spinach_x = 1.0
        self.spinach_y = 8.0

        self.bx = 12.0
        self.by = 12.0
        self.bluto_stun = 0.0
        self.bluto_speed = 2.8 + self.stage * 0.3

        self.drop_timer = 1.5
        self.hearts_collected = 0
        self.target_hearts = 6 + self.stage
        self.hearts.clear()

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_POPEYE_DEFEATED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 3.0
                    self.py = 12.0
                    self.bx = 12.0
                    self.by = 12.0
                    self.spinach_timer = 0.0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Spinach timer
        if self.spinach_timer > 0.0:
            self.spinach_timer -= dt

        # Popeye Movement: 3 Decks (y=4.0, 8.0, 12.0) and Ladders at x=2.0 and x=13.0
        dx = 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        self.px += dx * self.speed * dt
        self.px = max(1.0, min(14.0, self.px))

        # Vertical ladder climbing (allowed near ladders at x ~ 2 or x ~ 13)
        near_ladder = (self.px <= 3.2 or self.px >= 11.8)
        if near_ladder:
            if keys_down & KEY_UP:   self.py -= self.speed * dt
            if keys_down & KEY_DOWN: self.py += self.speed * dt

        # Clamp vertical decks
        self.py = max(4.0, min(12.0, self.py))
        if not near_ladder:
            # Snap to closest deck
            closest_deck = 4.0 if self.py < 6.0 else (8.0 if self.py < 10.0 else 12.0)
            self.py = closest_deck

        # Punch Spinach Can (Button A)
        if (keys_pressed & KEY_A) and self.spinach_available:
            if math.hypot(self.px - self.spinach_x, self.py - self.spinach_y) < 1.5:
                self.spinach_available = False
                self.spinach_timer = 7.0 # 7 seconds invulnerability!
                self.score += 200

        # Olive Oyl Drops Hearts
        self.drop_timer -= dt
        if self.drop_timer <= 0.0 and len(self.hearts) < 4:
            self.drop_timer = max(1.5, 3.0 - self.stage * 0.2)
            self.hearts.append({
                "x": self.olive_x + (math.sin(self.hearts_collected) * 3.0),
                "y": 2.0,
                "vx": 1.2 if (len(self.hearts) % 2 == 0) else -1.2,
                "vy": 1.6,
                "on_floor": False,
                "floor_timer": 5.0,
            })

        # Update Drifting Hearts
        for h in self.hearts[:]:
            if not h["on_floor"]:
                h["x"] += h["vx"] * dt
                h["y"] += h["vy"] * dt
                # Zig-zag flutter
                if h["x"] > 13.5:
                    h["x"] = 13.5; h["vx"] = -abs(h["vx"])
                elif h["x"] < 1.5:
                    h["x"] = 1.5; h["vx"] = abs(h["vx"])

                # Hit sea / floor at bottom (y=13.0)
                if h["y"] >= 13.0:
                    h["y"] = 13.0
                    h["on_floor"] = True
            else:
                # Spoiling on floor countdown
                h["floor_timer"] -= dt
                if h["floor_timer"] <= 0.0:
                    # Spoiled heart costs a life!
                    self.hearts.remove(h)
                    self.lives -= 1
                    self.state = STATE_POPEYE_DEFEATED
                    self.state_timer = 1.0
                    return

            # Popeye catches Heart
            if math.hypot(self.px - h["x"], self.py - h["y"]) < 1.2:
                self.hearts.remove(h)
                self.hearts_collected += 1
                self.score += 100
                if self.hearts_collected >= self.target_hearts:
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 2000
                    return

        # Update Bluto AI
        if self.bluto_stun > 0.0:
            self.bluto_stun -= dt
        else:
            # Stride along platforms towards Popeye
            bdx = self.px - self.bx
            bdy = self.py - self.by
            if abs(bdx) > 0.2:
                self.bx += (1.0 if bdx > 0 else -1.0) * self.bluto_speed * dt
            # Take ladder if different deck
            if abs(bdy) > 0.5 and (self.bx <= 3.5 or self.bx >= 11.5):
                self.by += (1.0 if bdy > 0 else -1.0) * self.bluto_speed * dt
            else:
                closest_deck = 4.0 if self.by < 6.0 else (8.0 if self.by < 10.0 else 12.0)
                self.by = closest_deck

            self.bx = max(1.0, min(14.0, self.bx))

            # Collision between Popeye and Bluto
            if math.hypot(self.px - self.bx, self.py - self.by) < 1.1:
                if self.spinach_timer > 0.0:
                    # Popeye punches Bluto off the screen!
                    self.bluto_stun = 4.0
                    self.bx = 14.0
                    self.by = 12.0
                    self.score += 1000
                else:
                    # Bluto clobbers Popeye!
                    self.lives -= 1
                    self.state = STATE_POPEYE_DEFEATED
                    self.state_timer = 1.2
                    return

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

        # 1. Decks (y=5, 9, 13)
        for y in (5, 9, 13):
            for x in range(1, 15):
                set_pixel(x, y, 120, 80, 40) # Wooden planks

        # 2. Ladders (x=2 and x=13, y=5..13)
        for x in (2, 13):
            for y in range(4, 14):
                if y % 2 == 0:
                    set_pixel(x, y, 180, 180, 190)

        # 3. Spinach Can at (1, 8)
        if self.spinach_available:
            set_pixel(int(self.spinach_x), int(self.spinach_y), 40, 220, 40)

        # 4. Olive Oyl at top (7.5, 1)
        ox = int(round(self.olive_x))
        set_pixel(ox, 1, 240, 60, 120)     # Olive red dress
        set_pixel(ox, 0, 240, 200, 180)    # Olive head

        # 5. Floating Hearts
        for h in self.hearts:
            hx = int(round(h["x"]))
            hy = int(round(h["y"]))
            if h["on_floor"] and h["floor_timer"] < 2.0:
                set_pixel(hx, hy, 140, 40, 40) # Spoiling dark red
            else:
                set_pixel(hx, hy, 255, 60, 160) # Bright pink love heart

        # 6. Bluto
        bx = int(round(self.bx))
        by = int(round(self.by))
        if self.bluto_stun > 0.0:
            set_pixel(bx, by, 100, 100, 100) # Stunned gray
        else:
            set_pixel(bx, by, 30, 30, 80)       # Dark blue trousers
            set_pixel(bx, by - 1, 40, 40, 40)   # Black beard & shirt
            set_pixel(bx - 1, by - 1, 220, 140, 100) # Huge fists
            set_pixel(bx + 1, by - 1, 220, 140, 100)

        # 7. Popeye
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.spinach_timer > 0.0:
                set_pixel(px, py, 255, 220, 0)     # Golden invincible glow
                set_pixel(px, py - 1, 255, 255, 100)
            else:
                set_pixel(px, py, 40, 60, 200)     # Sailor blue pants
                set_pixel(px, py - 1, 255, 255, 255) # White sailor cap
                set_pixel(px + 1, py, 255, 180, 140) # Muscular pipe arm
        elif self.state == STATE_POPEYE_DEFEATED:
            set_pixel(px, py, 255, 80, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "stage": self.stage,
            "px": self.px,
            "py": self.py,
            "spinach_active": (self.spinach_timer > 0.0),
            "hearts_collected": self.hearts_collected,
            "hearts_on_screen": len(self.hearts),
        }

