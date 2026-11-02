"""
Game #056: 太平洋空战 / 1942 (1942 1984 / Capcom)
WWII Pacific Shmup with Stunt Loop-the-Loop Evades, Dual Wingmen Escorts & Giant Ayako Bomber Boss.
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

MAX_BULLETS = 8
MAX_PLANES = 5


class Game056_1942(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 4000
        self.lives = 3

        self.player_x = 7.5
        self.player_y = 13.5
        self.is_looping = False
        self.loop_timer = 0.0
        self.loops_remaining = 3
        self.has_wingmen = False

        self.scroll_y = 0.0
        self.planes_defeated = 0

        self.boss_active = False
        self.boss_x = 7.5
        self.boss_y = 3.0
        self.boss_vx = 2.5
        self.boss_health = 10
        self.boss_shoot_cooldown = 1.2

        self.bullets: List[Dict[str, Any]] = []
        self.planes: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 56

    @property
    def name(self) -> str:
        return "太平洋空战"

    @property
    def english_name(self) -> str:
        return "1942"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "战机空中大回旋翻滚特技避弹 + 护航僚机合体 + 巨型重轰炸机BOSS对决"

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
        self.is_looping = False
        self.loop_timer = 0.0
        self.loops_remaining = 3
        self.has_wingmen = False
        self.scroll_y = 0.0
        self.planes_defeated = 0

        self.boss_active = False
        self.boss_x = 7.5
        self.boss_y = 3.0
        self.boss_vx = 2.5
        self.boss_health = 10
        self.boss_shoot_cooldown = 1.2

        self.bullets = []
        self.planes = [
            {"x": 3.0, "y": -2.0, "vx": 1.2, "vy": 2.5, "type": 0, "health": 1, "active": True, "cooldown": 1.5},
            {"x": 12.0, "y": -4.0, "vx": -1.2, "vy": 2.2, "type": 0, "health": 1, "active": True, "cooldown": 2.0},
            {"x": 7.5, "y": -6.0, "vx": 0.0, "vy": 3.0, "type": 1, "health": 1, "active": True, "cooldown": 1.8},
            {"x": 4.0, "y": -9.0, "vx": 1.5, "vy": 2.0, "type": 0, "health": 1, "active": True, "cooldown": 2.2},
            {"x": 11.0, "y": -12.0, "vx": -1.5, "vy": 2.0, "type": 0, "health": 1, "active": True, "cooldown": 1.6},
        ]

    def trigger_loop(self):
        if not self.is_looping and self.loops_remaining > 0:
            self.is_looping = True
            self.loop_timer = 0.6
            self.loops_remaining -= 1

    def fire_bullets(self):
        if len(self.bullets) < MAX_BULLETS:
            self.bullets.append({
                "x": self.player_x,
                "y": self.player_y - 1.0,
                "vx": 0.0,
                "vy": -18.0,
                "is_player": True,
                "active": True
            })

        if self.has_wingmen:
            for side in (-1, 1):
                if len(self.bullets) < MAX_BULLETS:
                    self.bullets.append({
                        "x": self.player_x + side * 1.5,
                        "y": self.player_y - 0.5,
                        "vx": side * 1.5,
                        "vy": -18.0,
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

        self.scroll_y += 6.0 * dt

        # Player Loop stunt
        if self.is_looping:
            self.loop_timer -= dt
            if self.loop_timer <= 0.0:
                self.is_looping = False
        else:
            speed = 7.0
            if buttons & KEY_LEFT:  self.player_x -= speed * dt
            if buttons & KEY_RIGHT: self.player_x += speed * dt
            if buttons & KEY_UP:    self.player_y -= speed * dt
            if buttons & KEY_DOWN:  self.player_y += speed * dt

            self.player_x = max(1.0, min(14.5, self.player_x))
            self.player_y = max(2.0, min(14.5, self.player_y))

            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.trigger_loop()

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.fire_bullets()

        # Update bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < 0.0 or b["x"] > 15.5 or b["y"] < 0.0 or b["y"] > 15.5:
                b["active"] = False

        self.bullets = [b for b in self.bullets if b["active"]]

        # Update planes or boss
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
                self.boss_shoot_cooldown = 1.3
                for dir in (-1, 0, 1):
                    if len(self.bullets) < MAX_BULLETS:
                        self.bullets.append({
                            "x": self.boss_x + dir * 1.5,
                            "y": self.boss_y + 1.5,
                            "vx": dir * 4.0,
                            "vy": 7.5,
                            "is_player": False,
                            "active": True
                        })
        else:
            for p in self.planes:
                if not p["active"]:
                    continue
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt

                if p["x"] < 1.0:
                    p["x"] = 1.0
                    p["vx"] = abs(p["vx"])
                elif p["x"] > 14.5:
                    p["x"] = 14.5
                    p["vx"] = -abs(p["vx"])

                if p["y"] > 16.0:
                    p["y"] = -2.0
                    p["health"] = 1

                p["cooldown"] -= dt
                if p["cooldown"] <= 0.0 and p["y"] > 1.0:
                    p["cooldown"] = 2.0
                    if len(self.bullets) < MAX_BULLETS:
                        self.bullets.append({
                            "x": p["x"],
                            "y": p["y"] + 1.0,
                            "vx": 2.5 if self.player_x > p["x"] else -2.5,
                            "vy": 8.0,
                            "is_player": False,
                            "active": True
                        })

            if self.planes_defeated >= 5:
                self.boss_active = True
                self.boss_y = 3.0
                for p in self.planes:
                    p["active"] = False

        # Collisions: Player bullets
        for b in self.bullets:
            if not b["active"] or not b["is_player"]:
                continue

            if self.boss_active:
                if abs(b["x"] - self.boss_x) < 2.2 and abs(b["y"] - self.boss_y) < 1.6:
                    b["active"] = False
                    self.boss_health -= 1
                    self.score += 50
                    if self.boss_health <= 0:
                        self.boss_active = False
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1500
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
            else:
                for p in self.planes:
                    if not p["active"]:
                        continue
                    if abs(b["x"] - p["x"]) < 1.2 and abs(b["y"] - p["y"]) < 1.2:
                        b["active"] = False
                        p["health"] -= 1
                        if p["health"] <= 0:
                            p["active"] = False
                            self.planes_defeated += 1
                            self.score += 200 if p["type"] == 1 else 100
                            if p["type"] == 1:
                                self.has_wingmen = True
                            if self.planes_defeated >= 5:
                                self.boss_active = True
                                self.boss_y = 3.0
                                for plane in self.planes:
                                    plane["active"] = False
                        break

        # If looping, player is 100% immune to bullets and crashes
        if self.is_looping:
            return

        # Enemy bullets hit player
        for b in self.bullets:
            if not b["active"] or b["is_player"]:
                continue
            if abs(b["x"] - self.player_x) < 0.9 and abs(b["y"] - self.player_y) < 0.9:
                b["active"] = False
                if self.has_wingmen:
                    self.has_wingmen = False
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # Direct plane collision
        for p in self.planes:
            if not p["active"]:
                continue
            if abs(p["x"] - self.player_x) < 1.0 and abs(p["y"] - self.player_y) < 1.0:
                p["active"] = False
                if self.has_wingmen:
                    self.has_wingmen = False
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        wave_offset = int(self.scroll_y) % 6
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 10
                fb[idx + 1] = 40
                fb[idx + 2] = 120
                if (y + wave_offset) % 5 == 0 and (x % 4 == 0):
                    fb[idx] = 40
                    fb[idx + 1] = 90
                    fb[idx + 2] = 180

        # Planes
        for p in self.planes:
            if p["active"]:
                px = int(round(p["x"]))
                py = int(round(p["y"]))
                if 0 <= px < 16 and 0 <= py < 16:
                    idx = (py * 16 + px) * 3
                    if p["type"] == 1:
                        fb[idx] = 255
                        fb[idx + 1] = 40
                        fb[idx + 2] = 40
                    else:
                        fb[idx] = 40
                        fb[idx + 1] = 180
                        fb[idx + 2] = 50

        # Boss
        if self.boss_active:
            bx = int(round(self.boss_x))
            by = int(round(self.boss_y))
            for dy in (-1, 0, 1):
                for dx in (-2, -1, 0, 1, 2):
                    px = bx + dx
                    py = by + dy
                    if 0 <= px < 16 and 0 <= py < 16:
                        idx = (py * 16 + px) * 3
                        fb[idx] = 150
                        fb[idx + 1] = 120
                        fb[idx + 2] = 40

        # Bullets
        for b in self.bullets:
            if b["active"]:
                bx = int(round(b["x"]))
                by = int(round(b["y"]))
                if 0 <= bx < 16 and 0 <= by < 16:
                    idx = (by * 16 + bx) * 3
                    if b["is_player"]:
                        fb[idx] = 255
                        fb[idx + 1] = 255
                        fb[idx + 2] = 80
                    else:
                        fb[idx] = 255
                        fb[idx + 1] = 40
                        fb[idx + 2] = 40

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            if self.is_looping:
                fb[idx] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 255
            else:
                fb[idx] = 220
                fb[idx + 1] = 220
                fb[idx + 2] = 240
                if self.has_wingmen:
                    if px > 1:
                        left_idx = (py * 16 + (px - 2)) * 3
                        fb[left_idx] = 180
                        fb[left_idx + 1] = 200
                        fb[left_idx + 2] = 255
                    if px < 14:
                        right_idx = (py * 16 + (px + 2)) * 3
                        fb[right_idx] = 180
                        fb[right_idx + 1] = 200
                        fb[right_idx + 2] = 255

        # HUD
        for l in range(min(self.lives, 3)):
            idx = l * 3
            fb[idx] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 0

        for r in range(self.loops_remaining):
            idx = (15 - r) * 3
            fb[idx] = 255
            fb[idx + 1] = 200
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
            "is_looping": self.is_looping,
            "loops_remaining": self.loops_remaining,
            "has_wingmen": self.has_wingmen,
            "boss_active": self.boss_active,
            "boss_health": self.boss_health,
        }
