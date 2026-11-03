"""
Game #168: 矿坑逃犯 / 淘金盗宝 (Bagman - 1982 Valadon Automation / Stern)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Developed by Valadon Automation and distributed by Stern in 1982, Bagman is a legendary
mining heist platformer. An escaped convict must haul heavy bags of gold up mine shafts
to his wheelbarrow on the surface, dodging rolling ore carts, swinging pickaxes at guards,
and managing heavy carrying weight that prevents ladder climbing!

Unique Mechanic (Strict Zero-Redundancy):
- Heavy Gold Bag Burden: Hauling gold halves movement speed and prevents climbing until dropped.
- Drop-to-Crush / Defense: Dropping a bag down shafts stuns chasing mine guards.
- Pickaxe Guard Stunner: Grab temporary pickaxes to knock guards unconscious.
- Surface Wheelbarrow Delivery: Deposit all subterranean gold into the surface cart to escape.
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
STATE_BAGMAN_CAUGHT = 2
STATE_GAME_OVER = 3

class Game168Bagman(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.mine = 1
        self.state_timer = 0.0

        # Player Bagman state
        self.px = 2.0
        self.py = 2.0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 4.5
        self.carrying_bag_idx = -1
        self.has_pickaxe = False
        self.pickaxe_timer = 0.0

        # Surface Wheelbarrow at (13.0, 2.0)
        self.wheelbarrow_x = 13.0
        self.wheelbarrow_y = 2.0
        self.bags_delivered = 0
        self.total_bags = 2

        # Gold Bags: list of {id, x, y, delivered}
        self.bags: List[Dict[str, Any]] = []

        # Guards: list of {id, x, y, vx, stunned_timer}
        self.guards: List[Dict[str, Any]] = []

        # Ore Cart rolling on track y=6
        self.cart_x = 3.0
        self.cart_vx = 2.5

        # Pickaxe at (8.0, 10.0)
        self.pickaxe = {"x": 8.0, "y": 10.0, "active": True}

        # Platforms and Ladders
        self.platforms = set()
        self.ladders = set()

        self.init()

    @property
    def game_id(self) -> int:
        return 168

    @property
    def name(self) -> str:
        return "矿坑逃犯"

    @property
    def english_name(self) -> str:
        return "Bagman"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "金袋负重搬运减速与卸货攀爬、垂直丢包砸晕狱警、矿车轨道滑行避险与独轮车归仓"

    def get_name(self) -> str:
        return "Bagman (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.mine = 1
        self._init_mine()

    def _init_mine(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 2.0
        self.carrying_bag_idx = -1
        self.has_pickaxe = False
        self.pickaxe_timer = 0.0
        self.bags_delivered = 0

        self.platforms.clear()
        self.ladders.clear()

        # Floor 0 (Surface): y=2, x=0..15
        for x in range(16): self.platforms.add((x, 2))
        # Floor 1 (Track level): y=6, x=0..15
        for x in range(16): self.platforms.add((x, 6))
        # Floor 2 (Mid shaft): y=10, x=0..15
        for x in range(16): self.platforms.add((x, 10))
        # Floor 3 (Deep mine): y=14, x=0..15
        for x in range(16): self.platforms.add((x, 14))

        # Ladders:
        for y in range(2, 6):  self.ladders.add((2, y))
        for y in range(6, 10): self.ladders.add((13, y))
        for y in range(10, 14): self.ladders.add((7, y))

        # 2 Gold Bags in deep mine
        self.bags = [
            {"id": 0, "x": 4.0, "y": 14.0, "delivered": False},
            {"id": 1, "x": 11.0, "y": 14.0, "delivered": False},
        ]

        # Guards
        self.guards = [
            {"id": 0, "x": 8.0, "y": 6.0, "vx": 1.6, "stunned_timer": 0.0},
            {"id": 1, "x": 4.0, "y": 10.0, "vx": -1.8, "stunned_timer": 0.0},
        ]

        # Ore cart
        self.cart_x = 3.0
        self.cart_vx = 2.5

        # Pickaxe
        self.pickaxe = {"x": 8.0, "y": 10.0, "active": True}

    def on_ladder(self, x: float, y: float) -> bool:
        ix = int(round(x))
        iy = int(round(y))
        return (ix, iy) in self.ladders or (ix, iy + 1) in self.ladders

    def grab_or_drop_bag(self):
        if self.carrying_bag_idx != -1:
            # Drop bag at feet!
            idx = self.carrying_bag_idx
            self.bags[idx]["x"] = self.px
            self.bags[idx]["y"] = self.py
            self.carrying_bag_idx = -1

            # Dropped bag stuns guard below!
            for g in self.guards:
                if abs(g["x"] - self.px) < 1.0 and abs(g["y"] - self.py) < 2.0:
                    g["stunned_timer"] = 3.5
                    self.score += 300
        else:
            # Check if standing near an undelivered bag
            for b in self.bags:
                if not b["delivered"] and math.hypot(b["x"] - self.px, b["y"] - self.py) < 1.0:
                    self.carrying_bag_idx = b["id"]
                    break

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.mine += 1
                self._init_mine()
            return

        if self.state == STATE_BAGMAN_CAUGHT:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 2.0
                    self.py = 2.0
                    self.carrying_bag_idx = -1
                    self.has_pickaxe = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.has_pickaxe:
            self.pickaxe_timer -= dt
            if self.pickaxe_timer <= 0.0:
                self.has_pickaxe = False

        # Current speed (halved if carrying heavy gold!)
        cur_speed = self.speed * 0.5 if (self.carrying_bag_idx != -1) else self.speed

        # Action: Button A to Grab / Drop Gold Bag
        if (keys_pressed & KEY_A):
            self.grab_or_drop_bag()

        # Movement:
        # Note: In Bagman, carrying heavy gold PREVENTS ladder climbing!
        is_on_ladder = self.on_ladder(self.px, self.py)

        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0

        # Ladder climbing only allowed when NOT carrying heavy gold bag!
        if is_on_ladder and (self.carrying_bag_idx == -1):
            if keys_down & KEY_UP:   dy -= 1.0
            if keys_down & KEY_DOWN: dy += 1.0

        self.px += dx * cur_speed * dt
        self.py += dy * cur_speed * dt

        self.px = max(1.0, min(14.5, self.px))
        self.py = max(2.0, min(14.0, self.py))

        # If carrying bag, bag follows player
        if self.carrying_bag_idx != -1:
            self.bags[self.carrying_bag_idx]["x"] = self.px
            self.bags[self.carrying_bag_idx]["y"] = self.py

            # Check delivery into surface wheelbarrow!
            if math.hypot(self.wheelbarrow_x - self.px, self.wheelbarrow_y - self.py) < 1.2:
                self.bags[self.carrying_bag_idx]["delivered"] = True
                self.carrying_bag_idx = -1
                self.bags_delivered += 1
                self.score += 1000

                # All bags delivered -> Clear!
                if self.bags_delivered >= self.total_bags:
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 2000
                    return

        # Pickaxe pickup
        if self.pickaxe["active"] and math.hypot(self.pickaxe["x"] - self.px, self.pickaxe["y"] - self.py) < 1.0:
            self.pickaxe["active"] = False
            self.has_pickaxe = True
            self.pickaxe_timer = 5.0
            self.score += 200

        # Ore cart update
        self.cart_x += self.cart_vx * dt
        if self.cart_x <= 2.0 or self.cart_x >= 13.0:
            self.cart_vx = -self.cart_vx

        # Ore cart hitting player
        if abs(self.py - 6.0) < 0.6 and abs(self.cart_x - self.px) < 1.0:
            self.lives -= 1
            self.state = STATE_BAGMAN_CAUGHT
            self.state_timer = 1.0
            return

        # Guards update
        for g in self.guards:
            if g["stunned_timer"] > 0.0:
                g["stunned_timer"] -= dt
                continue

            g["x"] += g["vx"] * dt
            if g["x"] <= 2.0 or g["x"] >= 13.0:
                g["vx"] = -g["vx"]

            # Guard encounters Bagman
            if math.hypot(g["x"] - self.px, g["y"] - self.py) < 0.9:
                if self.has_pickaxe:
                    # Stun guard with pickaxe!
                    g["stunned_timer"] = 4.0
                    self.score += 400
                else:
                    self.lives -= 1
                    self.state = STATE_BAGMAN_CAUGHT
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

        # 1. Mine Shaft Beams
        for (px, py) in self.platforms:
            set_pixel(px, py, 110, 80, 50) # Brown wood beams

        # 2. Ladders
        for (lx, ly) in self.ladders:
            set_pixel(lx, ly, 220, 220, 0) # Yellow ladders

        # 3. Surface Wheelbarrow
        set_pixel(13, 2, 255, 120, 0)
        set_pixel(14, 2, 200, 100, 0)

        # 4. Ore Cart (y=6)
        cx = int(round(self.cart_x))
        set_pixel(cx, 6, 80, 80, 255)
        set_pixel(cx + 1, 6, 80, 80, 255)

        # 5. Pickaxe
        if self.pickaxe["active"]:
            px, py = int(round(self.pickaxe["x"])), int(round(self.pickaxe["y"]))
            set_pixel(px, py, 200, 220, 240)

        # 6. Gold Bags (Yellow-Gold $ bags)
        for b in self.bags:
            if not b["delivered"]:
                bx, by = int(round(b["x"])), int(round(b["y"]))
                set_pixel(bx, by, 255, 230, 20)

        # 7. Guards (Policemen in blue uniform)
        for g in self.guards:
            gx, gy = int(round(g["x"])), int(round(g["y"]))
            if g["stunned_timer"] > 0.0:
                set_pixel(gx, gy, 255, 180, 50) # Stunned yellow
            else:
                set_pixel(gx, gy, 40, 80, 255)  # Blue guard

        # 8. Bagman (Convict in striped yellow/black)
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.has_pickaxe:
                set_pixel(px, py, 255, 255, 255) # Armed Bagman
            else:
                set_pixel(px, py, 255, 220, 60)  # Convict
            if self.carrying_bag_idx != -1:
                set_pixel(px + 1, py, 255, 200, 0) # Holding gold bag!
        elif self.state == STATE_BAGMAN_CAUGHT:
            set_pixel(px, py, 255, 60, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "mine": self.mine,
            "carrying_bag": (self.carrying_bag_idx != -1),
            "bags_delivered": self.bags_delivered,
            "has_pickaxe": self.has_pickaxe,
            "px": self.px,
            "py": self.py,
        }

