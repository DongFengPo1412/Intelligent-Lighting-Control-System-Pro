"""
Game #069: 疯狂跳球 / 螺旋弹球 (Q*bert 1982 / Gottlieb)
Isometric Stepped Cube Pyramid Jumping, Grid Color Flipping, Escape Discs & Coily the Snake Chase.
"""

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

NUM_ROWS = 5
TOTAL_CUBES = 15
MAX_BALLS = 2


def get_cube_index(r: int, c: int) -> int:
    if r < 0 or r >= NUM_ROWS or c < 0 or c > r:
        return -1
    return (r * (r + 1)) // 2 + c


class Game069Qbert(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 7000
        self.lives = 3

        self.player_row = 0
        self.player_col = 0
        self.jump_anim_timer = 0.0

        self.cube_flipped: List[bool] = [False] * TOTAL_CUBES
        self.cubes_flipped = 1

        self.disc_left_active = True
        self.disc_right_active = True
        self.freeze_timer = 0.0
        self.enemy_spawn_timer = 2.5

        # Coily
        self.coily = {
            "row": 0,
            "col": 0,
            "is_hatched": False,
            "jump_timer": 1.0,
            "active": True,
        }

        self.balls: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 69

    @property
    def name(self) -> str:
        return "疯狂跳球"

    @property
    def english_name(self) -> str:
        return "Q*bert"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "等轴立体金字塔斜向跳跃 + 阶梯方块踏步翻色 + 盘旋巨蟒诱捕与飞盘逃生"

    def get_name(self) -> str:
        return "Q*bert (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_stage()

    def init_stage(self):
        self.player_row = 0
        self.player_col = 0
        self.jump_anim_timer = 0.0

        self.cube_flipped = [False] * TOTAL_CUBES
        self.cube_flipped[0] = True
        self.cubes_flipped = 1

        self.disc_left_active = True
        self.disc_right_active = True
        self.freeze_timer = 0.0
        self.enemy_spawn_timer = 1.5

        self.coily = {
            "row": 0,
            "col": 0,
            "is_hatched": False,
            "jump_timer": 1.0,
            "active": False,
        }
        self.balls = []

    def jump(self, drow: int, dcol: int):
        if self.jump_anim_timer > 0.0:
            return

        nr = self.player_row + drow
        nc = self.player_col + dcol

        # Escape discs
        if nr == 2 and nc == -1 and self.disc_left_active:
            self.disc_left_active = False
            self.player_row = 0
            self.player_col = 0
            self.score += 500
            if self.coily["active"] and self.coily["is_hatched"]:
                self.coily["active"] = False
                self.score += 500
            return

        if nr == 2 and nc == 3 and self.disc_right_active:
            self.disc_right_active = False
            self.player_row = 0
            self.player_col = 0
            self.score += 500
            if self.coily["active"] and self.coily["is_hatched"]:
                self.coily["active"] = False
                self.score += 500
            return

        idx = get_cube_index(nr, nc)
        if idx == -1:
            # Fell off pyramid!
            self.lives -= 1
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        self.player_row = nr
        self.player_col = nc
        self.jump_anim_timer = 0.18

        if not self.cube_flipped[idx]:
            self.cube_flipped[idx] = True
            self.cubes_flipped += 1
            self.score += 25

            if self.cubes_flipped >= TOTAL_CUBES:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 3500
                if self.score > self.high_score:
                    self.high_score = self.score

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_row = 0
                    self.player_col = 0
                    self.coily["row"] = 0
                    self.coily["col"] = 0
                    self.coily["is_hatched"] = False
                    self.coily["jump_timer"] = 1.0
                    self.coily["active"] = True
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        if self.jump_anim_timer > 0.0:
            self.jump_anim_timer -= dt

        if self.freeze_timer > 0.0:
            self.freeze_timer -= dt
        else:
            self.update_enemies(dt)

        self.update_player(dt, buttons, prev_buttons)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        if self.jump_anim_timer > 0.0:
            return

        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            self.jump(-1, -1)
        elif (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
            self.jump(-1, 0)
        elif (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
            self.jump(1, 0)
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            self.jump(1, 1)

    def update_enemies(self, dt: float):
        if self.coily["active"]:
            self.coily["jump_timer"] -= dt
            if self.coily["jump_timer"] <= 0.0:
                self.coily["jump_timer"] = 0.85
                if not self.coily["is_hatched"]:
                    import random
                    self.coily["row"] += 1
                    self.coily["col"] += random.randint(0, 1)
                    if self.coily["row"] >= 4:
                        self.coily["is_hatched"] = True
                else:
                    dr, dc = 0, 0
                    if self.coily["row"] < self.player_row:
                        dr = 1
                        dc = 1 if self.coily["col"] <= self.player_col else 0
                    elif self.coily["row"] > self.player_row:
                        dr = -1
                        dc = -1 if self.coily["col"] > self.player_col else 0
                    else:
                        if self.coily["col"] < self.player_col:
                            dr, dc = 1, 1
                        else:
                            dr, dc = -1, -1

                    nr = self.coily["row"] + dr
                    nc = self.coily["col"] + dc
                    if get_cube_index(nr, nc) != -1:
                        self.coily["row"] = nr
                        self.coily["col"] = nc
        else:
            self.enemy_spawn_timer -= dt
            if self.enemy_spawn_timer <= 0.0:
                self.enemy_spawn_timer = 3.0
                self.coily["active"] = True
                self.coily["row"] = 0
                self.coily["col"] = 0
                self.coily["is_hatched"] = False
                self.coily["jump_timer"] = 1.0

        for b in self.balls:
            if not b["active"]:
                continue
            b["jump_timer"] -= dt
            if b["jump_timer"] <= 0.0:
                import random
                b["jump_timer"] = 0.75
                b["row"] += 1
                b["col"] += random.randint(0, 1)
                if b["row"] >= NUM_ROWS:
                    b["active"] = False

        self.balls = [b for b in self.balls if b["active"]]

    def check_collisions(self):
        # 1. Coily collision
        if self.coily["active"] and self.coily["row"] == self.player_row and self.coily["col"] == self.player_col:
            self.lives -= 1
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        # 2. Balls collision
        for b in self.balls:
            if not b["active"]:
                continue
            if b["row"] == self.player_row and b["col"] == self.player_col:
                b["active"] = False
                if b["is_green"]:
                    self.freeze_timer = 4.0
                    self.score += 100
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 2. Isometric Pyramid
        for r in range(NUM_ROWS):
            for c in range(r + 1):
                idx = get_cube_index(r, c)
                flipped = self.cube_flipped[idx]

                cx = 7 - r * 1 + c * 3
                cy = 3 + r * 2

                top_r = 255 if flipped else 20
                top_g = 220 if flipped else 60
                top_b = 20 if flipped else 200

                set_pixel(cx, cy, top_r, top_g, top_b)
                set_pixel(cx + 1, cy, top_r, top_g, top_b)
                set_pixel(cx, cy + 1, top_r // 2, top_g // 2, top_b // 2)
                set_pixel(cx + 1, cy + 1, top_r // 4, top_g // 4, top_b // 4)

        # 3. Escape Discs
        if self.disc_left_active:
            set_pixel(2, 7, 255, 100, 255)
            set_pixel(3, 7, 255, 100, 255)
        if self.disc_right_active:
            set_pixel(13, 7, 255, 100, 255)
            set_pixel(14, 7, 255, 100, 255)

        # 4. Balls
        for b in self.balls:
            if not b["active"]:
                continue
            bx = 7 - b["row"] * 1 + b["col"] * 3
            by = 3 + b["row"] * 2 - 1
            if b["is_green"]:
                set_pixel(bx, by, 50, 255, 50)
            else:
                set_pixel(bx, by, 255, 40, 40)

        # 5. Coily
        if self.coily["active"]:
            sx = 7 - self.coily["row"] * 1 + self.coily["col"] * 3
            sy = 3 + self.coily["row"] * 2 - 1
            if not self.coily["is_hatched"]:
                set_pixel(sx, sy, 200, 40, 220)
            else:
                set_pixel(sx, sy, 180, 20, 220)
                set_pixel(sx, sy - 1, 255, 30, 30)

        # 6. Q*bert
        if self.state != STATE_DEAD:
            qx = 7 - self.player_row * 1 + self.player_col * 3
            qy = 3 + self.player_row * 2 - 1
            set_pixel(qx, qy, 255, 140, 20)
            set_pixel(qx + 1, qy, 255, 100, 0)
            set_pixel(qx, qy - 1, 255, 255, 255)
        else:
            qx = 7 - self.player_row * 1 + self.player_col * 3
            qy = 3 + self.player_row * 2 - 1
            set_pixel(qx, qy, 255, 255, 0)
            set_pixel(qx + 1, qy - 1, 255, 0, 0)

        # 7. Freeze HUD
        if self.freeze_timer > 0.0:
            set_pixel(0, 0, 0, 255, 255)
            set_pixel(15, 0, 0, 255, 255)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "player_row": self.player_row,
            "player_col": self.player_col,
            "cubes_flipped": self.cubes_flipped,
            "disc_left_active": self.disc_left_active,
            "disc_right_active": self.disc_right_active,
            "freeze_timer": self.freeze_timer,
        }
