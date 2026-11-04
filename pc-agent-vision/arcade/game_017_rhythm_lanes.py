# -*- coding: utf-8 -*-
"""game_017_rhythm_lanes.py —— 目标 #017 四轨节奏 (Rhythm Lanes)
统一节拍时钟驱动四轨彩色音符下落 + y=13..14 判定线精准打击 (Perfect/Good/Combo)
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_MULTI_TRACK,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

MAX_NOTES = 10
TOTAL_BEATS = 64
MAX_MISSES = 5

BEAT_INTERVAL = 0.40
NOTE_FALL_SPEED = 10.0
JUDGE_Y = 13.0
JUDGE_WINDOW = 1.8
PERFECT_WINDOW = 0.75

NOTE_COLORS = (
    (255, 70, 115),
    (0, 225, 255),
    (50, 240, 120),
    (255, 205, 35),
)


class RhythmNote:
    def __init__(self, lane: int = 0, y: float = 0.0, active: bool = False):
        self.lane = lane
        self.y = y
        self.active = active


class Game017RhythmLanes(BaseCartridge):
    difficulty_supported = True
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.notes: List[RhythmNote] = [RhythmNote() for _ in range(MAX_NOTES)]
        self.beat_timer = 0.0
        self.beats_spawned = 0
        self.notes_cleared = 0
        self.combo = 0
        self.misses = 0
        self.last_lane = 0
        self.lane_flash = [0.0, 0.0, 0.0, 0.0]
        self.lane_grade = [0, 0, 0, 0]
        self.miss_flash_timer = 0.0
        self._seed = 0x17201401
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 17

    @property
    def name(self) -> str:
        return "四轨节奏"

    @property
    def english_name(self) -> str:
        return "Rhythm Lanes"

    @property
    def release_year(self) -> int:
        return 2014

    @property
    def control_type(self) -> int:
        return CTRL_MULTI_TRACK

    @property
    def core_mechanic(self) -> str:
        return "四轨节拍同步音符下落与判定窗连击"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _spawn_beat_note(self) -> None:
        if self.beats_spawned >= TOTAL_BEATS:
            return
        slot = -1
        for i, n in enumerate(self.notes):
            if not n.active:
                slot = i
                break
        if slot < 0:
            return

        lane = self._next_rand() % 4
        if lane == self.last_lane and (self._next_rand() % 3) != 0:
            lane = (lane + 1 + (self._next_rand() % 3)) % 4
        self.last_lane = lane
        if self._state==STATE_PLAYING:self.emit_sound("beat",lane)

        self.notes[slot].lane = lane
        self.notes[slot].y = 0.0
        self.notes[slot].active = True
        self.beats_spawned += 1

    def _any_active_notes(self) -> bool:
        return any(n.active for n in self.notes)

    def _handle_lane_press(self, lane: int) -> None:
        best_idx = -1
        best_dist = 999.0
        for i, n in enumerate(self.notes):
            if not n.active or n.lane != lane:
                continue
            dist = abs(n.y - JUDGE_Y)
            if dist <= (2.0,1.8,1.4)[self.difficulty] and dist < best_dist:
                best_dist = dist
                best_idx = i

        if best_idx >= 0:
            self.notes[best_idx].active = False
            self.notes_cleared += 1
            self.emit_sound("hit",lane)
            capped_combo = min(self.combo, 10)
            if best_dist <= PERFECT_WINDOW:
                self._add_score(20 + capped_combo * 2)
                self.lane_grade[lane] = 2
                self.lane_flash[lane] = 0.22
            else:
                self._add_score(10 + capped_combo)
                self.lane_grade[lane] = 1
                self.lane_flash[lane] = 0.18
            self.combo += 1
        else:
            self.combo = 0
            self.misses += 1
            self.miss_flash_timer = 0.20
            if self.misses >= (10,8,5)[self.difficulty]:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.notes = [RhythmNote() for _ in range(MAX_NOTES)]
        self.beat_timer = 0.0
        self.beats_spawned = 0
        self.notes_cleared = 0
        self.combo = 0
        self.misses = 0
        self.last_lane = 0
        self.lane_flash = [0.0, 0.0, 0.0, 0.0]
        self.lane_grade = [0, 0, 0, 0]
        self.miss_flash_timer = 0.0
        self._score = 0
        self._seed = 0x17201401
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._spawn_beat_note()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.notes = [RhythmNote() for _ in range(MAX_NOTES)]
            self.beat_timer = 0.0
            self.beats_spawned = 0
            self.notes_cleared = 0
            self.combo = 0
            self.misses = 0
            self.last_lane = 0
            self.lane_flash = [0.0, 0.0, 0.0, 0.0]
            self.lane_grade = [0, 0, 0, 0]
            self.miss_flash_timer = 0.0
            self._score = 0
            self._seed = 0x17201401
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._spawn_beat_note()

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt < 0.0:
            dt = 0.0
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (
                keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_DOWN | KEY_UP | KEY_RIGHT)
            ):
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

            for t in range(4):
                if self.lane_flash[t] > 0.0:
                    self.lane_flash[t] -= dt
                    if self.lane_flash[t] <= 0.0:
                        self.lane_flash[t] = 0.0
                        self.lane_grade[t] = 0
            if self.miss_flash_timer > 0.0:
                self.miss_flash_timer = max(0.0, self.miss_flash_timer - dt)

            if keys_pressed & KEY_LEFT:
                self._handle_lane_press(0)
                if self._state != STATE_PLAYING:
                    return
            if keys_pressed & KEY_DOWN:
                self._handle_lane_press(1)
                if self._state != STATE_PLAYING:
                    return
            if keys_pressed & KEY_UP:
                self._handle_lane_press(2)
                if self._state != STATE_PLAYING:
                    return
            if keys_pressed & KEY_RIGHT:
                self._handle_lane_press(3)
                if self._state != STATE_PLAYING:
                    return

            for n in self.notes:
                if not n.active:
                    continue
                n.y += (JUDGE_Y/(3*(.50,.40,.32)[self.difficulty])) * dt
                if n.y > 15.2:
                    n.active = False
                    self.combo = 0
                    self.misses += 1
                    self.miss_flash_timer = 0.20
                    if self.misses >= (10,8,5)[self.difficulty]:
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

            self.beat_timer += dt
            while self.beat_timer >= (.50,.40,.32)[self.difficulty]:
                self.beat_timer -= (.50,.40,.32)[self.difficulty]
                if self.beats_spawned < TOTAL_BEATS:self._spawn_beat_note()
                else:self.emit_sound("beat",self.last_lane)
            if self.beats_spawned >= TOTAL_BEATS and not self._any_active_notes():
                self._state = STATE_VICTORY
                self.state_timer = 0.0
                return

    @staticmethod
    def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < 16 and 0 <= y < 16:
            idx = (y * 16 + x) * 3
            fb[idx] = r
            fb[idx + 1] = g
            fb[idx + 2] = b

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)
        for y in range(16):
            for x in range(16):
                if x in (3, 7, 11, 15):
                    self._set_px(fb, x, y, 36, 42, 65)
                else:
                    self._set_px(fb, x, y, 10, 12, 24)

        for x in range(16):
            if x in (3, 7, 11, 15):
                continue
            if self.miss_flash_timer > 0.0:
                self._set_px(fb, x, 13, 240, 45, 45)
                self._set_px(fb, x, 14, 120, 20, 20)
            else:
                self._set_px(fb, x, 13, 220, 220, 245)
                self._set_px(fb, x, 14, 70, 75, 110)

        for n in self.notes:
            if not n.active:
                continue
            lane = n.lane
            x0 = lane * 4
            ny = int(round(n.y))
            cr, cg, cb = NOTE_COLORS[lane]
            for dx in range(3):
                self._set_px(fb, x0 + dx, ny, cr, cg, cb)
                self._set_px(fb, x0 + dx, ny - 1, cr // 2, cg // 2, cb // 2)

        for t in range(4):
            if self.lane_flash[t] > 0.0:
                x0 = t * 4
                fr, fg, fb_c = (255, 255, 140) if self.lane_grade[t] == 2 else (90, 255, 180)
                for y in range(12, 15):
                    for dx in range(3):
                        self._set_px(fb, x0 + dx, y, fr, fg, fb_c)

        hp = (10,8,5)[self.difficulty] - self.misses
        for i in range(min(max(0, hp), (10,8,5)[self.difficulty])):
            self._set_px(fb, i * 15 // ((10,8,5)[self.difficulty] - 1), 0, 80, 230, 140)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        hp = (10,8,5)[self.difficulty] - self.misses
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": hp if (hp > 0 and self._state != STATE_GAMEOVER) else 0,
            "state": self._state,
            "progress": min(100, (self.beats_spawned * 100) // TOTAL_BEATS),
        }
