# -*- coding: utf-8 -*-
"""
game_011_frogger.py —— 像素青蛙过河 1981 (Frogger 1981)
编号: #011
年代: 1981 (科乐美 Konami)
核心独占机制: 垂直多车道公路闪避 + 水流浮木动态附着漂移 + 五穴安全进驻清屏
手柄类型: CTRL_DPAD_4WAY (上下左右离散网格跳跃)
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_DPAD_4WAY,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

HOME_X = [1, 4, 7, 10, 13]

class LaneObstacle:
    def __init__(self, x: float, width: float):
        self.x = x
        self.width = width

class Lane:
    def __init__(self, speed: float, item_w: float, is_river: bool, r: int, g: int, b: int, items: List[LaneObstacle]):
        self.speed = speed
        self.item_w = item_w
        self.is_river = is_river
        self.r = r
        self.g = g
        self.b = b
        self.items = items

def check_item_overlap(px: float, item_x: float, item_w: float) -> bool:
    left = item_x
    right = item_x + item_w
    if left - 0.2 <= px <= right - 0.2:
        return True
    if right > 16.0:
        if 0.0 <= px <= (right - 16.0 - 0.2):
            return True
    if left < 0.0:
        if (16.0 + left - 0.2) <= px < 16.0:
            return True
    return False

class Game011Frogger(BaseCartridge):
    def __init__(self):
        self._id = 11
        self._name = "青蛙过河"
        self._english_name = "Frogger 1981"
        self._year = 1981
        self._control_type = CTRL_DPAD_4WAY
        self._core_mechanic = "垂直多车道公路闪避 + 水流浮木动态附着漂移 + 五穴安全进驻清屏"

        self.k_num_homes = 5
        self.k_total_lanes = 16

        self.state = STATE_TITLE
        self.frog_x = 7.0
        self.frog_y = 14
        self.lives = 3
        self.score = 0
        self.high_score = 0
        self.round_timer = 30.0
        self.state_timer = 0.0
        self.homes = [False] * self.k_num_homes
        self.homes_occupied = 0

        self.lanes: Dict[int, Lane] = {}
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

    def setup_lanes(self):
        self.lanes = {}
        # 河流车道 (1..5)
        self.lanes[1] = Lane(2.8, 3.0, True, 160, 82, 45, [LaneObstacle(1.0, 3.0), LaneObstacle(9.0, 3.0)])
        self.lanes[2] = Lane(-2.5, 2.0, True, 230, 126, 34, [LaneObstacle(0.0, 2.0), LaneObstacle(6.0, 2.0), LaneObstacle(12.0, 2.0)])
        self.lanes[3] = Lane(1.8, 4.0, True, 160, 82, 45, [LaneObstacle(2.0, 4.0), LaneObstacle(10.0, 4.0)])
        self.lanes[4] = Lane(-3.2, 2.0, True, 230, 126, 34, [LaneObstacle(3.0, 2.0), LaneObstacle(11.0, 2.0)])
        self.lanes[5] = Lane(2.4, 2.0, True, 160, 82, 45, [LaneObstacle(1.0, 2.0), LaneObstacle(7.0, 2.0), LaneObstacle(13.0, 2.0)])

        # 公路车道 (7..12)
        self.lanes[7] = Lane(-4.5, 1.0, False, 231, 76, 60, [LaneObstacle(4.0, 1.0), LaneObstacle(12.0, 1.0)])
        self.lanes[8] = Lane(2.2, 2.0, False, 236, 240, 241, [LaneObstacle(2.0, 2.0), LaneObstacle(10.0, 2.0)])
        self.lanes[9] = Lane(-1.6, 3.0, False, 241, 196, 15, [LaneObstacle(6.0, 3.0)])
        self.lanes[10] = Lane(3.8, 1.0, False, 155, 89, 182, [LaneObstacle(3.0, 1.0), LaneObstacle(11.0, 1.0)])
        self.lanes[11] = Lane(-2.8, 2.0, False, 52, 152, 219, [LaneObstacle(2.0, 2.0), LaneObstacle(9.0, 2.0)])
        self.lanes[12] = Lane(4.0, 1.0, False, 230, 126, 34, [LaneObstacle(1.0, 1.0), LaneObstacle(7.0, 1.0), LaneObstacle(13.0, 1.0)])

    def reset_frog_position(self):
        self.frog_x = 7.0
        self.frog_y = 14
        self.round_timer = 30.0

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.homes_occupied = 0
        self.homes = [False] * self.k_num_homes
        self.setup_lanes()
        self.reset_frog_position()

    def kill_frog(self):
        if self.lives > 0:
            self.lives -= 1
        if self.lives == 0:
            self.state = STATE_GAMEOVER
            self.state_timer = 0.0
        else:
            self.reset_frog_position()

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
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

            self.round_timer -= dt
            if self.round_timer <= 0.0:
                self.kill_frog()
                return

            # 车道障碍物移动
            for lane in self.lanes.values():
                for item in lane.items:
                    item.x += lane.speed * dt
                    if item.x >= 16.0:
                        item.x -= 16.0
                    elif item.x < -lane.item_w:
                        item.x += 16.0

            # 青蛙离散跳跃
            if keys_pressed & KEY_UP:
                self.frog_y -= 1
                self.score += 10
                if self.score > self.high_score:
                    self.high_score = self.score
            elif keys_pressed & KEY_DOWN:
                if self.frog_y < 14:
                    self.frog_y += 1
            elif keys_pressed & KEY_LEFT:
                self.frog_x = max(0.0, self.frog_x - 1.0)
            elif keys_pressed & KEY_RIGHT:
                self.frog_x = min(15.0, self.frog_x + 1.0)

            # 洞穴终点判定 (Row 0)
            if self.frog_y == 0:
                entered = False
                for h in range(self.k_num_homes):
                    if abs(self.frog_x - float(HOME_X[h])) < 0.75:
                        if not self.homes[h]:
                            self.homes[h] = True
                            self.homes_occupied += 1
                            self.score += 200 + int(self.round_timer * 10)
                            if self.score > self.high_score:
                                self.high_score = self.score
                            entered = True

                            if self.homes_occupied >= self.k_num_homes:
                                self.state = STATE_VICTORY
                                self.state_timer = 0.0
                                return
                            else:
                                self.reset_frog_position()
                                return
                        else:
                            self.kill_frog()
                            return
                if not entered:
                    self.kill_frog()
                    return

            # 河流检测 (Row 1..5)
            if 1 <= self.frog_y <= 5:
                rlane = self.lanes[self.frog_y]
                on_item = False
                for item in rlane.items:
                    if check_item_overlap(self.frog_x, item.x, item.width):
                        on_item = True
                        break

                if on_item:
                    self.frog_x += rlane.speed * dt
                    if self.frog_x < -0.2 or self.frog_x >= 15.8:
                        self.kill_frog()
                        return
                else:
                    self.kill_frog()
                    return

            # 公路碰撞检测 (Row 7..12)
            if 7 <= self.frog_y <= 12:
                hlane = self.lanes[self.frog_y]
                for item in hlane.items:
                    if check_item_overlap(self.frog_x, item.x, item.width):
                        self.kill_frog()
                        return

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        # 背景环境
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if y == 0:
                    self.frame_buffer[idx:idx+3] = bytes([19, 15, 64]) # 灌木
                elif 1 <= y <= 5:
                    self.frame_buffer[idx:idx+3] = bytes([21, 67, 96]) # 河水
                elif y == 6:
                    self.frame_buffer[idx:idx+3] = bytes([39, 174, 96]) # 中央草坪
                elif 7 <= y <= 12:
                    self.frame_buffer[idx:idx+3] = bytes([28, 40, 51]) # 柏油路
                elif 13 <= y <= 14:
                    self.frame_buffer[idx:idx+3] = bytes([46, 134, 193]) # 起跳站台
                else:
                    self.frame_buffer[idx:idx+3] = bytes([0, 0, 0])

        # 终点洞穴
        for h in range(self.k_num_homes):
            hx = HOME_X[h]
            idx = (0 * 16 + hx) * 3
            if self.homes[h]:
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
            else:
                self.frame_buffer[idx:idx+3] = bytes([0, 210, 211])

        # 车道物体
        for y, lane in self.lanes.items():
            for item in lane.items:
                for x in range(16):
                    if check_item_overlap(float(x), item.x, item.width):
                        idx = (y * 16 + x) * 3
                        self.frame_buffer[idx:idx+3] = bytes([lane.r, lane.g, lane.b])

        # 青蛙
        fx = int(round(self.frog_x))
        fy = self.frog_y
        if 0 <= fx < 16 and 0 <= fy < 16:
            idx = (fy * 16 + fx) * 3
            self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])

        # 状态栏 (生命与计时)
        for i in range(self.lives):
            idx = (15 * 16 + (i * 2)) * 3
            self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        timer_bars = int((self.round_timer / 30.0) * 6.0)
        for i in range(timer_bars):
            idx = (15 * 16 + (10 + i)) * 3
            self.frame_buffer[idx:idx+3] = bytes([241, 196, 15])

        # 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "homes_occupied": self.homes_occupied,
            "round_timer": self.round_timer,
        }
