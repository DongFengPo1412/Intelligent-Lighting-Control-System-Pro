"""
Game #101: 间谍猎手 (Spy Hunter 1983 / Bally Midway)
High-speed armed interceptor pursuit, weapons van rear-docking rearm,
oil slicks / smoke screens, and amphibious transformation into river speedboats.
"""

from typing import List, Dict, Any
import math
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

STATE_DRIVING = 0
STATE_WEAPONS_VAN_DOCK = 1
STATE_AMPHIBIOUS_BOATING = 2
STATE_CRASHED = 3
STATE_GAME_OVER = 4

WEAPON_NONE = 0
WEAPON_OIL_SLICK = 1
WEAPON_SMOKE_SCREEN = 2
WEAPON_MISSILE = 3

MAX_ENEMIES = 3
MAX_BULLETS = 4
MAX_HAZARDS = 3


class Game101SpyHunter(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_DRIVING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.distance_traveled = 0.0

        self.px = 8.0
        self.py = 12.0
        self.speed = 10.0
        self.current_weapon = WEAPON_NONE
        self.weapon_ammo = 0
        self.fire_cooldown = 0.0

        self.road_left = 3.0
        self.road_width = 10.0

        self.van: Dict[str, Any] = {}
        self.enemies: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []
        self.hazards: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 101

    @property
    def name(self) -> str:
        return "间谍猎手"

    @property
    def english_name(self) -> str:
        return "Spy Hunter"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "武装跑车高速追逐、货车倒车入库换装油污烟幕、水陆双栖变形快艇"

    def get_name(self) -> str:
        return "Spy Hunter (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.distance_traveled = 0.0
        self.state = STATE_DRIVING
        self.state_timer = 0.0
        self._reset_road()

    def _reset_road(self) -> None:
        self.px = 8.0
        self.py = 12.0
        self.speed = 10.0
        self.current_weapon = WEAPON_NONE
        self.weapon_ammo = 0
        self.fire_cooldown = 0.0

        self.road_left = 3.0
        self.road_width = 10.0

        self.van = {
            "x": 8.0,
            "y": -6.0,
            "speed": 9.0,
            "carrying_weapon": WEAPON_OIL_SLICK,
            "active": False,
        }

        self.bullets = [
            {"x": 0.0, "y": 0.0, "vy": -24.0, "active": False}
            for _ in range(MAX_BULLETS)
        ]
        self.hazards = [
            {"x": 0.0, "y": 0.0, "active": False}
            for _ in range(MAX_HAZARDS)
        ]

        self.enemies = [
            {
                "x": 6.0,
                "y": 2.0,
                "speed": 7.0,
                "type": 0,  # Enforcer
                "spinning": False,
                "spin_timer": 0.0,
                "active": True,
            },
            {
                "x": 10.0,
                "y": -2.0,
                "speed": 8.5,
                "type": 1,  # Tire Slasher
                "spinning": False,
                "spin_timer": 0.0,
                "active": True,
            },
            {
                "x": 8.0,
                "y": -8.0,
                "speed": 9.0,
                "type": 0,
                "spinning": False,
                "spin_timer": 0.0,
                "active": False,
            },
        ]

    def call_weapon_van(self) -> None:
        if not self.van["active"]:
            self.van["active"] = True
            self.van["x"] = self.road_left + self.road_width * 0.5
            self.van["y"] = -5.0
            self.van["speed"] = self.speed * 0.9
            self.van["carrying_weapon"] = (
                WEAPON_SMOKE_SCREEN if self.distance_traveled > 300.0 else WEAPON_OIL_SLICK
            )

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_CRASHED:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = (
                        STATE_AMPHIBIOUS_BOATING
                        if self.distance_traveled >= 500.0
                        else STATE_DRIVING
                    )
                    self.state_timer = 0.0
                    self.px = self.road_left + self.road_width * 0.5
                    self.py = 12.0
                    self.speed = 9.0
            return

        if self.state == STATE_WEAPONS_VAN_DOCK:
            self.van["y"] += (self.van["speed"] - self.speed) * dt
            self.px = self.van["x"]
            self.py = self.van["y"] + 2.5
            if self.state_timer > 1.4:
                self.current_weapon = self.van["carrying_weapon"]
                self.weapon_ammo = 3
                self.score += 500
                self.van["active"] = False
                self.state = (
                    STATE_AMPHIBIOUS_BOATING
                    if self.distance_traveled >= 500.0
                    else STATE_DRIVING
                )
                self.state_timer = 0.0
                self.speed = 12.0
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.distance_traveled += self.speed * dt
        self.score += int(self.speed * dt * 2.0)

        if self.state == STATE_DRIVING and self.distance_traveled >= 500.0:
            self.state = STATE_AMPHIBIOUS_BOATING
            self.state_timer = 0.0

        if (
            self.current_weapon == WEAPON_NONE
            and not self.van["active"]
            and (int(self.distance_traveled) % 180 < 20)
        ):
            self.call_weapon_van()

        self._update_car(dt, buttons, prev_buttons)
        self._update_van(dt)
        self._update_enemies(dt)
        self._update_bullets_and_hazards(dt)
        self._check_collisions()

    def _update_car(self, dt: float, buttons: int, prev_buttons: int) -> None:
        steer_speed = 8.5 if self.state == STATE_AMPHIBIOUS_BOATING else 10.0
        if buttons & KEY_LEFT:
            self.px -= steer_speed * dt
        if buttons & KEY_RIGHT:
            self.px += steer_speed * dt

        if buttons & KEY_UP:
            self.speed = min(18.0, self.speed + 8.0 * dt)
        elif buttons & KEY_DOWN:
            self.speed = max(6.0, self.speed - 12.0 * dt)
        else:
            if self.speed < 10.0:
                self.speed += 2.0 * dt
            elif self.speed > 10.0:
                self.speed -= 2.0 * dt

        curve = math.sin(self.distance_traveled * 0.02) * 1.5
        self.road_left = max(1.0, min(6.0, 3.0 + curve))

        if self.px < self.road_left or self.px > self.road_left + self.road_width - 1.0:
            self.state = STATE_CRASHED
            self.state_timer = 0.0
            return

        self.fire_cooldown -= dt
        if (buttons & KEY_A) and self.fire_cooldown <= 0.0:
            self.fire_cooldown = 0.2
            for b in self.bullets:
                if not b["active"]:
                    b["active"] = True
                    b["x"] = self.px
                    b["y"] = self.py - 1.2
                    b["vy"] = -24.0
                    break

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.current_weapon != WEAPON_NONE and self.weapon_ammo > 0:
                self.weapon_ammo -= 1
                for h in self.hazards:
                    if not h["active"]:
                        h["active"] = True
                        h["x"] = self.px
                        h["y"] = self.py + 1.2
                        break
                if self.weapon_ammo <= 0:
                    self.current_weapon = WEAPON_NONE
            elif not self.van["active"]:
                self.call_weapon_van()

    def _update_van(self, dt: float) -> None:
        if not self.van["active"]:
            return

        rel_speed = self.van["speed"] - self.speed
        self.van["y"] += rel_speed * dt

        if self.state in (STATE_DRIVING, STATE_AMPHIBIOUS_BOATING):
            dx = abs(self.px - self.van["x"])
            dy = self.py - (self.van["y"] + 2.8)
            if dx < 1.0 and abs(dy) < 0.6:
                self.state = STATE_WEAPONS_VAN_DOCK
                self.state_timer = 0.0

        if self.van["y"] > 18.0 or self.van["y"] < -12.0:
            self.van["active"] = False

    def _update_enemies(self, dt: float) -> None:
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                e["active"] = True
                e["x"] = self.road_left + 1.0 + float(i * 3)
                e["y"] = -4.0
                e["speed"] = 7.0 + float(i * 1.5)
                e["type"] = 2 if (self.state == STATE_AMPHIBIOUS_BOATING) else (i % 2)
                e["spinning"] = False
                continue

            if e["spinning"]:
                e["spin_timer"] -= dt
                e["x"] += (3.0 if i % 2 == 0 else -3.0) * dt
                e["y"] += (e["speed"] - self.speed) * dt
                if (
                    e["spin_timer"] <= 0.0
                    or e["x"] < self.road_left
                    or e["x"] > self.road_left + self.road_width
                ):
                    e["active"] = False
                    self.score += 300
                continue

            rel_spd = e["speed"] - self.speed
            e["y"] += rel_spd * dt

            if e["type"] == 1:
                if e["x"] < self.px:
                    e["x"] += 2.0 * dt
                elif e["x"] > self.px:
                    e["x"] -= 2.0 * dt

            if e["y"] > 18.0 or e["y"] < -8.0:
                e["active"] = False

    def _update_bullets_and_hazards(self, dt: float) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue
            b["y"] += b["vy"] * dt
            if b["y"] < -2.0:
                b["active"] = False

        for h in self.hazards:
            if not h["active"]:
                continue
            h["y"] -= self.speed * dt
            if h["y"] > 18.0:
                h["active"] = False

    def _check_collisions(self) -> None:
        # 1. Bullets vs Enemies
        for b in self.bullets:
            if not b["active"]:
                continue
            for e in self.enemies:
                if not e["active"] or e["spinning"]:
                    continue
                dx = abs(b["x"] - e["x"])
                dy = abs(b["y"] - e["y"])
                if dx < 1.2 and dy < 1.4:
                    b["active"] = False
                    if e["type"] == 0:
                        self.score += 50
                    else:
                        e["active"] = False
                        self.score += 200
                    break

        # 2. Hazards vs Enemies
        for h in self.hazards:
            if not h["active"]:
                continue
            for e in self.enemies:
                if not e["active"] or e["spinning"]:
                    continue
                dx = abs(h["x"] - e["x"])
                dy = abs(h["y"] - e["y"])
                if dx < 1.3 and dy < 1.3:
                    e["spinning"] = True
                    e["spin_timer"] = 1.0
                    self.score += 150

        # 3. Enemy vs Player Car
        for e in self.enemies:
            if not e["active"] or e["spinning"]:
                continue
            dx = abs(self.px - e["x"])
            dy = abs(self.py - e["y"])
            if dx < 1.1 and dy < 1.3:
                if e["type"] == 1:
                    self.state = STATE_CRASHED
                    self.state_timer = 0.0
                    return
                else:
                    if self.px < e["x"]:
                        self.px -= 0.8
                    else:
                        self.px += 0.8

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(len(fb)):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        is_water = self.state == STATE_AMPHIBIOUS_BOATING

        for y in range(16):
            r_left = int(round(self.road_left))
            r_right = int(round(self.road_left + self.road_width))
            for x in range(16):
                if x < r_left or x >= r_right:
                    if is_water:
                        set_pixel(x, y, 40, 80, 30)
                    else:
                        set_pixel(x, y, 30, 100, 20)
                else:
                    if is_water:
                        wave = 60 if ((y + int(self.distance_traveled * 0.5)) % 4 == 0) else 30
                        set_pixel(x, y, 10, wave, 140)
                    else:
                        set_pixel(x, y, 50, 50, 55)
                        if x == r_left + int(self.road_width * 0.5):
                            if (y + int(self.distance_traveled * 0.5)) % 4 < 2:
                                set_pixel(x, y, 220, 220, 200)

        for h in self.hazards:
            if not h["active"]:
                continue
            hx = int(round(h["x"]))
            hy = int(round(h["y"]))
            set_pixel(hx, hy, 20, 20, 20)
            set_pixel(hx + 1, hy, 40, 30, 10)

        if self.van["active"]:
            vx = int(round(self.van["x"]))
            vy = int(round(self.van["y"]))
            set_pixel(vx, vy, 220, 40, 30)
            set_pixel(vx + 1, vy, 220, 40, 30)
            set_pixel(vx, vy + 1, 240, 240, 240)
            set_pixel(vx + 1, vy + 1, 240, 240, 240)
            set_pixel(vx, vy + 2, 220, 40, 30)
            set_pixel(vx + 1, vy + 2, 220, 40, 30)
            set_pixel(vx, vy - 1, 255, 200, 0)

        for b in self.bullets:
            if not b["active"]:
                continue
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 120)

        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["spinning"]:
                set_pixel(ex, ey, 255, 120, 0)
                set_pixel(ex + 1, ey, 255, 60, 0)
            elif e["type"] == 0:
                set_pixel(ex, ey, 40, 60, 200)
                set_pixel(ex, ey - 1, 30, 40, 150)
                set_pixel(ex, ey + 1, 20, 30, 100)
            elif e["type"] == 1:
                set_pixel(ex, ey, 240, 100, 20)
                set_pixel(ex - 1, ey, 255, 255, 255)
                set_pixel(ex + 1, ey, 255, 255, 255)
            else:
                set_pixel(ex, ey, 180, 40, 180)
                set_pixel(ex, ey - 1, 220, 80, 220)

        px_i = int(round(self.px))
        py_i = int(round(self.py))

        if self.state == STATE_CRASHED:
            set_pixel(px_i, py_i, 255, 60, 20)
            set_pixel(px_i - 1, py_i, 255, 180, 0)
            set_pixel(px_i + 1, py_i, 255, 180, 0)
            set_pixel(px_i, py_i - 1, 255, 220, 0)
        else:
            if is_water:
                set_pixel(px_i, py_i, 250, 250, 255)
                set_pixel(px_i, py_i - 1, 40, 180, 255)
                set_pixel(px_i - 1, py_i + 1, 200, 240, 255)
                set_pixel(px_i + 1, py_i + 1, 200, 240, 255)
            else:
                set_pixel(px_i, py_i, 240, 240, 250)
                set_pixel(px_i, py_i - 1, 255, 255, 255)
                set_pixel(px_i, py_i + 1, 220, 20, 20)
                set_pixel(px_i - 1, py_i, 40, 40, 40)
                set_pixel(px_i + 1, py_i, 40, 40, 40)

        if self.weapon_ammo > 0:
            for a in range(self.weapon_ammo):
                set_pixel(a, 15, 255, 200, 0)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 255, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "px": self.px,
            "speed": self.speed,
            "current_weapon": self.current_weapon,
            "weapon_ammo": self.weapon_ammo,
            "distance_traveled": self.distance_traveled,
            "van_active": self.van["active"],
        }
