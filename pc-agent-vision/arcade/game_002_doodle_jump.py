# -*- coding: utf-8 -*-
"""game_002_doodle_jump.py —— 目标 #002 涂鸦跳跃 (Doodle Jump)
踩板自动弹跳上升 + 左右穿屏移动 + 镜头单向上移计分
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TWO_BUTTON,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
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

DOODLE_PLAT_NORMAL  = 0
DOODLE_PLAT_MOVING  = 1
DOODLE_PLAT_SPRING  = 2
DOODLE_PLAT_FRAGILE = 3


class DoodlePlatform:
    def __init__(self, x: float = 0.0, y: float = 0.0, vx: float = 0.0,
                 plat_type: int = DOODLE_PLAT_NORMAL, broken: bool = False):
        self.x = x
        self.y = y
        self.vx = vx
        self.type = plat_type
        self.broken = broken


class Game002DoodleJump(BaseCartridge):
    MAX_PLATFORMS = 7

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self.player_x = 7.0
        self.player_y = 11.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.facing_right = True
        self.max_altitude = 0.0
        self._score = 0
        self._high_score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_seed = 0x20090002
        self.platforms: List[DoodlePlatform] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 2

    @property
    def name(self) -> str:
        return "涂鸦跳跃"

    @property
    def english_name(self) -> str:
        return "Doodle Jump"

    @property
    def release_year(self) -> int:
        return 2009

    @property
    def control_type(self) -> int:
        return CTRL_TWO_BUTTON

    @property
    def core_mechanic(self) -> str:
        return "踩板自动弹跳与左右穿屏无限攀升"

    def _next_rand(self) -> int:
        self._rng_seed = (self._rng_seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._rng_seed >> 16) & 0x7FFF

    def _highest_solid_y(self) -> float:
        solids = [p.y for p in self.platforms if not p.broken and p.type != DOODLE_PLAT_FRAGILE]
        return min(solids) if solids else 14.0

    def _spawn_platform_above(self, ref_solid_y: float, allow_fragile: bool) -> DoodlePlatform:
        r1 = self._next_rand()
        r2 = self._next_rand()
        px = 1.0 + float(r1 % 12)
        roll = r2 % 100
        if self.max_altitude < 30.0:
            if roll < 75:
                ptype = DOODLE_PLAT_NORMAL
            elif roll < 90:
                ptype = DOODLE_PLAT_SPRING
            else:
                ptype = DOODLE_PLAT_MOVING
        else:
            if roll < 50:
                ptype = DOODLE_PLAT_NORMAL
            elif roll < 72:
                ptype = DOODLE_PLAT_MOVING
            elif roll < 88 or not allow_fragile:
                ptype = DOODLE_PLAT_SPRING
            else:
                ptype = DOODLE_PLAT_FRAGILE

        if ptype == DOODLE_PLAT_FRAGILE:
            py = ref_solid_y - 1.2
        else:
            gap = 2.1 + float(((r1 >> 5) % 7)) * 0.1
            py = ref_solid_y - gap

        vx = (2.8 if ((r2 >> 8) & 1) else -2.8) if ptype == DOODLE_PLAT_MOVING else 0.0
        return DoodlePlatform(px, py, vx, ptype, False)

    def _init_play_state(self) -> None:
        self._rng_seed = 0x20090002
        self.player_x = 7.0
        self.player_y = 11.0
        self.player_vx = 0.0
        self.player_vy = -14.5
        self.facing_right = True
        self.max_altitude = 0.0
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0

        self.platforms = [DoodlePlatform(6.0, 14.0, 0.0, DOODLE_PLAT_NORMAL, False)]
        ref_y = 14.0
        prev_fragile = False
        for _ in range(1, self.MAX_PLATFORMS):
            p = self._spawn_platform_above(ref_y, not prev_fragile)
            self.platforms.append(p)
            if p.type == DOODLE_PLAT_FRAGILE:
                prev_fragile = True
            else:
                prev_fragile = False
                ref_y = p.y

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._init_play_state()
        self._state = STATE_TITLE

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._init_play_state()
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.player_vy += 28.0 * dt
            self.player_y += self.player_vy * dt
            if self.player_y >= 12.0:
                self.player_y = 12.0
                self.player_vy = -11.5
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
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

            accel = 30.0
            max_vx = 8.5
            friction = 16.0

            if keys_down & KEY_LEFT:
                self.player_vx -= accel * dt
                self.facing_right = False
            elif keys_down & KEY_RIGHT:
                self.player_vx += accel * dt
                self.facing_right = True
            else:
                if self.player_vx > 0.0:
                    self.player_vx = max(0.0, self.player_vx - friction * dt)
                elif self.player_vx < 0.0:
                    self.player_vx = min(0.0, self.player_vx + friction * dt)

            self.player_vx = max(-max_vx, min(max_vx, self.player_vx))

            gravity = 28.0
            self.player_vy = min(16.0, self.player_vy + gravity * dt)

            next_x = (self.player_x + self.player_vx * dt) % 16.0
            self.player_x = next_x

            old_y = self.player_y
            next_y = self.player_y + self.player_vy * dt

            for p in self.platforms:
                if p.type == DOODLE_PLAT_MOVING and not p.broken:
                    p.x += p.vx * dt
                    if p.x <= 0.0:
                        p.x = 0.0
                        p.vx = -p.vx
                    elif p.x >= 13.0:
                        p.x = 13.0
                        p.vx = -p.vx

            if self.player_vy > 0.0:
                feet_old = old_y + 2.0
                feet_new = next_y + 2.0
                for p in self.platforms:
                    if p.broken:
                        continue
                    plat_top = p.y
                    plat_left = p.x - 0.6
                    plat_right = p.x + 2.8

                    horiz_hit = any(
                        (self.player_x + shift + 1.8 >= plat_left and self.player_x + shift <= plat_right)
                        for shift in (-16.0, 0.0, 16.0)
                    )
                    if horiz_hit and feet_old <= plat_top + 0.55 and feet_new >= plat_top - 0.2:
                        next_y = plat_top - 2.0
                        if p.type == DOODLE_PLAT_SPRING:
                            self.player_vy = -21.0
                        elif p.type == DOODLE_PLAT_FRAGILE:
                            p.broken = True
                            self.player_vy = -6.0
                        else:
                            self.player_vy = -14.5
                        break

            self.player_y = next_y

            scroll_line = 6.5
            if self.player_y < scroll_line:
                dy = scroll_line - self.player_y
                self.player_y = scroll_line
                self.max_altitude += dy
                new_score = int(self.max_altitude * 10.0)
                if new_score > self._score:
                    self._score = new_score
                    if self._score > self._high_score:
                        self._high_score = self._score

                for p in self.platforms:
                    p.y += dy
                for i, p in enumerate(self.platforms):
                    if p.y >= 16.0:
                        top_solid = self._highest_solid_y()
                        self.platforms[i] = self._spawn_platform_above(top_solid, True)

            if self.player_y >= 16.0:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                if self._score > self._high_score:
                    self._high_score = self._score

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                set_pixel(fb, x, y, 10, 14, 26)

        star_off = int(self.max_altitude) & 15
        for i in range(4):
            sx = (i * 5 + 2) & 15
            sy = (i * 7 + star_off) & 15
            set_pixel(fb, sx, sy, 32, 48, 76)

        for p in self.platforms:
            if p.broken:
                continue
            py = int(round(p.y))
            px = int(round(p.x))
            if 0 <= py < 16:
                r, g, b = 39, 174, 96
                if p.type == DOODLE_PLAT_MOVING:
                    r, g, b = 0, 210, 211
                elif p.type == DOODLE_PLAT_SPRING:
                    r, g, b = 241, 196, 15
                elif p.type == DOODLE_PLAT_FRAGILE:
                    r, g, b = 211, 84, 0
                for dx in range(3):
                    if p.type == DOODLE_PLAT_SPRING and dx == 1:
                        set_pixel(fb, px + dx, py, 255, 255, 255)
                    else:
                        set_pixel(fb, px + dx, py, r, g, b)

        px = int(round(self.player_x)) & 15
        py = int(round(self.player_y))
        for dy in range(2):
            for dx in range(2):
                wx = (px + dx) & 15
                wy = py + dy
                if dy == 0:
                    if (self.facing_right and dx == 1) or (not self.facing_right and dx == 0):
                        set_pixel(fb, wx, wy, 255, 255, 255)
                    else:
                        set_pixel(fb, wx, wy, 46, 204, 113)
                else:
                    set_pixel(fb, wx, wy, 230, 126, 34)

        if self._state == STATE_GAMEOVER:
            for x in range(16):
                set_pixel(fb, x, 15, 231, 76, 60)
        elif self._state == STATE_PAUSED:
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
            "progress": min(100, int(self.max_altitude)),
        }
