# -*- coding: utf-8 -*-
"""
Game #134: 动物园管理员 (Zoo Keeper 1982 / Taito)
街机历史上最经典的外环修墙筑牢与跳跃避兽益智动作游戏：
外环跑道环绕兽笼、按键A涂砌砖墙封堵缺口、按键B跳跃闪避逃窜猛兽、获取捕捉网回捕狮猴。
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

STATE_PLAYING = 0
STATE_LEVEL_CLEAR = 1
STATE_CAUGHT = 2
STATE_GAME_OVER = 3

TRACK_MIN = 1.0
TRACK_MAX = 14.0
WALL_MIN = 2
WALL_MAX = 13
CAGE_INNER_MIN = 2.5
CAGE_INNER_MAX = 12.5

NUM_ANIMALS = 4


class Game134ZooKeeper(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1
        self.time_left = 30.0

        # Zeke player state
        # pos on perimeter: track_pos in [0.0, 52.0)
        # Perimeter has 4 sides of length 13: 
        # Side 0: Top (y=1, x: 1->14, pos: 0..13)
        # Side 1: Right (x=14, y: 1->14, pos: 13..26)
        # Side 2: Bottom (y=14, x: 14->1, pos: 26..39)
        # Side 3: Left (x=1, y: 14->1, pos: 39..52)
        self.track_pos = 0.0
        self.px = 1.0
        self.py = 1.0
        self.is_jumping = False
        self.jump_timer = 0.0
        self.net_timer = 0.0

        # Brick walls: 16x16 boolean grid. Intact wall = True
        self.walls = [[False for _ in range(16)] for _ in range(16)]

        # Animals: each animal can be INSIDE cage or ESCAPED on track
        self.animals: List[Dict[str, Any]] = []

        # Net bonus item on track
        self.net_spawned = False
        self.net_pos = 26.0  # Bottom middle
        self.net_respawn_timer = 8.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 134

    @property
    def name(self) -> str:
        return "动物园管理员"

    @property
    def english_name(self) -> str:
        return "Zoo Keeper"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "外环巡逻筑砖补笼、跳跃跨越出逃猛兽、持网捕兽与时限防守"

    def get_name(self) -> str:
        return "Zoo Keeper (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_walls(self) -> None:
        for y in range(16):
            for x in range(16):
                self.walls[y][x] = False

        # Top wall: y=2, x=2..13
        for x in range(WALL_MIN, WALL_MAX + 1):
            self.walls[WALL_MIN][x] = True
        # Bottom wall: y=13, x=2..13
        for x in range(WALL_MIN, WALL_MAX + 1):
            self.walls[WALL_MAX][x] = True
        # Left wall: x=2, y=2..13
        for y in range(WALL_MIN, WALL_MAX + 1):
            self.walls[y][WALL_MIN] = True
        # Right wall: x=13, y=2..13
        for y in range(WALL_MIN, WALL_MAX + 1):
            self.walls[y][WALL_MAX] = True

    def _track_pos_to_xy(self, pos: float) -> tuple[float, float]:
        pos = pos % 52.0
        if pos < 13.0:
            # Top: x from 1 to 14, y = 1
            return (TRACK_MIN + pos, TRACK_MIN)
        elif pos < 26.0:
            # Right: x = 14, y from 1 to 14
            return (TRACK_MAX, TRACK_MIN + (pos - 13.0))
        elif pos < 39.0:
            # Bottom: x from 14 down to 1, y = 14
            return (TRACK_MAX - (pos - 26.0), TRACK_MAX)
        else:
            # Left: x = 1, y from 14 down to 1
            return (TRACK_MIN, TRACK_MAX - (pos - 39.0))

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.time_left = 30.0

        self.track_pos = 0.0
        self.px, self.py = self._track_pos_to_xy(self.track_pos)
        self.is_jumping = False
        self.jump_timer = 0.0
        self.net_timer = 0.0

        self._init_walls()

        # Create animals inside cage
        self.animals = []
        base_speed = 3.5 + self.level * 0.4
        dirs = [
            (base_speed * 0.7, base_speed * 0.7),
            (-base_speed * 0.8, base_speed * 0.6),
            (base_speed * 0.6, -base_speed * 0.8),
            (-base_speed * 0.7, -base_speed * 0.7),
        ]
        types = [0, 1, 0, 1]  # 0: Lion (Red), 1: Gorilla (Magenta)
        for i in range(NUM_ANIMALS):
            self.animals.append({
                "x": 5.0 + (i % 2) * 5.0,
                "y": 5.0 + (i // 2) * 5.0,
                "vx": dirs[i][0],
                "vy": dirs[i][1],
                "type": types[i],
                "escaped": False,
                "track_pos": 0.0,
                "track_dir": 1.0,
            })

        self.net_spawned = True
        self.net_pos = 26.0
        self.net_respawn_timer = 10.0

    def _get_adjacent_wall_coord(self, px: float, py: float) -> tuple[int, int]:
        ix = int(round(px))
        iy = int(round(py))
        ix = max(1, min(14, ix))
        iy = max(1, min(14, iy))

        if iy == 1:
            return (ix, WALL_MIN)
        elif iy == 14:
            return (ix, WALL_MAX)
        elif ix == 1:
            return (WALL_MIN, iy)
        elif ix == 14:
            return (WALL_MAX, iy)
        return (ix, iy)

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_LEVEL_CLEAR, STATE_CAUGHT):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_LEVEL_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_CAUGHT:
                    if self.lives > 0:
                        self._init_level()
                    else:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.state_timer += dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()

    def _update_playing(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.time_left -= dt
        if self.time_left <= 0.0:
            self.time_left = 0.0
            self.score += 1000
            self.state = STATE_LEVEL_CLEAR
            self.state_timer = 0.0
            return

        # Jump update
        if self.is_jumping:
            self.jump_timer -= dt
            if self.jump_timer <= 0.0:
                self.is_jumping = False
                self.jump_timer = 0.0
        else:
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.is_jumping = True
                self.jump_timer = 0.5  # half second jump

        # Net timer update
        if self.net_timer > 0.0:
            self.net_timer -= dt
            if self.net_timer < 0.0:
                self.net_timer = 0.0

        # Player track movement:
        # Check current track side to map arrow keys naturally:
        # Side 0 (Top, pos 0..13): RIGHT moves clockwise (+pos), LEFT moves counter-clockwise (-pos)
        # Side 1 (Right, pos 13..26): DOWN moves clockwise (+pos), UP moves counter-clockwise (-pos)
        # Side 2 (Bottom, pos 26..39): LEFT moves clockwise (+pos), RIGHT moves counter-clockwise (-pos)
        # Side 3 (Left, pos 39..52): UP moves clockwise (+pos), DOWN moves counter-clockwise (-pos)
        move_speed = 7.0  # units per sec
        delta_pos = 0.0

        pos = self.track_pos % 52.0
        if pos < 13.0 or pos == 52.0:
            # Top
            if buttons & KEY_RIGHT:
                delta_pos += move_speed * dt
            if buttons & KEY_LEFT:
                delta_pos -= move_speed * dt
            if pos <= 0.5 and (buttons & KEY_DOWN):
                delta_pos -= move_speed * dt
            elif pos >= 12.5 and (buttons & KEY_DOWN):
                delta_pos += move_speed * dt
        elif pos < 26.0:
            # Right
            if buttons & KEY_DOWN:
                delta_pos += move_speed * dt
            if buttons & KEY_UP:
                delta_pos -= move_speed * dt
            if pos <= 13.5 and (buttons & KEY_LEFT):
                delta_pos -= move_speed * dt
            elif pos >= 25.5 and (buttons & KEY_LEFT):
                delta_pos += move_speed * dt
        elif pos < 39.0:
            # Bottom
            if buttons & KEY_LEFT:
                delta_pos += move_speed * dt
            if buttons & KEY_RIGHT:
                delta_pos -= move_speed * dt
            if pos <= 26.5 and (buttons & KEY_UP):
                delta_pos -= move_speed * dt
            elif pos >= 38.5 and (buttons & KEY_UP):
                delta_pos += move_speed * dt
        else:
            # Left
            if buttons & KEY_UP:
                delta_pos += move_speed * dt
            if buttons & KEY_DOWN:
                delta_pos -= move_speed * dt
            if pos <= 39.5 and (buttons & KEY_RIGHT):
                delta_pos -= move_speed * dt
            elif pos >= 51.5 and (buttons & KEY_RIGHT):
                delta_pos += move_speed * dt

        self.track_pos = (self.track_pos + delta_pos) % 52.0
        self.px, self.py = self._track_pos_to_xy(self.track_pos)

        # Brick building / repairing with Key A
        if buttons & KEY_A:
            wx, wy = self._get_adjacent_wall_coord(self.px, self.py)
            if 0 <= wx < 16 and 0 <= wy < 16:
                if not self.walls[wy][wx]:
                    self.walls[wy][wx] = True
                    self.score += 15

        # Net spawn & pickup
        if not self.net_spawned and self.net_timer <= 0.0:
            self.net_respawn_timer -= dt
            if self.net_respawn_timer <= 0.0:
                self.net_spawned = True
                self.net_pos = (self.track_pos + 26.0) % 52.0
                self.net_respawn_timer = 12.0

        if self.net_spawned:
            dist_to_net = abs(self.track_pos - self.net_pos)
            if dist_to_net > 26.0:
                dist_to_net = 52.0 - dist_to_net
            if dist_to_net < 1.2:
                self.net_spawned = False
                self.net_timer = 6.0
                self.score += 100

        # Update Animals
        for animal in self.animals:
            if not animal["escaped"]:
                # Moving inside cage
                nx = animal["x"] + animal["vx"] * dt
                ny = animal["y"] + animal["vy"] * dt

                # Check collision with walls
                # Top wall: y=2
                if ny <= CAGE_INNER_MIN:
                    ix = int(round(animal["x"]))
                    ix = max(WALL_MIN, min(WALL_MAX, ix))
                    if self.walls[WALL_MIN][ix]:
                        # Bounce and chip wall
                        animal["vy"] = abs(animal["vy"])
                        self.walls[WALL_MIN][ix] = False
                    else:
                        # Escape through gap!
                        animal["escaped"] = True
                        animal["track_pos"] = (ix - TRACK_MIN) % 52.0
                        animal["track_dir"] = 1.0 if animal["vx"] >= 0 else -1.0
                # Bottom wall: y=13
                elif ny >= CAGE_INNER_MAX:
                    ix = int(round(animal["x"]))
                    ix = max(WALL_MIN, min(WALL_MAX, ix))
                    if self.walls[WALL_MAX][ix]:
                        animal["vy"] = -abs(animal["vy"])
                        self.walls[WALL_MAX][ix] = False
                    else:
                        animal["escaped"] = True
                        animal["track_pos"] = (26.0 + (TRACK_MAX - ix)) % 52.0
                        animal["track_dir"] = 1.0 if animal["vx"] <= 0 else -1.0
                # Left wall: x=2
                elif nx <= CAGE_INNER_MIN:
                    iy = int(round(animal["y"]))
                    iy = max(WALL_MIN, min(WALL_MAX, iy))
                    if self.walls[iy][WALL_MIN]:
                        animal["vx"] = abs(animal["vx"])
                        self.walls[iy][WALL_MIN] = False
                    else:
                        animal["escaped"] = True
                        animal["track_pos"] = (39.0 + (TRACK_MAX - iy)) % 52.0
                        animal["track_dir"] = 1.0 if animal["vy"] <= 0 else -1.0
                # Right wall: x=13
                elif nx >= CAGE_INNER_MAX:
                    iy = int(round(animal["y"]))
                    iy = max(WALL_MIN, min(WALL_MAX, iy))
                    if self.walls[iy][WALL_MAX]:
                        animal["vx"] = -abs(animal["vx"])
                        self.walls[iy][WALL_MAX] = False
                    else:
                        animal["escaped"] = True
                        animal["track_pos"] = (13.0 + (iy - TRACK_MIN)) % 52.0
                        animal["track_dir"] = 1.0 if animal["vy"] >= 0 else -1.0
                else:
                    animal["x"] = nx
                    animal["y"] = ny
            else:
                # Escaped animal patrols outer track
                escape_speed = 5.0
                animal["track_pos"] = (animal["track_pos"] + animal["track_dir"] * escape_speed * dt) % 52.0
                ax, ay = self._track_pos_to_xy(animal["track_pos"])
                animal["x"] = ax
                animal["y"] = ay

                # Interaction with Zeke
                dist = math.hypot(self.px - ax, self.py - ay)
                if dist < 1.1:
                    if self.net_timer > 0.0:
                        # Capture animal back into cage!
                        animal["escaped"] = False
                        animal["x"] = 7.5
                        animal["y"] = 7.5
                        animal["vx"] = 3.5 if animal["track_dir"] > 0 else -3.5
                        animal["vy"] = 3.0
                        self.score += 250
                    elif not self.is_jumping:
                        # Caught by wild animal!
                        self.lives -= 1
                        self.state = STATE_CAUGHT
                        self.state_timer = 0.0
                        return
                    else:
                        # Cleanly jumped over beast!
                        self.score += 50

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

        # 1. Draw outer perimeter track border lightly
        for x in range(1, 15):
            set_pixel(x, 1, 15, 25, 20)
            set_pixel(x, 14, 15, 25, 20)
        for y in range(1, 15):
            set_pixel(1, y, 15, 25, 20)
            set_pixel(14, y, 15, 25, 20)

        # 2. Draw brick walls
        for y in range(16):
            for x in range(16):
                if self.walls[y][x]:
                    # Warm brick orange-brown
                    set_pixel(x, y, 200, 110, 40)

        # 3. Draw Net bonus if spawned
        if self.net_spawned:
            nx, ny = self._track_pos_to_xy(self.net_pos)
            set_pixel(int(round(nx)), int(round(ny)), 255, 255, 60)

        # 4. Draw Animals
        for animal in self.animals:
            ax = int(round(animal["x"]))
            ay = int(round(animal["y"]))
            if animal["escaped"]:
                # Escaped beast flashes aggressively (Red / Orange)
                set_pixel(ax, ay, 255, 60, 30)
            else:
                if animal["type"] == 0:
                    # Lion (Yellow-Red)
                    set_pixel(ax, ay, 240, 150, 20)
                else:
                    # Gorilla (Purple-Magenta)
                    set_pixel(ax, ay, 180, 50, 220)

        # 5. Draw Player (Zeke)
        zx = int(round(self.px))
        zy = int(round(self.py))
        if self.is_jumping:
            # Jumping: bright cyan-white
            set_pixel(zx, zy, 200, 255, 255)
        elif self.net_timer > 0.0:
            # Holding net: glowing yellow-cyan
            set_pixel(zx, zy, 255, 240, 50)
        else:
            # Normal Zeke: Blue
            set_pixel(zx, zy, 40, 160, 255)

        # 6. Status flashes if CAUGHT or LEVEL CLEAR
        if self.state == STATE_CAUGHT:
            # Flash red border
            flash = int(self.state_timer * 10) % 2
            if flash == 0:
                for x in range(16):
                    set_pixel(x, 0, 220, 30, 30)
                    set_pixel(x, 15, 220, 30, 30)
        elif self.state == STATE_LEVEL_CLEAR:
            flash = int(self.state_timer * 10) % 2
            if flash == 0:
                for x in range(16):
                    set_pixel(x, 0, 30, 220, 60)
                    set_pixel(x, 15, 30, 220, 60)

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
            "time_left": self.time_left,
            "px": self.px,
            "py": self.py,
            "track_pos": self.track_pos,
            "is_jumping": self.is_jumping,
            "has_net": self.net_timer > 0.0,
        }
