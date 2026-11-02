"""
Game #077: 泡泡飞盘 / 飞盘争霸 (Windjammers 1994 / Data East / Neo Geo)
Head-to-head Power Disc Duels, Curve Throws, Slide Tackles & Super Custom Shots.
"""

import math
from typing import Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)

STATE_SERVE = 0
STATE_RALLY = 1
STATE_GOAL = 2
STATE_MATCH_OVER = 3


class Game077Windjammers(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_SERVE
        self.state_timer = 0.0
        self.match_timer = 60.0
        self.player_score = 0
        self.ai_score = 0
        self.last_scorer = 1

        # Player
        self.px = 3.0
        self.py = 7.5
        self.p_dash_vx = 0.0
        self.p_dash_vy = 0.0
        self.p_dash_timer = 0.0
        self.player_charge = 0.0

        # AI
        self.aix = 12.0
        self.aiy = 7.5
        self.ai_dash_timer = 0.0
        self.ai_charge = 0.0

        # Disc
        self.disc_x = 4.0
        self.disc_y = 7.5
        self.disc_vx = 0.0
        self.disc_vy = 0.0
        self.disc_speed = 10.0
        self.disc_is_super = False
        self.disc_held_by = 1
        self.disc_hold_timer = 1.5

        self.reset()

    @property
    def game_id(self) -> int:
        return 77

    @property
    def name(self) -> str:
        return "泡泡飞盘"

    @property
    def english_name(self) -> str:
        return "Windjammers"

    @property
    def release_year(self) -> int:
        return 1994

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双人球台飞盘弧线对掷 + 蓄力超必杀旋转螺旋盘 + 挡板防守反弹门线防守"

    def get_name(self) -> str:
        return "Windjammers (1994)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_SERVE
        self.state_timer = 0.0
        self.match_timer = 60.0
        self.player_score = 0
        self.ai_score = 0
        self.last_scorer = 1
        self.reset_point(1)

    def reset_point(self, server: int):
        self.px = 3.0
        self.py = 7.5
        self.p_dash_timer = 0.0
        self.player_charge = 0.0

        self.aix = 12.0
        self.aiy = 7.5
        self.ai_dash_timer = 0.0
        self.ai_charge = 0.0

        self.disc_is_super = False
        self.disc_speed = 10.0

        if server == 1:
            self.disc_held_by = 1
            self.disc_x = self.px + 0.8
            self.disc_y = self.py
            self.disc_vx = 0.0
            self.disc_vy = 0.0
            self.disc_hold_timer = 1.5
        else:
            self.disc_held_by = 2
            self.disc_x = self.aix - 0.8
            self.disc_y = self.aiy
            self.disc_vx = 0.0
            self.disc_vy = 0.0
            self.disc_hold_timer = 1.5

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_MATCH_OVER:
            if self.state_timer > 3.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_GOAL:
            if self.state_timer > 1.5:
                if self.player_score >= 12 or self.ai_score >= 12 or self.match_timer <= 0.0:
                    self.state = STATE_MATCH_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_SERVE
                    self.state_timer = 0.0
                    self.reset_point(2 if self.last_scorer == 1 else 1)
            return

        self.match_timer = max(0.0, self.match_timer - dt)
        if self.match_timer <= 0.0 and self.state == STATE_RALLY:
            self.state = STATE_MATCH_OVER
            self.state_timer = 0.0
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_ai(dt)
        self.update_disc(dt)
        self.check_goals()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        speed = 6.0

        if self.p_dash_timer > 0.0:
            self.p_dash_timer -= dt
            self.px += self.p_dash_vx * 14.0 * dt
            self.py += self.p_dash_vy * 14.0 * dt
        else:
            move_x = 0.0
            move_y = 0.0
            if buttons & KEY_LEFT:
                move_x -= 1.0
            if buttons & KEY_RIGHT:
                move_x += 1.0
            if buttons & KEY_UP:
                move_y -= 1.0
            if buttons & KEY_DOWN:
                move_y += 1.0

            self.px += move_x * speed * dt
            self.py += move_y * speed * dt

            # Slide Dash intercept
            if self.disc_held_by != 1 and (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.p_dash_vx = move_x if (move_x != 0.0 or move_y != 0.0) else 1.0
                self.p_dash_vy = move_y
                self.p_dash_timer = 0.22

        # Boundary
        self.px = max(1.0, min(7.0, self.px))
        self.py = max(1.0, min(14.0, self.py))

        if self.disc_held_by == 1:
            self.disc_x = self.px + 0.8
            self.disc_y = self.py
            self.disc_hold_timer -= dt
            self.player_charge = min(1.0, self.player_charge + dt * 1.5)

            throw_btn = (buttons & KEY_A) and not (prev_buttons & KEY_A)
            lob_btn = (buttons & KEY_B) and not (prev_buttons & KEY_B)

            if throw_btn or self.disc_hold_timer <= 0.0:
                self.disc_held_by = 0
                self.state = STATE_RALLY
                base_spd = 16.0 if self.player_charge >= 0.95 else 11.0
                self.disc_is_super = self.player_charge >= 0.95

                throw_vy = 0.0
                if buttons & KEY_UP:
                    throw_vy = -6.5
                if buttons & KEY_DOWN:
                    throw_vy = 6.5

                self.disc_vx = base_spd
                self.disc_vy = throw_vy
                self.player_charge = 0.0
            elif lob_btn:
                self.disc_held_by = 0
                self.state = STATE_RALLY
                self.disc_is_super = False
                self.disc_vx = 7.0
                self.disc_vy = -3.0 if (buttons & KEY_UP) else (3.0 if (buttons & KEY_DOWN) else 0.0)
                self.player_charge = 0.0
        else:
            dx = self.disc_x - self.px
            dy = self.disc_y - self.py
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 1.1 and self.disc_held_by == 0 and self.disc_vx < 0.0:
                self.disc_held_by = 1
                self.disc_hold_timer = 0.9
                self.disc_vx = 0.0
                self.disc_vy = 0.0
                self.player_charge = 0.6 if (self.p_dash_timer > 0.0) else 0.0

    def update_ai(self, dt: float):
        ai_speed = 5.2

        if self.disc_held_by == 2:
            self.disc_x = self.aix - 0.8
            self.disc_y = self.aiy
            self.disc_hold_timer -= dt
            self.ai_charge = min(1.0, self.ai_charge + dt * 1.4)

            if self.disc_hold_timer <= 0.3:
                self.disc_held_by = 0
                self.state = STATE_RALLY
                do_super = self.ai_charge >= 0.9
                self.disc_is_super = do_super
                self.disc_vx = -15.0 if do_super else -10.5
                self.disc_vy = 5.5 if self.py < 7.5 else -5.5
                self.ai_charge = 0.0
        else:
            target_y = self.disc_y
            if target_y > self.aiy + 0.3:
                self.aiy += ai_speed * dt
            elif target_y < self.aiy - 0.3:
                self.aiy -= ai_speed * dt

            target_x = self.disc_x if (self.disc_vx > 0.0 and self.disc_x > 10.0) else 12.5
            if target_x > self.aix + 0.3:
                self.aix += ai_speed * dt
            elif target_x < self.aix - 0.3:
                self.aix -= ai_speed * dt

            self.aix = max(8.5, min(14.5, self.aix))
            self.aiy = max(1.0, min(14.0, self.aiy))

            dx = self.disc_x - self.aix
            dy = self.disc_y - self.aiy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 1.1 and self.disc_held_by == 0 and self.disc_vx > 0.0:
                self.disc_held_by = 2
                self.disc_hold_timer = 0.8
                self.disc_vx = 0.0
                self.disc_vy = 0.0
                self.ai_charge = 0.2

    def update_disc(self, dt: float):
        if self.disc_held_by != 0:
            return

        self.disc_x += self.disc_vx * dt
        self.disc_y += self.disc_vy * dt

        if self.disc_y <= 0.5:
            self.disc_y = 0.5
            self.disc_vy = abs(self.disc_vy)
        elif self.disc_y >= 14.5:
            self.disc_y = 14.5
            self.disc_vy = -abs(self.disc_vy)

    def check_goals(self):
        if self.disc_held_by != 0:
            return

        if self.disc_x <= 0.0:
            pts = 5 if (5.0 <= self.disc_y <= 10.0) else 3
            self.ai_score += pts
            self.last_scorer = 2
            self.state = STATE_GOAL
            self.state_timer = 0.0
        elif self.disc_x >= 15.0:
            pts = 5 if (5.0 <= self.disc_y <= 10.0) else 3
            self.player_score += pts
            self.last_scorer = 1
            self.state = STATE_GOAL
            self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Court Turf
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 10, 30, 60)

        # 2. Goal lines
        for y in range(16):
            if 5 <= y <= 10:
                set_pixel(0, y, 255, 30, 30)
                set_pixel(15, y, 255, 30, 30)
            else:
                set_pixel(0, y, 255, 220, 0)
                set_pixel(15, y, 255, 220, 0)

        # 3. Center Net
        for y in range(0, 16, 2):
            set_pixel(7, y, 200, 200, 220)
            set_pixel(8, y, 200, 200, 220)

        # 4. Player
        px = int(round(self.px))
        py = int(round(self.py))
        if self.p_dash_timer > 0.0:
            set_pixel(px, py, 100, 200, 255)
            set_pixel(px - 1, py, 40, 100, 200)
        else:
            set_pixel(px, py, 30, 140, 255)
            set_pixel(px, py - 1, 255, 200, 140)
            if self.player_charge >= 0.9:
                set_pixel(px, py + 1, 255, 180, 0)

        # 5. AI
        ax = int(round(self.aix))
        ay = int(round(self.aiy))
        set_pixel(ax, ay, 255, 50, 60)
        set_pixel(ax, ay - 1, 255, 200, 140)
        if self.ai_charge >= 0.9:
            set_pixel(ax, ay + 1, 255, 100, 0)

        # 6. Disc
        dx = int(round(self.disc_x))
        dy = int(round(self.disc_y))
        if self.disc_is_super:
            set_pixel(dx, dy, 255, 255, 255)
            set_pixel(dx - 1, dy, 255, 120, 0)
            set_pixel(dx + 1, dy, 255, 200, 0)
        else:
            set_pixel(dx, dy, 255, 255, 80)

        # 7. Score HUD
        p_bars = min(7, self.player_score)
        for i in range(p_bars):
            set_pixel(i, 0, 50, 180, 255)
        a_bars = min(7, self.ai_score)
        for i in range(a_bars):
            set_pixel(15 - i, 0, 255, 60, 60)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "player_score": self.player_score,
            "ai_score": self.ai_score,
            "match_timer": self.match_timer,
            "px": self.px,
            "py": self.py,
            "aix": self.aix,
            "aiy": self.aiy,
            "disc_x": self.disc_x,
            "disc_y": self.disc_y,
            "disc_held_by": self.disc_held_by,
            "player_charge": self.player_charge,
            "is_super": self.disc_is_super,
        }
