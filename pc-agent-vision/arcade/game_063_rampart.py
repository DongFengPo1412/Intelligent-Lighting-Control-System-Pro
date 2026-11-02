"""
Game #063: 泡泡球塔防 / 绝地要塞 (Rampart 1990 / Atari)
Three-Phase Castle Defense with Naval Cannon Bombardment, Wall Reconstruction & Enclosure Flood-Fill.
"""

import math
from collections import deque
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
STATE_DEAD = 2
STATE_VICTORY = 3

PHASE_BOMBARD = 0
PHASE_REBUILD = 1

CELL_OCEAN = 0
CELL_LAND = 1
CELL_CASTLE = 2
CELL_WALL = 3
CELL_CANNON = 4

MAX_SHIPS = 3
MAX_CANNONBALLS = 4


class Game063Rampart(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 3500
        self.phase = PHASE_BOMBARD
        self.phase_timer = 8.0
        self.round = 1
        self.cursor_x = 12
        self.cursor_y = 7
        self.castle_enclosed = True
        self.cannons_count = 2
        self.ships_destroyed = 0

        self.grid = [[CELL_LAND for _ in range(16)] for _ in range(16)]
        self.ships: List[Dict[str, Any]] = []
        self.cannonballs: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 63

    @property
    def name(self) -> str:
        return "绝地要塞"

    @property
    def english_name(self) -> str:
        return "Rampart"

    @property
    def release_year(self) -> int:
        return 1990

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "筑墙合围封闭城堡 + 大炮摧毁敌舰队 + 废墟城墙限时拼图抢修"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.round = 1
        self.cannons_count = 2
        self.ships_destroyed = 0
        self.init_round()

    def init_round(self):
        self.grid = [[CELL_LAND for _ in range(16)] for _ in range(16)]

        for y in range(16):
            for x in range(10, 16):
                self.grid[y][x] = CELL_OCEAN

        # Castle keep at (4, 7) and (4, 8)
        self.grid[7][4] = CELL_CASTLE
        self.grid[8][4] = CELL_CASTLE

        # Enclosing walls
        for y in range(6, 10):
            self.grid[y][2] = CELL_WALL
            self.grid[y][6] = CELL_WALL
        for x in range(2, 7):
            self.grid[6][x] = CELL_WALL
            self.grid[9][x] = CELL_WALL

        # Cannons
        self.grid[7][6] = CELL_CANNON
        self.grid[8][6] = CELL_CANNON

        self.castle_enclosed = True
        self.phase = PHASE_BOMBARD
        self.phase_timer = 8.0
        self.cursor_x = 12
        self.cursor_y = 7

        self.cannonballs = []
        self.ships = [
            {"x": 12.0, "y": 2.0, "vy": 1.2, "health": 1, "active": True, "cooldown": 2.0},
            {"x": 14.0, "y": 6.0, "vy": -1.0, "health": 1, "active": True, "cooldown": 2.5},
            {"x": 11.0, "y": 11.0, "vy": 1.5, "health": 1, "active": True, "cooldown": 1.8},
        ]

    def fire_cannon_at_cursor(self):
        if len(self.cannonballs) < MAX_CANNONBALLS:
            self.cannonballs.append({
                "x": 6.0,
                "y": 7.5,
                "target_x": float(self.cursor_x),
                "target_y": float(self.cursor_y),
                "t": 0.0,
                "active": True
            })

    def place_wall_at_cursor(self):
        if 0 <= self.cursor_x < 10 and 0 <= self.cursor_y < 16:
            if self.grid[self.cursor_y][self.cursor_x] == CELL_LAND:
                self.grid[self.cursor_y][self.cursor_x] = CELL_WALL
                self.score += 10

    def check_enclosure(self):
        visited = [[False for _ in range(16)] for _ in range(16)]
        q = deque()

        for y in range(16):
            q.append((0, y))
            q.append((9, y))
            visited[y][0] = True
            visited[y][9] = True
        for x in range(10):
            q.append((x, 0))
            q.append((x, 15))
            visited[0][x] = True
            visited[15][x] = True

        castle_reached = False
        dxs = (1, -1, 0, 0)
        dys = (0, 0, 1, -1)

        while q:
            cx, cy = q.popleft()
            if self.grid[cy][cx] == CELL_CASTLE:
                castle_reached = True
                break

            if self.grid[cy][cx] in (CELL_WALL, CELL_CANNON):
                continue

            for i in range(4):
                nx, ny = cx + dxs[i], cy + dys[i]
                if 0 <= nx < 10 and 0 <= ny < 16 and not visited[ny][nx]:
                    visited[ny][nx] = True
                    q.append((nx, ny))

        self.castle_enclosed = not castle_reached

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 2.0:
                self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.reset()
            return

        self.phase_timer -= dt

        if self.phase == PHASE_BOMBARD:
            if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):   self.cursor_x = max(10, self.cursor_x - 1)
            if (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT): self.cursor_x = min(15, self.cursor_x + 1)
            if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):       self.cursor_y = max(0, self.cursor_y - 1)
            if (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):   self.cursor_y = min(15, self.cursor_y + 1)

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.fire_cannon_at_cursor()

            # Update ships
            for s in self.ships:
                if not s["active"]:
                    continue
                s["y"] += s["vy"] * dt
                if s["y"] < 1.0:
                    s["y"] = 1.0
                    s["vy"] = abs(s["vy"])
                elif s["y"] > 14.0:
                    s["y"] = 14.0
                    s["vy"] = -abs(s["vy"])

                s["cooldown"] -= dt
                if s["cooldown"] <= 0.0:
                    s["cooldown"] = 2.2
                    wall_x = 6
                    wall_y = max(6, min(9, int(round(s["y"]))))
                    if self.grid[wall_y][wall_x] == CELL_WALL:
                        self.grid[wall_y][wall_x] = CELL_LAND

            # Update cannonballs
            for b in self.cannonballs:
                if not b["active"]:
                    continue
                b["t"] += dt * 3.0
                b["x"] = (1.0 - b["t"]) * 6.0 + b["t"] * b["target_x"]
                b["y"] = (1.0 - b["t"]) * 7.5 + b["t"] * b["target_y"]
                if b["t"] >= 1.0:
                    b["active"] = False
                    for s in self.ships:
                        if not s["active"]:
                            continue
                        if abs(b["target_x"] - s["x"]) < 1.4 and abs(b["target_y"] - s["y"]) < 1.4:
                            s["active"] = False
                            self.ships_destroyed += 1
                            self.score += 200
                            break

            self.cannonballs = [b for b in self.cannonballs if b["active"]]

            if self.phase_timer <= 0.0:
                self.phase = PHASE_REBUILD
                self.phase_timer = 7.0
                self.cursor_x = 4
                self.cursor_y = 7

        elif self.phase == PHASE_REBUILD:
            if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):   self.cursor_x = max(0, self.cursor_x - 1)
            if (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT): self.cursor_x = min(9, self.cursor_x + 1)
            if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):       self.cursor_y = max(0, self.cursor_y - 1)
            if (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):   self.cursor_y = min(15, self.cursor_y + 1)

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.place_wall_at_cursor()

            if self.phase_timer <= 0.0:
                self.check_enclosure()
                if self.castle_enclosed:
                    self.score += 500
                    self.round += 1
                    if self.round > 3:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                    else:
                        self.phase = PHASE_BOMBARD
                        self.phase_timer = 8.0
                        self.cursor_x = 12
                        self.cursor_y = 7
                else:
                    self.state = STATE_DEAD
                    self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                cell = self.grid[y][x]
                if cell == CELL_OCEAN:
                    fb[idx] = 20;  fb[idx + 1] = 60;  fb[idx + 2] = 160
                elif cell == CELL_LAND:
                    fb[idx] = 60;  fb[idx + 1] = 140; fb[idx + 2] = 40
                elif cell == CELL_CASTLE:
                    fb[idx] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0
                elif cell == CELL_WALL:
                    fb[idx] = 180; fb[idx + 1] = 180; fb[idx + 2] = 190
                elif cell == CELL_CANNON:
                    fb[idx] = 50;  fb[idx + 1] = 50;  fb[idx + 2] = 50

        # Ships
        for s in self.ships:
            if s["active"]:
                sx = int(round(s["x"]))
                sy = int(round(s["y"]))
                if 0 <= sx < 16 and 0 <= sy < 16:
                    idx = (sy * 16 + sx) * 3
                    fb[idx] = 140; fb[idx + 1] = 80; fb[idx + 2] = 30
                    if sx < 15:
                        s_idx = (sy * 16 + (sx + 1)) * 3
                        fb[s_idx] = 255; fb[s_idx + 1] = 255; fb[s_idx + 2] = 255

        # Cannonballs
        for b in self.cannonballs:
            if b["active"]:
                bx = int(round(b["x"]))
                by = int(round(b["y"]))
                if 0 <= bx < 16 and 0 <= by < 16:
                    idx = (by * 16 + bx) * 3
                    fb[idx] = 255; fb[idx + 1] = 100; fb[idx + 2] = 0

        # Cursor
        if 0 <= self.cursor_x < 16 and 0 <= self.cursor_y < 16:
            idx = (self.cursor_y * 16 + self.cursor_x) * 3
            if self.phase == PHASE_BOMBARD:
                fb[idx] = 255; fb[idx + 1] = 0;   fb[idx + 2] = 0
            else:
                fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255

        # HUD
        time_bars = int((self.phase_timer / 8.0) * 10.0)
        for t in range(min(time_bars, 10)):
            idx = t * 3
            fb[idx] = 255 if self.phase == PHASE_BOMBARD else 0
            fb[idx + 1] = 100 if self.phase == PHASE_BOMBARD else 255
            fb[idx + 2] = 0 if self.phase == PHASE_BOMBARD else 255

        for r in range(min(self.round, 3)):
            idx = (15 - r) * 3
            fb[idx] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "phase": self.phase,
            "round": self.round,
            "castle_enclosed": self.castle_enclosed,
            "ships_destroyed": self.ships_destroyed,
        }
