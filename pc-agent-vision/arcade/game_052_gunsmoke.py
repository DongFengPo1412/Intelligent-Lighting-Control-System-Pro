"""
Game #052: 西部牛仔 / 荒野大镖客 (Gun.Smoke 1985 / Capcom)
Vertical Forced-Scroll Wild West Shoot'em Up with 3-Way Trajectory Aiming, Horse Armor & Wanted Boss Outlaws.
"""

import math
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

MAX_BULLETS = 6
MAX_BANDITS = 4
MAX_BARRELS = 2


class Game052GunSmoke(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 2000
        self.lives = 3

        self.player_x = 7.5
        self.player_y = 13.5
        self.has_horse = False
        self.horse_armor = 0

        self.scroll_dist = 0.0
        self.scroll_speed = 4.0

        self.boss_active = False
        self.boss_x = 7.5
        self.boss_y = 3.0
        self.boss_vx = 3.0
        self.boss_health = 8
        self.boss_shoot_cooldown = 1.5

        self.bullets: List[Dict[str, Any]] = []
        self.bandits: List[Dict[str, Any]] = []
        self.barrels: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 52

    @property
    def name(self) -> str:
        return "荒野大镖客"

    @property
    def english_name(self) -> str:
        return "Gun.Smoke"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "纵向强制卷轴推进 + 左右中三向射击锁定 + 悬赏通缉犯对决与护甲马匹"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_stage()

    def init_stage(self):
        self.player_x = 7.5
        self.player_y = 13.5
        self.has_horse = False
        self.horse_armor = 0
        self.scroll_dist = 0.0
        self.boss_active = False
        self.boss_health = 8
        self.boss_x = 7.5
        self.boss_y = 3.0
        self.boss_vx = 3.0
        self.boss_shoot_cooldown = 1.5

        self.bullets = []
        self.bandits = [
            {"x": 3.0, "y": -2.0, "vx": 1.5, "health": 1, "active": True, "cooldown": 1.2},
            {"x": 12.0, "y": -6.0, "vx": -1.8, "health": 1, "active": True, "cooldown": 2.0},
            {"x": 7.0, "y": -10.0, "vx": 1.0, "health": 1, "active": True, "cooldown": 1.5},
            {"x": 14.0, "y": -14.0, "vx": -1.2, "health": 1, "active": True, "cooldown": 2.5},
        ]
        self.barrels = [
            {"x": 4.0, "y": -5.0, "has_horse": True, "active": True},
            {"x": 11.0, "y": -12.0, "has_horse": False, "active": True},
        ]

    def shoot(self, direction: int):
        if len(self.bullets) >= MAX_BULLETS:
            return
        if direction < 0:
            vx, vy = -8.0, -16.0
        elif direction > 0:
            vx, vy = 8.0, -16.0
        else:
            vx, vy = 0.0, -20.0

        self.bullets.append({
            "x": self.player_x,
            "y": self.player_y - 1.0,
            "vx": vx,
            "vy": vy,
            "is_player": True,
            "active": True
        })

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.init_stage()
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        # Player Movement
        speed = 8.5 if self.has_horse else 6.0
        if buttons & KEY_LEFT:  self.player_x -= speed * dt
        if buttons & KEY_RIGHT: self.player_x += speed * dt
        if buttons & KEY_UP:    self.player_y -= speed * dt
        if buttons & KEY_DOWN:  self.player_y += speed * dt

        self.player_x = max(1.0, min(14.5, self.player_x))
        self.player_y = max(2.0, min(14.5, self.player_y))

        # Gun.Smoke 3-way shooting
        btn_a = bool(buttons & KEY_A)
        btn_b = bool(buttons & KEY_B)
        prev_a = bool(prev_buttons & KEY_A)
        prev_b = bool(prev_buttons & KEY_B)

        if (btn_a or btn_b) and (not prev_a or not prev_b):
            if btn_a and btn_b:
                self.shoot(0)
            elif btn_a:
                self.shoot(-1)
            else:
                self.shoot(1)

        # Scrolling terrain
        if not self.boss_active:
            self.scroll_dist += self.scroll_speed * dt
            if self.scroll_dist >= 40.0:
                self.boss_active = True
                self.boss_y = 3.0
                for b in self.bandits:
                    b["active"] = False

        # Update bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < 0.0 or b["x"] > 15.5 or b["y"] < 0.0 or b["y"] > 15.5:
                b["active"] = False

        self.bullets = [b for b in self.bullets if b["active"]]

        # Update bandits or boss
        if self.boss_active:
            self.boss_x += self.boss_vx * dt
            if self.boss_x < 3.0:
                self.boss_x = 3.0
                self.boss_vx = abs(self.boss_vx)
            elif self.boss_x > 12.0:
                self.boss_x = 12.0
                self.boss_vx = -abs(self.boss_vx)

            self.boss_shoot_cooldown -= dt
            if self.boss_shoot_cooldown <= 0.0:
                self.boss_shoot_cooldown = 1.4
                for dir in (-1, 1):
                    if len(self.bullets) < MAX_BULLETS:
                        self.bullets.append({
                            "x": self.boss_x,
                            "y": self.boss_y + 1.0,
                            "vx": dir * 4.0,
                            "vy": 9.0,
                            "is_player": False,
                            "active": True
                        })
        else:
            for b in self.bandits:
                if not b["active"]:
                    continue
                b["y"] += self.scroll_speed * dt * 0.8
                b["x"] += b["vx"] * dt
                if b["x"] < 2.0:
                    b["x"] = 2.0
                    b["vx"] = abs(b["vx"])
                elif b["x"] > 13.5:
                    b["x"] = 13.5
                    b["vx"] = -abs(b["vx"])

                if b["y"] > 16.0:
                    b["y"] = -2.0
                    b["health"] = 1

                b["cooldown"] -= dt
                if b["cooldown"] <= 0.0 and b["y"] > 1.0:
                    b["cooldown"] = 2.2
                    if len(self.bullets) < MAX_BULLETS:
                        dx = self.player_x - b["x"]
                        dy = self.player_y - b["y"]
                        dist = math.hypot(dx, dy)
                        vx = (dx / dist) * 8.0 if dist > 0.1 else 0.0
                        vy = (dy / dist) * 8.0 if dist > 0.1 else 8.0
                        self.bullets.append({
                            "x": b["x"],
                            "y": b["y"] + 1.0,
                            "vx": vx,
                            "vy": vy,
                            "is_player": False,
                            "active": True
                        })

            for r in self.barrels:
                if not r["active"]:
                    continue
                r["y"] += self.scroll_speed * dt
                if r["y"] > 16.0:
                    r["active"] = False

        # Check Collisions
        for b in self.bullets:
            if not b["active"] or not b["is_player"]:
                continue

            # Barrels
            for r in self.barrels:
                if not r["active"]:
                    continue
                if abs(b["x"] - r["x"]) < 1.2 and abs(b["y"] - r["y"]) < 1.2:
                    b["active"] = False
                    r["active"] = False
                    self.score += 50
                    if r["has_horse"]:
                        self.has_horse = True
                        self.horse_armor = 3
                        self.score += 200
                    break
            if not b["active"]:
                continue

            # Bandits
            for bandit in self.bandits:
                if not bandit["active"]:
                    continue
                if abs(b["x"] - bandit["x"]) < 1.1 and abs(b["y"] - bandit["y"]) < 1.1:
                    b["active"] = False
                    bandit["health"] -= 1
                    if bandit["health"] <= 0:
                        bandit["active"] = False
                        self.score += 100
                    break
            if not b["active"]:
                continue

            # Boss
            if self.boss_active:
                if abs(b["x"] - self.boss_x) < 1.6 and abs(b["y"] - self.boss_y) < 1.6:
                    b["active"] = False
                    self.boss_health -= 1
                    self.score += 50
                    if self.boss_health <= 0:
                        self.boss_active = False
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

        # Enemy bullets hit player
        for b in self.bullets:
            if not b["active"] or b["is_player"]:
                continue
            if abs(b["x"] - self.player_x) < 0.9 and abs(b["y"] - self.player_y) < 0.9:
                b["active"] = False
                if self.has_horse:
                    self.horse_armor -= 1
                    if self.horse_armor <= 0:
                        self.has_horse = False
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # Direct bandit body contact
        for bandit in self.bandits:
            if not bandit["active"]:
                continue
            if abs(bandit["x"] - self.player_x) < 0.9 and abs(bandit["y"] - self.player_y) < 0.9:
                if self.has_horse:
                    self.has_horse = False
                    bandit["active"] = False
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        offset = int(self.scroll_dist) % 4
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 120
                fb[idx + 1] = 90
                fb[idx + 2] = 40
                if x == 0 or x == 15:
                    fb[idx] = 80
                    fb[idx + 1] = 50
                    fb[idx + 2] = 20
                elif (y + offset) % 6 == 0 and (x % 3 == 0):
                    fb[idx] = 150
                    fb[idx + 1] = 110
                    fb[idx + 2] = 50

        # Barrels
        for r in self.barrels:
            if r["active"]:
                rx = int(round(r["x"]))
                ry = int(round(r["y"]))
                if 0 <= rx < 16 and 0 <= ry < 16:
                    idx = (ry * 16 + rx) * 3
                    fb[idx] = 180
                    fb[idx + 1] = 100
                    fb[idx + 2] = 20

        # Bandits
        for b in self.bandits:
            if b["active"]:
                bx = int(round(b["x"]))
                by = int(round(b["y"]))
                if 0 <= bx < 16 and 0 <= by < 16:
                    idx = (by * 16 + bx) * 3
                    fb[idx] = 40
                    fb[idx + 1] = 80
                    fb[idx + 2] = 200

        # Boss
        if self.boss_active:
            bx = int(round(self.boss_x))
            by = int(round(self.boss_y))
            for dy in range(2):
                for dx in (-1, 0, 1):
                    px = bx + dx
                    py = by + dy
                    if 0 <= px < 16 and 0 <= py < 16:
                        idx = (py * 16 + px) * 3
                        fb[idx] = 255
                        fb[idx + 1] = 20
                        fb[idx + 2] = 20

        # Bullets
        for b in self.bullets:
            if b["active"]:
                bx = int(round(b["x"]))
                by = int(round(b["y"]))
                if 0 <= bx < 16 and 0 <= py if False else (0 <= bx < 16 and 0 <= by < 16):
                    idx = (by * 16 + bx) * 3
                    if b["is_player"]:
                        fb[idx] = 255
                        fb[idx + 1] = 240
                        fb[idx + 2] = 50
                    else:
                        fb[idx] = 255
                        fb[idx + 1] = 50
                        fb[idx + 2] = 50

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx] = 255
            fb[idx + 1] = 255
            fb[idx + 2] = 255
            if self.has_horse:
                if px > 0:
                    left_idx = (py * 16 + (px - 1)) * 3
                    fb[left_idx] = 160
                    fb[left_idx + 1] = 82
                    fb[left_idx + 2] = 45
                if px < 15:
                    right_idx = (py * 16 + (px + 1)) * 3
                    fb[right_idx] = 160
                    fb[right_idx + 1] = 82
                    fb[right_idx + 2] = 45

        # HUD
        for l in range(min(self.lives, 4)):
            idx = l * 3
            fb[idx] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 0

        for a in range(self.horse_armor):
            idx = (15 - a) * 3
            fb[idx] = 255
            fb[idx + 1] = 165
            fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "has_horse": self.has_horse,
            "horse_armor": self.horse_armor,
            "scroll_dist": self.scroll_dist,
            "boss_active": self.boss_active,
            "boss_health": self.boss_health,
        }
