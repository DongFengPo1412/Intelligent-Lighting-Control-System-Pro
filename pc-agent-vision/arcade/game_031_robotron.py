# -*- coding: utf-8 -*-
"""game_031_robotron.py —— 目标 #031 双向射击 (Robotron 2084, 1982)
与 ESP32-S3 C++ Game031Robotron 1:1 对齐实现
"""

import math
from typing import Dict, Any, List
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
    KEY_SELECT,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

AIM_DX = (
    0.0, 0.70710678, 1.0, 0.70710678,
    0.0, -0.70710678, -1.0, -0.70710678,
)
AIM_DY = (
    -1.0, -0.70710678, 0.0, 0.70710678,
    1.0, 0.70710678, 0.0, -0.70710678,
)


def _vec_to_dir8(ix: int, iy: int) -> int:
    if ix == 0 and iy < 0:
        return 0
    if ix > 0 and iy < 0:
        return 1
    if ix > 0 and iy == 0:
        return 2
    if ix > 0 and iy > 0:
        return 3
    if ix == 0 and iy > 0:
        return 4
    if ix < 0 and iy > 0:
        return 5
    if ix < 0 and iy == 0:
        return 6
    if ix < 0 and iy < 0:
        return 7
    return 0


class RobotGrunt031:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.speed = 1.85


class HumanSurvivor031:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0


class ArenaLaser031:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.life = 0.0


