"""
Game #110: 魔鬼世界 (Devil World 1984 / Nintendo)
Dynamic maze screen shifting commanded by the overhead Devil,
pinch crush avoidance, Holy Cross fire-breathing, and fried egg devouring.
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

STATE_NAVIGATING = 0
STATE_CRUSHED = 1
STATE_ROUND_CLEAR = 2
STATE_GAME_OVER = 3

MAZE_WIDTH = 16
MAZE_HEIGHT = 16
MAX_MONSTERS = 2


class Game110DevilWorld(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_NAVIGATING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.pearls_remaining = 0

        self.px = 8.0
        self.py = 8.0
        self.facing_x = 1
        self.facing_y = 0
        self.has_cross = False
        self.fire_breath_timer = 0.0

        self.devil_point_dir = 0
        self.devil_timer = 2.5

        self.cross_x = 8.0
        self.cross_y = 12.0
        self.cross_spawned = True

        self.maze: List[List[int]] = []
        self.monsters: List[Dict[str, Any]] = []
        self._dir_cycle = 0

        self.reset()

    @property
    def game_id(self) -> int:
        return 110

    @property
    def name(self) -> str:
        return "魔鬼世界"

    @property
    def english_name(self) -> str:
        return "Devil World"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "大魔王顶部指点江山与迷宫四向挤压碾碎、十字架喷火煎蛋吞食"

    def get_name(self) -> str:
        return "Devil World (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._init_maze()

    def _init_maze(self) -> None:
        self.state = STATE_NAVIGATING
        self.state_timer = 0.0
        self.pearls_remaining = 0
        self.has_cross = False
        self.fire_breath_timer = 0.0

        self.px = 8.0
        self.py = 8.0
        self.facing_x = 1
        self.facing_y = 0

        self.devil_point_dir = 0
        self.devil_timer = 2.5

        self.cross_x = 8.0
        self.cross_y = 12.0
        self.cross_spawned = True

        self.maze = [[0 for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]

        # Outer walls
        for x in range(16):
            self.maze[2][x] = 1
            self.maze[15][x] = 1
        for y in range(2, 16):
            self.maze[y][0] = 1
            self.maze[y][15] = 1

        blocks = [
            (4, 5, 6, 6),
            (9, 5, 11, 6),
            (4, 9, 6, 10),
            (9, 9, 11, 10),
            (7, 4, 8, 5),
            (7, 10, 8, 11),
        ]
        for x1, y1, x2, y2 in blocks:
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    self.maze[y][x] = 1

        for y in range(3, 15):
            for x in range(1, 15):
                if self.maze[y][x] == 0 and (x + y) % 2 == 0:
                    self.maze[y][x] = 2
                    self.pearls_remaining += 1

        self.monsters = [
            {
                "x": 3.0,
                "y": 4.0,
                "vx": 2.2,
                "vy": 0.0,
                "is_fried_egg": False,
                "egg_timer": 0.0,
                "active": True,
            },
            {
                "x": 12.0,
                "y": 13.0,
                "vx": -2.2,
                "vy": 0.0,
                "is_fried_egg": False,
                "egg_timer": 0.0,
                "active": True,
            },
        ]

    def set_devil_direction(self, direction: int) -> None:
        self.devil_point_dir = direction

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_CRUSHED:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_NAVIGATING
                    self.state_timer = 0.0
                    self.px = 8.0
                    self.py = 8.0
                    self.devil_point_dir = 0
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 2.5:
                self.round += 1
                self._init_maze()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_devil(dt)
        self._update_tamagon(dt, buttons, prev_buttons)
        self._update_monsters(dt)
        self._check_collisions()
        self._check_wall_crush()

        if self.pearls_remaining <= 0 and self.state != STATE_ROUND_CLEAR:
            self.state = STATE_ROUND_CLEAR
            self.state_timer = 0.0
            self.score += 1500

    def _update_devil(self, dt: float) -> None:
        self.devil_timer -= dt
        if self.devil_timer <= 0.0:
            self.devil_timer = 2.5
            self.devil_point_dir = (self._dir_cycle % 4) + 1
            self._dir_cycle += 1

        shift_spd = 1.4
        if self.devil_point_dir == 1:
            self.px -= shift_spd * dt
            for m in self.monsters:
                m["x"] -= shift_spd * dt
        elif self.devil_point_dir == 2:
            self.px += shift_spd * dt
            for m in self.monsters:
                m["x"] += shift_spd * dt
        elif self.devil_point_dir == 3:
            self.py -= shift_spd * dt
            for m in self.monsters:
                m["y"] -= shift_spd * dt
        elif self.devil_point_dir == 4:
            self.py += shift_spd * dt
            for m in self.monsters:
                m["y"] += shift_spd * dt

    def _update_tamagon(self, dt: float, buttons: int, prev_buttons: int) -> None:
        move_spd = 5.0
        next_x = self.px
        next_y = self.py

        if buttons & KEY_LEFT:
            next_x -= move_spd * dt
            self.facing_x = -1
            self.facing_y = 0
        elif buttons & KEY_RIGHT:
            next_x += move_spd * dt
            self.facing_x = 1
            self.facing_y = 0
        elif buttons & KEY_UP:
            next_y -= move_spd * dt
            self.facing_x = 0
            self.facing_y = -1
        elif buttons & KEY_DOWN:
            next_y += move_spd * dt
            self.facing_x = 0
            self.facing_y = 1

        cx = int(round(next_x))
        cy = int(round(next_y))
        if 0 <= cx < 16 and 0 <= cy < 16:
            if self.maze[cy][cx] != 1:
                self.px = next_x
                self.py = next_y

        if self.cross_spawned:
            if abs(self.px - self.cross_x) < 1.0 and abs(self.py - self.cross_y) < 1.0:
                self.has_cross = True
                self.cross_spawned = False
                self.score += 300

        grid_x = int(round(self.px))
        grid_y = int(round(self.py))
        if 1 <= grid_x < 15 and 3 <= grid_y < 15:
            if self.maze[grid_y][grid_x] == 2:
                self.maze[grid_y][grid_x] = 0
                self.pearls_remaining -= 1
                self.score += 10

        if self.fire_breath_timer > 0.0:
            self.fire_breath_timer -= dt

        if (buttons & KEY_A) and self.has_cross and self.fire_breath_timer <= 0.0:
            self.fire_breath_timer = 0.4
            fire_x = self.px + float(self.facing_x) * 1.5
            fire_y = self.py + float(self.facing_y) * 1.5
            for m in self.monsters:
                if not m["active"]:
                    continue
                if abs(m["x"] - fire_x) < 1.3 and abs(m["y"] - fire_y) < 1.3:
                    m["is_fried_egg"] = True
                    m["egg_timer"] = 5.0
                    self.score += 100

    def _update_monsters(self, dt: float) -> None:
        for m in self.monsters:
            if not m["active"]:
                continue
            if m["is_fried_egg"]:
                m["egg_timer"] -= dt
                if m["egg_timer"] <= 0.0:
                    m["is_fried_egg"] = False
                continue

            m["x"] += m["vx"] * dt
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            if mx <= 1 or mx >= 14 or (0 <= my < 16 and self.maze[my][mx] == 1):
                m["vx"] = -m["vx"]

    def _check_collisions(self) -> None:
        for m in self.monsters:
            if not m["active"]:
                continue
            dx = abs(self.px - m["x"])
            dy = abs(self.py - m["y"])
            if dx < 0.9 and dy < 0.9:
                if m["is_fried_egg"]:
                    m["active"] = False
                    self.score += 400
                else:
                    self.state = STATE_CRUSHED
                    self.state_timer = 0.0
                    return

    def _check_wall_crush(self) -> None:
        if self.px <= 0.6 or self.px >= 14.4 or self.py <= 2.2 or self.py >= 14.4:
            self.state = STATE_CRUSHED
            self.state_timer = 0.0

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

        for x in range(16):
            set_pixel(x, 1, 80, 20, 20)
        set_pixel(7, 0, 220, 30, 20)
        set_pixel(8, 0, 255, 60, 40)
        set_pixel(6, 0, 255, 220, 0)
        set_pixel(9, 0, 255, 220, 0)

        if self.devil_point_dir == 1:
            set_pixel(5, 0, 255, 255, 255)
        elif self.devil_point_dir == 2:
            set_pixel(10, 0, 255, 255, 255)
        elif self.devil_point_dir == 3:
            set_pixel(7, 0, 255, 255, 255)
        elif self.devil_point_dir == 4:
            set_pixel(8, 1, 255, 255, 255)

        for y in range(2, 16):
            for x in range(16):
                cell = self.maze[y][x]
                if cell == 1:
                    set_pixel(x, y, 120, 40, 160)
                elif cell == 2:
                    set_pixel(x, y, 255, 220, 40)

        if self.cross_spawned:
            cx = int(round(self.cross_x))
            cy = int(round(self.cross_y))
            set_pixel(cx, cy, 255, 255, 255)
            set_pixel(cx, cy - 1, 255, 220, 0)
            set_pixel(cx - 1, cy, 255, 220, 0)
            set_pixel(cx + 1, cy, 255, 220, 0)

        for m in self.monsters:
            if not m["active"]:
                continue
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            if m["is_fried_egg"]:
                set_pixel(mx, my, 255, 200, 20)
                set_pixel(mx - 1, my, 240, 240, 250)
                set_pixel(mx + 1, my, 240, 240, 250)
            else:
                set_pixel(mx, my, 40, 100, 240)
                set_pixel(mx - 1, my, 60, 140, 255)
                set_pixel(mx + 1, my, 60, 140, 255)

        tx = int(round(self.px))
        ty = int(round(self.py))

        if self.state == STATE_CRUSHED:
            set_pixel(tx - 1, ty, 60, 200, 60)
            set_pixel(tx, ty, 255, 50, 40)
            set_pixel(tx + 1, ty, 60, 200, 60)
        else:
            set_pixel(tx, ty, 40, 220, 50)
            set_pixel(tx, ty - 1, 50, 240, 70)
            if self.has_cross:
                set_pixel(tx + self.facing_x, ty, 255, 220, 0)
            if self.fire_breath_timer > 0.0:
                set_pixel(tx + self.facing_x * 2, ty + self.facing_y * 2, 255, 80, 20)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 40, 220, 50)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "round": self.round,
            "px": self.px,
            "py": self.py,
            "has_cross": self.has_cross,
            "devil_point_dir": self.devil_point_dir,
            "pearls_remaining": self.pearls_remaining,
        }
