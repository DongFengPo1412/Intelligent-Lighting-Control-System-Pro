"""
Game #040: 热血躲避球 (Super Dodge Ball 1987 / Technos Japan / Yoshihisa Kishimoto)
Divided Court Battles, Super Killer Shots, Active Ball Catching & Stamina Knockouts.
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


class Game040Dodgeball(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.charge_timer = 0.0
        self.catch_window_timer = 0.0

        self.player = {"x": 4.0, "y": 8.0, "hp": 3, "is_alive": True}
        self.enemy = {"x": 11.0, "y": 8.0, "hp": 3, "is_alive": True}
        self.ball = {"x": 5.0, "y": 8.0, "vx": 0.0, "vy": 0.0, "state": 1, "is_super": False}

        self.reset()

    @property
    def game_id(self) -> int:
        return 40

    @property
    def name(self) -> str:
        return "热血躲避球"

    @property
    def english_name(self) -> str:
        return "Super Dodge Ball 1987"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "半场走位闪避 + 空手极限接球反击 + 魔球蓄力必杀技 + 击倒体力淘汰"

    def init(self) -> None:
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.charge_timer = 0.0
        self.catch_window_timer = 0.0

        self.player = {"x": 4.0, "y": 8.0, "hp": 3, "is_alive": True}
        self.enemy = {"x": 11.0, "y": 8.0, "hp": 3, "is_alive": True}
        self.ball = {"x": 5.0, "y": 8.0, "vx": 0.0, "vy": 0.0, "state": 1, "is_super": False}

    def throw_ball(self, is_super: bool):
        if self.ball["state"] != 1:
            return

        speed = 18.0 if is_super else 10.5
        dx = self.enemy["x"] - self.player["x"]
        dy = self.enemy["y"] - self.player["y"]
        dist = max(0.1, math.sqrt(dx * dx + dy * dy))

        self.ball["state"] = 3 # Thrown by player
        self.ball["x"] = self.player["x"] + 0.8
        self.ball["y"] = self.player["y"]
        self.ball["vx"] = (dx / dist) * speed
        self.ball["vy"] = (dy / dist) * speed
        self.ball["is_super"] = is_super

    def try_catch_ball(self) -> bool:
        if self.ball["state"] == 4:
            dist = abs(self.player["x"] - self.ball["x"]) + abs(self.player["y"] - self.ball["y"])
            if dist <= 1.45:
                self.ball["state"] = 1
                self.ball["vx"] = 0.0
                self.ball["vy"] = 0.0
                self.ball["is_super"] = False
                self.score += 100
                if self.score > self.high_score:
                    self.high_score = self.score
                return True
        return False

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_DEAD, STATE_VICTORY):
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_ai(dt)
        self.update_ball(dt)
        self.check_ball_hits()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        speed = 5.5

        if buttons & KEY_LEFT:
            self.player["x"] = max(1.5, self.player["x"] - speed * dt)
        if buttons & KEY_RIGHT:
            self.player["x"] = min(7.0, self.player["x"] + speed * dt)
        if buttons & KEY_UP:
            self.player["y"] = max(3.5, self.player["y"] - speed * dt)
        if buttons & KEY_DOWN:
            self.player["y"] = min(13.5, self.player["y"] + speed * dt)

        # Free ball pickup on left half
        if self.ball["state"] == 0 and self.ball["x"] <= 7.2:
            dist = abs(self.player["x"] - self.ball["x"]) + abs(self.player["y"] - self.ball["y"])
            if dist <= 1.0:
                self.ball["state"] = 1
                self.ball["vx"] = 0.0
                self.ball["vy"] = 0.0

        if self.ball["state"] == 1:
            self.ball["x"] = self.player["x"] + 0.6
            self.ball["y"] = self.player["y"]

            if buttons & KEY_A:
                self.charge_timer += dt
            elif prev_buttons & KEY_A:
                is_super = (self.charge_timer >= 0.5)
                self.throw_ball(is_super)
                self.charge_timer = 0.0
        else:
            self.charge_timer = 0.0

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.try_catch_ball()

    def update_ai(self, dt: float):
        speed = 4.8

        if self.ball["state"] == 2:
            dy = self.player["y"] - self.enemy["y"]
            if abs(dy) > 0.5:
                self.enemy["y"] += (1.0 if dy > 0 else -1.0) * speed * dt

            self.ball["x"] = self.enemy["x"] - 0.6
            self.ball["y"] = self.enemy["y"]

            if self.state_timer >= 0.6:
                self.state_timer = 0.0
                b_speed = 10.5
                dx = self.player["x"] - self.enemy["x"]
                bdy = self.player["y"] - self.enemy["y"]
                dist = max(0.1, math.sqrt(dx * dx + bdy * bdy))

                self.ball["state"] = 4
                self.ball["x"] = self.enemy["x"] - 0.8
                self.ball["y"] = self.enemy["y"]
                self.ball["vx"] = (dx / dist) * b_speed
                self.ball["vy"] = (bdy / dist) * b_speed
                self.ball["is_super"] = (random.randint(0, 2) == 0)

        elif self.ball["state"] == 0 and self.ball["x"] >= 7.5:
            dx = self.ball["x"] - self.enemy["x"]
            dy = self.ball["y"] - self.enemy["y"]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0.3:
                self.enemy["x"] += (dx / dist) * speed * dt
                self.enemy["y"] += (dy / dist) * speed * dt
            else:
                self.ball["state"] = 2
                self.ball["vx"] = 0.0
                self.ball["vy"] = 0.0
                self.state_timer = 0.0
        else:
            if self.ball["state"] == 3:
                if abs(self.enemy["y"] - self.ball["y"]) < 1.2:
                    dodge_dir = 1.0 if self.enemy["y"] < 8.0 else -1.0
                    self.enemy["y"] += dodge_dir * speed * dt

        self.enemy["x"] = max(8.0, min(13.5, self.enemy["x"]))
        self.enemy["y"] = max(3.5, min(13.5, self.enemy["y"]))

    def update_ball(self, dt: float):
        if self.ball["state"] in (3, 4):
            self.ball["x"] += self.ball["vx"] * dt
            self.ball["y"] += self.ball["vy"] * dt

            if self.ball["y"] <= 3.0:
                self.ball["y"] = 3.0
                self.ball["vy"] = -self.ball["vy"]
            elif self.ball["y"] >= 14.0:
                self.ball["y"] = 14.0
                self.ball["vy"] = -self.ball["vy"]

            if self.ball["x"] < 1.0 or self.ball["x"] > 14.5:
                self.ball["state"] = 0
                self.ball["vx"] = 0.0
                self.ball["vy"] = 0.0
                self.ball["is_super"] = False

    def check_ball_hits(self):
        if self.ball["state"] == 3:
            dist = abs(self.enemy["x"] - self.ball["x"]) + abs(self.enemy["y"] - self.ball["y"])
            if dist <= 1.0:
                dmg = 2 if self.ball["is_super"] else 1
                self.enemy["hp"] -= dmg
                self.score += dmg * 150
                if self.score > self.high_score:
                    self.high_score = self.score

                self.ball["state"] = 0
                self.ball["vx"] = 0.0
                self.ball["vy"] = 0.0
                self.ball["is_super"] = False

                if self.enemy["hp"] <= 0:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 1000
                    if self.score > self.high_score:
                        self.high_score = self.score

        elif self.ball["state"] == 4:
            dist = abs(self.player["x"] - self.ball["x"]) + abs(self.player["y"] - self.ball["y"])
            if dist <= 0.95:
                dmg = 2 if self.ball["is_super"] else 1
                self.player["hp"] -= dmg

                self.ball["state"] = 0
                self.ball["vx"] = 0.0
                self.ball["vy"] = 0.0
                self.ball["is_super"] = False

                if self.player["hp"] <= 0:
                    self.state = STATE_DEAD
                    self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Court Floor
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if 3 <= y <= 14 and 1 <= x <= 14:
                    fb[idx:idx + 3] = bytes([211, 84, 0])
                else:
                    fb[idx:idx + 3] = bytes([30, 30, 30])

        # Dividing line
        for y in range(3, 15):
            idx = (y * 16 + 7) * 3
            fb[idx:idx + 3] = bytes([245, 245, 245])

        # HUD HP
        for h in range(min(self.player["hp"], 3)):
            idx = (0 * 16 + (h + 1)) * 3
            fb[idx:idx + 3] = bytes([52, 152, 219])
        for h in range(min(self.enemy["hp"], 3)):
            idx = (0 * 16 + (14 - h)) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])

        # Enemy
        if self.enemy["hp"] > 0:
            ex = int(round(self.enemy["x"]))
            ey = int(round(self.enemy["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                fb[idx:idx + 3] = bytes([231, 76, 60])

        # Player
        if self.player["hp"] > 0:
            px = int(round(self.player["x"]))
            py = int(round(self.player["y"]))
            if 0 <= px < 16 and 0 <= py < 16:
                idx = (py * 16 + px) * 3
                if self.charge_timer >= 0.5:
                    fb[idx:idx + 3] = bytes([255, 255, 255])
                else:
                    fb[idx:idx + 3] = bytes([52, 152, 219])

        # Ball
        bx = int(round(self.ball["x"]))
        by = int(round(self.ball["y"]))
        if 0 <= bx < 16 and 0 <= by < 16:
            idx = (by * 16 + bx) * 3
            if self.ball["is_super"]:
                fb[idx:idx + 3] = bytes([255, 215, 0])
            else:
                fb[idx:idx + 3] = bytes([255, 255, 255])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "player_hp": self.player["hp"],
            "enemy_hp": self.enemy["hp"],
            "has_ball": (self.ball["state"] == 1),
            "ball_pos": (self.ball["x"], self.ball["y"]),
        }
