"""
Game #087: 怒之铁拳 / 召唤警车 (Streets of Rage 1991 / Sega)
Classic Beat 'em Up, German Suplex Back Grapple & Emergency Backup Police Car Rocket Artillery.
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

STATE_STREET_BRAWL = 0
STATE_POLICE_BACKUP = 1
STATE_STAGE_CLEAR = 2
STATE_HERO_DEAD = 3

ATK_NONE = 0
ATK_PUNCH = 1
ATK_FLYING_KICK = 2
ATK_SUPLEX = 3

MAX_THUGS = 3


class Game087StreetsOfRage(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_STREET_BRAWL
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 28000
        self.lives = 3
        self.hero_hp = 100
        self.backup_calls = 1
        self.thugs_defeated = 0

        # Axel Stone
        self.px = 3.5
        self.py = 10.5
        self.facing = 1
        self.atk_state = ATK_NONE
        self.atk_timer = 0.0

        self.thugs: List[Dict[str, Any]] = []

        # Police backup
        self.rocket_x = 0.0
        self.rocket_y = 14.0
        self.explosion_timer = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 87

    @property
    def name(self) -> str:
        return "怒之铁拳"

    @property
    def english_name(self) -> str:
        return "Streets of Rage"

    @property
    def release_year(self) -> int:
        return 1991

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "背后德式拱桥摔破防 + 呼叫警车火箭筒全屏火力支援"

    def get_name(self) -> str:
        return "Streets of Rage (1991)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_STREET_BRAWL
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.hero_hp = 100
        self.backup_calls = 1
        self.thugs_defeated = 0
        self.reset_stage()

    def reset_stage(self):
        self.px = 3.5
        self.py = 10.5
        self.facing = 1
        self.atk_state = ATK_NONE
        self.atk_timer = 0.0

        self.thugs = [
            {"x": 13.0 + i * 3.5, "y": 8.5 + (i * 2.0), "vx": -2.2, "hp": 3, "is_boss": False, "respawn_timer": 0.0, "active": True}
            for i in range(MAX_THUGS)
        ]

        self.rocket_x = 0.0
        self.rocket_y = 14.0
        self.explosion_timer = 0.0

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_HERO_DEAD, STATE_STAGE_CLEAR):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_POLICE_BACKUP:
            self.update_police_backup(dt)
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_thugs(dt)
        self.check_combat()

        if self.thugs_defeated >= 7:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 10000

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 5.0

        if self.atk_timer > 0.0:
            self.atk_timer -= dt
            if self.atk_timer <= 0.0:
                self.atk_state = ATK_NONE
            return

        # Call Police Backup (A + B)
        if (buttons & KEY_A) and (buttons & KEY_B) and (not (prev_buttons & KEY_A) or not (prev_buttons & KEY_B)):
            if self.backup_calls > 0:
                self.backup_calls -= 1
                self.state = STATE_POLICE_BACKUP
                self.state_timer = 0.0
                self.rocket_x = 1.0
                self.rocket_y = 13.0
                self.explosion_timer = 0.0
                return

        # Flying Jump Kick (B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.atk_state = ATK_FLYING_KICK
            self.atk_timer = 0.35
            self.px += self.facing * 1.5
            return

        # Punch or Suplex (A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            suplexed = False
            for t in self.thugs:
                if not t["active"]:
                    continue
                dx = (t["x"] - self.px) * self.facing
                dy = abs(t["y"] - self.py)

                if 0.0 < dx < 0.9 and dy < 0.8:
                    self.atk_state = ATK_SUPLEX
                    self.atk_timer = 0.45
                    t["hp"] -= 3
                    t["x"] -= self.facing * 3.0
                    self.score += 600
                    suplexed = True
                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
                    break

            if not suplexed:
                self.atk_state = ATK_PUNCH
                self.atk_timer = 0.22
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

        self.px = max(1.0, min(14.5, self.px))
        self.py = max(7.5, min(13.5, self.py))

    def update_thugs(self, dt: float):
        for i, t in enumerate(self.thugs):
            if not t["active"]:
                if t.get("respawn_timer", 0.0) > 0.0:
                    t["respawn_timer"] -= dt
                    if t["respawn_timer"] <= 0.0:
                        if self.thugs_defeated + i < 6:
                            t["active"] = True
                            t["x"] = 15.5
                            t["y"] = 8.0 + (i * 2.0)
                            t["hp"] = 3
                            t["is_boss"] = False
                        elif self.thugs_defeated >= 5 and not self.thugs[0].get("is_boss", False):
                            t["active"] = True
                            t["x"] = 15.0
                            t["y"] = 10.0
                            t["hp"] = 8
                            t["is_boss"] = True
                continue

            if t["x"] > self.px + 1.2:
                t["x"] -= 2.2 * dt
            elif t["x"] < self.px - 1.2:
                t["x"] += 2.2 * dt

            if t["y"] > self.py + 0.3:
                t["y"] -= 1.2 * dt
            elif t["y"] < self.py - 0.3:
                t["y"] += 1.2 * dt

    def check_combat(self):
        if self.atk_state in (ATK_PUNCH, ATK_FLYING_KICK):
            reach = 2.2 if self.atk_state == ATK_FLYING_KICK else 1.6
            dmg = 2 if self.atk_state == ATK_FLYING_KICK else 1

            for t in self.thugs:
                if not t["active"]:
                    continue
                dx = (t["x"] - self.px) * self.facing
                dy = abs(t["y"] - self.py)

                if 0.0 < dx < reach and dy < 1.2:
                    t["hp"] -= dmg
                    t["x"] += self.facing * 1.5
                    self.score += 200

                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
                        self.score += 5000 if t.get("is_boss", False) else 300

        for t in self.thugs:
            if not t["active"]:
                continue
            if abs(t["x"] - self.px) < 1.2 and abs(t["y"] - self.py) < 1.0:
                self.hero_hp -= 2 if t.get("is_boss", False) else 1
                if self.hero_hp <= 0:
                    self.lives -= 1
                    if self.lives > 0:
                        self.hero_hp = 100
                        self.px = 3.5
                        self.py = 10.5
                    else:
                        self.state = STATE_HERO_DEAD
                        self.state_timer = 0.0
                    return

    def update_police_backup(self, dt: float):
        if self.explosion_timer == 0.0:
            self.rocket_x += 16.0 * dt
            self.rocket_y -= 6.0 * dt

            if self.rocket_x >= 8.0:
                self.explosion_timer = 1.2
                for t in self.thugs:
                    if not t["active"]:
                        continue
                    t["hp"] -= 6
                    if t["hp"] <= 0:
                        t["active"] = False
                        t["respawn_timer"] = 2.0
                        self.thugs_defeated += 1
                        self.score += 5000 if t.get("is_boss", False) else 400
        else:
            self.explosion_timer -= dt
            if self.explosion_timer <= 0.0:
                self.state = STATE_STREET_BRAWL
                self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Skyline
        for y in range(7):
            for x in range(16):
                set_pixel(x, y, 10, 15, 30)
        set_pixel(3, 2, 255, 30, 120)
        set_pixel(4, 2, 255, 30, 120)
        set_pixel(12, 3, 30, 220, 255)

        # 2. Street
        for y in range(7, 15):
            for x in range(16):
                set_pixel(x, y, 35, 35, 40)

        # 3. Police Rocket & Explosion
        if self.state == STATE_POLICE_BACKUP:
            if self.explosion_timer > 0.0:
                for y in range(5, 15):
                    for x in range(16):
                        if (x + y) % 2 == 0:
                            set_pixel(x, y, 255, 140, 20)
                        else:
                            set_pixel(x, y, 255, 40, 20)
            else:
                set_pixel(0, 14, 240, 240, 250)
                set_pixel(1, 14, 20, 20, 20)
                set_pixel(0, 13, 255, 20, 20)
                rx = int(round(self.rocket_x))
                ry = int(round(self.rocket_y))
                set_pixel(rx, ry, 255, 255, 100)
                set_pixel(rx - 1, ry + 1, 255, 120, 0)

        # 4. Thugs
        for t in self.thugs:
            if not t["active"]:
                continue
            ex = int(round(t["x"]))
            ey = int(round(t["y"]))
            if t.get("is_boss", False):
                set_pixel(ex, ey, 220, 30, 40)
                set_pixel(ex, ey - 1, 240, 180, 140)
                set_pixel(ex - 1, ey - 1, 220, 220, 255)
            else:
                set_pixel(ex, ey, 200, 160, 40)
                set_pixel(ex, ey - 1, 240, 180, 140)
                set_pixel(ex, ey - 2, 40, 40, 40)

        # 5. Axel Stone
        px = int(round(self.px))
        py = int(round(self.py))
        set_pixel(px, py, 40, 100, 220)
        set_pixel(px, py - 1, 250, 250, 250)
        set_pixel(px, py - 2, 240, 180, 140)
        set_pixel(px, py - 3, 255, 30, 30)

        if self.atk_state == ATK_PUNCH:
            set_pixel(px + self.facing, py - 1, 255, 200, 120)
        elif self.atk_state == ATK_FLYING_KICK:
            set_pixel(px + self.facing * 2, py - 1, 40, 100, 220)
        elif self.atk_state == ATK_SUPLEX:
            set_pixel(px - self.facing, py - 1, 255, 140, 40)

        # 6. HUD
        hp_bars = max(0, min(8, self.hero_hp // 12))
        for b in range(hp_bars):
            set_pixel(b, 15, 50, 220, 50)
        if self.backup_calls > 0:
            set_pixel(15, 15, 255, 200, 0)
            set_pixel(14, 15, 20, 100, 255)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "hero_hp": self.hero_hp,
            "lives": self.lives,
            "backup_calls": self.backup_calls,
            "thugs_defeated": self.thugs_defeated,
            "atk_state": self.atk_state,
            "px": self.px,
            "py": self.py,
        }
