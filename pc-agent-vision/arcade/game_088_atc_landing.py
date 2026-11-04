# -*- coding: utf-8 -*-
"""game_088_atc_landing.py —— 目标 #088 机场降落引导 (Flight Control)
机制: 中央水平跑道(x=5..11, y=8)向东五边进近 + 多机航向引导 + 防相撞与燃油告警
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
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen, set_pixel

ATC_DIR_RIGHT = 0
ATC_DIR_DOWN = 1
ATC_DIR_LEFT = 2
ATC_DIR_UP = 3

ATC_DIR_VEC = (
    (1, 0),
    (0, 1),
    (-1, 0),
    (0, -1),
)

PLANE_COLORS = (
    (0, 225, 255),
    (255, 195, 35),
    (215, 105, 255),
    (80, 250, 140),
)

ENTRY_POINTS = (
    (1.0, 3.0, ATC_DIR_RIGHT),
    (14.0, 3.0, ATC_DIR_LEFT),
    (1.0, 13.0, ATC_DIR_RIGHT),
    (14.0, 13.0, ATC_DIR_LEFT),
    (3.0, 1.5, ATC_DIR_DOWN),
    (12.0, 1.5, ATC_DIR_DOWN),
    (3.0, 14.5, ATC_DIR_UP),
    (12.0, 14.5, ATC_DIR_UP),
)


class AtcPlane:
    def __init__(self, slot: int):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.dir = ATC_DIR_RIGHT
        self.speed = 1.9
        self.fuel = 30.0
        self.color_id = slot


class Game088AtcLanding(BaseCartridge):
    MAX_PLANES = 4
    TARGET_LANDINGS = 10

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.selected_plane = 0
        self.landed_count = 0
        self.spawn_timer = 2.4
        self.landing_flash_timer = 0.0
        self.rng_seed = 0x2009088B
        self.planes: List[AtcPlane] = [AtcPlane(i) for i in range(self.MAX_PLANES)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 88

    @property
    def name(self) -> str:
        return "机场降落引导"

    @property
    def english_name(self) -> str:
        return "Flight Control"

    @property
    def release_year(self) -> int:
        return 2009

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多机航向矢量调度与向东五边对准跑道降落"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _ensure_valid_selection(self) -> None:
        if 0 <= self.selected_plane < self.MAX_PLANES and self.planes[self.selected_plane].active:
            return
        for i, p in enumerate(self.planes):
            if p.active:
                self.selected_plane = i
                return
        self.selected_plane = 0

    def spawn_plane(self) -> None:
        slot = -1
        for i, p in enumerate(self.planes):
            if not p.active:
                slot = i
                break
        if slot < 0:
            return

        self.rng_seed = (self.rng_seed * 1103515245 + 12345) & 0xFFFFFFFF
        start_k = (self.rng_seed >> 16) % 8

        for attempt in range(8):
            k = (start_k + attempt) % 8
            sx, sy, sdir = ENTRY_POINTS[k]
            safe = True
            for p in self.planes:
                if p.active and (p.x - sx) ** 2 + (p.y - sy) ** 2 < 4.2 * 4.2:
                    safe = False
                    break
            if safe:
                pl = self.planes[slot]
                pl.active = True
                pl.x = sx
                pl.y = sy
                pl.dir = sdir
                pl.speed = 1.9
                pl.fuel = 30.0
                pl.color_id = slot
                self._ensure_valid_selection()
                return

    def _setup_match(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.selected_plane = 0
        self.landed_count = 0
        self.spawn_timer = 2.4
        self.landing_flash_timer = 0.0
        self.rng_seed = 0x2009088B
        self.planes = [AtcPlane(i) for i in range(self.MAX_PLANES)]
        self.spawn_plane()

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

    def _set_selected_heading(self, new_dir: int) -> None:
        self._ensure_valid_selection()
        pl = self.planes[self.selected_plane]
        if pl.active:
            pl.dir = new_dir
            if new_dir == ATC_DIR_RIGHT and abs(pl.y - 8.0) <= 0.6:
                pl.y = 8.0

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

        if self.landing_flash_timer > 0.0:
            self.landing_flash_timer -= dt

        self._ensure_valid_selection()

        if keys_pressed & KEY_B:
            for step in range(1, self.MAX_PLANES + 1):
                cand = (self.selected_plane + step) % self.MAX_PLANES
                if self.planes[cand].active:
                    self.selected_plane = cand
                    break

        if keys_pressed & KEY_RIGHT:
            self._set_selected_heading(ATC_DIR_RIGHT)
        elif keys_pressed & KEY_DOWN:
            self._set_selected_heading(ATC_DIR_DOWN)
        elif keys_pressed & KEY_LEFT:
            self._set_selected_heading(ATC_DIR_LEFT)
        elif keys_pressed & KEY_UP:
            self._set_selected_heading(ATC_DIR_UP)
        elif keys_pressed & KEY_A:
            self._ensure_valid_selection()
            if self.planes[self.selected_plane].active:
                self._set_selected_heading((self.planes[self.selected_plane].dir + 1) % 4)

        active_cnt = sum(1 for p in self.planes if p.active)
        self.spawn_timer -= dt
        if (active_cnt == 0 and self.landed_count < self.TARGET_LANDINGS) or (
            self.spawn_timer <= 0.0 and active_cnt < self.MAX_PLANES
        ):
            self.spawn_plane()
            self.spawn_timer = 3.6

        for p in self.planes:
            if not p.active:
                continue
            p.fuel -= dt
            if p.fuel <= 0.0:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

            p.x += ATC_DIR_VEC[p.dir][0] * p.speed * dt
            p.y += ATC_DIR_VEC[p.dir][1] * p.speed * dt

            if p.x < 0.6 and p.dir == ATC_DIR_LEFT:
                p.x = 0.6
                p.dir = ATC_DIR_RIGHT
            elif p.x > 14.6 and p.dir == ATC_DIR_RIGHT:
                p.x = 14.6
                p.dir = ATC_DIR_LEFT
            if p.y < 1.4 and p.dir == ATC_DIR_UP:
                p.y = 1.4
                p.dir = ATC_DIR_DOWN
            elif p.y > 14.6 and p.dir == ATC_DIR_DOWN:
                p.y = 14.6
                p.dir = ATC_DIR_UP

            if p.dir == ATC_DIR_RIGHT and abs(p.x - 5.0) <= 0.65 and abs(p.y - 8.0) <= 0.65:
                p.active = False
                self.landed_count += 1
                self.landing_flash_timer = 0.35
                self._add_score(100)
                self._ensure_valid_selection()
                if self.landed_count >= self.TARGET_LANDINGS:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                    return

        for i in range(self.MAX_PLANES):
            if not self.planes[i].active:
                continue
            for j in range(i + 1, self.MAX_PLANES):
                if not self.planes[j].active:
                    continue
                if math.hypot(self.planes[i].x - self.planes[j].x, self.planes[i].y - self.planes[j].y) < 1.3:
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)

        for y in range(16):
            for x in range(16):
                if y == 0:
                    set_pixel(fb, x, y, 8, 12, 18)
                elif x == 8 or y == 8:
                    set_pixel(fb, x, y, 12, 34, 28)
                else:
                    set_pixel(fb, x, y, 8, 22, 20)

        beacon_on = (int(self.anim_timer * 5.0) % 2) == 0
        set_pixel(fb, 3, 8, 15, 140 if beacon_on else 65, 50)
        set_pixel(fb, 4, 8, 20, 190 if beacon_on else 85, 65)

        for x in range(5, 12):
            if self.landing_flash_timer > 0.0:
                set_pixel(fb, x, 8, 60, 255, 130)
            elif x == 5:
                set_pixel(fb, x, 8, 40, 245, 95)
            elif (x & 1) == 1:
                set_pixel(fb, x, 8, 180, 190, 200)
            else:
                set_pixel(fb, x, 8, 70, 75, 85)

        fast_blink = (int(self.anim_timer * 10.0) % 2) == 0
        for i, p in enumerate(self.planes):
            if not p.active:
                continue
            px, py = int(round(p.x)), int(round(p.y))
            nx = px + ATC_DIR_VEC[p.dir][0]
            ny = py + ATC_DIR_VEC[p.dir][1]
            if i == self.selected_plane:
                set_pixel(fb, nx, ny, 255, 255, 255)
            else:
                set_pixel(fb, nx, ny, 90, 140, 150)

            if p.fuel < 7.0 and fast_blink:
                set_pixel(fb, px, py, 255, 35, 35)
            elif i == self.selected_plane and not fast_blink:
                set_pixel(fb, px, py, 255, 255, 255)
            else:
                col = PLANE_COLORS[p.color_id & 3]
                set_pixel(fb, px, py, col[0], col[1], col[2])

        for k in range(self.TARGET_LANDINGS):
            if k < self.landed_count:
                set_pixel(fb, k, 0, 45, 240, 105)
            else:
                set_pixel(fb, k, 0, 20, 45, 30)

        if 0 <= self.selected_plane < self.MAX_PLANES and self.planes[self.selected_plane].active:
            fpips = max(0, min(4, int(math.ceil((self.planes[self.selected_plane].fuel / 30.0) * 4.0))))
            for f in range(fpips):
                if fpips <= 1:
                    set_pixel(fb, 12 + f, 0, 255, 50, 50)
                else:
                    set_pixel(fb, 12 + f, 0, 255, 205, 40)

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
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (self.landed_count * 100) // self.TARGET_LANDINGS),
        }
