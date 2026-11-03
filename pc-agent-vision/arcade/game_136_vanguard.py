# -*- coding: utf-8 -*-
"""
Game #136: 宇宙巡航拦截者 (Vanguard 1981 / TOSE & SNK)
街机历史上第一部具备变向隧道卷轴、能量荚舱无敌冲撞与贡德巨眼BOSS的里程碑射击游戏：
山洞隧道变轨飞行、燃油能量条持续衰减补给、拾取能量荚舱启动彩虹无敌冲撞摧毁一切、
按键A前向主激光炮、按键B反向拦截炮、突破旋转护盾轰击贡德核心。
"""

from typing import List, Dict, Any, Optional
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

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_SHIP_CRASH = 2
STATE_GAME_OVER = 3

ZONE_MOUNTAIN = 0  # Horizontal scrolling cavern
ZONE_STRIPE = 1    # Vertical scrolling shaft
ZONE_GOND = 2      # Boss dome chamber (The Gond)


class Game136Vanguard(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.fuel = 100.0  # Constant fuel drain
        self.zone = ZONE_MOUNTAIN

        # Ship position and heading
        self.px = 2.0
        self.py = 7.5
        self.p_heading = (1.0, 0.0)  # Facing Right by default

        # Invulnerability energy pod status
        self.invulnerable_timer = 0.0

        # Cavern walls: top_wall[16], bot_wall[16]
        self.top_walls = [2.0 for _ in range(16)]
        self.bot_walls = [13.0 for _ in range(16)]
        self.wall_offset = 0.0

        # Lasers: list of bullets
        self.bullets: List[Dict[str, Any]] = []

        # Enemies: floating scouts / pods
        self.enemies: List[Dict[str, Any]] = []

        # Energy Pod powerup (one per zone)
        self.energy_pod: Optional[Dict[str, Any]] = None

        # Gond Boss (Zone 2)
        self.gond_hp = 3
        self.gond_shield_angle = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 136

    @property
    def name(self) -> str:
        return "宇宙巡航拦截者"

    @property
    def english_name(self) -> str:
        return "Vanguard"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "变向隧道飞行与燃油衰减消耗、能量荚舱无敌冲撞歼敌、双向火控与贡德核心眼爆破"

    def get_name(self) -> str:
        return "Vanguard (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.fuel = 100.0
        self.zone = ZONE_MOUNTAIN
        self.px = 2.0
        self.py = 7.5
        self.p_heading = (1.0, 0.0)
        self.invulnerable_timer = 0.0
        self.bullets = []
        self._init_zone_mountain()

    def _init_zone_mountain(self) -> None:
        self.zone = ZONE_MOUNTAIN
        self.wall_offset = 0.0
        # Horizontal tunnel
        self.top_walls = [2.0 + math.sin(i * 0.5) * 1.0 for i in range(16)]
        self.bot_walls = [13.0 - math.sin(i * 0.5) * 1.0 for i in range(16)]

        self.enemies = [
            {"x": 10.0, "y": 5.0, "vx": -2.0, "vy": 0.5, "alive": True},
            {"x": 13.0, "y": 9.0, "vx": -2.5, "vy": -0.6, "alive": True},
            {"x": 15.0, "y": 7.0, "vx": -3.0, "vy": 0.0, "alive": True},
        ]
        # Energy pod floating in tunnel
        self.energy_pod = {"x": 14.0, "y": 7.5, "collected": False}

    def _init_zone_stripe(self) -> None:
        self.zone = ZONE_STRIPE
        self.px = 7.5
        self.py = 13.0
        self.p_heading = (0.0, -1.0)  # Flying Up
        self.top_walls = [2.0 for _ in range(16)]  # Left wall
        self.bot_walls = [13.0 for _ in range(16)] # Right wall

        self.enemies = [
            {"x": 6.0, "y": 2.0, "vx": 1.0, "vy": 1.5, "alive": True},
            {"x": 9.0, "y": 4.0, "vx": -1.2, "vy": 1.2, "alive": True},
            {"x": 7.5, "y": 1.0, "vx": 0.0, "vy": 2.0, "alive": True},
        ]
        self.energy_pod = {"x": 7.5, "y": 3.0, "collected": False}

    def _init_zone_gond(self) -> None:
        self.zone = ZONE_GOND
        self.px = 7.5
        self.py = 13.5
        self.p_heading = (0.0, -1.0)
        self.gond_hp = 3
        self.gond_shield_angle = 0.0
        self.enemies = []
        self.energy_pod = None

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_SHIP_CRASH):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_SHIP_CRASH:
                    if self.lives > 0:
                        self.fuel = 100.0
                        self.px = 2.0 if self.zone == ZONE_MOUNTAIN else 7.5
                        self.py = 7.5 if self.zone == ZONE_MOUNTAIN else 13.0
                        self.state = STATE_PLAYING
                        self.state_timer = 0.0
                    else:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.state_timer += dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()

    def _update_playing(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Fuel drain
        self.fuel -= 2.5 * dt
        if self.fuel <= 0.0:
            self.fuel = 0.0
            self._crash_ship()
            return

        # Invulnerability timer
        if self.invulnerable_timer > 0.0:
            self.invulnerable_timer -= dt
            if self.invulnerable_timer < 0.0:
                self.invulnerable_timer = 0.0

        # Movement and heading
        move_speed = 7.0
        vx = 0.0
        vy = 0.0
        if buttons & KEY_LEFT:
            vx -= move_speed
        if buttons & KEY_RIGHT:
            vx += move_speed
        if buttons & KEY_UP:
            vy -= move_speed
        if buttons & KEY_DOWN:
            vy += move_speed

        if vx != 0.0 or vy != 0.0:
            mag = math.hypot(vx, vy)
            self.p_heading = (vx / mag, vy / mag)

        self.px += vx * dt
        self.py += vy * dt

        # Boundary clamping & tunnel walls
        if self.zone == ZONE_MOUNTAIN:
            self.px = max(0.5, min(14.5, self.px))
            # Check cavern top and bottom ceiling collision
            c_idx = max(0, min(15, int(round(self.px))))
            top_bound = self.top_walls[c_idx]
            bot_bound = self.bot_walls[c_idx]
            if (self.py <= top_bound or self.py >= bot_bound) and self.invulnerable_timer <= 0.0:
                self._crash_ship()
                return
            self.py = max(top_bound + 0.2, min(bot_bound - 0.2, self.py))
        elif self.zone in (ZONE_STRIPE, ZONE_GOND):
            self.px = max(2.5, min(12.5, self.px))
            self.py = max(0.5, min(14.5, self.py))

        # Laser Firing: Key A (Forward cannon)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.bullets) < 3:
                self.bullets.append({
                    "x": self.px + self.p_heading[0] * 0.8,
                    "y": self.py + self.p_heading[1] * 0.8,
                    "vx": self.p_heading[0] * 15.0,
                    "vy": self.p_heading[1] * 15.0,
                    "active": True,
                })
        # Laser Firing: Key B (Reverse cannon)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if len(self.bullets) < 3:
                self.bullets.append({
                    "x": self.px - self.p_heading[0] * 0.8,
                    "y": self.py - self.p_heading[1] * 0.8,
                    "vx": -self.p_heading[0] * 15.0,
                    "vy": -self.p_heading[1] * 15.0,
                    "active": True,
                })

        # Update Bullets
        for b in self.bullets:
            if b["active"]:
                b["x"] += b["vx"] * dt
                b["y"] += b["vy"] * dt
                if not (0.0 <= b["x"] < 16.0 and 0.0 <= b["y"] < 16.0):
                    b["active"] = False
                    continue

                # Enemy collision
                for enemy in self.enemies:
                    if enemy["alive"]:
                        if abs(b["x"] - enemy["x"]) < 1.0 and abs(b["y"] - enemy["y"]) < 1.0:
                            enemy["alive"] = False
                            b["active"] = False
                            self.score += 100
                            self.fuel = min(100.0, self.fuel + 15.0)
                            break

                # Gond Boss hit
                if self.zone == ZONE_GOND and self.gond_hp > 0:
                    if abs(b["x"] - 7.5) < 1.2 and abs(b["y"] - 3.5) < 1.2:
                        # Check if shield gap is open (angle between 0.3 and 1.2 rad)
                        shield_normalized = self.gond_shield_angle % (2 * math.pi)
                        if shield_normalized > 0.8 and shield_normalized < 2.5:
                            b["active"] = False
                            self.gond_hp -= 1
                            self.score += 300
                            if self.gond_hp <= 0:
                                self.score += 1000
                                self.state = STATE_STAGE_CLEAR
                                self.state_timer = 0.0
                                return
                        else:
                            # Blocked by shield
                            b["active"] = False

        self.bullets = [b for b in self.bullets if b["active"]]

        # Energy Pod Pickup
        if self.energy_pod and not self.energy_pod["collected"]:
            if abs(self.px - self.energy_pod["x"]) < 1.2 and abs(self.py - self.energy_pod["y"]) < 1.2:
                self.energy_pod["collected"] = True
                self.invulnerable_timer = 6.0
                self.fuel = 100.0
                self.score += 200

        # Update Enemies & Collisions
        all_enemies_dead = True
        for enemy in self.enemies:
            if enemy["alive"]:
                all_enemies_dead = False
                enemy["x"] += enemy["vx"] * dt
                enemy["y"] += enemy["vy"] * dt

                # Bounce or wrap inside zone
                if self.zone == ZONE_MOUNTAIN:
                    if enemy["x"] <= 0.0:
                        enemy["x"] = 15.5
                elif self.zone == ZONE_STRIPE:
                    if enemy["y"] >= 16.0:
                        enemy["y"] = 0.5

                # Player collision
                if abs(self.px - enemy["x"]) < 0.9 and abs(self.py - enemy["y"]) < 0.9:
                    if self.invulnerable_timer > 0.0:
                        # Ramming powerup!
                        enemy["alive"] = False
                        self.score += 200
                    else:
                        self._crash_ship()
                        return

        # Zone advancement when enemies cleared
        if self.zone == ZONE_MOUNTAIN and all_enemies_dead:
            self.score += 300
            self._init_zone_stripe()
        elif self.zone == ZONE_STRIPE and all_enemies_dead:
            self.score += 400
            self._init_zone_gond()
        elif self.zone == ZONE_GOND:
            self.gond_shield_angle += 3.0 * dt

    def _crash_ship(self) -> None:
        self.lives -= 1
        self.state = STATE_SHIP_CRASH
        self.state_timer = 0.0

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(16 * 16 * 3):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Render Cavern Walls / Shaft
        if self.zone == ZONE_MOUNTAIN:
            for x in range(16):
                top_y = int(round(self.top_walls[x]))
                bot_y = int(round(self.bot_walls[x]))
                for y in range(0, top_y + 1):
                    set_pixel(x, y, 100, 50, 20)
                for y in range(bot_y, 16):
                    set_pixel(x, y, 100, 50, 20)
        elif self.zone in (ZONE_STRIPE, ZONE_GOND):
            for y in range(16):
                set_pixel(1, y, 40, 60, 120)
                set_pixel(2, y, 70, 90, 160)
                set_pixel(13, y, 70, 90, 160)
                set_pixel(14, y, 40, 60, 120)

        # 2. Render Energy Pod
        if self.energy_pod and not self.energy_pod["collected"]:
            epx = int(round(self.energy_pod["x"]))
            epy = int(round(self.energy_pod["y"]))
            set_pixel(epx, epy, 255, 240, 50)
            set_pixel(epx + 1, epy, 255, 120, 30)

        # 3. Render Enemies
        for enemy in self.enemies:
            if enemy["alive"]:
                ex = int(round(enemy["x"]))
                ey = int(round(enemy["y"]))
                set_pixel(ex, ey, 240, 50, 40)
                set_pixel(ex, ey - 1, 255, 120, 60)

        # 4. Render Gond Boss (Zone 2)
        if self.zone == ZONE_GOND and self.gond_hp > 0:
            # Gond central eye
            set_pixel(7, 3, 255, 255, 255)
            set_pixel(8, 3, 255, 255, 255)
            set_pixel(7, 4, 255, 30, 30)
            set_pixel(8, 4, 255, 30, 30)
            # Rotating shield arc
            for a in range(4):
                rad = self.gond_shield_angle + a * 0.4
                sx = int(round(7.5 + math.cos(rad) * 2.5))
                sy = int(round(3.5 + math.sin(rad) * 2.5))
                set_pixel(sx, sy, 50, 220, 255)

        # 5. Render Bullets
        for b in self.bullets:
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 180)

        # 6. Render Player Ship
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.invulnerable_timer > 0.0:
                # Rainbow flashing invulnerability
                flash = int(self.invulnerable_timer * 15) % 3
                colors = [(255, 255, 255), (255, 220, 50), (50, 255, 220)]
                c = colors[flash]
                set_pixel(px, py, c[0], c[1], c[2])
                set_pixel(px - 1, py, c[0], c[1], c[2])
                set_pixel(px + 1, py, c[0], c[1], c[2])
            else:
                set_pixel(px, py, 60, 200, 255)
                set_pixel(px - 1, py, 40, 120, 220)
                set_pixel(px, py - 1, 255, 255, 255)
        elif self.state == STATE_SHIP_CRASH:
            set_pixel(px, py, 255, 120, 30)
            set_pixel(px - 1, py, 255, 40, 20)
            set_pixel(px + 1, py, 255, 40, 20)

        # 7. Fuel gauge line on bottom row
        fuel_pixels = int(round((self.fuel / 100.0) * 15.0))
        for x in range(fuel_pixels + 1):
            set_pixel(x, 15, 50, 220, 60)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "zone": self.zone,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "fuel": self.fuel,
            "px": self.px,
            "py": self.py,
            "invulnerable": self.invulnerable_timer > 0.0,
            "gond_hp": self.gond_hp,
        }
