# -*- coding: utf-8 -*-
"""
game_022_galaga.py —— 星际双子战机 1981 (Galaga 1981)
编号: #022
年代: 1981 (南梦宫 Namco)
核心独占机制: 弧形翻滚俯冲 + 牵引光束捕获战机 + 击坠蜂后解救 + 双战机合体火力加倍
手柄类型: CTRL_ARCADE_AB (左右移动 + A键主炮射击)
"""

import math
import random
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

ALIEN_ZAKO = 0
ALIEN_GOEI = 1
ALIEN_BOSS = 2


class Game022Galaga(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.player_x: float = 7.0
        self.lives: int = 3
        self.is_dual: bool = False
        self.is_being_captured: bool = False
        self.capture_timer: float = 0.0
        self.shoot_cooldown: float = 0.0

        self.beam_active: bool = False
        self.beam_x: float = 0.0
        self.beam_y: float = 0.0
        self.beam_boss_idx: int = -1

        self.aliens: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []

        self.dive_cycle_timer: float = 0.0
        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 22

    @property
    def name(self) -> str:
        return "星际双子战机"

    @property
    def english_name(self) -> str:
        return "Galaga 1981"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "弧形翻滚俯冲 + 牵引光束捕获战机 + 击坠蜂后解救 + 双战机合体火力加倍"

    def init(self) -> None:
        self.reset()

    def init_formation(self):
        self.aliens = []

        # 行 0: 2 只蜂后 Boss
        for col in range(2):
            hx = 5.0 if col == 0 else 10.0
            self.aliens.append({
                "active": True,
                "type": ALIEN_BOSS,
                "home_x": hx,
                "home_y": 2.0,
                "x": hx,
                "y": 2.0,
                "vx": 0.0,
                "vy": 0.0,
                "is_diving": False,
                "dive_timer": 0.0,
                "has_captured_fighter": False,
            })

        # 行 1: 4 只红色蝴蝶
        for col in range(4):
            hx = 3.0 + col * 3.0
            self.aliens.append({
                "active": True,
                "type": ALIEN_GOEI,
                "home_x": hx,
                "home_y": 4.0,
                "x": hx,
                "y": 4.0,
                "vx": 0.0,
                "vy": 0.0,
                "is_diving": False,
                "dive_timer": 0.0,
                "has_captured_fighter": False,
            })

        # 行 2: 4 只蓝色工蜂
        for col in range(4):
            hx = 3.0 + col * 3.0
            self.aliens.append({
                "active": True,
                "type": ALIEN_ZAKO,
                "home_x": hx,
                "home_y": 6.0,
                "x": hx,
                "y": 6.0,
                "vx": 0.0,
                "vy": 0.0,
                "is_diving": False,
                "dive_timer": 0.0,
                "has_captured_fighter": False,
            })

        self.bullets = []
        self.player_x = 7.0
        self.is_dual = False
        self.is_being_captured = False
        self.capture_timer = 0.0
        self.shoot_cooldown = 0.0
        self.beam_active = False
        self.beam_boss_idx = -1
        self.dive_cycle_timer = 0.0

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.init_formation()

    def fire_player_bullet(self):
        if self.shoot_cooldown > 0.0:
            return
        self.shoot_cooldown = 0.22

        if not self.is_dual:
            if len(self.bullets) < 8:
                self.bullets.append({
                    "active": True,
                    "x": float(round(self.player_x)),
                    "y": 13.0,
                    "vy": -14.0,
                    "is_player": True,
                })
        else:
            if len(self.bullets) <= 6:
                self.bullets.append({
                    "active": True,
                    "x": float(round(self.player_x)),
                    "y": 13.0,
                    "vy": -14.0,
                    "is_player": True,
                })
                self.bullets.append({
                    "active": True,
                    "x": float(round(self.player_x)) + 1.0,
                    "y": 13.0,
                    "vy": -14.0,
                    "is_player": True,
                })

    def trigger_tractor_beam(self, boss_idx: int):
        if 0 <= boss_idx < len(self.aliens):
            self.beam_active = True
            self.beam_boss_idx = boss_idx
            self.beam_x = self.aliens[boss_idx]["x"]
            self.beam_y = self.aliens[boss_idx]["y"]

    def update_aliens(self, dt: float):
        any_active = False
        sway = math.sin(self.state_timer * 2.5) * 1.5

        for i, alien in enumerate(self.aliens):
            if not alien["active"]:
                continue
            any_active = True

            if not alien["is_diving"]:
                alien["x"] = alien["home_x"] + sway
                alien["y"] = alien["home_y"]
            else:
                alien["dive_timer"] += dt
                alien["y"] += alien["vy"] * dt
                alien["x"] += alien["vx"] * dt

                if alien["type"] == ALIEN_BOSS and not alien["has_captured_fighter"] and not self.is_dual:
                    if 7.0 <= alien["y"] <= 7.5 and not self.beam_active:
                        self.trigger_tractor_beam(i)

                if alien["y"] > 16.5:
                    alien["y"] = -1.0
                    alien["vy"] = 4.0
                    alien["vx"] = (alien["home_x"] - alien["x"]) * 1.5

                if alien["y"] >= alien["home_y"] and alien["vy"] > 0.0 and alien["y"] < alien["home_y"] + 1.0:
                    alien["is_diving"] = False
                    alien["x"] = alien["home_x"]
                    alien["y"] = alien["home_y"]
                    if self.beam_active and self.beam_boss_idx == i:
                        self.beam_active = False
                        self.beam_boss_idx = -1

                if random.randint(0, 100) < 3 and len(self.bullets) < 8:
                    self.bullets.append({
                        "active": True,
                        "x": alien["x"],
                        "y": alien["y"] + 0.5,
                        "vy": 6.5,
                        "is_player": False,
                    })

        self.dive_cycle_timer += dt
        if self.dive_cycle_timer >= 3.0:
            self.dive_cycle_timer = 0.0
            candidates = [idx for idx, a in enumerate(self.aliens) if a["active"] and not a["is_diving"]]
            if candidates:
                pick = random.choice(candidates)
                alien = self.aliens[pick]
                alien["is_diving"] = True
                alien["dive_timer"] = 0.0
                alien["vy"] = 5.0
                alien["vx"] = (self.player_x - alien["x"]) * 0.4

        if self.beam_active and 0 <= self.beam_boss_idx < len(self.aliens):
            boss = self.aliens[self.beam_boss_idx]
            if not boss["active"]:
                self.beam_active = False
                self.beam_boss_idx = -1
            else:
                bx = boss["x"]
                if not self.is_dual and not self.is_being_captured and abs(self.player_x - bx) <= 1.5:
                    self.is_being_captured = True
                    self.capture_timer = 0.0

                if self.is_being_captured:
                    self.capture_timer += dt
                    self.player_x += (bx - self.player_x) * 5.0 * dt
                    if self.capture_timer >= 1.2:
                        self.is_being_captured = False
                        self.beam_active = False
                        boss["has_captured_fighter"] = True
                        self.lives -= 1
                        if self.lives <= 0:
                            self.state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        else:
                            self.player_x = 7.0

        if not any_active:
            self.state = STATE_VICTORY
            self.state_timer = 0.0

    def update_bullets(self, dt: float):
        for bullet in self.bullets:
            if not bullet["active"]:
                continue

            bullet["y"] += bullet["vy"] * dt
            if bullet["y"] < -0.5 or bullet["y"] > 16.5:
                bullet["active"] = False
                continue

            if bullet["is_player"]:
                for a in self.aliens:
                    if not a["active"]:
                        continue
                    dist = abs(bullet["x"] - a["x"]) + abs(bullet["y"] - a["y"])
                    if dist <= 1.1:
                        bullet["active"] = False
                        a["active"] = False

                        if a["type"] == ALIEN_BOSS:
                            self.score += 200
                        elif a["type"] == ALIEN_GOEI:
                            self.score += 120
                        else:
                            self.score += 80

                        if self.score > self.high_score:
                            self.high_score = self.score

                        if a["has_captured_fighter"]:
                            a["has_captured_fighter"] = False
                            self.is_dual = True
                            self.score += 500
                            if self.score > self.high_score:
                                self.high_score = self.score

                        if self.beam_active and self.beam_boss_idx == self.aliens.index(a):
                            self.beam_active = False
                            self.beam_boss_idx = -1
                        break
            else:
                p_left = self.player_x - 0.5
                p_right = self.player_x + 1.5 if self.is_dual else self.player_x + 0.5
                if 13.5 <= bullet["y"] <= 15.0 and p_left <= bullet["x"] <= p_right:
                    bullet["active"] = False
                    if self.is_dual:
                        self.is_dual = False
                    else:
                        self.lives -= 1
                        if self.lives <= 0:
                            self.state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        else:
                            self.player_x = 7.0

        self.bullets = [b for b in self.bullets if b["active"]]

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

            if self.shoot_cooldown > 0.0:
                self.shoot_cooldown -= dt

            if not self.is_being_captured:
                speed = 8.5
                if keys_down & KEY_LEFT:
                    self.player_x -= speed * dt
                if keys_down & KEY_RIGHT:
                    self.player_x += speed * dt

                max_x = 14.0 if self.is_dual else 15.0
                self.player_x = max(0.0, min(max_x, self.player_x))

                if keys_pressed & (KEY_A | KEY_B):
                    self.fire_player_bullet()

            self.update_aliens(dt)
            self.update_bullets(dt)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 1. 星空背景
        for i in range(6):
            sx = int(i * 5 + self.state_timer * 4.0) % 16
            sy = (i * 3 + 2) % 16
            idx = (sy * 16 + sx) * 3
            buf[idx:idx+3] = bytes([30, 30, 50])

        # 2. 牵引光束
        if self.beam_active and 0 <= self.beam_boss_idx < len(self.aliens):
            bx = int(round(self.aliens[self.beam_boss_idx]["x"]))
            for y in range(8, 15):
                width = (y - 7) // 2
                for dx in range(-width, width + 1):
                    px = bx + dx
                    if 0 <= px < 16:
                        idx = (y * 16 + px) * 3
                        buf[idx:idx+3] = bytes([41, 128, 185])

        # 3. 敌机
        for a in self.aliens:
            if not a["active"]:
                continue
            ax = int(round(a["x"]))
            ay = int(round(a["y"]))
            if not (0 <= ax < 16 and 0 <= ay < 16):
                continue

            idx = (ay * 16 + ax) * 3
            if a["type"] == ALIEN_BOSS:
                buf[idx:idx+3] = bytes([46, 204, 113])
            elif a["type"] == ALIEN_GOEI:
                buf[idx:idx+3] = bytes([231, 76, 60])
            else:
                buf[idx:idx+3] = bytes([52, 152, 219])

            if a["has_captured_fighter"] and ay > 0:
                cidx = ((ay - 1) * 16 + ax) * 3
                buf[cidx:cidx+3] = bytes([255, 255, 100])

        # 4. 子弹
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                if b["is_player"]:
                    buf[idx:idx+3] = bytes([255, 255, 255])
                else:
                    buf[idx:idx+3] = bytes([241, 196, 15])

        # 5. 战机
        if self.lives > 0:
            py = 14
            px1 = int(round(self.player_x))
            if 0 <= px1 < 16:
                idx = (py * 16 + px1) * 3
                buf[idx:idx+3] = bytes([255, 255, 255])
            if self.is_dual:
                px2 = px1 + 1
                if px2 < 16:
                    idx = (py * 16 + px2) * 3
                    buf[idx:idx+3] = bytes([0, 255, 255])

        # 6. 生命
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx:idx+3] = bytes([255, 255, 255])

        # 7. 特效
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
        alive = sum(1 for a in self.aliens if a["active"])
        total = len(self.aliens)
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": int(((total - alive) * 100) / total) if total > 0 else 100,
            "is_dual": self.is_dual,
        }
