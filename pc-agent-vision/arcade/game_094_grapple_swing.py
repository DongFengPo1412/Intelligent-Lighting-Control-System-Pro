# -*- coding: utf-8 -*-
"""game_094_grapple_swing.py —— 目标 #094 钩爪摆荡 (Grapple Swing)
横向卷轴熔岩峡谷 + 天顶锚点钩爪锁定 + 真实圆弧单摆角动量摆荡与切向抛射
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

FINISH_X_094 = 90.0


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class SwingAnchor:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.visited = False


class CanyonGem:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.collected = False


class CanyonLedge:
    def __init__(self, x1: float, x2: float, y: float):
        self.x1 = x1
        self.x2 = x2
        self.y = y


class Game094GrappleSwing(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.lives = 3
        self.px = 3.5
        self.py = 9.0
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.latched = False
        self.latched_by_hold = False
        self.latched_anchor = -1
        self.rope_len = 6.0
        self.theta = 0.0
        self.omega = 0.0
        self.grapple_buffer = 0.0
        self.checkpoint_x = 3.5
        self.checkpoint_y = 9.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.anchors: List[SwingAnchor] = []
        self.gems: List[CanyonGem] = []
        self.ledges: List[CanyonLedge] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 94

    @property
    def name(self) -> str:
        return "钩爪摆荡"

    @property
    def english_name(self) -> str:
        return "Grapple Swing"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "天顶锚点钩爪锁定、真实圆弧单摆角动量泵速与切向抛射飞跃"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _respawn_player(self) -> None:
        self.px = self.checkpoint_x
        self.py = self.checkpoint_y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.latched = False
        self.latched_by_hold = False
        self.latched_anchor = -1
        self.rope_len = 6.0
        self.theta = 0.0
        self.omega = 0.0
        self.grapple_buffer = 0.0

    def _setup_course(self) -> None:
        self._score = 0
        self.lives = 3
        self.checkpoint_x = 3.5
        self.checkpoint_y = 9.0
        self.state_timer = 0.0
        self.anim_timer = 0.0

        anchor_coords = [
            (9.5, 2.0), (21.0, 2.0), (33.0, 2.5), (45.0, 2.0),
            (57.0, 2.0), (69.0, 2.5), (80.0, 2.0), (88.5, 2.5),
        ]
        self.anchors = [SwingAnchor(x, y) for x, y in anchor_coords]

        gem_coords = [
            (15.0, 7.5), (27.0, 7.5), (39.0, 8.0),
            (51.0, 7.5), (63.0, 7.5), (75.0, 8.0), (85.0, 7.5),
        ]
        self.gems = [CanyonGem(x, y) for x, y in gem_coords]

        self.ledges = [
            CanyonLedge(0.0, 6.5, 10.0),
            CanyonLedge(41.5, 44.5, 11.0),
            CanyonLedge(89.0, 99.0, 10.5),
        ]
        self._respawn_player()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._setup_course()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_course()
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _try_attach_anchor(self, held: bool) -> bool:
        best = -1
        best_metric = 999.0
        for i, anc in enumerate(self.anchors):
            if anc.y >= self.py - 0.8:
                continue
            if anc.x < self.px - 3.5:
                continue
            dist = math.hypot(self.px - anc.x, self.py - anc.y)
            if dist < 2.2 or dist > 12.5:
                continue
            metric = dist - (1.5 if anc.x >= self.px else 0.0)
            if metric < best_metric:
                best_metric = metric
                best = i

        if best < 0:
            return False

        anc = self.anchors[best]
        dx = self.px - anc.x
        dy = self.py - anc.y
        dist = max(2.5, min(10.5, math.hypot(dx, dy)))

        self.latched = True
        self.latched_by_hold = held
        self.latched_anchor = best
        self.rope_len = dist
        self.theta = math.atan2(dx, dy)
        self.on_ground = False
        self.grapple_buffer = 0.0

        v_tan = self.vx * math.cos(self.theta) - self.vy * math.sin(self.theta)
        self.omega = v_tan / self.rope_len
        if anc.x > self.px and self.omega < 1.15:
            self.omega = 1.15
        self.omega = max(-5.5, min(5.5, self.omega))

        self.px = anc.x + self.rope_len * math.sin(self.theta)
        self.py = anc.y + self.rope_len * math.cos(self.theta)
        self.vx = self.rope_len * math.cos(self.theta) * self.omega
        self.vy = -self.rope_len * math.sin(self.theta) * self.omega

        if not anc.visited:
            anc.visited = True
            self._add_score(25)
        return True

    def _detach_grapple(self) -> None:
        if not self.latched:
            return
        self.vx = self.rope_len * math.cos(self.theta) * self.omega
        self.vy = -self.rope_len * math.sin(self.theta) * self.omega - 1.2
        self.latched = False
        self.latched_by_hold = False
        self.latched_anchor = -1

    def _lose_life(self) -> None:
        if self.lives > 1:
            self.lives -= 1
            self._respawn_player()
        else:
            self.lives = 0
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0

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

            if self.latched:
                release_hold = self.latched_by_hold and ((keys_down & KEY_A) == 0)
                if (keys_pressed & (KEY_A | KEY_B)) or release_hold:
                    self._detach_grapple()
            else:
                if keys_pressed & KEY_A:
                    if not self._try_attach_anchor((keys_down & KEY_A) != 0):
                        self.grapple_buffer = 0.18
                elif self.grapple_buffer > 0.0:
                    self.grapple_buffer -= dt
                    if keys_down & KEY_A:
                        self._try_attach_anchor(True)
                    else:
                        self.grapple_buffer = 0.0

            if self.latched and self.latched_anchor >= 0:
                ctrl = keys_down | keys_pressed
                if ctrl & KEY_UP:
                    self.rope_len = max(2.5, self.rope_len - 4.5 * dt)
                if ctrl & KEY_DOWN:
                    self.rope_len = min(10.5, self.rope_len + 4.5 * dt)

                ang_acc = -(24.0 / self.rope_len) * math.sin(self.theta)
                if ctrl & KEY_RIGHT:
                    ang_acc += 4.2
                if ctrl & KEY_LEFT:
                    ang_acc -= 4.2

                self.omega += ang_acc * dt
                self.omega *= 1.0 - 0.12 * dt
                self.omega = max(-5.5, min(5.5, self.omega))

                self.theta += self.omega * dt
                if self.theta < -1.42:
                    self.theta = -1.42
                    if self.omega < 0.0:
                        self.omega = -self.omega * 0.4
                elif self.theta > 1.42:
                    self.theta = 1.42
                    if self.omega > 0.0:
                        self.omega = -self.omega * 0.4

                anc = self.anchors[self.latched_anchor]
                self.px = anc.x + self.rope_len * math.sin(self.theta)
                self.py = anc.y + self.rope_len * math.cos(self.theta)
                self.vx = self.rope_len * math.cos(self.theta) * self.omega
                self.vy = -self.rope_len * math.sin(self.theta) * self.omega
            elif self.on_ground:
                ctrl = keys_down | keys_pressed
                if ctrl & KEY_LEFT:
                    self.px -= 6.0 * dt
                if ctrl & KEY_RIGHT:
                    self.px += 6.0 * dt
                self.px = max(0.5, self.px)

                if keys_pressed & (KEY_B | KEY_UP):
                    self.vy = -9.5
                    if ctrl & KEY_RIGHT:
                        self.vx = 4.5
                    self.on_ground = False
                else:
                    supported = any(
                        (lg.x1 - 0.3) <= self.px <= (lg.x2 + 0.3) and abs((self.py + 1.0) - lg.y) < 0.6
                        for lg in self.ledges
                    )
                    if not supported:
                        self.on_ground = False
            else:
                ctrl = keys_down | keys_pressed
                if ctrl & KEY_LEFT:
                    self.vx -= 5.0 * dt
                if ctrl & KEY_RIGHT:
                    self.vx += 5.0 * dt

                self.vy = min(16.0, self.vy + 20.0 * dt)
                prev_foot = self.py + 1.0
                self.px += self.vx * dt
                self.py += self.vy * dt

                if self.px < 0.5:
                    self.px = 0.5
                    if self.vx < 0.0:
                        self.vx = 0.0
                if self.py < 1.0:
                    self.py = 1.0
                    if self.vy < 0.0:
                        self.vy = 0.0

                if self.vy >= 0.0:
                    cur_foot = self.py + 1.0
                    for idx, lg in enumerate(self.ledges):
                        if (
                            (lg.x1 - 0.3) <= self.px <= (lg.x2 + 0.3)
                            and prev_foot <= lg.y + 0.4
                            and cur_foot >= lg.y
                        ):
                            self.py = lg.y - 1.0
                            self.vy = 0.0
                            self.vx *= 0.4
                            self.on_ground = True
                            if idx == 1:
                                self.checkpoint_x = 43.0
                                self.checkpoint_y = 10.0
                            break

            for gem in self.gems:
                if not gem.collected and math.hypot(self.px - gem.x, self.py - gem.y) <= 1.6:
                    gem.collected = True
                    self._add_score(50)

            if self.px >= 42.5 and self.py < 13.0 and self.checkpoint_x < 40.0:
                self.checkpoint_x = 43.0
                self.checkpoint_y = 10.0

            if self.px >= FINISH_X_094 and self.py <= 13.5:
                self._add_score(300)
                self._state = STATE_VICTORY
                self.state_timer = 0.0
                return

            if self.py >= 15.0:
                self._lose_life()
                return

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        cam_x = max(0, min(84, int(round(self.px - 5.0))))

        for y in range(16):
            for x in range(16):
                if y == 0:
                    _set_px(fb, x, y, 50, 42, 62)
                elif y == 15:
                    wave = ((x + cam_x + int(self.anim_timer * 8.0)) & 1) == 0
                    _set_px(fb, x, y, 255, 95 if wave else 45, 15)
                else:
                    _set_px(fb, x, y, 14, 18 + y, 34 + y)

        for idx, lg in enumerate(self.ledges):
            x1 = int(round(lg.x1)) - cam_x
            x2 = int(round(lg.x2)) - cam_x
            ly = int(round(lg.y))
            for sx in range(x1, x2 + 1):
                if not (0 <= sx < 16):
                    continue
                if idx == 2:
                    _set_px(fb, sx, ly, 50, 240, 120)
                    if sx == int(round(FINISH_X_094)) - cam_x + 1:
                        _set_px(fb, sx, ly - 1, 255, 225, 45)
                        _set_px(fb, sx, ly - 2, 255, 225, 45)
                else:
                    _set_px(fb, sx, ly, 155, 110, 65)
                for by in range(ly + 1, 15):
                    _set_px(fb, sx, by, 85, 58, 38)

        for gem in self.gems:
            if not gem.collected:
                _set_px(fb, int(round(gem.x)) - cam_x, int(round(gem.y)), 245, 75, 255)

        for idx, anc in enumerate(self.anchors):
            ax = int(round(anc.x)) - cam_x
            ay = int(round(anc.y))
            _set_px(fb, ax, ay - 1, 110, 95, 80)
            if self.latched and self.latched_anchor == idx:
                _set_px(fb, ax, ay, 140, 255, 255)
            else:
                _set_px(fb, ax, ay, 255, 210, 35)

        if self.latched and self.latched_anchor >= 0:
            anc = self.anchors[self.latched_anchor]
            ax = anc.x - float(cam_x)
            ay = anc.y
            sx = self.px - float(cam_x)
            sy = self.py
            for step in range(1, 11):
                t = float(step) / 10.0
                rx = int(round(ax + (sx - ax) * t))
                ry = int(round(ay + (sy - ay) * t))
                _set_px(fb, rx, ry, 70, 240, 255)

        psx = int(round(self.px)) - cam_x
        psy = int(round(self.py))
        _set_px(fb, psx, psy, 255, 245, 220)
        _set_px(fb, psx, psy + 1, 55, 165, 255)

        for i in range(min(3, self.lives)):
            _set_px(fb, i * 2, 0, 80, 235, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = max(0, min(100, int((self.px / FINISH_X_094) * 100.0)))
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": prog,
        }
