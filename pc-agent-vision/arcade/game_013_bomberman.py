# -*- coding: utf-8 -*-
"""
game_013_bomberman.py —— 像素炸弹人 1983 (Bomberman 1983)
编号: #013
年代: 1983 (哈德森 Hudson Soft)
核心独占机制: 定时炸弹放置 + 十字烈焰冲击波 + 软砖碎裂与自身回避 + 巡逻怪爆破消灭
手柄类型: CTRL_ARCADE_AB (四向移动 + A/B 埋设炸弹)
"""

import math
import random
from typing import Dict, Any, List
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
TILE_HARD_WALL = 1
TILE_SOFT_BRICK = 2

class Bomb:
    def __init__(self):
        self.active = False
        self.gx = 0
        self.gy = 0
        self.timer = 0.0
        self.range = 2

class FlamePixel:
    def __init__(self, x: int, y: int, timer: float):
        self.x = x
        self.y = y
        self.timer = timer

class BomberEnemy:
    def __init__(self, x: float, y: float, dir_x: int, dir_y: int, speed: float):
        self.alive = True
        self.x = x
        self.y = y
        self.dir_x = dir_x
        self.dir_y = dir_y
        self.speed = speed

class Game013Bomberman(BaseCartridge):
    def __init__(self):
        self._id = 13
        self._name = "像素炸弹人"
        self._english_name = "Bomberman 1983"
        self._year = 1983
        self._control_type = CTRL_ARCADE_AB
        self._core_mechanic = "定时炸弹放置 + 十字烈焰冲击波 + 软砖碎裂与自身回避 + 巡逻怪爆破消灭"

        self.k_num_enemies = 2
        self.state = STATE_TITLE
        self.player_x = 1.0
        self.player_y = 1.0
        self.lives = 3
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0
        self.flame_range = 2

        self.map: List[List[int]] = []
        self.bomb = Bomb()
        self.flames: List[FlamePixel] = []
        self.enemies: List[BomberEnemy] = []
        self.remaining_enemies = self.k_num_enemies

        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def english_name(self) -> str:
        return self._english_name

    @property
    def release_year(self) -> int:
        return self._year

    @property
    def control_type(self) -> int:
        return self._control_type

    @property
    def core_mechanic(self) -> str:
        return self._core_mechanic

    def reset_player(self):
        self.player_x = 1.0
        self.player_y = 1.0
        self.bomb.active = False
        self.flames = []

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.flame_range = 2
        self.flames = []
        self.remaining_enemies = self.k_num_enemies

        self.map = []
        for y in range(16):
            row = []
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    row.append(TILE_HARD_WALL)
                elif x % 2 == 0 and y % 2 == 0:
                    row.append(TILE_HARD_WALL)
                else:
                    if x <= 2 and y <= 2:
                        row.append(TILE_EMPTY)
                    elif (x == 13 and y == 1) or (x == 1 and y == 13):
                        row.append(TILE_EMPTY)
                    else:
                        row.append(TILE_SOFT_BRICK if ((x * 7 + y * 13) % 10 < 5) else TILE_EMPTY)
            self.map.append(row)

        self.enemies = [
            BomberEnemy(13.0, 1.0, -1, 0, 2.4),
            BomberEnemy(1.0, 13.0, 0, -1, 2.2),
        ]
        self.reset_player()

    def is_walkable(self, gx: int, gy: int, allow_bomb: bool) -> bool:
        if gx < 0 or gx >= 16 or gy < 0 or gy >= 16:
            return False
        if self.map[gy][gx] in (TILE_HARD_WALL, TILE_SOFT_BRICK):
            return False
        if not allow_bomb and self.bomb.active and self.bomb.gx == gx and self.bomb.gy == gy:
            return False
        return True

    def explode_bomb(self):
        self.bomb.active = False
        self.flames = []

        cx = self.bomb.gx
        cy = self.bomb.gy
        self.flames.append(FlamePixel(cx, cy, 0.45))

        dxs = [0, 0, -1, 1]
        dys = [-1, 1, 0, 0]

        for i in range(4):
            for step in range(1, self.bomb.range + 1):
                tx = cx + dxs[i] * step
                ty = cy + dys[i] * step

                if tx < 0 or tx >= 16 or ty < 0 or ty >= 16:
                    break
                if self.map[ty][tx] == TILE_HARD_WALL:
                    break
                if self.map[ty][tx] == TILE_SOFT_BRICK:
                    self.map[ty][tx] = TILE_EMPTY
                    self.flames.append(FlamePixel(tx, ty, 0.45))
                    self.score += 20
                    if self.score > self.high_score:
                        self.high_score = self.score
                    break

                self.flames.append(FlamePixel(tx, ty, 0.45))

        # 烈焰伤害判定
        for flame in self.flames:
            fx = flame.x
            fy = flame.y

            px = int(round(self.player_x))
            py = int(round(self.player_y))
            if px == fx and py == fy:
                if self.lives > 0:
                    self.lives -= 1
                if self.lives == 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
                else:
                    self.reset_player()
                    return

            for e in self.enemies:
                if e.alive:
                    ex = int(round(e.x))
                    ey = int(round(e.y))
                    if ex == fx and ey == fy:
                        e.alive = False
                        self.remaining_enemies -= 1
                        self.score += 100
                        if self.score > self.high_score:
                            self.high_score = self.score

                        if self.remaining_enemies <= 0:
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                            return

    def move_enemy(self, e: BomberEnemy, dt: float):
        if not e.alive:
            return

        cur_gx = int(round(e.x))
        cur_gy = int(round(e.y))
        dist = abs(e.x - cur_gx) + abs(e.y - cur_gy)

        if dist < 0.12:
            e.x = float(cur_gx)
            e.y = float(cur_gy)

            next_gx = cur_gx + e.dir_x
            next_gy = cur_gy + e.dir_y

            if not self.is_walkable(next_gx, next_gy, False):
                dxs = [0, 0, -1, 1]
                dys = [-1, 1, 0, 0]
                valid = []
                for i in range(4):
                    if self.is_walkable(cur_gx + dxs[i], cur_gy + dys[i], False):
                        valid.append(i)
                if valid:
                    pick = random.choice(valid)
                    e.dir_x = dxs[pick]
                    e.dir_y = dys[pick]
                else:
                    e.dir_x = -e.dir_x
                    e.dir_y = -e.dir_y

        e.x += e.dir_x * e.speed * dt
        e.y += e.dir_y * e.speed * dt

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)):
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

            player_speed = 4.2
            move_x, move_y = 0.0, 0.0
            if keys_down & KEY_UP: move_y = -player_speed * dt
            elif keys_down & KEY_DOWN: move_y = player_speed * dt
            elif keys_down & KEY_LEFT: move_x = -player_speed * dt
            elif keys_down & KEY_RIGHT: move_x = player_speed * dt

            if move_x != 0.0 or move_y != 0.0:
                new_x = self.player_x + move_x
                new_y = self.player_y + move_y

                can_move = True
                r = 0.35
                offsets = [(-r, -r), (r, -r), (-r, r), (r, r)]
                on_own_bomb = self.bomb.active and (self.bomb.gx == int(round(self.player_x))) and (self.bomb.gy == int(round(self.player_y)))

                for ox, oy in offsets:
                    cx = int(round(new_x + ox))
                    cy = int(round(new_y + oy))
                    if not self.is_walkable(cx, cy, on_own_bomb):
                        can_move = False
                        break

                if can_move:
                    self.player_x = new_x
                    self.player_y = new_y

            # 埋设炸弹
            if (keys_pressed & (KEY_A | KEY_B)) and not self.bomb.active:
                self.bomb.active = True
                self.bomb.gx = int(round(self.player_x))
                self.bomb.gy = int(round(self.player_y))
                self.bomb.timer = 2.0
                self.bomb.range = self.flame_range

            # 炸弹倒计时
            if self.bomb.active:
                self.bomb.timer -= dt
                if self.bomb.timer <= 0.0:
                    self.explode_bomb()

            # 烈焰消退
            for f in self.flames:
                f.timer -= dt
            self.flames = [f for f in self.flames if f.timer > 0.0]

            # 敌怪
            for e in self.enemies:
                if e.alive:
                    self.move_enemy(e, dt)
                    if abs(self.player_x - e.x) < 0.75 and abs(self.player_y - e.y) < 0.75:
                        if self.lives > 0:
                            self.lives -= 1
                        if self.lives == 0:
                            self.state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return
                        else:
                            self.reset_player()
                            return

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                tile = self.map[y][x]
                if tile == TILE_HARD_WALL:
                    self.frame_buffer[idx:idx+3] = bytes([52, 73, 94])
                elif tile == TILE_SOFT_BRICK:
                    self.frame_buffer[idx:idx+3] = bytes([211, 84, 0])
                else:
                    self.frame_buffer[idx:idx+3] = bytes([20, 90, 50])

        if self.bomb.active:
            idx = (self.bomb.gy * 16 + self.bomb.gx) * 3
            tick = (int(self.bomb.timer * 8.0) % 2 == 0)
            color = [231, 76, 60] if tick else [20, 20, 20]
            self.frame_buffer[idx:idx+3] = bytes(color)

        for flame in self.flames:
            if 0 <= flame.x < 16 and 0 <= flame.y < 16:
                idx = (flame.y * 16 + flame.x) * 3
                self.frame_buffer[idx:idx+3] = bytes([255, 200, 0])

        for e in self.enemies:
            if e.alive:
                ex = int(round(e.x))
                ey = int(round(e.y))
                if 0 <= ex < 16 and 0 <= ey < 16:
                    idx = (ey * 16 + ex) * 3
                    self.frame_buffer[idx:idx+3] = bytes([255, 105, 180])

        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 255, 255])

        for i in range(self.lives):
            idx = (0 * 16 + (i * 2 + 1)) * 3
            self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "remaining_enemies": self.remaining_enemies,
        }
