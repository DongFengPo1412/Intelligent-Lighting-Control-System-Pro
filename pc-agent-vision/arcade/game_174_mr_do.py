"""
Game #174: 挖金子小丑 (Mr. Do! - 1982 Universal)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Universal in 1982, Mr. Do! was an immediate worldwide arcade smash hit.
Featuring an energetic clown hero, it introduced the famous bouncing power ball weapon,
pushable gravity-affected giant apples that crush tunneling monsters, scattered cherry
clusters, and the iconic "EXTRA" letter collection mechanic.

Unique Core Mechanic (Strict Zero-Redundancy):
- Bouncing Power Ball (魔球): Mr. Do throws a single bouncy magic ball that travels down tunnels,
  ricochets off walls/dirt boundaries, squashes chasing Badmuns on impact, and can be caught back on return.
- Pushable & Falling Red Apples: Heavy apples can be pushed horizontally along tunnels or dropped down
  vertical shafts to crush monsters underneath for massive points.
- Cherry Harvesting: Collect all scattered cherry clusters to achieve instant stage victory.
- Tunnel Digging: Carve custom pathways through soil to create escape routes and tactical traps.
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
STATE_PLAYER_DIED = 2
STATE_GAME_OVER = 3

class Game174MrDo(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Mr. Do
        self.px = 7.5
        self.py = 13.0
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.speed = 5.0

        # Dirt grid (16x16 bool: True = solid soil, False = carved tunnel)
        self.dirt = [[True for _ in range(16)] for _ in range(16)]

        # Cherries set of (x, y)
        self.cherries = set()

        # Apples: list of {x, y, falling, fall_vy, wobble_timer}
        self.apples: List[Dict[str, Any]] = []

        # Monsters (Badmuns): list of {id, x, y, speed, alive}
        self.monsters: List[Dict[str, Any]] = []

        # Power Ball: {active, x, y, vx, vy, cooldown}
        self.ball = {"active": False, "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "cooldown": 0.0}

        self.init()

    @property
    def game_id(self) -> int:
        return 174

    @property
    def name(self) -> str:
        return "挖金子小丑"

    @property
    def english_name(self) -> str:
        return "Mr. Do!"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "地底回旋弹跳魔球投掷回收、横向推移大苹果砸扁地底怪兽、吃尽樱桃串清屏与拼写EXTRA"

    def get_name(self) -> str:
        return "Mr. Do! (1982)"

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
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.ball["active"] = False

        # Reset soil
        for y in range(16):
            for x in range(16):
                # Borders and surface sky
                if y == 0 or y == 15 or x == 0 or x == 15:
                    self.dirt[y][x] = False
                else:
                    self.dirt[y][x] = True

        # Pre-carved starting center shaft
        for y in range(8, 14):
            self.dirt[y][7] = False
            self.dirt[y][8] = False

        # Cherries in clusters (columns 2, 5, 10, 13)
        self.cherries.clear()
        for y in (3, 6, 9):
            for x in (2, 3, 12, 13):
                self.cherries.add((x, y))

        # Apples (Red boulders)
        self.apples = [
            {"x": 4.0, "y": 4.0, "falling": False, "fall_vy": 0.0, "wobble": 0.0},
            {"x": 11.0, "y": 4.0, "falling": False, "fall_vy": 0.0, "wobble": 0.0},
            {"x": 8.0, "y": 7.0, "falling": False, "fall_vy": 0.0, "wobble": 0.0},
        ]
        # Soil under apples is solid initially
        for a in self.apples:
            ax, ay = int(a["x"]), int(a["y"])
            self.dirt[ay][ax] = False

        # Monsters
        self.monsters = [
            {"id": 0, "x": 3.0, "y": 2.0, "speed": 2.2 + self.stage * 0.2, "alive": True},
            {"id": 1, "x": 12.0, "y": 2.0, "speed": 2.2 + self.stage * 0.2, "alive": True},
        ]
        for m in self.monsters:
            self.dirt[int(m["y"])][int(m["x"])] = False

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
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
                    self.ball["active"] = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Movement & Digging
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0; self.facing_x = -1.0; self.facing_y = 0.0
        if keys_down & KEY_RIGHT: dx += 1.0; self.facing_x = 1.0;  self.facing_y = 0.0
        if keys_down & KEY_UP:    dy -= 1.0; self.facing_x = 0.0;  self.facing_y = -1.0
        if keys_down & KEY_DOWN:  dy += 1.0; self.facing_x = 0.0;  self.facing_y = 1.0

        if dx != 0.0 or dy != 0.0:
            target_px = self.px + dx * self.speed * dt
            target_py = self.py + dy * self.speed * dt

            # Check pushing apple horizontally
            for a in self.apples:
                if not a["falling"] and math.hypot(a["x"] - target_px, a["y"] - target_py) < 0.8:
                    if dx != 0.0:
                        new_ax = a["x"] + dx * (self.speed * 0.6) * dt
                        if 1.0 <= new_ax <= 14.0:
                            a["x"] = new_ax
                    target_px = self.px # Pushing resistance

            self.px = max(1.0, min(14.0, target_px))
            self.py = max(1.0, min(14.0, target_py))

            # Dig current cell
            cx, cy = int(round(self.px)), int(round(self.py))
            if 0 <= cx < 16 and 0 <= cy < 16:
                if self.dirt[cy][cx]:
                    self.dirt[cy][cx] = False
                    self.score += 5

            # Eat cherry
            if (cx, cy) in self.cherries:
                self.cherries.remove((cx, cy))
                self.score += 50
                if len(self.cherries) == 0:
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 2.0
                    self.score += 3000
                    return

        # Throw Power Ball (Button A)
        if (keys_pressed & KEY_A) and not self.ball["active"]:
            self.ball["active"] = True
            self.ball["cooldown"] = 0.3
            self.ball["x"] = self.px
            self.ball["y"] = self.py
            b_speed = 10.0
            self.ball["vx"] = self.facing_x * b_speed
            self.ball["vy"] = self.facing_y * b_speed
            if self.ball["vx"] == 0.0 and self.ball["vy"] == 0.0:
                self.ball["vy"] = -b_speed

        # Update Power Ball bouncing
        if self.ball["active"]:
            if self.ball["cooldown"] > 0.0:
                self.ball["cooldown"] -= dt
            self.ball["x"] += self.ball["vx"] * dt
            self.ball["y"] += self.ball["vy"] * dt

            # Bounce off bounds
            if self.ball["x"] <= 1.0:
                self.ball["x"] = 1.0
                self.ball["vx"] = abs(self.ball["vx"])
            elif self.ball["x"] >= 14.0:
                self.ball["x"] = 14.0
                self.ball["vx"] = -abs(self.ball["vx"])

            if self.ball["y"] <= 1.0:
                self.ball["y"] = 1.0
                self.ball["vy"] = abs(self.ball["vy"])
            elif self.ball["y"] >= 14.0:
                self.ball["y"] = 14.0
                self.ball["vy"] = -abs(self.ball["vy"])

            # Check hit against monsters
            for m in self.monsters:
                if m["alive"] and math.hypot(m["x"] - self.ball["x"], m["y"] - self.ball["y"]) < 0.9:
                    m["alive"] = False
                    self.ball["active"] = False # Ball caught back
                    self.score += 500
                    self._check_monsters_eliminated()
                    break

            # Catch ball back if Mr. Do collides with it after cooldown
            if self.ball["active"] and self.ball["cooldown"] <= 0.0 and math.hypot(self.px - self.ball["x"], self.py - self.ball["y"]) < 0.8:
                self.ball["active"] = False

        # Update Apples (Falling & Crushing)
        for a in self.apples[:]:
            ax = int(round(a["x"]))
            ay = int(round(a["y"]))

            # Check if space below is open (no dirt)
            if ay + 1 < 16 and not self.dirt[ay + 1][ax]:
                if not a["falling"]:
                    a["wobble"] += dt
                    if a["wobble"] > 0.4:
                        a["falling"] = True
                        a["fall_vy"] = 8.0
                else:
                    a["y"] += a["fall_vy"] * dt
                    # Crush monster
                    for m in self.monsters:
                        if m["alive"] and math.hypot(m["x"] - a["x"], m["y"] - a["y"]) < 0.9:
                            m["alive"] = False
                            self.score += 1000
                            self._check_monsters_eliminated()

                    # Crush player
                    if math.hypot(self.px - a["x"], self.py - a["y"]) < 0.8:
                        self.lives -= 1
                        self.state = STATE_PLAYER_DIED
                        self.state_timer = 1.0
                        return

                    # Stop or crack apple when floor reached
                    if a["y"] >= 14.0 or (int(a["y"]) + 1 < 16 and self.dirt[int(a["y"]) + 1][ax]):
                        a["falling"] = False
                        a["wobble"] = 0.0

        # Monster AI (Pursue Mr. Do through tunnels)
        for m in self.monsters:
            if not m["alive"]:
                continue
            mdx = self.px - m["x"]
            mdy = self.py - m["y"]
            dist = math.hypot(mdx, mdy)
            if dist > 0.1:
                step_x = (mdx / dist) * m["speed"] * dt
                step_y = (mdy / dist) * m["speed"] * dt

                # Monsters can slowly dig or move faster in tunnels
                m["x"] += step_x
                m["y"] += step_y

            # Check catch Mr. Do
            if math.hypot(m["x"] - self.px, m["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_PLAYER_DIED
                self.state_timer = 1.0
                return

    def _check_monsters_eliminated(self):
        if not any(m["alive"] for m in self.monsters):
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 2000

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

        # 1. Soil & Dug Tunnels
        for y in range(16):
            for x in range(16):
                if self.dirt[y][x]:
                    set_pixel(x, y, 100, 60, 20) # Earth brown dirt
                else:
                    set_pixel(x, y, 10, 10, 15)  # Dark open tunnel

        # 2. Cherries (Bright Red paired berries)
        for (cx, cy) in self.cherries:
            set_pixel(cx, cy, 255, 30, 80)

        # 3. Apples (Big golden-red with green stem)
        for a in self.apples:
            ax = int(round(a["x"]))
            ay = int(round(a["y"]))
            set_pixel(ax, ay, 240, 20, 20)
            set_pixel(ax, ay - 1, 40, 180, 40)

        # 4. Monsters (Badmuns - Red demons)
        for m in self.monsters:
            if m["alive"]:
                mx = int(round(m["x"]))
                my = int(round(m["y"]))
                set_pixel(mx, my, 220, 40, 180)
                set_pixel(mx, my - 1, 255, 200, 0) # Horns

        # 5. Power Ball
        if self.ball["active"]:
            bx = int(round(self.ball["x"]))
            by = int(round(self.ball["y"]))
            set_pixel(bx, by, 80, 255, 255) # Glowing cyan ball

        # 6. Mr. Do Player
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 255, 255, 255) # White clown face
            set_pixel(px, py - 1, 255, 0, 0) # Red clown hat
            set_pixel(px, py + 1, 255, 200, 0) # Yellow suit
        elif self.state == STATE_PLAYER_DIED:
            set_pixel(px, py, 255, 100, 0)

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
            "ball_active": self.ball["active"],
            "cherries_left": len(self.cherries),
        }
