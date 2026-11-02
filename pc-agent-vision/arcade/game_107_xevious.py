"""
Game #107: 铁板阵 (Xevious 1982 / Namco)
Dual-plane targeting: Air-to-Air Zapper cannon vs flying Toroid rings,
Ground-Targeting Crosshair Blaster Bombing vs Barra/Zolbak/hidden Sol citadels,
and the legendary Andor Genesis floating mothership showdown.
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

STATE_FLYING = 0
STATE_BOSS_ANDOR = 1
STATE_SHIP_EXPLODED = 2
STATE_AREA_CLEAR = 3
STATE_GAME_OVER = 4

MAX_PLAYER_BULLETS = 3
MAX_ENEMY_BULLETS = 3
MAX_GROUND_BOMBS = 2
MAX_AIR_ENEMIES = 3
MAX_GROUND_TARGETS = 4


class Game107Xevious(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.area = 1
        self.scroll_y = 0.0
        self.enemies_downed = 0

        self.px = 8.0
        self.py = 13.0
        self.zapper_cooldown = 0.0
        self.blaster_cooldown = 0.0

        self.andor_x = 5.0
        self.andor_y = 2.5
        self.andor_vx = 1.8
        self.andor_hp = 6

        self.player_bullets: List[Dict[str, Any]] = []
        self.enemy_bullets: List[Dict[str, Any]] = []
        self.ground_bombs: List[Dict[str, Any]] = []
        self.air_enemies: List[Dict[str, Any]] = []
        self.ground_targets: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 107

    @property
    def name(self) -> str:
        return "铁板阵"

    @property
    def english_name(self) -> str:
        return "Xevious"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "对空直线激光与对地准星俯冲轰炸双层分立打击、隐藏地脉巨石发掘与母舰安多要塞决战"

    def get_name(self) -> str:
        return "Xevious (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.area = 1
        self._init_area()

    def _init_area(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.scroll_y = 0.0
        self.enemies_downed = 0

        self.px = 8.0
        self.py = 13.0
        self.zapper_cooldown = 0.0
        self.blaster_cooldown = 0.0

        self.player_bullets = [
            {"x": 0.0, "y": 0.0, "vy": -18.0, "active": False}
            for _ in range(MAX_PLAYER_BULLETS)
        ]
        self.enemy_bullets = [
            {"x": 0.0, "y": 0.0, "vy": 6.0, "active": False}
            for _ in range(MAX_ENEMY_BULLETS)
        ]
        self.ground_bombs = [
            {"x": 0.0, "y": 0.0, "target_x": 0.0, "target_y": 0.0, "timer": 0.0, "active": False}
            for _ in range(MAX_GROUND_BOMBS)
        ]

        self.air_enemies = []
        for i in range(MAX_AIR_ENEMIES):
            self.air_enemies.append({
                "x": 3.0 + float(i * 4.5),
                "y": -2.0 - float(i * 3.0),
                "vx": 1.5 if (i % 2 == 0) else -1.5,
                "vy": 3.2,
                "type": i % 2,
                "active": True,
            })

        self.ground_targets = []
        for i in range(MAX_GROUND_TARGETS):
            self.ground_targets.append({
                "x": 4.0 + float((i * 3) % 8),
                "y": 2.0 + float(i * 3.5),
                "type": 2 if (i == 3) else (i % 2),
                "hp": 1,
                "active": True,
            })

    def spawn_andor_genesis(self) -> None:
        self.state = STATE_BOSS_ANDOR
        self.state_timer = 0.0
        self.andor_x = 5.0
        self.andor_y = 2.5
        self.andor_vx = 1.8
        self.andor_hp = 6

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_SHIP_EXPLODED:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_FLYING
                    self.state_timer = 0.0
                    self.px = 8.0
                    self.py = 13.0
            return

        if self.state == STATE_AREA_CLEAR:
            if self.state_timer > 2.2:
                self.area += 1
                self._init_area()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.scroll_y += 3.0 * dt

        self._update_ship(dt, buttons, prev_buttons)
        self._update_air_entities(dt)
        self._update_ground_entities(dt)

        if self.state == STATE_BOSS_ANDOR:
            self._update_andor_genesis(dt)
        else:
            if self.enemies_downed >= 6:
                self.spawn_andor_genesis()

        self._check_air_collisions()
        self._check_ground_bomb_collisions()

    def _update_ship(self, dt: float, buttons: int, prev_buttons: int) -> None:
        spd = 7.5
        if buttons & KEY_LEFT:
            self.px = max(1.0, self.px - spd * dt)
        if buttons & KEY_RIGHT:
            self.px = min(14.0, self.px + spd * dt)
        if buttons & KEY_UP:
            self.py = max(2.0, self.py - spd * dt)
        if buttons & KEY_DOWN:
            self.py = min(14.0, self.py + spd * dt)

        # Button A: Air Zapper
        self.zapper_cooldown -= dt
        if (buttons & KEY_A) and self.zapper_cooldown <= 0.0:
            self.zapper_cooldown = 0.2
            for b in self.player_bullets:
                if not b["active"]:
                    b["active"] = True
                    b["x"] = self.px
                    b["y"] = self.py - 1.2
                    b["vy"] = -18.0
                    break

        # Button B: Blaster Ground Bomb
        self.blaster_cooldown -= dt
        if (buttons & KEY_B) and not (prev_buttons & KEY_B) and self.blaster_cooldown <= 0.0:
            self.blaster_cooldown = 0.4
            for gb in self.ground_bombs:
                if not gb["active"]:
                    gb["active"] = True
                    gb["x"] = self.px
                    gb["y"] = self.py - 0.5
                    gb["target_x"] = self.px
                    gb["target_y"] = self.py - 3.5
                    gb["timer"] = 0.35
                    break

    def _update_air_entities(self, dt: float) -> None:
        for b in self.player_bullets:
            if not b["active"]:
                continue
            b["y"] += b["vy"] * dt
            if b["y"] < -1.0:
                b["active"] = False

        for b in self.enemy_bullets:
            if not b["active"]:
                continue
            b["y"] += b["vy"] * dt
            if b["y"] > 16.0:
                b["active"] = False

        for i, e in enumerate(self.air_enemies):
            if not e["active"]:
                e["active"] = True
                e["x"] = 2.0 + float((i * 5) % 12)
                e["y"] = -2.0
                e["vx"] = 2.0 if (i % 2 == 0) else -2.0
                e["vy"] = 3.5
                continue

            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["x"] < 1.0 or e["x"] > 14.0:
                e["vx"] = -e["vx"]

            if e["y"] > 17.0:
                e["active"] = False

    def _update_ground_entities(self, dt: float) -> None:
        for i, g in enumerate(self.ground_targets):
            if not g["active"]:
                g["active"] = True
                g["x"] = 3.0 + float((i * 4) % 10)
                g["y"] = -3.0
                g["type"] = 2 if (i == 3) else (i % 2)
                g["hp"] = 1
                continue

            g["y"] += 3.0 * dt
            if g["y"] > 17.0:
                g["active"] = False

        for b in self.ground_bombs:
            if not b["active"]:
                continue
            b["timer"] -= dt
            progress = 1.0 - max(0.0, b["timer"] / 0.35)
            b["y"] = b["target_y"] + (1.0 - progress) * 3.0

    def _update_andor_genesis(self, dt: float) -> None:
        self.andor_x += self.andor_vx * dt
        if self.andor_x <= 2.0:
            self.andor_x = 2.0
            self.andor_vx = abs(self.andor_vx)
        elif self.andor_x >= 8.0:
            self.andor_x = 8.0
            self.andor_vx = -abs(self.andor_vx)

    def _check_air_collisions(self) -> None:
        for b in self.player_bullets:
            if not b["active"]:
                continue
            for e in self.air_enemies:
                if not e["active"]:
                    continue
                dx = abs(b["x"] - e["x"])
                dy = abs(b["y"] - e["y"])
                if dx < 1.2 and dy < 1.2:
                    b["active"] = False
                    e["active"] = False
                    self.score += 100
                    self.enemies_downed += 1
                    break

            if self.state == STATE_BOSS_ANDOR and b["active"]:
                if self.andor_y - 0.5 <= b["y"] <= self.andor_y + 3.0:
                    if self.andor_x + 1.0 <= b["x"] <= self.andor_x + 4.0:
                        b["active"] = False
                        self.andor_hp -= 1
                        self.score += 200
                        if self.andor_hp <= 0:
                            self.state = STATE_AREA_CLEAR
                            self.state_timer = 0.0
                            self.score += 4000

        for b in self.enemy_bullets:
            if not b["active"]:
                continue
            if abs(self.px - b["x"]) < 0.9 and abs(self.py - b["y"]) < 0.9:
                b["active"] = False
                self.state = STATE_SHIP_EXPLODED
                self.state_timer = 0.0
                return

        for e in self.air_enemies:
            if not e["active"]:
                continue
            if abs(self.px - e["x"]) < 0.9 and abs(self.py - e["y"]) < 0.9:
                self.state = STATE_SHIP_EXPLODED
                self.state_timer = 0.0
                return

    def _check_ground_bomb_collisions(self) -> None:
        for b in self.ground_bombs:
            if not b["active"]:
                continue
            if b["timer"] <= 0.0:
                b["active"] = False
                bx = b["target_x"]
                by = b["target_y"]
                for g in self.ground_targets:
                    if not g["active"]:
                        continue
                    dx = abs(bx - g["x"])
                    dy = abs(by - g["y"])
                    if dx < 1.3 and dy < 1.3:
                        g["active"] = False
                        if g["type"] == 2:
                            self.score += 2000
                        elif g["type"] == 1:
                            self.score += 300
                        else:
                            self.score += 200
                        self.enemies_downed += 1

                if self.state == STATE_BOSS_ANDOR:
                    if (
                        abs(bx - (self.andor_x + 2.5)) < 1.8
                        and abs(by - (self.andor_y + 1.5)) < 1.8
                    ):
                        self.andor_hp -= 2
                        self.score += 500
                        if self.andor_hp <= 0:
                            self.state = STATE_AREA_CLEAR
                            self.state_timer = 0.0
                            self.score += 4000

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

        # Ground Terrain
        for y in range(16):
            for x in range(16):
                pat = (x + y + int(self.scroll_y)) % 6
                if pat == 0:
                    set_pixel(x, y, 40, 100, 30)
                elif pat == 3:
                    set_pixel(x, y, 120, 110, 70)
                else:
                    set_pixel(x, y, 60, 120, 45)

        # Ground Targets
        for g in self.ground_targets:
            if not g["active"]:
                continue
            gx = int(round(g["x"]))
            gy = int(round(g["y"]))
            if g["type"] == 0:
                set_pixel(gx, gy, 220, 50, 40)
                set_pixel(gx, gy - 1, 240, 100, 80)
            elif g["type"] == 1:
                set_pixel(gx, gy, 60, 140, 220)
                set_pixel(gx + 1, gy, 180, 220, 255)
            else:
                set_pixel(gx, gy, 255, 200, 0)
                set_pixel(gx, gy - 1, 255, 255, 120)
                set_pixel(gx, gy + 1, 200, 150, 0)

        # Ground Bombs
        for b in self.ground_bombs:
            if not b["active"]:
                continue
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 200)

        # Andor Genesis
        if self.state == STATE_BOSS_ANDOR:
            ax = int(round(self.andor_x))
            ay = int(round(self.andor_y))
            for y in range(ay, ay + 3):
                for x in range(ax, ax + 5):
                    set_pixel(x, y, 140, 140, 150)
            set_pixel(ax + 2, ay + 1, 255, 40, 20)

        # Air Enemies
        for e in self.air_enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            set_pixel(ex, ey, 220, 180, 40)
            set_pixel(ex - 1, ey, 180, 120, 20)
            set_pixel(ex + 1, ey, 180, 120, 20)

        # Bullets
        for b in self.player_bullets:
            if not b["active"]:
                continue
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 100)

        for b in self.enemy_bullets:
            if not b["active"]:
                continue
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 60, 40)

        # Ship & Crosshair
        px_i = int(round(self.px))
        py_i = int(round(self.py))
        cx = px_i
        cy = py_i - 4

        set_pixel(cx, cy, 255, 255, 0)
        set_pixel(cx - 1, cy, 180, 180, 0)
        set_pixel(cx + 1, cy, 180, 180, 0)

        if self.state == STATE_SHIP_EXPLODED:
            set_pixel(px_i, py_i, 255, 60, 20)
            set_pixel(px_i - 1, py_i, 255, 180, 0)
            set_pixel(px_i + 1, py_i, 255, 180, 0)
            set_pixel(px_i, py_i - 1, 255, 220, 0)
        else:
            set_pixel(px_i, py_i, 230, 230, 240)
            set_pixel(px_i, py_i - 1, 0, 200, 255)
            set_pixel(px_i - 1, py_i + 1, 200, 40, 30)
            set_pixel(px_i + 1, py_i + 1, 200, 40, 30)
            set_pixel(px_i, py_i + 1, 255, 140, 20)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 255, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "area": self.area,
            "px": self.px,
            "py": self.py,
            "enemies_downed": self.enemies_downed,
            "andor_hp": self.andor_hp,
        }
