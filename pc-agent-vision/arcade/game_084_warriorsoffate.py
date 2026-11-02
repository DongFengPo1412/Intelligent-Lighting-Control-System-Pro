"""
Game #084: 吞食天地 / 马上三国 (Warriors of Fate 1992 / Capcom)
Mounted Cavalry Battles, Glaive Thrusts & Sweeps, De-horsing Dismounts & Dumpling Feast Bonus Stage.
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

STATE_BATTLE = 0
STATE_EATING_BONUS = 1
STATE_STAGE_CLEAR = 2
STATE_HERO_DEAD = 3

MAX_ENEMIES = 3


class Game084WarriorsOfFate(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_BATTLE
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 25000
        self.lives = 3
        self.hero_hp = 100
        self.enemies_defeated = 0

        # Hero Guan Yu
        self.hx = 3.0
        self.hy = 10.0
        self.facing = 1
        self.mounted = True
        self.charging = False
        self.charge_timer = 0.0
        self.atk_timer = 0.0

        self.enemies: List[Dict[str, Any]] = []

        # Eating Bonus
        self.baozi_total = 20
        self.baozi_eaten = 0
        self.eating_timer = 8.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 84

    @property
    def name(self) -> str:
        return "吞食天地"

    @property
    def english_name(self) -> str:
        return "Warriors of Fate"

    @property
    def release_year(self) -> int:
        return 1992

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "战马骑乘长矛突刺冲锋 + 下马步战摔投 + 吃肉包奖励关"

    def get_name(self) -> str:
        return "Warriors of Fate (1992)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_BATTLE
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.hero_hp = 100
        self.enemies_defeated = 0
        self.mounted = True
        self.reset_battle()

    def reset_battle(self):
        self.hx = 3.0
        self.hy = 10.0
        self.facing = 1
        self.charging = False
        self.charge_timer = 0.0
        self.atk_timer = 0.0

        self.enemies = [
            {"x": 14.0 + i * 3.5, "y": 8.5 + (i * 2.0), "vx": -2.2, "hp": 2, "is_boss": False, "active": True}
            for i in range(MAX_ENEMIES)
        ]

    def start_bonus_stage(self):
        self.state = STATE_EATING_BONUS
        self.state_timer = 0.0
        self.baozi_eaten = 0
        self.eating_timer = 8.0

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_HERO_DEAD, STATE_STAGE_CLEAR):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_EATING_BONUS:
            self.update_eating(dt, buttons, prev_buttons)
            return

        self.update_hero(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.check_attacks()

    def update_hero(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 6.5 if self.mounted else 4.2

        if self.charging:
            self.charge_timer -= dt
            self.hx += self.facing * 12.0 * dt
            if self.charge_timer <= 0.0:
                self.charging = False
        else:
            if buttons & KEY_LEFT:
                self.hx -= move_speed * dt
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.hx += move_speed * dt
                self.facing = 1
            if buttons & KEY_UP:
                self.hy -= (move_speed * 0.7) * dt
            if buttons & KEY_DOWN:
                self.hy += (move_speed * 0.7) * dt

            self.hx = max(1.0, min(14.5, self.hx))
            self.hy = max(8.0, min(13.5, self.hy))

            # Horse Stampede or Remount (B)
            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                if self.mounted:
                    self.atk_timer = 0.3
                    for e in self.enemies:
                        if e["active"] and abs(e["x"] - self.hx) < 2.0 and abs(e["y"] - self.hy) < 1.5:
                            e["hp"] -= 1
                            e["x"] += self.facing * 2.0
                else:
                    self.mounted = True

        if self.atk_timer > 0.0:
            self.atk_timer -= dt

        # Attack (A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.atk_timer = 0.25
            if self.mounted and ((self.facing == 1 and (buttons & KEY_RIGHT)) or (self.facing == -1 and (buttons & KEY_LEFT))):
                self.charging = True
                self.charge_timer = 0.35

    def update_enemies(self, dt: float):
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                if self.enemies_defeated < 6:
                    e["active"] = True
                    e["x"] = 15.5
                    e["y"] = 8.0 + (i * 2.0)
                    e["hp"] = 2
                    e["is_boss"] = False
                elif self.enemies_defeated == 6:
                    e["active"] = True
                    e["x"] = 15.0
                    e["y"] = 10.0
                    e["hp"] = 8
                    e["is_boss"] = True
                    self.enemies_defeated += 1
                continue

            if e["x"] > self.hx + 1.4:
                e["x"] -= 2.2 * dt
            elif e["x"] < self.hx - 1.4:
                e["x"] += 2.2 * dt

            if e["y"] > self.hy + 0.3:
                e["y"] -= 1.2 * dt
            elif e["y"] < self.hy - 0.3:
                e["y"] += 1.2 * dt

    def check_attacks(self):
        if self.atk_timer > 0.05 or self.charging:
            reach = 2.6 if self.mounted else 1.6
            for e in self.enemies:
                if not e["active"]:
                    continue

                dx = (e["x"] - self.hx) * self.facing
                dy = abs(e["y"] - self.hy)

                if 0.0 < dx < reach and dy < 1.4:
                    dmg = 2 if self.charging else 1
                    e["hp"] -= dmg
                    e["x"] += self.facing * 1.5

                    if e["hp"] <= 0:
                        e["active"] = False
                        self.score += 3000 if e["is_boss"] else 300
                        if e["is_boss"]:
                            self.start_bonus_stage()
                            return
                        else:
                            self.enemies_defeated += 1

        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - self.hx) < 1.3 and abs(e["y"] - self.hy) < 1.0:
                self.hero_hp -= 2 if e["is_boss"] else 1
                if self.mounted and self.hero_hp < 50:
                    self.mounted = False

                if self.hero_hp <= 0:
                    self.lives -= 1
                    if self.lives > 0:
                        self.hero_hp = 100
                        self.mounted = True
                        self.hx = 3.0
                        self.hy = 10.0
                    else:
                        self.state = STATE_HERO_DEAD
                        self.state_timer = 0.0
                    return

    def update_eating(self, dt: float, buttons: int, prev_buttons: int):
        self.eating_timer -= dt

        if ((buttons & KEY_A) and not (prev_buttons & KEY_A)) or \
           ((buttons & KEY_B) and not (prev_buttons & KEY_B)):
            if self.baozi_eaten < self.baozi_total:
                self.baozi_eaten += 1
                self.score += 250

        if self.baozi_eaten >= self.baozi_total or self.eating_timer <= 0.0:
            if self.baozi_eaten >= self.baozi_total:
                self.score += 5000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        if self.state == STATE_EATING_BONUS:
            for y in range(16):
                for x in range(16): set_pixel(x, y, 40, 20, 15)
            for y in range(8, 15):
                for x in range(2, 14): set_pixel(x, y, 160, 100, 50)

            remaining = self.baozi_total - self.baozi_eaten
            for i in range(min(10, remaining)):
                set_pixel(3 + i, 9, 255, 255, 230)
                set_pixel(3 + i, 10, 240, 240, 200)

            set_pixel(7, 5, 240, 180, 140)
            set_pixel(8, 5, 240, 180, 140)
            set_pixel(7, 6, 20, 100, 40)
            return bytes(fb)

        # 1. Sky
        for y in range(7):
            for x in range(16):
                set_pixel(x, y, 90, 30, 20)
        set_pixel(2, 4, 255, 200, 0)
        set_pixel(13, 4, 255, 40, 40)

        # 2. Ground
        for y in range(7, 15):
            for x in range(16):
                set_pixel(x, y, 80, 65, 45)

        # 3. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["is_boss"]:
                set_pixel(ex, ey, 220, 180, 40)
                set_pixel(ex, ey - 1, 255, 40, 40)
                set_pixel(ex - 1, ey, 240, 200, 50)
            else:
                set_pixel(ex, ey, 50, 100, 200)
                set_pixel(ex, ey - 1, 240, 180, 140)
                set_pixel(ex - 1, ey, 180, 180, 180)

        # 4. Hero
        hx = int(round(self.hx))
        hy = int(round(self.hy))

        if self.mounted:
            set_pixel(hx, hy, 180, 40, 30)
            set_pixel(hx + self.facing, hy, 210, 50, 40)
            set_pixel(hx - self.facing, hy, 160, 30, 20)
            set_pixel(hx, hy - 1, 30, 160, 50)
            set_pixel(hx, hy - 2, 200, 120, 80)
            if self.atk_timer > 0.0 or self.charging:
                set_pixel(hx + self.facing * 2, hy - 1, 240, 240, 255)
                set_pixel(hx + self.facing * 3, hy - 1, 255, 255, 255)
        else:
            set_pixel(hx, hy, 30, 160, 50)
            set_pixel(hx, hy - 1, 200, 120, 80)
            if self.atk_timer > 0.0:
                set_pixel(hx + self.facing, hy, 255, 255, 255)

        # 5. Health & Mount Icon
        hp_bars = max(0, min(8, self.hero_hp // 12))
        for b in range(hp_bars):
            set_pixel(b, 15, 50, 220, 50)
        if self.mounted:
            set_pixel(15, 15, 220, 50, 30)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "hero_hp": self.hero_hp,
            "lives": self.lives,
            "mounted": self.mounted,
            "charging": self.charging,
            "enemies_defeated": self.enemies_defeated,
            "baozi_eaten": self.baozi_eaten,
            "hx": self.hx,
            "hy": self.hy,
        }
