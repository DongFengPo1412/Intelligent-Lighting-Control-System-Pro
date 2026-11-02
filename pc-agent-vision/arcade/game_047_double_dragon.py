"""
Game #047: 热血快打 / 双截龙街机版 (Double Dragon 1987 / Technos)
2.5D Belt-Scrolling Beat 'Em Up with Punches, Kicks, Elbow Smashes, Weapon Pickups & Enemy Knockdowns.
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

MAX_ENEMIES = 3


class Game047DoubleDragon(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.player_health = 100
        self.enemies_defeated = 0
        self.total_wave_enemies = 4

        self.player_x = 2.0
        self.player_y = 11.0
        self.player_facing = 1
        self.has_weapon = False

        self.attack_type = 0  # 0: None, 1: Punch, 2: Kick, 3: Elbow
        self.attack_timer = 0.0
        self.attack_duration = 0.22

        self.enemies: List[Dict[str, Any]] = []
        self.weapon: Dict[str, Any] = {"x": 7.0, "y": 10.0, "on_ground": True}

        self.reset()

    @property
    def game_id(self) -> int:
        return 47

    @property
    def name(self) -> str:
        return "热血快打"

    @property
    def english_name(self) -> str:
        return "Double Dragon (1987)"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "2.5D街头清版搏击 + 组合拳回旋踢与铁肘反制 + 缴械铁棒挥舞与倒地硬直"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.player_health = 100
        self.enemies_defeated = 0
        self.total_wave_enemies = 4
        self.player_x = 2.0
        self.player_y = 11.0
        self.player_facing = 1
        self.has_weapon = False
        self.attack_type = 0
        self.attack_timer = 0.0

        self.weapon = {"x": 7.0, "y": 10.0, "on_ground": True}
        self.init_arena()

    def init_arena(self):
        self.enemies = [
            {"x": 13.0, "y": 10.0, "health": 30, "active": True, "is_knocked_down": False, "knockdown_timer": 0.0, "attack_cooldown": 0.8},
            {"x": 14.0, "y": 12.0, "health": 30, "active": True, "is_knocked_down": False, "knockdown_timer": 0.0, "attack_cooldown": 1.2},
            {"x": 11.0, "y": 9.0, "health": 30, "active": True, "is_knocked_down": False, "knockdown_timer": 0.0, "attack_cooldown": 1.6},
        ]

    def get_enemies_remaining(self) -> int:
        return self.total_wave_enemies - self.enemies_defeated

    def attack_punch(self):
        if self.attack_timer > 0.0:
            return
        self.attack_type = 1
        self.attack_timer = self.attack_duration

    def attack_kick(self):
        if self.attack_timer > 0.0:
            return
        self.attack_type = 2
        self.attack_timer = self.attack_duration + 0.05

    def attack_elbow(self):
        if self.attack_timer > 0.0:
            return
        self.attack_type = 3
        self.attack_timer = self.attack_duration + 0.1

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        walk_speed = 5.2

        if self.attack_timer > 0.0:
            self.attack_timer -= dt
            if self.attack_timer <= 0.0:
                self.attack_type = 0

        if self.attack_timer <= 0.0:
            vx = 0.0
            vy = 0.0
            if buttons & KEY_LEFT:
                vx = -walk_speed
                self.player_facing = -1
            if buttons & KEY_RIGHT:
                vx = walk_speed
                self.player_facing = 1
            if buttons & KEY_UP:
                vy = -walk_speed * 0.75
            if buttons & KEY_DOWN:
                vy = walk_speed * 0.75

            self.player_x += vx * dt
            self.player_y += vy * dt

            self.player_x = max(0.5, min(15.0, self.player_x))
            self.player_y = max(8.0, min(14.0, self.player_y))

            # Attacks
            if (buttons & KEY_A) and (buttons & KEY_B):
                self.attack_elbow()
            elif (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.attack_punch()
            elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.attack_kick()

            # Weapon pickup
            if self.weapon["on_ground"]:
                dist = abs(self.player_x - self.weapon["x"]) + abs(self.player_y - self.weapon["y"])
                if dist <= 0.85:
                    self.has_weapon = True
                    self.weapon["on_ground"] = False
                    self.score += 50
                    if self.score > self.high_score:
                        self.high_score = self.score

    def update_enemies(self, dt: float):
        enemy_speed = 2.6

        for e in self.enemies:
            if not e["active"]:
                continue

            if e["is_knocked_down"]:
                e["knockdown_timer"] -= dt
                if e["knockdown_timer"] <= 0.0:
                    e["is_knocked_down"] = False
                continue

            dx = self.player_x - e["x"]
            dy = self.player_y - e["y"]

            if abs(dx) > 0.8:
                e["x"] += (enemy_speed if dx > 0 else -enemy_speed) * dt
            if abs(dy) > 0.4:
                e["y"] += (enemy_speed * 0.6 if dy > 0 else -enemy_speed * 0.6) * dt

            e["x"] = max(0.5, min(15.0, e["x"]))
            e["y"] = max(8.0, min(14.0, e["y"]))

            if e["attack_cooldown"] > 0.0:
                e["attack_cooldown"] -= dt
            else:
                if abs(dx) <= 1.0 and abs(dy) <= 0.5:
                    self.player_health -= 10
                    e["attack_cooldown"] = 1.2
                    if self.player_health <= 0:
                        self.player_health = 0
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

    def check_hitboxes(self):
        if self.attack_type == 0:
            return

        range_x = 1.6 if self.has_weapon else 1.2
        range_y = 0.65
        dmg = 25 if (self.attack_type == 1 and self.has_weapon) else (12 if self.attack_type == 1 else (18 if self.attack_type == 2 else 35))

        for e in self.enemies:
            if not e["active"] or e["is_knocked_down"]:
                continue

            dx = e["x"] - self.player_x
            dy = abs(e["y"] - self.player_y)

            in_front = (self.player_facing > 0 and 0.0 <= dx <= range_x) or (self.player_facing < 0 and -range_x <= dx <= 0.0)

            if in_front and dy <= range_y:
                e["health"] -= dmg
                self.score += dmg * 5
                if self.score > self.high_score:
                    self.high_score = self.score

                e["x"] += self.player_facing * 1.2

                if e["health"] <= 0:
                    e["active"] = False
                    self.enemies_defeated += 1
                    if self.enemies_defeated >= self.total_wave_enemies:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
                elif self.attack_type >= 2 or e["health"] <= 15:
                    e["is_knocked_down"] = True
                    e["knockdown_timer"] = 1.4

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.check_hitboxes()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # 1. Slum Brick Wall
        for y in range(8):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx + 0] = 50
                fb[idx + 1] = 20
                fb[idx + 2] = 20

        # HUD Health Bar on row 0
        hp_bars = (self.player_health * 7) // 100
        for x in range(8):
            idx = (0 * 16 + x) * 3
            if x < hp_bars:
                fb[idx + 0] = 46
                fb[idx + 1] = 204
                fb[idx + 2] = 113

        # 2. Street Asphalt
        for y in range(8, 16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx + 0] = 30
                fb[idx + 1] = 35
                fb[idx + 2] = 40

        # 3. Dropped Weapon
        if self.weapon["on_ground"]:
            wx = int(round(self.weapon["x"]))
            wy = int(round(self.weapon["y"]))
            if 0 <= wx < 16 and 0 <= wy < 16:
                idx = (wy * 16 + wx) * 3
                fb[idx + 0] = 241
                fb[idx + 1] = 196
                fb[idx + 2] = 15

        # 4. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if e["is_knocked_down"]:
                    fb[idx + 0] = 180
                    fb[idx + 1] = 100
                    fb[idx + 2] = 80
                else:
                    fb[idx + 0] = 231
                    fb[idx + 1] = 76
                    fb[idx + 2] = 60

        # 5. Player Billy Lee
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            if self.attack_type != 0:
                fb[idx + 0] = 243
                fb[idx + 1] = 156
                fb[idx + 2] = 18
            else:
                fb[idx + 0] = 41
                fb[idx + 1] = 128
                fb[idx + 2] = 185

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "player_health": self.player_health,
            "enemies_remaining": self.get_enemies_remaining(),
            "has_weapon": self.has_weapon,
            "player_x": self.player_x,
            "player_y": self.player_y,
            "player_facing": self.player_facing,
            "attack_type": self.attack_type,
        }
