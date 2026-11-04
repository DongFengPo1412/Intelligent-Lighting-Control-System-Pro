# -*- coding: utf-8 -*-
"""game_087_traffic_control.py —— 目标 #087 交通灯管理 (Traffic Control)
机制: 十字路口双向车流排队 + 红绿灯相位切换/全红清空 + T字碰撞与压车路怒双重危机
"""

from typing import Dict, Any, List, Tuple
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
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
from .arcade_result_screen import ArcadeResultScreen, set_pixel

CAR_PALETTE = (
    (60, 200, 255),
    (255, 205, 45),
    (195, 110, 255),
    (240, 245, 250),
)


class TrafficCar:
    def __init__(self, lane: int, speed: float, color_id: int):
        self.active = True
        self.lane = lane  # 0=South(x=6), 1=North(x=9), 2=East(y=9), 3=West(y=6)
        self.prog = 0.0
        self.speed = speed
        self.color_id = color_id


class Game087TrafficControl(BaseCartridge):
    MAX_CARS = 16
    TARGET_CARS = 30

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.phase = 0
        self.all_red_timer = 0.0
        self.passed_cars = 0
        self.incidents = 0
        self.spawn_timer = 0.45
        self.rng_seed = 0x1992087A
        self.crash_flash_timer = 0.0
        self.crash_x = 7
        self.crash_y = 7
        self.lane_rage_timer: List[float] = [0.0, 0.0, 0.0, 0.0]
        self.cars: List[TrafficCar] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 87

    @property
    def name(self) -> str:
        return "交通灯管理"

    @property
    def english_name(self) -> str:
        return "Traffic Control"

    @property
    def release_year(self) -> int:
        return 1992

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "十字路口信号相位调度与防撞防堵车流控制"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _next_rand(self) -> int:
        self.rng_seed = (self.rng_seed * 1103515245 + 12345) & 0xFFFFFFFF
        return self.rng_seed

    def car_xy(self, c: TrafficCar) -> Tuple[float, float]:
        if c.lane == 0:
            return 6.0, c.prog
        if c.lane == 1:
            return 9.0, 15.0 - c.prog
        if c.lane == 2:
            return c.prog, 9.0
        return 15.0 - c.prog, 6.0

    def is_axis_green(self, axis: int) -> bool:
        if self.all_red_timer > 0.0:
            return False
        return self.phase == axis

    def spawn_car(self, lane: int) -> None:
        for c in self.cars:
            if c.active and c.lane == lane and c.prog < 2.0:
                return
        if sum(1 for c in self.cars if c.active) >= self.MAX_CARS:
            return
        r = self._next_rand()
        cid = (r >> 16) % 4
        spd = 4.6 + ((r >> 20) % 3) * 0.35
        self.cars.append(TrafficCar(lane, spd, cid))

    def _setup_match(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.phase = 0
        self.all_red_timer = 0.0
        self.passed_cars = 0
        self.incidents = 0
        self.spawn_timer = 0.45
        self.rng_seed = 0x1992087A
        self.crash_flash_timer = 0.0
        self.crash_x = 7
        self.crash_y = 7
        self.lane_rage_timer = [0.0, 0.0, 0.0, 0.0]
        self.cars = []
        self.spawn_car(0)
        self.spawn_car(2)

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._setup_match(STATE_TITLE)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_match(STATE_PLAYING)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _record_incident(self, fx: int, fy: int) -> None:
        self.crash_x = fx
        self.crash_y = fy
        self.crash_flash_timer = 0.5
        self.incidents += 1
        if self.incidents >= 3:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
                self.start()
            return

        if keys_pressed & KEY_START:
            self._state = STATE_PAUSED
            return

        if self.crash_flash_timer > 0.0:
            self.crash_flash_timer -= dt
        if self.all_red_timer > 0.0:
            self.all_red_timer = max(0.0, self.all_red_timer - dt)

        if keys_pressed & KEY_A:
            self.phase = 1 - self.phase
            self.all_red_timer = 0.0
        if keys_pressed & KEY_B:
            self.all_red_timer = 0.0 if self.all_red_timer > 0.0 else 2.0

        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            ln = (self._next_rand() >> 16) % 4
            self.spawn_car(ln)
            self.spawn_timer = 0.85

        for i, car in enumerate(self.cars):
            if not car.active:
                continue
            axis = 0 if car.lane < 2 else 1
            green = self.is_axis_green(axis)

            spd = car.speed
            if self.all_red_timer > 0.0 and 5.05 < car.prog < 10.0:
                spd *= 1.45

            next_prog = car.prog + spd * dt
            if not green and car.prog <= 5.05:
                next_prog = min(next_prog, 5.0)

            for j, other in enumerate(self.cars):
                if i == j or not other.active or other.lane != car.lane:
                    continue
                if other.prog > car.prog:
                    next_prog = min(next_prog, other.prog - 1.6)

            car.prog = max(car.prog, next_prog)

            if car.prog >= 15.6:
                car.active = False
                self.passed_cars += 1
                self._add_score(25)
                if self.passed_cars >= self.TARGET_CARS:
                    self._add_score(150)
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                    return

        for i, c1 in enumerate(self.cars):
            if not c1.active or c1.lane >= 2:
                continue
            x1, y1 = self.car_xy(c1)
            for j, c2 in enumerate(self.cars):
                if not c2.active or c2.lane < 2:
                    continue
                x2, y2 = self.car_xy(c2)
                if abs(x1 - x2) < 0.95 and abs(y1 - y2) < 0.95:
                    c1.active = False
                    c2.active = False
                    self._record_incident(int(round((x1 + x2) * 0.5)), int(round((y1 + y2) * 0.5)))
                    if self._state == STATE_GAMEOVER:
                        return
                    break

        for ln in range(4):
            axis = 0 if ln < 2 else 1
            green = self.is_axis_green(axis)
            waiting_cnt = 0
            edge_blocked = False
            front_car = None
            front_prog = -1.0

            for c in self.cars:
                if not c.active or c.lane != ln:
                    continue
                if c.prog <= 5.05:
                    waiting_cnt += 1
                    if c.prog <= 2.0:
                        edge_blocked = True
                    if c.prog > front_prog:
                        front_prog = c.prog
                        front_car = c

            if not green and waiting_cnt >= 3 and edge_blocked:
                self.lane_rage_timer[ln] += dt
                if self.lane_rage_timer[ln] > 3.5:
                    self.lane_rage_timer[ln] = 0.0
                    fx, fy = 7, 7
                    if front_car is not None:
                        cx, cy = self.car_xy(front_car)
                        fx, fy = int(round(cx)), int(round(cy))
                        front_car.active = False
                    self._record_incident(fx, fy)
                    if self._state == STATE_GAMEOVER:
                        return
            elif green or waiting_cnt < 2:
                self.lane_rage_timer[ln] = 0.0

        self.cars = [c for c in self.cars if c.active]

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)

        for y in range(16):
            for x in range(16):
                v_road = 6 <= x <= 9
                h_road = 6 <= y <= 9
                if v_road or h_road:
                    set_pixel(fb, x, y, 30, 32, 38)
                    if v_road and not h_road and (y % 3 == 1):
                        set_pixel(fb, 7, y, 75, 75, 55)
                    elif h_road and not v_road and (x % 3 == 1):
                        set_pixel(fb, x, 7, 75, 75, 55)
                else:
                    set_pixel(fb, x, y, 20, 42, 26)

        ns_green = self.is_axis_green(0)
        ew_green = self.is_axis_green(1)
        nsr, nsg, nsb = (30, 245, 70) if ns_green else (255, 35, 35)
        ewr, ewg, ewb = (30, 245, 70) if ew_green else (255, 35, 35)
        set_pixel(fb, 5, 5, nsr, nsg, nsb)
        set_pixel(fb, 10, 10, nsr, nsg, nsb)
        set_pixel(fb, 10, 5, ewr, ewg, ewb)
        set_pixel(fb, 5, 10, ewr, ewg, ewb)

        for c in self.cars:
            if not c.active:
                continue
            cx, cy = self.car_xy(c)
            col = CAR_PALETTE[c.color_id & 3]
            set_pixel(fb, int(round(cx)), int(round(cy)), col[0], col[1], col[2])

        if self.crash_flash_timer > 0.0:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    set_pixel(fb, self.crash_x + dx, self.crash_y + dy, 255, 95, 20)
            set_pixel(fb, self.crash_x, self.crash_y, 255, 240, 80)

        lives_rem = max(0, 3 - self.incidents)
        for i in range(3):
            if i < lives_rem:
                set_pixel(fb, i, 0, 45, 230, 95)
            else:
                set_pixel(fb, i, 0, 90, 25, 25)

        prog_pips = (self.passed_cars * 5) // self.TARGET_CARS
        for p in range(5):
            if p < prog_pips:
                set_pixel(fb, 11 + p, 0, 255, 215, 40)
            else:
                set_pixel(fb, 11 + p, 0, 45, 40, 15)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": max(0, 3 - self.incidents),
            "state": self._state,
            "progress": min(100, (self.passed_cars * 100) // self.TARGET_CARS),
        }
