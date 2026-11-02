"""
Game #073: 影子战机 / 宇宙巡航舰 (Gradius 1985 / Konami)
Modular Power Meter Selection Hierarchy (Speed-Missile-Double-Laser-Option-Shield) & Big Core Boss Battle.
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

TIER_SPEED_UP = 1
TIER_MISSILE = 2
TIER_DOUBLE = 3
TIER_LASER = 4
TIER_OPTION = 5
TIER_SHIELD = 6

MAX_SHOTS = 4
MAX_MISSILES = 2
MAX_CAPSULES = 3
MAX_ENEMIES = 4
TRAIL_SIZE = 12


class Game073Gradius(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 9000
        self.lives = 3

        # Vic Viper state
        self.px = 2.0
        self.py = 8.0
        self.shoot_cooldown = 0.0
        self.missile_cooldown = 0.0

        self.meter_slot = 0
        self.has_speed_up = False
        self.has_missile = False
        self.has_double = False
        self.has_laser = False
        self.has_option = False
        self.shield_hp = 0

        self.trail: List[Dict[str, float]] = []
        self.trail_idx = 0
        self.enemies_defeated = 0

        # Boss Big Core
        self.boss_active = False
        self.boss_x = 13.0
        self.boss_y = 8.0
        self.boss_vy = 2.5
        self.boss_barrier_health = 4
        self.boss_core_health = 4
        self.boss_shoot_cooldown = 1.2

        self.shots: List[Dict[str, Any]] = []
        self.missiles: List[Dict[str, Any]] = []
        self.capsules: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 73

    @property
    def name(self) -> str:
        return "宇宙巡航舰"

    @property
    def english_name(self) -> str:
        return "Gradius"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "能量胶囊六阶选择升级槽 + 僚机残影随动射击 + 核心战舰能量护罩穿透"

    def get_name(self) -> str:
        return "Gradius (1985)"

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
        self.py = 8.0
        self.shoot_cooldown = 0.0
        self.missile_cooldown = 0.0
        self.meter_slot = 0
        self.has_speed_up = False
        self.has_missile = False
        self.has_double = False
        self.has_laser = False
        self.has_option = False
        self.shield_hp = 0
        self.trail_idx = 0
        self.enemies_defeated = 0
        self.boss_active = False
        self.boss_x = 13.0
        self.boss_y = 8.0
        self.boss_vy = 2.5
        self.boss_barrier_health = 4
        self.boss_core_health = 4
        self.boss_shoot_cooldown = 1.2

        self.trail = [{"x": self.px, "y": self.py} for _ in range(TRAIL_SIZE)]
        self.shots = []
        self.missiles = []
        self.capsules = []

        self.enemies = [
            {"x": 16.0, "y": 4.0, "vx": -3.0, "type": 0, "health": 1, "active": True},
            {"x": 18.0, "y": 7.0, "vx": -3.0, "type": 0, "health": 1, "active": True},
            {"x": 20.0, "y": 10.0, "vx": -3.0, "type": 0, "health": 1, "active": True},
            {"x": 15.0, "y": 13.0, "vx": -2.5, "type": 1, "health": 1, "active": True},
        ]

    def collect_capsule(self):
        self.meter_slot = (self.meter_slot % 6) + 1
        self.score += 100

    def activate_power_meter(self):
        if self.meter_slot == 0:
            return

        if self.meter_slot == TIER_SPEED_UP:
            self.has_speed_up = True
        elif self.meter_slot == TIER_MISSILE:
            self.has_missile = True
        elif self.meter_slot == TIER_DOUBLE:
            self.has_double = True
            self.has_laser = False
        elif self.meter_slot == TIER_LASER:
            self.has_laser = True
            self.has_double = False
        elif self.meter_slot == TIER_OPTION:
            self.has_option = True
        elif self.meter_slot == TIER_SHIELD:
            self.shield_hp = 2

        self.meter_slot = 0
        self.score += 200

    def shoot(self):
        if self.shoot_cooldown > 0.0:
            return

        # 1. Main cannon / Laser
        if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
            self.shots.append({
                "x": self.px + 1.2,
                "y": self.py,
                "vx": 16.0,
                "vy": 0.0,
                "is_laser": self.has_laser,
                "active": True,
            })

        # 2. Double 45-degree angled shot
        if self.has_double:
            if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
                self.shots.append({
                    "x": self.px + 0.8,
                    "y": self.py - 0.8,
                    "vx": 12.0,
                    "vy": -12.0,
                    "is_laser": False,
                    "active": True,
                })

        # 3. Option shot
        if self.has_option:
            opt_idx = (self.trail_idx + TRAIL_SIZE // 2) % TRAIL_SIZE
            if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
                self.shots.append({
                    "x": self.trail[opt_idx]["x"] + 1.0,
                    "y": self.trail[opt_idx]["y"],
                    "vx": 16.0,
                    "vy": 0.0,
                    "is_laser": self.has_laser,
                    "active": True,
                })

        # 4. Missile drop
        if self.has_missile and self.missile_cooldown <= 0.0:
            if len([m for m in self.missiles if m["active"]]) < MAX_MISSILES:
                self.missiles.append({
                    "x": self.px,
                    "y": self.py + 0.6,
                    "vx": 7.0,
                    "vy": 6.0,
                    "active": True,
                })
                self.missile_cooldown = 0.5

        self.shoot_cooldown = 0.22

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 1.8:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.px = 2.0
                    self.py = 8.0
                    self.shield_hp = 0
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
        if self.missile_cooldown > 0.0:
            self.missile_cooldown -= dt

        self.update_player(dt, buttons, prev_buttons)
        self.update_projectiles(dt)

        if self.boss_active:
            self.update_boss(dt)
        else:
            self.update_enemies(dt)
            if self.enemies_defeated >= 6:
                self.boss_active = True
                self.boss_x = 13.0
                self.boss_y = 8.0
                for e in self.enemies:
                    e["active"] = False

        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        speed = 8.5 if self.has_speed_up else 5.5

        if buttons & KEY_LEFT:
            self.px -= speed * dt
        if buttons & KEY_RIGHT:
            self.px += speed * dt
        if buttons & KEY_UP:
            self.py -= speed * dt
        if buttons & KEY_DOWN:
            self.py += speed * dt

        self.px = max(1.0, min(14.5, self.px))
        self.py = max(2.0, min(13.5, self.py))

        self.trail[self.trail_idx] = {"x": self.px, "y": self.py}
        self.trail_idx = (self.trail_idx + 1) % TRAIL_SIZE

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.shoot()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.activate_power_meter()

    def update_projectiles(self, dt: float):
        for s in self.shots:
            if not s["active"]:
                continue
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            if s["x"] > 15.5 or s["y"] < 1.0 or s["y"] > 14.5:
                s["active"] = False

        for m in self.missiles:
            if not m["active"]:
                continue
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
            if m["x"] > 15.5 or m["y"] > 14.0:
                m["active"] = False

        for c in self.capsules:
            if not c["active"]:
                continue
            c["x"] -= 2.0 * dt
            if c["x"] < 0.0:
                c["active"] = False

        self.shots = [s for s in self.shots if s["active"]]
        self.missiles = [m for m in self.missiles if m["active"]]
        self.capsules = [c for c in self.capsules if c["active"]]

    def update_enemies(self, dt: float):
        for i, e in enumerate(self.enemies):
            if not e["active"]:
                continue
            e["x"] += e["vx"] * dt
            e["y"] += math.sin(self.state_timer * 4.0 + i) * 2.0 * dt
            if e["x"] < -1.5:
                e["x"] = 17.0 + (i * 3.0)
                e["health"] = 1

    def update_boss(self, dt: float):
        self.boss_y += self.boss_vy * dt
        if self.boss_y < 4.5:
            self.boss_y = 4.5
            self.boss_vy = abs(self.boss_vy)
        elif self.boss_y > 10.5:
            self.boss_y = 10.5
            self.boss_vy = -abs(self.boss_vy)

        self.boss_shoot_cooldown -= dt
        if self.boss_shoot_cooldown <= 0.0:
            self.boss_shoot_cooldown = 1.3
            for dy in (-1, 1):
                if len([s for s in self.shots if s["active"]]) < MAX_SHOTS:
                    self.shots.append({
                        "x": self.boss_x - 1.5,
                        "y": self.boss_y + dy * 1.5,
                        "vx": -12.0,
                        "vy": 0.0,
                        "is_laser": True,
                        "active": True,
                    })

    def check_collisions(self):
        # 1. Player shots hit enemies & Boss
        for s in self.shots:
            if not s["active"] or s["vx"] < 0.0:
                continue

            if self.boss_active:
                if abs(s["x"] - (self.boss_x - 1.0)) < 1.4 and abs(s["y"] - self.boss_y) < 2.0:
                    s["active"] = False
                    if self.boss_barrier_health > 0:
                        self.boss_barrier_health -= 1
                        self.score += 50
                    else:
                        self.boss_core_health -= 1
                        self.score += 200
                        if self.boss_core_health <= 0:
                            self.boss_active = False
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                            self.score += 3500
                            if self.score > self.high_score:
                                self.high_score = self.score
                            return
            else:
                for e in self.enemies:
                    if not e["active"]:
                        continue
                    if abs(s["x"] - e["x"]) < 1.2 and abs(s["y"] - e["y"]) < 1.2:
                        if not s["is_laser"]:
                            s["active"] = False
                        e["health"] -= 1
                        if e["health"] <= 0:
                            e["active"] = False
                            self.enemies_defeated += 1
                            self.score += 150

                            if e["type"] == 0 and len([c for c in self.capsules if c["active"]]) < MAX_CAPSULES:
                                self.capsules.append({"x": e["x"], "y": e["y"], "active": True})

                            if self.enemies_defeated >= 6:
                                self.boss_active = True
                                self.boss_x = 13.0
                                self.boss_y = 8.0
                                for k in self.enemies:
                                    k["active"] = False
                        break

        # 2. Missiles hit enemies
        for m in self.missiles:
            if not m["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                if abs(m["x"] - e["x"]) < 1.2 and abs(m["y"] - e["y"]) < 1.2:
                    m["active"] = False
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 200
                    break

        # 3. Capsule collection
        for c in self.capsules:
            if not c["active"]:
                continue
            if abs(self.px - c["x"]) < 1.3 and abs(self.py - c["y"]) < 1.3:
                c["active"] = False
                self.collect_capsule()
                break

        # 4. Enemy shots hit Vic Viper
        for s in self.shots:
            if not s["active"] or s["vx"] > 0.0:
                continue
            if abs(self.px - s["x"]) < 1.0 and abs(self.py - s["y"]) < 1.0:
                s["active"] = False
                if self.shield_hp > 0:
                    self.shield_hp -= 1
                else:
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # Direct enemy collision
        for e in self.enemies:
            if not e["active"]:
                continue
            if abs(self.px - e["x"]) < 1.0 and abs(self.py - e["y"]) < 1.0:
                if self.shield_hp > 0:
                    self.shield_hp -= 1
                    e["active"] = False
                else:
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

        # 1. Starfield
        for i in range(6):
            sx = int(self.state_timer * 6.0 + i * 5) % 16
            sy = 2 + (i * 2)
            set_pixel(15 - sx, sy, 100, 120, 160)

        # 2. Power Meter HUD (y=0)
        for slot in range(1, 7):
            hx = 2 + (slot - 1) * 2
            if self.meter_slot == slot:
                blink = (int(self.state_timer * 12.0) % 2 == 0)
                set_pixel(hx, 0, 255 if blink else 40, 220, 30 if blink else 255)
            else:
                set_pixel(hx, 0, 50, 60, 80)

        # 3. Capsules
        for c in self.capsules:
            if not c["active"]:
                continue
            cx = int(round(c["x"]))
            cy = int(round(c["y"]))
            set_pixel(cx, cy, 255, 120, 20)
            set_pixel(cx, cy - 1, 255, 220, 50)

        # 4. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["type"] == 0:
                set_pixel(ex, ey, 240, 30, 30)
                set_pixel(ex + 1, ey, 255, 100, 30)
            else:
                set_pixel(ex, ey, 140, 140, 160)
                set_pixel(ex - 1, ey, 255, 200, 40)

        # 5. Big Core Boss
        if self.boss_active:
            bx = int(round(self.boss_x))
            by = int(round(self.boss_y))
            for dx in (-1, 0, 1):
                set_pixel(bx + dx, by - 2, 160, 160, 180)
                set_pixel(bx + dx, by + 2, 160, 160, 180)

            if self.boss_barrier_health > 0:
                set_pixel(bx - 1, by, 60, 180, 255)
                set_pixel(bx - 1, by - 1, 60, 180, 255)
                set_pixel(bx - 1, by + 1, 60, 180, 255)

            cr = 255 if self.boss_barrier_health <= 0 else 40
            cg = 30 if self.boss_barrier_health <= 0 else 100
            cb = 30 if self.boss_barrier_health <= 0 else 255
            set_pixel(bx, by, cr, cg, cb)

        # 6. Projectiles
        for s in self.shots:
            if not s["active"]:
                continue
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            if s["is_laser"]:
                set_pixel(sx, sy, 50, 240, 255)
                set_pixel(sx - 1, sy, 50, 200, 255)
            else:
                set_pixel(sx, sy, 255, 240, 100)

        for m in self.missiles:
            if not m["active"]:
                continue
            set_pixel(int(round(m["x"])), int(round(m["y"])), 255, 120, 0)

        # 7. Option Follower
        if self.has_option:
            opt_idx = (self.trail_idx + TRAIL_SIZE // 2) % TRAIL_SIZE
            ox = int(round(self.trail[opt_idx]["x"]))
            oy = int(round(self.trail[opt_idx]["y"]))
            set_pixel(ox, oy, 255, 140, 20)

        # 8. Vic Viper
        if self.state != STATE_DEAD:
            vx = int(round(self.px))
            vy = int(round(self.py))

            if self.shield_hp > 0:
                set_pixel(vx + 2, vy, 100, 200, 255)
                set_pixel(vx + 2, vy - 1, 100, 200, 255)
                set_pixel(vx + 2, vy + 1, 100, 200, 255)

            set_pixel(vx, vy, 240, 240, 255)
            set_pixel(vx + 1, vy, 40, 100, 240)
            set_pixel(vx - 1, vy - 1, 220, 30, 30)
            set_pixel(vx - 1, vy + 1, 220, 30, 30)
            set_pixel(vx - 1, vy, 255, 160, 40)
        else:
            vx = int(round(self.px))
            vy = int(round(self.py))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    set_pixel(vx + dx, vy + dy, 255, 120, 30)

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
            "meter_slot": self.meter_slot,
            "has_speed_up": self.has_speed_up,
            "has_missile": self.has_missile,
            "has_double": self.has_double,
            "has_laser": self.has_laser,
            "has_option": self.has_option,
            "shield_hp": self.shield_hp,
            "boss_active": self.boss_active,
        }
