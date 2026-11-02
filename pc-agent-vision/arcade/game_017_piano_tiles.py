# -*- coding: utf-8 -*-
"""
game_017_piano_tiles.py —— 别踩白块儿 2014 (Piano Tiles 2014)
编号: #017
年代: 2014 (猎豹移动 Cheetah Mobile)
核心独占机制: 四轨乐符离散下落 + 底线节拍判定打击 + 踩白即死 + 漏击判负
手柄类型: CTRL_MULTI_TRACK (四轨多键打击: LEFT, DOWN, UP, RIGHT)
"""

import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    CTRL_MULTI_TRACK,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

class PianoNote:
    def __init__(self, track: int, y: float):
        self.active = True
        self.track = track
        self.y = y
        self.height = 3.0
        self.hit = False

class Game017PianoTiles(BaseCartridge):
    def __init__(self):
        self._id = 17
        self._name = "别踩白块儿"
        self._english_name = "Piano Tiles 2014"
        self._year = 2014
        self._control_type = CTRL_MULTI_TRACK
        self._core_mechanic = "四轨乐符离散下落 + 底线节拍判定打击 + 踩白即死 + 漏击判负"

        self.k_max_notes = 6
        self.k_target_hits = 40

        self.state = STATE_TITLE
        self.fall_speed = 10.0
        self.combo = 0
        self.total_hits = 0
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0
        self.spawn_timer = 0.0
        self.hit_flash_timer = [0.0] * 4

        self.notes: List[PianoNote] = []
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

    def spawn_next_note(self):
        active_cnt = sum(1 for n in self.notes if n.active)
        if active_cnt >= self.k_max_notes:
            return
        track = random.randint(0, 3)
        self.notes.append(PianoNote(track, -3.5))

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.combo = 0
        self.total_hits = 0
        self.fall_speed = 10.0
        self.state_timer = 0.0
        self.spawn_timer = 0.0
        self.hit_flash_timer = [0.0] * 4
        self.notes = []

        self.spawn_next_note()

    def handle_track_hit(self, track: int):
        candidate = None
        lowest_y = -999.0
        for n in self.notes:
            if n.active and not n.hit and n.track == track:
                if n.y > lowest_y:
                    lowest_y = n.y
                    candidate = n

        if candidate is not None:
            if (candidate.y + candidate.height) >= 10.5 and candidate.y <= 15.5:
                candidate.hit = True
                candidate.active = False
                self.combo += 1
                self.total_hits += 1
                self.hit_flash_timer[track] = 0.2

                self.score += 25 * self.combo
                if self.score > self.high_score:
                    self.high_score = self.score

                if self.fall_speed < 24.0:
                    self.fall_speed += 0.35

                if self.total_hits >= self.k_target_hits:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                return

        # 踩白块猝死
        self.state = STATE_GAMEOVER
        self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)):
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

            for t in range(4):
                if self.hit_flash_timer[t] > 0.0:
                    self.hit_flash_timer[t] -= dt

            if keys_pressed & KEY_LEFT:
                self.handle_track_hit(0)
                if self.state != STATE_PLAYING: return
            if keys_pressed & KEY_DOWN:
                self.handle_track_hit(1)
                if self.state != STATE_PLAYING: return
            if keys_pressed & KEY_UP:
                self.handle_track_hit(2)
                if self.state != STATE_PLAYING: return
            if keys_pressed & KEY_RIGHT:
                self.handle_track_hit(3)
                if self.state != STATE_PLAYING: return

            for n in self.notes:
                if n.active and not n.hit:
                    n.y += self.fall_speed * dt
                    if n.y > 15.2:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

            self.notes = [n for n in self.notes if n.active]

            self.spawn_timer += dt
            spawn_interval = 4.8 / self.fall_speed
            if self.spawn_timer >= spawn_interval:
                self.spawn_timer = 0.0
                self.spawn_next_note()

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if x in (3, 7, 11):
                    self.frame_buffer[idx:idx+3] = bytes([189, 195, 199])
                else:
                    self.frame_buffer[idx:idx+3] = bytes([236, 240, 241])

        for n in self.notes:
            if n.active and not n.hit:
                track_x = n.track * 4
                y_start = int(n.y)
                y_end = int(n.y + n.height)
                for y in range(y_start, y_end):
                    if 0 <= y < 16:
                        for dx in range(3):
                            x = track_x + dx
                            if 0 <= x < 16:
                                idx = (y * 16 + x) * 3
                                self.frame_buffer[idx:idx+3] = bytes([24, 44, 97])

        for x in range(16):
            idx = (13 * 16 + x) * 3
            self.frame_buffer[idx:idx+3] = bytes([241, 196, 15])

        for t in range(4):
            if self.hit_flash_timer[t] > 0.0:
                tx = t * 4
                for y in range(12, 15):
                    for dx in range(3):
                        x = tx + dx
                        idx = (y * 16 + x) * 3
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
            "combo": self.combo,
            "total_hits": self.total_hits,
            "state": self.state,
            "progress": int((self.total_hits * 100) / self.k_target_hits),
        }
