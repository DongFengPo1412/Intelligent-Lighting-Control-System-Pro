"""
Game #043: 蜈蚣大战 (Centipede 1980 / Atari)
Dynamic Multi-segment Centipede in Mushroom Field with Body Splitting Fission and Bouncing Spider.
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

MAX_SEGMENTS = 12
MAX_BULLETS = 3
MAX_MUSHROOMS = 24


class Game043Centipede(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3

        self.player_x = 7.5
        self.player_y = 14.0
        self.fire_cooldown = 0.0

        self.centipede_step_timer = 0.0
        self.centipede_step_interval = 0.14
        self.spider_spawn_timer = 4.0

        self.segments: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []
        self.mushrooms: List[Dict[str, Any]] = []
        self.spider: Dict[str, Any] = {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False}

        self.reset()

    @property
    def game_id(self) -> int:
        return 43

    @property
    def name(self) -> str:
        return "蜈蚣大战"

    @property
    def english_name(self) -> str:
        return "Centipede (1980)"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多节蜈蚣穿梭蘑菇阵 + 击中身体裂变为新独立蜈蚣 + 毒蜘蛛跳跃"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_x = 7.5
        self.player_y = 14.0
        self.fire_cooldown = 0.0
        self.centipede_step_timer = 0.0
        self.centipede_step_interval = 0.14
        self.spider_spawn_timer = 4.0

        self.bullets = []
        self.spider = {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False}

        self.init_arena()

    def init_arena(self):
        # 1. Initialize mushrooms
        self.mushrooms = []
        seed_mushrooms = [
            (2, 3), (7, 3), (12, 4), (4, 6), (9, 6), (14, 7),
            (1, 8), (6, 9), (11, 9), (3, 11), (8, 11), (13, 12)
        ]
        for sx, sy in seed_mushrooms:
            self.mushrooms.append({"x": sx, "y": sy, "health": 2, "active": True})

        # 2. Initialize 8-segment centipede along top row
        self.segments = []
        for i in range(8):
            self.segments.append({
                "x": float(7 - i),
                "y": 0.0,
                "dir_x": 1,
                "is_head": (i == 0),
                "active": True,
            })

    def get_active_segment_count(self) -> int:
        return sum(1 for s in self.segments if s["active"])

    def spawn_mushroom(self, x: int, y: int):
        if not (0 <= x < 16 and 0 <= y < 16):
            return
        for m in self.mushrooms:
            if m["active"] and m["x"] == x and m["y"] == y:
                return
        if len(self.mushrooms) < MAX_MUSHROOMS:
            self.mushrooms.append({"x": x, "y": y, "health": 2, "active": True})

    def hit_centipede_segment(self, seg_idx: int):
        if seg_idx < 0 or seg_idx >= len(self.segments) or not self.segments[seg_idx]["active"]:
            return

        seg = self.segments[seg_idx]
        seg["active"] = False

        mx = int(round(seg["x"]))
        my = int(round(seg["y"]))
        self.spawn_mushroom(mx, my)

        if seg["is_head"]:
            self.score += 100
        else:
            self.score += 10

        # Fission: next segment becomes new head!
        if seg_idx + 1 < len(self.segments) and self.segments[seg_idx + 1]["active"]:
            self.segments[seg_idx + 1]["is_head"] = True

        if self.score > self.high_score:
            self.high_score = self.score

        if self.get_active_segment_count() == 0:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000
            if self.score > self.high_score:
                self.high_score = self.score

    def fire_bullet(self):
        if self.fire_cooldown > 0.0:
            return
        active_bullets = sum(1 for b in self.bullets if b["active"])
        if active_bullets < MAX_BULLETS:
            self.bullets.append({"x": self.player_x, "y": self.player_y - 0.5, "active": True})
            self.fire_cooldown = 0.2

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        speed = 8.0
        if buttons & KEY_LEFT:
            self.player_x -= speed * dt
        if buttons & KEY_RIGHT:
            self.player_x += speed * dt
        if buttons & KEY_UP:
            self.player_y -= speed * dt
        if buttons & KEY_DOWN:
            self.player_y += speed * dt

        self.player_x = max(0.0, min(15.0, self.player_x))
        self.player_y = max(11.0, min(15.0, self.player_y))

        if buttons & KEY_A:
            self.fire_bullet()

    def update_bullets(self, dt: float):
        bullet_speed = 18.0
        for b in self.bullets:
            if not b["active"]:
                continue
            b["y"] -= bullet_speed * dt
            if b["y"] < 0.0:
                b["active"] = False

    def update_spider(self, dt: float):
        if not self.spider["active"]:
            self.spider_spawn_timer -= dt
            if self.spider_spawn_timer <= 0.0:
                self.spider["active"] = True
                self.spider["x"] = 0.0
                self.spider["y"] = 12.0
                self.spider["vx"] = 3.5
                self.spider["vy"] = 2.5
                self.spider_spawn_timer = 6.0
            return

        self.spider["x"] += self.spider["vx"] * dt
        self.spider["y"] += self.spider["vy"] * dt

        if self.spider["y"] <= 10.0:
            self.spider["y"] = 10.0
            self.spider["vy"] = abs(self.spider["vy"])
        elif self.spider["y"] >= 15.0:
            self.spider["y"] = 15.0
            self.spider["vy"] = -abs(self.spider["vy"])

        if self.spider["x"] < -1.0 or self.spider["x"] > 16.0:
            self.spider["active"] = False
            self.spider_spawn_timer = 5.0

    def update_centipede(self, dt: float):
        self.centipede_step_timer += dt
        if self.centipede_step_timer < self.centipede_step_interval:
            return
        self.centipede_step_timer -= self.centipede_step_interval

        for s in self.segments:
            if not s["active"]:
                continue

            next_x = s["x"] + s["dir_x"]
            check_x = int(round(next_x))
            cur_y = int(round(s["y"]))

            hit_obstacle = False
            if next_x < 0.0 or next_x > 15.0:
                hit_obstacle = True
            else:
                for m in self.mushrooms:
                    if m["active"] and m["x"] == check_x and m["y"] == cur_y:
                        hit_obstacle = True
                        break

            if hit_obstacle:
                s["y"] += 1.0
                if s["y"] >= 15.5:
                    s["y"] = 11.0
                s["dir_x"] = -s["dir_x"]
            else:
                s["x"] = next_x

    def check_collisions(self):
        # 1. Bullets vs Mushrooms
        for b in self.bullets:
            if not b["active"]:
                continue
            for m in self.mushrooms:
                if not m["active"]:
                    continue
                if abs(b["x"] - m["x"]) <= 0.8 and abs(b["y"] - m["y"]) <= 0.8:
                    b["active"] = False
                    m["health"] -= 1
                    if m["health"] <= 0:
                        m["active"] = False
                        self.score += 5
                        if self.score > self.high_score:
                            self.high_score = self.score
                    break

        # 2. Bullets vs Centipede Segments
        for b in self.bullets:
            if not b["active"]:
                continue
            for s_idx, s in enumerate(self.segments):
                if not s["active"]:
                    continue
                if abs(b["x"] - s["x"]) <= 0.85 and abs(b["y"] - s["y"]) <= 0.85:
                    b["active"] = False
                    self.hit_centipede_segment(s_idx)
                    break

        # 3. Bullets vs Spider
        if self.spider["active"]:
            for b in self.bullets:
                if not b["active"]:
                    continue
                if abs(b["x"] - self.spider["x"]) <= 1.0 and abs(b["y"] - self.spider["y"]) <= 1.0:
                    b["active"] = False
                    self.spider["active"] = False
                    self.score += 300
                    if self.score > self.high_score:
                        self.high_score = self.score
                    break

        # 4. Centipede or Spider vs Player
        for s in self.segments:
            if not s["active"]:
                continue
            if abs(self.player_x - s["x"]) <= 0.85 and abs(self.player_y - s["y"]) <= 0.85:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        if self.spider["active"]:
            if abs(self.player_x - self.spider["x"]) <= 0.9 and abs(self.player_y - self.spider["y"]) <= 0.9:
                self.lives -= 1
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt
        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 7.5
                    self.player_y = 14.0
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_bullets(dt)
        self.update_spider(dt)
        self.update_centipede(dt)
        self.check_collisions()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # 1. Mushrooms
        for m in self.mushrooms:
            if not m["active"]:
                continue
            mx = m["x"]
            my = m["y"]
            if 0 <= mx < 16 and 0 <= my < 16:
                idx = (my * 16 + mx) * 3
                if m["health"] == 2:
                    fb[idx + 0] = 39
                    fb[idx + 1] = 174
                    fb[idx + 2] = 96
                else:
                    fb[idx + 0] = 142
                    fb[idx + 1] = 68
                    fb[idx + 2] = 173

        # 2. Centipede Segments
        for s in self.segments:
            if not s["active"]:
                continue
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            if 0 <= sx < 16 and 0 <= sy < 16:
                idx = (sy * 16 + sx) * 3
                if s["is_head"]:
                    fb[idx + 0] = 231
                    fb[idx + 1] = 76
                    fb[idx + 2] = 60
                else:
                    fb[idx + 0] = 46
                    fb[idx + 1] = 204
                    fb[idx + 2] = 113

        # 3. Spider
        if self.spider["active"]:
            spx = int(round(self.spider["x"]))
            spy = int(round(self.spider["y"]))
            if 0 <= spx < 16 and 0 <= spy < 16:
                idx = (spy * 16 + spx) * 3
                fb[idx + 0] = 241
                fb[idx + 1] = 196
                fb[idx + 2] = 15

        # 4. Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                fb[idx + 0] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 255

        # 5. Player Bug Blaster
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx + 0] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 255

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "active_segments": self.get_active_segment_count(),
            "player_x": self.player_x,
            "player_y": self.player_y,
            "spider_active": self.spider["active"],
        }
