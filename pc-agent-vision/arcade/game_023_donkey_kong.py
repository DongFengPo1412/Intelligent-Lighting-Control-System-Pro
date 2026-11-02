# -*- coding: utf-8 -*-
"""
game_023_donkey_kong.py —— 经典大金刚 1981 (Donkey Kong 1981)
编号: #023
年代: 1981 (任天堂 Nintendo)
核心独占机制: 多层倾斜钢梁 + 梯子垂直攀爬 + 滚木桶跳跃规避 + 铁锤破击拯救
手柄类型: CTRL_ARCADE_AB (左右跑动 + 上下攀爬 + A键起跳跨桶)
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


class Game023DonkeyKong(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.player_x: float = 1.0
        self.player_y: float = 13.0
        self.player_vy: float = 0.0
        self.jump_base_y: float = 13.0
        self.is_climbing: bool = False
        self.is_jumping: bool = False
        self.lives: int = 3
        self.hammer_timer: float = 0.0
        self.barrel_spawn_timer: float = 0.0

        self.hammer_x: int = 2
        self.hammer_y: int = 9
        self.hammer_available: bool = True

        self.barrels: List[Dict[str, Any]] = []

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 23

    @property
    def name(self) -> str:
        return "经典大金刚"

    @property
    def english_name(self) -> str:
        return "Donkey Kong 1981"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多层倾斜钢梁 + 梯子垂直攀爬 + 滚木桶跳跃规避 + 铁锤破击拯救"

    def init(self) -> None:
        self.reset()

    def is_on_ladder(self, x: int, y: int) -> bool:
        if x == 12 and 10 <= y <= 14:
            return True
        if x == 3 and 6 <= y <= 10:
            return True
        if x == 7 and 2 <= y <= 6:
            return True
        return False

    def init_level(self):
        self.player_x = 1.0
        self.player_y = 13.0
        self.player_vy = 0.0
        self.is_climbing = False
        self.is_jumping = False
        self.hammer_timer = 0.0
        self.barrel_spawn_timer = 0.0
        self.hammer_x = 2
        self.hammer_y = 9
        self.hammer_available = True
        self.barrels = []

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.init_level()

    def spawn_barrel(self):
        if len(self.barrels) < 4:
            self.barrels.append({
                "active": True,
                "x": 6.0,
                "y": 2.0,
                "vx": 3.5,
                "layer": 3,
                "falling_ladder": False,
            })

    def update_barrels(self, dt: float):
        self.barrel_spawn_timer += dt
        if self.barrel_spawn_timer >= 3.2:
            self.barrel_spawn_timer = 0.0
            self.spawn_barrel()

        for barrel in self.barrels:
            if not barrel["active"]:
                continue

            if barrel["falling_ladder"]:
                barrel["y"] += 5.0 * dt
                target_y = 6.0 if barrel["layer"] == 2 else (10.0 if barrel["layer"] == 1 else 14.0)
                if barrel["y"] >= target_y:
                    barrel["y"] = target_y
                    barrel["falling_ladder"] = False
                    barrel["vx"] = 3.5 if barrel["layer"] % 2 == 1 else -3.5
            else:
                barrel["x"] += barrel["vx"] * dt

                if barrel["layer"] == 3:
                    if barrel["x"] >= 11.0:
                        barrel["layer"] = 2
                        barrel["x"] = 11.0
                        barrel["y"] = 5.0
                        barrel["vx"] = -3.5
                elif barrel["layer"] == 2:
                    if abs(barrel["x"] - 3.0) < 0.25 and random.randint(0, 9) < 4:
                        barrel["layer"] = 1
                        barrel["falling_ladder"] = True
                        barrel["x"] = 3.0
                    elif barrel["x"] <= 2.0:
                        barrel["layer"] = 1
                        barrel["x"] = 2.0
                        barrel["y"] = 9.0
                        barrel["vx"] = 3.5
                elif barrel["layer"] == 1:
                    if abs(barrel["x"] - 12.0) < 0.25 and random.randint(0, 9) < 4:
                        barrel["layer"] = 0
                        barrel["falling_ladder"] = True
                        barrel["x"] = 12.0
                    elif barrel["x"] >= 13.0:
                        barrel["layer"] = 0
                        barrel["x"] = 13.0
                        barrel["y"] = 13.0
                        barrel["vx"] = -3.5
                elif barrel["layer"] == 0:
                    if barrel["x"] < -0.5:
                        barrel["active"] = False

            dist = abs(self.player_x - barrel["x"]) + abs(self.player_y - barrel["y"])
            if dist <= 0.85:
                if self.hammer_timer > 0.0:
                    barrel["active"] = False
                    self.score += 300
                    if self.score > self.high_score:
                        self.high_score = self.score
                else:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                    else:
                        self.init_level()
                        return
            elif self.is_jumping and self.player_y < barrel["y"] and abs(self.player_x - barrel["x"]) < 0.8:
                self.score += 100
                if self.score > self.high_score:
                    self.high_score = self.score

        self.barrels = [b for b in self.barrels if b["active"]]

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
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

            if self.hammer_timer > 0.0:
                self.hammer_timer = max(0.0, self.hammer_timer - dt)

            # 拾取铁锤
            if self.hammer_available and int(round(self.player_x)) == self.hammer_x and int(round(self.player_y)) == self.hammer_y:
                self.hammer_available = False
                self.hammer_timer = 5.0
                self.score += 200
                if self.score > self.high_score:
                    self.high_score = self.score

            px = int(round(self.player_x))
            py = int(round(self.player_y))

            if self.is_climbing:
                climb_speed = 4.0
                if keys_down & KEY_UP:
                    self.player_y -= climb_speed * dt
                if keys_down & KEY_DOWN:
                    self.player_y += climb_speed * dt

                check_y = int(round(self.player_y))
                if not self.is_on_ladder(px, check_y):
                    self.is_climbing = False
            else:
                move_speed = 5.5
                if keys_down & KEY_LEFT:
                    self.player_x -= move_speed * dt
                if keys_down & KEY_RIGHT:
                    self.player_x += move_speed * dt

                self.player_x = max(0.0, min(15.0, self.player_x))

                if (keys_down & (KEY_UP | KEY_DOWN)) and self.is_on_ladder(px, py):
                    self.is_climbing = True
                    self.player_x = float(px)
                    self.player_vy = 0.0
                    self.is_jumping = False
                    return

                if not self.is_jumping and (keys_pressed & (KEY_A | KEY_B)):
                    self.is_jumping = True
                    self.jump_base_y = self.player_y
                    self.player_vy = -6.8

                if self.is_jumping:
                    self.player_vy += 14.0 * dt
                    self.player_y += self.player_vy * dt

                    if self.player_y >= self.jump_base_y:
                        self.player_y = self.jump_base_y
                        self.player_vy = 0.0
                        self.is_jumping = False
                else:
                    if self.player_y <= 3.0 and 4.0 <= self.player_x <= 11.0:
                        self.player_y = 1.0
                    elif self.player_y <= 7.0 and self.player_x >= 2.0:
                        self.player_y = 5.0
                    elif self.player_y <= 11.0 and self.player_x <= 13.0:
                        self.player_y = 9.0
                    else:
                        self.player_y = 13.0

            self.update_barrels(dt)

            if self.player_y <= 2.5 and self.player_x >= 9.0:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 1000
                if self.score > self.high_score:
                    self.high_score = self.score

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 1. 4 层钢梁
        for x in range(16):
            idx = (14 * 16 + x) * 3
            buf[idx:idx+3] = bytes([231, 76, 60])
        for x in range(14):
            idx = (10 * 16 + x) * 3
            buf[idx:idx+3] = bytes([231, 76, 60])
        for x in range(2, 16):
            idx = (6 * 16 + x) * 3
            buf[idx:idx+3] = bytes([231, 76, 60])
        for x in range(4, 12):
            idx = (2 * 16 + x) * 3
            buf[idx:idx+3] = bytes([231, 76, 60])

        # 2. 梯子
        for y in range(10, 15):
            idx = (y * 16 + 12) * 3
            buf[idx:idx+3] = bytes([52, 152, 219])
        for y in range(6, 11):
            idx = (y * 16 + 3) * 3
            buf[idx:idx+3] = bytes([52, 152, 219])
        for y in range(2, 7):
            idx = (y * 16 + 7) * 3
            buf[idx:idx+3] = bytes([52, 152, 219])

        # 3. 大金刚与宝琳
        dk_idx = (1 * 16 + 4) * 3
        buf[dk_idx:dk_idx+3] = bytes([140, 70, 20])
        pauline_idx = (1 * 16 + 10) * 3
        buf[pauline_idx:pauline_idx+3] = bytes([255, 105, 180])

        # 4. 铁锤
        if self.hammer_available:
            h_idx = (self.hammer_y * 16 + self.hammer_x) * 3
            buf[h_idx:h_idx+3] = bytes([241, 196, 15])

        # 5. 木桶
        for b in self.barrels:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                buf[idx:idx+3] = bytes([230, 126, 34])

        # 6. 玩家
        if self.lives > 0:
            px = int(round(self.player_x))
            py = int(round(self.player_y))
            if 0 <= px < 16 and 0 <= py < 16:
                idx = (py * 16 + px) * 3
                if self.hammer_timer > 0.0:
                    buf[idx:idx+3] = bytes([255, 215, 0])
                else:
                    buf[idx:idx+3] = bytes([255, 255, 255])

        # 7. 生命
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx:idx+3] = bytes([255, 255, 255])

        # 8. 胜负特效
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
        prog = int(((13.0 - self.player_y) / 12.0) * 100.0)
        prog = max(0, min(100, prog))
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": prog,
            "has_hammer": self.hammer_timer > 0.0,
        }
