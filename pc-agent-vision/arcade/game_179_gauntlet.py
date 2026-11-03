"""
Game #179: 圣铠传说 (Gauntlet - 1985 Atari Games / Ed Logg)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Atari Games in 1985 and designed by Ed Logg, Gauntlet was a monumental
arcade sensation. It defined the cooperative hack-and-slash dungeon crawler genre,
famed for its digitized narrator ("Warrior needs food badly!"), monster generators,
locked door routing, ticking health decay, and screen-clearing magic potions.

Unique Core Mechanic (Strict Zero-Redundancy):
- Monster Nest Destruction: Swarming monster generators continuously spawn ghosts and grunts
  until the player shoots and demolishes the nest structures.
- Decaying Health & Food Replenishment: Health continuously ticks downward as a survival clock,
  forcing aggressive exploration to forage food rations.
- Keys & Locked Gate Routing: Collect keys to unlock maze gates blocking paths to the exit.
- Magic Smart Potions: Button B detonates an arcane potion, obliterating all active monsters in a flash.
- Exit Stairs: Reach the shimmering exit portal to conquer the dungeon floor.
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
STATE_WARRIOR_DIED = 2
STATE_GAME_OVER = 3

class Game179Gauntlet(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.health = 500 # Ticking health
        self.max_health = 1000
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Warrior
        self.px = 2.0
        self.py = 2.0
        self.facing_x = 1.0
        self.facing_y = 0.0
        self.speed = 5.5
        self.keys_count = 0
        self.potions_count = 1

        # Projectiles [{x, y, vx, vy, active}]
        self.axes: List[Dict[str, Any]] = []

        # Dungeon Map (16x16)
        # 0: Floor, 1: Wall, 2: Locked Door, 3: Exit Stairs
        self.grid = [[0 for _ in range(16)] for _ in range(16)]

        # Pickups [{x, y, type: "food"|"key"|"potion"}]
        self.pickups: List[Dict[str, Any]] = []

        # Monster Generators [{x, y, hp, spawn_timer}]
        self.generators: List[Dict[str, Any]] = []

        # Monsters [{x, y, speed, alive}]
        self.monsters: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 179

    @property
    def name(self) -> str:
        return "圣铠传说"

    @property
    def english_name(self) -> str:
        return "Gauntlet"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "地牢魔物巢穴定点摧毁、钥匙开锁迷宫拓扑、生命流逝捡拾食物续命与全屏魔法药水清场"

    def get_name(self) -> str:
        return "Gauntlet (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.health = 500
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 2.0
        self.facing_x = 1.0
        self.facing_y = 0.0
        self.keys_count = 1
        self.potions_count = 1
        self.health = max(400, self.health)

        self.axes.clear()
        self.pickups.clear()
        self.generators.clear()
        self.monsters.clear()

        # Build Dungeon Floor Layout
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    self.grid[y][x] = 1 # Outer walls
                else:
                    self.grid[y][x] = 0

        # Interior labyrinth partitions
        for y in range(1, 10): self.grid[y][5] = 1
        for x in range(5, 12): self.grid[9][x] = 1
        for y in range(6, 15): self.grid[y][11] = 1

        # Locked Door (x=5, y=5)
        self.grid[5][5] = 2 # Door requiring a key

        # Exit Stairs at (13, 13)
        self.grid[13][13] = 3

        # Pickups
        self.pickups = [
            {"x": 2, "y": 8, "type": "food"},
            {"x": 8, "y": 2, "type": "food"},
            {"x": 8, "y": 7, "type": "key"},
            {"x": 13, "y": 3, "type": "potion"},
            {"x": 7, "y": 13, "type": "food"},
        ]

        # Monster Generators
        self.generators = [
            {"x": 8, "y": 4, "hp": 3, "timer": 1.5},
            {"x": 13, "y": 7, "hp": 3, "timer": 2.0},
            {"x": 4, "y": 12, "hp": 3, "timer": 1.8},
        ]

        # Initial wandering monsters
        self.monsters = [
            {"x": 7.0, "y": 4.0, "speed": 2.0 + self.stage * 0.2, "alive": True},
            {"x": 13.0, "y": 5.0, "speed": 2.0 + self.stage * 0.2, "alive": True},
        ]

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_WARRIOR_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 2.0
                    self.py = 2.0
                    self.health = 500
                    self.axes.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Health decay over time ("Warrior needs food badly!")
        self.health -= 12.0 * dt
        if self.health <= 0.0:
            self.health = 0.0
            self.lives -= 1
            self.state = STATE_WARRIOR_DIED
            self.state_timer = 1.2
            return

        # Player Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0; self.facing_x = -1.0; self.facing_y = 0.0
        if keys_down & KEY_RIGHT: dx += 1.0; self.facing_x = 1.0;  self.facing_y = 0.0
        if keys_down & KEY_UP:    dy -= 1.0; self.facing_x = 0.0;  self.facing_y = -1.0
        if keys_down & KEY_DOWN:  dy += 1.0; self.facing_x = 0.0;  self.facing_y = 1.0

        if dx != 0.0 or dy != 0.0:
            new_px = self.px + dx * self.speed * dt
            new_py = self.py + dy * self.speed * dt

            # Wall collision
            cx, cy = int(round(new_px)), int(round(new_py))
            if 0 <= cx < 16 and 0 <= cy < 16:
                cell = self.grid[cy][cx]
                if cell == 1:
                    # Solid Wall
                    pass
                elif cell == 2:
                    # Locked Door
                    if self.keys_count > 0:
                        self.keys_count -= 1
                        self.grid[cy][cx] = 0 # Door unlocked!
                        self.score += 100
                        self.px, self.py = new_px, new_py
                elif cell == 3:
                    # Exit Stairs
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 2500
                    return
                else:
                    self.px, self.py = new_px, new_py

        # Collect Pickups
        for p in self.pickups[:]:
            if math.hypot(p["x"] - self.px, p["y"] - self.py) < 0.8:
                self.pickups.remove(p)
                p_type = p["type"]
                if p_type == "food":
                    self.health = min(float(self.max_health), self.health + 150.0)
                    self.score += 100
                elif p_type == "key":
                    self.keys_count += 1
                    self.score += 100
                elif p_type == "potion":
                    self.potions_count += 1
                    self.score += 200

        # Throw Axe (Button A)
        active_axes = sum(1 for a in self.axes if a["active"])
        if (keys_pressed & KEY_A) and active_axes < 2:
            self.axes.append({
                "x": self.px,
                "y": self.py,
                "vx": self.facing_x * 12.0,
                "vy": self.facing_y * 12.0,
                "active": True,
            })

        # Cast Magic Potion (Button B)
        if (keys_pressed & KEY_B) and self.potions_count > 0:
            self.potions_count -= 1
            # Destroy all active monsters on screen!
            killed = len([m for m in self.monsters if m["alive"]])
            for m in self.monsters:
                m["alive"] = False
            self.score += killed * 150

        # Update Axes
        for a in self.axes[:]:
            if not a["active"]:
                continue
            a["x"] += a["vx"] * dt
            a["y"] += a["vy"] * dt

            ax, ay = int(round(a["x"])), int(round(a["y"]))
            if ax < 1 or ax >= 15 or ay < 1 or ay >= 15 or self.grid[ay][ax] in (1, 2):
                a["active"] = False
                continue

            # Hit Monsters
            for m in self.monsters:
                if m["alive"] and math.hypot(m["x"] - a["x"], m["y"] - a["y"]) < 0.9:
                    m["alive"] = False
                    a["active"] = False
                    self.score += 100
                    break

            # Hit Generators
            if a["active"]:
                for g in self.generators:
                    if g["hp"] > 0 and math.hypot(g["x"] - a["x"], g["y"] - a["y"]) < 0.9:
                        g["hp"] -= 1
                        a["active"] = False
                        self.score += 150
                        if g["hp"] <= 0:
                            self.score += 500
                        break

        self.axes = [a for a in self.axes if a["active"]]

        # Update Generators (Spawn Monsters)
        for g in self.generators:
            if g["hp"] <= 0:
                continue
            g["timer"] -= dt
            if g["timer"] <= 0.0:
                g["timer"] = 3.0
                if len([m for m in self.monsters if m["alive"]]) < 8:
                    self.monsters.append({
                        "x": float(g["x"]),
                        "y": float(g["y"] + 0.5),
                        "speed": 2.0 + self.stage * 0.2,
                        "alive": True,
                    })

        # Update Monsters AI
        for m in self.monsters:
            if not m["alive"]:
                continue
            mdx = self.px - m["x"]
            mdy = self.py - m["y"]
            dist = math.hypot(mdx, mdy)
            if dist > 0.1:
                step_x = (mdx / dist) * m["speed"] * dt
                step_y = (mdy / dist) * m["speed"] * dt
                m["x"] += step_x
                m["y"] += step_y

            # Monster damages Warrior
            if math.hypot(m["x"] - self.px, m["y"] - self.py) < 0.8:
                self.health -= 50.0 * dt
                if self.health <= 0.0:
                    self.health = 0.0
                    self.lives -= 1
                    self.state = STATE_WARRIOR_DIED
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

        # 1. Dungeon Walls & Doors
        for y in range(16):
            for x in range(16):
                cell = self.grid[y][x]
                if cell == 1:
                    set_pixel(x, y, 60, 60, 80) # Stone Wall
                elif cell == 2:
                    set_pixel(x, y, 200, 160, 40) # Locked Golden Gate
                elif cell == 3:
                    set_pixel(x, y, 60, 240, 255) # Shimmering Exit Portal

        # 2. Pickups
        for p in self.pickups:
            px, py = p["x"], p["y"]
            p_type = p["type"]
            if p_type == "food":
                set_pixel(px, py, 240, 100, 40) # Roast meat / food
            elif p_type == "key":
                set_pixel(px, py, 255, 220, 0)  # Golden Key
            elif p_type == "potion":
                set_pixel(px, py, 180, 40, 240) # Arcane Potion

        # 3. Monster Generators (Bones / Nests)
        for g in self.generators:
            if g["hp"] > 0:
                gx, gy = g["x"], g["y"]
                set_pixel(gx, gy, 140, 20, 20)
                set_pixel(gx, gy - 1, 200, 40, 40)

        # 4. Monsters (Grunts / Ghosts)
        for m in self.monsters:
            if m["alive"]:
                mx = int(round(m["x"]))
                my = int(round(m["y"]))
                set_pixel(mx, my, 40, 220, 60) # Green Grunt

        # 5. Flying Axes
        for a in self.axes:
            if a["active"]:
                ax = int(round(a["x"]))
                ay = int(round(a["y"]))
                set_pixel(ax, ay, 255, 255, 200)

        # 6. Warrior (Thor)
        wx = int(round(self.px))
        wy = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(wx, wy, 240, 40, 40)      # Red tunic
            set_pixel(wx, wy - 1, 255, 220, 140) # Winged helmet
            set_pixel(wx + int(self.facing_x), wy + int(self.facing_y), 200, 200, 220) # Battle Axe
        elif self.state == STATE_WARRIOR_DIED:
            set_pixel(wx, wy, 255, 100, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "health": int(self.health),
            "stage": self.stage,
            "keys_count": self.keys_count,
            "potions_count": self.potions_count,
            "monsters_alive": len([m for m in self.monsters if m["alive"]]),
            "generators_alive": len([g for g in self.generators if g["hp"] > 0]),
        }

