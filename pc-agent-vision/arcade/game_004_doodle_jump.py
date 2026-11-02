# -*- coding: utf-8 -*-
"""
game_004_doodle_jump.py —— 涂鸦跳跃 16 (Doodle Jump 16)
编号: #004
年代: 2009 (Lima Sky)
核心独占机制: 接触刚体自动高弹起跳 + 左右无限穿屏 + 纵向单向向上无限滚动 (无主动跳跃键)
手柄类型: CTRL_TWO_BUTTON (左 / 右双键)
"""

import math
import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    KEY_A,
    CTRL_TWO_BUTTON,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)

PLAT_NORMAL  = 0  # 绿色稳定跳板 (弹力 1.0x)
PLAT_MOVING  = 1  # 青色水平巡逻跳板 (左右移动)
PLAT_SPRING  = 2  # 金色弹簧跳板 (弹力 1.6x 超级跳)
PLAT_FRAGILE = 3  # 棕色脆弱碎板 (踩后断裂失效)

class Platform:
    def __init__(self, x: float, y: float, plat_type: int = PLAT_NORMAL, vx: float = 0.0):
        self.x = x
        self.y = y
        self.type = plat_type
        self.vx = vx
        self.broken = False

class Game004DoodleJump(BaseCartridge):
    def __init__(self):
        self._id = 4
        self._name = "涂鸦跳跃"
        self._english_name = "Doodle Jump 16"
        self._year = 2009
        self._control_type = CTRL_TWO_BUTTON
        self._core_mechanic = "接触刚体自动反弹起跳 + 左右无限穿屏 + 纵向单向上冲"

        self.state = STATE_TITLE
        self.player_x = 7.0
        self.player_y = 10.0
        self.player_vx = 0.0
        self.player_vy = -12.0
        self.facing_right = True

        self.camera_altitude = 0.0
        self.score = 0
        self.high_score = 0
        self.platforms: List[Platform] = []
        self.frame_buffer = bytearray(16 * 16 * 3)

        self.reset()

    @property
    def game_id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def english_name(self) -> str:
        return self._english_name

    @property
    def release_year(self) -> int:
        return self._year

    @property
    def control_type(self) -> int:
        return self._control_type

    @property
    def core_mechanic(self) -> str:
        return self._core_mechanic

    def init(self) -> None:
        self.reset()

    def _spawn_platform(self, min_y: float, max_y: float) -> Platform:
        x = float(random.randint(1, 12))
        y = random.uniform(min_y, max_y)
        roll = random.random()

        if self.camera_altitude < 50.0:
            if roll < 0.80:
                p_type = PLAT_NORMAL
            elif roll < 0.95:
                p_type = PLAT_SPRING
            else:
                p_type = PLAT_MOVING
        else:
            if roll < 0.45:
                p_type = PLAT_NORMAL
            elif roll < 0.70:
                p_type = PLAT_MOVING
            elif roll < 0.85:
                p_type = PLAT_SPRING
            else:
                p_type = PLAT_FRAGILE

        vx = 2.5 if p_type == PLAT_MOVING and random.random() < 0.5 else -2.5 if p_type == PLAT_MOVING else 0.0
        return Platform(x, y, p_type, vx)

    def reset(self) -> None:
        self.state = STATE_PLAYING
        self.player_x = 7.0
        self.player_y = 10.0
        self.player_vx = 0.0
        self.player_vy = -12.0
        self.facing_right = True
        self.camera_altitude = 0.0
        self.score = 0

        self.platforms = [Platform(6.0, 13.0, PLAT_NORMAL, 0.0)]
        for i in range(1, 6):
            min_y = 13.0 - (i * 2.5)
            max_y = min_y + 1.0
            self.platforms.append(self._spawn_platform(min_y, max_y))

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self.state == STATE_TITLE:
            self.player_vy += 24.0 * dt
            self.player_y += self.player_vy * dt
            if self.player_y >= 12.0:
                self.player_y = 12.0
                self.player_vy = -10.0
            if keys_pressed & (KEY_START | KEY_A | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_GAMEOVER:
            if keys_pressed & (KEY_START | KEY_A | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            move_accel = 24.0
            max_vx = 7.0
            friction = 12.0

            if keys_down & KEY_LEFT:
                self.player_vx -= move_accel * dt
                self.facing_right = False
            elif keys_down & KEY_RIGHT:
                self.player_vx += move_accel * dt
                self.facing_right = True
            else:
                if self.player_vx > 0.0:
                    self.player_vx = max(0.0, self.player_vx - friction * dt)
                elif self.player_vx < 0.0:
                    self.player_vx = min(0.0, self.player_vx + friction * dt)

            self.player_vx = max(-max_vx, min(max_vx, self.player_vx))

            gravity = 28.0
            self.player_vy += gravity * dt

            next_x = self.player_x + self.player_vx * dt
            next_y = self.player_y + self.player_vy * dt

            # 左右穿屏
            if next_x < -1.5:
                next_x = 15.5
            elif next_x > 15.5:
                next_x = -1.5
            self.player_x = next_x

            # 移动跳板巡逻
            for p in self.platforms:
                if p.type == PLAT_MOVING and not p.broken:
                    p.x += p.vx * dt
                    if p.x <= 0.0:
                        p.x = 0.0
                        p.vx = -p.vx
                    elif p.x >= 13.0:
                        p.x = 13.0
                        p.vx = -p.vx

            # 踏板物理碰撞 (仅在向下下落时判定脚底相交)
            if self.player_vy > 0.0:
                feet_old_y = self.player_y + 2.0
                feet_new_y = next_y + 2.0

                for p in self.platforms:
                    if p.broken:
                        continue

                    plat_top = p.y
                    plat_left = p.x - 0.8
                    plat_right = p.x + 3.0

                    if (self.player_x + 1.8 >= plat_left) and (self.player_x <= plat_right):
                        if (feet_old_y <= plat_top + 0.5) and (feet_new_y >= plat_top - 0.2):
                            next_y = plat_top - 2.0
                            if p.type == PLAT_SPRING:
                                self.player_vy = -20.5  # 金色弹簧超级跳
                            elif p.type == PLAT_FRAGILE:
                                p.broken = True
                                self.player_vy = -7.5   # 碎板微弹后坍塌
                            else:
                                self.player_vy = -13.5  # 绿色标准反弹
                            break

            self.player_y = next_y

            # 摄像机向上滚动
            scroll_threshold = 7.0
            if self.player_y < scroll_threshold:
                dy = scroll_threshold - self.player_y
                self.player_y = scroll_threshold
                self.camera_altitude += dy
                self.score = int(self.camera_altitude * 10.0)
                if self.score > self.high_score:
                    self.high_score = self.score

                # 平台相对下移
                for p in self.platforms:
                    p.y += dy
                    if p.y > 16.5:
                        # 顶部循环生成新平台
                        new_p = self._spawn_platform(-1.5, 0.5)
                        p.x = new_p.x
                        p.y = new_p.y
                        p.type = new_p.type
                        p.vx = new_p.vx
                        p.broken = False

            # 跌落屏幕底部死亡
            if self.player_y > 16.5:
                self.state = STATE_GAMEOVER

        elif self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING

    def render(self) -> bytearray:
        fb = self.frame_buffer
        # 1. 午夜蓝背景
        for i in range(256):
            fb[i * 3 + 0] = 10
            fb[i * 3 + 1] = 14
            fb[i * 3 + 2] = 24

        # 2. 星星点缀
        star_offset = int(self.camera_altitude) % 16
        for i in range(4):
            sx = (i * 5 + 3) % 16
            sy = (i * 7 + star_offset) % 16
            idx = (sy * 16 + sx) * 3
            fb[idx + 0] = 30
            fb[idx + 1] = 45
            fb[idx + 2] = 70

        # 3. 绘制跳板
        for p in self.platforms:
            if p.broken:
                continue
            py = int(round(p.y))
            px = int(round(p.x))
            if 0 <= py < 16:
                r, g, b = (39, 174, 96)
                if p.type == PLAT_MOVING:
                    r, g, b = (0, 210, 211)
                elif p.type == PLAT_SPRING:
                    r, g, b = (241, 196, 15)
                elif p.type == PLAT_FRAGILE:
                    r, g, b = (211, 84, 0)

                for dx in range(3):
                    x = px + dx
                    if 0 <= x < 16:
                        idx = (py * 16 + x) * 3
                        fb[idx + 0] = r
                        fb[idx + 1] = g
                        fb[idx + 2] = b
                        if p.type == PLAT_SPRING and dx == 1:
                            fb[idx + 0] = fb[idx + 1] = fb[idx + 2] = 255

        # 4. 绘制小涂鸦 (2x2)
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        for dy in range(2):
            for dx in range(2):
                x = px + dx
                y = py + dy
                if 0 <= x < 16 and 0 <= y < 16:
                    idx = (y * 16 + x) * 3
                    if dy == 0:
                        fb[idx + 0] = 46
                        fb[idx + 1] = 204
                        fb[idx + 2] = 113
                        if (self.facing_right and dx == 1) or (not self.facing_right and dx == 0):
                            fb[idx + 0] = fb[idx + 1] = fb[idx + 2] = 255
                    else:
                        fb[idx + 0] = 230
                        fb[idx + 1] = 126
                        fb[idx + 2] = 34

        # 5. 状态特效
        if self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                fb[idx + 0] = 231
                fb[idx + 1] = 76
                fb[idx + 2] = 60
        elif self.state == STATE_PAUSED:
            for y in range(6, 10):
                idx1 = (y * 16 + 6) * 3
                idx2 = (y * 16 + 9) * 3
                fb[idx1 + 0] = fb[idx1 + 1] = fb[idx1 + 2] = 240
                fb[idx2 + 0] = fb[idx2 + 1] = fb[idx2 + 2] = 240

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self._id,
            "name": self._name,
            "score": self.score,
            "high_score": self.high_score,
            "lives": 0 if self.state == STATE_GAMEOVER else 1,
            "state": self.state,
            "altitude": round(self.camera_altitude, 1),
            "progress": min(100, int(self.camera_altitude)),
        }
