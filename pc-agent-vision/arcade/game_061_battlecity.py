"""
Game #061: 坦克大战 (Battle City / Tank Battalion 1980 / Namco)
Defend the Golden Eagle Headquarters with Destructible Brick Mazes, Steel Fortifications & Star Cannons.
"""

import math
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

TILE_EMPTY = 0
TILE_BRICK = 1
TILE_STEEL = 2
TILE_WATER = 3
TILE_FOREST = 4
TILE_EAGLE = 5
TILE_EAGLE_DEAD = 6

MAX_SHELLS = 6
MAX_ENEMIES = 3


class Game061BattleCity(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 4000
        self.lives = 3

        self.player_x = 4.0
        self.player_y = 14.0
        self.player_dir = 0
        self.tank_tier = 1
        self.shoot_cooldown = 0.0

        self.eagle_alive = True
        self.shovel_timer = 0.0

        self.enemies_defeated = 0
        self.total_enemies_spawn = 6

        self.map = [[TILE_EMPTY for _ in range(16)] for _ in range(16)]
        self.shells: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 61

    @property
    def name(self) -> str:
        return "坦克大战"

    @property
    def english_name(self) -> str:
        return "Battle City"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "基地神鹰老鹰守护 + 钢砖与土墙爆破穿孔 + 铁锹筑钢与星星升级"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.eagle_alive = True
        self.shovel_timer = 0.0
        self.tank_tier = 1
        self.enemies_defeated = 0
        self.total_enemies_spawn = 6
        self.init_map()

    def init_map(self):
        self.map = [[TILE_EMPTY for _ in range(16)] for _ in range(16)]

        # Golden Eagle at (7, 14) and (8, 14)
        self.map[14][7] = TILE_EAGLE
        self.map[14][8] = TILE_EAGLE

        # Brick perimeter around Eagle
        self.map[14][6] = TILE_BRICK
        self.map[13][6] = TILE_BRICK
        self.map[13][7] = TILE_BRICK
        self.map[13][8] = TILE_BRICK
        self.map[13][9] = TILE_BRICK
        self.map[14][9] = TILE_BRICK

        # Brick corridors
        for y in range(3, 11, 2):
            for x in range(2, 14, 3):
                self.map[y][x] = TILE_BRICK
                self.map[y + 1][x] = TILE_BRICK

        # Steel center
        self.map[7][7] = TILE_STEEL
        self.map[7][8] = TILE_STEEL

        # Water
        self.map[5][0] = TILE_WATER
        self.map[5][1] = TILE_WATER
        self.map[5][14] = TILE_WATER
        self.map[5][15] = TILE_WATER

        # Forest
        self.map[9][3] = TILE_FOREST
        self.map[9][12] = TILE_FOREST

        self.player_x = 4.0
        self.player_y = 14.0
        self.player_dir = 0
        self.shoot_cooldown = 0.0

        self.shells = []
        self.enemies = [
            {"x": 1.0, "y": 1.0, "dir": 2, "health": 1, "type": 0, "active": True, "cooldown": 1.5, "timer": 0.0},
            {"x": 7.0, "y": 1.0, "dir": 2, "health": 1, "type": 1, "active": True, "cooldown": 2.0, "timer": 0.0},
            {"x": 14.0, "y": 1.0, "dir": 2, "health": 2, "type": 2, "active": True, "cooldown": 1.8, "timer": 0.0},
        ]

    def trigger_shovel_reinforce(self):
        self.shovel_timer = 8.0
        self.map[14][6] = TILE_STEEL
        self.map[13][6] = TILE_STEEL
        self.map[13][7] = TILE_STEEL
        self.map[13][8] = TILE_STEEL
        self.map[13][9] = TILE_STEEL
        self.map[14][9] = TILE_STEEL

    def destroy_eagle(self):
        self.eagle_alive = False
        self.map[14][7] = TILE_EAGLE_DEAD
        self.map[14][8] = TILE_EAGLE_DEAD
        self.state = STATE_DEAD
        self.state_timer = 0.0

    def can_move_to(self, x: float, y: float) -> bool:
        if x < 0.2 or x > 14.8 or y < 0.2 or y > 14.8:
            return False

        gx1 = int(math.floor(x))
        gy1 = int(math.floor(y))
        gx2 = int(math.floor(x + 0.8))
        gy2 = int(math.floor(y + 0.8))

        for gy in range(gy1, gy2 + 1):
            for gx in range(gx1, gx2 + 1):
                if 0 <= gx < 16 and 0 <= gy < 16:
                    tile = self.map[gy][gx]
                    if tile in (TILE_BRICK, TILE_STEEL, TILE_WATER, TILE_EAGLE, TILE_EAGLE_DEAD):
                        return False
        return True

    def shoot_shell(self):
        if self.shoot_cooldown > 0.0:
            return
        if len(self.shells) < MAX_SHELLS:
            speed = 18.0 if self.tank_tier >= 2 else 14.0
            vx, vy = 0.0, 0.0
            if self.player_dir == 0:   vy = -speed
            elif self.player_dir == 1: vx = speed
            elif self.player_dir == 2: vy = speed
            else:                      vx = -speed

            self.shells.append({
                "x": self.player_x + 0.4,
                "y": self.player_y + 0.4,
                "vx": vx,
                "vy": vy,
                "is_player": True,
                "active": True
            })
            self.shoot_cooldown = 0.2 if self.tank_tier >= 3 else 0.35

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 2.0:
                if self.lives > 0 and self.eagle_alive:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 4.0
                    self.player_y = 14.0
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.reset()
            return

        if self.shovel_timer > 0.0:
            self.shovel_timer -= dt
            if self.shovel_timer <= 0.0:
                self.map[14][6] = TILE_BRICK
                self.map[13][6] = TILE_BRICK
                self.map[13][7] = TILE_BRICK
                self.map[13][8] = TILE_BRICK
                self.map[13][9] = TILE_BRICK
                self.map[14][9] = TILE_BRICK

        if self.shoot_cooldown > 0.0:
            self.shoot_cooldown -= dt

        # Player move
        speed = 6.5 if self.tank_tier >= 2 else 5.0
        nx, ny = self.player_x, self.player_y

        if buttons & KEY_UP:
            self.player_dir = 0
            ny -= speed * dt
        elif buttons & KEY_DOWN:
            self.player_dir = 2
            ny += speed * dt
        elif buttons & KEY_LEFT:
            self.player_dir = 3
            nx -= speed * dt
        elif buttons & KEY_RIGHT:
            self.player_dir = 1
            nx += speed * dt

        if self.can_move_to(nx, ny):
            self.player_x = nx
            self.player_y = ny

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.shoot_shell()

        # Update enemies
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue
            e["timer"] += dt
            if e["timer"] >= 1.2:
                e["timer"] = 0.0
                if e["y"] < 12.0 and (i % 2 == 0):
                    e["dir"] = 2
                else:
                    e["dir"] = 1 if e["x"] < 7.0 else (3 if e["x"] > 8.0 else 2)

            e_spd = 4.5 if e["type"] == 1 else 3.0
            enx, eny = e["x"], e["y"]
            if e["dir"] == 0: eny -= e_spd * dt
            elif e["dir"] == 1: enx += e_spd * dt
            elif e["dir"] == 2: eny += e_spd * dt
            else: enx -= e_spd * dt

            if self.can_move_to(enx, eny):
                e["x"] = enx
                e["y"] = eny
            else:
                e["dir"] = (e["dir"] + 1) % 4

            e["cooldown"] -= dt
            if e["cooldown"] <= 0.0:
                e["cooldown"] = 1.8
                if len(self.shells) < MAX_SHELLS:
                    sh_spd = 12.0
                    vx, vy = 0.0, 0.0
                    if e["dir"] == 0:   vy = -sh_spd
                    elif e["dir"] == 1: vx = sh_spd
                    elif e["dir"] == 2: vy = sh_spd
                    else:               vx = -sh_spd
                    self.shells.append({
                        "x": e["x"] + 0.4,
                        "y": e["y"] + 0.4,
                        "vx": vx,
                        "vy": vy,
                        "is_player": False,
                        "active": True
                    })

        # Update shells
        for s in self.shells:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            if s["x"] < 0.0 or s["x"] > 15.5 or s["y"] < 0.0 or s["y"] > 15.5:
                s["active"] = False

        # Collisions
        for s in self.shells:
            if not s["active"]:
                continue

            gx = int(math.floor(s["x"]))
            gy = int(math.floor(s["y"]))

            if 0 <= gx < 16 and 0 <= gy < 16:
                tile = self.map[gy][gx]
                if tile == TILE_BRICK:
                    self.map[gy][gx] = TILE_EMPTY
                    s["active"] = False
                    self.score += 10
                    continue
                elif tile == TILE_STEEL:
                    s["active"] = False
                    if s["is_player"] and self.tank_tier >= 3:
                        self.map[gy][gx] = TILE_EMPTY
                    continue
                elif tile == TILE_EAGLE:
                    s["active"] = False
                    self.destroy_eagle()
                    return

            # Shell vs Enemy tank
            if s["is_player"]:
                for e in self.enemies:
                    if not e["active"]:
                        continue
                    if abs(s["x"] - e["x"]) < 0.9 and abs(s["y"] - e["y"]) < 0.9:
                        s["active"] = False
                        e["health"] -= 1
                        if e["health"] <= 0:
                            e["active"] = False
                            self.enemies_defeated += 1
                            self.score += 300 if e["type"] == 2 else 150
                            if self.enemies_defeated + MAX_ENEMIES <= self.total_enemies_spawn:
                                e["x"] = 7.0
                                e["y"] = 1.0
                                e["health"] = 1
                                e["type"] = 0
                                e["active"] = True
                        break
            else:
                if abs(s["x"] - self.player_x) < 0.9 and abs(s["y"] - self.player_y) < 0.9:
                    s["active"] = False
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        self.shells = [s for s in self.shells if s["active"]]

        if self.enemies_defeated >= self.total_enemies_spawn:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1500
            if self.score > self.high_score:
                self.high_score = self.score

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                tile = self.map[y][x]
                if tile == TILE_BRICK:
                    fb[idx] = 180; fb[idx + 1] = 60;  fb[idx + 2] = 30
                elif tile == TILE_STEEL:
                    fb[idx] = 220; fb[idx + 1] = 220; fb[idx + 2] = 230
                elif tile == TILE_WATER:
                    fb[idx] = 20;  fb[idx + 1] = 80;  fb[idx + 2] = 220
                elif tile == TILE_FOREST:
                    fb[idx] = 20;  fb[idx + 1] = 160; fb[idx + 2] = 30
                elif tile == TILE_EAGLE:
                    fb[idx] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0
                elif tile == TILE_EAGLE_DEAD:
                    fb[idx] = 80;  fb[idx + 1] = 80;  fb[idx + 2] = 80

        # Shells
        for s in self.shells:
            if s["active"]:
                sx = int(round(s["x"]))
                sy = int(round(s["y"]))
                if 0 <= sx < 16 and 0 <= sy < 16:
                    idx = (sy * 16 + sx) * 3
                    fb[idx] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255

        # Enemies
        for e in self.enemies:
            if e["active"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                if 0 <= ex < 16 and 0 <= ey < 16:
                    idx = (ey * 16 + ex) * 3
                    if e["type"] == 2:
                        fb[idx] = 200; fb[idx + 1] = 20;  fb[idx + 2] = 20
                    elif e["type"] == 1:
                        fb[idx] = 255; fb[idx + 1] = 140; fb[idx + 2] = 0
                    else:
                        fb[idx] = 180; fb[idx + 1] = 180; fb[idx + 2] = 180

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx] = 255; fb[idx + 1] = 200; fb[idx + 2] = 0

            bx, by = px, py
            if self.player_dir == 0: by -= 1
            elif self.player_dir == 1: bx += 1
            elif self.player_dir == 2: by += 1
            else: bx -= 1

            if 0 <= bx < 16 and 0 <= by < 16:
                b_idx = (by * 16 + bx) * 3
                fb[b_idx] = 255; fb[b_idx + 1] = 240; fb[b_idx + 2] = 100

        # HUD
        for l in range(min(self.lives, 3)):
            idx = l * 3
            fb[idx] = 0; fb[idx + 1] = 255; fb[idx + 2] = 0

        rem = self.total_enemies_spawn - self.enemies_defeated
        for r in range(min(rem, 6)):
            idx = (15 - r) * 3
            fb[idx] = 255; fb[idx + 1] = 50; fb[idx + 2] = 50

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "eagle_alive": self.eagle_alive,
            "tank_tier": self.tank_tier,
            "enemies_remaining": self.total_enemies_spawn - self.enemies_defeated,
        }
