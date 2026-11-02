# -*- coding: utf-8 -*-
"""
game_027_magic_tower.py —— 经典魔塔 1996 (Magic Tower 1996)
编号: #027
年代: 1996
核心独占机制: 零随机精密数值战斗 + 黄蓝钥匙门禁决策 + 攻防红蓝宝石强化 + 终极魔王讨伐
手柄类型: CTRL_DPAD_4WAY (四向十字键行走并触碰交互)
"""

from typing import Dict, Any, List, Optional, Tuple
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    CTRL_DPAD_4WAY,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

TOWER_FLOOR = 0
TOWER_WALL = 1
TOWER_DOOR_YELLOW = 2
TOWER_DOOR_BLUE = 3
TOWER_KEY_YELLOW = 4
TOWER_KEY_BLUE = 5
TOWER_GEM_RED = 6
TOWER_GEM_BLUE = 7
TOWER_POTION_RED = 8
TOWER_POTION_BLUE = 9
TOWER_MONSTER_SLIME = 10
TOWER_MONSTER_SKELETON = 11
TOWER_MONSTER_MAGE = 12
TOWER_MONSTER_BOSS = 13
TOWER_STAIRS = 14

MONSTER_STATS = {
    TOWER_MONSTER_SLIME: {"hp": 50, "atk": 20, "def": 1, "gold": 10},
    TOWER_MONSTER_SKELETON: {"hp": 110, "atk": 35, "def": 5, "gold": 30},
    TOWER_MONSTER_MAGE: {"hp": 200, "atk": 55, "def": 10, "gold": 60},
    TOWER_MONSTER_BOSS: {"hp": 500, "atk": 80, "def": 20, "gold": 200},
}


