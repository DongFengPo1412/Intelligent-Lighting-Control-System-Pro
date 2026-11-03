# -*- coding: utf-8 -*-
"""
Game #140: 巨脸毁灭者 (Sinistar 1983 / Williams Electronics)
街机历史上最震撼的星际采矿萃取晶石与反击狂暴机械巨脸的传奇射击游戏：
自由惯性漂移星域、轰击小行星开采能量晶石合成为西尼追踪炸弹、
拦截偷运晶石组装魔头的工蜂战机、发射西尼炸弹引爆巨型咆哮魔头“西尼星君”。
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
STATE_SHIP_DEVOURED = 2
STATE_GAME_OVER = 3


class Game140Sinistar(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        # Player ship
        self.px = 7.5
        self.py = 7.5
        self.vx = 0.0
        self.vy = 0.0
        self.angle = -math.pi / 2  # Facing Up
        self.sinibombs = 3  # Stockpile of target-seeking bombs

        # Bullets
        self.bullets: List[Dict[str, Any]] = []

        # Sinibombs in flight
        self.active_bombs: List[Dict[str, Any]] = []

        # Asteroids to mine
        self.asteroids: List[Dict[str, Any]] = []

        # Drifting crystals
        self.crystals: List[Dict[str, Any]] = []

        # Worker drone enemies
        self.workers: List[Dict[str, Any]] = []

        # Sinistar Boss
        self.sinistar_alive = False
        self.sinistar_pieces = 0
        self.sinistar_hp = 5
        self.sinistar_x = 7.5
        self.sinistar_y = -10.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 140

    @property
    def name(self) -> str:
        return "巨脸毁灭者"

    @property
    def english_name(self) -> str:
        return "Sinistar"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "射击行星采矿萃取晶石造弹、拦截工蜂组装魔头、发射追踪核弹歼灭狂暴巨脸"

    def get_name(self) -> str:
        return "Sinistar (1983)"

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
        self.px = 7.5
        self.py = 7.5
        self.vx = 0.0
        self.vy = 0.0
        self.angle = -math.pi / 2
        self.sinibombs = 3

        self.bullets = []
        self.active_bombs = []
        self.crystals = []

        self.sinistar_alive = False
        self.sinistar_pieces = 0
        self.sinistar_hp = 5
        self.sinistar_x = 7.5
        self.sinistar_y = 1.0

        # Asteroids
        self.asteroids = [
            {"x": 3.0, "y": 4.0, "hp": 4},
            {"x": 12.0, "y": 4.0, "hp": 4},
            {"x": 4.0, "y": 12.0, "hp": 4},
            {"x": 12.0, "y": 12.0, "hp": 4},
        ]

        # Worker Drones
        self.workers = [
            {"x": 2.0, "y": 2.0, "vx": 1.2, "vy": 0.8, "has_crystal": False, "alive": True, "respawn_timer": 0.0},
            {"x": 13.0, "y": 13.0, "vx": -1.2, "vy": -0.8, "has_crystal": False, "alive": True, "respawn_timer": 0.0},
        ]

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_SHIP_DEVOURED):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_SHIP_DEVOURED:
                    if self.lives > 0:
                        self.px = 7.5
                        self.py = 7.5
                        self.vx = 0.0
                        self.vy = 0.0
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
        # Rotation & Thrust
        turn_speed = 4.5
        if buttons & KEY_LEFT:
            self.angle -= turn_speed * dt
        if buttons & KEY_RIGHT:
            self.angle += turn_speed * dt

        # Normalize angle
        self.angle = (self.angle + math.pi) % (2 * math.pi) - math.pi

        thrust = 10.0
        if buttons & KEY_UP:
            self.vx += math.cos(self.angle) * thrust * dt
            self.vy += math.sin(self.angle) * thrust * dt

        # Inertia dampening
        self.vx *= 0.96
        self.vy *= 0.96

        self.px = (self.px + self.vx * dt) % 16.0
        self.py = (self.py + self.vy * dt) % 16.0

        # Fire Standard Laser: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.bullets) < 3:
                self.bullets.append({
                    "x": self.px + math.cos(self.angle) * 0.8,
                    "y": self.py + math.sin(self.angle) * 0.8,
                    "vx": math.cos(self.angle) * 16.0,
                    "vy": math.sin(self.angle) * 16.0,
                    "active": True,
                })

        # Launch Sinibomb: Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.sinibombs > 0 and len(self.active_bombs) < 2:
                self.sinibombs -= 1
                self.active_bombs.append({
                    "x": self.px,
                    "y": self.py,
                    "vx": math.cos(self.angle) * 10.0,
                    "vy": math.sin(self.angle) * 10.0,
                    "active": True,
                })

        # Update Standard Lasers
        for b in self.bullets:
            if b["active"]:
                b["x"] += b["vx"] * dt
                b["y"] += b["vy"] * dt
                if not (0.0 <= b["x"] < 16.0 and 0.0 <= b["y"] < 16.0):
                    b["active"] = False
                    continue

                # Check asteroid mining hit
                for a in self.asteroids:
                    if a["hp"] > 0:
                        if abs(b["x"] - a["x"]) < 1.1 and abs(b["y"] - a["y"]) < 1.1:
                            b["active"] = False
                            a["hp"] -= 1
                            self.score += 20
                            # Eject glowing crystal!
                            if len(self.crystals) < 5:
                                self.crystals.append({
                                    "x": a["x"] + (b["vx"] / 16.0) * 0.8,
                                    "y": a["y"] + (b["vy"] / 16.0) * 0.8,
                                    "active": True,
                                })
                            break

                # Check worker hit
                if b["active"]:
                    for w in self.workers:
                        if w["alive"]:
                            if abs(b["x"] - w["x"]) < 0.9 and abs(b["y"] - w["y"]) < 0.9:
                                w["alive"] = False
                                w["respawn_timer"] = 3.0
                                b["active"] = False
                                self.score += 150
                                break

        self.bullets = [b for b in self.bullets if b["active"]]

        # Player collects drifting crystals -> +1 Sinibomb!
        for c in self.crystals:
            if c["active"]:
                if abs(self.px - c["x"]) < 1.0 and abs(self.py - c["y"]) < 1.0:
                    c["active"] = False
                    self.sinibombs = min(20, self.sinibombs + 1)
                    self.score += 100

        # Update Worker Drones (Gather crystals to assemble Sinistar)
        for w in self.workers:
            if not w["alive"]:
                continue
            if not w["has_crystal"]:
                # Head towards nearest crystal
                target_c = None
                min_d = 999.0
                for c in self.crystals:
                    if c["active"]:
                        d = math.hypot(c["x"] - w["x"], c["y"] - w["y"])
                        if d < min_d:
                            min_d = d
                            target_c = c
                if target_c:
                    ang = math.atan2(target_c["y"] - w["y"], target_c["x"] - w["x"])
                    w["vx"] = math.cos(ang) * 2.5
                    w["vy"] = math.sin(ang) * 2.5
                    if min_d < 0.6:
                        target_c["active"] = False
                        w["has_crystal"] = True
            else:
                # Deliver crystal to Sinistar construction site
                ang = math.atan2(self.sinistar_y - w["y"], self.sinistar_x - w["x"])
                w["vx"] = math.cos(ang) * 2.5
                w["vy"] = math.sin(ang) * 2.5
                if math.hypot(self.sinistar_x - w["x"], self.sinistar_y - w["y"]) < 1.0:
                    w["has_crystal"] = False
                    self.sinistar_pieces += 1
                    if self.sinistar_pieces >= 6 and not self.sinistar_alive:
                        self.sinistar_alive = True  # "BEWARE, I LIVE!"

            w["x"] = (w["x"] + w["vx"] * dt) % 16.0
            w["y"] = (w["y"] + w["vy"] * dt) % 16.0

        self.crystals = [c for c in self.crystals if c["active"]]

        # Respawn dead workers
        for w in self.workers:
            if not w["alive"]:
                w["respawn_timer"] -= dt
                if w["respawn_timer"] <= 0.0:
                    w["x"] = 0.5
                    w["y"] = 0.5
                    w["alive"] = True
                    w["has_crystal"] = False

        # Sinistar Boss Pursuit
        if self.sinistar_alive:
            s_speed = 3.5
            ang = math.atan2(self.py - self.sinistar_y, self.px - self.sinistar_x)
            self.sinistar_x += math.cos(ang) * s_speed * dt
            self.sinistar_y += math.sin(ang) * s_speed * dt

            # Collision with player -> Devoured!
            if abs(self.px - self.sinistar_x) < 1.2 and abs(self.py - self.sinistar_y) < 1.2:
                self.lives -= 1
                self.state = STATE_SHIP_DEVOURED
                self.state_timer = 0.0
                return

        # Update Homing Sinibombs
        for sb in self.active_bombs:
            if sb["active"]:
                if self.sinistar_alive:
                    ang = math.atan2(self.sinistar_y - sb["y"], self.sinistar_x - sb["x"])
                    sb["vx"] = math.cos(ang) * 14.0
                    sb["vy"] = math.sin(ang) * 14.0
                sb["x"] += sb["vx"] * dt
                sb["y"] += sb["vy"] * dt

                if not (0.0 <= sb["x"] < 16.0 and 0.0 <= sb["y"] < 16.0):
                    sb["active"] = False
                    continue

                if self.sinistar_alive:
                    if abs(sb["x"] - self.sinistar_x) < 1.5 and abs(sb["y"] - self.sinistar_y) < 1.5:
                        sb["active"] = False
                        self.sinistar_hp -= 1
                        self.score += 400
                        if self.sinistar_hp <= 0:
                            # Sinistar destroyed!
                            self.sinistar_alive = False
                            self.score += 2000
                            self.state = STATE_STAGE_CLEAR
                            self.state_timer = 0.0
                            return

        self.active_bombs = [sb for sb in self.active_bombs if sb["active"]]

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

        # 1. Render Asteroids (Brown / Gray)
        for a in self.asteroids:
            if a["hp"] > 0:
                ax = int(round(a["x"]))
                ay = int(round(a["y"]))
                set_pixel(ax, ay, 140, 110, 80)
                set_pixel(ax + 1, ay, 100, 80, 50)
                set_pixel(ax, ay + 1, 100, 80, 50)

        # 2. Render Crystals (Glowing White-Cyan)
        for c in self.crystals:
            if c["active"]:
                cx = int(round(c["x"]))
                cy = int(round(c["y"]))
                set_pixel(cx, cy, 180, 255, 255)

        # 3. Render Worker Drones (Red/Orange)
        for w in self.workers:
            if w["alive"]:
                wx = int(round(w["x"]))
                wy = int(round(w["y"]))
                set_pixel(wx, wy, 255, 100, 30)
                if w["has_crystal"]:
                    set_pixel(wx, wy - 1, 255, 255, 255)

        # 4. Render Sinistar
        if self.sinistar_alive:
            # Terrifying 3x3 Skull Face (Silver-Grey & Red Eyes)
            sx = int(round(self.sinistar_x))
            sy = int(round(self.sinistar_y))
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    set_pixel(sx + ox, sy + oy, 160, 160, 180)
            # Glowing red eyes
            set_pixel(sx - 1, sy - 1, 255, 20, 20)
            set_pixel(sx + 1, sy - 1, 255, 20, 20)
            # Menacing jaw/mouth
            set_pixel(sx, sy + 1, 40, 0, 0)
        elif self.sinistar_pieces > 0:
            # Construction site pieces
            sx = int(round(self.sinistar_x))
            sy = int(round(self.sinistar_y))
            for p in range(min(self.sinistar_pieces, 6)):
                set_pixel(sx + (p % 3) - 1, sy + (p // 3) - 1, 90, 90, 110)

        # 5. Render Bullets
        for b in self.bullets:
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 100)

        # 6. Render Sinibombs
        for sb in self.active_bombs:
            set_pixel(int(round(sb["x"])), int(round(sb["y"])), 255, 40, 220)

        # 7. Render Player Ship
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 50, 180, 255)
            # Nose cone pointing along angle
            nx = int(round(self.px + math.cos(self.angle) * 1.1))
            ny = int(round(self.py + math.sin(self.angle) * 1.1))
            set_pixel(nx, ny, 255, 255, 255)
        elif self.state == STATE_SHIP_DEVOURED:
            set_pixel(px, py, 255, 50, 20)
            set_pixel(px - 1, py, 255, 150, 20)
            set_pixel(px + 1, py, 255, 150, 20)

        # 8. Sinibomb Stockpile count on bottom row
        for b in range(min(self.sinibombs, 5)):
            set_pixel(b * 2, 15, 255, 60, 240)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "px": self.px,
            "py": self.py,
            "sinibombs": self.sinibombs,
            "sinistar_alive": self.sinistar_alive,
            "sinistar_hp": self.sinistar_hp,
            "sinistar_pieces": self.sinistar_pieces,
        }
