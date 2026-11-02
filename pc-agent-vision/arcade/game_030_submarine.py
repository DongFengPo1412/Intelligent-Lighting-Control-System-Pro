# -*- coding: utf-8 -*-
"""
game_030_submarine.py —— 潜艇鱼雷大战 1979 (Submarine 1979 / Sea Wolf)
编号: #030
年代: 1979
核心独占机制: 多吃水层水面舰艇穿行 + 浮力垂直鱼雷前置预判 + 游弋水雷引爆阻截 + 声呐制海权
手柄类型: CTRL_ARCADE_AB (左右深海潜航 + A/B键垂直发射鱼雷)
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

SHIP_PT_BOAT = 0
SHIP_DESTROYER = 1
SHIP_CARRIER = 2


class Game030Submarine(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.player_x: float = 7.0
        self.lives: int = 3
        self.reload_timer: float = 0.0
        self.ships_sunk: int = 0
        self.ship_spawn_timer: float = 0.0
        self.mine_spawn_timer: float = 0.0

        self.ships: List[Dict[str, Any]] = []
        self.torpedoes: List[Dict[str, Any]] = []
        self.mines: List[Dict[str, Any]] = []

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 30

    @property
    def name(self) -> str:
        return "深海鱼雷战"

    @property
    def english_name(self) -> str:
        return "Submarine 1979"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多吃水层水面舰艇穿行 + 浮力垂直鱼雷前置预判 + 游弋水雷引爆阻截 + 声呐制海权"

    def init(self) -> None:
        self.reset()

    def spawn_ship(self):
        if len(self.ships) < 4:
            from_left = random.choice([True, False])
            roll = random.randint(0, 99)
            if roll < 45:
                stype = SHIP_PT_BOAT
                sy = 2.0
                svx = 5.5 if from_left else -5.5
                shp = 1
            elif roll < 80:
                stype = SHIP_DESTROYER
                sy = 3.5
                svx = 3.5 if from_left else -3.5
                shp = 1
            else:
                stype = SHIP_CARRIER
                sy = 4.5
                svx = 2.2 if from_left else -2.2
                shp = 2

            self.ships.append({
                "active": True,
                "type": stype,
                "x": -2.0 if from_left else 17.0,
                "y": sy,
                "vx": svx,
                "hp": shp,
            })

    def spawn_mine(self):
        if len(self.mines) < 3:
            from_left = random.choice([True, False])
            self.mines.append({
                "active": True,
                "x": -1.0 if from_left else 16.0,
                "y": 8.0 + float(random.randint(0, 2)),
                "vx": 1.5 if from_left else -1.5,
            })

    def init_ocean(self):
        self.player_x = 7.0
        self.lives = 3
        self.reload_timer = 0.0
        self.ships_sunk = 0
        self.ship_spawn_timer = 0.0
        self.mine_spawn_timer = 0.0
        self.ships = []
        self.torpedoes = []
        self.mines = []

        self.spawn_ship()
        self.spawn_mine()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.init_ocean()

    def fire_torpedo(self):
        if self.reload_timer > 0.0:
            return
        self.reload_timer = 0.35

        if len(self.torpedoes) < 3:
            self.torpedoes.append({
                "active": True,
                "x": self.player_x + 0.5,
                "y": 13.0,
                "vy": -10.5,
            })

    def update_ships(self, dt: float):
        self.ship_spawn_timer += dt
        if self.ship_spawn_timer >= 1.6:
            self.ship_spawn_timer = 0.0
            self.spawn_ship()

        for ship in self.ships:
            if not ship["active"]:
                continue
            ship["x"] += ship["vx"] * dt
            if (ship["vx"] > 0 and ship["x"] > 18.0) or (ship["vx"] < 0 and ship["x"] < -3.0):
                ship["active"] = False

        self.ships = [s for s in self.ships if s["active"]]

    def update_mines(self, dt: float):
        self.mine_spawn_timer += dt
        if self.mine_spawn_timer >= 3.5:
            self.mine_spawn_timer = 0.0
            self.spawn_mine()

        for mine in self.mines:
            if not mine["active"]:
                continue
            mine["x"] += mine["vx"] * dt
            if (mine["vx"] > 0 and mine["x"] > 17.0) or (mine["vx"] < 0 and mine["x"] < -2.0):
                mine["active"] = False

        self.mines = [m for m in self.mines if m["active"]]

    def update_torpedoes(self, dt: float):
        for torp in self.torpedoes:
            if not torp["active"]:
                continue

            torp["y"] += torp["vy"] * dt
            if torp["y"] < 0.5:
                torp["active"] = False
                continue

            for mine in self.mines:
                if mine["active"]:
                    dist = abs(torp["x"] - mine["x"]) + abs(torp["y"] - mine["y"])
                    if dist <= 1.0:
                        torp["active"] = False
                        mine["active"] = False
                        self.score += 20
                        if self.score > self.high_score:
                            self.high_score = self.score
                        break
            if not torp["active"]:
                continue

            for ship in self.ships:
                if ship["active"]:
                    width = 2.0 if ship["type"] == SHIP_CARRIER else 1.2
                    dx = abs(torp["x"] - ship["x"])
                    dy = abs(torp["y"] - ship["y"])
                    if dx <= width and dy <= 0.9:
                        torp["active"] = False
                        ship["hp"] -= 1

                        if ship["hp"] <= 0:
                            ship["active"] = False
                            self.ships_sunk += 1

                            if ship["type"] == SHIP_PT_BOAT:
                                self.score += 100
                            elif ship["type"] == SHIP_DESTROYER:
                                self.score += 200
                            else:
                                self.score += 400

                            if self.score > self.high_score:
                                self.high_score = self.score

                            if self.ships_sunk >= 8:
                                self.state = STATE_VICTORY
                                self.state_timer = 0.0
                                self.score += 1000
                                if self.score > self.high_score:
                                    self.high_score = self.score
                                return
                        break

        self.torpedoes = [t for t in self.torpedoes if t["active"]]
        self.mines = [m for m in self.mines if m["active"]]
        self.ships = [s for s in self.ships if s["active"]]

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)):
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

            if self.reload_timer > 0.0:
                self.reload_timer -= dt

            speed = 7.5
            if keys_down & KEY_LEFT:
                self.player_x -= speed * dt
            if keys_down & KEY_RIGHT:
                self.player_x += speed * dt

            self.player_x = max(0.5, min(14.0, self.player_x))

            if keys_pressed & (KEY_A | KEY_B):
                self.fire_torpedo()

            self.update_ships(dt)
            self.update_mines(dt)
            self.update_torpedoes(dt)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 海洋渐变
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if y == 0:
                    buf[idx:idx+3] = bytes([52, 152, 219])
                elif y <= 5:
                    buf[idx:idx+3] = bytes([41, 128, 185])
                elif y <= 11:
                    buf[idx:idx+3] = bytes([21, 67, 96])
                else:
                    buf[idx:idx+3] = bytes([11, 22, 44])

        # 舰艇
        for ship in self.ships:
            if not ship["active"]:
                continue
            sx = int(round(ship["x"]))
            sy = int(round(ship["y"]))
            if 0 <= sy < 16:
                if ship["type"] == SHIP_PT_BOAT:
                    cr, cg, cb = 241, 196, 15
                elif ship["type"] == SHIP_DESTROYER:
                    cr, cg, cb = 189, 195, 199
                else:
                    cr, cg, cb = 231, 76, 60

                w = 2 if ship["type"] == SHIP_CARRIER else 1
                for dx in range(w):
                    px = sx + dx
                    if 0 <= px < 16:
                        idx = (sy * 16 + px) * 3
                        buf[idx:idx+3] = bytes([cr, cg, cb])

        # 水雷
        for mine in self.mines:
            if not mine["active"]:
                continue
            mx = int(round(mine["x"]))
            my = int(round(mine["y"]))
            if 0 <= mx < 16 and 0 <= my < 16:
                idx = (my * 16 + mx) * 3
                buf[idx:idx+3] = bytes([231, 76, 60])

        # 鱼雷
        for torp in self.torpedoes:
            if not torp["active"]:
                continue
            tx = int(round(torp["x"]))
            ty = int(round(torp["y"]))
            if 0 <= tx < 16 and 0 <= ty < 16:
                idx = (ty * 16 + tx) * 3
                buf[idx:idx+3] = bytes([255, 255, 255])

        # 潜艇
        if self.lives > 0:
            px1 = int(round(self.player_x))
            px2 = px1 + 1
            py = 14
            if 0 <= px1 < 16:
                idx1 = (py * 16 + px1) * 3
                buf[idx1:idx1+3] = bytes([46, 204, 113])
            if 0 <= px2 < 16:
                idx2 = (py * 16 + px2) * 3
                buf[idx2:idx2+3] = bytes([0, 255, 255])

        # HUD
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx:idx+3] = bytes([46, 204, 113])

        for i in range(self.ships_sunk):
            idx = (0 * 16 + (15 - i)) * 3
            buf[idx:idx+3] = bytes([241, 196, 15])

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
        prog = (self.ships_sunk * 100) // 8
        prog = min(100, prog)
        return {
            "score": self.score,
            "lives": self.lives,
            "sunk": self.ships_sunk,
            "state": self.state,
            "progress": prog,
        }
