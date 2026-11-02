"""
Game #080: 恐龙快打 / 恐龙新世纪 (Cadillacs and Dinosaurs 1993 / Capcom)
Beat 'em up Masterpiece, Weapon Pickups (Uzis/Bazookas), Neutral/Enraged Dinosaur Ecology & Cadillac Turbo Drive.
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
STATE_CADILLAC_DRIVE = 1
STATE_PLAYER_DEAD = 2
STATE_VICTORY = 3

WEAPON_FIST = 0
WEAPON_UZI = 1
WEAPON_SHOTGUN = 2
WEAPON_BAZOOKA = 3

MAX_ENEMIES = 3
MAX_BULLETS = 6
MAX_DROPS = 2


class Game080Cadillacs(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 15000
        self.lives = 3
        self.player_hp = 100
        self.enemies_defeated = 0

        # Player
        self.px = 3.0
        self.py = 10.0
        self.facing = 1
        self.in_air = False
        self.pvy = 0.0
        self.atk_timer = 0.0

        # Weapons
        self.current_weapon = WEAPON_FIST
        self.weapon_ammo = 0

        # Dinosaur
        self.dino = {
            "x": 12.0,
            "y": 10.0,
            "vx": -1.2,
            "enraged": False,
            "calm_timer": 0.0,
            "hp": 4,
            "active": True,
        }

        self.enemies: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []
        self.drops: List[Dict[str, Any]] = []

        self.caddy_x = -8.0
        self.caddy_speed = 20.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 80

    @property
    def name(self) -> str:
        return "恐龙快打"

    @property
    def english_name(self) -> str:
        return "Cadillacs and Dinosaurs"

    @property
    def release_year(self) -> int:
        return 1993

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "枪械捡拾射击与中立恐龙狂暴驯服 + 凯迪拉克飞车冲撞清版"

    def get_name(self) -> str:
        return "Cadillacs and Dinosaurs (1993)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_hp = 100
        self.enemies_defeated = 0
        self.current_weapon = WEAPON_FIST
        self.weapon_ammo = 0
        self.reset_stage()

    def reset_stage(self):
        self.px = 3.0
        self.py = 10.0
        self.facing = 1
        self.in_air = False
        self.pvy = 0.0
        self.atk_timer = 0.0

        self.dino = {
            "x": 12.0,
            "y": 10.0,
            "vx": -1.2,
            "enraged": False,
            "calm_timer": 0.0,
            "hp": 4,
            "active": True,
        }

        self.enemies = [
            {"x": 14.0 + i * 4.0, "y": 8.0 + (i * 2.0), "vx": -2.2, "hp": 2, "active": True, "respawn_timer": 0.0}
            for i in range(MAX_ENEMIES)
        ]

        self.bullets = []
        self.drops = [
            {"x": 7.0, "y": 11.0, "type": WEAPON_UZI, "ammo": 15, "active": True},
            {"x": 0.0, "y": 0.0, "type": WEAPON_BAZOOKA, "ammo": 4, "active": False},
        ]

        self.caddy_x = -8.0

    def trigger_cadillac_raid(self):
        self.state = STATE_CADILLAC_DRIVE
        self.state_timer = 0.0
        self.caddy_x = -6.0
        self.score += 3000

    def fire_weapon(self):
        if len([b for b in self.bullets if b["active"]]) < MAX_BULLETS:
            self.bullets.append({
                "x": self.px + (self.facing * 1.0),
                "y": self.py,
                "vx": self.facing * 20.0,
                "is_bazooka": (self.current_weapon == WEAPON_BAZOOKA),
                "active": True,
            })
            self.weapon_ammo -= 1
            if self.weapon_ammo <= 0:
                self.current_weapon = WEAPON_FIST

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state in (STATE_PLAYER_DEAD, STATE_VICTORY):
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_CADILLAC_DRIVE:
            self.caddy_x += self.caddy_speed * dt
            self.px = self.caddy_x

            for e in self.enemies:
                if e["active"] and abs(e["x"] - self.caddy_x) < 2.5:
                    e["active"] = False
                    self.score += 500
                    self.enemies_defeated += 1

            if self.dino["active"] and abs(self.dino["x"] - self.caddy_x) < 3.0:
                self.dino["active"] = False
                self.score += 2000

            if self.caddy_x > 20.0:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 5000
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.update_dino(dt)
        self.update_bullets(dt)
        self.check_collisions()

        if self.enemies_defeated >= 8 and self.state == STATE_PLAYING:
            self.trigger_cadillac_raid()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 5.0

        # Whirlwind Kick (A + B)
        if (buttons & KEY_A) and (buttons & KEY_B) and (not (prev_buttons & KEY_A) or not (prev_buttons & KEY_B)):
            if self.player_hp > 15:
                self.player_hp -= 10
                self.atk_timer = 0.35
                for e in self.enemies:
                    if e["active"] and abs(e["x"] - self.px) < 2.8 and abs(e["y"] - self.py) < 2.0:
                        e["hp"] -= 2
                        if e["hp"] <= 0:
                            e["active"] = False
                            e["respawn_timer"] = 2.0
                            self.enemies_defeated += 1
                            self.score += 300

                if self.dino["active"] and abs(self.dino["x"] - self.px) < 3.0 and abs(self.dino["y"] - self.py) < 2.0:
                    self.dino["enraged"] = False
                return

        if self.in_air:
            self.pvy += 22.0 * dt
            self.py += self.pvy * dt
            if self.py >= 10.0:
                self.py = 10.0
                self.pvy = 0.0
                self.in_air = False
        else:
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
            self.py = max(7.0, min(13.5, self.py))

            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.in_air = True
                self.pvy = -8.5

        if self.atk_timer > 0.0:
            self.atk_timer -= dt

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.atk_timer = 0.22
            if self.current_weapon != WEAPON_FIST and self.weapon_ammo > 0:
                self.fire_weapon()
            else:
                picked = False
                for d in self.drops:
                    if d["active"] and abs(d["x"] - self.px) < 1.6 and abs(d["y"] - self.py) < 1.6:
                        self.current_weapon = d["type"]
                        self.weapon_ammo = d["ammo"]
                        d["active"] = False
                        picked = True
                        self.score += 200
                        break

                if not picked:
                    for e in self.enemies:
                        if e["active"] and abs(e["x"] - self.px) < 2.0 and abs(e["y"] - self.py) < 1.4:
                            e["hp"] -= 1
                            if e["hp"] <= 0:
                                e["active"] = False
                                e["respawn_timer"] = 2.0
                                self.enemies_defeated += 1
                                self.score += 300
                                if not self.drops[1]["active"]:
                                    self.drops[1]["active"] = True
                                    self.drops[1]["x"] = e["x"]
                                    self.drops[1]["y"] = e["y"]
                                    self.drops[1]["type"] = WEAPON_BAZOOKA
                                    self.drops[1]["ammo"] = 4

                    if self.dino["active"] and abs(self.dino["x"] - self.px) < 2.2 and abs(self.dino["y"] - self.py) < 1.5:
                        if not self.dino["enraged"]:
                            self.dino["enraged"] = True
                            self.dino["vx"] = self.facing * 3.5
                        else:
                            self.dino["hp"] -= 1
                            if self.dino["hp"] <= 1:
                                self.dino["enraged"] = False
                                self.dino["hp"] = 4
                                self.score += 1000

    def update_enemies(self, dt: float):
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                if e.get("respawn_timer", 0.0) > 0.0:
                    e["respawn_timer"] -= dt
                    if e["respawn_timer"] <= 0.0 and self.enemies_defeated + i < 8:
                        e["active"] = True
                        e["x"] = 15.5
                        e["y"] = 8.0 + (i * 2.0)
                        e["hp"] = 2
                continue

            if e["x"] > self.px + 1.2:
                e["x"] -= 2.5 * dt
            elif e["x"] < self.px - 1.2:
                e["x"] += 2.5 * dt

            if e["y"] > self.py + 0.4:
                e["y"] -= 1.5 * dt
            elif e["y"] < self.py - 0.4:
                e["y"] += 1.5 * dt

    def update_dino(self, dt: float):
        if not self.dino["active"]:
            return

        if self.dino["enraged"]:
            self.dino["x"] += self.dino["vx"] * dt
            if self.dino["x"] < 1.0:
                self.dino["x"] = 1.0
                self.dino["vx"] = 4.0
            elif self.dino["x"] > 14.5:
                self.dino["x"] = 14.5
                self.dino["vx"] = -4.0

            for e in self.enemies:
                if e["active"] and abs(e["x"] - self.dino["x"]) < 2.0 and abs(e["y"] - self.dino["y"]) < 1.5:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 400
        else:
            self.dino["x"] += self.dino["vx"] * dt
            if self.dino["x"] < 6.0:
                self.dino["vx"] = 1.0
            elif self.dino["x"] > 14.0:
                self.dino["vx"] = -1.0

    def update_bullets(self, dt: float):
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            if b["x"] < 0.0 or b["x"] > 15.5:
                b["active"] = False

        self.bullets = [b for b in self.bullets if b["active"]]

    def check_collisions(self):
        for b in self.bullets:
            if not b["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(b["x"] - e["x"]) < 1.5 and abs(b["y"] - e["y"]) < 1.4:
                    b["active"] = False
                    dmg = 3 if b["is_bazooka"] else 1
                    e["hp"] -= dmg
                    if e["hp"] <= 0:
                        e["active"] = False
                        self.enemies_defeated += 1
                        self.score += 350
                    break

            if b["active"] and self.dino["active"]:
                if abs(b["x"] - self.dino["x"]) < 1.8 and abs(b["y"] - self.dino["y"]) < 1.6:
                    b["active"] = False
                    self.dino["enraged"] = True
                    self.score += 100

        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(e["x"] - self.px) < 1.2 and abs(e["y"] - self.py) < 1.0:
                self.player_hp -= 1
                if self.player_hp <= 0:
                    self.lives -= 1
                    if self.lives > 0:
                        self.player_hp = 100
                        self.px = 3.0
                        self.py = 10.0
                    else:
                        self.state = STATE_PLAYER_DEAD
                        self.state_timer = 0.0
                    return

        if self.dino["active"] and self.dino["enraged"]:
            if abs(self.dino["x"] - self.px) < 1.6 and abs(self.dino["y"] - self.py) < 1.2:
                self.player_hp -= 2
                if self.player_hp <= 0:
                    self.lives -= 1
                    if self.lives > 0:
                        self.player_hp = 100
                        self.px = 3.0
                        self.py = 10.0
                    else:
                        self.state = STATE_PLAYER_DEAD
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

        # 1. Sky & Ruin
        for y in range(7):
            for x in range(16):
                set_pixel(x, y, 20, 45, 25)

        # 2. Highway
        for y in range(7, 15):
            for x in range(16):
                set_pixel(x, y, 70, 60, 45)

        # 3. Cadillac
        if self.state == STATE_CADILLAC_DRIVE:
            cx = int(round(self.caddy_x))
            cy = 10
            for dx in range(-2, 3):
                set_pixel(cx + dx, cy, 255, 40, 40)
                set_pixel(cx + dx, cy - 1, 255, 220, 0)
            set_pixel(cx + 3, cy, 255, 255, 200)

        # 4. Drops
        for d in self.drops:
            if not d["active"]:
                continue
            dx = int(round(d["x"]))
            dy = int(round(d["y"]))
            if d["type"] == WEAPON_UZI:
                set_pixel(dx, dy, 50, 150, 255)
            else:
                set_pixel(dx, dy, 255, 120, 0)

        # 5. Dino
        if self.dino["active"]:
            dx = int(round(self.dino["x"]))
            dy = int(round(self.dino["y"]))
            if self.dino["enraged"]:
                set_pixel(dx, dy, 255, 30, 30)
                set_pixel(dx, dy - 1, 255, 80, 0)
                set_pixel(dx + 1, dy, 255, 180, 0)
            else:
                set_pixel(dx, dy, 30, 200, 50)
                set_pixel(dx, dy - 1, 60, 240, 80)
                set_pixel(dx + 1, dy, 20, 160, 40)

        # 6. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            set_pixel(ex, ey, 180, 40, 200)
            set_pixel(ex, ey - 1, 240, 180, 140)

        # 7. Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["is_bazooka"]:
                set_pixel(bx, by, 255, 200, 0)
                set_pixel(bx - 1, by, 255, 80, 0)
            else:
                set_pixel(bx, by, 255, 255, 100)

        # 8. Player
        if self.state != STATE_CADILLAC_DRIVE:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px, py, 40, 100, 220)
            set_pixel(px, py - 1, 255, 240, 200)
            set_pixel(px, py - 2, 255, 220, 0)
            if self.atk_timer > 0.0:
                set_pixel(px + self.facing, py - 1, 255, 200, 50)

        # 9. Health & Ammo HUD
        hp_bars = max(0, min(8, self.player_hp // 12))
        for b in range(hp_bars):
            set_pixel(b, 15, 50, 220, 50)
        if self.current_weapon != WEAPON_FIST:
            for a in range(min(6, self.weapon_ammo)):
                set_pixel(15 - a, 15, 255, 200, 0)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "player_hp": self.player_hp,
            "enemies_defeated": self.enemies_defeated,
            "px": self.px,
            "py": self.py,
            "current_weapon": self.current_weapon,
            "weapon_ammo": self.weapon_ammo,
            "dino_enraged": self.dino["enraged"],
        }
