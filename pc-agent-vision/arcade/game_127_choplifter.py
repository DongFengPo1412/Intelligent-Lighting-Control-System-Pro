# -*- coding: utf-8 -*-
"""
Game #127: 救难直升机 (Choplifter 1982 / Broderbund & Sega Arcade)
街机历史上最具传奇色彩的敌后人质营救飞行战斗模拟：
三向姿态切换(左/中俯视投弹/右)、轰碎敌军集中营牢房、平稳着陆登机撤离、规避高炮与防空喷气机、基地安全卸载。
"""

from typing import List, Dict, Any, Optional
import math
import random
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
STATE_CHOPPER_DOWN = 1
STATE_MISSION_CLEAR = 2
STATE_GAME_OVER = 3

FACING_LEFT = 0
FACING_FORWARD = 1
FACING_RIGHT = 2

GROUND_Y = 13.8
BASE_MAX_X = 3.2
MAX_HOSTAGES = 16
MAX_ONBOARD = 8
MAX_BULLETS = 4
MAX_ENEMY_JETS = 2


class Game127Choplifter(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.mission = 1

        self.hx = 1.5
        self.hy = GROUND_Y
        self.hvx = 0.0
        self.hvy = 0.0
        self.facing = FACING_RIGHT
        self.is_landed = True

        self.onboard_count = 0
        self.rescued_count = 0
        self.kia_count = 0

        self.barracks_broken = False
        self.barracks_hp = 3.0

        self.hostages: List[Dict[str, Any]] = []
        self.bullets: List[Dict[str, Any]] = []
        self.jets: List[Dict[str, Any]] = []
        self.jet_spawn_timer = 3.0

        self.tank_x = 8.0
        self.tank_vx = 1.2
        self.tank_alive = True

        self.reset()

    @property
    def game_id(self) -> int:
        return 127

    @property
    def name(self) -> str:
        return "救难直升机"

    @property
    def english_name(self) -> str:
        return "Choplifter"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "三向姿态切换、炸毁集中营牢房、地面降落登机撤离人质与基地安全转运"

    def get_name(self) -> str:
        return "Choplifter (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.mission = 1
        self._init_mission()

    def _init_mission(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0

        self.hx = 1.5
        self.hy = GROUND_Y
        self.hvx = 0.0
        self.hvy = 0.0
        self.facing = FACING_RIGHT
        self.is_landed = True

        self.onboard_count = 0
        self.rescued_count = 0
        self.kia_count = 0

        self.barracks_broken = False
        self.barracks_hp = 3.0

        self.hostages = []
        for _ in range(MAX_HOSTAGES):
            self.hostages.append({
                "x": 10.5,
                "y": GROUND_Y,
                "state": 0,  # 0: Barracks, 1: Running, 2: Onboard, 3: Rescued
            })

        self.bullets = []
        for _ in range(MAX_BULLETS):
            self.bullets.append({
                "x": 0.0,
                "y": 0.0,
                "vx": 0.0,
                "vy": 0.0,
                "is_bomb": False,
                "active": False,
            })

        self.jets = []
        for _ in range(MAX_ENEMY_JETS):
            self.jets.append({
                "x": 0.0,
                "y": 0.0,
                "vx": 0.0,
                "active": False,
            })
        self.jet_spawn_timer = 3.0

        self.tank_x = 8.0
        self.tank_vx = 1.2
        self.tank_alive = True

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_CHOPPER_DOWN:
            if self.state_timer > 1.5:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_FLYING
                    self.hx = 1.5
                    self.hy = GROUND_Y
                    self.hvx = 0.0
                    self.hvy = 0.0
                    self.facing = FACING_RIGHT
                    self.is_landed = True
                    self.onboard_count = 0
            return

        if self.state == STATE_MISSION_CLEAR:
            if self.state_timer > 1.8:
                self.mission += 1
                self.score += 2000
                self._init_mission()
            return

        self._update_chopper(dt, buttons, prev_buttons)
        self._update_hostages(dt)
        self._update_bullets(dt)
        self._update_enemies(dt)
        self._check_collisions()

        if self.rescued_count + self.kia_count >= MAX_HOSTAGES and self.onboard_count == 0:
            if self.rescued_count >= 8:
                self.state = STATE_MISSION_CLEAR
                self.state_timer = 0.0
            else:
                self.state = STATE_GAME_OVER

    def _update_chopper(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Button B: Cycle facing
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.facing == FACING_LEFT:
                self.facing = FACING_FORWARD
            elif self.facing == FACING_FORWARD:
                self.facing = FACING_RIGHT
            else:
                self.facing = FACING_LEFT

        # Button A: Fire weapon
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            for b in self.bullets:
                if not b["active"]:
                    b["active"] = True
                    b["x"] = self.hx
                    b["y"] = self.hy
                    if self.facing == FACING_LEFT:
                        b["vx"] = -14.0
                        b["vy"] = 0.0
                        b["is_bomb"] = False
                    elif self.facing == FACING_RIGHT:
                        b["vx"] = 14.0
                        b["vy"] = 0.0
                        b["is_bomb"] = False
                    else:
                        b["vx"] = self.hvx * 0.4
                        b["vy"] = 10.0
                        b["is_bomb"] = True
                    break

        lift_accel = 12.0
        grav = 6.0
        if buttons & KEY_UP:
            self.hvy -= lift_accel * dt
            self.is_landed = False
        else:
            self.hvy += grav * dt

        if buttons & KEY_DOWN:
            self.hvy += lift_accel * 0.5 * dt

        lateral_thrust = 9.0
        if buttons & KEY_LEFT:
            self.hvx -= lateral_thrust * dt
            self.is_landed = False
        if buttons & KEY_RIGHT:
            self.hvx += lateral_thrust * dt
            self.is_landed = False

        self.hvx *= 0.94
        self.hvy *= 0.94

        self.hx += self.hvx * dt
        self.hy += self.hvy * dt

        if self.hx < 0.5:
            self.hx = 0.5
            self.hvx = 0.0
        elif self.hx > 15.0:
            self.hx = 15.0
            self.hvx = 0.0

        if self.hy < 1.0:
            self.hy = 1.0
            self.hvy = 0.0

        # Touchdown check
        if self.hy >= GROUND_Y:
            self.hy = GROUND_Y
            if abs(self.hvy) > 4.5 or abs(self.hvx) > 3.0:
                self.state = STATE_CHOPPER_DOWN
                self.state_timer = 0.0
            else:
                self.hvy = 0.0
                self.hvx = 0.0
                self.is_landed = True

                if self.hx <= BASE_MAX_X and self.onboard_count > 0:
                    self.rescued_count += self.onboard_count
                    self.score += self.onboard_count * 500
                    self.onboard_count = 0

    def _update_hostages(self, dt: float) -> None:
        for h in self.hostages:
            if h["state"] == 1:
                target_x = self.hx if self.is_landed else 1.5
                run_spd = 2.0
                if h["x"] < target_x - 0.2:
                    h["x"] += run_spd * dt
                elif h["x"] > target_x + 0.2:
                    h["x"] -= run_spd * dt

                if self.is_landed and abs(h["x"] - self.hx) < 0.6 and self.onboard_count < MAX_ONBOARD:
                    h["state"] = 2
                    self.onboard_count += 1

    def _update_bullets(self, dt: float) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            if b["is_bomb"]:
                b["vy"] += 4.0 * dt

            if b["x"] < 0.0 or b["x"] > 15.5 or b["y"] < 0.5 or b["y"] > GROUND_Y:
                b["active"] = False

    def _update_enemies(self, dt: float) -> None:
        if self.tank_alive:
            self.tank_x += self.tank_vx * dt
            if self.tank_x < 5.0:
                self.tank_x = 5.0
                self.tank_vx = -self.tank_vx
            elif self.tank_x > 14.5:
                self.tank_x = 14.5
                self.tank_vx = -self.tank_vx

        self.jet_spawn_timer -= dt
        if self.jet_spawn_timer <= 0.0:
            self.jet_spawn_timer = max(1.5, 4.0 - self.mission * 0.2)
            for j in self.jets:
                if not j["active"]:
                    j["active"] = True
                    j["x"] = 15.5
                    j["y"] = 2.5 + random.random() * 3.0
                    j["vx"] = -(6.0 + self.mission * 0.5)
                    break

        for j in self.jets:
            if not j["active"]:
                continue
            j["x"] += j["vx"] * dt
            if j["x"] < -1.0:
                j["active"] = False

    def _check_collisions(self) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue

            if not self.barracks_broken and 9.0 <= b["x"] <= 12.0 and b["y"] >= 12.0:
                b["active"] = False
                self.barracks_hp -= 1.0
                if self.barracks_hp <= 0.0:
                    self.barracks_broken = True
                    self.score += 300
                    for idx, h in enumerate(self.hostages):
                        if h["state"] == 0:
                            h["state"] = 1
                            h["x"] = 9.5 + (idx % 3) * 0.8
                continue

            if self.tank_alive and abs(b["x"] - self.tank_x) < 1.0 and b["y"] >= 13.0:
                b["active"] = False
                self.tank_alive = False
                self.score += 400
                continue

            for j in self.jets:
                if not j["active"]:
                    continue
                if abs(b["x"] - j["x"]) < 0.9 and abs(b["y"] - j["y"]) < 0.9:
                    b["active"] = False
                    j["active"] = False
                    self.score += 250
                    break

        if self.tank_alive and abs(self.hx - self.tank_x) < 0.9 and self.hy >= 13.0:
            self.state = STATE_CHOPPER_DOWN
            self.state_timer = 0.0

        for j in self.jets:
            if not j["active"]:
                continue
            if abs(self.hx - j["x"]) < 0.9 and abs(self.hy - j["y"]) < 0.9:
                self.state = STATE_CHOPPER_DOWN
                self.state_timer = 0.0
                break

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        elif len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Ground & Base
        for x in range(16):
            set_pixel(x, 15, 120, 80, 30)
            set_pixel(x, 14, 80, 140, 40)

        # Base camp bunker
        set_pixel(0, 13, 0, 180, 255)
        set_pixel(1, 13, 0, 220, 255)
        set_pixel(2, 13, 0, 180, 255)
        set_pixel(1, 12, 255, 255, 255)
        set_pixel(1, 11, 255, 30, 20)

        # Barracks
        if not self.barracks_broken:
            for bx in range(9, 13):
                set_pixel(bx, 13, 160, 50, 40)
                set_pixel(bx, 12, 120, 30, 20)
        else:
            set_pixel(9, 13, 100, 40, 20)
            set_pixel(12, 13, 100, 40, 20)

        # Hostages
        for h in self.hostages:
            if h["state"] == 1:
                hx_s = int(round(h["x"]))
                set_pixel(hx_s, 14, 255, 240, 160)
                set_pixel(hx_s, 13, 255, 255, 255)

        # Tank
        if self.tank_alive:
            tx = int(round(self.tank_x))
            set_pixel(tx, 14, 200, 40, 30)
            set_pixel(tx, 13, 160, 20, 20)

        # Jets
        for j in self.jets:
            if j["active"]:
                jx = int(round(j["x"]))
                jy = int(round(j["y"]))
                set_pixel(jx, jy, 255, 60, 40)
                set_pixel(jx + 1, jy, 255, 180, 0)

        # Bullets
        for b in self.bullets:
            if b["active"]:
                bx = int(round(b["x"]))
                by = int(round(b["y"]))
                if b["is_bomb"]:
                    set_pixel(bx, by, 255, 200, 30)
                else:
                    set_pixel(bx, by, 80, 255, 255)

        # Helicopter
        chx = int(round(self.hx))
        chy = int(round(self.hy))
        if self.state in (STATE_FLYING, STATE_MISSION_CLEAR):
            blade = (int(self.state_timer * 20.0) % 2) == 0
            if blade:
                set_pixel(chx - 1, chy - 1, 220, 220, 240)
                set_pixel(chx + 1, chy - 1, 220, 220, 240)
            else:
                set_pixel(chx, chy - 1, 255, 255, 255)

            set_pixel(chx, chy, 40, 220, 100)
            if self.facing == FACING_LEFT:
                set_pixel(chx - 1, chy, 255, 255, 255)
                set_pixel(chx + 1, chy, 40, 160, 70)
            elif self.facing == FACING_RIGHT:
                set_pixel(chx + 1, chy, 255, 255, 255)
                set_pixel(chx - 1, chy, 40, 160, 70)
            else:
                set_pixel(chx, chy, 255, 255, 255)
                set_pixel(chx - 1, chy, 40, 200, 80)
                set_pixel(chx + 1, chy, 40, 200, 80)
        elif self.state == STATE_CHOPPER_DOWN:
            set_pixel(chx, chy, 255, 200, 40)
            set_pixel(chx - 1, chy, 255, 40, 20)
            set_pixel(chx + 1, chy, 255, 40, 20)
            set_pixel(chx, chy - 1, 255, 120, 0)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 40, 220, 100)
        for ob in range(min(self.onboard_count, 8)):
            set_pixel(7 + ob, 0, 255, 240, 160)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "mission": self.mission,
            "onboard": self.onboard_count,
            "rescued": self.rescued_count,
            "facing": self.facing,
            "hx": self.hx,
            "hy": self.hy,
        }
