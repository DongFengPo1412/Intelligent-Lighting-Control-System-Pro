# -*- coding: utf-8 -*-
"""game_093_black_hole.py —— 目标 #093 黑洞吞噬 (Hole.io)
城市街区四向游走黑洞 + 三阶体积阈值判定(阻挡推挤 vs 引力吞噬) + 半径成长扩张清图
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
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

WORLD_SIZE_093 = 24.0
ROUND_DURATION_093 = 45.0


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class CityProp:
    def __init__(self, tier: int, size: int, x: float, y: float, req_radius: float):
        self.alive = True
        self.tier = tier
        self.size = size
        self.x = x
        self.y = y
        self.req_radius = req_radius


class Game093BlackHole(BaseCartridge):
    TOTAL_PROPS = 20

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.hole_x = 12.0
        self.hole_y = 12.0
        self.hole_radius = 1.0
        self.time_left = ROUND_DURATION_093
        self.swallow_pulse = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.remaining_props = self.TOTAL_PROPS
        self.props: List[CityProp] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 93

    @property
    def name(self) -> str:
        return "黑洞吞噬"

    @property
    def english_name(self) -> str:
        return "Hole.io"

    @property
    def release_year(self) -> int:
        return 2018

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "三阶体积门限吞噬成长与大型建筑物理阻挡"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _setup_city(self) -> None:
        self._score = 0
        self.hole_x = 12.0
        self.hole_y = 12.0
        self.hole_radius = 1.0
        self.time_left = ROUND_DURATION_093
        self.swallow_pulse = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.remaining_props = self.TOTAL_PROPS

        tier1_pos = [
            (9.0, 11.0), (14.0, 11.0), (11.0, 8.0), (11.0, 15.0),
            (6.0, 6.0),  (17.0, 6.0),  (6.0, 17.0), (17.0, 17.0),
            (7.0, 13.0), (16.0, 9.0),
        ]
        tier2_pos = [
            (2.0, 9.0), (20.0, 9.0), (2.0, 15.0),
            (20.0, 15.0), (9.0, 2.0), (14.0, 20.0),
        ]
        tier3_pos = [
            (1.0, 1.0), (20.0, 1.0), (1.0, 20.0), (20.0, 20.0),
        ]

        self.props = (
            [CityProp(1, 1, x, y, 1.0) for x, y in tier1_pos]
            + [CityProp(2, 2, x, y, 1.8) for x, y in tier2_pos]
            + [CityProp(3, 3, x, y, 2.6) for x, y in tier3_pos]
        )

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._setup_city()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_city()
            self._state = STATE_PLAYING

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
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (
                keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)
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

            if self.swallow_pulse > 0.0:
                self.swallow_pulse = max(0.0, self.swallow_pulse - dt)

            self.time_left -= dt
            if self.time_left <= 0.0:
                self.time_left = 0.0
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

            move_mask = keys_down | keys_pressed
            vx = 0.0
            vy = 0.0
            if move_mask & KEY_LEFT:
                vx -= 1.0
            if move_mask & KEY_RIGHT:
                vx += 1.0
            if move_mask & KEY_UP:
                vy -= 1.0
            if move_mask & KEY_DOWN:
                vy += 1.0

            if vx != 0.0 or vy != 0.0:
                inv = 1.0 / math.hypot(vx, vy)
                move_speed = 9.0
                self.hole_x += vx * inv * move_speed * dt
                self.hole_y += vy * inv * move_speed * dt

            self.hole_x = max(1.2, min(WORLD_SIZE_093 - 1.2, self.hole_x))
            self.hole_y = max(1.2, min(WORLD_SIZE_093 - 1.2, self.hole_y))

            for prop in self.props:
                if not prop.alive:
                    continue
                half = float(prop.size) * 0.5
                ox = prop.x + half
                oy = prop.y + half
                dx = self.hole_x - ox
                dy = self.hole_y - oy
                dist = math.hypot(dx, dy)

                if self.hole_radius + 0.001 >= prop.req_radius:
                    pull_range = self.hole_radius + half + 0.8
                    if 0.05 < dist < pull_range:
                        pull = 5.5 * dt
                        prop.x += (dx / dist) * pull
                        prop.y += (dy / dist) * pull
                        ox = prop.x + half
                        oy = prop.y + half
                        dist = math.hypot(self.hole_x - ox, self.hole_y - oy)

                    capture_r = self.hole_radius * 0.85 + 0.45
                    if dist <= capture_r:
                        prop.alive = False
                        if self.remaining_props > 0:
                            self.remaining_props -= 1
                        self.swallow_pulse = 0.22
                        if prop.tier == 1:
                            self.hole_radius += 0.10
                            self._add_score(15)
                        elif prop.tier == 2:
                            self.hole_radius += 0.15
                            self._add_score(40)
                        else:
                            self.hole_radius += 0.20
                            self._add_score(100)
                        self.hole_radius = min(3.5, self.hole_radius)

                        if self.remaining_props == 0:
                            self._add_score(int(self.time_left * 5.0))
                            self._state = STATE_VICTORY
                            self.state_timer = 0.0
                            return
                else:
                    min_sep = half + 0.68
                    if dist < min_sep:
                        if dist < 0.001:
                            self.hole_x = ox + min_sep
                        else:
                            self.hole_x = ox + (dx / dist) * min_sep
                            self.hole_y = oy + (dy / dist) * min_sep
                        self.hole_x = max(1.2, min(WORLD_SIZE_093 - 1.2, self.hole_x))
                        self.hole_y = max(1.2, min(WORLD_SIZE_093 - 1.2, self.hole_y))

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        cam_x = max(0, min(8, int(round(self.hole_x - 8.0))))
        cam_y = max(0, min(8, int(round(self.hole_y - 8.0))))

        for sy in range(16):
            wy = cam_y + sy
            for sx in range(16):
                wx = cam_x + sx
                if wx % 6 == 0 or wy % 6 == 0:
                    if ((wx + wy) % 3) == 0:
                        _set_px(fb, sx, sy, 52, 54, 64)
                    else:
                        _set_px(fb, sx, sy, 34, 36, 44)
                else:
                    _set_px(fb, sx, sy, 22, 26, 32)

        for i, prop in enumerate(self.props):
            if not prop.alive:
                continue
            px = int(round(prop.x)) - cam_x
            py = int(round(prop.y)) - cam_y
            edible = (self.hole_radius + 0.001) >= prop.req_radius

            if prop.tier == 1:
                if (i & 1) == 0:
                    _set_px(fb, px, py, 46, 215, 90)
                else:
                    _set_px(fb, px, py, 255, 145, 35)
            elif prop.tier == 2:
                r, g, b = (255, 225, 55) if edible else (215, 175, 25)
                for dy in range(2):
                    for dx in range(2):
                        _set_px(
                            fb,
                            px + dx,
                            py + dy,
                            255 if (dx == 0 and dy == 0) else r,
                            250 if (dx == 0 and dy == 0) else g,
                            b,
                        )
            else:
                for dy in range(3):
                    for dx in range(3):
                        if dx == 1 and dy == 1:
                            _set_px(fb, px + dx, py + dy, 255, 195, 70)
                        elif edible:
                            _set_px(fb, px + dx, py + dy, 55, 225, 255)
                        else:
                            _set_px(fb, px + dx, py + dy, 35, 135, 185)

        hsx = self.hole_x - float(cam_x)
        hsy = self.hole_y - float(cam_y)
        pulse = 0.5 + 0.5 * math.sin(self.anim_timer * 7.0)
        outer_r = self.hole_radius + 0.48 + (0.25 if self.swallow_pulse > 0.0 else 0.0)
        core_r = max(0.65, self.hole_radius * 0.72)

        for sy in range(16):
            for sx in range(16):
                d = math.hypot((float(sx) + 0.5) - hsx, (float(sy) + 0.5) - hsy)
                if d <= core_r:
                    _set_px(fb, sx, sy, 5, 2, 10)
                elif d <= outer_r:
                    pr = int(165.0 + 75.0 * pulse)
                    pg = int(40.0 + (90.0 if self.swallow_pulse > 0.0 else 35.0 * pulse))
                    _set_px(fb, sx, sy, pr, pg, 255)

        bars = max(0, min(16, int(math.ceil((self.time_left / ROUND_DURATION_093) * 16.0))))
        for x in range(bars):
            if self.time_left > 15.0:
                _set_px(fb, x, 0, 140, 80, 255)
            else:
                _set_px(fb, x, 0, 255, 65, 55)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        eaten = self.TOTAL_PROPS - self.remaining_props
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": 0 if self._state == STATE_GAMEOVER else 1,
            "state": self._state,
            "progress": min(100, (eaten * 100) // self.TOTAL_PROPS),
        }
