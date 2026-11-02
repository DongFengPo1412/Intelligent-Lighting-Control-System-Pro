"""
Game #041: 涂鸦滚刷 (Crush Roller / Make Trax 1981 / Kural / Williams)
Full Surface Road Painting with Chasing Monsters & Steamroller Anti-Chase Crush Traps.
"""

from typing import List, Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
)

STATE_START = 0
STATE_PLAYING = 1
STATE_DEAD = 2
STATE_VICTORY = 3

DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]


class Game041CrushRoller(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.unpainted_tiles = 0
        self.total_paint_tiles = 0

        self.player_x = 1.0
        self.player_y = 1.0
        self.player_dir = 1
        self.next_dir = 1

        self.rollers: List[Dict[str, Any]] = []
        self.monsters: List[Dict[str, Any]] = []
        self.maze: List[List[int]] = [[0 for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 41

    @property
    def name(self) -> str:
        return "涂鸦滚刷"

    @property
    def english_name(self) -> str:
        return "Crush Roller 1981"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "街道地面滚涂覆漆 + 重型压路机陷阱碾碎追兵 + 100%全图涂覆通关"

    def init(self) -> None:
        self.reset()

    def init_maze(self):
        self.maze = [[0 for _ in range(16)] for _ in range(16)]

        road_rows = [1, 5, 9, 14]
        road_cols = [1, 5, 10, 14]

        for ry in road_rows:
            for x in range(1, 15):
                self.maze[ry][x] = 1

        for cx in road_cols:
            for y in range(1, 15):
                self.maze[y][cx] = 1

        self.unpainted_tiles = sum(row.count(1) for row in self.maze)
        self.total_paint_tiles = self.unpainted_tiles

        self.paint_tile(1, 1)

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_x = 1.0
        self.player_y = 1.0
        self.player_dir = 1
        self.next_dir = 1

        self.init_maze()

        self.rollers = [
            {"x": 5.0, "y": 5.0, "dir": 0, "active": True, "cooldown": 0.0},
            {"x": 10.0, "y": 9.0, "dir": 0, "active": True, "cooldown": 0.0},
        ]

        self.monsters = [
            {"x": 14.0, "y": 14.0, "dir": 3, "active": True, "respawn_timer": 0.0},
            {"x": 14.0, "y": 1.0, "dir": 2, "active": True, "respawn_timer": 0.0},
        ]

    def paint_tile(self, x: int, y: int):
        if 0 <= x < 16 and 0 <= y < 16:
            if self.maze[y][x] == 1:
                self.maze[y][x] = 2
                self.unpainted_tiles -= 1
                self.score += 10
                if self.score > self.high_score:
                    self.high_score = self.score

                if self.unpainted_tiles == 0:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 1000
                    if self.score > self.high_score:
                        self.high_score = self.score

    def trigger_roller(self, idx: int) -> bool:
        if 0 <= idx < len(self.rollers):
            r = self.rollers[idx]
            if r["active"] and r["dir"] == 0 and r["cooldown"] <= 0.0:
                r["dir"] = self.player_dir + 1
                return True
        return False

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 1.0
                    self.player_y = 1.0
                    self.player_dir = 1
                    self.next_dir = 1
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
                self.reset()
            return

        self.update_player(dt, buttons)
        self.update_rollers(dt)
        self.update_monsters(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int):
        if buttons & KEY_UP:
            self.next_dir = 0
        elif buttons & KEY_RIGHT:
            self.next_dir = 1
        elif buttons & KEY_DOWN:
            self.next_dir = 2
        elif buttons & KEY_LEFT:
            self.next_dir = 3

        speed = 4.2
        gx = round(self.player_x)
        gy = round(self.player_y)
        dist_to_center = abs(self.player_x - gx) + abs(self.player_y - gy)

        if dist_to_center < 0.25 and self.next_dir != self.player_dir:
            nx = int(gx) + DX[self.next_dir]
            ny = int(gy) + DY[self.next_dir]
            if 0 <= nx < 16 and 0 <= ny < 16 and self.maze[ny][nx] != 0:
                self.player_x = float(gx)
                self.player_y = float(gy)
                self.player_dir = self.next_dir

        next_x = self.player_x + DX[self.player_dir] * speed * dt
        next_y = self.player_y + DY[self.player_dir] * speed * dt

        check_x = int(round(next_x + DX[self.player_dir] * 0.45))
        check_y = int(round(next_y + DY[self.player_dir] * 0.45))

        if 0 <= check_x < 16 and 0 <= check_y < 16 and self.maze[check_y][check_x] != 0:
            self.player_x = next_x
            self.player_y = next_y
        else:
            self.player_x = float(gx)
            self.player_y = float(gy)

        self.paint_tile(int(round(self.player_x)), int(round(self.player_y)))

        for i, r in enumerate(self.rollers):
            if r["dir"] == 0 and r["cooldown"] <= 0.0:
                dist = abs(self.player_x - r["x"]) + abs(self.player_y - r["y"])
                if dist <= 0.85:
                    self.trigger_roller(i)

    def update_rollers(self, dt: float):
        roller_speed = 12.0

        for i, r in enumerate(self.rollers):
            if r["cooldown"] > 0.0:
                r["cooldown"] -= dt

            if r["dir"] == 0:
                continue

            dir_idx = r["dir"] - 1
            r["x"] += DX[dir_idx] * roller_speed * dt
            r["y"] += DY[dir_idx] * roller_speed * dt

            check_x = int(round(r["x"] + DX[dir_idx] * 0.5))
            check_y = int(round(r["y"] + DY[dir_idx] * 0.5))

            if not (0 <= check_x < 16 and 0 <= check_y < 16) or self.maze[check_y][check_x] == 0:
                r["dir"] = 0
                r["cooldown"] = 4.0
                if i == 0:
                    r["x"], r["y"] = 5.0, 5.0
                else:
                    r["x"], r["y"] = 10.0, 9.0
                continue

            for m in self.monsters:
                if m["active"]:
                    dist = abs(r["x"] - m["x"]) + abs(r["y"] - m["y"])
                    if dist <= 1.1:
                        m["active"] = False
                        m["respawn_timer"] = 4.0
                        self.score += 400
                        if self.score > self.high_score:
                            self.high_score = self.score

    def update_monsters(self, dt: float):
        speed = 3.2

        for m in self.monsters:
            if not m["active"]:
                m["respawn_timer"] -= dt
                if m["respawn_timer"] <= 0.0:
                    m["active"] = True
                    m["x"] = 14.0
                    m["y"] = 14.0
                continue

            mgx = round(m["x"])
            mgy = round(m["y"])
            dist_to_center = abs(m["x"] - mgx) + abs(m["y"] - mgy)

            if dist_to_center < 0.22:
                best_dir = m["dir"]
                min_dist = 99999.0
                opp_dir = (m["dir"] + 2) % 4

                for d in range(4):
                    nx = int(mgx) + DX[d]
                    ny = int(mgy) + DY[d]
                    if 0 <= nx < 16 and 0 <= ny < 16 and self.maze[ny][nx] != 0:
                        penalty = 10.0 if d == opp_dir else 0.0
                        d2 = (nx - self.player_x) ** 2 + (ny - self.player_y) ** 2 + penalty
                        if d2 < min_dist:
                            min_dist = d2
                            best_dir = d

                m["x"] = float(mgx)
                m["y"] = float(mgy)
                m["dir"] = best_dir

            m["x"] += DX[m["dir"]] * speed * dt
            m["y"] += DY[m["dir"]] * speed * dt

    def check_collisions(self):
        for m in self.monsters:
            if m["active"]:
                dist = abs(self.player_x - m["x"]) + abs(self.player_y - m["y"])
                if dist <= 0.72:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                tile = self.maze[y][x]
                if tile == 0:
                    fb[idx:idx + 3] = bytes([30, 55, 153]) # Dark blue block
                elif tile == 1:
                    fb[idx:idx + 3] = bytes([74, 85, 104]) # Unpainted
                elif tile == 2:
                    fb[idx:idx + 3] = bytes([241, 196, 15]) # Golden painted

        # Rollers
        for r in self.rollers:
            if r["active"]:
                rx = int(round(r["x"]))
                ry = int(round(r["y"]))
                if 0 <= rx < 16 and 0 <= ry < 16:
                    idx = (ry * 16 + rx) * 3
                    if r["dir"] != 0:
                        fb[idx:idx + 3] = bytes([230, 126, 34]) # Charging orange
                    else:
                        fb[idx:idx + 3] = bytes([0, 206, 209])  # Parked steel cyan

        # Monsters
        for m in self.monsters:
            if m["active"]:
                mx = int(round(m["x"]))
                my = int(round(m["y"]))
                if 0 <= mx < 16 and 0 <= my < 16:
                    idx = (my * 16 + mx) * 3
                    fb[idx:idx + 3] = bytes([231, 76, 60])

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx:idx + 3] = bytes([255, 255, 255])

        # Lives
        for l in range(min(self.lives, 3)):
            idx = (0 * 16 + l) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "unpainted": self.unpainted_tiles,
            "total_tiles": self.total_paint_tiles,
            "player_pos": (self.player_x, self.player_y),
        }
