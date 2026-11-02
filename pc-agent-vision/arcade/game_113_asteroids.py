"""
Game #113: 小行星 (Asteroids 1979 / Atari)
Newtonian zero-gravity rotational vector mechanics, 3-tier recursive asteroid splitting,
toroidal 4-edge screen wrap-around, hostile UFO flying saucer encounters,
and emergency hyperspace quantum jumps.
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

STATE_PLAYING = 0
STATE_PLAYER_EXPLODING = 1
STATE_WAVE_CLEAR = 2
STATE_GAME_OVER = 3

MAX_ASTEROIDS = 16
MAX_BULLETS = 4


def wrap_coord(val: float, max_val: float = 16.0) -> float:
    while val < 0.0:
        val += max_val
    while val >= max_val:
        val -= max_val
    return val


def wrap_diff(a: float, b: float, max_val: float = 16.0) -> float:
    diff = abs(a - b)
    if diff > max_val * 0.5:
        diff = max_val - diff
    return diff


class Game113Asteroids(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.wave = 1

        self.px = 8.0
        self.py = 8.0
        self.vx = 0.0
        self.vy = 0.0
        self.angle = -math.pi / 2.0
        self.thrusting = False

        self.asteroids: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []
        self.saucer: Dict[str, Any] = {
            "x": 0.0, "y": 3.5, "vx": 4.0, "active": False, "shoot_timer": 2.0
        }
        self.saucer_spawn_timer = 8.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 113

    @property
    def name(self) -> str:
        return "小行星"

    @property
    def english_name(self) -> str:
        return "Asteroids"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "360度牛顿惯性失重漂移、多级分裂小行星群、飞碟对决与超空间跳跃"

    def get_name(self) -> str:
        return "Asteroids (1979)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.wave = 1
        self._init_wave()

    def _init_wave(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 8.0
        self.py = 8.0
        self.vx = 0.0
        self.vy = 0.0
        self.angle = -math.pi / 2.0
        self.thrusting = False

        self.asteroids = []
        for _ in range(MAX_ASTEROIDS):
            self.asteroids.append({"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "tier": 0, "active": False})

        self.bullets = []
        for _ in range(MAX_BULLETS):
            self.bullets.append({"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "life": 0.0, "active": False})

        self.saucer = {"x": 0.0, "y": 3.5, "vx": 4.0, "active": False, "shoot_timer": 2.0}
        self.saucer_spawn_timer = 8.0

        # Spawn initial wave of Tier 3 (Large) asteroids
        count = min(4, 2 + self.wave)
        positions = [
            (2.0, 2.0),
            (14.0, 2.0),
            (2.0, 14.0),
            (14.0, 14.0),
        ]
        for i in range(count):
            dir_angle = float(i) * 1.57 + 0.4
            speed = 2.0 + float(self.wave) * 0.3
            self._spawn_asteroid(
                positions[i][0], positions[i][1],
                math.cos(dir_angle) * speed,
                math.sin(dir_angle) * speed,
                3
            )

    def _spawn_asteroid(self, x: float, y: float, vx: float, vy: float, tier: int) -> None:
        for a in self.asteroids:
            if not a["active"]:
                a["x"] = wrap_coord(x)
                a["y"] = wrap_coord(y)
                a["vx"] = vx
                a["vy"] = vy
                a["tier"] = tier
                a["active"] = True
                break

    def split_asteroid(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.asteroids) or not self.asteroids[idx]["active"]:
            return

        old_tier = self.asteroids[idx]["tier"]
        ox = self.asteroids[idx]["x"]
        oy = self.asteroids[idx]["y"]
        ovx = self.asteroids[idx]["vx"]
        ovy = self.asteroids[idx]["vy"]

        self.asteroids[idx]["active"] = False

        if old_tier == 3:
            self.score += 20
            spd = math.sqrt(ovx * ovx + ovy * ovy) * 1.3
            ang = math.atan2(ovy, ovx)
            self._spawn_asteroid(ox, oy, math.cos(ang + 0.7) * spd, math.sin(ang + 0.7) * spd, 2)
            self._spawn_asteroid(ox, oy, math.cos(ang - 0.7) * spd, math.sin(ang - 0.7) * spd, 2)
        elif old_tier == 2:
            self.score += 50
            spd = math.sqrt(ovx * ovx + ovy * ovy) * 1.4
            ang = math.atan2(ovy, ovx)
            self._spawn_asteroid(ox, oy, math.cos(ang + 0.9) * spd, math.sin(ang + 0.9) * spd, 1)
            self._spawn_asteroid(ox, oy, math.cos(ang - 0.9) * spd, math.sin(ang - 0.9) * spd, 1)
        elif old_tier == 1:
            self.score += 100

    def fire_bullet(self) -> None:
        for b in self.bullets:
            if not b["active"]:
                b["x"] = wrap_coord(self.px + math.cos(self.angle) * 1.2)
                b["y"] = wrap_coord(self.py + math.sin(self.angle) * 1.2)
                b["vx"] = self.vx + math.cos(self.angle) * 22.0
                b["vy"] = self.vy + math.sin(self.angle) * 22.0
                b["life"] = 0.75
                b["active"] = True
                break

    def hyperspace_jump(self) -> None:
        self.px = float((int(self.px * 7.0 + 5.0)) % 14 + 1)
        self.py = float((int(self.py * 11.0 + 3.0)) % 14 + 1)
        self.vx = 0.0
        self.vy = 0.0

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
                    self.state = STATE_PLAYING
                    self.px = 8.0
                    self.py = 8.0
                    self.vx = 0.0
                    self.vy = 0.0
                    self.angle = -math.pi / 2.0
            return

        if self.state == STATE_WAVE_CLEAR:
            if self.state_timer > 1.5:
                self.wave += 1
                self._init_wave()
            return

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_bullet()
        if (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            self.hyperspace_jump()

        self._update_ship(dt, buttons)
        self._update_asteroids(dt)
        self._update_bullets(dt)
        self._update_saucer(dt)
        self._check_collisions()
        self._check_wave_clear()

    def _update_ship(self, dt: float, buttons: int) -> None:
        rot_speed = 4.2
        if buttons & KEY_LEFT:
            self.angle -= rot_speed * dt
        if buttons & KEY_RIGHT:
            self.angle += rot_speed * dt

        self.thrusting = bool(buttons & (KEY_UP | KEY_B))
        if self.thrusting:
            thrust = 14.0
            self.vx += math.cos(self.angle) * thrust * dt
            self.vy += math.sin(self.angle) * thrust * dt

        self.vx *= (1.0 - 0.25 * dt)
        self.vy *= (1.0 - 0.25 * dt)

        self.px = wrap_coord(self.px + self.vx * dt)
        self.py = wrap_coord(self.py + self.vy * dt)

    def _update_asteroids(self, dt: float) -> None:
        for a in self.asteroids:
            if not a["active"]:
                continue
            a["x"] = wrap_coord(a["x"] + a["vx"] * dt)
            a["y"] = wrap_coord(a["y"] + a["vy"] * dt)

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

    def _update_saucer(self, dt: float) -> None:
        if not self.saucer["active"]:
            self.saucer_spawn_timer -= dt
            if self.saucer_spawn_timer <= 0.0:
                self.saucer["active"] = True
                self.saucer["x"] = 0.0
                self.saucer["y"] = 3.5
                self.saucer["vx"] = 4.0
                self.saucer["shoot_timer"] = 2.0
        else:
            self.saucer["x"] += self.saucer["vx"] * dt
            if self.saucer["x"] >= 16.0:
                self.saucer["active"] = False
                self.saucer_spawn_timer = 12.0

    def _check_collisions(self) -> None:
        # Bullet vs Asteroid
        for b in self.bullets:
            if not b["active"]:
                continue
            for a_idx, a in enumerate(self.asteroids):
                if not a["active"]:
                    continue

                hit_radius = 1.6 if a["tier"] == 3 else (1.1 if a["tier"] == 2 else 0.7)
                dx = wrap_diff(b["x"], a["x"])
                dy = wrap_diff(b["y"], a["y"])

                if dx < hit_radius and dy < hit_radius:
                    b["active"] = False
                    self.split_asteroid(a_idx)
                    break

        # Bullet vs Saucer
        if self.saucer["active"]:
            for b in self.bullets:
                if not b["active"]:
                    continue
                dx = wrap_diff(b["x"], self.saucer["x"])
                dy = wrap_diff(b["y"], self.saucer["y"])
                if dx < 1.0 and dy < 1.0:
                    b["active"] = False
                    self.saucer["active"] = False
                    self.saucer_spawn_timer = 14.0
                    self.score += 200
                    break

        # Ship vs Asteroid
        for a_idx, a in enumerate(self.asteroids):
            if not a["active"]:
                continue
            hit_radius = 1.4 if a["tier"] == 3 else (1.0 if a["tier"] == 2 else 0.6)
            dx = wrap_diff(self.px, a["x"])
            dy = wrap_diff(self.py, a["y"])
            if dx < hit_radius and dy < hit_radius:
                self.state = STATE_PLAYER_EXPLODING
                self.state_timer = 0.0
                self.split_asteroid(a_idx)
                break

        # Ship vs Saucer
        if self.saucer["active"]:
            dx = wrap_diff(self.px, self.saucer["x"])
            dy = wrap_diff(self.py, self.saucer["y"])
            if dx < 1.0 and dy < 1.0:
                self.state = STATE_PLAYER_EXPLODING
                self.state_timer = 0.0
                self.saucer["active"] = False

    def _check_wave_clear(self) -> None:
        if not any(a["active"] for a in self.asteroids):
            self.state = STATE_WAVE_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Asteroids
        for a in self.asteroids:
            if not a["active"]:
                continue
            ax = int(round(a["x"]))
            ay = int(round(a["y"]))

            if a["tier"] == 3:
                set_pixel(ax, ay, 180, 180, 190)
                set_pixel((ax + 1) % 16, ay, 140, 140, 150)
                set_pixel((ax + 15) % 16, ay, 140, 140, 150)
                set_pixel(ax, (ay + 1) % 16, 110, 110, 120)
                set_pixel(ax, (ay + 15) % 16, 210, 210, 220)
            elif a["tier"] == 2:
                set_pixel(ax, ay, 160, 160, 170)
                set_pixel((ax + 1) % 16, ay, 130, 130, 140)
                set_pixel(ax, (ay + 1) % 16, 110, 110, 120)
            else:
                set_pixel(ax, ay, 220, 220, 240)

        # 2. Saucer
        if self.saucer["active"]:
            sx = int(round(self.saucer["x"]))
            sy = int(round(self.saucer["y"]))
            set_pixel(sx, sy, 255, 60, 40)
            set_pixel((sx + 1) % 16, sy, 255, 200, 30)
            set_pixel((sx + 15) % 16, sy, 255, 200, 30)
            set_pixel(sx, (sy + 15) % 16, 0, 220, 255)

        # 3. Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            set_pixel(bx, by, 0, 255, 255)

        # 4. Ship
        if self.state == STATE_PLAYING:
            sx = int(round(self.px))
            sy = int(round(self.py))

            nx = int(round(self.px + math.cos(self.angle) * 1.0))
            ny = int(round(self.py + math.sin(self.angle) * 1.0))
            set_pixel(int(wrap_coord(nx)), int(wrap_coord(ny)), 255, 255, 255)

            set_pixel(sx, sy, 60, 160, 255)

            w1x = int(round(self.px + math.cos(self.angle + 2.4) * 1.0))
            w1y = int(round(self.py + math.sin(self.angle + 2.4) * 1.0))
            w2x = int(round(self.px + math.cos(self.angle - 2.4) * 1.0))
            w2y = int(round(self.py + math.sin(self.angle - 2.4) * 1.0))
            set_pixel(int(wrap_coord(w1x)), int(wrap_coord(w1y)), 40, 100, 220)
            set_pixel(int(wrap_coord(w2x)), int(wrap_coord(w2y)), 40, 100, 220)

            if self.thrusting:
                tx = int(round(self.px - math.cos(self.angle) * 1.2))
                ty = int(round(self.py - math.sin(self.angle) * 1.2))
                set_pixel(int(wrap_coord(tx)), int(wrap_coord(ty)), 255, 120, 20)
        elif self.state == STATE_PLAYER_EXPLODING:
            sx = int(round(self.px))
            sy = int(round(self.py))
            set_pixel(sx, sy, 255, 220, 50)
            set_pixel((sx + 1) % 16, (sy + 1) % 16, 255, 60, 30)
            set_pixel((sx + 15) % 16, (sy + 15) % 16, 255, 60, 30)
            set_pixel((sx + 1) % 16, (sy + 15) % 16, 255, 180, 0)

        # 5. Lives HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 0, 220, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "wave": self.wave,
            "px": self.px,
            "py": self.py,
            "vx": self.vx,
            "vy": self.vy,
            "angle": self.angle,
            "thrusting": self.thrusting,
            "saucer_active": self.saucer["active"],
        }
