"""game_074_highway_racer.py —— 目标 #074 变道赛车 (Highway Racer 1979)
三车道极速逆向慢车冲刷 + 左右变道超车 + 1000m 极速通关
"""

import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TWO_BUTTON,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

LANE_CENTERS = [3.5, 7.0, 10.5]


class TrafficCar:
    def __init__(self, lane: int, car_type: int):
        self.active = True
        self.lane = lane
        self.x = LANE_CENTERS[lane]
        self.y = -3.0
        if car_type == 0:
            self.width, self.height, self.speed = 2, 3, 6.0
            self.r, self.g, self.b = 241, 196, 15
        elif car_type == 1:
            self.width, self.height, self.speed = 2, 2, 9.0
            self.r, self.g, self.b = 52, 152, 219
        else:
            self.width, self.height, self.speed = 2, 2, 12.0
            self.r, self.g, self.b = 236, 240, 241


class Game074HighwayRacer(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.car_x = 7.0
        self.speed = 18.0
        self.road_scroll_y = 0.0
        self.distance_m = 0.0
        self.target_distance = 1000.0
        self.lives = 3
        self.traffic: List[TrafficCar] = []
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.spawn_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 74

    @property
    def name(self) -> str:
        return "变道赛车"

    @property
    def english_name(self) -> str:
        return "Highway Racer 1979"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_TWO_BUTTON

    @property
    def core_mechanic(self) -> str:
        return "三车道高速变道超车与路障闪避"

    def init(self) -> None:
        self.reset()

    def _reset_player_car(self):
        self.car_x = 7.0
        self.speed = 16.0
        self.traffic = [c for c in self.traffic if c.y <= 8.0]

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 3
        self.distance_m = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.spawn_timer = 0.0
        self.road_scroll_y = 0.0
        self.traffic = []
        self._reset_player_car()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.lives = 3
            self.distance_m = 0.0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.spawn_timer = 0.0
            self.road_scroll_y = 0.0
            self.traffic = []
            self._reset_player_car()

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _crash_car(self):
        if self.lives > 1:
            self.lives -= 1
            self._reset_player_car()
        else:
            self.lives = 0
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0

    def _spawn_traffic(self):
        if len(self.traffic) >= 4:
            return
        lane = random.randint(0, 2)
        for c in self.traffic:
            if c.y < 2.0 and c.lane == lane:
                return
        self.traffic.append(TrafficCar(lane, random.randint(0, 2)))

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN | KEY_A | KEY_B):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN | KEY_A | KEY_B)):
                self.start()
            return

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            steer_speed = 9.0
            if keys_down & KEY_LEFT:
                self.car_x -= steer_speed * dt
            elif keys_down & KEY_RIGHT:
                self.car_x += steer_speed * dt

            if keys_down & (KEY_UP | KEY_A):
                self.speed = min(28.0, self.speed + 10.0 * dt)
            elif keys_down & (KEY_DOWN | KEY_B):
                self.speed = max(10.0, self.speed - 12.0 * dt)
            else:
                if self.speed > 18.0:
                    self.speed -= 4.0 * dt
                elif self.speed < 18.0:
                    self.speed += 4.0 * dt

            if self.car_x < 2.2 or self.car_x > 11.8:
                self._crash_car()
                return

            self.road_scroll_y = (self.road_scroll_y + self.speed * dt) % 4.0
            self.distance_m += self.speed * dt * 2.5
            self._score = int(self.distance_m)
            if self._score > self._high_score:
                self._high_score = self._score

            if self.distance_m >= self.target_distance:
                self._state = STATE_VICTORY
                self.state_timer = 0.0
                return

            self.spawn_timer += dt
            if self.spawn_timer >= 1.2:
                self.spawn_timer = 0.0
                self._spawn_traffic()

            for c in self.traffic:
                rel_speed = self.speed - c.speed
                c.y += rel_speed * dt

                px1, px2 = self.car_x, self.car_x + 1.8
                py1, py2 = 12.0, 14.5
                tx1, tx2 = c.x, c.x + c.width - 0.2
                ty1, ty2 = c.y, c.y + c.height

                if px2 >= tx1 and px1 <= tx2 and py2 >= ty1 and py1 <= ty2:
                    self._crash_car()
                    return

            self.traffic = [c for c in self.traffic if c.y <= 17.0]

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for y in range(16):
            for x in (0, 1, 14, 15):
                idx = (y * 16 + x) * 3
                fb[idx : idx + 3] = bytes([34, 139, 34])
            for x in range(2, 14):
                idx = (y * 16 + x) * 3
                fb[idx : idx + 3] = bytes([35, 35, 38])

        scroll_offset = int(round(self.road_scroll_y))
        for y in range(16):
            if ((y + scroll_offset) % 4) < 2:
                for col in (5, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([220, 220, 220])

        for c in self.traffic:
            tx = int(round(c.x))
            ty = int(round(c.y))
            for dy in range(c.height):
                for dx in range(c.width):
                    x, y = tx + dx, ty + dy
                    if 0 <= x < 16 and 0 <= y < 16:
                        idx = (y * 16 + x) * 3
                        fb[idx : idx + 3] = bytes([c.r, c.g, c.b])

        cx = int(round(self.car_x))
        for dy in range(3):
            for dx in range(2):
                x, y = cx + dx, 12 + dy
                if 0 <= x < 16 and y < 16:
                    idx = (y * 16 + x) * 3
                    if dy in (0, 2):
                        fb[idx : idx + 3] = bytes([231, 76, 60])
                    else:
                        fb[idx : idx + 3] = bytes([52, 152, 219])

        for i in range(min(3, self.lives)):
            idx = (i * 2) * 3
            fb[idx : idx + 3] = bytes([231, 76, 60])

        if self._state == STATE_PAUSED:
            for y in range(6, 10):
                for col in (6, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([250, 250, 250])

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": int(self.distance_m),
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, int(self.distance_m * 100 // max(1.0, self.target_distance))),
        }
