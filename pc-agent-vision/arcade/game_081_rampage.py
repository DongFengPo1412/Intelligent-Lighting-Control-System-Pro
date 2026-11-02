"""
Game #081: 狂暴巨兽 / 拆楼大战 (Rampage 1986 / Midway)
Kaiju Building Climber, Facade Demolition, Structural Collapse & Helicopter Interception.
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

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_MONSTER_DEAD = 2


class Game081Rampage(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 16000
        self.lives = 3
        self.monster_hp = 100
        self.days_survived = 1

        # Monster
        self.mx = 1.0
        self.my = 14.0
        self.mvy = 0.0
        self.on_ground = True
        self.on_wall = False
        self.current_building = -1
        self.facing = 1
        self.punch_timer = 0.0

        self.buildings: List[Dict[str, Any]] = []
        self.heli = {
            "x": 15.0,
            "y": 3.0,
            "vx": -2.5,
            "active": True,
        }

        self.reset()

    @property
    def game_id(self) -> int:
        return 81

    @property
    def name(self) -> str:
        return "狂暴巨兽"

    @property
    def english_name(self) -> str:
        return "Rampage"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "巨兽大楼攀爬 + 拳击承重墙拆楼坍塌 + 破窗击坠武装直升机"

    def get_name(self) -> str:
        return "Rampage (1986)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.monster_hp = 100
        self.days_survived = 1
        self.reset_city()

    def reset_city(self):
        self.mx = 1.0
        self.my = 14.0
        self.mvy = 0.0
        self.on_ground = True
        self.on_wall = False
        self.current_building = -1
        self.facing = 1
        self.punch_timer = 0.0

        self.buildings = [
            {"x_left": 1.0, "x_right": 4.0, "height": 10, "hp": 6, "collapsed": False},
            {"x_left": 6.0, "x_right": 9.0, "height": 12, "hp": 8, "collapsed": False},
            {"x_left": 11.0, "x_right": 14.0, "height": 9, "hp": 6, "collapsed": False},
        ]

        self.heli = {
            "x": 15.0,
            "y": 3.0,
            "vx": -2.5,
            "active": True,
        }

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_MONSTER_DEAD:
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.days_survived += 1
                self.score += 5000
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.reset_city()
            return

        self.update_monster(dt, buttons, prev_buttons)
        self.update_helicopter(dt)

        if all(b["collapsed"] for b in self.buildings):
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def update_monster(self, dt: float, buttons: int, prev_buttons: int):
        walk_speed = 4.0
        climb_speed = 3.5

        if self.punch_timer > 0.0:
            self.punch_timer -= dt

        # Attach wall check
        if not self.on_wall:
            for i, b in enumerate(self.buildings):
                if b["collapsed"]:
                    continue
                top_y = 14.0 - b["height"]
                if top_y <= self.my <= 14.0:
                    if abs(self.mx - b["x_left"]) < 0.6 and (buttons & KEY_UP):
                        self.on_wall = True
                        self.on_ground = False
                        self.current_building = i
                        self.mx = b["x_left"]
                        self.mvy = 0.0
                        break
                    elif abs(self.mx - b["x_right"]) < 0.6 and (buttons & KEY_UP):
                        self.on_wall = True
                        self.on_ground = False
                        self.current_building = i
                        self.mx = b["x_right"]
                        self.mvy = 0.0
                        break

        if self.on_wall:
            if buttons & KEY_UP:
                self.my -= climb_speed * dt
            if buttons & KEY_DOWN:
                self.my += climb_speed * dt

            top_y = 14.0 - self.buildings[self.current_building]["height"]
            self.my = max(top_y, min(14.0, self.my))

            if self.my >= 14.0:
                self.on_wall = False
                self.on_ground = True
                self.mvy = 0.0

            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.on_wall = False
                self.mvy = -6.0
                leap_dir = -1.0 if self.mx <= self.buildings[self.current_building]["x_left"] else 1.0
                self.mx += leap_dir * 1.5
        else:
            if buttons & KEY_LEFT:
                self.mx -= walk_speed * dt
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.mx += walk_speed * dt
                self.facing = 1

            self.mx = max(0.5, min(15.0, self.mx))

            if self.on_ground and (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.on_ground = False
                self.mvy = -8.0

            if not self.on_ground:
                self.mvy += 20.0 * dt
                self.my += self.mvy * dt
                if self.my >= 14.0:
                    self.my = 14.0
                    self.mvy = 0.0
                    self.on_ground = True

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.punch_timer = 0.22
            self.check_punch()

    def check_punch(self):
        # 1. Swat Helicopter
        if self.heli["active"]:
            dx = abs(self.heli["x"] - self.mx)
            dy = abs(self.heli["y"] - self.my)
            if dx < 2.0 and dy < 2.0:
                self.heli["active"] = False
                self.heli["respawn_timer"] = 3.0
                self.score += 1000
                return

        # 2. Punch Building Wall
        for i, b in enumerate(self.buildings):
            if b["collapsed"]:
                continue

            in_range_x = (b["x_left"] - 1.2 <= self.mx <= b["x_right"] + 1.2)
            top_y = 14.0 - b["height"]
            in_range_y = (top_y <= self.my <= 14.0)

            if in_range_x and in_range_y:
                b["hp"] -= 1
                self.score += 200

                if b["hp"] <= 0:
                    b["collapsed"] = True
                    self.score += 2000
                    if self.on_wall and self.current_building == i:
                        self.on_wall = False
                        self.mvy = 4.0
                break

    def update_helicopter(self, dt: float):
        if not self.heli["active"]:
            if self.heli.get("respawn_timer", 0.0) > 0.0:
                self.heli["respawn_timer"] -= dt
                if self.heli["respawn_timer"] <= 0.0:
                    self.heli["x"] = 15.5
                    self.heli["y"] = 4.0
                    self.heli["vx"] = -2.5
                    self.heli["active"] = True
            return

        self.heli["x"] += self.heli["vx"] * dt
        if self.heli["x"] < -1.0:
            self.heli["x"] = 16.0

        if abs(self.heli["x"] - self.mx) < 1.4 and abs(self.heli["y"] - self.my) < 1.4:
            self.monster_hp -= 8
            if self.monster_hp <= 0:
                self.lives -= 1
                if self.lives > 0:
                    self.monster_hp = 100
                    self.mx = 1.0
                    self.my = 14.0
                    self.on_wall = False
                    self.on_ground = True
                else:
                    self.state = STATE_MONSTER_DEAD
                    self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Sky
        for y in range(14):
            for x in range(16):
                set_pixel(x, y, 10, 15, 30)

        # 2. Ground
        for y in range(14, 16):
            for x in range(16):
                set_pixel(x, y, 60, 60, 60)

        # 3. Buildings
        for b in self.buildings:
            xl = int(round(b["x_left"]))
            xr = int(round(b["x_right"]))

            if b["collapsed"]:
                for x in range(xl, xr + 1):
                    set_pixel(x, 14, 100, 80, 60)
                    set_pixel(x, 13, 80, 60, 40)
            else:
                top_y = 14 - b["height"]
                for y in range(top_y, 14):
                    for x in range(xl, xr + 1):
                        if (x + y) % 2 == 0:
                            set_pixel(x, y, 255, 230, 100)
                        else:
                            set_pixel(x, y, 120, 100, 90)

        # 4. Heli
        if self.heli["active"]:
            hx = int(round(self.heli["x"]))
            hy = int(round(self.heli["y"]))
            set_pixel(hx, hy, 40, 120, 220)
            set_pixel(hx - 1, hy, 255, 255, 255)
            set_pixel(hx + 1, hy, 255, 255, 255)
            set_pixel(hx, hy - 1, 200, 200, 200)

        # 5. Monster
        mx = int(round(self.mx))
        my = int(round(self.my))
        set_pixel(mx, my, 140, 80, 30)
        set_pixel(mx, my - 1, 255, 200, 50)
        if self.punch_timer > 0.0:
            set_pixel(mx + self.facing, my, 255, 100, 20)

        # 6. Health & Lives
        hp_bars = max(0, min(8, self.monster_hp // 12))
        for b in range(hp_bars):
            set_pixel(b, 0, 50, 240, 50)
        for l in range(self.lives):
            set_pixel(15 - l * 2, 0, 255, 180, 0)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "monster_hp": self.monster_hp,
            "mx": self.mx,
            "my": self.my,
            "on_wall": self.on_wall,
            "buildings_standing": len([b for b in self.buildings if not b["collapsed"]]),
        }
