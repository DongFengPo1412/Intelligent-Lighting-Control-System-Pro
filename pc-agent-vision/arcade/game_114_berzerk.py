"""
Game #114: 狂暴机器人 (Berzerk 1980 / Stern Electronics)
Electrified lethal maze walls, auto-detonating security robots,
multidirectional laser combat, four open doorway sector escapes,
and the relentless bouncing indestructible pursuer "Evil Otto".
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

STATE_EXPLORING = 0
STATE_PLAYER_DYING = 1
STATE_ROOM_TRANSITION = 2
STATE_GAME_OVER = 3

MAX_ROBOTS = 4
MAX_LASERS = 6


class Game114Berzerk(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_EXPLORING
        self.state_timer = 0.0
        self.room_timer = 0.0
        self.score = 0
        self.lives = 3
        self.rooms_cleared = 0

        self.px = 8.0
        self.py = 8.0
        self.aim_dx = 1
        self.aim_dy = 0

        self.maze: List[List[int]] = [[0] * 16 for _ in range(16)]
        self.robots: List[Dict[str, Any]] = []
        self.lasers: List[Dict[str, Any]] = []
        self.otto: Dict[str, Any] = {"x": 8.0, "y": 0.5, "bounce_timer": 0.0, "active": False}

        self.reset()

    @property
    def game_id(self) -> int:
        return 114

    @property
    def name(self) -> str:
        return "狂暴机器人"

    @property
    def english_name(self) -> str:
        return "Berzerk"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "高压电网致命迷宫、机器人自毁诱导、无敌穿墙弹跳奥托与四向密室穿梭"

    def get_name(self) -> str:
        return "Berzerk (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.rooms_cleared = 0
        self.px = 8.0
        self.py = 8.0
        self.aim_dx = 1
        self.aim_dy = 0
        self._generate_room()

    def _generate_room(self) -> None:
        self.state = STATE_EXPLORING
        self.state_timer = 0.0
        self.room_timer = 0.0
        self.otto = {"x": 8.0, "y": 0.5, "bounce_timer": 0.0, "active": False}

        self.lasers = []
        for _ in range(MAX_LASERS):
            self.lasers.append({"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "is_player": True, "active": False})

        # Build electrified perimeter walls
        self.maze = [[0] * 16 for _ in range(16)]
        for i in range(16):
            self.maze[0][i] = 1
            self.maze[15][i] = 1
            self.maze[i][0] = 1
            self.maze[i][15] = 1

        # 4 Open Doorways
        self.maze[0][7] = 0
        self.maze[0][8] = 0
        self.maze[15][7] = 0
        self.maze[15][8] = 0
        self.maze[7][0] = 0
        self.maze[8][0] = 0
        self.maze[7][15] = 0
        self.maze[8][15] = 0

        # Interior electrified posts
        variant = self.rooms_cleared % 3
        if variant == 0:
            for y in range(4, 8):
                self.maze[y][4] = 1
            for y in range(8, 12):
                self.maze[y][11] = 1
        elif variant == 1:
            for x in range(4, 7):
                self.maze[5][x] = 1
            for x in range(9, 12):
                self.maze[10][x] = 1
        else:
            self.maze[5][5] = 1
            self.maze[5][10] = 1
            self.maze[10][5] = 1
            self.maze[10][10] = 1

        # Spawn Robots
        count = min(MAX_ROBOTS, 2 + self.rooms_cleared // 2)
        robot_spawns = [
            (3.0, 3.0),
            (12.0, 3.0),
            (3.0, 12.0),
            (12.0, 12.0),
        ]
        self.robots = []
        for i in range(MAX_ROBOTS):
            if i < count:
                self.robots.append({
                    "x": robot_spawns[i][0],
                    "y": robot_spawns[i][1],
                    "shoot_timer": 1.0 + float(i) * 0.8,
                    "active": True,
                })
            else:
                self.robots.append({
                    "x": 0.0, "y": 0.0, "shoot_timer": 0.0, "active": False,
                })

    def is_wall(self, x: int, y: int) -> bool:
        if 0 <= x < 16 and 0 <= y < 16:
            return self.maze[y][x] == 1
        return False

    def force_spawn_otto(self) -> None:
        self.otto["active"] = True
        self.otto["x"] = 8.0
        self.otto["y"] = 0.5
        self.otto["bounce_timer"] = 0.0

    def _fire_laser(self, x: float, y: float, vx: float, vy: float, is_player: bool) -> None:
        for l in self.lasers:
            if not l["active"]:
                l["x"] = x
                l["y"] = y
                l["vx"] = vx
                l["vy"] = vy
                l["is_player"] = is_player
                l["active"] = True
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

        if self.state == STATE_PLAYER_DYING:
            if self.state_timer > 1.2:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.px = 8.0
                    self.py = 8.0
                    self.state = STATE_EXPLORING
                    self.otto["active"] = False
                    self.room_timer = 0.0
            return

        if self.state == STATE_ROOM_TRANSITION:
            if self.state_timer > 0.4:
                self._generate_room()
            return

        self.room_timer += dt

        # Spawn Otto after 7 seconds in room
        if not self.otto["active"] and self.room_timer > 7.0:
            self.force_spawn_otto()

        # Fire laser
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            spd = 20.0
            self._fire_laser(
                self.px + float(self.aim_dx) * 0.8,
                self.py + float(self.aim_dy) * 0.8,
                float(self.aim_dx) * spd,
                float(self.aim_dy) * spd,
                True
            )

        self._update_player(dt, buttons)
        self._update_robots(dt)
        self._update_lasers(dt)
        self._update_evil_otto(dt)
        self._check_collisions()

    def _update_player(self, dt: float, buttons: int) -> None:
        move_spd = 5.5
        dx = 0.0
        dy = 0.0

        if buttons & KEY_LEFT:
            dx -= 1.0
            self.aim_dx = -1
            self.aim_dy = 0
        if buttons & KEY_RIGHT:
            dx += 1.0
            self.aim_dx = 1
            self.aim_dy = 0
        if buttons & KEY_UP:
            dy -= 1.0
            self.aim_dx = 0
            self.aim_dy = -1
        if buttons & KEY_DOWN:
            dy += 1.0
            self.aim_dx = 0
            self.aim_dy = 1

        self.px += dx * move_spd * dt
        self.py += dy * move_spd * dt

        # Doorway Sector Exit checks
        if self.px < 0.2 and (6.5 <= self.py <= 8.5):
            self.rooms_cleared += 1
            self.score += 100
            self.px = 14.2
            self.state = STATE_ROOM_TRANSITION
            self.state_timer = 0.0
            return
        if self.px > 14.8 and (6.5 <= self.py <= 8.5):
            self.rooms_cleared += 1
            self.score += 100
            self.px = 0.8
            self.state = STATE_ROOM_TRANSITION
            self.state_timer = 0.0
            return
        if self.py < 0.2 and (6.5 <= self.px <= 8.5):
            self.rooms_cleared += 1
            self.score += 100
            self.py = 14.2
            self.state = STATE_ROOM_TRANSITION
            self.state_timer = 0.0
            return
        if self.py > 14.8 and (6.5 <= self.px <= 8.5):
            self.rooms_cleared += 1
            self.score += 100
            self.py = 0.8
            self.state = STATE_ROOM_TRANSITION
            self.state_timer = 0.0
            return

        # Touch Electrified Wall Check
        ix = int(round(self.px))
        iy = int(round(self.py))
        if self.is_wall(ix, iy):
            self.state = STATE_PLAYER_DYING
            self.state_timer = 0.0

    def _update_robots(self, dt: float) -> None:
        for r in self.robots:
            if not r["active"]:
                continue

            dx = self.px - r["x"]
            dy = self.py - r["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > 0.1:
                step = 1.6 * dt
                r["x"] += (dx / dist) * step
                r["y"] += (dy / dist) * step

            # Walk into electric wall -> destroyed!
            rx = int(round(r["x"]))
            ry = int(round(r["y"]))
            if self.is_wall(rx, ry):
                r["active"] = False
                self.score += 50
                continue

            # Robot firing
            r["shoot_timer"] -= dt
            if r["shoot_timer"] <= 0.0:
                r["shoot_timer"] = 2.2 - min(1.0, float(self.rooms_cleared) * 0.15)
                if abs(dx) > abs(dy):
                    lvx = 12.0 if (dx > 0) else -12.0
                    lvy = 0.0
                else:
                    lvx = 0.0
                    lvy = 12.0 if (dy > 0) else -12.0
                self._fire_laser(r["x"], r["y"], lvx, lvy, False)

    def _update_lasers(self, dt: float) -> None:
        for l in self.lasers:
            if not l["active"]:
                continue
            l["x"] += l["vx"] * dt
            l["y"] += l["vy"] * dt

            lx = int(round(l["x"]))
            ly = int(round(l["y"]))

            if lx < 0 or lx >= 16 or ly < 0 or ly >= 16 or self.is_wall(lx, ly):
                l["active"] = False

    def _update_evil_otto(self, dt: float) -> None:
        if not self.otto["active"]:
            return

        self.otto["bounce_timer"] += dt * 4.0
        otto_speed = 2.2 + float(self.rooms_cleared) * 0.2

        dx = self.px - self.otto["x"]
        dy = self.py - self.otto["y"]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0.1:
            self.otto["x"] += (dx / dist) * otto_speed * dt
            self.otto["y"] += (dy / dist) * otto_speed * dt

    def _check_collisions(self) -> None:
        # 1. Lasers
        for l in self.lasers:
            if not l["active"]:
                continue

            if l["is_player"]:
                for r in self.robots:
                    if not r["active"]:
                        continue
                    dx = abs(l["x"] - r["x"])
                    dy = abs(l["y"] - r["y"])
                    if dx < 0.9 and dy < 0.9:
                        l["active"] = False
                        r["active"] = False
                        self.score += 100
                        break
            else:
                dx = abs(l["x"] - self.px)
                dy = abs(l["y"] - self.py)
                if dx < 0.8 and dy < 0.8:
                    l["active"] = False
                    self.state = STATE_PLAYER_DYING
                    self.state_timer = 0.0
                    break

        # 2. Robot body vs Player body
        for r in self.robots:
            if not r["active"]:
                continue
            dx = abs(r["x"] - self.px)
            dy = abs(r["y"] - self.py)
            if dx < 0.8 and dy < 0.8:
                self.state = STATE_PLAYER_DYING
                self.state_timer = 0.0
                break

        # 3. Evil Otto vs Player body
        if self.otto["active"]:
            dx = abs(self.otto["x"] - self.px)
            dy = abs(self.otto["y"] - self.py)
            if dx < 0.9 and dy < 0.9:
                self.state = STATE_PLAYER_DYING
                self.state_timer = 0.0

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Electrified Maze Walls
        for y in range(16):
            for x in range(16):
                if self.maze[y][x] == 1:
                    set_pixel(x, y, 40, 140, 255)

        # 2. Robots
        for r in self.robots:
            if not r["active"]:
                continue
            rx = int(round(r["x"]))
            ry = int(round(r["y"]))
            set_pixel(rx, ry, 230, 40, 30)
            set_pixel(rx, ry - 1, 255, 230, 40)

        # 3. Lasers
        for l in self.lasers:
            if not l["active"]:
                continue
            lx = int(round(l["x"]))
            ly = int(round(l["y"]))
            if l["is_player"]:
                set_pixel(lx, ly, 0, 255, 255)
            else:
                set_pixel(lx, ly, 255, 220, 0)

        # 4. Evil Otto
        if self.otto["active"]:
            ox = int(round(self.otto["x"]))
            oy = int(round(self.otto["y"] + abs(math.sin(self.otto["bounce_timer"])) * -0.6))
            set_pixel(ox, oy, 255, 220, 0)
            set_pixel(ox, oy - 1, 255, 60, 40)

        # 5. Player
        if self.state == STATE_EXPLORING:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px, py, 60, 240, 80)
            set_pixel(px, py - 1, 255, 220, 160)
            set_pixel(px + self.aim_dx, py + self.aim_dy, 220, 255, 100)
        elif self.state == STATE_PLAYER_DYING:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px - 1, py, 40, 140, 255)
            set_pixel(px + 1, py, 40, 140, 255)
            set_pixel(px, py - 1, 40, 140, 255)
            set_pixel(px, py + 1, 40, 140, 255)

        # 6. Lives HUD
        for l in range(min(self.lives, 3)):
            set_pixel(1 + l, 0, 60, 240, 80)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "rooms_cleared": self.rooms_cleared,
            "px": self.px,
            "py": self.py,
            "aim_dx": self.aim_dx,
            "aim_dy": self.aim_dy,
            "otto_active": self.otto["active"],
            "room_timer": self.room_timer,
        }
