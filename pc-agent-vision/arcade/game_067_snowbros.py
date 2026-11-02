"""
Game #067: 雪人兄弟 (Snow Bros. 1990 / Toaplan)
Snow Ball Packing & Bowling-Ball Kicking Platformer with Speed/Power Potions.
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

STATE_START = 0
STATE_PLAYING = 1
STATE_DEAD = 2
STATE_VICTORY = 3

SNOW_NONE = 0
SNOW_LIGHT = 1
SNOW_MEDIUM = 2
SNOW_FULL_BALL = 3

MAX_SHOTS = 3
MAX_ENEMIES = 4
MAX_POTIONS = 2


def is_on_solid(x: float, y: float) -> bool:
    ix = int(round(x))
    iy = int(round(y))
    if iy == 14:
        return True
    if iy == 9 and ((1 <= ix <= 6) or (9 <= ix <= 14)):
        return True
    if iy == 4 and (4 <= ix <= 11):
        return True
    return False


class Game067SnowBros(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 5500
        self.lives = 3

        # Player snowman state
        self.px = 2.0
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.facing = 1
        self.shoot_cooldown = 0.0

        self.has_speed_potion = False
        self.has_power_potion = False
        self.has_range_potion = False
        self.enemies_defeated = 0

        self.shots: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.potions: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 67

    @property
    def name(self) -> str:
        return "雪人兄弟"

    @property
    def english_name(self) -> str:
        return "Snow Bros."

    @property
    def release_year(self) -> int:
        return 1990

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "发射堆积雪球 + 沿途推滚保龄球式全屏扫荡清怪 + 红蓝黄药水能力增强"

    def get_name(self) -> str:
        return "Snow Bros. (1990)"

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
        self.px = 2.0
        self.py = 14.0
        self.pvy = 0.0
        self.on_ground = True
        self.facing = 1
        self.shoot_cooldown = 0.0
        self.has_speed_potion = False
        self.has_power_potion = False
        self.has_range_potion = False
        self.enemies_defeated = 0

        self.shots = []
        self.potions = []

        self.enemies = [
            {"x": 12.0, "y": 14.0, "vx": -2.5, "snow_stage": SNOW_NONE, "is_rolling": False, "roll_vx": 0.0, "melt_timer": 0.0, "active": True},
            {"x": 3.0, "y": 9.0, "vx": 2.5, "snow_stage": SNOW_NONE, "is_rolling": False, "roll_vx": 0.0, "melt_timer": 0.0, "active": True},
            {"x": 11.0, "y": 9.0, "vx": -2.5, "snow_stage": SNOW_NONE, "is_rolling": False, "roll_vx": 0.0, "melt_timer": 0.0, "active": True},
            {"x": 7.0, "y": 4.0, "vx": 2.2, "snow_stage": SNOW_NONE, "is_rolling": False, "roll_vx": 0.0, "melt_timer": 0.0, "active": True},
        ]

    def throw_snow(self):
        if self.shoot_cooldown > 0.0:
            return

        if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
            self.shots.append({
                "x": self.px + self.facing * 0.8,
                "y": self.py,
                "vx": self.facing * (16.0 if self.has_range_potion else 11.0),
                "active": True,
            })

        self.shoot_cooldown = 0.22

    def jump(self):
        if self.on_ground:
            self.pvy = -9.2
            self.on_ground = False

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

        self.update_player(dt, buttons, prev_buttons)
        self.update_projectiles(dt)
        self.update_enemies(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 7.5 if self.has_speed_potion else 5.0

        if buttons & KEY_LEFT:
            self.px -= move_speed * dt
            self.facing = -1
        if buttons & KEY_RIGHT:
            self.px += move_speed * dt
            self.facing = 1

        self.px = max(0.5, min(14.5, self.px))

        # Gravity & platforms
        self.pvy += 24.0 * dt
        self.py += self.pvy * dt

        self.on_ground = False
        if self.pvy >= 0.0:
            if self.py >= 14.0:
                self.py = 14.0
                self.pvy = 0.0
                self.on_ground = True
            elif 9.0 <= self.py <= 9.6 and ((0.8 <= self.px <= 6.2) or (8.8 <= self.px <= 14.2)):
                self.py = 9.0
                self.pvy = 0.0
                self.on_ground = True
            elif 4.0 <= self.py <= 4.6 and (3.8 <= self.px <= 11.2):
                self.py = 4.0
                self.pvy = 0.0
                self.on_ground = True

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.jump()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.throw_snow()

    def update_projectiles(self, dt: float):
        for s in self.shots:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            if s["x"] < 0.0 or s["x"] > 15.5:
                s["active"] = False
        self.shots = [s for s in self.shots if s["active"]]

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"]:
                continue

            if e["is_rolling"]:
                e["x"] += e["roll_vx"] * dt

                if e["x"] <= 1.0:
                    e["x"] = 1.0
                    e["roll_vx"] = abs(e["roll_vx"])
                elif e["x"] >= 14.0:
                    e["x"] = 14.0
                    e["roll_vx"] = -abs(e["roll_vx"])

                if not is_on_solid(e["x"], e["y"]):
                    e["y"] += 12.0 * dt
                    if e["y"] >= 14.0:
                        e["y"] = 14.0

                e["melt_timer"] -= dt
                if e["melt_timer"] <= 0.0:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 500
                    if self.enemies_defeated >= 6:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 2500
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return
            elif e["snow_stage"] == SNOW_FULL_BALL:
                e["melt_timer"] -= dt
                if e["melt_timer"] <= 0.0:
                    e["snow_stage"] = SNOW_MEDIUM
                    e["melt_timer"] = 2.0
            else:
                spd = 1.2 if e["snow_stage"] == SNOW_LIGHT else 2.6
                e["x"] += (spd if e["vx"] > 0 else -spd) * dt

                if e["x"] <= 1.0:
                    e["x"] = 1.0
                    e["vx"] = abs(e["vx"])
                elif e["x"] >= 14.0:
                    e["x"] = 14.0
                    e["vx"] = -abs(e["vx"])

                if e["snow_stage"] > SNOW_NONE:
                    e["melt_timer"] -= dt
                    if e["melt_timer"] <= 0.0:
                        e["snow_stage"] -= 1
                        e["melt_timer"] = 2.0

    def check_collisions(self):
        # 1. Snow shots hit enemies
        for s in self.shots:
            if not s["active"]:
                continue
            for e in self.enemies:
                if not e["active"] or e["is_rolling"]:
                    continue
                if abs(s["x"] - e["x"]) < 1.2 and abs(s["y"] - e["y"]) < 1.2:
                    s["active"] = False
                    boost = 2 if self.has_power_potion else 1
                    e["snow_stage"] = min(SNOW_FULL_BALL, e["snow_stage"] + boost)
                    e["melt_timer"] = 3.5
                    self.score += 50
                    break

        # 2. Rolling snowball sweeps enemies
        for r in self.enemies:
            if not r["active"] or not r["is_rolling"]:
                continue
            for e in self.enemies:
                if e is r or not e["active"]:
                    continue
                if abs(r["x"] - e["x"]) < 1.4 and abs(r["y"] - e["y"]) < 1.4:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 300

                    if len([p for p in self.potions if p["active"]]) < MAX_POTIONS:
                        self.potions.append({
                            "x": e["x"],
                            "y": e["y"],
                            "type": self.enemies_defeated % 3,
                            "active": True,
                        })

                    if self.enemies_defeated >= 6:
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 2500
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

        # 3. Player kicks giant snowball
        for e in self.enemies:
            if not e["active"] or e["is_rolling"]:
                continue
            if e["snow_stage"] == SNOW_FULL_BALL:
                if abs(self.px - e["x"]) < 1.4 and abs(self.py - e["y"]) < 1.4:
                    e["is_rolling"] = True
                    e["roll_vx"] = 12.0 if self.px < e["x"] else -12.0
                    e["melt_timer"] = 2.5
                    self.score += 200

        # 4. Player collects Potion
        for p in self.potions:
            if not p["active"]:
                continue
            if abs(self.px - p["x"]) < 1.2 and abs(self.py - p["y"]) < 1.2:
                p["active"] = False
                if p["type"] == 0:
                    self.has_speed_potion = True
                elif p["type"] == 1:
                    self.has_power_potion = True
                else:
                    self.has_range_potion = True
                self.score += 500
                if self.score > self.high_score:
                    self.high_score = self.score

        # 5. Unfrozen enemy hurts player
        for e in self.enemies:
            if not e["active"] or e["is_rolling"] or e["snow_stage"] >= SNOW_MEDIUM:
                continue
            if abs(self.px - e["x"]) < 0.9 and abs(self.py - e["y"]) < 0.9:
                self.lives -= 1
                self.state = STATE_DEAD
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

        # 1. Background
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 10, 15, 35)

        # 2. Platforms
        for x in range(16):
            set_pixel(x, 15, 60, 140, 200)
        for x in range(1, 7):
            set_pixel(x, 10, 60, 140, 200)
        for x in range(9, 15):
            set_pixel(x, 10, 60, 140, 200)
        for x in range(4, 12):
            set_pixel(x, 5, 60, 140, 200)

        # 3. Potions
        for p in self.potions:
            if not p["active"]:
                continue
            px = int(round(p["x"]))
            py = int(round(p["y"]))
            if p["type"] == 0:
                set_pixel(px, py, 255, 30, 30)
            elif p["type"] == 1:
                set_pixel(px, py, 40, 80, 255)
            else:
                set_pixel(px, py, 255, 230, 20)

        # 4. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))

            if e["is_rolling"]:
                for dy in (-1, 0):
                    for dx in (-1, 0):
                        set_pixel(ex + dx, ey + dy, 240, 250, 255)
            elif e["snow_stage"] == SNOW_FULL_BALL:
                for dy in (-1, 0):
                    for dx in (-1, 0):
                        set_pixel(ex + dx, ey + dy, 210, 240, 255)
            elif e["snow_stage"] == SNOW_MEDIUM:
                set_pixel(ex, ey, 220, 240, 255)
                set_pixel(ex, ey - 1, 255, 60, 60)
            elif e["snow_stage"] == SNOW_LIGHT:
                set_pixel(ex, ey, 255, 120, 120)
                set_pixel(ex, ey - 1, 255, 60, 60)
            else:
                set_pixel(ex, ey, 240, 30, 30)
                set_pixel(ex, ey - 1, 255, 80, 50)

        # 5. Projectiles
        for s in self.shots:
            if not s["active"]:
                continue
            set_pixel(int(round(s["x"])), int(round(s["y"])), 255, 255, 255)

        # 6. Player Snowman
        if self.state != STATE_DEAD:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px, py, 250, 250, 255)
            set_pixel(px, py - 1, 50, 120, 255)
            set_pixel(px + self.facing, py, 255, 120, 40)
        else:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px - 1, py, 180, 220, 255)
            set_pixel(px,     py, 180, 220, 255)
            set_pixel(px + 1, py, 180, 220, 255)

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
            "enemies_defeated": self.enemies_defeated,
            "has_speed_potion": self.has_speed_potion,
            "has_power_potion": self.has_power_potion,
            "has_range_potion": self.has_range_potion,
        }
