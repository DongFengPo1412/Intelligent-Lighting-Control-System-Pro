"""
Game #051: 影子忍者 / 忍之之道 (Shinobi 1987 / Sega)
Dual-Tier Balcony Leaping Ninja Action with Hostage Rescues, Close/Ranged Combat, Gun Upgrades & Ninjutsu.
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
    KEY_SELECT,
)

STATE_START = 0
STATE_PLAYING = 1
STATE_DEAD = 2
STATE_VICTORY = 3

MAX_ENEMIES = 4
MAX_SHURIKENS = 3
MAX_HOSTAGES = 2


class Game051Shinobi(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 1000
        self.lives = 3
        self.hostages_rescued = 0
        self.enemies_defeated = 0
        self.total_enemies = 4

        self.player_x = 1.0
        self.player_tier = 1  # 0: Upper (y=7), 1: Lower (y=13)
        self.player_facing = 1  # +1 right, -1 left
        self.is_crouching = False
        self.is_leaping_tier = False
        self.leap_progress = 0.0
        self.is_melee_slashing = False
        self.melee_timer = 0.0

        self.has_gun_upgrade = False
        self.has_ninjutsu = True
        self.ninjutsu_flash_timer = 0.0

        self.enemies: List[Dict[str, Any]] = []
        self.shurikens: List[Dict[str, Any]] = []
        self.hostages: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 51

    @property
    def name(self) -> str:
        return "影子忍者"

    @property
    def english_name(self) -> str:
        return "Shinobi"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双层楼阁纵向跳跃突袭 + 近身刀斩远程手里剑/手枪 + 人质解救升级与全屏忍术"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.has_gun_upgrade = False
        self.has_ninjutsu = True
        self.ninjutsu_flash_timer = 0.0
        self.init_stage()

    def init_stage(self):
        self.player_x = 1.0
        self.player_tier = 1
        self.player_facing = 1
        self.is_crouching = False
        self.is_leaping_tier = False
        self.leap_progress = 0.0
        self.is_melee_slashing = False
        self.melee_timer = 0.0
        self.hostages_rescued = 0
        self.enemies_defeated = 0

        self.hostages = [
            {"x": 6.0, "tier": 0, "rescued": False},
            {"x": 11.0, "tier": 1, "rescued": False},
        ]

        self.enemies = [
            {"x": 8.0, "tier": 1, "vx": -1.5, "health": 1, "active": True, "cooldown": 2.0},
            {"x": 14.0, "tier": 1, "vx": -2.0, "health": 1, "active": True, "cooldown": 1.5},
            {"x": 10.0, "tier": 0, "vx": -1.0, "health": 1, "active": True, "cooldown": 2.5},
            {"x": 13.0, "tier": 0, "vx": -1.2, "health": 2, "active": True, "cooldown": 1.8},
        ]
        self.total_enemies = len(self.enemies)
        self.shurikens = []

    def get_hostages_remaining(self) -> int:
        return sum(1 for h in self.hostages if not h["rescued"])

    def throw_shuriken(self):
        if len(self.shurikens) >= MAX_SHURIKENS:
            return
        speed = 18.0 if self.has_gun_upgrade else 12.0
        self.shurikens.append({
            "x": self.player_x + (1.0 if self.player_facing > 0 else -1.0),
            "tier": self.player_tier,
            "vx": speed * self.player_facing,
            "is_gunshot": self.has_gun_upgrade,
            "is_player": True,
            "active": True
        })

    def trigger_ninjutsu(self):
        if not self.has_ninjutsu:
            return
        self.has_ninjutsu = False
        self.ninjutsu_flash_timer = 0.6
        for e in self.enemies:
            if e["active"]:
                e["active"] = False
                self.enemies_defeated += 1
                self.score += 200

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

        if self.ninjutsu_flash_timer > 0.0:
            self.ninjutsu_flash_timer -= dt

        # Update player
        if self.is_melee_slashing:
            self.melee_timer -= dt
            if self.melee_timer <= 0.0:
                self.is_melee_slashing = False

        if self.is_leaping_tier:
            self.leap_progress += dt * 3.5
            if self.leap_progress >= 1.0:
                self.is_leaping_tier = False
                self.leap_progress = 0.0
                self.player_tier = 1 - self.player_tier
        else:
            # Crouching
            self.is_crouching = bool(buttons & KEY_DOWN)

            # Move horizontally
            if not self.is_crouching:
                if buttons & KEY_LEFT:
                    self.player_x -= 5.0 * dt
                    self.player_facing = -1
                elif buttons & KEY_RIGHT:
                    self.player_x += 5.0 * dt
                    self.player_facing = 1

            self.player_x = max(0.5, min(15.0, self.player_x))

            # Leap tier: Button B
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.is_leaping_tier = True
                self.leap_progress = 0.0

            # Ninjutsu: SELECT
            if (buttons & KEY_SELECT) and not (prev_buttons & KEY_SELECT):
                self.trigger_ninjutsu()

            # Attack: Button A
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                # Melee check if enemy close on same tier
                melee_hit = False
                for e in self.enemies:
                    if e["active"] and e["tier"] == self.player_tier:
                        if abs(e["x"] - self.player_x) <= 1.8:
                            e["health"] -= 2
                            if e["health"] <= 0:
                                e["active"] = False
                                self.enemies_defeated += 1
                                self.score += 100
                            melee_hit = True

                if melee_hit:
                    self.is_melee_slashing = True
                    self.melee_timer = 0.2
                else:
                    self.throw_shuriken()

        # Update enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            e["x"] += e["vx"] * dt
            if e["x"] < 2.0:
                e["x"] = 2.0
                e["vx"] = abs(e["vx"])
            elif e["x"] > 14.5:
                e["x"] = 14.5
                e["vx"] = -abs(e["vx"])

            e["cooldown"] -= dt
            if e["cooldown"] <= 0.0:
                e["cooldown"] = 2.0
                if e["tier"] == self.player_tier and not self.is_leaping_tier:
                    if len(self.shurikens) < MAX_SHURIKENS:
                        self.shurikens.append({
                            "x": e["x"],
                            "tier": e["tier"],
                            "vx": -6.0 if e["x"] > self.player_x else 6.0,
                            "is_gunshot": False,
                            "is_player": False,
                            "active": True
                        })

        # Update projectiles
        for s in self.shurikens:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            if s["x"] < -1.0 or s["x"] > 16.0:
                s["active"] = False

        self.shurikens = [s for s in self.shurikens if s["active"]]

        # Check Collisions
        # Hostages
        for idx, h in enumerate(self.hostages):
            if not h["rescued"]:
                if self.player_tier == h["tier"] and not self.is_leaping_tier:
                    if abs(self.player_x - h["x"]) < 1.0:
                        h["rescued"] = True
                        self.hostages_rescued += 1
                        self.score += 300
                        if idx == 0:
                            self.has_gun_upgrade = True
                        else:
                            self.has_ninjutsu = True

        # Projectiles
        for s in self.shurikens:
            if not s["active"]:
                continue
            if s["is_player"]:
                for e in self.enemies:
                    if e["active"] and e["tier"] == s["tier"]:
                        if abs(s["x"] - e["x"]) < 0.8:
                            s["active"] = False
                            e["health"] -= 2 if s["is_gunshot"] else 1
                            if e["health"] <= 0:
                                e["active"] = False
                                self.enemies_defeated += 1
                                self.score += 100
                            break
            else:
                if s["tier"] == self.player_tier and not self.is_leaping_tier:
                    if abs(s["x"] - self.player_x) < 0.8:
                        if not self.is_crouching:
                            s["active"] = False
                            self.lives -= 1
                            self.state = STATE_DEAD
                            self.state_timer = 0.0
                            return

        # Body contact
        for e in self.enemies:
            if e["active"] and e["tier"] == self.player_tier and not self.is_leaping_tier:
                if abs(e["x"] - self.player_x) < 0.7:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # Victory check
        if self.get_hostages_remaining() == 0 and self.enemies_defeated >= self.total_enemies:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 500
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        if self.ninjutsu_flash_timer > 0.0:
            return bytes([255] * (16 * 16 * 3))

        # Catwalk y=8, Ground y=14
        for x in range(16):
            idx_catwalk = (8 * 16 + x) * 3
            fb[idx_catwalk] = 40
            fb[idx_catwalk + 1] = 40
            fb[idx_catwalk + 2] = 50

            idx_ground = (14 * 16 + x) * 3
            fb[idx_ground] = 50
            fb[idx_ground + 1] = 30
            fb[idx_ground + 2] = 20

        # Hostages (Cyan)
        for h in self.hostages:
            if not h["rescued"]:
                hx = int(round(h["x"]))
                hy = 7 if h["tier"] == 0 else 13
                if 0 <= hx < 16 and 0 <= hy < 16:
                    idx = (hy * 16 + hx) * 3
                    fb[idx] = 0
                    fb[idx + 1] = 255
                    fb[idx + 2] = 255

        # Enemies (Red)
        for e in self.enemies:
            if e["active"]:
                ex = int(round(e["x"]))
                ey = 7 if e["tier"] == 0 else 13
                if 0 <= ex < 16 and 0 <= ey < 16:
                    idx = (ey * 16 + ex) * 3
                    fb[idx] = 255
                    fb[idx + 1] = 30
                    fb[idx + 2] = 30

        # Shurikens
        for s in self.shurikens:
            if s["active"]:
                sx = int(round(s["x"]))
                sy = 7 if s["tier"] == 0 else 13
                if 0 <= sx < 16 and 0 <= sy < 16:
                    idx = (sy * 16 + sx) * 3
                    if s["is_gunshot"]:
                        fb[idx] = 255
                        fb[idx + 1] = 200
                        fb[idx + 2] = 0
                    else:
                        fb[idx] = 220
                        fb[idx + 1] = 220
                        fb[idx + 2] = 255

        # Player
        px = int(round(self.player_x))
        if self.is_leaping_tier:
            start_y = 7.0 if self.player_tier == 0 else 13.0
            end_y = 13.0 if self.player_tier == 0 else 7.0
            mid_y = min(start_y, end_y) - 3.0
            t = self.leap_progress
            py = int(round((1.0 - t) ** 2 * start_y + 2.0 * (1.0 - t) * t * mid_y + t ** 2 * end_y))
        else:
            py = 7 if self.player_tier == 0 else 13

        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx] = 240
            fb[idx + 1] = 240
            fb[idx + 2] = 255

            if self.is_melee_slashing:
                slash_x = px + self.player_facing
                if 0 <= slash_x < 16:
                    s_idx = (py * 16 + slash_x) * 3
                    fb[s_idx] = 100
                    fb[s_idx + 1] = 220
                    fb[s_idx + 2] = 255

        # HUD lives
        for l in range(min(self.lives, 4)):
            idx = l * 3
            fb[idx] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 0

        # Ninjutsu scroll
        if self.has_ninjutsu:
            idx = 15 * 3
            fb[idx] = 255
            fb[idx + 1] = 0
            fb[idx + 2] = 255

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "player_tier": self.player_tier,
            "hostages_remaining": self.get_hostages_remaining(),
            "has_gun_upgrade": self.has_gun_upgrade,
            "has_ninjutsu": self.has_ninjutsu,
        }
