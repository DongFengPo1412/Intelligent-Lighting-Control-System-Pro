# -*- coding: utf-8 -*-
"""
game_021_dig_dug.py —— 掘地打气人 1982 (Dig Dug 1982)
编号: #021
年代: 1982 (南梦宫 Namco)
核心独占机制: 地底自由隧道挖掘 + 鱼叉充气引爆 + 巨石塌陷碾压 + 喷火伏击
手柄类型: CTRL_ARCADE_AB (方向键挖掘/移动 + A键刺叉/充气引爆)
"""

import random
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

TILE_EMPTY = 0
TILE_DIRT = 1
TILE_ROCK = 2

ENEMY_POOKA = 0
ENEMY_FYGAR = 1

DX = [0, 1, 0, -1]  # UP, RIGHT, DOWN, LEFT
DY = [-1, 0, 1, 0]


class Game021DigDug(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.grid: List[List[int]] = [[TILE_DIRT for _ in range(16)] for _ in range(16)]
        self.player_x: int = 7
        self.player_y: int = 7
        self.player_dir: int = 1
        self.player_lives: int = 3
        self.move_timer: float = 0.0

        self.harpoon: Dict[str, Any] = {
            "active": False,
            "origin_x": 7,
            "origin_y": 7,
            "dir": 1,
            "target_idx": -1,
            "timer": 0.0,
        }

        self.enemies: List[Dict[str, Any]] = []
        self.rocks: List[Dict[str, Any]] = []

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 21

    @property
    def name(self) -> str:
        return "掘地打气人"

    @property
    def english_name(self) -> str:
        return "Dig Dug 1982"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "地底自由隧道挖掘 + 鱼叉充气引爆 + 巨石塌陷碾压 + 喷火伏击"

    def init(self) -> None:
        self.reset()

    def init_level(self):
        # 1. 地面与地下
        self.grid = [[TILE_DIRT for _ in range(16)] for _ in range(16)]
        for x in range(16):
            self.grid[0][x] = TILE_EMPTY

        # 2. 玩家出生小室
        self.player_x = 7
        self.player_y = 7
        self.player_dir = 1
        self.move_timer = 0.0
        for y in range(5, 8):
            self.grid[y][7] = TILE_EMPTY
        self.grid[7][6] = TILE_EMPTY
        self.grid[7][8] = TILE_EMPTY

        # 3. 怪物洞窟
        # 怪物 0: 红色波卡 (左上)
        for x in range(2, 5):
            self.grid[3][x] = TILE_EMPTY
        # 怪物 1: 喷火飞加 (右下)
        for x in range(11, 14):
            self.grid[11][x] = TILE_EMPTY
        # 怪物 2: 红色波卡 (左下)
        for x in range(3, 6):
            self.grid[12][x] = TILE_EMPTY
        # 怪物 3: 喷火飞加 (右上)
        for x in range(10, 13):
            self.grid[4][x] = TILE_EMPTY

        self.enemies = [
            {
                "active": True,
                "type": ENEMY_POOKA,
                "x": 3.0,
                "y": 3.0,
                "dir": 1,
                "inflate_stage": 0,
                "inflate_timer": 0.0,
                "move_timer": 0.0,
                "firing": False,
                "fire_timer": 0.0,
            },
            {
                "active": True,
                "type": ENEMY_FYGAR,
                "x": 12.0,
                "y": 11.0,
                "dir": 3,
                "inflate_stage": 0,
                "inflate_timer": 0.0,
                "move_timer": 0.0,
                "firing": False,
                "fire_timer": 0.0,
            },
            {
                "active": True,
                "type": ENEMY_POOKA,
                "x": 4.0,
                "y": 12.0,
                "dir": 1,
                "inflate_stage": 0,
                "inflate_timer": 0.0,
                "move_timer": 0.0,
                "firing": False,
                "fire_timer": 0.0,
            },
            {
                "active": True,
                "type": ENEMY_FYGAR,
                "x": 11.0,
                "y": 4.0,
                "dir": 3,
                "inflate_stage": 0,
                "inflate_timer": 0.0,
                "move_timer": 0.0,
                "firing": False,
                "fire_timer": 0.0,
            },
        ]

        # 4. 巨石布置
        self.rocks = [
            {"active": True, "x": 4, "y": 2, "falling": False, "shake_timer": 0.0},
            {"active": True, "x": 12, "y": 8, "falling": False, "shake_timer": 0.0},
        ]
        self.grid[2][4] = TILE_ROCK
        self.grid[8][12] = TILE_ROCK

        self.harpoon = {
            "active": False,
            "origin_x": 7,
            "origin_y": 7,
            "dir": 1,
            "target_idx": -1,
            "timer": 0.0,
        }

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.player_lives = 3
        self.state_timer = 0.0
        self.init_level()

    def pump_target(self):
        if not self.harpoon["active"]:
            hx = self.player_x
            hy = self.player_y
            for _ in range(2):
                hx += DX[self.player_dir]
                hy += DY[self.player_dir]
                if not (0 <= hx < 16 and 0 <= hy < 16):
                    break
                if self.grid[hy][hx] in (TILE_DIRT, TILE_ROCK):
                    break

                for i, enemy in enumerate(self.enemies):
                    if enemy["active"]:
                        ex = int(round(enemy["x"]))
                        ey = int(round(enemy["y"]))
                        if ex == hx and ey == hy:
                            self.harpoon["active"] = True
                            self.harpoon["origin_x"] = self.player_x
                            self.harpoon["origin_y"] = self.player_y
                            self.harpoon["dir"] = self.player_dir
                            self.harpoon["target_idx"] = i
                            self.harpoon["timer"] = 0.8
                            enemy["inflate_stage"] = 1
                            enemy["inflate_timer"] = 0.9
                            return
        else:
            tidx = self.harpoon["target_idx"]
            if 0 <= tidx < len(self.enemies) and self.enemies[tidx]["active"]:
                self.enemies[tidx]["inflate_stage"] += 1
                self.enemies[tidx]["inflate_timer"] = 0.9
                self.harpoon["timer"] = 0.8

                if self.enemies[tidx]["inflate_stage"] >= 3:
                    self.enemies[tidx]["active"] = False
                    self.harpoon["active"] = False
                    self.score += 200
                    if self.score > self.high_score:
                        self.high_score = self.score
            else:
                self.harpoon["active"] = False

    def update_rocks(self, dt: float):
        for rock in self.rocks:
            if not rock["active"]:
                continue

            rx = rock["x"]
            ry = rock["y"]

            if not rock["falling"]:
                if ry < 15 and self.grid[ry + 1][rx] == TILE_EMPTY:
                    rock["shake_timer"] += dt
                    if rock["shake_timer"] >= 0.7:
                        rock["falling"] = True
                        self.grid[ry][rx] = TILE_EMPTY
                else:
                    rock["shake_timer"] = 0.0
            else:
                rock["shake_timer"] += dt
                if rock["shake_timer"] >= 0.12:
                    rock["shake_timer"] = 0.0
                    next_y = ry + 1
                    if next_y < 16 and self.grid[next_y][rx] not in (TILE_DIRT, TILE_ROCK):
                        self.grid[ry][rx] = TILE_EMPTY
                        rock["y"] = next_y
                        self.grid[next_y][rx] = TILE_ROCK

                        # 碾压怪物
                        for enemy in self.enemies:
                            if enemy["active"]:
                                ex = int(round(enemy["x"]))
                                ey = int(round(enemy["y"]))
                                if ex == rx and ey == next_y:
                                    enemy["active"] = False
                                    self.score += 500
                                    if self.score > self.high_score:
                                        self.high_score = self.score

                        # 碾压玩家
                        if self.player_x == rx and self.player_y == next_y:
                            self.player_lives -= 1
                            if self.player_lives <= 0:
                                self.state = STATE_GAMEOVER
                                self.state_timer = 0.0
                                return
                            else:
                                self.player_x = 7
                                self.player_y = 7
                    else:
                        rock["active"] = False

    def update_enemies(self, dt: float):
        any_alive = False

        for i, enemy in enumerate(self.enemies):
            if not enemy["active"]:
                continue
            any_alive = True

            # 膨胀管理
            if enemy["inflate_stage"] > 0:
                enemy["inflate_timer"] -= dt
                if enemy["inflate_timer"] <= 0.0:
                    enemy["inflate_stage"] -= 1
                    enemy["inflate_timer"] = 0.6
                    if enemy["inflate_stage"] == 0 and self.harpoon["active"] and self.harpoon["target_idx"] == i:
                        self.harpoon["active"] = False
                continue

            # 飞加喷火
            if enemy["type"] == ENEMY_FYGAR:
                enemy["fire_timer"] += dt
                if not enemy["firing"] and enemy["fire_timer"] > 3.5:
                    enemy["firing"] = True
                    enemy["fire_timer"] = 0.0
                elif enemy["firing"]:
                    if enemy["fire_timer"] > 1.2:
                        enemy["firing"] = False
                        enemy["fire_timer"] = 0.0
                    else:
                        fx = int(round(enemy["x"]))
                        fy = int(round(enemy["y"]))
                        fdir = enemy["dir"]
                        for _ in range(2):
                            fx += DX[fdir]
                            fy += DY[fdir]
                            if not (0 <= fx < 16 and 0 <= fy < 16):
                                break
                            if self.grid[fy][fx] == TILE_DIRT:
                                break
                            if self.player_x == fx and self.player_y == fy:
                                self.player_lives -= 1
                                if self.player_lives <= 0:
                                    self.state = STATE_GAMEOVER
                                    self.state_timer = 0.0
                                    return
                                else:
                                    self.player_x = 7
                                    self.player_y = 7

            # 移动巡逻
            enemy["move_timer"] += dt
            if enemy["move_timer"] >= 0.28:
                enemy["move_timer"] = 0.0
                ex = int(round(enemy["x"]))
                ey = int(round(enemy["y"]))

                next_x = ex + DX[enemy["dir"]]
                next_y = ey + DY[enemy["dir"]]

                can_walk = (0 <= next_x < 16 and 0 <= next_y < 16 and
                            self.grid[next_y][next_x] == TILE_EMPTY)

                if not can_walk:
                    new_dir = random.randint(0, 3)
                    for t in range(4):
                        d = (new_dir + t) % 4
                        nx = ex + DX[d]
                        ny = ey + DY[d]
                        if 0 <= nx < 16 and 0 <= ny < 16 and self.grid[ny][nx] == TILE_EMPTY:
                            enemy["dir"] = d
                            next_x = nx
                            next_y = ny
                            can_walk = True
                            break

                if can_walk:
                    enemy["x"] = float(next_x)
                    enemy["y"] = float(next_y)

                if int(round(enemy["x"])) == self.player_x and int(round(enemy["y"])) == self.player_y:
                    self.player_lives -= 1
                    if self.player_lives <= 0:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                    else:
                        self.player_x = 7
                        self.player_y = 7

        if not any_alive:
            self.state = STATE_VICTORY
            self.state_timer = 0.0

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

            if self.harpoon["active"]:
                self.harpoon["timer"] -= dt
                if self.harpoon["timer"] <= 0.0:
                    self.harpoon["active"] = False

            if keys_pressed & KEY_A:
                self.pump_target()

            self.move_timer += dt
            if self.move_timer >= 0.16:
                target_dir = -1
                if keys_down & KEY_UP:
                    target_dir = 0
                elif keys_down & KEY_RIGHT:
                    target_dir = 1
                elif keys_down & KEY_DOWN:
                    target_dir = 2
                elif keys_down & KEY_LEFT:
                    target_dir = 3

                if target_dir != -1:
                    self.move_timer = 0.0
                    self.player_dir = target_dir
                    nx = self.player_x + DX[target_dir]
                    ny = self.player_y + DY[target_dir]

                    if 0 <= nx < 16 and 0 <= ny < 16:
                        if self.grid[ny][nx] != TILE_ROCK:
                            self.player_x = nx
                            self.player_y = ny
                            if self.grid[ny][nx] == TILE_DIRT:
                                self.grid[ny][nx] = TILE_EMPTY
                                self.score += 10
                                if self.score > self.high_score:
                                    self.high_score = self.score

            self.update_rocks(dt)
            self.update_enemies(dt)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 1. 泥土与背景
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                t = self.grid[y][x]
                if t == TILE_EMPTY:
                    if y == 0:
                        buf[idx:idx+3] = bytes([52, 152, 219])
                    else:
                        buf[idx:idx+3] = bytes([18, 18, 22])
                elif t == TILE_DIRT:
                    if y <= 4:
                        buf[idx:idx+3] = bytes([160, 90, 40])
                    elif y <= 9:
                        buf[idx:idx+3] = bytes([130, 70, 25])
                    else:
                        buf[idx:idx+3] = bytes([95, 48, 18])
                elif t == TILE_ROCK:
                    buf[idx:idx+3] = bytes([149, 165, 166])

        # 2. 怪物
        for enemy in self.enemies:
            if not enemy["active"]:
                continue
            ex = int(round(enemy["x"]))
            ey = int(round(enemy["y"]))
            if not (0 <= ex < 16 and 0 <= ey < 16):
                continue

            idx = (ey * 16 + ex) * 3
            if enemy["inflate_stage"] > 0:
                g = 220 if enemy["inflate_stage"] == 1 else 100
                b = 50 if enemy["inflate_stage"] == 1 else 200
                buf[idx:idx+3] = bytes([255, g, b])
            elif enemy["type"] == ENEMY_POOKA:
                buf[idx:idx+3] = bytes([231, 76, 60])
            else:
                buf[idx:idx+3] = bytes([46, 204, 113])

            if enemy["type"] == ENEMY_FYGAR and enemy["firing"]:
                fx = ex
                fy = ey
                for _ in range(2):
                    fx += DX[enemy["dir"]]
                    fy += DY[enemy["dir"]]
                    if 0 <= fx < 16 and 0 <= fy < 16 and self.grid[fy][fx] == TILE_EMPTY:
                        fidx = (fy * 16 + fx) * 3
                        buf[fidx:fidx+3] = bytes([243, 156, 18])

        # 3. 鱼叉
        if self.harpoon["active"]:
            hx = self.player_x + DX[self.player_dir]
            hy = self.player_y + DY[self.player_dir]
            if 0 <= hx < 16 and 0 <= hy < 16:
                idx = (hy * 16 + hx) * 3
                buf[idx:idx+3] = bytes([255, 255, 255])

        # 4. 玩家
        if self.player_lives > 0:
            idx = (self.player_y * 16 + self.player_x) * 3
            buf[idx:idx+3] = bytes([255, 255, 255])

        # 5. 生命
        for i in range(self.player_lives):
            idx = (0 * 16 + (15 - i)) * 3
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
        alive = sum(1 for e in self.enemies if e["active"])
        total = len(self.enemies)
        return {
            "score": self.score,
            "lives": self.player_lives,
            "state": self.state,
            "progress": int(((total - alive) * 100) / total) if total > 0 else 100,
        }
