# -*- coding: utf-8 -*-
"""game_029_centipede.py —— 目标 #029 百足蜈蚣 (Centipede, 1980)
与 ESP32-S3 C++ Game029Centipede 1:1 对齐实现
"""

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
from .arcade_result_screen import ArcadeResultScreen


class CentipedeSeg029:
    def __init__(self):
        self.active = False
        self.is_head = False
        self.ahead = -1
        self.x = 0
        self.y = 1
        self.dir_x = 1
        self.dir_y = 1


class BugBolt029:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0


class Game029Centipede(BaseCartridge):
    MAX_SEGMENTS = 8
    MAX_BULLETS = 3

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.lives = 3
        self.wave = 1
        self.player_x = 8.0
        self.player_y = 14.0
        self.fire_cooldown = 0.0
        self.invuln_timer = 0.0
        self.step_timer = 0.0
        self.step_interval = 0.15
        self.mushrooms: List[List[int]] = [[0] * 16 for _ in range(16)]
        self.segments: List[CentipedeSeg029] = [CentipedeSeg029() for _ in range(self.MAX_SEGMENTS)]
        self.bullets: List[BugBolt029] = [BugBolt029() for _ in range(self.MAX_BULLETS)]
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x029CE171
        self.reset()

    @property
    def game_id(self) -> int:
        return 29

    @property
    def name(self) -> str:
        return "百足蜈蚣"

    @property
    def english_name(self) -> str:
        return "Centipede"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多节蜈蚣触障折返下移与击中中间节变蘑菇分裂双链"

    def _next_rand(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def count_active_segments(self) -> int:
        return sum(1 for s in self.segments if s.active)

    def count_chains(self) -> int:
        return sum(1 for s in self.segments if s.active and s.is_head)

    def _init_mushrooms(self) -> None:
        self.mushrooms = [[0] * 16 for _ in range(16)]
        fixed = (
            (3, 3), (11, 3), (6, 5), (13, 5), (2, 7),
            (9, 7), (5, 9), (12, 9), (4, 11), (10, 11),
        )
        for mx, my in fixed:
            self.mushrooms[my][mx] = 2
        for _ in range(3):
            mx = 1 + (self._next_rand() % 14)
            my = 3 + (self._next_rand() % 9)
            self.mushrooms[my][mx] = 2

    def _spawn_centipede_wave(self) -> None:
        for b in self.bullets:
            b.active = False

        seg_count = 7 if self.wave == 1 else 8
        self.step_interval = max(0.09, 0.15 - (self.wave - 1) * 0.02)
        self.step_timer = 0.0

        for i in range(self.MAX_SEGMENTS):
            s = self.segments[i]
            if i < seg_count:
                s.active = True
                s.is_head = (i == 0)
                s.ahead = -1 if i == 0 else (i - 1)
                s.x = seg_count - i
                s.y = 1
                s.dir_x = 1
                s.dir_y = 1
            else:
                s.active = False
                s.is_head = False
                s.ahead = -1

    def _setup_new_game(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.lives = 3
        self.wave = 1
        self.player_x = 8.0
        self.player_y = 14.0
        self.fire_cooldown = 0.0
        self.invuln_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._seed = 0x029CE171
        self._init_mushrooms()
        self._spawn_centipede_wave()

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

    def _step_centipede(self) -> None:
        old_state = [(s.x, s.y, s.dir_x, s.dir_y) for s in self.segments]

        for i, s in enumerate(self.segments):
            if not s.active:
                continue
            leader = s.ahead
            if s.is_head or leader < 0 or not self.segments[leader].active:
                s.is_head = True
                s.ahead = -1
                nx = s.x + s.dir_x
                cy = s.y
                blocked = (nx < 0 or nx > 15) or (0 <= cy < 16 and self.mushrooms[cy][nx] > 0)
                if blocked:
                    ny = cy + s.dir_y
                    if ny > 15:
                        s.dir_y = -1
                        ny = 14
                    elif ny < 12 and s.dir_y < 0:
                        s.dir_y = 1
                        ny = 13
                    s.y = ny
                    s.dir_x = -s.dir_x
                else:
                    s.x = nx
            else:
                s.x, s.y, s.dir_x, s.dir_y = old_state[leader]

    def _hit_segment(self, idx: int) -> None:
        if idx < 0 or idx >= self.MAX_SEGMENTS or not self.segments[idx].active:
            return
        seg = self.segments[idx]
        sx, sy = seg.x, seg.y
        was_head = seg.is_head
        seg.active = False

        if 0 <= sx < 16 and 0 <= sy < 16:
            self.mushrooms[sy][sx] = 2

        for j in range(self.MAX_SEGMENTS):
            if self.segments[j].active and self.segments[j].ahead == idx:
                self.segments[j].ahead = -1
                self.segments[j].is_head = True

        self._add_score(100 if was_head else 25)

        if self.count_active_segments() == 0:
            self._add_score(200)
            if self.wave >= 3:
                self._state = STATE_VICTORY
                self.state_timer = 0.0
            else:
                self.wave += 1
                self._spawn_centipede_wave()

    def _fire_bolt(self) -> None:
        if self.fire_cooldown > 0.0:
            return
        for b in self.bullets:
            if not b.active:
                b.active = True
                b.x = self.player_x
                b.y = self.player_y - 0.6
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
            self.step_timer += dt
            if self.step_timer >= 0.22:
                self.step_timer -= 0.22
                self._step_centipede()
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

            speed = 10.0
            nx = self.player_x
            ny = self.player_y
            if keys_down & KEY_LEFT:
                nx -= speed * dt
            if keys_down & KEY_RIGHT:
                nx += speed * dt
            if keys_down & KEY_UP:
                ny -= speed * dt
            if keys_down & KEY_DOWN:
                ny += speed * dt

            nx = max(0.0, min(15.0, nx))
            ny = max(13.0, min(15.0, ny))
            gx = int(round(nx))
            gy = int(round(ny))
            if self.mushrooms[gy][gx] == 0:
                self.player_x = nx
                self.player_y = ny

            if (keys_pressed & (KEY_A | KEY_B)) or (keys_down & (KEY_A | KEY_B)):
                self._fire_bolt()

            bolt_speed = 24.0
            for b in self.bullets:
                if not b.active:
                    continue
                b.y -= bolt_speed * dt
                if b.y < 0.0:
                    b.active = False
                    continue

                hit = False
                for idx, s in enumerate(self.segments):
                    if not s.active:
                        continue
                    if abs(b.x - s.x) <= 0.65 and abs(b.y - s.y) <= 0.65:
                        b.active = False
                        self._hit_segment(idx)
                        hit = True
                        break
                if hit or self._state != STATE_PLAYING:
                    if self._state != STATE_PLAYING:
                        return
                    continue

                bx = int(round(b.x))
                by = int(round(b.y))
                if 0 <= bx < 16 and 0 <= by < 16 and self.mushrooms[by][bx] > 0:
                    b.active = False
                    self.mushrooms[by][bx] -= 1
                    if self.mushrooms[by][bx] == 0:
                        self._add_score(5)

            self.step_timer += dt
            while self.step_timer >= self.step_interval:
                self.step_timer -= self.step_interval
                self._step_centipede()

            if self.invuln_timer <= 0.0:
                for s in self.segments:
                    if not s.active:
                        continue
                    if abs(self.player_x - s.x) <= 0.75 and abs(self.player_y - s.y) <= 0.75:
                        if self.lives > 1:
                            self.lives -= 1
                            self.player_x = 8.0
                            self.player_y = 15.0
                            self.invuln_timer = 1.5
                        else:
                            self.lives = 0
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        break

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
                set_px(x, y, 4, 8, 6)

        for y in range(16):
            for x in range(16):
                if self.mushrooms[y][x] == 2:
                    set_px(x, y, 210, 60, 180)
                elif self.mushrooms[y][x] == 1:
                    set_px(x, y, 120, 45, 110)

        for s in reversed(self.segments):
            if not s.active:
                continue
            if s.is_head:
                set_px(s.x, s.y, 255, 85, 45)
            else:
                set_px(s.x, s.y, 46, 215, 105)

        for b in self.bullets:
            if b.active:
                set_px(int(round(b.x)), int(round(b.y)), 255, 255, 120)

        blink_hide = (self.invuln_timer > 0.0) and ((int(self.anim_timer * 12.0) & 1) == 1)
        if not blink_hide and self._state != STATE_GAMEOVER:
            set_px(int(round(self.player_x)), int(round(self.player_y)), 0, 240, 255)

        for i in range(min(3, self.lives)):
            set_px(i * 2, 0, 0, 240, 255)
        for w in range(min(3, self.wave)):
            set_px(15 - w * 2, 0, 255, 215, 0)

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
