"""
Game #169: 军阀混战 / 四国城堡 (Warlords - 1980 Atari / Carla Meninsky)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Designed by Carla Meninsky and released by Atari in 1980, Warlords is the quintessential
4-corner fortress combat arcade classic. Defending their monarchs behind multi-layered
brick castles, four warlords control perimeter shields to catch and sling lethal fireballs
to breach enemy battlements and eliminate opposing rulers.

Unique Mechanic (Strict Zero-Redundancy):
- Quadrant Castle Siege: 4 fortified corner redoubts housing kings surrounded by destructible bricks.
- Perimeter Arc Shield: Guard your castle gateway and deflect incoming fireballs.
- Ball Catch & Power Sling (Key A): Trap the fireball in your shield, aim, and fling at high velocity.
- Regicide Elimination: Breaching an opponent's wall to assassinate their king eliminates them.
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
STATE_ROUND_CLEAR = 1
STATE_PLAYER_ELIMINATED = 2
STATE_GAME_OVER = 3

class Game169Warlords(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.round = 1
        self.state_timer = 0.0

        # 4 Warlords: 0=Player(Bottom-Left), 1=Top-Left, 2=Top-Right, 3=Bottom-Right
        # Each: {id, king_x, king_y, alive, shield_pos (0.0 .. 1.0 along arc)}
        self.warlords: List[Dict[str, Any]] = []

        # Bricks: set of (x, y)
        self.bricks: Dict[int, set] = {} # warlord_id -> set of (x, y)

        # Fireball state: {x, y, vx, vy, speed, caught_by: -1}
        self.ball = {"x": 7.5, "y": 7.5, "vx": 5.0, "vy": 4.0, "speed": 6.5, "caught_by": -1, "catch_timer": 0.0}

        self.init()

    @property
    def game_id(self) -> int:
        return 169

    @property
    def name(self) -> str:
        return "军阀混战"

    @property
    def english_name(self) -> str:
        return "Warlords"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "四隅要塞城堡攻防、弧面盾牌控球拦截与蓄力弹射、碎石破壁弑君斩首大决战"

    def get_name(self) -> str:
        return "Warlords (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.round = 1
        self._init_round()

    def _init_round(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0

        # Warlords setup
        self.warlords = [
            {"id": 0, "king_x": 1.0, "king_y": 14.0, "alive": True, "shield_t": 0.5}, # Player (Bottom-Left)
            {"id": 1, "king_x": 1.0, "king_y": 1.0,  "alive": True, "shield_t": 0.5}, # CPU Top-Left
            {"id": 2, "king_x": 14.0, "king_y": 1.0, "alive": True, "shield_t": 0.5}, # CPU Top-Right
            {"id": 3, "king_x": 14.0, "king_y": 14.0,"alive": True, "shield_t": 0.5}, # CPU Bottom-Right
        ]

        # Bricks per warlord
        self.bricks = {
            0: {(3, 14), (3, 13), (3, 12), (2, 12), (1, 12), (0, 12)},
            1: {(3, 1),  (3, 2),  (3, 3),  (2, 3),  (1, 3),  (0, 3)},
            2: {(12, 1), (12, 2), (12, 3), (13, 3), (14, 3), (15, 3)},
            3: {(12, 14),(12, 13),(12, 12),(13, 12),(14, 12),(15, 12)},
        }

        # Fireball
        angle = 0.8
        speed = 7.0 + self.round * 0.5
        self.ball = {
            "x": 7.5, "y": 7.5,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "speed": speed,
            "caught_by": -1,
            "catch_timer": 0.0
        }

    def get_shield_coord(self, wid: int, t: float) -> Tuple[float, float]:
        """Calculates (x, y) along the quadrant perimeter arc for warlord wid."""
        # t in [0.0, 1.0]
        if wid == 0:   # Bottom-Left: from (0.5, 11.5) to (4.5, 15.0)
            return (0.5 + t * 4.0, 11.5 + t * 3.5)
        elif wid == 1: # Top-Left: from (0.5, 4.5) to (4.5, 0.5)
            return (0.5 + t * 4.0, 4.5 - t * 4.0)
        elif wid == 2: # Top-Right: from (11.5, 0.5) to (15.0, 4.5)
            return (11.5 + t * 3.5, 0.5 + t * 4.0)
        else:          # Bottom-Right: from (11.5, 15.0) to (15.0, 11.5)
            return (11.5 + t * 3.5, 15.0 - t * 3.5)

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_ROUND_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.round += 1
                self._init_round()
            return

        if self.state == STATE_PLAYER_ELIMINATED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Shield Control (Warlord 0)
        if self.warlords[0]["alive"]:
            if keys_down & (KEY_LEFT | KEY_UP):
                self.warlords[0]["shield_t"] = max(0.0, self.warlords[0]["shield_t"] - 2.5 * dt)
            elif keys_down & (KEY_RIGHT | KEY_DOWN):
                self.warlords[0]["shield_t"] = min(1.0, self.warlords[0]["shield_t"] + 2.5 * dt)

        # CPU Shields AI (Follow fireball when in their half)
        for wid in (1, 2, 3):
            if self.warlords[wid]["alive"]:
                # Simple tracking towards ball
                sx, sy = self.get_shield_coord(wid, self.warlords[wid]["shield_t"])
                target_t = 0.5
                if wid == 1: # Top-Left
                    target_t = (self.ball["x"] / 6.0) if self.ball["x"] < 7.5 else 0.5
                elif wid == 2: # Top-Right
                    target_t = (self.ball["y"] / 6.0) if self.ball["x"] > 7.5 else 0.5
                elif wid == 3: # Bottom-Right
                    target_t = (self.ball["x"] - 10.0) / 5.0 if self.ball["x"] > 7.5 else 0.5
                target_t = max(0.0, min(1.0, target_t))

                diff = target_t - self.warlords[wid]["shield_t"]
                step = 1.8 * dt
                if abs(diff) > step:
                    self.warlords[wid]["shield_t"] += math.copysign(step, diff)

        # Fireball handling
        if self.ball["caught_by"] != -1:
            wid = self.ball["caught_by"]
            sx, sy = self.get_shield_coord(wid, self.warlords[wid]["shield_t"])
            self.ball["x"] = sx
            self.ball["y"] = sy
            self.ball["catch_timer"] -= dt

            # If player caught, can aim and release with Key A
            release = False
            if wid == 0:
                if (keys_pressed & KEY_A) or self.ball["catch_timer"] <= 0.0:
                    release = True
            else:
                if self.ball["catch_timer"] <= 0.0:
                    release = True

            if release:
                # Fling towards center or opposite corner
                aim_dx = 7.5 - self.ball["x"]
                aim_dy = 7.5 - self.ball["y"]
                d_len = math.hypot(aim_dx, aim_dy)
                power = self.ball["speed"] * 1.3
                self.ball["vx"] = (aim_dx / d_len) * power
                self.ball["vy"] = (aim_dy / d_len) * power
                self.ball["caught_by"] = -1
        else:
            # Ball movement
            self.ball["x"] += self.ball["vx"] * dt
            self.ball["y"] += self.ball["vy"] * dt

            # Screen bounds reflection
            if self.ball["x"] <= 0.0:
                self.ball["x"] = 0.0; self.ball["vx"] = abs(self.ball["vx"])
            elif self.ball["x"] >= 15.0:
                self.ball["x"] = 15.0; self.ball["vx"] = -abs(self.ball["vx"])
            if self.ball["y"] <= 0.0:
                self.ball["y"] = 0.0; self.ball["vy"] = abs(self.ball["vy"])
            elif self.ball["y"] >= 15.0:
                self.ball["y"] = 15.0; self.ball["vy"] = -abs(self.ball["vy"])

            # Check Shield Collisions
            for wid in range(4):
                if self.warlords[wid]["alive"]:
                    sx, sy = self.get_shield_coord(wid, self.warlords[wid]["shield_t"])
                    if math.hypot(sx - self.ball["x"], sy - self.ball["y"]) < 1.1:
                        # Catch or reflect
                        if wid == 0 and (keys_down & KEY_A):
                            # Player catches ball!
                            self.ball["caught_by"] = 0
                            self.ball["catch_timer"] = 1.5
                            self.score += 50
                            break
                        else:
                            # Reflect ball away from castle corner
                            dx = self.ball["x"] - self.warlords[wid]["king_x"]
                            dy = self.ball["y"] - self.warlords[wid]["king_y"]
                            d_len = math.hypot(dx, dy)
                            if d_len > 0.1:
                                self.ball["vx"] = (dx / d_len) * self.ball["speed"]
                                self.ball["vy"] = (dy / d_len) * self.ball["speed"]
                                if wid == 0: self.score += 25
                            break

            # Check Brick Collisions
            bx = int(round(self.ball["x"]))
            by = int(round(self.ball["y"]))
            for wid, bset in self.bricks.items():
                if (bx, by) in bset:
                    bset.remove((bx, by))
                    self.ball["vx"] = -self.ball["vx"]
                    self.ball["vy"] = -self.ball["vy"]
                    if wid != 0: self.score += 100
                    break

            # Check King / Monarch assassinations
            for w in self.warlords:
                if w["alive"] and math.hypot(w["king_x"] - self.ball["x"], w["king_y"] - self.ball["y"]) < 1.0:
                    w["alive"] = False
                    if w["id"] == 0:
                        # Player King slain!
                        self.state = STATE_PLAYER_ELIMINATED
                        self.state_timer = 1.5
                        return
                    else:
                        self.score += 1000

            # Check remaining opponents
            alive_cpus = sum(1 for w in self.warlords[1:] if w["alive"])
            if alive_cpus == 0 and self.warlords[0]["alive"]:
                self.state = STATE_ROUND_CLEAR
                self.state_timer = 2.0
                self.score += 3000

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

        # 1. Castle Bricks
        for wid, bset in self.bricks.items():
            for (bx, by) in bset:
                if wid == 0:   set_pixel(bx, by, 0, 180, 255) # Blue bricks
                elif wid == 1: set_pixel(bx, by, 255, 60, 60) # Red bricks
                elif wid == 2: set_pixel(bx, by, 255, 200, 0) # Gold bricks
                else:          set_pixel(bx, by, 40, 220, 80) # Green bricks

        # 2. Warlord Kings
        for w in self.warlords:
            if w["alive"]:
                kx, ky = int(round(w["king_x"])), int(round(w["king_y"]))
                set_pixel(kx, ky, 255, 255, 255) # White crown / monarch
                set_pixel(kx, ky - 1 if ky > 8 else ky + 1, 255, 215, 0) # Gold banner

        # 3. Perimeter Shields
        for w in self.warlords:
            if w["alive"]:
                sx, sy = self.get_shield_coord(w["id"], w["shield_t"])
                ix, iy = int(round(sx)), int(round(sy))
                color = (255, 255, 255) if w["id"] == 0 else (200, 150, 255)
                set_pixel(ix, iy, *color)

        # 4. Fireball
        fx, fy = int(round(self.ball["x"])), int(round(self.ball["y"]))
        set_pixel(fx, fy, 255, 120, 0)   # Blazing fireball core
        set_pixel(fx, fy - 1, 255, 40, 0) # Trailing flame

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "round": self.round,
            "player_alive": self.warlords[0]["alive"] if self.warlords else False,
            "cpus_alive": sum(1 for w in self.warlords[1:] if w["alive"]) if len(self.warlords) > 1 else 0,
            "ball_x": self.ball["x"],
            "ball_y": self.ball["y"],
        }

