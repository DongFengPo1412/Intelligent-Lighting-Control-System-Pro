"""
Game #036: 导弹防线 (Missile Command 1980 / Atari)
Anti-Ballistic Defense with Expanding Flak Fireball AOE Blast, Base Silos & City Defense.
"""

import math
import random
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

STATE_START = 0
STATE_PLAYING = 1
STATE_WAVE_CLEAR = 2
STATE_GAMEOVER = 3

CITY_X = [2, 4, 5, 9, 10, 12]
BASE_X = [0, 7, 15]


class Game036MissileCommand(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.wave = 1
        self.ammo = 15
        self.enemy_spawn_remaining = 10
        self.spawn_timer = 0.0
        self.crosshair_x = 7.5
        self.crosshair_y = 7.5

        self.cities_alive = [True] * 6
        self.enemy_missiles: List[Dict[str, Any]] = []
        self.interceptors: List[Dict[str, Any]] = []
        self.explosions: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 36

    @property
    def name(self) -> str:
        return "导弹防线"

    @property
    def english_name(self) -> str:
        return "Missile Command 1980"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "空对地弹道拦截 + 范围扩散火球爆风破片 + 基地弹药管理与城市保卫"

    def init(self) -> None:
        self.reset()

    def get_surviving_cities(self) -> int:
        return sum(1 for c in self.cities_alive if c)

    def init_wave(self):
        self.ammo = 15
        self.enemy_spawn_remaining = 8 + self.wave * 2
        self.spawn_timer = 0.5
        self.enemy_missiles.clear()
        self.interceptors.clear()
        self.explosions.clear()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.wave = 1
        self.crosshair_x = 7.5
        self.crosshair_y = 7.5
        self.cities_alive = [True] * 6
        self.init_wave()

    def spawn_enemy_missile(self):
        if self.enemy_spawn_remaining <= 0:
            return

        alive_cities = [CITY_X[i] for i, alive in enumerate(self.cities_alive) if alive]
        target_x = random.choice(alive_cities) if alive_cities else random.choice(BASE_X)
        target_y = 15.0

        x0 = float(random.randint(1, 14))
        y0 = 0.0

        dx = target_x - x0
        dy = target_y - y0
        dist = max(0.1, math.sqrt(dx * dx + dy * dy))
        speed = 1.8 + self.wave * 0.25

        self.enemy_missiles.append({
            "active": True,
            "x": x0,
            "y": y0,
            "target_x": target_x,
            "target_y": target_y,
            "vx": (dx / dist) * speed,
            "vy": (dy / dist) * speed,
        })
        self.enemy_spawn_remaining -= 1

    def fire_interceptor(self) -> bool:
        if self.ammo <= 0:
            return False

        self.ammo -= 1
        # Closest launch base
        best_base = min(BASE_X, key=lambda b: abs(self.crosshair_x - b))
        x0 = float(best_base)
        y0 = 15.0

        dx = self.crosshair_x - x0
        dy = self.crosshair_y - y0
        dist = max(0.1, math.sqrt(dx * dx + dy * dy))
        speed = 18.0

        self.interceptors.append({
            "active": True,
            "x": x0,
            "y": y0,
            "target_x": self.crosshair_x,
            "target_y": self.crosshair_y,
            "vx": (dx / dist) * speed,
            "vy": (dy / dist) * speed,
        })
        return True

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_GAMEOVER:
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_WAVE_CLEAR:
            if self.state_timer >= 1.5:
                self.wave += 1
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_wave()
            return

        speed = 12.0
        if buttons & KEY_LEFT:
            self.crosshair_x = max(0.5, self.crosshair_x - speed * dt)
        if buttons & KEY_RIGHT:
            self.crosshair_x = min(14.5, self.crosshair_x + speed * dt)
        if buttons & KEY_UP:
            self.crosshair_y = max(1.0, self.crosshair_y - speed * dt)
        if buttons & KEY_DOWN:
            self.crosshair_y = min(14.0, self.crosshair_y + speed * dt)

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_interceptor()

        self.update_enemy_missiles(dt)
        self.update_interceptors(dt)
        self.update_explosions(dt)
        self.check_wave_end()

    def update_enemy_missiles(self, dt: float):
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn_timer = max(0.4, 1.2 - self.wave * 0.1)
            self.spawn_enemy_missile()

        for m in self.enemy_missiles:
            if not m["active"]:
                continue
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt

            if m["y"] >= 15.0:
                m["active"] = False
                for c, cx in enumerate(CITY_X):
                    if self.cities_alive[c] and abs(m["x"] - cx) <= 1.0:
                        self.cities_alive[c] = False
                        break

                if self.get_surviving_cities() == 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0

        self.enemy_missiles = [m for m in self.enemy_missiles if m["active"]]

    def update_interceptors(self, dt: float):
        for ic in self.interceptors:
            if not ic["active"]:
                continue
            ic["x"] += ic["vx"] * dt
            ic["y"] += ic["vy"] * dt

            dx = ic["target_x"] - ic["x"]
            dy = ic["target_y"] - ic["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= 0.8 or ic["y"] <= ic["target_y"]:
                ic["active"] = False
                self.explosions.append({
                    "active": True,
                    "x": ic["target_x"],
                    "y": ic["target_y"],
                    "radius": 0.5,
                    "max_radius": 2.0,
                    "timer": 0.6,
                })

        self.interceptors = [ic for ic in self.interceptors if ic["active"]]

    def update_explosions(self, dt: float):
        for ex in self.explosions:
            if not ex["active"]:
                continue
            ex["timer"] -= dt
            if ex["timer"] <= 0.0:
                ex["active"] = False
                continue

            if ex["timer"] > 0.3:
                ex["radius"] = min(ex["max_radius"], ex["radius"] + 6.0 * dt)
            else:
                ex["radius"] = max(0.3, ex["radius"] - 4.0 * dt)

            for m in self.enemy_missiles:
                if m["active"]:
                    dist = math.sqrt((m["x"] - ex["x"]) ** 2 + (m["y"] - ex["y"]) ** 2)
                    if dist <= ex["radius"]:
                        m["active"] = False
                        self.score += 100
                        if self.score > self.high_score:
                            self.high_score = self.score

        self.explosions = [ex for ex in self.explosions if ex["active"]]
        self.enemy_missiles = [m for m in self.enemy_missiles if m["active"]]

    def check_wave_end(self):
        if self.enemy_spawn_remaining <= 0 and len(self.enemy_missiles) == 0:
            self.state = STATE_WAVE_CLEAR
            self.state_timer = 0.0
            self.score += self.get_surviving_cities() * 100 + self.ammo * 5
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray([5, 8, 16] * 256)

        # Ground
        for x in range(16):
            idx = (15 * 16 + x) * 3
            fb[idx:idx + 3] = bytes([180, 130, 70])

        # Bases
        for bx in BASE_X:
            idx = (15 * 16 + bx) * 3
            fb[idx:idx + 3] = bytes([52, 152, 219])
            if self.ammo > 0:
                top_idx = (14 * 16 + bx) * 3
                fb[top_idx:top_idx + 3] = bytes([236, 240, 241])

        # Cities
        for c, cx in enumerate(CITY_X):
            if self.cities_alive[c]:
                idx = (15 * 16 + cx) * 3
                fb[idx:idx + 3] = bytes([46, 204, 113])

        # Enemy Missiles
        for m in self.enemy_missiles:
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            if 0 <= mx < 16 and 0 <= my < 16:
                idx = (my * 16 + mx) * 3
                fb[idx:idx + 3] = bytes([231, 76, 60])

        # Interceptors
        for ic in self.interceptors:
            ix = int(round(ic["x"]))
            iy = int(round(ic["y"]))
            if 0 <= ix < 16 and 0 <= iy < 16:
                idx = (iy * 16 + ix) * 3
                fb[idx:idx + 3] = bytes([255, 255, 255])

        # Explosions
        for ex in self.explosions:
            ex_x = int(round(ex["x"]))
            ex_y = int(round(ex["y"]))
            r = int(round(ex["radius"]))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        px = ex_x + dx
                        py = ex_y + dy
                        if 0 <= px < 16 and 0 <= py < 16:
                            idx = (py * 16 + px) * 3
                            fb[idx:idx + 3] = bytes([241, 196, 15])

        # Crosshair
        hx = int(round(self.crosshair_x))
        hy = int(round(self.crosshair_y))
        if 0 <= hx < 16 and 0 <= hy < 16:
            fb[(hy * 16 + hx) * 3:(hy * 16 + hx) * 3 + 3] = bytes([46, 204, 113])
            if hx > 0:
                fb[(hy * 16 + (hx - 1)) * 3:(hy * 16 + (hx - 1)) * 3 + 3] = bytes([46, 204, 113])
            if hx < 15:
                fb[(hy * 16 + (hx + 1)) * 3:(hy * 16 + (hx + 1)) * 3 + 3] = bytes([46, 204, 113])
            if hy > 0:
                fb[((hy - 1) * 16 + hx) * 3:((hy - 1) * 16 + hx) * 3 + 3] = bytes([46, 204, 113])
            if hy < 15:
                fb[((hy + 1) * 16 + hx) * 3:((hy + 1) * 16 + hx) * 3 + 3] = bytes([46, 204, 113])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "wave": self.wave,
            "ammo": self.ammo,
            "surviving_cities": self.get_surviving_cities(),
            "crosshair": (self.crosshair_x, self.crosshair_y),
            "enemy_count": len(self.enemy_missiles),
        }
