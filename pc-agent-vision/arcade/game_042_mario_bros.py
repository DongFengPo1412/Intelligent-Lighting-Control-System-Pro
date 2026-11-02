"""
Game #042: 水管兄弟 (Mario Bros. 1983 / Nintendo)
Iconic Under-Floor Concussion Jump + POW Block Earthquake + Flipped Turtle Kick Clean-up.
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

MAX_ENEMIES = 4


class Game042MarioBros(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.pow_hits = 3
        self.enemies_defeated = 0
        self.total_wave_enemies = 6

        self.player_x = 4.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_grounded = True

        self.pow_shake_timer = 0.0
        self.enemies: List[Dict[str, Any]] = []
        self.platform_grid: List[List[int]] = [[0 for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 42

    @property
    def name(self) -> str:
        return "水管兄弟"

    @property
    def english_name(self) -> str:
        return "Mario Bros. (1983)"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "下层顶击震翻地底海龟 + POW地震全屏眩晕 + 踢飞翻盖乌龟清屏"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.pow_hits = 3
        self.enemies_defeated = 0
        self.total_wave_enemies = 6
        self.player_x = 4.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_facing = 1
        self.is_grounded = True
        self.pow_shake_timer = 0.0

        self.init_arena()

        self.enemies = [
            {"x": 2.0, "y": 4.0, "vx": 2.5, "vy": 0.0, "active": True, "is_flipped": False, "flip_timer": 0.0, "is_enraged": False},
            {"x": 13.0, "y": 4.0, "vx": -2.5, "vy": 0.0, "active": True, "is_flipped": False, "flip_timer": 0.0, "is_enraged": False},
            {"x": 6.0, "y": 7.0, "vx": 2.5, "vy": 0.0, "active": True, "is_flipped": False, "flip_timer": 0.0, "is_enraged": False},
            {"x": 10.0, "y": 10.0, "vx": -2.5, "vy": 0.0, "active": True, "is_flipped": False, "flip_timer": 0.0, "is_enraged": False},
        ]

    def init_arena(self):
        self.platform_grid = [[0 for _ in range(16)] for _ in range(16)]

        # Ground floor (y = 14..15)
        for x in range(16):
            self.platform_grid[14][x] = 2
            self.platform_grid[15][x] = 2

        # Tier 1 (Low): y = 11
        for x in range(1, 7):
            self.platform_grid[11][x] = 2
        for x in range(9, 15):
            self.platform_grid[11][x] = 2

        # Tier 2 (Mid): y = 8 (center)
        for x in range(4, 12):
            self.platform_grid[8][x] = 2

        # Tier 3 (High): y = 5
        for x in range(1, 7):
            self.platform_grid[5][x] = 2
        for x in range(9, 15):
            self.platform_grid[5][x] = 2

        # Spawn pipes (y = 3)
        self.platform_grid[3][1] = 1
        self.platform_grid[3][14] = 1

        # Central POW block at x = 7, 8, y = 12
        self.platform_grid[12][7] = 3
        self.platform_grid[12][8] = 3

    def get_enemies_remaining(self) -> int:
        return self.total_wave_enemies - self.enemies_defeated

    def hit_pow_block(self):
        if self.pow_hits <= 0:
            return
        self.pow_hits -= 1
        self.pow_shake_timer = 0.35

        # Earthquake flips all active enemies
        for e in self.enemies:
            if e["active"]:
                e["is_flipped"] = True
                e["flip_timer"] = 5.0

        self.score += 100
        if self.score > self.high_score:
            self.high_score = self.score

        if self.pow_hits <= 0:
            self.platform_grid[12][7] = 0
            self.platform_grid[12][8] = 0

    def bump_ceiling(self, bump_x: float, bump_y: float):
        bx = int(round(bump_x))
        by = int(round(bump_y))

        # Check POW hit
        if by == 12 and (bx == 7 or bx == 8):
            self.hit_pow_block()
            return

        # Check enemy above
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - bump_x) <= 1.25 and abs(e["y"] - float(by - 1)) <= 0.65:
                if not e["is_flipped"]:
                    e["is_flipped"] = True
                    e["flip_timer"] = 5.0
                else:
                    e["is_flipped"] = False  # Bumping flipped enemy un-flips it
                self.score += 50
                if self.score > self.high_score:
                    self.high_score = self.score

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        gravity = 22.0
        run_speed = 5.5

        # Horizontal run
        self.player_vx = 0.0
        if buttons & KEY_LEFT:
            self.player_vx = -run_speed
            self.player_facing = -1
        if buttons & KEY_RIGHT:
            self.player_vx = run_speed
            self.player_facing = 1

        self.player_x += self.player_vx * dt
        # Screen wrap
        if self.player_x < 0.0:
            self.player_x += 16.0
        if self.player_x >= 16.0:
            self.player_x -= 16.0

        # Jump (KEY_A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A) and self.is_grounded:
            self.player_vy = -10.5
            self.is_grounded = False

        # Vertical physics
        if not self.is_grounded:
            self.player_vy += gravity * dt
            self.player_y += self.player_vy * dt

            # Head bump on ceiling
            if self.player_vy < 0.0:
                ceil_y = int(round(self.player_y - 0.45))
                head_x = int(round(self.player_x))
                if 0 <= ceil_y < 16 and 0 <= head_x < 16:
                    if self.platform_grid[ceil_y][head_x] != 0:
                        self.player_vy = 0.0
                        self.bump_ceiling(self.player_x, float(ceil_y))
            # Downward landing
            elif self.player_vy >= 0.0:
                floor_y = int(round(self.player_y + 1.0))
                foot_x = int(round(self.player_x))
                if 0 <= floor_y < 16 and 0 <= foot_x < 16:
                    if self.platform_grid[floor_y][foot_x] != 0 and self.player_y <= float(floor_y - 0.8):
                        self.player_y = float(floor_y - 1.0)
                        self.player_vy = 0.0
                        self.is_grounded = True
        else:
            # Check edge drop
            floor_y = int(round(self.player_y + 1.0))
            foot_x = int(round(self.player_x))
            if 0 <= floor_y < 16 and 0 <= foot_x < 16:
                if self.platform_grid[floor_y][foot_x] == 0:
                    self.is_grounded = False

    def update_enemies(self, dt: float):
        gravity = 20.0

        for e in self.enemies:
            if not e["active"]:
                continue

            if e["is_flipped"]:
                e["flip_timer"] -= dt
                if e["flip_timer"] <= 0.0:
                    e["is_flipped"] = False
                    e["is_enraged"] = True
                    e["vx"] = 5.2 if e["vx"] > 0 else -5.2
                continue

            e["x"] += e["vx"] * dt
            if e["x"] < 0.0:
                e["x"] += 16.0
            if e["x"] >= 16.0:
                e["x"] -= 16.0

            floor_y = int(round(e["y"] + 1.0))
            foot_x = int(round(e["x"]))

            on_floor = False
            if 0 <= floor_y < 16 and 0 <= foot_x < 16:
                if self.platform_grid[floor_y][foot_x] != 0:
                    on_floor = True

            if not on_floor:
                e["vy"] += gravity * dt
                e["y"] += e["vy"] * dt

                new_floor = int(round(e["y"] + 1.0))
                if 0 <= new_floor < 16 and 0 <= foot_x < 16:
                    if self.platform_grid[new_floor][foot_x] != 0 and e["y"] <= float(new_floor - 0.8):
                        e["y"] = float(new_floor - 1.0)
                        e["vy"] = 0.0

    def check_collisions(self):
        for e in self.enemies:
            if not e["active"]:
                continue

            dist = abs(self.player_x - e["x"]) + abs(self.player_y - e["y"])
            if dist <= 0.82:
                if e["is_flipped"]:
                    e["active"] = False
                    self.enemies_defeated += 1
                    pts = 400 if e["is_enraged"] else 200
                    self.score += pts
                    if self.score > self.high_score:
                        self.high_score = self.score

                    if self.enemies_defeated >= self.total_wave_enemies:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.pow_shake_timer > 0.0:
            self.pow_shake_timer -= dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 4.0
                    self.player_y = 13.0
                    self.player_vx = 0.0
                    self.player_vy = 0.0
                    self.is_grounded = True
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.check_collisions()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # Sewer Navy background
        for i in range(256):
            fb[i * 3 + 0] = 5
            fb[i * 3 + 1] = 5
            fb[i * 3 + 2] = 10

        # Platforms
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                tile = self.platform_grid[y][x]
                if tile == 2:
                    # Blue Platform
                    fb[idx + 0] = 41
                    fb[idx + 1] = 128
                    fb[idx + 2] = 185
                elif tile == 1:
                    # Green Pipe
                    fb[idx + 0] = 39
                    fb[idx + 1] = 174
                    fb[idx + 2] = 96
                elif tile == 3:
                    # POW Block
                    fb[idx + 0] = 230
                    fb[idx + 1] = 126
                    fb[idx + 2] = 34

        # Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                if e["is_flipped"]:
                    fb[idx + 0] = 241
                    fb[idx + 1] = 196
                    fb[idx + 2] = 15
                elif e["is_enraged"]:
                    fb[idx + 0] = 231
                    fb[idx + 1] = 76
                    fb[idx + 2] = 60
                else:
                    fb[idx + 0] = 46
                    fb[idx + 1] = 204
                    fb[idx + 2] = 113

        # Player Mario (Scarlet)
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx + 0] = 231
            fb[idx + 1] = 76
            fb[idx + 2] = 60

        # HUD: Lives on top row
        for l in range(min(self.lives, 3)):
            idx = (0 * 16 + l) * 3
            fb[idx + 0] = 231
            fb[idx + 1] = 76
            fb[idx + 2] = 60

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "pow_hits": self.pow_hits,
            "enemies_remaining": self.get_enemies_remaining(),
            "player_x": self.player_x,
            "player_y": self.player_y,
            "is_grounded": self.is_grounded,
        }