class Game027MagicTower(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.grid: List[List[int]] = [[TOWER_FLOOR for _ in range(16)] for _ in range(16)]
        self.hero_x: int = 1
        self.hero_y: int = 14
        self.hero_hp: int = 1000
        self.hero_atk: int = 25
        self.hero_def: int = 10
        self.yellow_keys: int = 1
        self.blue_keys: int = 0
        self.move_timer: float = 0.0

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 27

    @property
    def name(self) -> str:
        return "经典魔塔"

    @property
    def english_name(self) -> str:
        return "Magic Tower 1996"

    @property
    def release_year(self) -> int:
        return 1996

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "零随机精密数值战斗 + 黄蓝钥匙门禁决策 + 攻防红蓝宝石强化 + 终极魔王讨伐"

    def init(self) -> None:
        self.reset()

    def get_monster_stats(self, tile_type: int) -> Dict[str, int]:
        return MONSTER_STATS.get(tile_type, {"hp": 0, "atk": 0, "def": 0, "gold": 0})

    def calculate_damage(self, tile_type: int) -> int:
        m = self.get_monster_stats(tile_type)
        if self.hero_atk <= m["def"]:
            return -1

        hero_dmg = self.hero_atk - m["def"]
        enemy_dmg = max(0, m["atk"] - self.hero_def)
        rounds = (m["hp"] + hero_dmg - 1) // hero_dmg
        total_dmg = (rounds - 1) * enemy_dmg
        return total_dmg

    def init_level(self):
        self.grid = [[TOWER_FLOOR for _ in range(16)] for _ in range(16)]

        # 外墙
        for x in range(16):
            self.grid[0][x] = TOWER_WALL
            self.grid[15][x] = TOWER_WALL
        for y in range(16):
            self.grid[y][0] = TOWER_WALL
            self.grid[y][15] = TOWER_WALL

        # 内墙
        for x in range(1, 7):
            self.grid[12][x] = TOWER_WALL
        for y in range(8, 15):
            self.grid[y][6] = TOWER_WALL
        for x in range(6, 15):
            self.grid[8][x] = TOWER_WALL
        for y in range(1, 9):
            self.grid[y][11] = TOWER_WALL
        for x in range(1, 9):
            self.grid[4][x] = TOWER_WALL

        # 门禁
        self.grid[12][3] = TOWER_DOOR_YELLOW
        self.grid[8][8] = TOWER_DOOR_YELLOW
        self.grid[4][4] = TOWER_DOOR_YELLOW
        self.grid[4][11] = TOWER_DOOR_BLUE

        # 补给道具
        self.grid[13][2] = TOWER_KEY_YELLOW
        self.grid[14][4] = TOWER_GEM_RED
        self.grid[13][5] = TOWER_POTION_RED

        self.grid[10][2] = TOWER_KEY_YELLOW
        self.grid[9][3] = TOWER_GEM_BLUE
        self.grid[10][4] = TOWER_KEY_BLUE

        self.grid[6][2] = TOWER_POTION_BLUE
        self.grid[5][3] = TOWER_GEM_RED
        self.grid[6][4] = TOWER_GEM_BLUE

        self.grid[2][2] = TOWER_GEM_RED
        self.grid[2][4] = TOWER_GEM_BLUE
        self.grid[1][3] = TOWER_POTION_BLUE

        # 怪物
        self.grid[12][4] = TOWER_MONSTER_SLIME
        self.grid[11][8] = TOWER_MONSTER_SLIME
        self.grid[8][9] = TOWER_MONSTER_SKELETON
        self.grid[6][8] = TOWER_MONSTER_SKELETON
        self.grid[4][9] = TOWER_MONSTER_MAGE
        self.grid[2][8] = TOWER_MONSTER_MAGE
        self.grid[2][12] = TOWER_MONSTER_BOSS

        # 楼梯
        self.grid[1][14] = TOWER_STAIRS

        self.hero_x = 1
        self.hero_y = 14
        self.hero_hp = 1000
        self.hero_atk = 25
        self.hero_def = 10
        self.yellow_keys = 1
        self.blue_keys = 0
        self.move_timer = 0.0

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.init_level()

    def interact(self, nx: int, ny: int) -> bool:
        if not (0 <= nx < 16 and 0 <= ny < 16):
            return False

        tile = self.grid[ny][nx]

        if tile == TOWER_FLOOR:
            self.hero_x = nx
            self.hero_y = ny
            return True

        if tile == TOWER_WALL:
            return False

        if tile == TOWER_KEY_YELLOW:
            self.yellow_keys += 1
            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            self.score += 10
            return True

        if tile == TOWER_KEY_BLUE:
            self.blue_keys += 1
            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            self.score += 20
            return True

        if tile == TOWER_GEM_RED:
            self.hero_atk += 3
            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            self.score += 30
            return True

        if tile == TOWER_GEM_BLUE:
            self.hero_def += 3
            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            self.score += 30
            return True

        if tile == TOWER_POTION_RED:
            self.hero_hp += 200
            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            self.score += 15
            return True

        if tile == TOWER_POTION_BLUE:
            self.hero_hp += 500
            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            self.score += 40
            return True

        if tile == TOWER_DOOR_YELLOW:
            if self.yellow_keys > 0:
                self.yellow_keys -= 1
                self.grid[ny][nx] = TOWER_FLOOR
                self.hero_x = nx
                self.hero_y = ny
                self.score += 20
                return True
            return False

        if tile == TOWER_DOOR_BLUE:
            if self.blue_keys > 0:
                self.blue_keys -= 1
                self.grid[ny][nx] = TOWER_FLOOR
                self.hero_x = nx
                self.hero_y = ny
                self.score += 50
                return True
            return False

        if tile in (TOWER_MONSTER_SLIME, TOWER_MONSTER_SKELETON, TOWER_MONSTER_MAGE, TOWER_MONSTER_BOSS):
            dmg = self.calculate_damage(tile)
            if dmg == -1 or dmg >= self.hero_hp:
                return False

            m = self.get_monster_stats(tile)
            self.hero_hp -= dmg
            self.score += m["gold"]
            if self.score > self.high_score:
                self.high_score = self.score

            self.grid[ny][nx] = TOWER_FLOOR
            self.hero_x = nx
            self.hero_y = ny
            return True

        if tile == TOWER_STAIRS:
            self.hero_x = nx
            self.hero_y = ny
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000
            if self.score > self.high_score:
                self.high_score = self.score
            return True

        return False

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
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
                    self.interact(self.hero_x + dx, self.hero_y + dy)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                t = self.grid[y][x]
                if t == TOWER_FLOOR:
                    buf[idx:idx+3] = bytes([30, 30, 35])
                elif t == TOWER_WALL:
                    buf[idx:idx+3] = bytes([100, 100, 110])
                elif t == TOWER_DOOR_YELLOW:
                    buf[idx:idx+3] = bytes([241, 196, 15])
                elif t == TOWER_DOOR_BLUE:
                    buf[idx:idx+3] = bytes([41, 128, 185])
                elif t == TOWER_KEY_YELLOW:
                    buf[idx:idx+3] = bytes([243, 156, 18])
                elif t == TOWER_KEY_BLUE:
                    buf[idx:idx+3] = bytes([52, 152, 219])
                elif t == TOWER_GEM_RED:
                    buf[idx:idx+3] = bytes([231, 76, 60])
                elif t == TOWER_GEM_BLUE:
                    buf[idx:idx+3] = bytes([52, 152, 219])
                elif t == TOWER_POTION_RED:
                    buf[idx:idx+3] = bytes([255, 105, 180])
                elif t == TOWER_POTION_BLUE:
                    buf[idx:idx+3] = bytes([0, 255, 255])
                elif t == TOWER_MONSTER_SLIME:
                    buf[idx:idx+3] = bytes([46, 204, 113])
                elif t == TOWER_MONSTER_SKELETON:
                    buf[idx:idx+3] = bytes([189, 195, 199])
                elif t == TOWER_MONSTER_MAGE:
                    buf[idx:idx+3] = bytes([155, 89, 182])
                elif t == TOWER_MONSTER_BOSS:
                    buf[idx:idx+3] = bytes([255, 0, 0])
                elif t == TOWER_STAIRS:
                    buf[idx:idx+3] = bytes([255, 255, 255])

        # 勇士
        h_idx = (self.hero_y * 16 + self.hero_x) * 3
        buf[h_idx:h_idx+3] = bytes([255, 215, 0])

        # HUD 生命指示
        hp_color_g = 200 if self.hero_hp > 500 else (150 if self.hero_hp > 200 else 50)
        buf[0] = 231
        buf[1] = hp_color_g
        buf[2] = 60

        # 特效
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
        boss_alive = self.grid[2][12] == TOWER_MONSTER_BOSS
        prog = 100 if not boss_alive else min(100, int((self.score * 100) / 1000))
        return {
            "score": self.score,
            "hp": self.hero_hp,
            "atk": self.hero_atk,
            "def": self.hero_def,
            "yellow_keys": self.yellow_keys,
            "blue_keys": self.blue_keys,
            "state": self.state,
            "progress": prog,
        }
