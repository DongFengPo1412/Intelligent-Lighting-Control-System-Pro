"""
Game #058: 疯狂送报生 (Paperboy 1984 / Atari)
Isometric Suburban Bicycle Route with Newspaper Mailbox Delivery, Window Vandalism & Hazard Dodging.
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

MAX_PAPERS = 3
MAX_HOUSES = 3
MAX_HAZARDS = 3


class Game058Paperboy(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 2500
        self.lives = 3

        self.player_x = 8.0
        self.player_y = 12.5
        self.speed = 6.0
        self.papers_remaining = 10
        self.delivered_count = 0
        self.route_progress = 0.0

        self.papers: List[Dict[str, Any]] = []
        self.houses: List[Dict[str, Any]] = []
        self.hazards: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 58

    @property
    def name(self) -> str:
        return "疯狂送报生"

    @property
    def english_name(self) -> str:
        return "Paperboy"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "45度斜向骑行避障 + 沿街投掷报纸入信箱 + 击碎恶意破窗与疯狗追咬"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_route()

    def init_route(self):
        self.player_x = 8.0
        self.player_y = 12.5
        self.speed = 6.0
        self.papers_remaining = 10
        self.delivered_count = 0
        self.route_progress = 0.0

        self.papers = []
        self.houses = [
            {"y": -5.0, "is_subscriber": True, "mailbox_x": 4.0, "window_x": 2.0, "delivered": False, "window_broken": False},
            {"y": -20.0, "is_subscriber": False, "mailbox_x": 4.0, "window_x": 2.0, "delivered": False, "window_broken": False},
            {"y": -35.0, "is_subscriber": True, "mailbox_x": 4.0, "window_x": 2.0, "delivered": False, "window_broken": False},
        ]
        self.hazards = [
            {"x": 6.0, "y": -10.0, "vx": 1.5, "vy": 2.0, "type": 0, "active": True},
            {"x": 11.0, "y": -25.0, "vx": -1.0, "vy": 2.5, "type": 1, "active": True},
            {"x": 8.0, "y": -40.0, "vx": 0.0, "vy": 4.0, "type": 2, "active": True},
        ]

    def throw_paper(self):
        if self.papers_remaining <= 0:
            return
        if len(self.papers) < MAX_PAPERS:
            self.papers.append({
                "x": self.player_x - 1.0,
                "y": self.player_y,
                "vx": -12.0,
                "vy": -3.0,
                "active": True
            })
            self.papers_remaining -= 1

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.init_route()
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_route()
            return

        # Bicycle speed
        if buttons & KEY_UP:
            self.speed = min(9.0, self.speed + 8.0 * dt)
        elif buttons & KEY_DOWN:
            self.speed = max(3.5, self.speed - 10.0 * dt)
        else:
            if self.speed < 6.0: self.speed += 4.0 * dt
            if self.speed > 6.0: self.speed -= 4.0 * dt

        # Steering
        if buttons & KEY_LEFT:  self.player_x -= 6.0 * dt
        if buttons & KEY_RIGHT: self.player_x += 6.0 * dt

        self.player_x = max(5.0, min(14.5, self.player_x))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.throw_paper()

        self.route_progress += self.speed * dt
        self.score += int(self.speed * dt * 2.0)

        # Update papers
        for p in self.papers:
            if not p["active"]:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["x"] < 0.0 or p["y"] < 0.0 or p["y"] > 15.0:
                p["active"] = False

        self.papers = [p for p in self.papers if p["active"]]

        # Update houses & hazards
        dy = self.speed * dt
        for h in self.houses:
            h["y"] += dy
            if h["y"] > 18.0:
                h["y"] = -15.0
                h["delivered"] = False
                h["window_broken"] = False

        for haz in self.hazards:
            if not haz["active"]:
                continue
            haz["y"] += dy + haz["vy"] * dt
            haz["x"] += haz["vx"] * dt

            if haz["x"] < 5.0:
                haz["x"] = 5.0
                haz["vx"] = abs(haz["vx"])
            elif haz["x"] > 14.0:
                haz["x"] = 14.0
                haz["vx"] = -abs(haz["vx"])

            if haz["y"] > 18.0:
                haz["y"] = -15.0

        # Collisions: Papers into mailboxes or windows
        for p in self.papers:
            if not p["active"]:
                continue
            for h in self.houses:
                # Mailbox hit
                if abs(p["x"] - h["mailbox_x"]) < 1.3 and abs(p["y"] - h["y"]) < 1.5:
                    p["active"] = False
                    if h["is_subscriber"] and not h["delivered"]:
                        h["delivered"] = True
                        self.delivered_count += 1
                        self.score += 250
                    break

                # Window hit
                if abs(p["x"] - h["window_x"]) < 1.3 and abs(p["y"] - h["y"]) < 1.5:
                    p["active"] = False
                    if not h["is_subscriber"] and not h["window_broken"]:
                        h["window_broken"] = True
                        self.score += 150
                    break

        # Collisions: Bike into hazards
        for haz in self.hazards:
            if not haz["active"]:
                continue
            if abs(self.player_x - haz["x"]) < 0.9 and abs(self.player_y - haz["y"]) < 0.9:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        # Route victory
        if self.route_progress >= 45.0:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000 + self.delivered_count * 200
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if x < 5:
                    fb[idx] = 40;  fb[idx + 1] = 160; fb[idx + 2] = 40
                elif x < 9:
                    fb[idx] = 160; fb[idx + 1] = 160; fb[idx + 2] = 160
                    if (y + int(self.route_progress)) % 4 == 0:
                        fb[idx] = 120; fb[idx + 1] = 120; fb[idx + 2] = 120
                else:
                    fb[idx] = 50;  fb[idx + 1] = 50;  fb[idx + 2] = 55

        # Houses
        for h in self.houses:
            hy = int(round(h["y"]))
            if 0 <= hy < 16:
                for wx in range(3):
                    idx = (hy * 16 + wx) * 3
                    if h["is_subscriber"]:
                        fb[idx] = 200; fb[idx + 1] = 180; fb[idx + 2] = 50
                    else:
                        fb[idx] = 100; fb[idx + 1] = 50;  fb[idx + 2] = 50

                # Mailbox x=4
                mb_idx = (hy * 16 + 4) * 3
                if h["delivered"]:
                    fb[mb_idx] = 0;   fb[mb_idx + 1] = 255; fb[mb_idx + 2] = 0
                else:
                    fb[mb_idx] = 220; fb[mb_idx + 1] = 30;  fb[mb_idx + 2] = 30

                # Window x=2
                if h["window_broken"]:
                    win_idx = (hy * 16 + 2) * 3
                    fb[win_idx] = 255; fb[win_idx + 1] = 255; fb[win_idx + 2] = 255

        # Hazards
        for haz in self.hazards:
            if haz["active"]:
                hx = int(round(haz["x"]))
                hy = int(round(haz["y"]))
                if 0 <= hx < 16 and 0 <= hy < 16:
                    idx = (hy * 16 + hx) * 3
                    if haz["type"] == 0:
                        fb[idx] = 160; fb[idx + 1] = 82;  fb[idx + 2] = 45
                    elif haz["type"] == 1:
                        fb[idx] = 255; fb[idx + 1] = 100; fb[idx + 2] = 0
                    else:
                        fb[idx] = 0;   fb[idx + 1] = 220; fb[idx + 2] = 255

        # Papers
        for p in self.papers:
            if p["active"]:
                px = int(round(p["x"]))
                py = int(round(p["y"]))
                if 0 <= px < 16 and 0 <= py < 16:
                    idx = (py * 16 + px) * 3
                    fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255

        # Player
        bx = int(round(self.player_x))
        by = int(round(self.player_y))
        if 0 <= bx < 16 and 0 <= by < 16:
            idx = (by * 16 + bx) * 3
            fb[idx] = 50; fb[idx + 1] = 100; fb[idx + 2] = 255
            if by > 0:
                f_idx = ((by - 1) * 16 + bx) * 3
                fb[f_idx] = 200; fb[f_idx + 1] = 200; fb[f_idx + 2] = 200
            if by < 15:
                r_idx = ((by + 1) * 16 + bx) * 3
                fb[r_idx] = 200; fb[r_idx + 1] = 200; fb[r_idx + 2] = 200

        # HUD
        for p in range(min(self.papers_remaining, 10)):
            idx = p * 3
            fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255

        for l in range(min(self.lives, 3)):
            idx = (15 - l) * 3
            fb[idx] = 255; fb[idx + 1] = 0;   fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "speed": self.speed,
            "papers_remaining": self.papers_remaining,
            "delivered_count": self.delivered_count,
            "route_progress": self.route_progress,
        }
