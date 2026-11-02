"""
Game #055: 影子刺客 / 忍者龙剑传街机版 (Ninja Gaiden 1988 / Tecmo)
Belt-Scroll Ninja Beat'em Up with Horizontal Bar Swings, Wall Rebound Jumps & Destructive Crate Throws.
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

ACTION_IDLE = 0
ACTION_SLASH = 1
ACTION_WALL_JUMP = 2
ACTION_BAR_SWING = 3

MAX_ENEMIES = 4


class Game055NinjaGaiden(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 3500
        self.lives = 3
        self.player_health = 100
        self.enemies_defeated = 0
        self.total_enemies = 4

        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.action = ACTION_IDLE
        self.action_timer = 0.0

        self.is_hanging_bar = False
        self.swing_timer = 0.0

        self.crate_x = 6.0
        self.crate_y = 13.0
        self.crate_vx = 0.0
        self.is_carrying_crate = False
        self.crate_thrown = False
        self.crate_active = True

        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 55

    @property
    def name(self) -> str:
        return "忍者龙剑传"

    @property
    def english_name(self) -> str:
        return "Ninja Gaiden"

    @property
    def release_year(self) -> int:
        return 1988

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "踩墙三角反弹跳跃 + 抓挂悬空单杠回旋飞踢 + 摔投击碎街头木箱道具"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_health = 100
        self.init_stage()

    def init_stage(self):
        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.action = ACTION_IDLE
        self.action_timer = 0.0
        self.is_hanging_bar = False
        self.swing_timer = 0.0

        self.crate_x = 6.0
        self.crate_y = 13.0
        self.crate_vx = 0.0
        self.is_carrying_crate = False
        self.crate_thrown = False
        self.crate_active = True

        self.enemies_defeated = 0
        self.enemies = [
            {"x": 8.0, "y": 13.0, "vx": -2.0, "health": 2, "active": True},
            {"x": 12.0, "y": 13.0, "vx": -1.5, "health": 2, "active": True},
            {"x": 9.0, "y": 11.5, "vx": -1.8, "health": 2, "active": True},
            {"x": 14.0, "y": 13.0, "vx": -1.0, "health": 4, "active": True},
        ]
        self.total_enemies = len(self.enemies)

    def trigger_bar_grab(self):
        self.is_hanging_bar = True
        self.action = ACTION_BAR_SWING
        self.swing_timer = 0.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_y = 5.0

    def trigger_wall_rebound(self):
        self.action = ACTION_WALL_JUMP
        self.action_timer = 0.35
        self.player_vx = 10.0 if self.player_x < 5.0 else -10.0
        self.player_vy = -8.0

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

        # Player update
        if self.is_hanging_bar:
            self.swing_timer += dt * 8.0
            if ((buttons & KEY_A) and not (prev_buttons & KEY_A)) or \
               ((buttons & KEY_B) and not (prev_buttons & KEY_B)):
                self.is_hanging_bar = False
                self.action = ACTION_WALL_JUMP
                self.action_timer = 0.45
                self.player_vx = self.player_facing * 14.0
                self.player_vy = 4.0
        elif self.action == ACTION_WALL_JUMP:
            self.action_timer -= dt
            self.player_x += self.player_vx * dt
            self.player_y += self.player_vy * dt
            self.player_vy += 25.0 * dt
            if self.player_y >= 13.0:
                self.player_y = 13.0
                self.player_vy = 0.0
                self.player_vx = 0.0
                self.action = ACTION_IDLE
        else:
            if self.action == ACTION_SLASH:
                self.action_timer -= dt
                if self.action_timer <= 0.0:
                    self.action = ACTION_IDLE

            speed = 6.0
            self.player_vx = 0.0
            self.player_vy = 0.0

            if buttons & KEY_LEFT:
                self.player_vx = -speed
                self.player_facing = -1
            elif buttons & KEY_RIGHT:
                self.player_vx = speed
                self.player_facing = 1

            if buttons & KEY_UP:
                self.player_vy = -speed * 0.7
            elif buttons & KEY_DOWN:
                self.player_vy = speed * 0.7

            self.player_x += self.player_vx * dt
            self.player_y += self.player_vy * dt

            self.player_x = max(0.8, min(14.8, self.player_x))
            self.player_y = max(9.0, min(14.5, self.player_y))

            if self.is_carrying_crate:
                self.crate_x = self.player_x
                self.crate_y = self.player_y - 1.5

            # Jump button
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                if self.player_x <= 1.2 or self.player_x >= 14.2:
                    self.trigger_wall_rebound()
                    return
                if 4.0 <= self.player_x <= 11.0:
                    self.trigger_bar_grab()
                    return
                self.action = ACTION_WALL_JUMP
                self.action_timer = 0.4
                self.player_vy = -9.0
                self.player_vx = self.player_facing * 4.0
                return

            # Attack button
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                if self.is_carrying_crate:
                    self.is_carrying_crate = False
                    self.crate_thrown = True
                    self.crate_vx = self.player_facing * 13.0
                    return

                if self.crate_active and not self.crate_thrown and not self.is_carrying_crate:
                    if abs(self.player_x - self.crate_x) < 1.4 and abs(self.player_y - self.crate_y) < 1.4:
                        self.is_carrying_crate = True
                        return

                self.action = ACTION_SLASH
                self.action_timer = 0.22

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

        # Update enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            dx = self.player_x - e["x"]
            dy = self.player_y - e["y"]
            dist = math.hypot(dx, dy)
            if dist > 0.8:
                e["x"] += (1.0 if dx > 0 else -1.0) * 2.2 * dt
                e["y"] += (1.0 if dy > 0 else -1.0) * 1.5 * dt
            e["x"] = max(1.0, min(14.5, e["x"]))
            e["y"] = max(9.0, min(14.5, e["y"]))

        # Update crate
        if self.crate_thrown:
            self.crate_x += self.crate_vx * dt
            self.crate_y += 3.0 * dt
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(self.crate_x - e["x"]) < 1.3 and abs(self.crate_y - e["y"]) < 1.3:
                    e["health"] -= 3
                    self.crate_thrown = False
                    self.crate_active = False
                    self.score += 250
                    if e["health"] <= 0:
                        e["active"] = False
                        self.enemies_defeated += 1
                    break

            if self.crate_x < 0.0 or self.crate_x > 16.0 or self.crate_y > 15.0:
                self.crate_thrown = False
                self.crate_active = False

        # Collision with enemies
        if self.action == ACTION_WALL_JUMP:
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(self.player_x - e["x"]) < 1.4 and abs(self.player_y - e["y"]) < 1.4:
                    e["health"] -= 2
                    self.score += 200
                    if e["health"] <= 0:
                        e["active"] = False
                        self.enemies_defeated += 1

        for e in self.enemies:
            if not e["active"]:
                continue
            if self.action != ACTION_WALL_JUMP and not self.is_hanging_bar:
                if abs(self.player_x - e["x"]) < 0.8 and abs(self.player_y - e["y"]) < 0.7:
                    self.player_health -= 15
                    if self.player_health <= 0:
                        self.lives -= 1
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

        if self.enemies_defeated >= self.total_enemies:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Sky y=0..3
        for y in range(4):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx] = 20
                fb[idx + 1] = 10
                fb[idx + 2] = 40

        # Bar y=4, x=4..11
        for x in range(4, 12):
            idx = (4 * 16 + x) * 3
            fb[idx] = 180
            fb[idx + 1] = 180
            fb[idx + 2] = 190

        # Wall bricks
        for y in range(4, 16):
            idx_l = (y * 16 + 0) * 3
            fb[idx_l] = 90
            fb[idx_l + 1] = 40
            fb[idx_l + 2] = 30

            idx_r = (y * 16 + 15) * 3
            fb[idx_r] = 90
            fb[idx_r + 1] = 40
            fb[idx_r + 2] = 30

        # Asphalt street
        for y in range(9, 16):
            for x in range(1, 15):
                idx = (y * 16 + x) * 3
                fb[idx] = 40
                fb[idx + 1] = 45
                fb[idx + 2] = 50

        # Crate
        if self.crate_active or self.is_carrying_crate or self.crate_thrown:
            cx = int(round(self.crate_x))
            cy = int(round(self.crate_y))
            if 0 <= cx < 16 and 0 <= cy < 16:
                idx = (cy * 16 + cx) * 3
                fb[idx] = 180
                fb[idx + 1] = 110
                fb[idx + 2] = 40

        # Enemies
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if i == 3:
                    fb[idx] = 255
                    fb[idx + 1] = 255
                    fb[idx + 2] = 255
                else:
                    fb[idx] = 200
                    fb[idx + 1] = 40
                    fb[idx + 2] = 40

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx] = 30
            fb[idx + 1] = 100
            fb[idx + 2] = 240

            if self.action == ACTION_SLASH:
                sx = px + self.player_facing
                if 0 <= sx < 16:
                    s_idx = (py * 16 + sx) * 3
                    fb[s_idx] = 200
                    fb[s_idx + 1] = 230
                    fb[s_idx + 2] = 255
            elif self.action == ACTION_WALL_JUMP:
                tx = px - self.player_facing
                if 0 <= tx < 16:
                    t_idx = (py * 16 + tx) * 3
                    fb[t_idx] = 255
                    fb[t_idx + 1] = 200
                    fb[t_idx + 2] = 0

        # HUD
        hp_bars = (self.player_health * 6) // 100
        for h in range(min(hp_bars, 6)):
            idx = h * 3
            fb[idx] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 0

        for l in range(min(self.lives, 3)):
            idx = (15 - l) * 3
            fb[idx] = 255
            fb[idx + 1] = 0
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
            "health": self.player_health,
            "action": self.action,
            "is_hanging_bar": self.is_hanging_bar,
            "is_carrying_crate": self.is_carrying_crate,
            "enemies_remaining": sum(1 for e in self.enemies if e["active"]),
        }
