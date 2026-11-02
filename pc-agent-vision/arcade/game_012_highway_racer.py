# -*- coding: utf-8 -*-
"""
game_012_highway_racer.py —— 极速变道赛车 1982 (Highway Racer 1982)
编号: #012
年代: 1982 (南梦宫 Namco Pole Position / 世嘉 Monaco GP)
核心独占机制: 极速三车道逆向慢车冲刷 + 左右变道超车 + 油门加减速 + 护栏碰撞损毁
手柄类型: CTRL_TWO_BUTTON (左右变道避让 + 油门/刹车)
"""

import math
import random
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
    CTRL_TWO_BUTTON,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

LANE_CENTERS = [3.5, 7.0, 10.5]

class TrafficCar:
    def __init__(self):
        self.active = False
        self.x = 7.0
        self.y = -3.0
        self.lane = 1
        self.width = 2
        self.height = 2
        self.speed = 8.0
        self.r = 52
        self.g = 152
        self.b = 219

class Game012HighwayRacer(BaseCartridge):
    def __init__(self):
        self._id = 12
        self._name = "极速变道赛车"
        self._english_name = "Highway Racer 1982"
        self._year = 1982
        self._control_type = CTRL_TWO_BUTTON
        self._core_mechanic = "极速三车道逆向慢车冲刷 + 左右变道超车 + 油门加减速 + 护栏碰撞损毁"

        self.k_max_traffic = 4
        self.state = STATE_TITLE
        self.car_x = 7.0
        self.speed = 18.0
        self.road_scroll_y = 0.0
        self.distance_m = 0.0
        self.target_distance = 1000.0

        self.lives = 3
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0
        self.spawn_timer = 0.0

        self.traffic = [TrafficCar() for _ in range(self.k_max_traffic)]
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

    def reset_player_car(self):
        self.car_x = 7.0
        self.speed = 16.0
        for t in self.traffic:
            if t.active and t.y > 8.0:
                t.active = False

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.distance_m = 0.0
        self.state_timer = 0.0
        self.spawn_timer = 0.0
        self.road_scroll_y = 0.0

        for t in self.traffic:
            t.active = False

        self.reset_player_car()

    def crash_car(self):
        if self.lives > 0:
            self.lives -= 1
        if self.lives == 0:
            self.state = STATE_GAMEOVER
            self.state_timer = 0.0
        else:
            self.reset_player_car()

    def spawn_traffic(self):
        slot = -1
        for i, t in enumerate(self.traffic):
            if not t.active:
                slot = i
                break
        if slot == -1:
            return

        chosen_lane = random.randint(0, 2)
        for t in self.traffic:
            if t.active and t.y < 2.0 and t.lane == chosen_lane:
                return

        car_type = random.randint(0, 2)
        target = self.traffic[slot]
        target.active = True
        target.lane = chosen_lane
        target.x = LANE_CENTERS[chosen_lane]
        target.y = -3.0

        if car_type == 0:
            target.width = 2
            target.height = 3
            target.speed = 6.0
            target.r, target.g, target.b = 241, 196, 15
        elif car_type == 1:
            target.width = 2
            target.height = 2
            target.speed = 9.0
            target.r, target.g, target.b = 52, 152, 219
        else:
            target.width = 2
            target.height = 2
            target.speed = 12.0
            target.r, target.g, target.b = 236, 240, 241

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)):
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

            accel_rate = 14.0
            brake_rate = 22.0
            if keys_down & (KEY_UP | KEY_A):
                self.speed = min(28.0, self.speed + accel_rate * dt)
            elif keys_down & (KEY_DOWN | KEY_B):
                self.speed = max(8.0, self.speed - brake_rate * dt)
            else:
                if self.speed < 18.0:
                    self.speed = min(18.0, self.speed + 4.0 * dt)
                elif self.speed > 18.0:
                    self.speed = max(18.0, self.speed - 4.0 * dt)

            steer_speed = 10.0
            if keys_down & KEY_LEFT:
                self.car_x -= steer_speed * dt
            elif keys_down & KEY_RIGHT:
                self.car_x += steer_speed * dt

            if self.car_x < 2.4 or self.car_x > 11.6:
                self.crash_car()
                return

            self.distance_m += self.speed * 2.5 * dt
            self.road_scroll_y += self.speed * dt
            if self.road_scroll_y >= 4.0:
                self.road_scroll_y -= 4.0

            if self.distance_m >= self.target_distance:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 500
                if self.score > self.high_score:
                    self.high_score = self.score
                return

            self.spawn_timer += dt
            if self.spawn_timer >= 1.4:
                self.spawn_timer = 0.0
                self.spawn_traffic()

            for t in self.traffic:
                if t.active:
                    rel_speed = self.speed - t.speed
                    t.y += rel_speed * dt

                    if t.y > 15.5:
                        t.active = False
                        self.score += 50
                        if self.score > self.high_score:
                            self.high_score = self.score
                    elif t.y < -4.0:
                        t.active = False
                    else:
                        car_top = 13.0
                        car_bottom = 14.8
                        t_top = t.y
                        t_bottom = t.y + t.height

                        if t_bottom >= car_top and t_top <= car_bottom:
                            if abs(self.car_x - t.x) < 1.5:
                                self.crash_car()
                                return

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if x < 2 or x > 12:
                    self.frame_buffer[idx:idx+3] = bytes([39, 174, 96])
                else:
                    self.frame_buffer[idx:idx+3] = bytes([33, 33, 33])

        scroll_step = int(self.road_scroll_y)
        for y in range(16):
            red = ((y + scroll_step) % 4 < 2)
            cr = 231 if red else 255
            cg = 76  if red else 255
            cb = 60  if red else 255

            idx_left = (y * 16 + 1) * 3
            idx_right = (y * 16 + 13) * 3
            self.frame_buffer[idx_left:idx_left+3] = bytes([cr, cg, cb])
            self.frame_buffer[idx_right:idx_right+3] = bytes([cr, cg, cb])

        for y in range(16):
            if (y + scroll_step) % 4 < 2:
                idx1 = (y * 16 + 5) * 3
                idx2 = (y * 16 + 9) * 3
                self.frame_buffer[idx1:idx1+3] = bytes([241, 196, 15])
                self.frame_buffer[idx2:idx2+3] = bytes([241, 196, 15])

        for t in self.traffic:
            if t.active:
                tx = int(round(t.x))
                ty_start = int(round(t.y))
                ty_end = ty_start + t.height
                for y in range(ty_start, ty_end):
                    if 0 <= y < 16:
                        for dx in (-1, 0):
                            x = tx + dx
                            if 0 <= x < 16:
                                idx = (y * 16 + x) * 3
                                self.frame_buffer[idx:idx+3] = bytes([t.r, t.g, t.b])

        px = int(round(self.car_x))
        if 0 <= px < 16:
            idx = (13 * 16 + px) * 3
            self.frame_buffer[idx:idx+3] = bytes([0, 255, 255])
        for dx in (-1, 0, 1):
            x = px + dx
            if 0 <= x < 16:
                idx = (14 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        speed_dots = int((self.speed - 8.0) / 4.0) + 1
        for i in range(min(6, speed_dots)):
            idx = (0 * 16 + (15 - i)) * 3
            self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])

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
            "speed": self.speed,
            "distance_m": self.distance_m,
            "progress": min(100, int((self.distance_m * 100) / self.target_distance)),
        }
