"""
Game #092: 战国之刃 / 战国传承飞天巫女 (Sengoku Blade / Tengai 1996 / Psikyo)
Horizontal flying shooter, close-range melee katana slashes erasing bullets, shikigami charge blasts & mandala bomb.
"""

from typing import List, Dict, Any
import math
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

STATE_AIR_BATTLE = 0
STATE_HERO_HIT = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3

MAX_HERO_BULLETS = 6
MAX_ENEMY_BULLETS = 8
MAX_ENEMIES = 3


class Game092SengokuBlade(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_AIR_BATTLE
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.bombs = 2
        self.stage = 1
        self.enemies_defeated = 0

        # Flying Miko Hero
        self.px = 2.0
        self.py = 8.0
        self.charge_timer = 0.0
        self.is_charging = False
        self.melee_timer = 0.0
        self.bomb_timer = 0.0
        self.fire_cooldown = 0.0
        self.cloud_scroll = 0.0

        self.hero_bullets: List[Dict[str, Any]] = []
        self.enemy_bullets: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 92

    @property
    def name(self) -> str:
        return "战国之刃"

    @property
    def english_name(self) -> str:
        return "Sengoku Blade"

    @property
    def release_year(self) -> int:
        return 1996

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "横版贴脸拔刀斩消弹、式神蓄力喷射与忍法曼荼罗"

    def get_name(self) -> str:
        return "Sengoku Blade (1996)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.bombs = 2
        self.stage = 1
        self._reset_battle(hard_reset=True)

    def _reset_battle(self, hard_reset: bool = False) -> None:
        self.state = STATE_AIR_BATTLE
        self.state_timer = 0.0
        self.enemies_defeated = 0

        self.px = 2.0
        self.py = 8.0
        self.charge_timer = 0.0
        self.is_charging = False
        self.melee_timer = 0.0
        self.bomb_timer = 0.0
        self.fire_cooldown = 0.0
        self.cloud_scroll = 0.0

        self.hero_bullets = [
            {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "is_charge_shot": False, "active": False}
            for _ in range(MAX_HERO_BULLETS)
        ]

        self.enemy_bullets = [
            {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "active": False}
            for _ in range(MAX_ENEMY_BULLETS)
        ]

        self.enemies = []
        for i in range(MAX_ENEMIES):
            self.enemies.append({
                "x": 12.0 + i * 1.5,
                "y": 4.0 + i * 4.0,
                "vy": 1.5 if (i % 2 == 0) else -1.5,
                "hp": 4 if (i == 0) else 2,
                "is_boss": (i == 0),
                "shoot_timer": 0.8 + i * 0.6,
                "respawn_timer": 0.0,
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt
        self.cloud_scroll += 2.0 * dt
        if self.cloud_scroll >= 16.0:
            self.cloud_scroll -= 16.0

        if self.state == STATE_HERO_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_battle(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.stage += 1
                self._reset_battle(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_hero_projectiles(dt)
        self._update_enemies(dt)
        self._update_enemy_bullets(dt)
        self._check_combat()

        if self.enemies_defeated >= 6:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1500

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt
        if self.melee_timer > 0.0:
            self.melee_timer -= dt

        if self.bomb_timer > 0.0:
            self.bomb_timer -= dt

        # 8-Way Flight
        flight_speed = 6.5
        if buttons & KEY_LEFT:
            self.px -= flight_speed * dt
        if buttons & KEY_RIGHT:
            self.px += flight_speed * dt
        if buttons & KEY_UP:
            self.py -= flight_speed * dt
        if buttons & KEY_DOWN:
            self.py += flight_speed * dt

        self.px = max(1.0, min(14.5, self.px))
        self.py = max(1.5, min(14.5, self.py))

        # Button B: Mandala Bomb
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.bombs > 0 and self.bomb_timer <= 0.0:
                self.bombs -= 1
                self.bomb_timer = 1.2
                self.score += 50

                for eb in self.enemy_bullets:
                    if eb["active"]:
                        eb["active"] = False
                        self.score += 100

                for e in self.enemies:
                    if e["active"]:
                        e["hp"] -= 3
                        if e["hp"] <= 0:
                            e["active"] = False
                            e["respawn_timer"] = 2.0
                            self.score += 300
                            self.enemies_defeated += 1

        # Button A: Hold for charge, release for blast / melee
        if buttons & KEY_A:
            self.charge_timer += dt
            self.is_charging = True
        else:
            if self.is_charging:
                if self.charge_timer >= 0.75:
                    # Shikigami Charge Blast
                    for b in self.hero_bullets:
                        if not b["active"]:
                            b["active"] = True
                            b["is_charge_shot"] = True
                            b["x"] = self.px + 1.2
                            b["y"] = self.py
                            b["vx"] = 14.0
                            b["vy"] = 0.0
                            self.score += 20
                            break
                elif self.fire_cooldown <= 0.0:
                    # Short tap: check close-range melee
                    nearby_enemy = False
                    for e in self.enemies:
                        if e["active"]:
                            dx = e["x"] - self.px
                            dy = abs(e["y"] - self.py)
                            if 0.0 < dx < 2.5 and dy < 1.4:
                                nearby_enemy = True
                                break

                    if nearby_enemy:
                        self.melee_timer = 0.22
                        self.fire_cooldown = 0.25
                        self.score += 30
                        # Erase adjacent enemy bullets
                        for eb in self.enemy_bullets:
                            if eb["active"]:
                                bdx = eb["x"] - self.px
                                bdy = abs(eb["y"] - self.py)
                                if 0.0 < bdx < 2.5 and bdy < 1.5:
                                    eb["active"] = False
                                    self.score += 50
                    else:
                        for b in self.hero_bullets:
                            if not b["active"]:
                                b["active"] = True
                                b["is_charge_shot"] = False
                                b["x"] = self.px + 0.8
                                b["y"] = self.py
                                b["vx"] = 12.0
                                b["vy"] = 0.0
                                self.fire_cooldown = 0.18
                                break

                self.charge_timer = 0.0
                self.is_charging = False

    def _update_hero_projectiles(self, dt: float) -> None:
        for b in self.hero_bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] > 17.0 or b["x"] < -1.0 or b["y"] < -1.0 or b["y"] > 17.0:
                b["active"] = False

    def _update_enemies(self, dt: float) -> None:
        for idx, e in enumerate(self.enemies):
            if not e["active"]:
                if e["respawn_timer"] > 0.0:
                    e["respawn_timer"] -= dt
                else:
                    e["active"] = True
                    e["hp"] = 4 if idx == 0 else 2
                    e["x"] = 13.0 + (idx * 0.7) % 2.0
                    e["y"] = 3.0 + (idx * 3.5) % 9.0
                    e["vy"] = 1.5 if idx % 2 == 0 else -1.5
                    e["shoot_timer"] = 1.0 + (idx * 0.3)
                continue

            e["y"] += e["vy"] * dt
            if e["y"] <= 2.5:
                e["y"] = 2.5
                e["vy"] = abs(e["vy"])
            elif e["y"] >= 13.5:
                e["y"] = 13.5
                e["vy"] = -abs(e["vy"])

            e["shoot_timer"] -= dt
            if e["shoot_timer"] <= 0.0:
                e["shoot_timer"] = 1.4 + (idx * 0.2)
                for eb in self.enemy_bullets:
                    if not eb["active"]:
                        eb["active"] = True
                        eb["x"] = e["x"] - 0.8
                        eb["y"] = e["y"]
                        eb["vx"] = -6.0
                        eb["vy"] = 0.0
                        break

    def _update_enemy_bullets(self, dt: float) -> None:
        for eb in self.enemy_bullets:
            if not eb["active"]:
                continue
            eb["x"] += eb["vx"] * dt
            eb["y"] += eb["vy"] * dt
            if eb["x"] < -1.0 or eb["x"] > 17.0 or eb["y"] < -1.0 or eb["y"] > 17.0:
                eb["active"] = False

    def _check_combat(self) -> None:
        # Melee slash
        if self.melee_timer > 0.0:
            for e in self.enemies:
                if not e["active"]:
                    continue
                dx = e["x"] - self.px
                dy = abs(e["y"] - self.py)
                if 0.0 < dx < 2.5 and dy < 1.4:
                    e["hp"] -= 3
                    self.score += 150
                    if e["hp"] <= 0:
                        e["active"] = False
                        e["respawn_timer"] = 2.0
                        self.enemies_defeated += 1

        # Hero Bullets
        for b in self.hero_bullets:
            if not b["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                dx = abs(b["x"] - e["x"])
                dy = abs(b["y"] - e["y"])
                if dx < 1.2 and dy < 1.2:
                    dmg = 4 if b["is_charge_shot"] else 1
                    e["hp"] -= dmg
                    self.score += 200 if b["is_charge_shot"] else 50
                    if not b["is_charge_shot"]:
                        b["active"] = False
                    if e["hp"] <= 0:
                        e["active"] = False
                        e["respawn_timer"] = 2.0
                        self.enemies_defeated += 1
                    break

        # Enemy Bullets vs Hero
        if self.bomb_timer <= 0.0:
            for eb in self.enemy_bullets:
                if not eb["active"]:
                    continue
                dx = abs(eb["x"] - self.px)
                dy = abs(eb["y"] - self.py)
                if dx < 0.9 and dy < 0.9:
                    eb["active"] = False
                    self.state = STATE_HERO_HIT
                    self.state_timer = 0.0
                    return

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(len(fb)):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # Twilight sky
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 40 + y * 4, 20 + y * 2, 70 + y * 3)

        # Clouds
        cloud_offset = int(self.cloud_scroll)
        for i in range(4):
            cx = (cloud_offset + i * 5) % 16
            cy = 3 + i * 3
            set_pixel(cx, cy, 120, 80, 150)
            set_pixel(cx + 1, cy, 120, 80, 150)

        # Mandala bomb effect
        if self.bomb_timer > 0.0:
            for y in range(16):
                for x in range(16):
                    if (x + y) % 3 == 0:
                        set_pixel(x, y, 255, 220, 50)

        # Karakuri Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["is_boss"]:
                set_pixel(ex, ey, 140, 110, 80)
                set_pixel(ex + 1, ey, 140, 110, 80)
                set_pixel(ex, ey - 1, 240, 30, 30)
                set_pixel(ex + 1, ey - 1, 140, 110, 80)
            else:
                set_pixel(ex, ey, 200, 50, 40)
                set_pixel(ex, ey - 1, 240, 220, 180)
                set_pixel(ex + 1, ey, 100, 30, 20)

        # Hero Bullets
        for b in self.hero_bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["is_charge_shot"]:
                set_pixel(bx, by, 255, 230, 40)
                set_pixel(bx + 1, by, 255, 255, 180)
                set_pixel(bx, by - 1, 255, 200, 0)
                set_pixel(bx + 1, by - 1, 255, 240, 100)
            else:
                set_pixel(bx, by, 255, 255, 255)
                set_pixel(bx + 1, by, 240, 60, 60)

        # Enemy Bullets
        for eb in self.enemy_bullets:
            if not eb["active"]:
                continue
            bx = int(round(eb["x"]))
            by = int(round(eb["y"]))
            set_pixel(bx, by, 255, 40, 180)

        # Flying Miko Hero
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_HERO_HIT:
            set_pixel(px, py, 255, 50, 0)
            set_pixel(px, py - 1, 255, 200, 0)
        else:
            set_pixel(px, py, 220, 40, 40)
            set_pixel(px, py - 1, 255, 255, 255)
            set_pixel(px, py - 2, 240, 190, 140)
            set_pixel(px - 1, py - 2, 40, 40, 40)

            if self.melee_timer > 0.0:
                set_pixel(px + 1, py - 2, 220, 240, 255)
                set_pixel(px + 2, py - 1, 255, 255, 255)
                set_pixel(px + 1, py, 200, 230, 255)

            if self.is_charging and self.charge_timer >= 0.75:
                set_pixel(px - 1, py - 1, 255, 220, 0)
                set_pixel(px, py - 3, 255, 240, 100)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 60, 60)
        for b in range(min(self.bombs, 3)):
            set_pixel(15 - b, 0, 255, 215, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "bombs": self.bombs,
            "stage": self.stage,
            "charge_timer": self.charge_timer,
            "is_charging": self.is_charging,
            "melee_active": self.melee_timer > 0.0,
            "bomb_active": self.bomb_timer > 0.0,
            "enemies_defeated": self.enemies_defeated,
            "player_x": self.px,
            "player_y": self.py,
        }
