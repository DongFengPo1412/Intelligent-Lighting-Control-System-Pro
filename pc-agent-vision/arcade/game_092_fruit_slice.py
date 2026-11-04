# -*- coding: utf-8 -*-
"""game_092_fruit_slice.py —— 目标 #092 水果忍者 (Fruit Ninja)
抛物线上抛多彩水果与脉冲炸弹 + 十字键刀光游标与10像素直线斩击 + 多果连斩暴击
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
from .arcade_result_screen import ArcadeResultScreen


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class FruitItem:
    def __init__(
        self,
        active: bool = False,
        is_bomb: bool = False,
        kind: int = 0,
        x: float = 0.0,
        y: float = 16.0,
        vx: float = 0.0,
        vy: float = 0.0,
    ):
        self.active = active
        self.is_bomb = is_bomb
        self.kind = kind
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


class JuiceDrop:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.life = 0.0
        self.r = 255
        self.g = 255
        self.b = 255


class Game092FruitSlice(BaseCartridge):
    difficulty_supported = True
    MAX_ITEMS = 8
    MAX_DROPS = 24

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.lives = (5,3,2)[self.difficulty]
        self.fruits_sliced = 0
        self.rng_seed = 0x2010F92A
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.spawn_timer = 0.25
        self.blade_x = 7.5
        self.blade_y = 8.0
        self.slash_timer = 0.0
        self.slash_x0 = 2.5
        self.slash_y0 = 8.0
        self.slash_x1 = 12.5
        self.slash_y1 = 8.0
        self.last_combo = 0
        self.exploded = False
        self.items: List[FruitItem] = [FruitItem() for _ in range(self.MAX_ITEMS)]
        self.drops: List[JuiceDrop] = [JuiceDrop() for _ in range(self.MAX_DROPS)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 92

    @property
    def name(self) -> str:
        return "水果忍者"

    @property
    def english_name(self) -> str:
        return "Fruit Ninja"

    @property
    def release_year(self) -> int:
        return 2010

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "抛物线水果与炸弹投掷、方向直线刀光一闪多果暴击"

    def _next_rand(self) -> int:
        self.rng_seed = (self.rng_seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self.rng_seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _setup_match(self) -> None:
        self._score = 0
        self.lives = (5,3,2)[self.difficulty]
        self.fruits_sliced = 0
        self.rng_seed = 0x2010F92A
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.spawn_timer = 0.20
        self.blade_x = 7.5
        self.blade_y = 8.0
        self.slash_timer = 0.0
        self.last_combo = 0
        self.exploded = False
        for it in self.items:
            it.active = False
        for dp in self.drops:
            dp.active = False

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._setup_match()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_match()
            self._state = STATE_PLAYING
            self._spawn_wave()

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _spawn_wave(self) -> None:
        count = 1 + (self._next_rand() % 3)
        spawned_bomb = False
        for _ in range(count):
            slot = next((i for i, it in enumerate(self.items) if not it.active), -1)
            if slot < 0:
                break
            r1 = self._next_rand()
            r2 = self._next_rand()
            r3 = self._next_rand()
            start_x = 2.0 + float(r1 % 11)
            make_bomb = (not spawned_bomb) and (count >= 2) and (r2 % 5 == 0)
            if make_bomb:
                spawned_bomb = True

            it = self.items[slot]
            it.active = True
            it.is_bomb = make_bomb
            it.kind = r3 % 4
            it.x = start_x
            it.y = 15.6
            it.vx = (7.0 - start_x) * 0.35 + float((r2 % 5) - 2) * 0.25
            it.vy = -15.8 - float(r1 % 35) * 0.1

    def _spawn_juice(self, cx: float, cy: float, kind: int, explosion: bool) -> None:
        if explosion:
            r, g, b = 255, 90, 30
        elif kind == 0:
            r, g, b = 245, 55, 65
        elif kind == 1:
            r, g, b = 255, 150, 25
        elif kind == 2:
            r, g, b = 255, 235, 45
        else:
            r, g, b = 80, 145, 255

        burst = 8 if explosion else 4
        for k in range(burst):
            slot = next((i for i, dp in enumerate(self.drops) if not dp.active), -1)
            if slot < 0:
                break
            ang = float(k) * (2.0 * math.pi / float(burst)) + 0.35
            spd = 9.5 if explosion else 5.5
            dp = self.drops[slot]
            dp.active = True
            dp.x = cx
            dp.y = cy
            dp.vx = math.cos(ang) * spd
            dp.vy = math.sin(ang) * spd - 2.0
            dp.life = 0.55 if explosion else 0.42
            if explosion and (k & 1):
                dp.r, dp.g, dp.b = 255, 245, 200
            else:
                dp.r, dp.g, dp.b = r, g, b

    def _perform_slash(self, keys_down: int, keys_pressed: int) -> None:
        dir_mask = keys_down | keys_pressed
        dx = 0.0
        dy = 0.0
        if dir_mask & KEY_LEFT:
            dx -= 1.0
        if dir_mask & KEY_RIGHT:
            dx += 1.0
        if dir_mask & KEY_UP:
            dy -= 1.0
        if dir_mask & KEY_DOWN:
            dy += 1.0

        if dx == 0.0 and dy == 0.0:
            if keys_pressed & KEY_B:
                dx = 0.70710678
                dy = -0.70710678
            else:
                dx = 1.0
                dy = 0.0
        else:
            inv = 1.0 / math.hypot(dx, dy)
            dx *= inv
            dy *= inv

        self.slash_x0 = self.blade_x - dx * 5.0
        self.slash_y0 = self.blade_y - dy * 5.0
        self.slash_x1 = self.blade_x + dx * 5.0
        self.slash_y1 = self.blade_y + dy * 5.0
        self.slash_timer = 0.18

        sx = self.slash_x1 - self.slash_x0
        sy = self.slash_y1 - self.slash_y0
        seg_len_sq = max(0.001, sx * sx + sy * sy)

        hit_fruits = 0
        for it in self.items:
            if not it.active:
                continue
            cx = it.x + 1.0
            cy = it.y + 1.0
            t = ((cx - self.slash_x0) * sx + (cy - self.slash_y0) * sy) / seg_len_sq
            t = max(0.0, min(1.0, t))
            qx = self.slash_x0 + t * sx
            qy = self.slash_y0 + t * sy
            if math.hypot(cx - qx, cy - qy) <= (1.9,1.65,1.4)[self.difficulty]:
                if it.is_bomb:
                    it.active = False
                    self.exploded = True
                    self.lives = 0
                    self._spawn_juice(cx, cy, 0, True)
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
                else:
                    it.active = False
                    hit_fruits += 1
                    self.fruits_sliced += 1
                    self._spawn_juice(cx, cy, it.kind, False)

        if hit_fruits:self.emit_sound("hit",hit_fruits)
        self.last_combo = hit_fruits
        if hit_fruits > 0:
            pts = hit_fruits * 10
            if hit_fruits >= 2:
                pts += hit_fruits * 20
            self._add_score(pts)
            if self.fruits_sliced >= 40:
                self._add_score(100)
                self._state = STATE_VICTORY
                self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt < 0.0:
            dt = 0.0
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.blade_x = 7.5 + math.cos(self.anim_timer * 2.5) * 3.0
            self.blade_y = 8.0 + math.sin(self.anim_timer * 3.5) * 2.0
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            for dp in self.drops:
                if not dp.active:
                    continue
                dp.vy += 16.0 * dt
                dp.x += dp.vx * dt
                dp.y += dp.vy * dt
                dp.life -= dt
                if dp.life <= 0.0:
                    dp.active = False
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
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

            blade_speed = 14.0
            if keys_down & KEY_LEFT:
                self.blade_x -= blade_speed * dt
            if keys_down & KEY_RIGHT:
                self.blade_x += blade_speed * dt
            if keys_down & KEY_UP:
                self.blade_y -= blade_speed * dt
            if keys_down & KEY_DOWN:
                self.blade_y += blade_speed * dt
            self.blade_x = max(1.0, min(14.0, self.blade_x))
            self.blade_y = max(1.5, min(14.5, self.blade_y))

            if self.slash_timer > 0.0:
                self.slash_timer = max(0.0, self.slash_timer - dt)

            if keys_pressed & (KEY_A | KEY_B) and self.slash_timer<=0:
                self._perform_slash(keys_down, keys_pressed)
                if self._state != STATE_PLAYING:
                    return

            self.spawn_timer -= dt
            if self.spawn_timer <= 0.0:
                self._spawn_wave()
                self.spawn_timer = max((.85,.65,.48)[self.difficulty], (1.40,1.15,.95)[self.difficulty] - float(self.fruits_sliced) * 0.01)

            gravity = 16.0
            for it in self.items:
                if not it.active:
                    continue
                it.vy += gravity * dt
                it.x += it.vx * dt
                it.y += it.vy * dt

                if it.x < 0.5:
                    it.x = 0.5
                    it.vx = abs(it.vx)
                elif it.x > 13.5:
                    it.x = 13.5
                    it.vx = -abs(it.vx)

                if it.vy > 0.0 and it.y > 16.2:
                    was_bomb = it.is_bomb
                    it.active = False
                    if not was_bomb:
                        if self.lives > 1:
                            self.lives -= 1
                        else:
                            self.lives = 0
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return

            for dp in self.drops:
                if not dp.active:
                    continue
                dp.vy += 18.0 * dt
                dp.x += dp.vx * dt
                dp.y += dp.vy * dt
                dp.life -= dt
                if dp.life <= 0.0:
                    dp.active = False

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            r, g, b = (30, 19, 11) if (y % 4 == 0) else (22, 13, 8)
            for x in range(16):
                _set_px(fb, x, y, r, g, b)

        if self._state == STATE_GAMEOVER and self.exploded and self.state_timer < 0.45:
            for y in range(16):
                for x in range(16):
                    if ((x + y) & 1) == 0:
                        _set_px(fb, x, y, 255, 70, 50)
                    else:
                        _set_px(fb, x, y, 255, 220, 180)

        if self._state == STATE_TITLE:
            _set_px(fb, 4, 6, 240, 50, 60)
            _set_px(fb, 5, 6, 240, 50, 60)
            _set_px(fb, 4, 7, 40, 200, 70)
            _set_px(fb, 5, 7, 40, 200, 70)
            _set_px(fb, 10, 5, 255, 150, 25)
            _set_px(fb, 11, 5, 255, 200, 60)
            _set_px(fb, 10, 6, 255, 140, 20)
            _set_px(fb, 11, 6, 255, 150, 25)
            for s in range(-4, 5):
                _set_px(fb, 8 + s, 8 - int(s / 2), 190, 250, 255)

        for dp in self.drops:
            if dp.active:
                _set_px(fb, int(round(dp.x)), int(round(dp.y)), dp.r, dp.g, dp.b)

        pulse = (int(self.anim_timer * 10.0) & 1) != 0
        for it in self.items:
            if not it.active:
                continue
            ix = int(round(it.x))
            iy = int(round(it.y))
            if it.is_bomb:
                br, bg, bb = (210, 30, 35) if pulse else (55, 20, 28)
                _set_px(fb, ix, iy, br, bg, bb)
                _set_px(fb, ix + 1, iy, 40, 15, 20)
                _set_px(fb, ix, iy + 1, 40, 15, 20)
                _set_px(fb, ix + 1, iy + 1, br, bg, bb)
                if pulse:
                    _set_px(fb, ix + 1, iy - 1, 255, 245, 90)
                else:
                    _set_px(fb, ix + 1, iy - 1, 255, 120, 20)
            elif it.kind == 0:
                _set_px(fb, ix, iy, 245, 50, 65)
                _set_px(fb, ix + 1, iy, 245, 50, 65)
                _set_px(fb, ix, iy + 1, 40, 205, 70)
                _set_px(fb, ix + 1, iy + 1, 40, 205, 70)
            elif it.kind == 1:
                _set_px(fb, ix, iy, 255, 195, 65)
                _set_px(fb, ix + 1, iy, 255, 145, 20)
                _set_px(fb, ix, iy + 1, 255, 145, 20)
                _set_px(fb, ix + 1, iy + 1, 225, 110, 10)
            elif it.kind == 2:
                _set_px(fb, ix, iy, 255, 240, 55)
                _set_px(fb, ix + 1, iy, 255, 230, 35)
                _set_px(fb, ix, iy + 1, 235, 195, 20)
                _set_px(fb, ix + 1, iy + 1, 255, 240, 55)
            else:
                _set_px(fb, ix, iy, 150, 205, 255)
                _set_px(fb, ix + 1, iy, 65, 130, 255)
                _set_px(fb, ix, iy + 1, 65, 130, 255)
                _set_px(fb, ix + 1, iy + 1, 45, 95, 220)

        if self.slash_timer > 0.0:
            blitz = self.last_combo >= 2
            for step in range(11):
                t = float(step) / 10.0
                sx = int(round(self.slash_x0 + (self.slash_x1 - self.slash_x0) * t))
                sy = int(round(self.slash_y0 + (self.slash_y1 - self.slash_y0) * t))
                if blitz:
                    _set_px(fb, sx, sy, 255, 245, 130)
                elif 3 <= step <= 7:
                    _set_px(fb, sx, sy, 255, 255, 255)
                else:
                    _set_px(fb, sx, sy, 110, 245, 255)

        _set_px(fb, int(round(self.blade_x)), int(round(self.blade_y)), 180, 250, 255)

        for i in range(min(5, self.lives)):
            _set_px(fb, 15 - i * 2, 0, 46, 215, 95)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (self.fruits_sliced * 100) // 40),
        }
