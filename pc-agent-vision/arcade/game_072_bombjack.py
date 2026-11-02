"""
Game #072: 炸弹杰克 / 金币小飞侠 (Bomb Jack 1984 / Tehkan)
High-Altitude Glide & Wing Flapping Jump, Lit Fuse Sequential Bomb Defusal & Power Ball Coin Transmutation.
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

MAX_BOMBS = 8
MAX_ENEMIES = 3


class Game072BombJack(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 8500
        self.lives = 3

        # Jack state
        self.px = 7.5
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.is_gliding = False
        self.facing = 1

        self.lit_bombs_collected = 0
        self.combo_multiplier = 1
        self.power_ball_spawned = False
        self.pb_x = 7.5
        self.pb_y = -2.0
        self.pb_vy = 2.0
        self.power_ball_timer = 0.0

        self.bombs: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 72

    @property
    def name(self) -> str:
        return "炸弹杰克"

    @property
    def english_name(self) -> str:
        return "Bomb Jack"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "悬空滑翔重力扑翼 + 导火索按序引爆炸弹 + 能量球时间定身清怪"

    def get_name(self) -> str:
        return "Bomb Jack (1984)"

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
        self.px = 7.5
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.is_gliding = False
        self.facing = 1
        self.lit_bombs_collected = 0
        self.combo_multiplier = 1
        self.power_ball_spawned = False
        self.power_ball_timer = 0.0

        self.bombs = [
            {"x": 3.0, "y": 10.0, "is_lit": True, "active": True},
            {"x": 12.0, "y": 10.0, "is_lit": False, "active": True},
            {"x": 2.5, "y": 5.0, "is_lit": False, "active": True},
            {"x": 12.5, "y": 5.0, "is_lit": False, "active": True},
            {"x": 7.0, "y": 3.0, "is_lit": False, "active": True},
            {"x": 8.5, "y": 3.0, "is_lit": False, "active": True},
            {"x": 4.0, "y": 14.0, "is_lit": False, "active": True},
            {"x": 11.0, "y": 14.0, "is_lit": False, "active": True},
        ]

        self.enemies = [
            {"x": 2.0, "y": 2.0, "vx": 2.5, "vy": 1.8, "type": 0, "is_frozen": False, "active": True},
            {"x": 13.0, "y": 8.0, "vx": -2.0, "vy": 0.0, "type": 1, "is_frozen": False, "active": True},
            {"x": 7.0, "y": 9.0, "vx": -1.8, "vy": 2.0, "type": 2, "is_frozen": False, "active": True},
        ]

    def get_bombs_remaining(self) -> int:
        return len([b for b in self.bombs if b["active"]])

    def light_next_bomb(self):
        for b in self.bombs:
            if b["active"] and not b["is_lit"]:
                b["is_lit"] = True
                return

    def jump(self):
        if self.on_ground:
            self.pvy = -12.5
            self.on_ground = False
            self.is_gliding = False

    def glide_brake(self):
        if not self.on_ground:
            self.pvy = max(-3.0, self.pvy * 0.4 - 2.0)
            self.is_gliding = True

    def dive_stomp(self):
        if not self.on_ground:
            self.pvy = 14.0
            self.is_gliding = False

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.px = 7.5
                    self.py = 14.0
                    self.pvy = 0.0
                    self.on_ground = True
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        if self.power_ball_timer > 0.0:
            self.power_ball_timer -= dt
            if self.power_ball_timer <= 0.0:
                for e in self.enemies:
                    e["is_frozen"] = False

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.update_power_ball(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 6.0
        if buttons & KEY_LEFT:
            self.px -= move_speed * dt
            self.facing = -1
        if buttons & KEY_RIGHT:
            self.px += move_speed * dt
            self.facing = 1

        self.px = max(0.5, min(15.0, self.px))

        grav = 6.0 if self.is_gliding else 20.0
        self.pvy += grav * dt
        self.py += self.pvy * dt

        self.on_ground = False
        if self.pvy >= 0.0:
            if self.py >= 14.0:
                self.py = 14.0
                self.pvy = 0.0
                self.on_ground = True
                self.is_gliding = False
            elif 10.0 <= self.py <= 10.6 and ((1.8 <= self.px <= 6.2) or (8.8 <= self.px <= 13.2)):
                self.py = 10.0
                self.pvy = 0.0
                self.on_ground = True
                self.is_gliding = False
            elif 5.0 <= self.py <= 5.6 and ((0.8 <= self.px <= 4.2) or (10.8 <= self.px <= 14.2)):
                self.py = 5.0
                self.pvy = 0.0
                self.on_ground = True
                self.is_gliding = False
            elif 3.0 <= self.py <= 3.6 and (5.8 <= self.px <= 9.2):
                self.py = 3.0
                self.pvy = 0.0
                self.on_ground = True
                self.is_gliding = False

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.on_ground:
                self.jump()
            else:
                self.glide_brake()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.dive_stomp()

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"] or e["is_frozen"]:
                continue

            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["x"] <= 1.0:
                e["x"] = 1.0
                e["vx"] = abs(e["vx"])
            elif e["x"] >= 14.5:
                e["x"] = 14.5
                e["vx"] = -abs(e["vx"])

            if e["y"] <= 1.0:
                e["y"] = 1.0
                e["vy"] = abs(e["vy"])
            elif e["y"] >= 14.0:
                e["y"] = 14.0
                e["vy"] = -abs(e["vy"])

    def update_power_ball(self, dt: float):
        if not self.power_ball_spawned:
            return
        self.pb_y += self.pb_vy * dt
        if self.pb_y > 15.5:
            self.power_ball_spawned = False

    def check_collisions(self):
        # 1. Bomb collections
        for b in self.bombs:
            if not b["active"]:
                continue

            if abs(self.px - b["x"]) < 1.1 and abs(self.py - b["y"]) < 1.1:
                b["active"] = False

                if b["is_lit"]:
                    self.score += 200 * self.combo_multiplier
                    self.combo_multiplier = min(4, self.combo_multiplier + 1)
                    self.lit_bombs_collected += 1
                    self.light_next_bomb()

                    if self.lit_bombs_collected == 3 and not self.power_ball_spawned:
                        self.power_ball_spawned = True
                        self.pb_x = self.px
                        self.pb_y = 1.0
                        self.pb_vy = 2.5
                else:
                    self.score += 100
                    self.combo_multiplier = 1

                if self.get_bombs_remaining() == 0:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 3500
                    if self.score > self.high_score:
                        self.high_score = self.score
                    return

        # 2. Power Ball collection
        if self.power_ball_spawned:
            if abs(self.px - self.pb_x) < 1.2 and abs(self.py - self.pb_y) < 1.2:
                self.power_ball_spawned = False
                self.power_ball_timer = 5.0
                self.score += 1000
                for e in self.enemies:
                    e["is_frozen"] = True

        # 3. Enemy collisions
        for e in self.enemies:
            if not e["active"]:
                continue

            if abs(self.px - e["x"]) < 1.0 and abs(self.py - e["y"]) < 1.0:
                if e["is_frozen"]:
                    e["active"] = False
                    self.score += 500
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

        # 1. Background
        for y in range(16):
            for x in range(16):
                if y >= 10:
                    set_pixel(x, y, 160, 120, 50)
                else:
                    set_pixel(x, y, 30, 80, 160)

        # 2. Platforms
        for x in range(16): set_pixel(x, 15, 180, 140, 60)
        for x in range(2, 7): set_pixel(x, 11, 200, 180, 80)
        for x in range(9, 14): set_pixel(x, 11, 200, 180, 80)
        for x in range(1, 5): set_pixel(x, 6, 200, 180, 80)
        for x in range(11, 15): set_pixel(x, 6, 200, 180, 80)
        for x in range(6, 10): set_pixel(x, 4, 200, 180, 80)

        # 3. Bombs
        for b in self.bombs:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))

            set_pixel(bx, by, 30, 30, 40)
            if b["is_lit"]:
                spark = (int(self.state_timer * 20.0) % 2 == 0)
                set_pixel(bx, by - 1, 255, 50 if spark else 220, 0)
            else:
                set_pixel(bx, by - 1, 140, 100, 40)

        # 4. Power Ball
        if self.power_ball_spawned:
            px = int(round(self.pb_x))
            py = int(round(self.pb_y))
            set_pixel(px, py, 255, 215, 0)
            set_pixel(px, py - 1, 255, 255, 255)

        # 5. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))

            if e["is_frozen"]:
                set_pixel(ex, ey, 255, 220, 0)
                set_pixel(ex, ey - 1, 255, 255, 100)
            else:
                if e["type"] == 0:
                    set_pixel(ex, ey, 40, 200, 220)
                    set_pixel(ex - 1, ey, 220, 40, 40)
                    set_pixel(ex + 1, ey, 220, 40, 40)
                elif e["type"] == 1:
                    set_pixel(ex, ey, 220, 220, 200)
                    set_pixel(ex, ey - 1, 255, 50, 50)
                else:
                    set_pixel(ex, ey, 240, 100, 30)
                    set_pixel(ex, ey - 1, 255, 200, 50)

        # 6. Jack
        if self.state != STATE_DEAD:
            jx = int(round(self.px))
            jy = int(round(self.py))
            set_pixel(jx, jy, 40, 100, 240)
            set_pixel(jx - self.facing, jy, 220, 30, 30)
            set_pixel(jx, jy - 1, 255, 220, 160)
            set_pixel(jx, jy - 2, 240, 220, 40)
        else:
            jx = int(round(self.px))
            jy = int(round(self.py))
            set_pixel(jx, jy, 255, 50, 50)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "px": self.px,
            "py": self.py,
            "bombs_remaining": self.get_bombs_remaining(),
            "lit_bombs_collected": self.lit_bombs_collected,
            "combo_multiplier": self.combo_multiplier,
            "power_ball_timer": self.power_ball_timer,
        }
