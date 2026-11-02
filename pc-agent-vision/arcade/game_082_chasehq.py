"""
Game #082: 烈火特警 / 追捕HQ (Chase H.Q. 1988 / Taito)
High-Speed Police Interceptor, Nitro Turbo Boosts, Suspect Ramming & Vehicle Apprehension.
"""

from typing import List, Dict, Any
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

STATE_APPROACH = 0
STATE_PURSUIT = 1
STATE_ARRESTED = 2
STATE_TIME_UP = 3

MAX_TRAFFIC = 3


class Game082ChaseHQ(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_APPROACH
        self.state_timer = 0.0
        self.time_remaining = 45.0
        self.score = 0
        self.high_score = 20000
        self.turbos_left = 3
        self.turbo_timer = 0.0
        self.suspect_damage = 0.0
        self.distance_to_suspect = 100.0

        # Player Police Cruiser
        self.px = 7.5
        self.py = 13.0
        self.p_speed = 11.0

        # Suspect Car
        self.sx = 7.5
        self.sy = 6.0
        self.s_speed = 9.0
        self.s_swerve_timer = 0.0

        self.traffic: List[Dict[str, Any]] = []
        self.road_scroll = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 82

    @property
    def name(self) -> str:
        return "烈火特警"

    @property
    def english_name(self) -> str:
        return "Chase H.Q."

    @property
    def release_year(self) -> int:
        return 1988

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "警车氮气极速追击 + 连续猛烈撞击截停罪犯跑车"

    def get_name(self) -> str:
        return "Chase H.Q. (1988)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_APPROACH
        self.state_timer = 0.0
        self.time_remaining = 45.0
        self.score = 0
        self.turbos_left = 3
        self.turbo_timer = 0.0
        self.suspect_damage = 0.0
        self.distance_to_suspect = 100.0
        self.reset_mission()

    def reset_mission(self):
        self.px = 7.5
        self.py = 13.0
        self.p_speed = 11.0

        self.sx = 7.5
        self.sy = 6.0
        self.s_speed = 9.0
        self.s_swerve_timer = 0.0

        self.traffic = []
        self.road_scroll = 0.0

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_ARRESTED, STATE_TIME_UP):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.time_remaining = max(0.0, self.time_remaining - dt)
        if self.time_remaining <= 0.0:
            self.state = STATE_TIME_UP
            self.state_timer = 0.0
            return

        self.update_player(dt, buttons, prev_buttons)

        if self.state == STATE_APPROACH:
            self.distance_to_suspect -= (self.p_speed - 8.0) * dt * 2.0
            self.score += int(self.p_speed * dt * 5.0)

            if self.distance_to_suspect <= 0.0:
                self.state = STATE_PURSUIT
                self.state_timer = 0.0
                self.time_remaining += 25.0
                self.score += 2000
        elif self.state == STATE_PURSUIT:
            self.update_suspect(dt)
            self.check_ramming()

        self.update_traffic(dt)
        self.road_scroll += self.p_speed * dt

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        steer_speed = 7.5
        if buttons & KEY_LEFT:
            self.px -= steer_speed * dt
        if buttons & KEY_RIGHT:
            self.px += steer_speed * dt

        self.px = max(2.0, min(13.0, self.px))

        # Turbo Boost (B)
        if self.turbo_timer > 0.0:
            self.turbo_timer -= dt
            self.p_speed = 20.0
        else:
            if (buttons & KEY_B) and not (prev_buttons & KEY_B) and self.turbos_left > 0:
                self.turbos_left -= 1
                self.turbo_timer = 2.5
                self.p_speed = 20.0
            elif buttons & KEY_A:
                self.p_speed = 12.0
            else:
                self.p_speed = 9.0

    def update_suspect(self, dt: float):
        self.s_swerve_timer += dt
        if self.s_swerve_timer > 0.8:
            self.s_swerve_timer = 0.0
            import random
            target_dir = -1.0 if random.choice([True, False]) else 1.0
            self.sx += target_dir * 1.5
            self.sx = max(3.0, min(12.0, self.sx))

        speed_diff = self.p_speed - self.s_speed
        self.sy += speed_diff * 0.1 * dt
        self.sy = max(5.0, min(10.0, self.sy))

    def check_ramming(self):
        dx = abs(self.px - self.sx)
        dy = abs(self.py - self.sy)

        if dx < 1.6 and dy < 1.6:
            dmg = 25.0 if self.turbo_timer > 0.0 else 15.0
            self.suspect_damage = min(100.0, self.suspect_damage + dmg)
            self.score += int(dmg * 100.0)

            if self.px < self.sx:
                self.px -= 0.6
                self.sx += 0.6
            else:
                self.px += 0.6
                self.sx -= 0.6

            if self.suspect_damage >= 100.0:
                self.state = STATE_ARRESTED
                self.state_timer = 0.0
                self.score += 10000

    def update_traffic(self, dt: float):
        for t in self.traffic:
            if not t["active"]:
                continue
            t["y"] += (self.p_speed - t["speed"]) * 0.6 * dt
            if abs(t["x"] - self.px) < 1.4 and abs(t["y"] - self.py) < 1.2:
                t["active"] = False
                self.p_speed = 4.0
                self.turbo_timer = 0.0

            if t["y"] > 15.0:
                t["active"] = False

        self.traffic = [t for t in self.traffic if t["active"]]

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Sky
        for y in range(4):
            for x in range(16):
                set_pixel(x, y, 10, 20, 40)

        # 2. Highway
        for y in range(4, 16):
            for x in range(16):
                set_pixel(x, y, 50, 50, 55)

        # 3. Curbs
        scroll_offset = int(self.road_scroll) % 4
        for y in range(4, 16):
            stripe = ((y + scroll_offset) % 4 < 2)
            set_pixel(0, y, 255 if stripe else 20, 30 if stripe else 120, 20)
            set_pixel(1, y, 255 if stripe else 20, 30 if stripe else 120, 20)
            set_pixel(14, y, 255 if stripe else 20, 30 if stripe else 120, 20)
            set_pixel(15, y, 255 if stripe else 20, 30 if stripe else 120, 20)
            if stripe:
                set_pixel(7, y, 255, 255, 100)
                set_pixel(8, y, 255, 255, 100)

        # 4. Traffic
        for t in self.traffic:
            if not t["active"]:
                continue
            tx = int(round(t["x"]))
            ty = int(round(t["y"]))
            set_pixel(tx, ty, 200, 200, 200)
            set_pixel(tx, ty - 1, 150, 150, 160)
            set_pixel(tx - 1, ty, 255, 30, 30)
            set_pixel(tx + 1, ty, 255, 30, 30)

        # 5. Suspect
        if self.state in (STATE_PURSUIT, STATE_ARRESTED):
            sx = int(round(self.sx))
            sy = int(round(self.sy))
            set_pixel(sx, sy, 220, 30, 30)
            set_pixel(sx, sy - 1, 20, 20, 20)
            set_pixel(sx - 1, sy, 255, 50, 50)
            set_pixel(sx + 1, sy, 255, 50, 50)
            if self.state == STATE_ARRESTED or self.suspect_damage > 60.0:
                set_pixel(sx, sy - 2, 80, 80, 80)
                set_pixel(sx + 1, sy - 2, 255, 120, 0)

        # 6. Police Cruiser
        px = int(round(self.px))
        py = int(round(self.py))
        set_pixel(px, py, 20, 20, 20)
        set_pixel(px, py - 1, 240, 240, 245)
        set_pixel(px - 1, py, 20, 20, 20)
        set_pixel(px + 1, py, 20, 20, 20)

        # Lightbar
        siren_flash = (int(self.state_timer * 8.0) % 2 == 0)
        set_pixel(px - 1, py - 1, 255 if siren_flash else 20, 20, 20 if siren_flash else 255)
        set_pixel(px + 1, py - 1, 20 if siren_flash else 255, 20, 255 if siren_flash else 20)

        if self.turbo_timer > 0.0:
            set_pixel(px - 1, py + 1, 255, 140, 0)
            set_pixel(px + 1, py + 1, 255, 140, 0)

        # 7. HUD
        for t in range(self.turbos_left):
            set_pixel(t * 2, 0, 255, 200, 0)

        if self.state == STATE_PURSUIT:
            dmg_bars = int((self.suspect_damage / 100.0) * 6.0)
            for d in range(dmg_bars):
                set_pixel(15 - d, 0, 255, 30, 30)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "time_remaining": self.time_remaining,
            "turbos_left": self.turbos_left,
            "suspect_damage": self.suspect_damage,
            "distance_to_suspect": self.distance_to_suspect,
            "px": self.px,
            "sx": self.sx,
        }
