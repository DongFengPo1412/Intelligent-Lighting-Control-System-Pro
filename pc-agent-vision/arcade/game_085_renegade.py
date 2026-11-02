"""
Game #085: 热血硬派 / 站台对决 (Renegade 1986 / Technos)
Origin of Beat 'em Ups, Backhand Elbow Strikes, Mounted Ground-and-Pound & Subway Track Hazard Pushes.
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

STATE_FIGHT = 0
STATE_VICTORY = 1
STATE_HERO_DEAD = 2

ACT_IDLE = 0
ACT_FRONT_PUNCH = 1
ACT_BACK_ELBOW = 2
ACT_GROUND_POUND = 3
ACT_JUMP_KICK = 4

MAX_THUGS = 3


class Game085Renegade(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FIGHT
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 22000
        self.lives = 3
        self.hero_hp = 100
        self.thugs_defeated = 0

        # Hero Kunio
        self.px = 4.0
        self.py = 10.0
        self.facing = 1
        self.action = ACT_IDLE
        self.act_timer = 0.0
        self.mounted_thug_idx = -1

        self.thugs: List[Dict[str, Any]] = []

        # Train
        self.train_x = -30.0
        self.train_speed = 25.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 85

    @property
    def name(self) -> str:
        return "热血硬派"

    @property
    def english_name(self) -> str:
        return "Renegade"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "反手肘击与骑乘颜面猛揍 + 站台推落铁轨秒杀"

    def get_name(self) -> str:
        return "Renegade (1986)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_FIGHT
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.hero_hp = 100
        self.thugs_defeated = 0
        self.reset_fight()

    def reset_fight(self):
        self.px = 4.0
        self.py = 10.0
        self.facing = 1
        self.action = ACT_IDLE
        self.act_timer = 0.0
        self.mounted_thug_idx = -1

        self.thugs = [
            {"x": 13.0 + i * 3.0, "y": 8.0 + (i * 2.0), "vx": -2.0, "hp": 3, "is_down": False, "down_timer": 0.0, "active": True, "respawn_timer": 0.0}
            for i in range(MAX_THUGS)
        ]

        self.train_x = -30.0

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_HERO_DEAD, STATE_VICTORY):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.train_x += self.train_speed * dt
        if self.train_x > 40.0:
            self.train_x = -30.0

        self.update_player(dt, buttons, prev_buttons)
        self.update_thugs(dt)
        self.check_combat()

        # Train hazard
        if -2.0 <= self.train_x <= 18.0:
            for t in self.thugs:
                if t["active"] and t["y"] >= 13.8 and abs(t["x"] - self.train_x) < 6.0:
                    t["active"] = False
                    self.thugs_defeated += 1
                    self.score += 1000

            if self.py >= 13.8 and abs(self.px - self.train_x) < 5.0:
                self.hero_hp = 0
                self.lives -= 1
                if self.lives > 0:
                    self.hero_hp = 100
                    self.px = 4.0
                    self.py = 10.0
                else:
                    self.state = STATE_HERO_DEAD
                    self.state_timer = 0.0

        if self.thugs_defeated >= 8:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 8000

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 4.8

        if self.act_timer > 0.0:
            self.act_timer -= dt
            if self.act_timer <= 0.0:
                self.action = ACT_IDLE
                self.mounted_thug_idx = -1
            return

        # Jump kick (A + B)
        if (buttons & KEY_A) and (buttons & KEY_B) and (not (prev_buttons & KEY_A) or not (prev_buttons & KEY_B)):
            self.action = ACT_JUMP_KICK
            self.act_timer = 0.35
            return

        # Ground pound / front punch (A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            target_down = -1
            for i, t in enumerate(self.thugs):
                if t["active"] and t["is_down"] and abs(t["x"] - self.px) < 1.4 and abs(t["y"] - self.py) < 1.2:
                    target_down = i
                    break

            if target_down >= 0:
                self.action = ACT_GROUND_POUND
                self.act_timer = 0.5
                self.mounted_thug_idx = target_down
                self.px = self.thugs[target_down]["x"]
                self.py = self.thugs[target_down]["y"]
                self.thugs[target_down]["hp"] -= 2
                self.score += 300
                if self.thugs[target_down]["hp"] <= 0:
                    self.thugs[target_down]["active"] = False
                    self.thugs[target_down]["respawn_timer"] = 2.0
                    self.thugs_defeated += 1
                return
            else:
                self.action = ACT_FRONT_PUNCH
                self.act_timer = 0.22
                return

        # Back elbow (B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.action = ACT_BACK_ELBOW
            self.act_timer = 0.25
            return

        if buttons & KEY_LEFT:
            self.px -= move_speed * dt
            self.facing = -1
        if buttons & KEY_RIGHT:
            self.px += move_speed * dt
            self.facing = 1
        if buttons & KEY_UP:
            self.py -= (move_speed * 0.7) * dt
        if buttons & KEY_DOWN:
            self.py += (move_speed * 0.7) * dt

        self.px = max(1.0, min(15.0, self.px))
        self.py = max(7.0, min(14.2, self.py))

    def update_thugs(self, dt: float):
        for i, t in enumerate(self.thugs):
            if not t["active"]:
                if t.get("respawn_timer", 0.0) > 0.0:
                    t["respawn_timer"] -= dt
                    if t["respawn_timer"] <= 0.0 and self.thugs_defeated + i < 8:
                        t["active"] = True
                        t["x"] = 15.5
                        t["y"] = 8.0 + (i * 2.0)
                        t["hp"] = 3
                        t["is_down"] = False
                        t["down_timer"] = 0.0
                continue

            if t["is_down"]:
                t["down_timer"] -= dt
                if t["down_timer"] <= 0.0:
                    t["is_down"] = False
                continue

            if t["x"] > self.px + 1.2:
                t["x"] -= 2.2 * dt
            elif t["x"] < self.px - 1.2:
                t["x"] += 2.2 * dt

            if t["y"] > self.py + 0.3:
                t["y"] -= 1.3 * dt
            elif t["y"] < self.py - 0.3:
                t["y"] += 1.3 * dt

    def check_combat(self):
        if self.action == ACT_FRONT_PUNCH:
            for t in self.thugs:
                if not t["active"] or t["is_down"]:
                    continue
                dx = (t["x"] - self.px) * self.facing
                dy = abs(t["y"] - self.py)

                if 0.0 < dx < 1.8 and dy < 1.2:
                    t["hp"] -= 1
                    t["x"] += self.facing * 1.5
                    self.score += 150
                    if t["hp"] == 1:
                        t["is_down"] = True
                        t["down_timer"] = 2.5
                    elif t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
        elif self.action == ACT_BACK_ELBOW:
            for t in self.thugs:
                if not t["active"] or t["is_down"]:
                    continue
                dx = (t["x"] - self.px) * (-self.facing)
                dy = abs(t["y"] - self.py)

                if 0.0 < dx < 1.6 and dy < 1.2:
                    t["hp"] -= 2
                    t["x"] -= self.facing * 2.0
                    self.score += 250
                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
        elif self.action == ACT_JUMP_KICK:
            for t in self.thugs:
                if not t["active"]:
                    continue
                dx = (t["x"] - self.px) * self.facing
                dy = abs(t["y"] - self.py)

                if 0.0 < dx < 2.0 and dy < 1.4:
                    t["hp"] -= 2
                    t["x"] += self.facing * 3.5
                    t["y"] += 1.0
                    t["is_down"] = True
                    t["down_timer"] = 2.0
                    self.score += 350
                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1

        for t in self.thugs:
            if not t["active"] or t["is_down"] or self.action == ACT_GROUND_POUND:
                continue
            if abs(t["x"] - self.px) < 1.2 and abs(t["y"] - self.py) < 1.0:
                self.hero_hp -= 1
                if self.hero_hp <= 0:
                    self.lives -= 1
                    if self.lives > 0:
                        self.hero_hp = 100
                        self.px = 4.0
                        self.py = 10.0
                    else:
                        self.state = STATE_HERO_DEAD
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

        # 1. Station Wall
        for y in range(7):
            for x in range(16):
                set_pixel(x, y, 40, 50, 60)
        for x in range(4, 12):
            set_pixel(x, 2, 20, 100, 200)

        # 2. Platform
        for y in range(7, 14):
            for x in range(16):
                set_pixel(x, y, 90, 90, 95)
        for x in range(16):
            set_pixel(x, 13, 255, 220, 0)

        # 3. Track
        for y in range(14, 16):
            for x in range(16):
                set_pixel(x, y, 25, 20, 20)

        tx = int(round(self.train_x))
        for dx in range(-5, 6):
            set_pixel(tx + dx, 14, 200, 40, 40)
            set_pixel(tx + dx, 15, 180, 180, 190)

        # 4. Thugs
        for t in self.thugs:
            if not t["active"]:
                continue
            ex = int(round(t["x"]))
            ey = int(round(t["y"]))

            if t["is_down"]:
                set_pixel(ex, ey, 200, 40, 50)
                set_pixel(ex + 1, ey, 240, 180, 140)
            else:
                set_pixel(ex, ey, 200, 40, 50)
                set_pixel(ex, ey - 1, 240, 180, 140)
                set_pixel(ex, ey - 2, 50, 220, 80)

        # 5. Hero
        px = int(round(self.px))
        py = int(round(self.py))

        if self.action == ACT_GROUND_POUND:
            set_pixel(px, py, 250, 250, 250)
            set_pixel(px, py - 1, 240, 180, 140)
            set_pixel(px, py + 1, 255, 120, 0)
        else:
            set_pixel(px, py, 250, 250, 250)
            set_pixel(px, py - 1, 240, 180, 140)
            set_pixel(px, py - 2, 20, 20, 20)

            if self.action == ACT_FRONT_PUNCH:
                set_pixel(px + self.facing, py, 255, 200, 150)
            elif self.action == ACT_BACK_ELBOW:
                set_pixel(px - self.facing, py, 255, 200, 150)
            elif self.action == ACT_JUMP_KICK:
                set_pixel(px + self.facing * 2, py - 1, 255, 255, 255)

        # 6. HUD
        hp_bars = max(0, min(8, self.hero_hp // 12))
        for b in range(hp_bars):
            set_pixel(b, 15, 50, 220, 50)
        for l in range(self.lives):
            set_pixel(15 - l * 2, 0, 250, 250, 250)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "hero_hp": self.hero_hp,
            "lives": self.lives,
            "thugs_defeated": self.thugs_defeated,
            "action": self.action,
            "px": self.px,
            "py": self.py,
        }
