"""
Game #039: 影子传说 (The Legend of Kage 1985 / Taito)
High-Flying Treetop Super Jumps, Shuriken Sniping & Kodachi Sword Projectile Parrying.
"""

import math
import random
from typing import List, Dict, Any
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

STATE_START = 0
STATE_PLAYING = 1
STATE_DEAD = 2
STATE_VICTORY = 3


class Game039LegendOfKage(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.enemies_defeated = 0
        self.target_kills = 10

        self.player_x = 8.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_grounded = True
        self.slash_timer = 0.0

        self.shurikens: List[Dict[str, Any]] = []
        self.enemy_bullets: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.tree_map: List[List[int]] = [[0 for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 39

    @property
    def name(self) -> str:
        return "影子传说"

    @property
    def english_name(self) -> str:
        return "Legend of Kage 1985"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "密林树冠超高轻功纵跃 + 远投手里剑 + 短刀近战格挡破镖招架"

    def init(self) -> None:
        self.reset()

    def init_forest(self):
        self.tree_map = [[0 for _ in range(16)] for _ in range(16)]
        for x in range(16):
            self.tree_map[14][x] = 3
            self.tree_map[15][x] = 3

        for tx in (3, 8, 13):
            for y in range(2, 14):
                self.tree_map[y][tx] = 1

        for by in (10, 6, 3):
            for tx in (3, 8, 13):
                self.tree_map[by][tx - 1] = 2
                self.tree_map[by][tx] = 2
                self.tree_map[by][tx + 1] = 2

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.enemies_defeated = 0
        self.target_kills = 10
        self.player_x = 8.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_grounded = True
        self.slash_timer = 0.0

        self.init_forest()

        self.shurikens.clear()
        self.enemy_bullets.clear()
        self.enemies = [
            {"x": 3.0, "y": 9.0, "vx": 2.5, "vy": 0.0, "is_red": False, "active": True, "shoot_timer": 1.0},
            {"x": 13.0, "y": 5.0, "vx": -2.5, "vy": 0.0, "is_red": True, "active": True, "shoot_timer": 1.5},
            {"x": 8.0, "y": 2.0, "vx": 2.0, "vy": 0.0, "is_red": False, "active": True, "shoot_timer": 2.0},
        ]

    def is_slashing(self) -> bool:
        return self.slash_timer > 0.0

    def throw_shuriken(self):
        if len(self.shurikens) < 4:
            self.shurikens.append({
                "active": True,
                "x": self.player_x + self.player_facing * 0.6,
                "y": self.player_y,
                "vx": self.player_facing * 14.0,
                "vy": 0.0,
            })

    def slash_sword(self):
        self.slash_timer = 0.22

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 8.0
                    self.player_y = 13.0
                    self.player_vx = 0.0
                    self.player_vy = 0.0
                    self.is_grounded = True
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_projectiles(dt)
        self.update_enemies(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        gravity = 20.0
        run_speed = 5.5

        self.player_vx = 0.0
        if buttons & KEY_LEFT:
            self.player_vx = -run_speed
            self.player_facing = -1
        if buttons & KEY_RIGHT:
            self.player_vx = run_speed
            self.player_facing = 1

        self.player_x += self.player_vx * dt
        self.player_x = max(0.5, min(14.5, self.player_x))

        # Super Leap
        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP) and self.is_grounded:
            self.player_vy = -13.5
            self.is_grounded = False

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.throw_shuriken()
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.slash_sword()

        if self.slash_timer > 0.0:
            self.slash_timer -= dt

        if not self.is_grounded:
            self.player_vy += gravity * dt
            self.player_y += self.player_vy * dt

            if self.player_vy >= 0.0:
                check_y = int(round(self.player_y + 1.0))
                check_x = int(round(self.player_x))
                if 0 <= check_y < 16 and 0 <= check_x < 16:
                    tile = self.tree_map[check_y][check_x]
                    if tile in (2, 3) and self.player_y <= float(check_y - 0.75):
                        self.player_y = float(check_y - 1.0)
                        self.player_vy = 0.0
                        self.is_grounded = True
        else:
            check_y = int(round(self.player_y + 1.0))
            check_x = int(round(self.player_x))
            if 0 <= check_y < 16 and 0 <= check_x < 16:
                if self.tree_map[check_y][check_x] not in (2, 3):
                    self.is_grounded = False

    def update_projectiles(self, dt: float):
        for s in self.shurikens:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            if s["x"] < 0.0 or s["x"] > 15.5:
                s["active"] = False

        for b in self.enemy_bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < 0.0 or b["x"] > 15.5 or b["y"] > 15.0:
                b["active"] = False

        self.shurikens = [s for s in self.shurikens if s["active"]]
        self.enemy_bullets = [b for b in self.enemy_bullets if b["active"]]

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"]:
                e["active"] = True
                e["x"] = 1.0 if random.choice([True, False]) else 14.0
                e["y"] = float(random.choice([10, 6, 3]) - 1)
                e["vx"] = 2.5 if e["x"] < 8.0 else -2.5
                e["is_red"] = (random.randint(0, 2) == 0)
                e["shoot_timer"] = random.uniform(1.0, 2.5)
                continue

            e["x"] += e["vx"] * dt
            if e["x"] <= 1.0:
                e["x"] = 1.0
                e["vx"] = -e["vx"]
            elif e["x"] >= 14.0:
                e["x"] = 14.0
                e["vx"] = -e["vx"]

            e["shoot_timer"] -= dt
            if e["shoot_timer"] <= 0.0:
                e["shoot_timer"] = 2.0
                if len(self.enemy_bullets) < 4:
                    dx = self.player_x - e["x"]
                    dy = self.player_y - e["y"]
                    dist = max(0.1, math.sqrt(dx * dx + dy * dy))
                    speed = 7.0
                    self.enemy_bullets.append({
                        "active": True,
                        "x": e["x"],
                        "y": e["y"],
                        "vx": (dx / dist) * speed,
                        "vy": (dy / dist) * speed,
                    })

    def check_collisions(self):
        # 1. Shuriken hits Enemy
        for s in self.shurikens:
            if not s["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                dist = abs(s["x"] - e["x"]) + abs(s["y"] - e["y"])
                if dist <= 1.1:
                    s["active"] = False
                    e["active"] = False
                    self.enemies_defeated += 1
                    pts = 300 if e["is_red"] else 100
                    self.score += pts
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if self.enemies_defeated >= self.target_kills:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
                    break

        # 2. Kodachi Sword Slash Parries Projectiles and Slashes Enemies
        if self.slash_timer > 0.0:
            for b in self.enemy_bullets:
                if not b["active"]:
                    continue
                dist = abs(self.player_x - b["x"]) + abs(self.player_y - b["y"])
                if dist <= 1.4:
                    b["active"] = False # Parried!
                    self.score += 50
                    if self.score > self.high_score:
                        self.high_score = self.score

            for e in self.enemies:
                if not e["active"]:
                    continue
                dist = abs(self.player_x - e["x"]) + abs(self.player_y - e["y"])
                if dist <= 1.35:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 200
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if self.enemies_defeated >= self.target_kills:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

        # 3. Enemy bullet hits Kage
        for b in self.enemy_bullets:
            if not b["active"]:
                continue
            dist = abs(self.player_x - b["x"]) + abs(self.player_y - b["y"])
            if dist <= 0.75:
                b["active"] = False
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        # 4. Enemy body touch Kage
        for e in self.enemies:
            if not e["active"]:
                continue
            dist = abs(self.player_x - e["x"]) + abs(self.player_y - e["y"])
            if dist <= 0.72:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        self.shurikens = [s for s in self.shurikens if s["active"]]
        self.enemy_bullets = [b for b in self.enemy_bullets if b["active"]]

    def render(self) -> bytes:
        fb = bytearray([5, 25, 17] * 256)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                tile = self.tree_map[y][x]
                if tile == 3:
                    fb[idx:idx + 3] = bytes([30, 70, 32])
                elif tile == 1:
                    fb[idx:idx + 3] = bytes([100, 60, 30])
                elif tile == 2:
                    fb[idx:idx + 3] = bytes([46, 125, 50])

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if e["is_red"]:
                    fb[idx:idx + 3] = bytes([231, 76, 60])
                else:
                    fb[idx:idx + 3] = bytes([52, 73, 94])

        # Shurikens
        for s in self.shurikens:
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            if 0 <= sx < 16 and 0 <= sy < 16:
                idx = (sy * 16 + sx) * 3
                fb[idx:idx + 3] = bytes([0, 255, 255])

        # Enemy Bullets
        for b in self.enemy_bullets:
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                fb[idx:idx + 3] = bytes([243, 156, 18])

        # Player Kage
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])
            if self.slash_timer > 0.0:
                sx = px + self.player_facing
                if 0 <= sx < 16:
                    s_idx = (py * 16 + sx) * 3
                    fb[s_idx:s_idx + 3] = bytes([255, 255, 255])

        # Lives
        for l in range(min(self.lives, 3)):
            idx = (0 * 16 + l) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "kills": self.enemies_defeated,
            "target_kills": self.target_kills,
            "player_pos": (self.player_x, self.player_y),
            "is_slashing": (self.slash_timer > 0.0),
        }