class Game031Robotron(BaseCartridge):
    MAX_ROBOTS = 12
    MAX_HUMANS = 3
    MAX_LASERS = 6

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.lives = 3
        self.wave = 1
        self.px = 7.5
        self.py = 7.5
        self.aim_dir = 2
        self.aim_locked = False
        self.fire_cooldown = 0.0
        self.invuln_timer = 0.0
        self.robots: List[RobotGrunt031] = [RobotGrunt031() for _ in range(self.MAX_ROBOTS)]
        self.humans: List[HumanSurvivor031] = [HumanSurvivor031() for _ in range(self.MAX_HUMANS)]
        self.lasers: List[ArenaLaser031] = [ArenaLaser031() for _ in range(self.MAX_LASERS)]
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x0312084A
        self.reset()

    @property
    def game_id(self) -> int:
        return 31

    @property
    def name(self) -> str:
        return "双向射击"

    @property
    def english_name(self) -> str:
        return "Robotron 2084"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "8向走位与独立锁定瞄准双向射击突围救人"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def count_active_robots(self) -> int:
        return sum(1 for r in self.robots if r.active)

    def _init_wave(self) -> None:
        self.px = 7.5
        self.py = 7.5
        self.invuln_timer = 1.0
        for l in self.lasers:
            l.active = False

        human_init = (
            (3.5, 4.0, 1.1, 0.8),
            (11.5, 4.0, -1.0, 0.9),
            (7.5, 12.0, 0.9, -1.0),
        )
        for h_idx, h in enumerate(self.humans):
            h.active = True
            h.x, h.y, h.vx, h.vy = human_init[h_idx]

        count = min(self.MAX_ROBOTS, 6 + self.wave * 2)
        base_spd = 1.85 + (self.wave - 1) * 0.35
        perim = (
            (1.2, 1.2), (13.8, 1.2), (1.2, 13.8), (13.8, 13.8),
            (7.5, 1.2), (7.5, 13.8), (1.2, 7.5), (13.8, 7.5),
            (4.0, 1.2), (11.0, 1.2), (4.0, 13.8), (11.0, 13.8),
        )
        for i, rob in enumerate(self.robots):
            if i < count:
                r = self._next_rand()
                rob.active = True
                rob.x, rob.y = perim[i]
                rob.speed = base_spd + (r % 4) * 0.1
            else:
                rob.active = False

    def _setup_new_game(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.lives = 3
        self.wave = 1
        self.aim_dir = 2
        self.aim_locked = False
        self.fire_cooldown = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x0312084A
        self._init_wave()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._setup_new_game(STATE_TITLE)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_new_game(STATE_PLAYING)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _fire_laser(self) -> None:
        if self.fire_cooldown > 0.0:
            return
        for l in self.lasers:
            if not l.active:
                dx = AIM_DX[self.aim_dir]
                dy = AIM_DY[self.aim_dir]
                l.active = True
                l.x = self.px + dx * 0.6
                l.y = self.py + dy * 0.6
                l.vx = dx * 18.0
                l.vy = dy * 18.0
                l.life = 0.85
                self.fire_cooldown = 0.14
                return

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt < 0.0:
            dt = 0.0
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.aim_dir = int(self.anim_timer * 4.0) & 7
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
                self.start()
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            if self.fire_cooldown > 0.0:
                self.fire_cooldown -= dt
            if self.invuln_timer > 0.0:
                self.invuln_timer -= dt

            if keys_pressed & KEY_B:
                if not self.aim_locked:
                    self.aim_locked = True
                else:
                    self.aim_dir = (self.aim_dir + 1) & 7
            if keys_pressed & KEY_SELECT:
                self.aim_locked = False

            move_ix = 0
            move_iy = 0
            if keys_down & KEY_LEFT:
                move_ix -= 1
            if keys_down & KEY_RIGHT:
                move_ix += 1
            if keys_down & KEY_UP:
                move_iy -= 1
            if keys_down & KEY_DOWN:
                move_iy += 1

            if move_ix != 0 or move_iy != 0:
                if not self.aim_locked:
                    self.aim_dir = _vec_to_dir8(move_ix, move_iy)
                length = math.hypot(move_ix, move_iy)
                move_speed = 6.2
                self.px = max(1.0, min(14.0, self.px + (move_ix / length) * move_speed * dt))
                self.py = max(1.0, min(14.0, self.py + (move_iy / length) * move_speed * dt))

            if (keys_pressed & KEY_A) or (keys_down & KEY_A):
                self._fire_laser()

            for h in self.humans:
                if not h.active:
                    continue
                h.x += h.vx * dt
                h.y += h.vy * dt
                if h.x <= 1.2 or h.x >= 13.8:
                    h.vx = -h.vx
                if h.y <= 1.2 or h.y >= 13.8:
                    h.vy = -h.vy
                if math.hypot(h.x - self.px, h.y - self.py) <= 0.95:
                    h.active = False
                    self._add_score(100)

            for l in self.lasers:
                if not l.active:
                    continue
                l.x += l.vx * dt
                l.y += l.vy * dt
                l.life -= dt
                if l.life <= 0.0 or l.x < 0.5 or l.x > 14.5 or l.y < 0.5 or l.y > 14.5:
                    l.active = False
                    continue

                for rob in self.robots:
                    if rob.active and math.hypot(rob.x - l.x, rob.y - l.y) <= 0.85:
                        rob.active = False
                        l.active = False
                        self._add_score(50)
                        break

            for rob in self.robots:
                if not rob.active:
                    continue
                dx = self.px - rob.x
                dy = self.py - rob.y
                dist = math.hypot(dx, dy)
                if dist > 0.05:
                    rob.x += (dx / dist) * rob.speed * dt
                    rob.y += (dy / dist) * rob.speed * dt

                if self.invuln_timer <= 0.0 and dist <= 0.72:
                    if self.lives > 1:
                        self.lives -= 1
                        self.px = 7.5
                        self.py = 7.5
                        self.invuln_timer = 1.4
                        for krob in self.robots:
                            if not krob.active:
                                continue
                            kdx = krob.x - 7.5
                            kdy = krob.y - 7.5
                            kd = math.hypot(kdx, kdy)
                            if kd < 4.0:
                                if kd < 0.1:
                                    kdx, kdy, kd = 1.0, 0.0, 1.0
                                krob.x = max(1.2, min(13.8, 7.5 + (kdx / kd) * 5.0))
                                krob.y = max(1.2, min(13.8, 7.5 + (kdy / kd) * 5.0))
                    else:
                        self.lives = 0
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                    break

            if self.count_active_robots() == 0:
                self._add_score(200)
                if self.wave >= 3:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                else:
                    self.wave += 1
                    self._init_wave()

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)

        def set_px(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        for y in range(16):
            for x in range(16):
                if x in (0, 15) or y in (0, 15):
                    set_px(x, y, 90, 20, 175)
                else:
                    set_px(x, y, 5, 5, 12)

        for h in self.humans:
            if h.active:
                set_px(int(round(h.x)), int(round(h.y)), 46, 235, 150)

        for rob in self.robots:
            if rob.active:
                set_px(int(round(rob.x)), int(round(rob.y)), 245, 50, 45)

        for l in self.lasers:
            if l.active:
                set_px(int(round(l.x)), int(round(l.y)), 255, 245, 80)

        blink_hide = (self.invuln_timer > 0.0) and ((int(self.anim_timer * 12.0) & 1) == 1)
        if not blink_hide and self._state != STATE_GAMEOVER:
            ix = int(round(self.px))
            iy = int(round(self.py))
            ax = int(round(self.px + AIM_DX[self.aim_dir]))
            ay = int(round(self.py + AIM_DY[self.aim_dir]))
            if self.aim_locked:
                set_px(ax, ay, 255, 165, 0)
            else:
                set_px(ax, ay, 0, 200, 255)
            set_px(ix, iy, 255, 255, 255)

        for i in range(min(3, self.lives)):
            set_px(1 + i * 2, 0, 0, 240, 255)
        for w in range(min(3, self.wave)):
            set_px(14 - w * 2, 0, 255, 215, 0)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                set_px(x, 0, 231, 76, 60)
        elif self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_px(6, y, 250, 250, 250)
                set_px(9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": 100 if self._state == STATE_VICTORY else (self.wave - 1) * 33,
        }
