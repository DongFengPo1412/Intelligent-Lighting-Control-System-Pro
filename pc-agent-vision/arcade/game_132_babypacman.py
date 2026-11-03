# -*- coding: utf-8 -*-
"""
Game #132: 幼年吃豆人弹珠台 (Baby Pac-Man 1982 / Bally Midway)
街机历史上绝无仅有的视频迷宫与实体弹珠台混合机台鼻祖：
无大力丸无助吃豆迷宫、底部通道穿梭降落弹珠台、击打挡板与目标槽解锁大力丸、返航吞噬幽灵。
"""

from typing import List, Dict, Any, Optional
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

MODE_MAZE = 0
MODE_PINBALL = 1

STATE_PLAYING = 0
STATE_DEATH = 1
STATE_MAZE_CLEAR = 2
STATE_GAME_OVER = 3

NUM_GHOSTS = 3
NUM_TARGETS = 3


class Game132BabyPacman(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.mode = MODE_MAZE
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7.5
        self.py = 11.0
        self.p_dir_x = 0
        self.p_dir_y = -1
        self.next_dir_x = 0
        self.next_dir_y = -1

        self.frightened_timer = 0.0
        self.energizers_earned = 0
        self.energizer_active = [False, False]

        self.dots = [[False] * 16 for _ in range(16)]
        self.remaining_dots = 0

        self.ghosts: List[Dict[str, Any]] = []
        self.ball = {"x": 14.0, "y": 12.0, "vx": -4.0, "vy": -14.0, "in_play": False}
        self.pinball_targets = [False] * NUM_TARGETS

        self.reset()

    @property
    def game_id(self) -> int:
        return 132

    @property
    def name(self) -> str:
        return "幼年吃豆人弹珠台"

    @property
    def english_name(self) -> str:
        return "Baby Pac-Man"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "迷宫与弹珠双模式穿梭、底部暗道入场弹珠台击打目标解锁大力丸、返航吞噬幽灵"

    def get_name(self) -> str:
        return "Baby Pac-Man (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_maze()

    def _init_maze(self) -> None:
        self.mode = MODE_MAZE
        self.state = STATE_PLAYING
        self.state_timer = 0.0

        self.px = 7.5
        self.py = 11.0
        self.p_dir_x = 0
        self.p_dir_y = -1
        self.next_dir_x = 0
        self.next_dir_y = -1

        self.frightened_timer = 0.0
        self.energizers_earned = 0
        self.energizer_active = [False, False]

        self.remaining_dots = 0
        self.dots = [[False] * 16 for _ in range(16)]
        for y in range(16):
            for x in range(16):
                is_corridor = (y in (2, 6, 11) or x in (2, 7, 13))
                if is_corridor and (1 <= y <= 13) and (1 <= x <= 14):
                    self.dots[y][x] = True
                    self.remaining_dots += 1

        self.dots[11][7] = False
        self.remaining_dots -= 1

        self.ghosts = [
            {"x": 7.5, "y": 5.0, "dir_x": 1, "dir_y": 0, "frightened": False},
            {"x": 3.0, "y": 6.0, "dir_x": 0, "dir_y": -1, "frightened": False},
            {"x": 12.0, "y": 6.0, "dir_x": 0, "dir_y": 1, "frightened": False},
        ]

        self.pinball_targets = [False] * NUM_TARGETS

    def start_pinball(self) -> None:
        self.mode = MODE_PINBALL
        self.ball["in_play"] = True
        self.ball["x"] = 14.0
        self.ball["y"] = 12.0
        self.ball["vx"] = -4.0
        self.ball["vy"] = -14.0

    def return_to_maze(self) -> None:
        self.mode = MODE_MAZE
        self.px = 7.5
        self.py = 13.0
        self.p_dir_x = 0
        self.p_dir_y = -1

        if self.energizers_earned >= 1:
            self.energizer_active[0] = True
        if self.energizers_earned >= 2:
            self.energizer_active[1] = True

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

        if self.state == STATE_DEATH:
            if self.state_timer > 1.3:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 11.0
                    self.p_dir_x = 0
                    self.p_dir_y = -1
                    self.ghosts[0] = {"x": 7.5, "y": 5.0, "dir_x": 1, "dir_y": 0, "frightened": False}
                    self.ghosts[1] = {"x": 3.0, "y": 6.0, "dir_x": 0, "dir_y": -1, "frightened": False}
                    self.ghosts[2] = {"x": 12.0, "y": 6.0, "dir_x": 0, "dir_y": 1, "frightened": False}
            return

        if self.state == STATE_MAZE_CLEAR:
            if self.state_timer > 1.6:
                self.level += 1
                self.score += 1500
                self._init_maze()
            return

        if self.mode == MODE_MAZE:
            self._update_maze(dt, buttons)
        else:
            self._update_pinball(dt, buttons)

    def _update_maze(self, dt: float, buttons: int) -> None:
        if buttons & KEY_UP:
            self.next_dir_x = 0
            self.next_dir_y = -1
        elif buttons & KEY_DOWN:
            self.next_dir_x = 0
            self.next_dir_y = 1
        elif buttons & KEY_LEFT:
            self.next_dir_x = -1
            self.next_dir_y = 0
        elif buttons & KEY_RIGHT:
            self.next_dir_x = 1
            self.next_dir_y = 0

        if self.next_dir_x != 0 or self.next_dir_y != 0:
            self.p_dir_x = self.next_dir_x
            self.p_dir_y = self.next_dir_y

        speed = 5.8 if (self.frightened_timer > 0.0) else 5.0
        self.px += self.p_dir_x * speed * dt
        self.py += self.p_dir_y * speed * dt

        if self.py >= 14.5 and abs(self.px - 7.5) < 1.5:
            self.start_pinball()
            return

        if self.px < 1.0:
            self.px = 1.0
        elif self.px > 14.0:
            self.px = 14.0
        if self.py < 1.0:
            self.py = 1.0
        elif self.py > 14.0:
            self.py = 14.0

        ix = int(round(self.px))
        iy = int(round(self.py))
        if 0 <= ix < 16 and 0 <= iy < 16:
            if self.dots[iy][ix]:
                self.dots[iy][ix] = False
                self.score += 10
                self.remaining_dots -= 1

        if self.energizer_active[0] and abs(self.px - 2.0) < 0.8 and abs(self.py - 2.0) < 0.8:
            self.energizer_active[0] = False
            self.frightened_timer = 6.0
            self.score += 50

        if self.energizer_active[1] and abs(self.px - 13.0) < 0.8 and abs(self.py - 2.0) < 0.8:
            self.energizer_active[1] = False
            self.frightened_timer = 6.0
            self.score += 50

        if self.frightened_timer > 0.0:
            self.frightened_timer -= dt

        for g in self.ghosts:
            g["frightened"] = (self.frightened_timer > 0.0)
            g_spd = 2.5 if g["frightened"] else (4.0 + self.level * 0.2)
            g["x"] += g["dir_x"] * g_spd * dt
            g["y"] += g["dir_y"] * g_spd * dt

            if g["x"] < 2.0:
                g["x"] = 2.0
                g["dir_x"] = 1
            elif g["x"] > 13.0:
                g["x"] = 13.0
                g["dir_x"] = -1

            if g["y"] < 2.0:
                g["y"] = 2.0
                g["dir_y"] = 1
            elif g["y"] > 11.0:
                g["y"] = 11.0
                g["dir_y"] = -1

        self._check_maze_collisions()

        if self.remaining_dots <= 0:
            self.state = STATE_MAZE_CLEAR
            self.state_timer = 0.0

    def _check_maze_collisions(self) -> None:
        for g in self.ghosts:
            dx = abs(self.px - g["x"])
            dy = abs(self.py - g["y"])
            if dx < 0.8 and dy < 0.8:
                if g["frightened"]:
                    g["x"] = 7.5
                    g["y"] = 6.0
                    g["frightened"] = False
                    self.score += 200
                else:
                    self.state = STATE_DEATH
                    self.state_timer = 0.0
                    break

    def _update_pinball(self, dt: float, buttons: int) -> None:
        self.ball["vy"] += 16.0 * dt
        self.ball["vx"] *= 0.99
        self.ball["x"] += self.ball["vx"] * dt
        self.ball["y"] += self.ball["vy"] * dt

        left_flip = (buttons & (KEY_LEFT | KEY_A)) != 0
        right_flip = (buttons & (KEY_RIGHT | KEY_B)) != 0

        if 13.0 <= self.ball["y"] <= 14.5:
            if left_flip and 2.0 <= self.ball["x"] <= 6.5:
                self.ball["vy"] = -13.0
                self.ball["vx"] += 3.5
                self.score += 20
            if right_flip and 8.5 <= self.ball["x"] <= 13.0:
                self.ball["vy"] = -13.0
                self.ball["vx"] -= 3.5
                self.score += 20

        if self.ball["x"] <= 1.5:
            self.ball["x"] = 1.5
            self.ball["vx"] = -self.ball["vx"] * 0.85
        elif self.ball["x"] >= 14.5:
            self.ball["x"] = 14.5
            self.ball["vx"] = -self.ball["vx"] * 0.85

        if self.ball["y"] <= 1.5:
            self.ball["y"] = 1.5
            self.ball["vy"] = -self.ball["vy"] * 0.85

        # Bumpers
        for bx, by in [(5.0, 7.0), (10.0, 7.0)]:
            dx = self.ball["x"] - bx
            dy = self.ball["y"] - by
            if math.sqrt(dx * dx + dy * dy) < 1.3:
                self.ball["vx"] += (5.0 if dx > 0 else -5.0)
                self.ball["vy"] = -8.0
                self.score += 50

        # Targets
        target_x = [4.0, 7.5, 11.0]
        for t in range(3):
            if not self.pinball_targets[t]:
                if abs(self.ball["y"] - 3.0) < 0.8 and abs(self.ball["x"] - target_x[t]) < 0.9:
                    self.pinball_targets[t] = True
                    self.ball["vy"] = 4.0
                    self.score += 100
                    self.energizers_earned += 1

        if self.ball["y"] >= 15.5:
            self.return_to_maze()

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
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

        if self.mode == MODE_MAZE:
            for y in range(16):
                for x in range(16):
                    if self.dots[y][x]:
                        set_pixel(x, y, 255, 180, 160)

            if self.energizer_active[0]:
                set_pixel(2, 2, 255, 255, 255)
                set_pixel(2, 3, 255, 220, 50)
            if self.energizer_active[1]:
                set_pixel(13, 2, 255, 255, 255)
                set_pixel(13, 3, 255, 220, 50)

            set_pixel(7, 14, 0, 255, 200)
            set_pixel(8, 14, 0, 255, 200)

            for g_idx, g in enumerate(self.ghosts):
                gx = int(round(g["x"]))
                gy = int(round(g["y"]))
                if g["frightened"]:
                    set_pixel(gx, gy, 40, 60, 255)
                    set_pixel(gx, gy - 1, 255, 255, 255)
                else:
                    if g_idx == 0:
                        set_pixel(gx, gy, 255, 40, 40)
                    elif g_idx == 1:
                        set_pixel(gx, gy, 255, 120, 200)
                    else:
                        set_pixel(gx, gy, 40, 220, 255)

            px_s = int(round(self.px))
            py_s = int(round(self.py))
            set_pixel(px_s, py_s, 255, 255, 0)
            set_pixel(px_s, py_s - 1, 255, 100, 180)
        else:
            for p in range(16):
                set_pixel(1, p, 100, 40, 20)
                set_pixel(14, p, 100, 40, 20)
                set_pixel(p, 1, 100, 40, 20)

            target_x = [4.0, 7.5, 11.0]
            for t in range(3):
                tx = int(round(target_x[t]))
                if not self.pinball_targets[t]:
                    set_pixel(tx, 3, 255, 220, 0)
                else:
                    set_pixel(tx, 3, 60, 60, 60)

            set_pixel(5, 7, 255, 40, 60)
            set_pixel(10, 7, 255, 40, 60)

            for x in range(3, 7):
                set_pixel(x, 14, 0, 220, 255)
            for x in range(9, 13):
                set_pixel(x, 14, 0, 220, 255)

            bx = int(round(self.ball["x"]))
            by = int(round(self.ball["y"]))
            set_pixel(bx, by, 255, 255, 255)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 255, 255, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "mode": self.mode,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "remaining_dots": self.remaining_dots,
            "energizers_earned": self.energizers_earned,
            "px": self.px,
            "py": self.py,
        }
