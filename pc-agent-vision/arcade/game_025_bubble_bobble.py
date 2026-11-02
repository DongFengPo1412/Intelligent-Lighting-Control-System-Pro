# -*- coding: utf-8 -*-
"""
game_025_bubble_bobble.py —— 经典泡泡龙打怪 1986 (Bubble Bobble 1986)
编号: #025
年代: 1986 (太东 Taito)
核心独占机制: 吐泡包裹怪物 + 跳跃撞刺戳破秒杀 + 借泡弹跳漂浮 + 气泡升空气流
手柄类型: CTRL_ARCADE_AB (左右跑动 + A键吐出气泡 / B键起跳踩踏)
"""

from typing import Dict, Any, List, Optional
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)


class Game025BubbleBobble(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.player_x: float = 2.0
        self.player_y: float = 13.0
        self.player_vy: float = 0.0
        self.player_dir: int = 1
        self.is_jumping: bool = False
        self.lives: int = 3
        self.spit_cooldown: float = 0.0

        self.bubbles: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 25

    @property
    def name(self) -> str:
        return "经典泡泡龙打怪"

    @property
    def english_name(self) -> str:
        return "Bubble Bobble 1986"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "吐泡包裹怪物 + 跳跃撞刺戳破秒杀 + 借泡弹跳漂浮 + 气泡升空气流"

    def init(self) -> None:
        self.reset()

    def is_on_platform(self, x: float, y: float) -> bool:
        px = int(round(x))
        py = int(round(y))
        if py == 13:
            return True
        if py == 9 and ((2 <= px <= 6) or (9 <= px <= 13)):
            return True
        if py == 5 and (4 <= px <= 11):
            return True
        return False

    def init_level(self):
        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vy = 0.0
        self.player_dir = 1
        self.is_jumping = False
        self.spit_cooldown = 0.0
        self.bubbles = []

        self.enemies = [
            {"active": True, "x": 12.0, "y": 13.0, "vx": -3.0, "trapped": False, "move_timer": 0.0},
            {"active": True, "x": 4.0, "y": 9.0, "vx": 2.5, "trapped": False, "move_timer": 0.0},
            {"active": True, "x": 10.0, "y": 5.0, "vx": -2.5, "trapped": False, "move_timer": 0.0},
        ]

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.init_level()

    def spit_bubble(self):
        if self.spit_cooldown > 0.0:
            return
        self.spit_cooldown = 0.28

        if len(self.bubbles) < 6:
            self.bubbles.append({
                "active": True,
                "x": self.player_x + float(self.player_dir) * 1.0,
                "y": self.player_y,
                "vx": float(self.player_dir) * 6.5,
                "vy": 0.0,
                "trapped_enemy": -1,
                "timer": 7.0,
            })

    def update_bubbles(self, dt: float):
        for bubble in self.bubbles:
            if not bubble["active"]:
                continue

            bubble["timer"] -= dt
            if bubble["timer"] <= 0.0:
                if bubble["trapped_enemy"] >= 0:
                    e = bubble["trapped_enemy"]
                    if e < len(self.enemies):
                        self.enemies[e]["trapped"] = False
                        self.enemies[e]["x"] = bubble["x"]
                        self.enemies[e]["y"] = bubble["y"]
                bubble["active"] = False
                continue

            if abs(bubble["vx"]) > 0.2:
                bubble["x"] += bubble["vx"] * dt
                bubble["vx"] *= 0.80
            else:
                bubble["vx"] = 0.0
                bubble["vy"] = -1.8
                bubble["y"] += bubble["vy"] * dt
                if bubble["y"] < 1.0:
                    bubble["y"] = 1.0
                    bubble["vy"] = 0.0

            if bubble["trapped_enemy"] >= 0:
                e = bubble["trapped_enemy"]
                if e < len(self.enemies):
                    self.enemies[e]["x"] = bubble["x"]
                    self.enemies[e]["y"] = bubble["y"]
            else:
                for e_idx, enemy in enumerate(self.enemies):
                    if enemy["active"] and not enemy["trapped"]:
                        dist = abs(bubble["x"] - enemy["x"]) + abs(bubble["y"] - enemy["y"])
                        if dist <= 0.85:
                            bubble["trapped_enemy"] = e_idx
                            enemy["trapped"] = True
                            self.score += 50
                            if self.score > self.high_score:
                                self.high_score = self.score
                            break

            p_dist = abs(self.player_x - bubble["x"]) + abs(self.player_y - bubble["y"])
            if p_dist <= 1.0:
                if bubble["trapped_enemy"] >= 0:
                    e = bubble["trapped_enemy"]
                    if e < len(self.enemies):
                        self.enemies[e]["active"] = False
                    bubble["active"] = False
                    self.score += 300
                    if self.score > self.high_score:
                        self.high_score = self.score
                elif self.player_vy > 0.0 and self.player_y < bubble["y"]:
                    self.player_vy = -6.2
                    self.is_jumping = True
                    self.score += 20
                    if self.score > self.high_score:
                        self.high_score = self.score

        self.bubbles = [b for b in self.bubbles if b["active"]]

    def update_enemies(self, dt: float):
        any_active = False

        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            any_active = True

            if enemy["trapped"]:
                continue

            enemy["x"] += enemy["vx"] * dt

            if enemy["x"] <= 0.5:
                enemy["x"] = 0.5
                enemy["vx"] = -enemy["vx"]
            elif enemy["x"] >= 14.5:
                enemy["x"] = 14.5
                enemy["vx"] = -enemy["vx"]

            dist = abs(self.player_x - enemy["x"]) + abs(self.player_y - enemy["y"])
            if dist <= 0.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
                else:
                    self.player_x = 2.0
                    self.player_y = 13.0
                    return

        if not any_active:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000
            if self.score > self.high_score:
                self.high_score = self.score

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)):
                self.reset()
            return

        if self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            if self.spit_cooldown > 0.0:
                self.spit_cooldown -= dt

            if keys_pressed & KEY_A:
                self.spit_bubble()

            speed = 6.0
            if keys_down & KEY_LEFT:
                self.player_x -= speed * dt
                self.player_dir = -1
            if keys_down & KEY_RIGHT:
                self.player_x += speed * dt
                self.player_dir = 1
            self.player_x = max(0.0, min(15.0, self.player_x))

            if not self.is_jumping and (keys_pressed & (KEY_B | KEY_UP)):
                self.is_jumping = True
                self.player_vy = -6.8

            if self.is_jumping:
                self.player_vy += 14.0 * dt
                self.player_y += self.player_vy * dt

                if self.player_vy > 0.0 and self.is_on_platform(self.player_x, self.player_y):
                    self.player_y = float(round(self.player_y))
                    self.player_vy = 0.0
                    self.is_jumping = False
            else:
                if not self.is_on_platform(self.player_x, self.player_y):
                    self.is_jumping = True
                    self.player_vy = 2.0

            if self.player_y > 13.0:
                self.player_y = 13.0
                self.player_vy = 0.0
                self.is_jumping = False

            self.update_bubbles(dt)
            self.update_enemies(dt)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 1. 平台横梁
        for x in range(16):
            idx = (14 * 16 + x) * 3
            buf[idx:idx+3] = bytes([46, 204, 113])
        for x in range(2, 7):
            idx = (10 * 16 + x) * 3
            buf[idx:idx+3] = bytes([46, 204, 113])
        for x in range(9, 14):
            idx = (10 * 16 + x) * 3
            buf[idx:idx+3] = bytes([46, 204, 113])
        for x in range(4, 12):
            idx = (6 * 16 + x) * 3
            buf[idx:idx+3] = bytes([46, 204, 113])

        # 2. 气泡
        for b in self.bubbles:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                if b["trapped_enemy"] >= 0:
                    buf[idx:idx+3] = bytes([241, 196, 15])
                else:
                    buf[idx:idx+3] = bytes([52, 152, 219])

        # 3. 怪物
        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            ex = int(round(enemy["x"]))
            ey = int(round(enemy["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if not enemy["trapped"]:
                    buf[idx:idx+3] = bytes([231, 76, 60])

        # 4. 玩家
        if self.lives > 0:
            px = int(round(self.player_x))
            py = int(round(self.player_y))
            if 0 <= px < 16 and 0 <= py < 16:
                idx = (py * 16 + px) * 3
                buf[idx:idx+3] = bytes([255, 255, 255])

        # 5. 生命
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx:idx+3] = bytes([255, 255, 255])

        # 6. 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx:idx+3] = bytes([231, 76, 60])

        return bytes(buf)

    def get_status(self) -> Dict[str, Any]:
        alive = sum(1 for e in self.enemies if e["active"])
        total = len(self.enemies)
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": int(((total - alive) * 100) / total) if total > 0 else 100,
        }
