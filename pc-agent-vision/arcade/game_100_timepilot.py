"""
Game #100: 时空领航员 / 穿越世纪 (Time Pilot 1982 / Konami)
Centrifugal 360-degree multidirectional aerial dogfighting, historical era warp transitions,
parachutist pilot search-and-rescue, and massive era flagship boss showdowns.
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

STATE_DOGFIGHT = 0
STATE_TIME_WARP = 1
STATE_PLAYER_SHOT_DOWN = 2
STATE_GAME_OVER = 3

MAX_PLAYER_BULLETS = 4
MAX_ENEMY_BULLETS = 4
MAX_ENEMIES = 4
MAX_PARACHUTES = 2
MAX_CLOUDS = 4


class Game100TimePilot(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_DOGFIGHT
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.era = 0  # 0: 1910, 1: 1940, 2: 1970, 3: 2001, 4: UFO
        self.squadron_defeated = 0
        self.boss_active = False

        self.player_angle = -math.pi / 2.0  # Facing up
        self.speed = 4.5
        self.fire_cooldown = 0.0

        self.player_bullets: List[Dict[str, Any]] = []
        self.enemy_bullets: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.parachutes: List[Dict[str, Any]] = []
        self.clouds: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 100

    @property
    def name(self) -> str:
        return "时空领航员"

    @property
    def english_name(self) -> str:
        return "Time Pilot"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "360度环形多向空战、五大历史纪元跳跃、空降兵搜救与战队母舰围歼"

    def get_name(self) -> str:
        return "Time Pilot (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.era = 0
        self._reset_era()

    def _reset_era(self) -> None:
        self.state = STATE_DOGFIGHT
        self.state_timer = 0.0
        self.squadron_defeated = 0
        self.boss_active = False
        self.player_angle = -math.pi / 2.0
        self.speed = 4.5
        self.fire_cooldown = 0.0

        self.player_bullets = [
            {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "life": 0.0, "active": False}
            for _ in range(MAX_PLAYER_BULLETS)
        ]
        self.enemy_bullets = [
            {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "life": 0.0, "active": False}
            for _ in range(MAX_ENEMY_BULLETS)
        ]
        self.parachutes = [
            {"x": 0.0, "y": 0.0, "vy": 0.8, "active": False}
            for _ in range(MAX_PARACHUTES)
        ]
        self.clouds = [
            {"x": float((i * 7) % 16), "y": float((i * 5) % 16), "speed": 0.5 + float(i) * 0.2}
            for i in range(MAX_CLOUDS)
        ]

        # 4 escorts + 1 boss slot
        self.enemies = []
        for i in range(MAX_ENEMIES):
            self.enemies.append({
                "x": -2.0 if (i % 2 == 0) else 18.0,
                "y": 2.0 + float(i * 3),
                "vx": 3.0 if (i % 2 == 0) else -3.0,
                "vy": 0.5,
                "hp": 1,
                "is_boss": False,
                "fire_timer": 1.0 + float(i) * 0.8,
                "active": True,
            })
        # Boss slot
        self.enemies.append({
            "x": 8.0,
            "y": -3.0,
            "vx": 1.2,
            "vy": 1.0,
            "hp": 4 + self.era,
            "is_boss": True,
            "fire_timer": 0.8,
            "active": False,
        })

    def _spawn_boss(self) -> None:
        self.boss_active = True
        boss = self.enemies[MAX_ENEMIES]
        boss["active"] = True
        boss["is_boss"] = True
        boss["hp"] = 4 + self.era
        boss["x"] = 8.0
        boss["y"] = -3.0
        boss["vx"] = 1.2
        boss["vy"] = 1.0
        boss["fire_timer"] = 0.8

    def _spawn_parachute(self, x: float, y: float) -> None:
        for p in self.parachutes:
            if not p["active"]:
                p["active"] = True
                p["x"] = x
                p["y"] = y
                p["vy"] = 0.8
                break

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_PLAYER_SHOT_DOWN:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_DOGFIGHT
                    self.state_timer = 0.0
                    self.player_angle = -math.pi / 2.0
            return

        if self.state == STATE_TIME_WARP:
            if self.state_timer > 2.2:
                self.era = (self.era + 1) % 5
                self._reset_era()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_flight(dt, buttons, prev_buttons)

        scroll_x = -math.cos(self.player_angle) * self.speed * dt
        scroll_y = -math.sin(self.player_angle) * self.speed * dt

        self._update_clouds(dt, scroll_x, scroll_y)
        self._update_bullets(dt, scroll_x, scroll_y)
        self._update_enemies(dt, scroll_x, scroll_y)
        self._update_parachutes(dt, scroll_x, scroll_y)
        self._check_collisions()

        if not self.boss_active and self.squadron_defeated >= 5:
            self._spawn_boss()

    def _update_flight(self, dt: float, buttons: int, prev_buttons: int) -> None:
        target_dx = 0.0
        target_dy = 0.0
        if buttons & KEY_LEFT:
            target_dx -= 1.0
        if buttons & KEY_RIGHT:
            target_dx += 1.0
        if buttons & KEY_UP:
            target_dy -= 1.0
        if buttons & KEY_DOWN:
            target_dy += 1.0

        if target_dx != 0.0 or target_dy != 0.0:
            target_angle = math.atan2(target_dy, target_dx)
            diff = target_angle - self.player_angle
            while diff > math.pi:
                diff -= 2.0 * math.pi
            while diff < -math.pi:
                diff += 2.0 * math.pi

            turn_speed = 9.0
            if abs(diff) < turn_speed * dt:
                self.player_angle = target_angle
            else:
                self.player_angle += (1.0 if diff > 0.0 else -1.0) * turn_speed * dt

        # Button B: Afterburner turbo boost
        if buttons & KEY_B:
            self.speed = 7.5
        else:
            self.speed = 4.5

        # Button A: Forward cannons fire
        self.fire_cooldown -= dt
        if (buttons & KEY_A) and self.fire_cooldown <= 0.0:
            self.fire_cooldown = 0.22
            for b in self.player_bullets:
                if not b["active"]:
                    b["active"] = True
                    b["x"] = 7.5 + math.cos(self.player_angle) * 1.5
                    b["y"] = 7.5 + math.sin(self.player_angle) * 1.5
                    b["vx"] = math.cos(self.player_angle) * 12.0
                    b["vy"] = math.sin(self.player_angle) * 12.0
                    b["life"] = 1.2
                    break

    def _update_clouds(self, dt: float, scroll_x: float, scroll_y: float) -> None:
        for c in self.clouds:
            c["x"] += scroll_x * c["speed"]
            c["y"] += scroll_y * c["speed"]
            if c["x"] < -4.0:
                c["x"] += 24.0
            elif c["x"] > 20.0:
                c["x"] -= 24.0
            if c["y"] < -4.0:
                c["y"] += 24.0
            elif c["y"] > 20.0:
                c["y"] -= 24.0

    def _update_bullets(self, dt: float, scroll_x: float, scroll_y: float) -> None:
        for b in self.player_bullets:
            if not b["active"]:
                continue
            b["x"] += (b["vx"] * dt) + scroll_x
            b["y"] += (b["vy"] * dt) + scroll_y
            b["life"] -= dt
            if (
                b["life"] <= 0.0
                or b["x"] < -2.0
                or b["x"] > 18.0
                or b["y"] < -2.0
                or b["y"] > 18.0
            ):
                b["active"] = False

        for b in self.enemy_bullets:
            if not b["active"]:
                continue
            b["x"] += (b["vx"] * dt) + scroll_x
            b["y"] += (b["vy"] * dt) + scroll_y
            b["life"] -= dt
            if (
                b["life"] <= 0.0
                or b["x"] < -2.0
                or b["x"] > 18.0
                or b["y"] < -2.0
                or b["y"] > 18.0
            ):
                b["active"] = False

    def _update_enemies(self, dt: float, scroll_x: float, scroll_y: float) -> None:
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue

            e["x"] += (e["vx"] * dt) + scroll_x
            e["y"] += (e["vy"] * dt) + scroll_y

            if e["is_boss"]:
                if e["x"] < 2.0:
                    e["vx"] = abs(e["vx"])
                elif e["x"] > 14.0:
                    e["vx"] = -abs(e["vx"])
                if e["y"] < 2.0:
                    e["vy"] = abs(e["vy"])
                elif e["y"] > 10.0:
                    e["vy"] = -abs(e["vy"])
            else:
                if e["x"] < -5.0:
                    e["x"] = 21.0
                elif e["x"] > 21.0:
                    e["x"] = -5.0
                if e["y"] < -5.0:
                    e["y"] = 21.0
                elif e["y"] > 21.0:
                    e["y"] = -5.0

                to_p_x = 7.5 - e["x"]
                to_p_y = 7.5 - e["y"]
                dist = math.hypot(to_p_x, to_p_y)
                if dist > 0.1:
                    target_vx = (to_p_x / dist) * 3.2
                    target_vy = (to_p_y / dist) * 3.2
                    e["vx"] += (target_vx - e["vx"]) * 1.5 * dt
                    e["vy"] += (target_vy - e["vy"]) * 1.5 * dt

            e["fire_timer"] -= dt
            if e["fire_timer"] <= 0.0:
                e["fire_timer"] = 1.0 if e["is_boss"] else (2.0 + float(i) * 0.5)
                to_p_x = 7.5 - e["x"]
                to_p_y = 7.5 - e["y"]
                dist = math.hypot(to_p_x, to_p_y)
                if 1.0 < dist < 12.0:
                    for eb in self.enemy_bullets:
                        if not eb["active"]:
                            eb["active"] = True
                            eb["x"] = e["x"]
                            eb["y"] = e["y"]
                            b_spd = 5.5 + float(self.era) * 0.8
                            eb["vx"] = (to_p_x / dist) * b_spd
                            eb["vy"] = (to_p_y / dist) * b_spd
                            eb["life"] = 2.0
                            break

    def _update_parachutes(self, dt: float, scroll_x: float, scroll_y: float) -> None:
        for p in self.parachutes:
            if not p["active"]:
                continue
            p["x"] += scroll_x
            p["y"] += (p["vy"] * dt) + scroll_y
            if p["y"] > 18.0 or p["x"] < -4.0 or p["x"] > 20.0:
                p["active"] = False

    def _check_collisions(self) -> None:
        px = 7.5
        py = 7.5

        # 1. Player bullets vs Enemies
        for b in self.player_bullets:
            if not b["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                hit_radius = 1.8 if e["is_boss"] else 1.2
                dx = b["x"] - e["x"]
                dy = b["y"] - e["y"]
                if math.hypot(dx, dy) < hit_radius:
                    b["active"] = False
                    e["hp"] -= 1
                    if e["hp"] <= 0:
                        e["active"] = False
                        if e["is_boss"]:
                            self.score += 3000 + self.era * 1000
                            self.state = STATE_TIME_WARP
                            self.state_timer = 0.0
                        else:
                            self.score += 100 + self.era * 50
                            self.squadron_defeated += 1
                            if self.squadron_defeated % 2 == 1:
                                self._spawn_parachute(e["x"], e["y"])
                            if not self.boss_active:
                                e["active"] = True
                                e["hp"] = 1
                                e["x"] = -3.0 if (self.squadron_defeated % 2 == 0) else 19.0
                                e["y"] = 2.0 + float((self.squadron_defeated * 3) % 12)
                                e["vx"] = 3.0 if (self.squadron_defeated % 2 == 0) else -3.0
                                e["vy"] = 0.0
                    break

        # 2. Parachute rescue
        for p in self.parachutes:
            if not p["active"]:
                continue
            if math.hypot(px - p["x"], py - p["y"]) < 1.4:
                p["active"] = False
                self.score += 500

        # 3. Enemy bullets vs Player
        for eb in self.enemy_bullets:
            if not eb["active"]:
                continue
            if math.hypot(px - eb["x"], py - eb["y"]) < 0.9:
                eb["active"] = False
                self.state = STATE_PLAYER_SHOT_DOWN
                self.state_timer = 0.0
                return

        # 4. Enemy body ramming player
        for e in self.enemies:
            if not e["active"]:
                continue
            hit_dist = 1.5 if e["is_boss"] else 1.0
            if math.hypot(px - e["x"], py - e["y"]) < hit_dist:
                self.state = STATE_PLAYER_SHOT_DOWN
                self.state_timer = 0.0
                return

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

        # Sky background by Era
        bg_colors = [
            (40, 35, 20),  # Era 0: 1910 Sepia
            (15, 25, 50),  # Era 1: 1940 WWII Azure
            (50, 25, 15),  # Era 2: 1970 Sunset
            (10, 10, 35),  # Era 3: 2001 Midnight
            (5, 5, 15),    # Era 4: Alien Space
        ]
        bg_r, bg_g, bg_b = bg_colors[self.era]
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, bg_r, bg_g, bg_b)

        # Clouds
        cr = 140 if self.era == 0 else 180
        cg = 130 if self.era == 0 else 190
        cb = 110 if self.era == 0 else 210
        for c in self.clouds:
            cx = int(round(c["x"]))
            cy = int(round(c["y"]))
            set_pixel(cx, cy, cr, cg, cb)
            set_pixel(cx + 1, cy, cr, cg, cb)
            set_pixel(cx, cy + 1, cr, cg, cb)

        # Parachutists
        for p in self.parachutes:
            if not p["active"]:
                continue
            px_i = int(round(p["x"]))
            py_i = int(round(p["y"]))
            set_pixel(px_i, py_i - 1, 255, 255, 255)
            set_pixel(px_i - 1, py_i - 1, 240, 240, 240)
            set_pixel(px_i + 1, py_i - 1, 240, 240, 240)
            set_pixel(px_i, py_i, 255, 200, 150)

        # Bullets
        for b in self.player_bullets:
            if not b["active"]:
                continue
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 100)

        for eb in self.enemy_bullets:
            if not eb["active"]:
                continue
            set_pixel(int(round(eb["x"])), int(round(eb["y"])), 255, 60, 40)

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["is_boss"]:
                br, bg, bb = (80, 255, 120) if self.era == 4 else (255, 180, 40)
                set_pixel(ex, ey, br, bg, bb)
                set_pixel(ex - 1, ey, br, bg, bb)
                set_pixel(ex + 1, ey, br, bg, bb)
                set_pixel(ex, ey - 1, br, bg, bb)
                set_pixel(ex, ey + 1, br, bg, bb)
            else:
                er, eg, eb = 220, 80, 60
                if self.era == 2:
                    er, eg, eb = 100, 200, 50
                elif self.era == 3:
                    er, eg, eb = 60, 150, 240
                elif self.era == 4:
                    er, eg, eb = 220, 60, 220
                set_pixel(ex, ey, er, eg, eb)

        # Time Warp Visual FX
        if self.state == STATE_TIME_WARP:
            ring = int(self.state_timer * 7.0) % 8
            for i in range(16):
                set_pixel(i, ring, 255, 255, 255)
                set_pixel(i, 15 - ring, 255, 255, 255)
                set_pixel(ring, i, 255, 255, 255)
                set_pixel(15 - ring, i, 255, 255, 255)

        # Player Craft at Center (7, 7)
        px_c = 7
        py_c = 7
        if self.state == STATE_PLAYER_SHOT_DOWN:
            set_pixel(px_c, py_c, 255, 50, 20)
            set_pixel(px_c - 1, py_c, 255, 180, 0)
            set_pixel(px_c + 1, py_c, 255, 180, 0)
            set_pixel(px_c, py_c - 1, 255, 180, 0)
            set_pixel(px_c, py_c + 1, 255, 180, 0)
        else:
            set_pixel(px_c, py_c, 255, 255, 255)
            nose_x = px_c + int(round(math.cos(self.player_angle)))
            nose_y = py_c + int(round(math.sin(self.player_angle)))
            set_pixel(nose_x, nose_y, 0, 220, 255)

            wing_x = px_c - int(round(math.cos(self.player_angle)))
            wing_y = py_c - int(round(math.sin(self.player_angle)))
            set_pixel(wing_x, wing_y, 255, 120, 20)

        # HUD
        for i in range(min(self.squadron_defeated, 5)):
            set_pixel(i, 15, 0, 255, 100)
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 220, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "era": self.era,
            "squadron_defeated": self.squadron_defeated,
            "boss_active": self.boss_active,
            "player_angle": self.player_angle,
            "speed": self.speed,
        }
