"""
Game #090: 经典落日骑士 / 西部牛仔 (Sunset Riders 1991 / Konami)
Wild west saloon gunfights, sliding under enemy bullets, dual gun badges & bull stampede hops.
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

STATE_SALOON_BRAWL = 0
STATE_STAMPEDE = 1
STATE_HERO_HIT = 2
STATE_STAGE_CLEAR = 3
STATE_GAME_OVER = 4

MAX_BULLETS = 8
MAX_BANDITS = 3
MAX_BULLS = 3


class Game090SunsetRiders(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_SALOON_BRAWL
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.bandits_defeated = 0

        # Cowboy Hero
        self.px = 2.5
        self.py = 13.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = True
        self.is_sliding = False
        self.slide_timer = 0.0
        self.has_dual_guns = False
        self.has_rapid_fire = False
        self.fire_cooldown = 0.0

        # Sheriff Badge
        self.badge_x = 8.0
        self.badge_y = 8.0
        self.badge_active = True
        self.badge_type = 0  # 0 = Gold, 1 = Silver

        self.bullets: List[Dict[str, Any]] = []
        self.bandits: List[Dict[str, Any]] = []
        self.bulls: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 90

    @property
    def name(self) -> str:
        return "落日骑士"

    @property
    def english_name(self) -> str:
        return "Sunset Riders"

    @property
    def release_year(self) -> int:
        return 1991

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双枪铲地滑铲避弹与狂奔牛群借力跳跃"

    def get_name(self) -> str:
        return "Sunset Riders (1991)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.has_dual_guns = False
        self.has_rapid_fire = False
        self._reset_mission(hard_reset=True)

    def _reset_mission(self, hard_reset: bool = False) -> None:
        self.state = STATE_SALOON_BRAWL
        self.state_timer = 0.0
        self.bandits_defeated = 0

        self.px = 2.5
        self.py = 13.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = True
        self.is_sliding = False
        self.slide_timer = 0.0
        self.fire_cooldown = 0.0

        self.badge_x = 8.0
        self.badge_y = 8.0
        self.badge_active = True
        self.badge_type = 0 if (self.stage % 2 == 1) else 1

        self.bullets = [
            {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "is_enemy": False, "active": False}
            for _ in range(MAX_BULLETS)
        ]

        self.bandits = []
        init_bandit_pos = [(13.5, 13.0), (12.0, 8.0), (5.0, 8.0)]
        for i in range(MAX_BANDITS):
            self.bandits.append({
                "x": init_bandit_pos[i][0],
                "y": init_bandit_pos[i][1],
                "hp": 1,
                "shoot_timer": 0.8 + i * 0.7,
                "respawn_timer": 0.0,
                "active": True,
            })

        self.bulls = []
        for i in range(MAX_BULLS):
            self.bulls.append({
                "x": 18.0 + i * 5.0,
                "y": 13.0,
                "vx": -4.5,
                "active": False,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_HERO_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_mission(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.2:
                self.stage += 1
                self._reset_mission(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_bullets(dt)

        if self.state == STATE_STAMPEDE:
            self._update_bulls(dt)
        else:
            self._update_bandits(dt)
            if 3 <= self.bandits_defeated < 6:
                self.state = STATE_STAMPEDE
                self.state_timer = 0.0
                for i in range(MAX_BULLS):
                    self.bulls[i]["active"] = True
                    self.bulls[i]["x"] = 17.0 + i * 5.5

        self._check_combat()

        if self.bandits_defeated >= 6:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 2000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Slide Dodge (Down + Button A)
        if (buttons & KEY_DOWN) and (buttons & KEY_A) and self.on_ground:
            if not self.is_sliding:
                self.is_sliding = True
                self.slide_timer = 0.35

        if self.is_sliding:
            self.slide_timer -= dt
            self.px += self.facing * 9.0 * dt
            if self.slide_timer <= 0.0:
                self.is_sliding = False
        else:
            move_speed = 6.0
            if buttons & KEY_LEFT:
                self.px -= move_speed * dt
                self.facing = -1
            if buttons & KEY_RIGHT:
                self.px += move_speed * dt
                self.facing = 1

            if (buttons & KEY_B) and not (prev_buttons & KEY_B):
                if self.on_ground:
                    if (buttons & KEY_UP) and self.py >= 12.0:
                        self.vy = -14.0
                        self.on_ground = False
                    elif (buttons & KEY_DOWN) and self.py <= 9.0:
                        self.py += 1.0
                        self.vy = 1.0
                        self.on_ground = False
                    else:
                        self.vy = -5.8
                        self.on_ground = False

        prev_py = self.py
        if not self.on_ground:
            self.vy += 16.0 * dt
            self.py += self.vy * dt

        if self.py >= 13.0:
            self.py = 13.0
            self.vy = 0.0
            self.on_ground = True
        else:
            if self.vy >= 0.0 and prev_py <= 8.0 and self.py >= 8.0:
                if 3.0 <= self.px <= 14.5:
                    self.py = 8.0
                    self.vy = 0.0
                    self.on_ground = True

        self.px = max(1.0, min(15.0, self.px))

        # Shoot Revolver (Button A without Down)
        if (buttons & KEY_A) and not (buttons & KEY_DOWN):
            can_fire = (self.fire_cooldown <= 0.0) if self.has_rapid_fire else (not (prev_buttons & KEY_A) and self.fire_cooldown <= 0.0)
            if can_fire:
                self.fire_cooldown = 0.18 if self.has_rapid_fire else 0.28
                for b in self.bullets:
                    if not b["active"]:
                        b["active"] = True
                        b["is_enemy"] = False
                        b["x"] = self.px + self.facing * 0.8
                        b["y"] = self.py - 0.5
                        b["vx"] = self.facing * 12.0
                        b["vy"] = 0.0
                        break

                if self.has_dual_guns:
                    for b in self.bullets:
                        if not b["active"]:
                            b["active"] = True
                            b["is_enemy"] = False
                            b["x"] = self.px + self.facing * 0.8
                            b["y"] = self.py - 0.7
                            b["vx"] = self.facing * 10.0
                            b["vy"] = -5.0
                            break

        # Collect Badge
        if self.badge_active:
            dx = abs(self.px - self.badge_x)
            dy = abs(self.py - self.badge_y)
            if dx < 1.2 and dy < 1.2:
                self.badge_active = False
                self.score += 100
                if self.badge_type == 0:
                    self.has_dual_guns = True
                else:
                    self.has_rapid_fire = True

    def _update_bandits(self, dt: float) -> None:
        for idx, b in enumerate(self.bandits):
            if not b["active"]:
                if b["respawn_timer"] > 0.0:
                    b["respawn_timer"] -= dt
                else:
                    b["active"] = True
                    b["hp"] = 1
                    b["shoot_timer"] = 1.0 + (idx * 0.4)
                    b["x"] = 11.5 + (idx * 1.5) % 4.0
                    b["y"] = 13.0 if idx == 0 else 8.0
                continue

            b["shoot_timer"] -= dt
            if b["shoot_timer"] <= 0.0:
                b["shoot_timer"] = 1.5 + (idx * 0.3)
                for bl in self.bullets:
                    if not bl["active"]:
                        bl["active"] = True
                        bl["is_enemy"] = True
                        bl["x"] = b["x"] - 0.8
                        bl["y"] = b["y"] - 0.4
                        bl["vx"] = -6.5
                        bl["vy"] = 0.0
                        break

    def _update_bulls(self, dt: float) -> None:
        all_cleared = True
        for bull in self.bulls:
            if not bull["active"]:
                continue
            bull["x"] += bull["vx"] * dt
            if bull["x"] < -3.0:
                bull["active"] = False
            else:
                all_cleared = False

        if all_cleared:
            self.state = STATE_SALOON_BRAWL
            self.score += 500
            self.bandits_defeated = 4

    def _update_bullets(self, dt: float) -> None:
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < -1.0 or b["x"] > 17.0 or b["y"] < -1.0 or b["y"] > 17.0:
                b["active"] = False

    def _check_combat(self) -> None:
        # Player bullets vs Bandits
        for b in self.bullets:
            if not b["active"] or b["is_enemy"]:
                continue
            for bandit in self.bandits:
                if not bandit["active"]:
                    continue
                dx = abs(b["x"] - bandit["x"])
                dy = abs(b["y"] - bandit["y"])
                if dx < 1.1 and dy < 1.2:
                    b["active"] = False
                    bandit["hp"] -= 1
                    if bandit["hp"] <= 0:
                        bandit["active"] = False
                        bandit["respawn_timer"] = 2.0
                        self.score += 200
                        self.bandits_defeated += 1
                    break

        # Enemy bullets vs Hero
        for b in self.bullets:
            if not b["active"] or not b["is_enemy"]:
                continue
            dx = abs(b["x"] - self.px)
            dy = abs(b["y"] - self.py)
            if dx < 1.0:
                if self.is_sliding:
                    # Slide under bullet!
                    continue
                if dy < 1.1:
                    b["active"] = False
                    self.state = STATE_HERO_HIT
                    self.state_timer = 0.0
                    return

        # Stampeding Bulls vs Hero
        if self.state == STATE_STAMPEDE:
            for bull in self.bulls:
                if not bull["active"]:
                    continue
                dx = abs(bull["x"] - self.px)
                if dx < 1.3:
                    if 10.0 <= self.py <= 12.0 and self.vy >= 0.0:
                        # Bounce on back of bull
                        self.vy = -5.5
                        self.on_ground = False
                        self.score += 30
                    elif self.py > 12.0:
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

        # Sunset background
        for y in range(7):
            for x in range(16):
                set_pixel(x, y, 160 + y * 10, 80 + y * 5, 20)

        # Balcony
        for x in range(3, 15):
            set_pixel(x, 9, 139, 69, 19)
        set_pixel(4, 10, 100, 50, 15)
        set_pixel(4, 11, 100, 50, 15)
        set_pixel(4, 12, 100, 50, 15)
        set_pixel(13, 10, 100, 50, 15)
        set_pixel(13, 11, 100, 50, 15)
        set_pixel(13, 12, 100, 50, 15)

        # Ground
        for x in range(16):
            set_pixel(x, 14, 180, 130, 70)
            set_pixel(x, 15, 120, 80, 40)

        # Badge
        if self.badge_active:
            bx = int(round(self.badge_x))
            by = int(round(self.badge_y))
            if self.badge_type == 0:
                set_pixel(bx, by, 255, 220, 0)
            else:
                set_pixel(bx, by, 220, 230, 255)

        # Bulls
        if self.state == STATE_STAMPEDE:
            for bull in self.bulls:
                if not bull["active"]:
                    continue
                bx = int(round(bull["x"]))
                by = int(round(bull["y"]))
                set_pixel(bx, by, 110, 50, 20)
                set_pixel(bx + 1, by, 110, 50, 20)
                set_pixel(bx - 1, by, 80, 35, 15)
                set_pixel(bx - 1, by - 1, 230, 230, 200)

        # Bandits
        for b in self.bandits:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            set_pixel(bx, by, 160, 40, 40)
            set_pixel(bx, by - 1, 220, 160, 120)
            set_pixel(bx, by - 2, 60, 30, 10)
            set_pixel(bx - 1, by - 1, 40, 40, 40)

        # Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["is_enemy"]:
                set_pixel(bx, by, 255, 50, 0)
            else:
                set_pixel(bx, by, 255, 255, 100)

        # Cowboy
        px = int(round(self.px))
        py = int(round(self.py))

        if self.state == STATE_HERO_HIT:
            set_pixel(px, py, 255, 50, 0)
            set_pixel(px, py - 1, 255, 200, 0)
        else:
            if self.is_sliding:
                set_pixel(px, py, 30, 100, 220)
                set_pixel(px + self.facing, py, 220, 170, 130)
                set_pixel(px - self.facing, py, 200, 180, 100)
            else:
                set_pixel(px, py, 30, 100, 220)
                set_pixel(px, py - 1, 220, 170, 130)
                set_pixel(px, py - 2, 180, 120, 40)
                set_pixel(px + self.facing, py - 1, 240, 240, 240)
                if self.has_dual_guns:
                    set_pixel(px - self.facing, py - 1, 240, 240, 240)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 50, 50)
        if self.has_dual_guns:
            set_pixel(14, 0, 255, 220, 0)
        if self.has_rapid_fire:
            set_pixel(15, 0, 220, 230, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "stage": self.stage,
            "is_sliding": self.is_sliding,
            "has_dual_guns": self.has_dual_guns,
            "has_rapid_fire": self.has_rapid_fire,
            "bandits_defeated": self.bandits_defeated,
            "player_x": self.px,
            "player_y": self.py,
        }
