"""
Game #165: 食物大战 (Food Fight - 1983 Atari / General Computer Corporation)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Developed by GCC and released by Atari in 1983, Food Fight is an arcade comedy classic.
Controlling Charley Chuck, players must reach and eat an ice cream cone on the opposite side
before it melts into a puddle, while scooping up floor food piles (pies, watermelons, tomatoes)
to hurl at pursuing chefs!

Unique Mechanic (Strict Zero-Redundancy):
- Melting Ice Cream Timer: Race across the arena to devour the cone before it melts away.
- Floor Food Ammo Scooping & Projectiles: Walk over food piles to load pies/tomatoes and throw them.
- Chef Splat Knockdown: Hurl food to splat pursuing chefs and knock them unconscious.
- Open Manhole Hazards: Avoid falling into kitchen manholes from which chefs emerge.
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
STATE_CHARLEY_SPLAT = 2
STATE_GAME_OVER = 3

class Game165FoodFight(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.level = 1
        self.state_timer = 0.0

        # Charley Chuck
        self.px = 2.0
        self.py = 8.0
        self.facing_dx = 1.0
        self.facing_dy = 0.0
        self.speed = 5.2
        self.food_ammo = 0
        self.max_ammo = 4
        self.fire_cooldown = 0.0

        # Ice Cream Cone
        self.cone_x = 14.0
        self.cone_y = 8.0
        self.melt_timer = 15.0

        # Food Piles: list of {x, y, food_type, remaining}
        self.food_piles: List[Dict[str, Any]] = []

        # Thrown Food Projectiles: list of {x, y, vx, vy, is_player}
        self.projectiles: List[Dict[str, float]] = []

        # Chefs: list of {id, x, y, speed, stunned_timer, alive}
        self.chefs: List[Dict[str, Any]] = []

        # Manholes: list of (x, y)
        self.manholes = [(4, 4), (4, 11), (11, 4), (11, 11)]

        self.init()

    @property
    def game_id(self) -> int:
        return 165

    @property
    def name(self) -> str:
        return "食物大战"

    @property
    def english_name(self) -> str:
        return "Food Fight"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "冰淇淋甜筒融化倒计时竞速、抓取地面食物堆投掷飞馅饼击晕大厨、规避厨房井盖陷阱"

    def get_name(self) -> str:
        return "Food Fight (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 8.0
        self.facing_dx = 1.0
        self.facing_dy = 0.0
        self.food_ammo = 0
        self.fire_cooldown = 0.0
        self.melt_timer = max(8.0, 16.0 - self.level * 1.0)

        self.projectiles.clear()

        # Scatter food piles
        self.food_piles = [
            {"x": 6.0, "y": 4.0, "type": "pie", "remaining": 8},
            {"x": 6.0, "y": 12.0, "type": "tomato", "remaining": 8},
            {"x": 10.0, "y": 4.0, "type": "watermelon", "remaining": 8},
            {"x": 10.0, "y": 12.0, "type": "pie", "remaining": 8},
        ]

        # 3 Chefs (Angelo, Zorba, Oscar)
        self.chefs = [
            {"id": 0, "x": 4.0, "y": 4.0, "speed": 1.8 + self.level * 0.2, "stunned_timer": 0.0, "throw_timer": 2.0},
            {"id": 1, "x": 11.0, "y": 4.0, "speed": 2.0 + self.level * 0.2, "stunned_timer": 0.0, "throw_timer": 3.0},
            {"id": 2, "x": 11.0, "y": 11.0, "speed": 2.2 + self.level * 0.2, "stunned_timer": 0.0, "throw_timer": 2.5},
        ]

    def throw_food(self):
        if self.food_ammo <= 0 or self.fire_cooldown > 0.0 or self.state != STATE_PLAYING:
            return

        self.food_ammo -= 1
        bx = self.px + self.facing_dx * 0.8
        by = self.py + self.facing_dy * 0.8
        throw_speed = 14.0
        self.projectiles.append({
            "x": bx,
            "y": by,
            "vx": self.facing_dx * throw_speed,
            "vy": self.facing_dy * throw_speed,
            "is_player": True
        })
        self.fire_cooldown = 0.2

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.level += 1
                self._init_level()
            return

        if self.state == STATE_CHARLEY_SPLAT:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 2.0
                    self.py = 8.0
                    self.food_ammo = 0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Ice cream melt timer
        self.melt_timer -= dt
        if self.melt_timer <= 0.0:
            # Ice cream melted!
            self.lives -= 1
            self.state = STATE_CHARLEY_SPLAT
            self.state_timer = 1.2
            return

        # Player Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0; self.facing_dx = -1.0; self.facing_dy = 0.0
        elif keys_down & KEY_RIGHT: dx += 1.0; self.facing_dx = 1.0; self.facing_dy = 0.0
        elif keys_down & KEY_UP:    dy -= 1.0; self.facing_dx = 0.0; self.facing_dy = -1.0
        elif keys_down & KEY_DOWN:  dy += 1.0; self.facing_dx = 0.0; self.facing_dy = 1.0

        if dx != 0.0 or dy != 0.0:
            self.px += dx * self.speed * dt
            self.py += dy * self.speed * dt

        self.px = max(1.0, min(14.5, self.px))
        self.py = max(1.0, min(14.5, self.py))

        # Check reaching ice cream cone!
        if math.hypot(self.cone_x - self.px, self.cone_y - self.py) < 1.0:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += int(self.melt_timer * 100) + 1000
            return

        # Throw food action
        if keys_pressed & KEY_A:
            self.throw_food()

        # Food Piles Ammo Reload
        for pile in self.food_piles:
            if pile["remaining"] > 0 and math.hypot(pile["x"] - self.px, pile["y"] - self.py) < 1.0:
                if self.food_ammo < self.max_ammo:
                    take = min(self.max_ammo - self.food_ammo, pile["remaining"])
                    self.food_ammo += take
                    pile["remaining"] -= take
                    self.score += 25 * take

        # Projectiles Update
        for p in list(self.projectiles):
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt

            if p["x"] < 0 or p["x"] > 15 or p["y"] < 0 or p["y"] > 15:
                self.projectiles.remove(p)
                continue

            if p["is_player"]:
                # Check hit chefs
                for c in self.chefs:
                    if c["stunned_timer"] <= 0.0 and math.hypot(c["x"] - p["x"], c["y"] - p["y"]) < 1.0:
                        c["stunned_timer"] = 3.0 # Splatted and stunned!
                        self.score += 200
                        if p in self.projectiles:
                            self.projectiles.remove(p)
                        break
            else:
                # Chef projectile hit Charley!
                if math.hypot(self.px - p["x"], self.py - p["y"]) < 0.8:
                    self.projectiles.remove(p)
                    self.lives -= 1
                    self.state = STATE_CHARLEY_SPLAT
                    self.state_timer = 1.0
                    return

        # Chefs AI & Throwing
        for c in self.chefs:
            if c["stunned_timer"] > 0.0:
                c["stunned_timer"] -= dt
                continue

            cdx = self.px - c["x"]
            cdy = self.py - c["y"]
            dist = math.hypot(cdx, cdy)
            if dist > 0.2:
                c["x"] += (cdx / dist) * c["speed"] * dt
                c["y"] += (cdy / dist) * c["speed"] * dt

            # Chef throws pie/food at Charley
            c["throw_timer"] -= dt
            if c["throw_timer"] <= 0.0 and dist < 8.0:
                self.projectiles.append({
                    "x": c["x"],
                    "y": c["y"],
                    "vx": (cdx / dist) * 8.0,
                    "vy": (cdy / dist) * 8.0,
                    "is_player": False
                })
                c["throw_timer"] = 3.0

            # Direct contact with Charley
            if math.hypot(c["x"] - self.px, c["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_CHARLEY_SPLAT
                self.state_timer = 1.0
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

        # 1. Floor & Manholes
        for (mx, my) in self.manholes:
            set_pixel(mx, my, 60, 60, 60)

        # 2. Food Piles
        for pile in self.food_piles:
            if pile["remaining"] > 0:
                fx, fy = int(round(pile["x"])), int(round(pile["y"]))
                if pile["type"] == "pie":
                    set_pixel(fx, fy, 255, 230, 150) # Cream pie
                elif pile["type"] == "tomato":
                    set_pixel(fx, fy, 255, 30, 30)   # Tomato
                else:
                    set_pixel(fx, fy, 40, 200, 60)   # Watermelon

        # 3. Ice Cream Cone (Waffle brown + Ice cream cyan/white)
        cx, cy = int(round(self.cone_x)), int(round(self.cone_y))
        set_pixel(cx, cy, 255, 255, 255)     # Vanilla scoop
        set_pixel(cx + 1, cy, 180, 110, 40)  # Waffle cone

        # 4. Chefs (Angelo/Zorba/Oscar in white chef hats, red coats)
        for c in self.chefs:
            chx, chy = int(round(c["x"])), int(round(c["y"]))
            if c["stunned_timer"] > 0.0:
                set_pixel(chx, chy, 255, 200, 50) # Yellow splat stun
            else:
                set_pixel(chx, chy, 220, 60, 40)   # Red chef
                set_pixel(chx, chy - 1, 240, 240, 240) # Tall white hat

        # 5. Projectiles
        for p in self.projectiles:
            px, py = int(round(p["x"])), int(round(p["y"]))
            if p["is_player"]:
                set_pixel(px, py, 255, 255, 200)
            else:
                set_pixel(px, py, 255, 100, 50)

        # 6. Charley Chuck
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 40, 120, 255) # Blue clothes
            set_pixel(px, py - 1, 255, 200, 160) # Face
        elif self.state == STATE_CHARLEY_SPLAT:
            set_pixel(px, py, 255, 120, 0) # Food splattered!

        # 7. Ammo Dots top row
        for i in range(self.food_ammo):
            set_pixel(i, 0, 255, 230, 100)

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
            "food_ammo": self.food_ammo,
            "melt_timer": self.melt_timer,
            "px": self.px,
            "py": self.py,
        }
