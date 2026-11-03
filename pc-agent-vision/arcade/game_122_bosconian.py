"""
Game #122: 宇宙巡航者 (Bosconian 1981 / Namco)
The pioneering free-roaming space shooter:
simultaneous front-and-rear twin cannons, 360-degree radar homing,
hexagonal space station nuclear core penetration, and spy ship Alert Condition Red.
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

STATE_FLYING = 0
STATE_PLAYER_EXPLODING = 1
STATE_SECTOR_CLEAR = 2
STATE_GAME_OVER = 3

ALERT_GREEN = 0
ALERT_YELLOW = 1
ALERT_RED = 2

WORLD_SIZE = 48.0
MAX_STATIONS = 3
MAX_BULLETS = 6
MAX_INTERCEPTORS = 4


def wrap_coord(val: float, max_val: float = WORLD_SIZE) -> float:
    while val < 0.0:
        val += max_val
    while val >= max_val:
        val -= max_val
    return val


def wrap_diff(a: float, b: float, max_val: float = WORLD_SIZE) -> float:
    diff = a - b
    while diff > max_val * 0.5:
        diff -= max_val
    while diff < -max_val * 0.5:
        diff += max_val
    return diff


class Game122Bosconian(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.alert = ALERT_GREEN
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1

        self.px = 24.0
        self.py = 24.0
        self.vx = 0.0
        self.vy = -5.0
        self.dir_x = 0
        self.dir_y = -1

        self.stations: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []
        self.interceptors: List[Dict[str, Any]] = []
        self.spawn_timer = 1.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 122

    @property
    def name(self) -> str:
        return "宇宙巡航者"

    @property
    def english_name(self) -> str:
        return "Bosconian"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "前后双向火炮齐射、360度全景雷达制导、六角太空战站核心穿透与红色警戒"

    def get_name(self) -> str:
        return "Bosconian (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._init_sector()

    def _init_sector(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.alert = ALERT_GREEN
        self.spawn_timer = 1.0

        self.px = 24.0
        self.py = 24.0
        self.vx = 0.0
        self.vy = -5.0
        self.dir_x = 0
        self.dir_y = -1

        station_coords = [
            (12.0, 12.0),
            (36.0, 12.0),
            (24.0, 36.0),
        ]
        self.stations = []
        for i in range(MAX_STATIONS):
            self.stations.append({
                "x": station_coords[i][0],
                "y": station_coords[i][1],
                "core_alive": True,
                "pods_alive": [True] * 6,
                "active": True,
            })

        self.bullets = []
        for _ in range(MAX_BULLETS):
            self.bullets.append({
                "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "life": 0.0, "active": False
            })

        self.interceptors = []
        for _ in range(MAX_INTERCEPTORS):
            self.interceptors.append({
                "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "is_spy": False, "active": False
            })

    def fire_twin_cannons(self) -> None:
        if self.state != STATE_FLYING:
            return

        # Forward
        for b in self.bullets:
            if not b["active"]:
                b["x"] = wrap_coord(self.px + float(self.dir_x) * 1.0)
                b["y"] = wrap_coord(self.py + float(self.dir_y) * 1.0)
                b["vx"] = float(self.dir_x) * 22.0
                b["vy"] = float(self.dir_y) * 22.0
                b["life"] = 0.8
                b["active"] = True
                break

        # Backward (Simultaneous twin cannons)
        for b in self.bullets:
            if not b["active"]:
                b["x"] = wrap_coord(self.px - float(self.dir_x) * 1.0)
                b["y"] = wrap_coord(self.py - float(self.dir_y) * 1.0)
                b["vx"] = -float(self.dir_x) * 22.0
                b["vy"] = -float(self.dir_y) * 22.0
                b["life"] = 0.8
                b["active"] = True
                break

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PLAYER_EXPLODING:
            if self.state_timer > 1.2:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_FLYING
                    self.px = 24.0
                    self.py = 24.0
                    self.vx = 0.0
                    self.vy = -5.0
                    self.dir_x = 0
                    self.dir_y = -1
            return

        if self.state == STATE_SECTOR_CLEAR:
            if self.state_timer > 1.6:
                self.round += 1
                self.score += 2000
                self._init_sector()
            return

        if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
            self.fire_twin_cannons()

        self._update_ship(dt, buttons)
        self._update_stations(dt)
        self._update_interceptors(dt)
        self._update_bullets(dt)
        self._check_collisions()
        self._check_sector_clear()

    def _update_ship(self, dt: float, buttons: int) -> None:
        in_x = 0
        in_y = 0
        if buttons & KEY_LEFT:
            in_x -= 1
        if buttons & KEY_RIGHT:
            in_x += 1
        if buttons & KEY_UP:
            in_y -= 1
        if buttons & KEY_DOWN:
            in_y += 1

        if in_x != 0 or in_y != 0:
            self.dir_x = in_x
            self.dir_y = in_y

        cruise_speed = 6.0
        length = math.sqrt(float(self.dir_x * self.dir_x + self.dir_y * self.dir_y))
        if length > 0.0:
            self.vx = (float(self.dir_x) / length) * cruise_speed
            self.vy = (float(self.dir_y) / length) * cruise_speed

        self.px = wrap_coord(self.px + self.vx * dt)
        self.py = wrap_coord(self.py + self.vy * dt)

    def _update_stations(self, dt: float) -> None:
        for s in self.stations:
            if not s["active"]:
                continue

            any_pod = any(s["pods_alive"])
            if not any_pod or not s["core_alive"]:
                s["active"] = False
                self.score += 1500 if (not s["core_alive"]) else 800

    def _update_interceptors(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn_timer = 1.5 if (self.alert == ALERT_RED) else 3.5

            for i, enemy in enumerate(self.interceptors):
                if not enemy["active"]:
                    enemy["x"] = wrap_coord(self.px + (14.0 if (i % 2 == 0) else -14.0))
                    enemy["y"] = wrap_coord(self.py + (14.0 if (i > 1) else -14.0))
                    enemy["is_spy"] = (i == 0 and self.alert != ALERT_RED)
                    enemy["active"] = True
                    break

        for enemy in self.interceptors:
            if not enemy["active"]:
                continue

            dx = wrap_diff(self.px, enemy["x"])
            dy = wrap_diff(self.py, enemy["y"])
            dist = math.sqrt(dx * dx + dy * dy)

            if enemy["is_spy"]:
                enemy["vx"] = -4.5 if (dx > 0) else 4.5
                enemy["vy"] = -4.5 if (dy > 0) else 4.5
                if dist > 18.0:
                    self.alert = ALERT_RED
                    enemy["active"] = False
            else:
                if dist > 0.5:
                    spd = 5.2 if (self.alert == ALERT_RED) else 3.8
                    enemy["vx"] = (dx / dist) * spd
                    enemy["vy"] = (dy / dist) * spd

            enemy["x"] = wrap_coord(enemy["x"] + enemy["vx"] * dt)
            enemy["y"] = wrap_coord(enemy["y"] + enemy["vy"] * dt)

    def _update_bullets(self, dt: float) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue
            b["life"] -= dt
            if b["life"] <= 0.0:
                b["active"] = False
                continue
            b["x"] = wrap_coord(b["x"] + b["vx"] * dt)
            b["y"] = wrap_coord(b["y"] + b["vy"] * dt)

    def _check_collisions(self) -> None:
        # Bullets vs Stations & Interceptors
        pod_offsets = [
            (0.0, -1.8), (1.5, -0.9), (1.5, 0.9),
            (0.0, 1.8), (-1.5, 0.9), (-1.5, -0.9)
        ]

        for b in self.bullets:
            if not b["active"]:
                continue

            for s in self.stations:
                if not s["active"]:
                    continue

                cdx = abs(wrap_diff(b["x"], s["x"]))
                cdy = abs(wrap_diff(b["y"], s["y"]))
                if cdx < 0.9 and cdy < 0.9 and s["core_alive"]:
                    b["active"] = False
                    s["core_alive"] = False
                    break

                for p in range(6):
                    if not s["pods_alive"][p]:
                        continue
                    px_pos = s["x"] + pod_offsets[p][0]
                    py_pos = s["y"] + pod_offsets[p][1]
                    pdx = abs(wrap_diff(b["x"], px_pos))
                    pdy = abs(wrap_diff(b["y"], py_pos))
                    if pdx < 0.8 and pdy < 0.8:
                        b["active"] = False
                        s["pods_alive"][p] = False
                        self.score += 100
                        break

            for enemy in self.interceptors:
                if not enemy["active"]:
                    continue
                dx = abs(wrap_diff(b["x"], enemy["x"]))
                dy = abs(wrap_diff(b["y"], enemy["y"]))
                if dx < 0.9 and dy < 0.9:
                    b["active"] = False
                    enemy["active"] = False
                    self.score += 300 if enemy["is_spy"] else 100
                    break

        # Player vs Interceptors
        for enemy in self.interceptors:
            if not enemy["active"]:
                continue
            dx = abs(wrap_diff(self.px, enemy["x"]))
            dy = abs(wrap_diff(self.py, enemy["y"]))
            if dx < 0.8 and dy < 0.8:
                self.state = STATE_PLAYER_EXPLODING
                self.state_timer = 0.0
                enemy["active"] = False
                break

        # Player vs Station
        for s in self.stations:
            if not s["active"]:
                continue
            dx = abs(wrap_diff(self.px, s["x"]))
            dy = abs(wrap_diff(self.py, s["y"]))
            if dx < 1.4 and dy < 1.4:
                self.state = STATE_PLAYER_EXPLODING
                self.state_timer = 0.0
                break

    def _check_sector_clear(self) -> None:
        if not any(s["active"] for s in self.stations):
            self.state = STATE_SECTOR_CLEAR
            self.state_timer = 0.0

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        elif len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Radar
        for rx in range(16):
            set_pixel(rx, 0, 10, 20, 40)
        for s in self.stations:
            if s["active"]:
                rx = int(s["x"] / WORLD_SIZE * 16.0)
                set_pixel(rx, 0, 0, 255, 120)
        r_px = int(self.px / WORLD_SIZE * 16.0)
        set_pixel(r_px, 0, 255, 255, 255)

        if self.alert == ALERT_RED:
            set_pixel(15, 0, 255, 30, 20)
        elif self.alert == ALERT_YELLOW:
            set_pixel(15, 0, 255, 220, 0)

        # 2. Stations
        pod_offsets = [
            (0.0, -1.8), (1.5, -0.9), (1.5, 0.9),
            (0.0, 1.8), (-1.5, 0.9), (-1.5, -0.9)
        ]
        for s in self.stations:
            if not s["active"]:
                continue
            scx = wrap_diff(s["x"], self.px) + 7.5
            scy = wrap_diff(s["y"], self.py) + 7.5

            iscx = int(round(scx))
            iscy = int(round(scy))
            if s["core_alive"] and 0 <= iscx < 16 and 1 <= iscy < 16:
                set_pixel(iscx, iscy, 255, 220, 0)

            for p in range(6):
                if not s["pods_alive"][p]:
                    continue
                px_screen = int(round(scx + pod_offsets[p][0]))
                py_screen = int(round(scy + pod_offsets[p][1]))
                if 0 <= px_screen < 16 and 1 <= py_screen < 16:
                    set_pixel(px_screen, py_screen, 40, 180, 240)

        # 3. Interceptors
        for enemy in self.interceptors:
            if not enemy["active"]:
                continue
            sx = int(round(wrap_diff(enemy["x"], self.px) + 7.5))
            sy = int(round(wrap_diff(enemy["y"], self.py) + 7.5))
            if 0 <= sx < 16 and 1 <= sy < 16:
                if enemy["is_spy"]:
                    set_pixel(sx, sy, 255, 240, 0)
                    set_pixel(sx, sy - 1, 255, 120, 0)
                else:
                    set_pixel(sx, sy, 255, 40, 20)

        # 4. Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(wrap_diff(b["x"], self.px) + 7.5))
            by = int(round(wrap_diff(b["y"], self.py) + 7.5))
            if 0 <= bx < 16 and 1 <= by < 16:
                set_pixel(bx, by, 255, 255, 255)

        # 5. Starfighter at Center (8, 8)
        if self.state in (STATE_FLYING, STATE_SECTOR_CLEAR):
            cx = 8
            cy = 8
            set_pixel(cx, cy, 255, 255, 255)
            set_pixel(cx + self.dir_x, cy + self.dir_y, 40, 140, 255)
            set_pixel(cx - self.dir_x, cy - self.dir_y, 255, 120, 20)
        elif self.state == STATE_PLAYER_EXPLODING:
            cx = 8
            cy = 8
            set_pixel(cx, cy, 255, 220, 50)
            set_pixel(cx - 1, cy - 1, 255, 60, 20)
            set_pixel(cx + 1, cy + 1, 255, 60, 20)
            set_pixel(cx + 1, cy - 1, 255, 180, 0)

        # 6. Lives
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 1, 40, 140, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "alert": self.alert,
            "score": self.score,
            "lives": self.lives,
            "px": self.px,
            "py": self.py,
            "dir_x": self.dir_x,
            "dir_y": self.dir_y,
        }
