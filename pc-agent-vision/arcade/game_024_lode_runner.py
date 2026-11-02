# -*- coding: utf-8 -*-
"""
game_024_lode_runner.py —— 淘金者 1983 (Lode Runner 1983)
编号: #024
年代: 1983 (Brøderbund)
核心独占机制: 左右掘坑陷阱 + 活埋警卫再生 + 踏头过坑 + 收集全金显现逃生天梯
手柄类型: CTRL_ARCADE_AB (方向键跑动/攀爬 + A键左下掘坑 / B键右下掘坑)
"""

from typing import Dict, Any, List, Optional
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

LODE_AIR = 0
LODE_BRICK = 1
LODE_SOLID = 2
LODE_LADDER = 3
LODE_BAR = 4
LODE_HOLE = 5


class Game024LodeRunner(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.grid: List[List[int]] = [[LODE_AIR for _ in range(16)] for _ in range(16)]
        self.player_x: float = 1.0
        self.player_y: float = 14.0
        self.player_dir: int = 1
        self.lives: int = 3
        self.move_timer: float = 0.0

        self.holes: List[Dict[str, Any]] = []
        self.guards: List[Dict[str, Any]] = []
        self.golds: List[Dict[str, Any]] = []

        self.escape_ladder_revealed: bool = False
        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 24

    @property
    def name(self) -> str:
        return "淘金者"

    @property
    def english_name(self) -> str:
        return "Lode Runner 1983"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "左右掘坑陷阱 + 活埋警卫再生 + 踏头过坑 + 收集全金显现逃生天梯"

    def init(self) -> None:
        self.reset()

    def init_level(self):
        self.grid = [[LODE_AIR for _ in range(16)] for _ in range(16)]

        for x in range(16):
            self.grid[15][x] = LODE_SOLID

        for x in range(13):
            self.grid[11][x] = LODE_BRICK
        for x in range(3, 16):
            self.grid[7][x] = LODE_BRICK
        for x in range(11):
            self.grid[3][x] = LODE_BRICK

        for y in range(11, 15):
            self.grid[y][11] = LODE_LADDER
        for y in range(7, 12):
            self.grid[y][4] = LODE_LADDER
        for y in range(3, 8):
            self.grid[y][9] = LODE_LADDER

        for x in range(10, 14):
            self.grid[5][x] = LODE_BAR

        self.golds = [
            {"collected": False, "x": 1, "y": 10},
            {"collected": False, "x": 14, "y": 6},
            {"collected": False, "x": 5, "y": 2},
        ]

        self.player_x = 1.0
        self.player_y = 14.0
        self.player_dir = 1
        self.move_timer = 0.0
        self.escape_ladder_revealed = False

        self.holes = []
        self.guards = [
            {"active": True, "x": 12.0, "y": 10.0, "move_timer": 0.0, "trapped": False, "trap_timer": 0.0},
            {"active": True, "x": 14.0, "y": 6.0, "move_timer": 0.0, "trapped": False, "trap_timer": 0.0},
        ]

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.init_level()

    def can_walk(self, x: int, y: int) -> bool:
        if not (0 <= x < 16 and 0 <= y < 16):
            return False
        t = self.grid[y][x]
        return t in (LODE_AIR, LODE_LADDER, LODE_BAR, LODE_HOLE)

    def can_fall(self, x: int, y: int) -> bool:
        if y >= 14:
            return False
        cur = self.grid[y][x]
        if cur in (LODE_LADDER, LODE_BAR):
            return False

        below = self.grid[y + 1][x]
        if below in (LODE_AIR, LODE_HOLE):
            for guard in self.guards:
                if guard["active"] and guard["trapped"]:
                    if int(round(guard["x"])) == x and int(round(guard["y"])) == y + 1:
                        return False
            return True
        return False

    def dig_hole(self, dx: int):
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        hx = px + dx
        hy = py + 1

        if not (0 <= hx < 16 and 0 <= hy < 16):
            return

        if self.grid[hy][hx] == LODE_BRICK and self.grid[py][hx] == LODE_AIR:
            if len(self.holes) < 4:
                self.holes.append({"active": True, "x": hx, "y": hy, "timer": 4.5})
                self.grid[hy][hx] = LODE_HOLE
                self.score += 20
                if self.score > self.high_score:
                    self.high_score = self.score

    def update_holes(self, dt: float):
        for hole in self.holes:
            if not hole["active"]:
                continue
            hole["timer"] -= dt
            if hole["timer"] <= 0.0:
                hole["active"] = False
                hx = hole["x"]
                hy = hole["y"]
                self.grid[hy][hx] = LODE_BRICK

                for guard in self.guards:
                    if guard["active"] and guard["trapped"]:
                        if int(round(guard["x"])) == hx and int(round(guard["y"])) == hy:
                            guard["trapped"] = False
                            guard["x"] = 7.0
                            guard["y"] = 1.0
                            self.score += 200
                            if self.score > self.high_score:
                                self.high_score = self.score

        self.holes = [h for h in self.holes if h["active"]]

    def update_guards(self, dt: float):
        for guard in self.guards:
            if not guard["active"]:
                continue

            gx = int(round(guard["x"]))
            gy = int(round(guard["y"]))

            if guard["trapped"]:
                guard["trap_timer"] -= dt
                if guard["trap_timer"] <= 0.0:
                    guard["trapped"] = False
                    guard["y"] = float(gy - 1)
                continue

            if self.grid[gy][gx] == LODE_HOLE:
                guard["trapped"] = True
                guard["trap_timer"] = 3.5
                self.score += 80
                if self.score > self.high_score:
                    self.high_score = self.score
                continue

            if self.can_fall(gx, gy):
                guard["move_timer"] += dt
                if guard["move_timer"] >= 0.12:
                    guard["move_timer"] = 0.0
                    guard["y"] += 1.0
                continue

            guard["move_timer"] += dt
            if guard["move_timer"] >= 0.26:
                guard["move_timer"] = 0.0

                target_dx = 0
                target_dy = 0

                if guard["y"] < self.player_y and self.grid[gy][gx] == LODE_LADDER:
                    target_dy = 1
                elif guard["y"] > self.player_y and (self.grid[gy][gx] == LODE_LADDER or (gy > 0 and self.grid[gy - 1][gx] == LODE_LADDER)):
                    target_dy = -1
                elif guard["x"] < self.player_x:
                    target_dx = 1
                elif guard["x"] > self.player_x:
                    target_dx = -1

                nx = gx + target_dx
                ny = gy + target_dy

                if target_dy != 0 and self.can_walk(gx, ny):
                    guard["y"] = float(ny)
                elif target_dx != 0 and self.can_walk(nx, gy):
                    guard["x"] = float(nx)

            if not guard["trapped"]:
                if int(round(guard["x"])) == int(round(self.player_x)) and int(round(guard["y"])) == int(round(self.player_y)):
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                    else:
                        self.player_x = 1.0
                        self.player_y = 14.0
                        return

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
                self.reset()
            return

        if self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            if keys_pressed & KEY_A:
                self.dig_hole(-1)
            if keys_pressed & KEY_B:
                self.dig_hole(1)

            px = int(round(self.player_x))
            py = int(round(self.player_y))

            if self.can_fall(px, py):
                self.move_timer += dt
                if self.move_timer >= 0.10:
                    self.move_timer = 0.0
                    self.player_y += 1.0
            else:
                self.move_timer += dt
                if self.move_timer >= 0.16:
                    dx = 0
                    dy = 0
                    if keys_down & KEY_UP:
                        dy = -1
                    elif keys_down & KEY_DOWN:
                        dy = 1
                    elif keys_down & KEY_LEFT:
                        dx = -1
                    elif keys_down & KEY_RIGHT:
                        dx = 1

                    if dx != 0 or dy != 0:
                        self.move_timer = 0.0
                        nx = px + dx
                        ny = py + dy

                        if dy != 0:
                            if self.grid[py][px] == LODE_LADDER or (dy < 0 and ny >= 0 and self.grid[ny][px] == LODE_LADDER) or (self.escape_ladder_revealed and px == 2 and 0 <= ny <= 3):
                                if self.can_walk(px, ny):
                                    self.player_y = float(ny)
                        elif dx != 0:
                            self.player_dir = 1 if dx > 0 else -1
                            if self.can_walk(nx, py):
                                self.player_x = float(nx)

            all_collected = True
            for gold in self.golds:
                if not gold["collected"]:
                    if int(round(self.player_x)) == gold["x"] and int(round(self.player_y)) == gold["y"]:
                        gold["collected"] = True
                        self.score += 150
                        if self.score > self.high_score:
                            self.high_score = self.score
                    else:
                        all_collected = False

            if all_collected and not self.escape_ladder_revealed:
                self.escape_ladder_revealed = True
                for y in range(4):
                    self.grid[y][2] = LODE_LADDER
                self.score += 300
                if self.score > self.high_score:
                    self.high_score = self.score

            if self.escape_ladder_revealed and int(round(self.player_x)) == 2 and self.player_y <= 0.5:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 1000
                if self.score > self.high_score:
                    self.high_score = self.score

            self.update_holes(dt)
            self.update_guards(dt)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 1. 砖块、基岩、爬梯、滑索
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                t = self.grid[y][x]
                if t == LODE_BRICK:
                    buf[idx:idx+3] = bytes([180, 80, 40])
                elif t == LODE_SOLID:
                    buf[idx:idx+3] = bytes([127, 140, 141])
                elif t == LODE_LADDER:
                    buf[idx:idx+3] = bytes([52, 152, 219])
                elif t == LODE_BAR:
                    buf[idx:idx+3] = bytes([241, 196, 15])
                elif t == LODE_HOLE:
                    buf[idx:idx+3] = bytes([30, 20, 15])

        # 2. 金矿
        for gold in self.golds:
            if not gold["collected"]:
                idx = (gold["y"] * 16 + gold["x"]) * 3
                buf[idx:idx+3] = bytes([255, 215, 0])

        # 3. 警卫
        for guard in self.guards:
            if not guard["active"]:
                continue
            gx = int(round(guard["x"]))
            gy = int(round(guard["y"]))
            if 0 <= gx < 16 and 0 <= gy < 16:
                idx = (gy * 16 + gx) * 3
                if guard["trapped"]:
                    buf[idx:idx+3] = bytes([192, 57, 43])
                else:
                    buf[idx:idx+3] = bytes([231, 76, 60])

        # 4. 淘金者
        if self.lives > 0:
            px = int(round(self.player_x))
            py = int(round(self.player_y))
            if 0 <= px < 16 and 0 <= py < 16:
                idx = (py * 16 + px) * 3
                buf[idx:idx+3] = bytes([255, 255, 255])

        # 5. 生命
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx:idx+3] = bytes([255, 255, 255])

        # 6. 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx:idx+3] = bytes([231, 76, 60])

        return bytes(buf)

    def get_status(self) -> Dict[str, Any]:
        gathered = sum(1 for g in self.golds if g["collected"])
        total = len(self.golds)
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": int((gathered * 100) / total) if total > 0 else 100,
            "escape_ladder": self.escape_ladder_revealed,
        }
