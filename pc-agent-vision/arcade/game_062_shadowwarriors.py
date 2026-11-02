"""
Game #062: 影武者 / 影子传说2 (Shadow Warriors 1988 / Tecmo / Sega)
Ninja Action with Trailing Shadow Clone Doppelgangers, Shinobi Hound Companion & Vertical Wall Clinging.
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

MAX_ENEMIES = 4
MAX_CLONES = 2
HISTORY_LEN = 20


class Game062ShadowWarriors(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 4000
        self.lives = 3
        self.player_health = 100
        self.enemies_defeated = 0
        self.total_enemies = 4

        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_slashing = False
        self.slash_timer = 0.0
        self.is_wall_clinging = False

        self.history_x = [self.player_x] * HISTORY_LEN
        self.history_y = [self.player_y] * HISTORY_LEN
        self.history_facing = [self.player_facing] * HISTORY_LEN
        self.history_slashing = [False] * HISTORY_LEN
        self.history_idx = 0
        self.num_clones = 1

        self.dog_active = False
        self.dog_x = 0.0
        self.dog_y = 13.0
        self.dog_vx = 0.0
        self.dog_timer = 0.0

        self.fireball: Dict[str, Any] = {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False}
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 62

    @property
    def name(self) -> str:
        return "影武者"

    @property
    def english_name(self) -> str:
        return "Shadow Warriors"

    @property
    def release_year(self) -> int:
        return 1988

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "忍犬协助伙伴召唤与自动突咬 + 双影分身残影跟随攻击 + 飞檐攀爬与忍术火龙弹"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_health = 100
        self.num_clones = 1
        self.init_stage()

    def init_stage(self):
        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_slashing = False
        self.slash_timer = 0.0
        self.is_wall_clinging = False

        self.history_x = [self.player_x] * HISTORY_LEN
        self.history_y = [self.player_y] * HISTORY_LEN
        self.history_facing = [self.player_facing] * HISTORY_LEN
        self.history_slashing = [False] * HISTORY_LEN
        self.history_idx = 0

        self.dog_active = False
        self.dog_timer = 0.0
        self.fireball["active"] = False

        self.enemies_defeated = 0
        self.enemies = [
            {"x": 8.0, "y": 13.0, "vx": -2.0, "health": 1, "active": True},
            {"x": 12.0, "y": 13.0, "vx": -1.8, "health": 1, "active": True},
            {"x": 9.0, "y": 7.0, "vx": -1.2, "health": 1, "active": True},
            {"x": 14.0, "y": 13.0, "vx": -1.5, "health": 3, "active": True},
        ]
        self.total_enemies = len(self.enemies)

    def summon_dog(self):
        if not self.dog_active:
            self.dog_active = True
            self.dog_x = self.player_x
            self.dog_y = 13.0
            self.dog_vx = self.player_facing * 12.0
            self.dog_timer = 3.0

    def add_shadow_clone(self):
        if self.num_clones < MAX_CLONES:
            self.num_clones += 1

    def trigger_fire_dragon(self):
        if not self.fireball["active"]:
            self.fireball["active"] = True
            self.fireball["x"] = self.player_x + self.player_facing * 1.0
            self.fireball["y"] = self.player_y - 0.5
            self.fireball["vx"] = self.player_facing * 8.0
            self.fireball["vy"] = -10.0

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_health = 100
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

        # Player slash timer
        if self.is_slashing:
            self.slash_timer -= dt
            if self.slash_timer <= 0.0:
                self.is_slashing = False

        # Wall clinging check
        if (self.player_x <= 1.0 and (buttons & KEY_LEFT)) or \
           (self.player_x >= 14.5 and (buttons & KEY_RIGHT)):
            self.is_wall_clinging = True
            self.player_vy = 0.0
            if buttons & KEY_UP:   self.player_y -= 5.0 * dt
            if buttons & KEY_DOWN: self.player_y += 5.0 * dt
        else:
            self.is_wall_clinging = False

        # Horizontal move
        if not self.is_wall_clinging:
            speed = 6.0
            self.player_vx = 0.0
            if buttons & KEY_LEFT:  self.player_vx = -speed; self.player_facing = -1
            if buttons & KEY_RIGHT: self.player_vx = speed;  self.player_facing = 1

            self.player_x += self.player_vx * dt

            # Gravity jump
            self.player_y += self.player_vy * dt
            self.player_vy += 30.0 * dt
            if self.player_y >= 13.0:
                self.player_y = 13.0
                self.player_vy = 0.0

            if (buttons & KEY_UP) and not (prev_buttons & KEY_UP) and self.player_y >= 12.9:
                self.player_vy = -12.0

        self.player_x = max(1.0, min(14.5, self.player_x))
        self.player_y = max(2.0, min(13.0, self.player_y))

        # Button A attack
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.is_slashing = True
            self.slash_timer = 0.18

            for e in self.enemies:
                if not e["active"]:
                    continue
                dx = e["x"] - self.player_x
                dy = e["y"] - self.player_y
                if abs(dx) < 1.6 and abs(dy) < 1.2 and (dx * self.player_facing >= 0):
                    e["health"] -= 1
                    self.score += 100
                    if e["health"] <= 0:
                        e["active"] = False
                        self.enemies_defeated += 1
                        self.score += 150

        # Button B summon hound
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.summon_dog()

        # Update clones
        self.history_x[self.history_idx] = self.player_x
        self.history_y[self.history_idx] = self.player_y
        self.history_facing[self.history_idx] = self.player_facing
        self.history_slashing[self.history_idx] = self.is_slashing

        self.history_idx = (self.history_idx + 1) % HISTORY_LEN

        for c in range(1, self.num_clones + 1):
            delay = c * 6
            idx = (self.history_idx - delay + HISTORY_LEN) % HISTORY_LEN
            if self.history_slashing[idx]:
                cx = self.history_x[idx]
                cy = self.history_y[idx]
                cf = self.history_facing[idx]
                for e in self.enemies:
                    if not e["active"]:
                        continue
                    dx = e["x"] - cx
                    dy = e["y"] - cy
                    if abs(dx) < 1.6 and abs(dy) < 1.2 and (dx * cf >= 0):
                        e["health"] -= 1
                        self.score += 50
                        if e["health"] <= 0:
                            e["active"] = False
                            self.enemies_defeated += 1

        # Update dog
        if self.dog_active:
            self.dog_x += self.dog_vx * dt
            self.dog_timer -= dt
            if self.dog_x < 0.0 or self.dog_x > 15.5 or self.dog_timer <= 0.0:
                self.dog_active = False
            else:
                for e in self.enemies:
                    if not e["active"]:
                        continue
                    if abs(self.dog_x - e["x"]) < 1.3 and abs(self.dog_y - e["y"]) < 1.2:
                        e["health"] -= 2
                        self.score += 150
                        if e["health"] <= 0:
                            e["active"] = False
                            self.enemies_defeated += 1
                        break

        # Update enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            e["x"] += e["vx"] * dt
            if e["x"] < 2.0:
                e["x"] = 2.0
                e["vx"] = abs(e["vx"])
            elif e["x"] > 14.0:
                e["x"] = 14.0
                e["vx"] = -abs(e["vx"])

        # Collisions: Enemy on player
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - self.player_x) < 0.8 and abs(e["y"] - self.player_y) < 0.8:
                self.player_health -= 20
                if self.player_health <= 0:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # Victory
        if self.enemies_defeated >= self.total_enemies:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1200
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Background
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 10; fb[idx + 1] = 15; fb[idx + 2] = 35
                if y == 8 and 4 <= x <= 12:
                    fb[idx] = 60; fb[idx + 1] = 60; fb[idx + 2] = 80
                if y == 14:
                    fb[idx] = 50; fb[idx + 1] = 40; fb[idx + 2] = 40

        # Enemies
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if i == 3:
                    fb[idx] = 255; fb[idx + 1] = 30; fb[idx + 2] = 30
                else:
                    fb[idx] = 160; fb[idx + 1] = 40; fb[idx + 2] = 180

        # Clones
        for c in range(1, self.num_clones + 1):
            delay = c * 6
            idx_h = (self.history_idx - delay + HISTORY_LEN) % HISTORY_LEN
            cx = int(round(self.history_x[idx_h]))
            cy = int(round(self.history_y[idx_h]))
            cf = self.history_facing[idx_h]
            if 0 <= cx < 16 and 0 <= cy < 16:
                p_idx = (cy * 16 + cx) * 3
                fb[p_idx] = 255; fb[p_idx + 1] = 60; fb[p_idx + 2] = 20
                if self.history_slashing[idx_h]:
                    csx = cx + cf
                    if 0 <= csx < 16:
                        s_idx = (cy * 16 + csx) * 3
                        fb[s_idx] = 255; fb[s_idx + 1] = 180; fb[s_idx + 2] = 0

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx] = 30; fb[idx + 1] = 90; fb[idx + 2] = 240
            if self.is_slashing:
                sx = px + self.player_facing
                if 0 <= sx < 16:
                    s_idx = (py * 16 + sx) * 3
                    fb[s_idx] = 200; fb[s_idx + 1] = 240; fb[s_idx + 2] = 255

        # Dog
        if self.dog_active:
            dx = int(round(self.dog_x))
            dy = int(round(self.dog_y))
            if 0 <= dx < 16 and 0 <= dy < 16:
                idx = (dy * 16 + dx) * 3
                fb[idx] = 200; fb[idx + 1] = 200; fb[idx + 2] = 210

        # HUD
        hp_bars = (self.player_health * 5) // 100
        for h in range(min(hp_bars, 5)):
            idx = h * 3
            fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 0

        for c in range(self.num_clones):
            idx = (15 - c) * 3
            fb[idx] = 255; fb[idx + 1] = 50; fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "health": self.player_health,
            "num_clones": self.num_clones,
            "dog_active": self.dog_active,
            "enemies_remaining": sum(1 for e in self.enemies if e["active"]),
        }
