"""
Game #175: 创战纪飞盘决斗 (Discs of Tron - 1983 Bally Midway)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Bally Midway in 1983, Discs of Tron captured the climactic gladiator disc
arena duel from Disney's 1982 film TRON. Standing on floating energy ring platforms
suspended in a deep void, Flynn battles Commander Sark in high-velocity ricocheting
disc combat with energy shields and environmental deflection walls.

Unique Core Mechanic (Strict Zero-Redundancy):
- Kinetic Ricocheting Energy Discs: Throw holographic discs that ricochet off side deflection walls
  at precise reflection angles to bypass Sark's defenses.
- Deployable Deflection Shield: Button B raises Flynn's personal energy shield to bounce Sark's
  incoming lethal discs right back at him with accelerated velocity!
- Mid-Air Disc Clashes: Player and boss discs can collide in mid-air, causing mutual deflection.
- Platform Knock-Off Victory: Strike Commander Sark 3 times to knock him off the elevated ring
  into the MCP bottomless grid chasm!
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
STATE_SARK_FALLING = 1
STATE_PLAYER_DIED = 2
STATE_GAME_OVER = 3

class Game175DiscsOfTron(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Flynn (Player)
        self.px = 7.5
        self.py = 13.0
        self.speed = 6.5
        self.shield_active = False
        self.shield_energy = 100.0 # Drain while held, recharge when idle

        # Sark (Opponent)
        self.sx = 7.5
        self.sy = 2.5
        self.sark_hp = 3
        self.sark_dir = 1.0
        self.sark_speed = 3.0
        self.sark_throw_timer = 1.5

        # Discs: list of {x, y, vx, vy, is_player, active}
        self.discs: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 175

    @property
    def name(self) -> str:
        return "创战纪飞盘决斗"

    @property
    def english_name(self) -> str:
        return "Discs of Tron"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "悬空光环平台对决、多重边界反弹回旋能量飞盘、按键激活能量偏转护盾与打落萨克坠入深渊"

    def get_name(self) -> str:
        return "Discs of Tron (1983)"

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
        self.px = 7.5
        self.py = 13.0
        self.shield_active = False
        self.shield_energy = 100.0

        self.sx = 7.5
        self.sy = 2.5
        self.sark_hp = 3
        self.sark_dir = 1.0
        self.sark_speed = 3.0 + self.stage * 0.4
        self.sark_throw_timer = 1.2

        self.discs.clear()

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_SARK_FALLING:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_PLAYER_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.0
                    self.shield_active = False
                    self.discs.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Movement on Floating Ring
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            self.px += dx * self.speed * dt
            self.py += dy * self.speed * dt

        # Constrain to player's lower disc platform ring
        self.px = max(2.5, min(12.5, self.px))
        self.py = max(10.5, min(14.0, self.py))

        # Deflection Shield (Button B)
        if (keys_down & KEY_B) and self.shield_energy > 0.0:
            self.shield_active = True
            self.shield_energy = max(0.0, self.shield_energy - 35.0 * dt)
        else:
            self.shield_active = False
            self.shield_energy = min(100.0, self.shield_energy + 20.0 * dt)

        # Throw Energy Disc (Button A)
        player_discs_active = sum(1 for d in self.discs if d["is_player"])
        if (keys_pressed & KEY_A) and player_discs_active < 2:
            # Angle disc based on player position/motion
            vx = 4.0 if self.px < 7.5 else -4.0
            if dx != 0.0:
                vx = dx * 6.0
            vy = -12.0
            self.discs.append({
                "x": self.px,
                "y": self.py - 1.0,
                "vx": vx,
                "vy": vy,
                "is_player": True,
            })

        # Sark AI & Disc Throws
        self.sx += self.sark_dir * self.sark_speed * dt
        if self.sx > 12.0:
            self.sx = 12.0
            self.sark_dir = -1.0
        elif self.sx < 3.0:
            self.sx = 3.0
            self.sark_dir = 1.0

        self.sark_throw_timer -= dt
        if self.sark_throw_timer <= 0.0:
            self.sark_throw_timer = max(0.8, 1.8 - self.stage * 0.15)
            # Throw disc aiming towards Flynn or deflection wall
            sark_vx = (self.px - self.sx) * 0.8
            self.discs.append({
                "x": self.sx,
                "y": self.sy + 1.0,
                "vx": sark_vx,
                "vy": 8.0 + self.stage * 0.5,
                "is_player": False,
            })

        # Update Discs Physics & Ricochet
        for d in self.discs[:]:
            d["x"] += d["vx"] * dt
            d["y"] += d["vy"] * dt

            # Side Wall Ricochet (left at x=1.5, right at x=13.5)
            if d["x"] <= 1.5:
                d["x"] = 1.5
                d["vx"] = abs(d["vx"])
            elif d["x"] >= 13.5:
                d["x"] = 13.5
                d["vx"] = -abs(d["vx"])

            # Boundary Despawn (top or bottom out of arena)
            if d["y"] < 0.5 or d["y"] > 15.5:
                if d in self.discs:
                    self.discs.remove(d)
                continue

            # Player Disc hits Sark
            if d["is_player"]:
                if math.hypot(d["x"] - self.sx, d["y"] - self.sy) < 1.1:
                    if d in self.discs:
                        self.discs.remove(d)
                    self.sark_hp -= 1
                    self.score += 500
                    if self.sark_hp <= 0:
                        # Sark knocked off platform!
                        self.state = STATE_SARK_FALLING
                        self.state_timer = 2.0
                        self.score += 3000
                        return
                    continue

            # Sark Disc approaches Flynn
            else:
                if math.hypot(d["x"] - self.px, d["y"] - self.py) < 1.2:
                    if self.shield_active:
                        # Deflection shield reflects Sark's disc back towards Sark!
                        d["is_player"] = True
                        d["vy"] = -abs(d["vy"]) * 1.2 # Accelerate reflection!
                        d["vx"] = -d["vx"]
                        self.score += 250
                    else:
                        # Flynn hit by disc!
                        self.lives -= 1
                        self.state = STATE_PLAYER_DIED
                        self.state_timer = 1.0
                        return

        # Mid-air disc clashes
        for i in range(len(self.discs)):
            for j in range(i + 1, len(self.discs)):
                d1 = self.discs[i]
                d2 = self.discs[j]
                if math.hypot(d1["x"] - d2["x"], d1["y"] - d2["y"]) < 0.8:
                    # Mutual deflection
                    d1["vx"], d2["vx"] = -d1["vx"], -d2["vx"]
                    d1["vy"], d2["vy"] = -d1["vy"], -d2["vy"]
                    self.score += 50

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

        # 1. Deflection Walls on Left and Right borders
        for y in range(16):
            set_pixel(1, y, 40, 100, 180) # Neon blue energy conduit
            set_pixel(14, y, 40, 100, 180)

        # 2. Upper Platform (Sark's Elevated Ring) at y=3
        for x in range(3, 13):
            set_pixel(x, 3, 160, 40, 40) # Crimson platform edge

        # 3. Lower Platform (Flynn's Floating Ring) at y=14
        for x in range(3, 13):
            set_pixel(x, 14, 0, 140, 200) # Cyan platform edge

        # 4. Discs
        for d in self.discs:
            dx = int(round(d["x"]))
            dy = int(round(d["y"]))
            if d["is_player"]:
                set_pixel(dx, dy, 80, 240, 255) # Cyan disc
            else:
                set_pixel(dx, dy, 255, 60, 40)  # Red Sark disc

        # 5. Commander Sark
        sx = int(round(self.sx))
        sy = int(round(self.sy))
        if self.state in (STATE_PLAYING, STATE_PLAYER_DIED):
            set_pixel(sx, sy, 255, 30, 30)      # Red armor
            set_pixel(sx, sy - 1, 255, 200, 0)  # Sark crested helmet
            set_pixel(sx - 1, sy, 200, 20, 20)  # Left shoulder
            set_pixel(sx + 1, sy, 200, 20, 20)  # Right shoulder
        elif self.state == STATE_SARK_FALLING:
            # Sark falling into the chasm
            fall_y = int(sy + (2.0 - self.state_timer) * 6)
            set_pixel(sx, fall_y, 255, 100, 0)

        # 6. Flynn (Player)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_SARK_FALLING):
            set_pixel(px, py, 40, 200, 255)     # Glowing cyan suit
            set_pixel(px, py - 1, 100, 240, 255) # Flynn helmet
            set_pixel(px - 1, py, 20, 140, 220)  # Left arm
            set_pixel(px + 1, py, 20, 140, 220)  # Right arm

            # Deflection Shield Aura
            if self.shield_active:
                set_pixel(px - 1, py - 1, 255, 255, 80)
                set_pixel(px, py - 2, 255, 255, 140)
                set_pixel(px + 1, py - 1, 255, 255, 80)
        elif self.state == STATE_PLAYER_DIED:
            set_pixel(px, py, 255, 100, 0)
            set_pixel(px - 1, py, 255, 0, 0)
            set_pixel(px + 1, py, 255, 0, 0)

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
            "sx": self.sx,
            "sark_hp": self.sark_hp,
            "shield_energy": self.shield_energy,
            "shield_active": self.shield_active,
            "discs_count": len(self.discs),
        }

