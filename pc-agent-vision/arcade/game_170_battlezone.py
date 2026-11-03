"""
Game #170: 矢量坦克战 (Battlezone - 1980 Atari / Ed Rotberg)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Atari in 1980, Battlezone was the very first 3D first-person vector combat simulator.
Peering through the periscope viewport across a volcanic battlefield, players utilized a top-mounted
360-degree radar scanner to locate enemy tanks, supertanks, and missiles, maneuvering around geometric
tank obstacles to engage targets at distance.

Unique Mechanic (Strict Zero-Redundancy):
- Top Radar Periscope Display: Real-time 360-degree scanner displaying enemy bearings and ranges.
- Dual-Tread Tank Navigation & Hull Rotation: Rotate and drive relative to geometric battle obstacles.
- Ballistic Shell Travel & Reticle Targeting: Long-range tank artillery with projectile flight time.
- Geometric Solid Obstacles: Pyramids and cubes that block shells and provide protective cover.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

STATE_PLAYING = 0
STATE_SECTOR_CLEAR = 1
STATE_TANK_EXPLODING = 2
STATE_GAME_OVER = 3

class Game170Battlezone(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.sector = 1
        self.state_timer = 0.0

        # Player Tank State (World space coordinates and heading angle)
        self.px = 8.0
        self.py = 10.0
        self.angle = -math.pi / 2.0 # Facing UP
        self.speed = 4.2
        self.rot_speed = 3.5
        self.fire_cooldown = 0.0

        # Shells: list of {x, y, vx, vy, is_player, life}
        self.shells: List[Dict[str, float]] = []

        # Geometric Obstacles (Pyramids / Cubes): list of (x, y)
        self.obstacles = [(4.0, 5.0), (12.0, 5.0), (8.0, 8.0)]

        # Enemy Tanks: list of {id, x, y, angle, speed, fire_timer, is_supertank, alive}
        self.enemies: List[Dict[str, Any]] = []
        self.enemies_killed = 0
        self.target_kills = 4

        self.init()

    @property
    def game_id(self) -> int:
        return 170

    @property
    def name(self) -> str:
        return "矢量坦克战"

    @property
    def english_name(self) -> str:
        return "Battlezone"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "顶置360度潜望镜雷达搜索、双履带旋转航向、几何金字塔掩体战术周旋与远程弹道火控"

    def get_name(self) -> str:
        return "Battlezone (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.sector = 1
        self._init_sector()

    def _init_sector(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 8.0
        self.py = 10.0
        self.angle = -math.pi / 2.0
        self.fire_cooldown = 0.0
        self.shells.clear()
        self.enemies.clear()
        self.enemies_killed = 0
        self.target_kills = 4 + self.sector * 2

        # Spawn initial enemy tanks
        self._spawn_enemy(False)

    def _spawn_enemy(self, is_supertank: bool = False):
        if len([e for e in self.enemies if e["alive"]]) >= 2:
            return
        side = len(self.enemies) % 4
        ex, ey = 8.0, 2.0
        if side == 0: ex, ey = 2.0, 2.0
        elif side == 1: ex, ey = 14.0, 2.0
        elif side == 2: ex, ey = 2.0, 8.0
        else: ex, ey = 14.0, 8.0

        self.enemies.append({
            "id": len(self.enemies),
            "x": ex,
            "y": ey,
            "angle": math.pi / 2.0,
            "speed": 2.2 if is_supertank else 1.5,
            "fire_timer": 2.5,
            "is_supertank": is_supertank,
            "alive": True
        })

    def fire_cannon(self):
        if self.fire_cooldown > 0.0 or self.state != STATE_PLAYING:
            return

        shell_speed = 12.0
        vx = math.cos(self.angle) * shell_speed
        vy = math.sin(self.angle) * shell_speed
        self.shells.append({
            "x": self.px + math.cos(self.angle) * 0.8,
            "y": self.py + math.sin(self.angle) * 0.8,
            "vx": vx,
            "vy": vy,
            "is_player": True,
            "life": 1.2
        })
        self.fire_cooldown = 0.35

    def is_blocked_by_obstacle(self, x: float, y: float) -> bool:
        for (ox, oy) in self.obstacles:
            if math.hypot(ox - x, oy - y) < 1.0:
                return True
        return False

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_SECTOR_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.sector += 1
                self._init_sector()
            return

        if self.state == STATE_TANK_EXPLODING:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 8.0
                    self.py = 10.0
                    self.angle = -math.pi / 2.0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Tank Rotation & Tread Steering
        if keys_down & KEY_LEFT:
            self.angle -= self.rot_speed * dt
        if keys_down & KEY_RIGHT:
            self.angle += self.rot_speed * dt

        move_v = 0.0
        if keys_down & KEY_UP:   move_v += self.speed
        if keys_down & KEY_DOWN: move_v -= self.speed * 0.6

        if move_v != 0.0:
            new_px = self.px + math.cos(self.angle) * move_v * dt
            new_py = self.py + math.sin(self.angle) * move_v * dt

            if not self.is_blocked_by_obstacle(new_px, new_py):
                self.px = max(1.0, min(14.5, new_px))
                self.py = max(2.5, min(14.5, new_py))

        # Fire Cannon Action
        if keys_pressed & KEY_A:
            self.fire_cannon()

        # Shells Update
        for s in list(self.shells):
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["life"] -= dt

            # Obstacle impact
            if self.is_blocked_by_obstacle(s["x"], s["y"]) or s["life"] <= 0 or \
               s["x"] < 0 or s["x"] > 15 or s["y"] < 0 or s["y"] > 15:
                self.shells.remove(s)
                continue

            if s["is_player"]:
                # Check hit enemy tanks
                for e in self.enemies:
                    if e["alive"] and math.hypot(e["x"] - s["x"], e["y"] - s["y"]) < 1.1:
                        e["alive"] = False
                        self.enemies_killed += 1
                        self.score += 1000 if e["is_supertank"] else 500
                        if s in self.shells:
                            self.shells.remove(s)

                        if self.enemies_killed >= self.target_kills:
                            self.state = STATE_SECTOR_CLEAR
                            self.state_timer = 2.0
                            self.score += 2500
                        else:
                            self._spawn_enemy(self.enemies_killed % 2 == 1)
                        break
            else:
                # Enemy shell hit player
                if math.hypot(self.px - s["x"], self.py - s["y"]) < 0.9:
                    self.shells.remove(s)
                    self.lives -= 1
                    self.state = STATE_TANK_EXPLODING
                    self.state_timer = 1.0
                    return

        # Enemies AI & Ballistics
        for e in self.enemies:
            if not e["alive"]:
                continue

            # Steer toward player
            edx = self.px - e["x"]
            edy = self.py - e["y"]
            target_angle = math.atan2(edy, edx)

            # Turn towards target
            diff = (target_angle - e["angle"] + math.pi) % (2 * math.pi) - math.pi
            e["angle"] += math.copysign(min(abs(diff), 2.0 * dt), diff)

            # Move forward if clear
            dist = math.hypot(edx, edy)
            if dist > 3.0:
                new_ex = e["x"] + math.cos(e["angle"]) * e["speed"] * dt
                new_ey = e["y"] + math.sin(e["angle"]) * e["speed"] * dt
                if not self.is_blocked_by_obstacle(new_ex, new_ey):
                    e["x"] = max(1.0, min(14.5, new_ex))
                    e["y"] = max(2.5, min(14.5, new_ey))

            # Fire shell at player
            e["fire_timer"] -= dt
            if e["fire_timer"] <= 0.0 and dist < 12.0:
                shell_speed = 8.0
                self.shells.append({
                    "x": e["x"] + math.cos(e["angle"]) * 0.8,
                    "y": e["y"] + math.sin(e["angle"]) * 0.8,
                    "vx": math.cos(e["angle"]) * shell_speed,
                    "vy": math.sin(e["angle"]) * shell_speed,
                    "is_player": False,
                    "life": 1.5
                })
                e["fire_timer"] = 3.0

            # Collision with player
            if dist < 1.0:
                self.lives -= 1
                self.state = STATE_TANK_EXPLODING
                self.state_timer = 1.0
                return

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(16 * 16 * 3):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Top Radar Periscope Display (Rows y=0, 1)
        for x in range(16):
            set_pixel(x, 1, 0, 100, 40) # Radar perimeter bar

        # Radar blips of enemies relative to player heading
        for e in self.enemies:
            if e["alive"]:
                rel_angle = math.atan2(e["y"] - self.py, e["x"] - self.px) - self.angle
                rel_angle = (rel_angle + math.pi) % (2 * math.pi) - math.pi
                rx = int(round(8.0 + (rel_angle / math.pi) * 7.0))
                rx = max(0, min(15, rx))
                set_pixel(rx, 0, 255, 30, 30) # Red radar blip

        # 2. Geometric Obstacles (Pyramids / Cubes)
        for (ox, oy) in self.obstacles:
            ix, iy = int(round(ox)), int(round(oy))
            set_pixel(ix, iy, 40, 200, 220)
            set_pixel(ix + 1, iy, 20, 120, 140)

        # 3. Enemy Tanks
        for e in self.enemies:
            if e["alive"]:
                ex, ey = int(round(e["x"])), int(round(e["y"]))
                color = (255, 60, 60) if e["is_supertank"] else (220, 120, 40)
                set_pixel(ex, ey, *color)

        # 4. Shells
        for s in self.shells:
            sx, sy = int(round(s["x"])), int(round(s["y"]))
            color = (255, 255, 255) if s["is_player"] else (255, 100, 0)
            set_pixel(sx, sy, *color)

        # 5. Player Tank & Reticle
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_SECTOR_CLEAR):
            set_pixel(px, py, 0, 255, 100) # Bright green vector tank
            # Turret barrel
            tx = int(round(self.px + math.cos(self.angle) * 1.1))
            ty = int(round(self.py + math.sin(self.angle) * 1.1))
            set_pixel(tx, ty, 100, 255, 150)
        elif self.state == STATE_TANK_EXPLODING:
            set_pixel(px, py, 255, 50, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "sector": self.sector,
            "enemies_killed": self.enemies_killed,
            "target_kills": self.target_kills,
            "px": self.px,
            "py": self.py,
            "angle": self.angle,
        }

