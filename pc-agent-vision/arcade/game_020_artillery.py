# -*- coding: utf-8 -*-
"""
game_020_artillery.py —— 像素百战天虫 1980 (Artillery 1980)
编号: #020
年代: 1980
核心独占机制: 仰角蓄力抛物线弹道 + 动态侧风抗风偏 + 可破坏弹坑地形 + 对阵炮战
手柄类型: CTRL_ARCADE_AB (左右调仰角 + A键蓄力松开发射)
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


class Game020Artillery(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.terrain: List[int] = [12] * 16
        self.player: Dict[str, Any] = {
            "x": 2,
            "y": 11,
            "hp": 3,
            "angle_deg": 45.0,
            "power": 50.0,
        }
        self.enemy: Dict[str, Any] = {
            "x": 13,
            "y": 11,
            "hp": 3,
            "angle_deg": 45.0,
            "power": 50.0,
        }
        self.shell: Dict[str, Any] = {
            "active": False,
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "is_player": True,
        }
        self.wind: float = 0.0
        self.charging_power: bool = False
        self.turn_player: bool = True
        self.turn_timer: float = 0.0
        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 20

    @property
    def name(self) -> str:
        return "像素百战天虫"

    @property
    def english_name(self) -> str:
        return "Artillery 1980"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "仰角蓄力抛物线弹道 + 动态侧风抗风偏 + 可破坏弹坑地形 + 对阵炮战"

    def init(self) -> None:
        self.reset()

    def generate_terrain(self):
        self.terrain = []
        for x in range(16):
            normalized = float(x) / 15.0
            hill = math.sin(normalized * math.pi) * 4.0
            h = 13 - int(round(hill)) + random.randint(0, 1)
            h = max(8, min(14, h))
            self.terrain.append(h)

        self.wind = (random.randint(-20, 20)) / 10.0

        self.player["x"] = 2
        self.player["y"] = self.terrain[2] - 1
        self.player["hp"] = 3
        self.player["angle_deg"] = 45.0
        self.player["power"] = 50.0

        self.enemy["x"] = 13
        self.enemy["y"] = self.terrain[13] - 1
        self.enemy["hp"] = 3
        self.enemy["angle_deg"] = 45.0
        self.enemy["power"] = 50.0

        self.turn_player = True
        self.turn_timer = 0.0
        self.charging_power = False
        self.shell["active"] = False

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.generate_terrain()

    def fire_shell(self, from_player: bool):
        self.shell["active"] = True
        self.shell["is_player"] = from_player

        if from_player:
            self.shell["x"] = float(self.player["x"])
            self.shell["y"] = float(self.player["y"]) - 0.5
            rad = math.radians(self.player["angle_deg"])
            speed = (self.player["power"] / 100.0) * 16.5
            self.shell["vx"] = speed * math.cos(rad)
            self.shell["vy"] = -speed * math.sin(rad)
        else:
            self.shell["x"] = float(self.enemy["x"])
            self.shell["y"] = float(self.enemy["y"]) - 0.5
            rad = math.radians(self.enemy["angle_deg"])
            speed = (self.enemy["power"] / 100.0) * 16.5
            self.shell["vx"] = -speed * math.cos(rad)
            self.shell["vy"] = -speed * math.sin(rad)

    def explode(self, ex: float, ey: float, from_player: bool):
        self.shell["active"] = False
        gx = int(round(ex))

        # 地形凹陷
        if 0 <= gx < 16:
            if self.terrain[gx] < 15:
                self.terrain[gx] += 1
            if gx > 0 and self.terrain[gx - 1] < 15:
                self.terrain[gx - 1] += 1
            if gx < 15 and self.terrain[gx + 1] < 15:
                self.terrain[gx + 1] += 1

        # 命中判定
        if from_player:
            dist = abs(ex - self.enemy["x"]) + abs(ey - self.enemy["y"])
            if dist <= 1.8:
                self.enemy["hp"] -= 1
                self.score += 150
                if self.score > self.high_score:
                    self.high_score = self.score
                if self.enemy["hp"] <= 0:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    return
            self.turn_player = False
            self.turn_timer = 0.0
        else:
            dist = abs(ex - self.player["x"]) + abs(ey - self.player["y"])
            if dist <= 1.8:
                self.player["hp"] -= 1
                if self.player["hp"] <= 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
            self.turn_player = True
            self.turn_timer = 0.0
            self.wind = (random.randint(-20, 20)) / 10.0

        # 地面下沉
        self.player["y"] = self.terrain[self.player["x"]] - 1
        self.enemy["y"] = self.terrain[self.enemy["x"]] - 1

    def ai_shoot(self):
        self.enemy["angle_deg"] = 45.0 + random.randint(-7, 7)
        estimated_power = 62.0 + (self.wind * 4.0) + random.randint(-5, 5)
        estimated_power = max(30.0, min(95.0, estimated_power))
        self.enemy["power"] = estimated_power
        self.fire_shell(False)

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

            # 1. 炮弹飞行物理
            if self.shell["active"]:
                self.shell["vx"] += self.wind * 2.5 * dt
                self.shell["vy"] += 11.5 * dt  # 重力
                self.shell["x"] += self.shell["vx"] * dt
                self.shell["y"] += self.shell["vy"] * dt

                # 出界判定
                if self.shell["x"] < -1.0 or self.shell["x"] > 16.5 or self.shell["y"] > 15.5:
                    self.shell["active"] = False
                    if self.shell["is_player"]:
                        self.turn_player = False
                        self.turn_timer = 0.0
                    else:
                        self.turn_player = True
                        self.turn_timer = 0.0
                        self.wind = (random.randint(-20, 20)) / 10.0
                    return

                # 撞地判定
                check_gx = int(round(self.shell["x"]))
                if 0 <= check_gx < 16:
                    if self.shell["y"] >= float(self.terrain[check_gx]):
                        self.explode(self.shell["x"], self.shell["y"], self.shell["is_player"])
                        return
                return

            # 2. 玩家回合
            if self.turn_player:
                if keys_down & KEY_LEFT:
                    self.player["angle_deg"] -= 35.0 * dt
                    if self.player["angle_deg"] < 15.0:
                        self.player["angle_deg"] = 15.0
                elif keys_down & KEY_RIGHT:
                    self.player["angle_deg"] += 35.0 * dt
                    if self.player["angle_deg"] > 75.0:
                        self.player["angle_deg"] = 75.0

                if keys_down & KEY_A:
                    self.charging_power = True
                    self.player["power"] += 60.0 * dt
                    if self.player["power"] > 100.0:
                        self.player["power"] = 20.0
                elif self.charging_power:
                    self.charging_power = False
                    self.fire_shell(True)
            else:
                # 3. AI 回合
                self.turn_timer += dt
                if self.turn_timer >= 0.8:
                    self.turn_timer = 0.0
                    self.ai_shoot()

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        # 清空画面
        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 1. 山脉地形
        for x in range(16):
            surface_y = self.terrain[x]
            for y in range(surface_y, 16):
                idx = (y * 16 + x) * 3
                if y == surface_y:
                    buf[idx + 0] = 39
                    buf[idx + 1] = 174
                    buf[idx + 2] = 96
                else:
                    buf[idx + 0] = 120
                    buf[idx + 1] = 66
                    buf[idx + 2] = 18

        # 2. 玩家坦克
        if self.player["hp"] > 0:
            idx = (self.player["y"] * 16 + self.player["x"]) * 3
            buf[idx + 0] = 0
            buf[idx + 1] = 255
            buf[idx + 2] = 255

        # 3. 敌方坦克
        if self.enemy["hp"] > 0:
            idx = (self.enemy["y"] * 16 + self.enemy["x"]) * 3
            buf[idx + 0] = 231
            buf[idx + 1] = 76
            buf[idx + 2] = 60

        # 4. 飞行炮弹
        if self.shell["active"]:
            sx = int(round(self.shell["x"]))
            sy = int(round(self.shell["y"]))
            if 0 <= sx < 16 and 0 <= sy < 16:
                idx = (sy * 16 + sx) * 3
                buf[idx + 0] = 255
                buf[idx + 1] = 255
                buf[idx + 2] = 220

        # 5. 顶部 HUD
        for i in range(self.player["hp"]):
            idx = (0 * 16 + (i + 1)) * 3
            buf[idx + 0] = 0
            buf[idx + 1] = 255
            buf[idx + 2] = 255

        for i in range(self.enemy["hp"]):
            idx = (0 * 16 + (14 - i)) * 3
            buf[idx + 0] = 231
            buf[idx + 1] = 76
            buf[idx + 2] = 60

        wind_center = 8 if self.wind > 0.3 else 7
        idx_wind = (0 * 16 + wind_center) * 3
        buf[idx_wind + 0] = 241
        buf[idx_wind + 1] = 196
        buf[idx_wind + 2] = 15

        # 6. 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx + 0] = 46
                buf[idx + 1] = 204
                buf[idx + 2] = 113
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx + 0] = 231
                buf[idx + 1] = 76
                buf[idx + 2] = 60

        return bytes(buf)

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "lives": self.player["hp"],
            "state": self.state,
            "progress": int(((3 - self.enemy["hp"]) * 100) / 3),
        }
