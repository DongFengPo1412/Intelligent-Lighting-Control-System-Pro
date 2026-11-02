"""
Game #066: 兵蜂 / 铃铛射击 (TwinBee 1985 / Konami)
Cute-'Em-Up Aerial Shooter: Bell Juggling & Color-Morph Upgrades, Ground Bombing, and Angel Ambulance Rescue.
"""

import math
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

STATE_START = 0
STATE_PLAYING = 1
STATE_DEAD = 2
STATE_VICTORY = 3

BELL_YELLOW = 0  # Bonus Points
BELL_WHITE = 1   # Speed & Twin Gun
BELL_BLUE = 2    # Energy Shield
BELL_RED = 3     # Shadow Option Clone

MAX_SHOTS = 4
MAX_BOMBS = 2
MAX_ENEMIES = 4
MAX_GROUND_TARGETS = 3
MAX_BELLS = 2


class Game066TwinBee(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 6000
        self.lives = 3

        # TwinBee ship state
        self.px = 7.5
        self.py = 13.0
        self.shoot_cooldown = 0.0
        self.bomb_cooldown = 0.0
        self.has_twin_gun = False
        self.has_shield = False
        self.has_option_clone = False
        self.has_arms = True

        # Ambulance angel
        self.ambulance_active = False
        self.amb_x = 7.5
        self.amb_y = -2.0

        self.enemies_defeated = 0
        self.cloud_timer = 2.0

        self.shots: List[Dict[str, Any]] = []
        self.bombs: List[Dict[str, Any]] = []
        self.bells: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.ground_targets: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 66

    @property
    def name(self) -> str:
        return "兵蜂"

    @property
    def english_name(self) -> str:
        return "TwinBee"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "射击击打空中铃铛颠球变色升级 + 地面炸弹投掷与断臂救援天使"

    def get_name(self) -> str:
        return "TwinBee (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.init_stage()

    def init_stage(self):
        self.px = 7.5
        self.py = 13.0
        self.shoot_cooldown = 0.0
        self.bomb_cooldown = 0.0
        self.has_twin_gun = False
        self.has_shield = False
        self.has_option_clone = False
        self.has_arms = True
        self.ambulance_active = False
        self.amb_x = 7.5
        self.amb_y = -2.0
        self.enemies_defeated = 0
        self.cloud_timer = 2.0

        self.shots = []
        self.bombs = []
        self.bells = []

        self.enemies = [
            {"x": 2.0, "y": -2.0, "vx": 2.0, "vy": 2.5, "type": 0, "active": True},
            {"x": 12.0, "y": -5.0, "vx": -2.0, "vy": 2.2, "type": 0, "active": True},
            {"x": 6.0, "y": -9.0, "vx": 1.5, "vy": 2.0, "type": 1, "active": True},
            {"x": 9.0, "y": -12.0, "vx": -1.8, "vy": 2.0, "type": 1, "active": True},
        ]

        self.ground_targets = [
            {"x": 4.0, "y": 5.0, "type": 0, "active": True},
            {"x": 11.0, "y": 2.0, "type": 1, "active": True},
            {"x": 7.0, "y": -4.0, "type": 0, "active": True},
        ]

    def spawn_bell(self, x: float, y: float):
        if len([b for b in self.bells if b["active"]]) < MAX_BELLS:
            self.bells.append({
                "x": x,
                "y": y,
                "vy": 1.0,
                "hit_count": 0,
                "color_type": BELL_YELLOW,
                "active": True,
            })

    def shoot_air(self):
        if self.shoot_cooldown > 0.0:
            return

        if self.has_twin_gun:
            for dx in (-1, 1):
                if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
                    self.shots.append({
                        "x": self.px + dx * 0.8,
                        "y": self.py - 1.0,
                        "vx": 0.0,
                        "vy": -16.0,
                        "active": True,
                    })
        else:
            if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
                self.shots.append({
                    "x": self.px,
                    "y": self.py - 1.0,
                    "vx": 0.0,
                    "vy": -16.0,
                    "active": True,
                })

        if self.has_option_clone:
            if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
                self.shots.append({
                    "x": self.px - 2.0,
                    "y": self.py + 0.5,
                    "vx": 0.0,
                    "vy": -16.0,
                    "active": True,
                })

        self.shoot_cooldown = 0.22

    def drop_ground_bomb(self):
        if not self.has_arms or self.bomb_cooldown > 0.0:
            return

        if len([b for b in self.bombs if b["active"]]) < MAX_BOMBS:
            self.bombs.append({
                "x": self.px,
                "y": self.py + 0.5,
                "vx": 0.0,
                "vy": 5.0,
                "active": True,
            })

        self.bomb_cooldown = 0.40

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.init_stage()
                else:
                    self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_stage()
            return

        if self.shoot_cooldown > 0.0:
            self.shoot_cooldown -= dt
        if self.bomb_cooldown > 0.0:
            self.bomb_cooldown -= dt

        self.cloud_timer -= dt
        if self.cloud_timer <= 0.0:
            self.cloud_timer = 5.0
            import random
            self.spawn_bell(3.0 + random.randint(0, 9), 1.0)

        self.update_player(dt, buttons, prev_buttons)
        self.update_projectiles(dt)
        self.update_bells(dt)
        self.update_enemies(dt)
        self.update_ambulance(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        speed = 8.0 if self.has_twin_gun else 6.5

        if buttons & KEY_LEFT:
            self.px -= speed * dt
        if buttons & KEY_RIGHT:
            self.px += speed * dt
        if buttons & KEY_UP:
            self.py -= speed * dt
        if buttons & KEY_DOWN:
            self.py += speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(2.0, min(14.5, self.py))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.shoot_air()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.drop_ground_bomb()

    def update_projectiles(self, dt: float):
        for s in self.shots:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            if s["y"] < 0.0:
                s["active"] = False

        for b in self.bombs:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["y"] > 15.5:
                b["active"] = False

        self.shots = [s for s in self.shots if s["active"]]
        self.bombs = [b for b in self.bombs if b["active"]]

    def update_bells(self, dt: float):
        for b in self.bells:
            if not b["active"]:
                continue
            b["y"] += b["vy"] * dt
            b["vy"] = min(3.5, b["vy"] + 8.0 * dt)
            if b["y"] > 16.0:
                b["active"] = False

        self.bells = [b for b in self.bells if b["active"]]

    def update_enemies(self, dt: float):
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue
            e["y"] += e["vy"] * dt
            e["x"] += math.sin(self.state_timer * 4.0 + i) * 3.0 * dt
            if e["y"] > 16.0:
                e["y"] = -2.0
                e["x"] = 2.0 + (i * 3.5)

        for g in self.ground_targets:
            if not g["active"]:
                continue
            g["y"] += 1.5 * dt
            if g["y"] > 16.0:
                g["y"] = -3.0
                import random
                g["x"] = 3.0 + random.randint(0, 9)
                g["active"] = True

    def update_ambulance(self, dt: float):
        if not self.ambulance_active:
            return
        self.amb_y += 2.5 * dt
        if self.amb_y > 16.0:
            self.ambulance_active = False

    def check_collisions(self):
        # 1. Air shots hit Bells
        for s in self.shots:
            if not s["active"]:
                continue
            for b in self.bells:
                if not b["active"]:
                    continue
                if abs(s["x"] - b["x"]) < 1.2 and abs(s["y"] - b["y"]) < 1.2:
                    s["active"] = False
                    b["vy"] = -4.5
                    b["hit_count"] += 1
                    self.score += 20

                    if b["hit_count"] >= 15:
                        b["color_type"] = BELL_RED
                    elif b["hit_count"] >= 10:
                        b["color_type"] = BELL_BLUE
                    elif b["hit_count"] >= 5:
                        b["color_type"] = BELL_WHITE
                    else:
                        b["color_type"] = BELL_YELLOW
                    break

        # 2. Air shots hit Aerial enemies
        for s in self.shots:
            if not s["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(s["x"] - e["x"]) < 1.2 and abs(s["y"] - e["y"]) < 1.2:
                    s["active"] = False
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 150
                    if self.enemies_defeated >= 8:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 2500
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
                    break

        # 3. Ground bombs hit Ground Targets
        for b in self.bombs:
            if not b["active"]:
                continue
            for g in self.ground_targets:
                if not g["active"]:
                    continue
                if abs(b["x"] - g["x"]) < 1.4 and abs(b["y"] - g["y"]) < 1.4:
                    b["active"] = False
                    g["active"] = False
                    self.score += 300
                    break

        # 4. Player collects Bell
        for b in self.bells:
            if not b["active"]:
                continue
            if abs(self.px - b["x"]) < 1.3 and abs(self.py - b["y"]) < 1.3:
                b["active"] = False
                if b["color_type"] == BELL_YELLOW:
                    self.score += 500
                elif b["color_type"] == BELL_WHITE:
                    self.has_twin_gun = True
                    self.score += 1000
                elif b["color_type"] == BELL_BLUE:
                    self.has_shield = True
                    self.score += 1000
                elif b["color_type"] == BELL_RED:
                    self.has_option_clone = True
                    self.score += 1000
                if self.score > self.high_score:
                    self.high_score = self.score
                break

        # 5. Player touches Ambulance Angel
        if self.ambulance_active:
            if abs(self.px - self.amb_x) < 1.4 and abs(self.py - self.amb_y) < 1.4:
                self.ambulance_active = False
                self.has_arms = True
                self.score += 500

        # 6. Player collides with Aerial Enemy
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(self.px - e["x"]) < 1.1 and abs(self.py - e["y"]) < 1.1:
                e["active"] = False
                if self.has_shield:
                    self.has_shield = False
                elif self.has_arms:
                    self.has_arms = False
                    self.ambulance_active = True
                    self.amb_x = self.px
                    self.amb_y = 0.0
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return
                break

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Pastoral Green land / Sky borders
        for y in range(16):
            for x in range(16):
                if 3 <= x <= 12:
                    set_pixel(x, y, 30, 140, 50)
                else:
                    set_pixel(x, y, 20, 80, 180)

        # Ground targets
        for g in self.ground_targets:
            if not g["active"]:
                continue
            gx = int(round(g["x"]))
            gy = int(round(g["y"]))
            if g["type"] == 0:
                set_pixel(gx, gy, 230, 30, 30)
                set_pixel(gx, gy - 1, 30, 200, 30)
            else:
                set_pixel(gx, gy, 120, 120, 130)
                set_pixel(gx, gy - 1, 200, 200, 50)

        # Bells
        for b in self.bells:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))

            br, bg, bb = 255, 215, 0
            if b["color_type"] == BELL_WHITE:
                br, bg, bb = 255, 255, 255
            elif b["color_type"] == BELL_BLUE:
                br, bg, bb = 50, 120, 255
            elif b["color_type"] == BELL_RED:
                br, bg, bb = 255, 40, 40

            set_pixel(bx, by, br, bg, bb)
            set_pixel(bx - 1, by + 1, max(0, br - 40), max(0, bg - 40), bb)
            set_pixel(bx + 1, by + 1, max(0, br - 40), max(0, bg - 40), bb)

        # Aerial Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["type"] == 0:
                set_pixel(ex, ey, 255, 60, 80)
                set_pixel(ex, ey - 1, 40, 220, 40)
            else:
                set_pixel(ex, ey, 220, 180, 40)
                set_pixel(ex - 1, ey, 180, 140, 30)
                set_pixel(ex + 1, ey, 180, 140, 30)

        # Ambulance Angel
        if self.ambulance_active:
            ax = int(round(self.amb_x))
            ay = int(round(self.amb_y))
            set_pixel(ax, ay, 255, 255, 255)
            set_pixel(ax, ay - 1, 255, 220, 0)
            set_pixel(ax - 1, ay, 255, 50, 50)
            set_pixel(ax + 1, ay, 255, 50, 50)

        # Projectiles
        for s in self.shots:
            if not s["active"]:
                continue
            set_pixel(int(round(s["x"])), int(round(s["y"])), 255, 255, 100)

        for b in self.bombs:
            if not b["active"]:
                continue
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 120, 0)

        # Player TwinBee
        if self.state != STATE_DEAD:
            px = int(round(self.px))
            py = int(round(self.py))

            if self.has_shield:
                set_pixel(px - 1, py - 2, 80, 180, 255)
                set_pixel(px + 1, py - 2, 80, 180, 255)
                set_pixel(px - 2, py, 80, 180, 255)
                set_pixel(px + 2, py, 80, 180, 255)

            set_pixel(px, py, 40, 100, 240)
            set_pixel(px, py - 1, 255, 220, 50)

            if self.has_arms:
                set_pixel(px - 1, py, 255, 255, 255)
                set_pixel(px + 1, py, 255, 255, 255)

            if self.has_option_clone:
                set_pixel(px - 2, py + 1, 150, 60, 200)
        else:
            px = int(round(self.px))
            py = int(round(self.py))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    set_pixel(px + dx, py + dy, 255, 150, 30)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "px": self.px,
            "py": self.py,
            "has_shield": self.has_shield,
            "has_twin_gun": self.has_twin_gun,
            "has_option_clone": self.has_option_clone,
            "has_arms": self.has_arms,
            "enemies_defeated": self.enemies_defeated,
        }
