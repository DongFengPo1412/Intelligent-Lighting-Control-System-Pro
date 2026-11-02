"""
Game #088: 疯狂碰碰车 / 跳跃撞击 (Bump 'n' Jump 1982 / Data East)
High-flying buggy leaps, enemy crushing landing, bump-tackles into guard rails & river gap leaps.
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
STATE_CRASHED = 1
STATE_LEVEL_CLEAR = 2
STATE_GAME_OVER = 3

ENEMY_CAR = 0
ENEMY_TRUCK = 1
ENEMY_OBSTACLE = 2

MAX_ENEMIES = 4


class Game088BumpNJump(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_DRIVING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1
        self.crushed_count = 0

        # Player Buggy
        self.px = 7.5
        self.py = 13.0
        self.speed = 110.0  # 40 to 180 km/h
        self.jump_z = 0.0
        self.jump_vz = 0.0
        self.is_jumping = False
        self.bump_vx = 0.0
        self.bump_boost_cooldown = 0.0

        # Road & Hazards
        self.distance = 0.0
        self.stage_length = 600.0
        self.road_scroll = 0.0
        self.water_gap_dist = 160.0
        self.water_gap_length = 6.0

        self.enemies: List[Dict[str, Any]] = []
        self._prev_keys = 0

        self.reset()

    @property
    def game_id(self) -> int:
        return 88

    @property
    def name(self) -> str:
        return "疯狂碰碰车"

    @property
    def english_name(self) -> str:
        return "Bump 'n' Jump"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "高空飞跃下压砸扁敌车、地面侧向撞击推挤、跨越断桥死穴"

    def get_name(self) -> str:
        return "Bump 'n' Jump (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = STATE_DRIVING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1
        self.crushed_count = 0
        self._reset_stage(hard_reset=True)

    def _reset_stage(self, hard_reset: bool = False) -> None:
        self.state = STATE_DRIVING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 13.0
        self.speed = 110.0
        self.jump_z = 0.0
        self.jump_vz = 0.0
        self.is_jumping = False
        self.bump_vx = 0.0
        self.bump_boost_cooldown = 0.0
        self.distance = 0.0
        self.stage_length = 500.0 + self.level * 100.0
        self.water_gap_dist = 160.0

        self.enemies = []
        for i in range(MAX_ENEMIES):
            self.enemies.append({
                "x": 4.0 + (i % 3) * 3.5,
                "y": -2.0 - i * 4.0,
                "speed": 70.0 + (i % 2) * 20.0,
                "type": ENEMY_TRUCK if i == 1 else ENEMY_CAR,
                "active": False,
                "respawn_timer": 1.0 + i * 1.5,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_CRASHED:
            if self.state_timer > 2.0:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_stage(hard_reset=False)
            return

        if self.state == STATE_LEVEL_CLEAR:
            if self.state_timer > 2.5:
                self.level += 1
                self._reset_stage(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        # STATE_DRIVING
        self._update_player(dt, buttons, prev_buttons)
        self._update_enemies(dt)
        self._update_road_hazards(dt)
        self._check_collisions()

        # Progression
        self.distance += (self.speed * 0.08) * dt
        if self.distance >= self.stage_length:
            self.state = STATE_LEVEL_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, keys: int, prev_keys: int) -> None:
        # Throttle / Brake
        if keys & KEY_UP:
            self.speed = min(180.0, self.speed + 40.0 * dt)
        elif keys & KEY_DOWN:
            self.speed = max(40.0, self.speed - 50.0 * dt)
        else:
            if self.speed < 100.0:
                self.speed += 10.0 * dt
            elif self.speed > 100.0:
                self.speed -= 10.0 * dt

        # Steering
        steer_speed = 7.0
        if keys & KEY_LEFT:
            self.px -= steer_speed * dt
        if keys & KEY_RIGHT:
            self.px += steer_speed * dt

        # Bump recoil impulse
        if abs(self.bump_vx) > 0.01:
            self.px += self.bump_vx * dt
            self.bump_vx *= max(0.0, 1.0 - 8.0 * dt)

        # Boundaries
        if self.px < 2.2:
            self.px = 2.2
            self.bump_vx = 2.0
            self.speed = max(40.0, self.speed - 15.0 * dt)
        elif self.px > 12.8:
            self.px = 12.8
            self.bump_vx = -2.0
            self.speed = max(40.0, self.speed - 15.0 * dt)

        # Jump (Button A, speed >= 100 km/h)
        if (keys & KEY_A) and not (prev_keys & KEY_A):
            if not self.is_jumping and self.speed >= 100.0:
                self.is_jumping = True
                self.jump_z = 0.05
                self.jump_vz = 4.8

        # Lateral Bump Tackle (Button B)
        if self.bump_boost_cooldown > 0.0:
            self.bump_boost_cooldown -= dt
        if (keys & KEY_B) and not (prev_keys & KEY_B) and self.bump_boost_cooldown <= 0.0:
            self.bump_boost_cooldown = 0.8
            direction = -1.0 if (keys & KEY_LEFT) else (1.0 if (keys & KEY_RIGHT) else (1.0 if self.px < 7.5 else -1.0))
            self.bump_vx = direction * 9.0
            self.score += 10

        # Airborne Jump physics
        if self.is_jumping:
            self.jump_z += self.jump_vz * dt
            self.jump_vz -= 8.5 * dt
            if self.jump_z <= 0.0:
                self.jump_z = 0.0
                self.jump_vz = 0.0
                self.is_jumping = False

        self.road_scroll += (self.speed * 0.15) * dt
        if self.road_scroll >= 4.0:
            self.road_scroll -= 4.0

    def _update_enemies(self, dt: float) -> None:
        for idx, e in enumerate(self.enemies):
            if not e["active"]:
                if e["respawn_timer"] > 0.0:
                    e["respawn_timer"] -= dt
                else:
                    e["active"] = True
                    e["x"] = 3.5 + (idx * 2.3) % 7.0
                    e["y"] = -2.0
                    e["speed"] = 60.0 + (idx * 15.0) % 40.0
                    e["type"] = ENEMY_TRUCK if idx == 1 else ENEMY_CAR
                continue

            rel_speed = (self.speed - e["speed"]) * 0.1
            e["y"] += rel_speed * dt

            if e["type"] == ENEMY_CAR:
                e["x"] += (0.8 if idx % 2 == 0 else -0.8) * dt
                if e["x"] < 3.0:
                    e["x"] = 3.0
                elif e["x"] > 12.0:
                    e["x"] = 12.0

            if e["y"] > 18.0 or e["y"] < -8.0:
                e["active"] = False
                e["respawn_timer"] = 2.0

    def _update_road_hazards(self, dt: float) -> None:
        self.water_gap_dist -= (self.speed * 0.12) * dt

        # Water gap spans player's vertical location (py = 13.0)
        if 10.0 <= self.water_gap_dist <= 14.5:
            if not self.is_jumping or self.jump_z < 0.25:
                self.state = STATE_CRASHED
                self.state_timer = 0.0
                return

        if self.water_gap_dist < -8.0:
            self.water_gap_dist = 220.0

    def _check_collisions(self) -> None:
        for e in self.enemies:
            if not e["active"]:
                continue

            dx = abs(self.px - e["x"])
            dy = abs(self.py - e["y"])

            if dx < 1.3 and dy < 1.4:
                if self.is_jumping:
                    # Landing crush
                    if self.jump_vz < 0.5 and self.jump_z <= 1.2:
                        e["active"] = False
                        e["respawn_timer"] = 2.5
                        self.score += 200
                        self.crushed_count += 1
                        self.jump_vz = 2.5  # Bounce up after crushing
                else:
                    # Ground bump
                    shove_dir = -1.0 if self.px < e["x"] else 1.0
                    self.px += shove_dir * 0.6
                    e["x"] -= shove_dir * 1.5

                    if e["type"] == ENEMY_TRUCK:
                        self.bump_vx = shove_dir * 3.5
                        self.speed = max(40.0, self.speed - 20.0)
                    else:
                        self.bump_vx = shove_dir * 1.5

                    if e["x"] < 2.2 or e["x"] > 12.8:
                        e["active"] = False
                        e["respawn_timer"] = 2.0
                        self.score += 100

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

        scroll_offset = int(self.road_scroll) % 2

        # Draw road & grass
        for y in range(16):
            set_pixel(0, y, 10, 45, 10)
            set_pixel(1, y, 15, 60, 15)
            set_pixel(14, y, 15, 60, 15)
            set_pixel(15, y, 10, 45, 10)

            stripe = ((y + scroll_offset) % 2 == 0)
            if stripe:
                set_pixel(2, y, 220, 220, 220)
                set_pixel(13, y, 220, 220, 220)
            else:
                set_pixel(2, y, 180, 30, 30)
                set_pixel(13, y, 180, 30, 30)

            for x in range(3, 13):
                set_pixel(x, y, 35, 38, 45)

            if (y + scroll_offset) % 4 < 2:
                set_pixel(7, y, 120, 120, 100)
                set_pixel(8, y, 120, 120, 100)

        # Draw water gap
        water_y = int(self.water_gap_dist)
        for dy in range(3):
            wy = water_y + dy
            if 0 <= wy < 16:
                for x in range(2, 14):
                    set_pixel(x, wy, 0, 70, 180)
                set_pixel(2, wy, 139, 69, 19)
                set_pixel(13, wy, 139, 69, 19)

        # Draw enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["type"] == ENEMY_TRUCK:
                set_pixel(ex, ey, 180, 40, 180)
                set_pixel(ex + 1, ey, 180, 40, 180)
                set_pixel(ex, ey + 1, 100, 20, 100)
                set_pixel(ex + 1, ey + 1, 100, 20, 100)
            else:
                set_pixel(ex, ey, 240, 120, 20)
                set_pixel(ex, ey + 1, 180, 60, 10)
                set_pixel(ex - 1, ey + 1, 40, 40, 40)
                set_pixel(ex + 1, ey + 1, 40, 40, 40)

        # Draw player buggy
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_CRASHED:
            set_pixel(px, py, 255, 200, 0)
            set_pixel(px - 1, py - 1, 255, 50, 0)
            set_pixel(px + 1, py - 1, 255, 100, 0)
            set_pixel(px - 1, py + 1, 200, 20, 0)
            set_pixel(px + 1, py + 1, 255, 150, 0)
        else:
            if self.is_jumping:
                set_pixel(px, py, 15, 15, 18)
                set_pixel(px, py + 1, 15, 15, 18)

                elevated_y = py - int(round(self.jump_z * 1.5))
                set_pixel(px, elevated_y, 80, 240, 255)
                set_pixel(px, elevated_y + 1, 30, 180, 240)
                set_pixel(px - 1, elevated_y, 255, 255, 255)
                set_pixel(px + 1, elevated_y, 255, 255, 255)
            else:
                set_pixel(px, py, 40, 180, 240)
                set_pixel(px, py + 1, 20, 120, 200)
                set_pixel(px - 1, py, 30, 30, 30)
                set_pixel(px + 1, py, 30, 30, 30)
                set_pixel(px - 1, py + 1, 30, 30, 30)
                set_pixel(px + 1, py + 1, 30, 30, 30)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 0, 255, 100)

        speed_bars = int((self.speed / 180.0) * 4.0)
        for s in range(speed_bars):
            r = 0 if self.speed >= 100.0 else 255
            g = 255 if self.speed >= 100.0 else 200
            set_pixel(15 - s, 0, r, g, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "speed": self.speed,
            "jump_z": self.jump_z,
            "is_jumping": self.is_jumping,
            "distance": self.distance,
            "crushed_count": self.crushed_count,
            "player_x": self.px,
            "player_y": self.py,
        }
