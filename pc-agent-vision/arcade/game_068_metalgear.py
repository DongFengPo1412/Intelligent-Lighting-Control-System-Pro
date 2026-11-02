"""
Game #068: 经典潜行刺杀 / 燃烧要塞 (Metal Gear 1987 / Konami)
Tactical Espionage Action: Cardboard Box Camouflage, Line-of-Sight Stealth, Silenced CQC & Keycard Infiltration.
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

ALERT_NORMAL = 0
ALERT_CAUTION = 1
ALERT_EVASION = 2

MAX_GUARDS = 3
MAX_DARTS = 2


def is_wall_or_crate(x: int, y: int, door_open: bool) -> bool:
    if x <= 0 or x >= 15 or y <= 0 or y >= 15:
        return True
    if (x == 7 or x == 8) and y == 2:
        return not door_open
    if (x == 4 or x == 5) and (4 <= y <= 6):
        return True
    if (x == 10 or x == 11) and (7 <= y <= 9):
        return True
    if y == 2 and x != 7 and x != 8:
        return True
    return False


class Game068MetalGear(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 6500
        self.lives = 3

        # Solid Snake state
        self.px = 2.0
        self.py = 13.0
        self.player_dir = 0
        self.in_box = False
        self.is_moving = False
        self.dart_cooldown = 0.0
        self.has_keycard = False

        self.alert_level = ALERT_NORMAL
        self.alert_timer = 0.0
        self.guards_neutralized = 0

        self.guards: List[Dict[str, Any]] = []
        self.darts: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 68

    @property
    def name(self) -> str:
        return "燃烧要塞"

    @property
    def english_name(self) -> str:
        return "Metal Gear"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "战术谍报潜行 + 敌人视线锥体暗影侦测 + 纸箱掩护与消音背刺"

    def get_name(self) -> str:
        return "Metal Gear (1987)"

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
        self.py = 13.0
        self.player_dir = 0
        self.in_box = False
        self.is_moving = False
        self.dart_cooldown = 0.0
        self.has_keycard = False
        self.alert_level = ALERT_NORMAL
        self.alert_timer = 0.0
        self.guards_neutralized = 0

        self.darts = []

        self.guards = [
            {"x": 6.0, "y": 5.0, "dir": 1, "patrol_timer": 0.0, "alert": False, "active": True},
            {"x": 9.0, "y": 9.0, "dir": 2, "patrol_timer": 0.0, "alert": False, "active": True},
            {"x": 12.0, "y": 11.0, "dir": 3, "patrol_timer": 0.0, "alert": False, "active": True},
        ]

    def toggle_cardboard_box(self):
        self.in_box = not self.in_box

    def fire_silenced_dart(self):
        if self.dart_cooldown > 0.0 or self.in_box:
            return

        if len([d for d in self.darts if d["active"]]) < MAX_DARTS:
            spd = 12.0
            vx, vy = 0.0, 0.0
            if self.player_dir == 0:
                vy = -spd
            elif self.player_dir == 1:
                vx = spd
            elif self.player_dir == 2:
                vy = spd
            else:
                vx = -spd

            self.darts.append({
                "x": self.px,
                "y": self.py,
                "vx": vx,
                "vy": vy,
                "active": True,
            })

        self.dart_cooldown = 0.35

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

        if self.dart_cooldown > 0.0:
            self.dart_cooldown -= dt

        if self.alert_level > ALERT_NORMAL:
            self.alert_timer -= dt
            if self.alert_timer <= 0.0:
                self.alert_level = ALERT_NORMAL
                for g in self.guards:
                    g["alert"] = False

        self.update_player(dt, buttons, prev_buttons)
        self.update_guards(dt)
        self.update_darts(dt)
        self.check_line_of_sight()
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        move_speed = 2.5 if self.in_box else 5.0
        next_x = self.px
        next_y = self.py
        self.is_moving = False

        if buttons & KEY_UP:
            next_y -= move_speed * dt
            self.player_dir = 0
            self.is_moving = True
        elif buttons & KEY_DOWN:
            next_y += move_speed * dt
            self.player_dir = 2
            self.is_moving = True
        elif buttons & KEY_LEFT:
            next_x -= move_speed * dt
            self.player_dir = 3
            self.is_moving = True
        elif buttons & KEY_RIGHT:
            next_x += move_speed * dt
            self.player_dir = 1
            self.is_moving = True

        if not is_wall_or_crate(int(round(next_x)), int(round(next_y)), self.has_keycard):
            self.px = next_x
            self.py = next_y

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(1.0, min(14.0, self.py))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_silenced_dart()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.toggle_cardboard_box()

        # Keycard pickup
        if not self.has_keycard and abs(self.px - 13.0) < 0.9 and abs(self.py - 13.0) < 0.9:
            self.has_keycard = True
            self.score += 500

        # Goal nuclear computer reached
        if self.has_keycard and abs(self.px - 7.5) < 1.0 and self.py <= 1.5:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 3000
            if self.score > self.high_score:
                self.high_score = self.score

    def update_guards(self, dt: float):
        for g in self.guards:
            if not g["active"]:
                continue

            if g["alert"]:
                dx = self.px - g["x"]
                dy = self.py - g["y"]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0.1:
                    spd = 4.0
                    g["x"] += (dx / dist) * spd * dt
                    g["y"] += (dy / dist) * spd * dt
            else:
                g["patrol_timer"] += dt
                if g["patrol_timer"] > 2.2:
                    g["patrol_timer"] = 0.0
                    g["dir"] = (g["dir"] + 1) % 4

                spd = 2.0
                nx = g["x"]
                ny = g["y"]
                if g["dir"] == 0:
                    ny -= spd * dt
                elif g["dir"] == 1:
                    nx += spd * dt
                elif g["dir"] == 2:
                    ny += spd * dt
                else:
                    nx -= spd * dt

                if not is_wall_or_crate(int(round(nx)), int(round(ny)), self.has_keycard):
                    g["x"] = nx
                    g["y"] = ny
                else:
                    g["dir"] = (g["dir"] + 2) % 4

    def update_darts(self, dt: float):
        for d in self.darts:
            if not d["active"]:
                continue
            d["x"] += d["vx"] * dt
            d["y"] += d["vy"] * dt
            if is_wall_or_crate(int(round(d["x"])), int(round(d["y"])), self.has_keycard):
                d["active"] = False

        self.darts = [d for d in self.darts if d["active"]]

    def check_line_of_sight(self):
        for g in self.guards:
            if not g["active"] or g["alert"]:
                continue

            gx = g["x"]
            gy = g["y"]
            dx = self.px - gx
            dy = self.py - gy

            in_sight_cone = False
            if g["dir"] == 0 and dy < 0.0 and abs(dx) <= 1.2 and abs(dy) <= 4.0:
                in_sight_cone = True
            if g["dir"] == 1 and dx > 0.0 and abs(dy) <= 1.2 and abs(dx) <= 4.0:
                in_sight_cone = True
            if g["dir"] == 2 and dy > 0.0 and abs(dx) <= 1.2 and abs(dy) <= 4.0:
                in_sight_cone = True
            if g["dir"] == 3 and dx < 0.0 and abs(dy) <= 1.2 and abs(dx) <= 4.0:
                in_sight_cone = True

            if in_sight_cone:
                if self.in_box and not self.is_moving:
                    continue  # Undetected inside stationary cardboard box!

                g["alert"] = True
                self.alert_level = ALERT_EVASION
                self.alert_timer = 8.0
                self.score = max(0, self.score - 100)

    def check_collisions(self):
        # 1. Darts hit guards
        for d in self.darts:
            if not d["active"]:
                continue
            for g in self.guards:
                if not g["active"]:
                    continue
                if abs(d["x"] - g["x"]) < 1.2 and abs(d["y"] - g["y"]) < 1.2:
                    d["active"] = False
                    g["active"] = False
                    self.guards_neutralized += 1
                    self.score += 150 if g["alert"] else 400
                    break

        # 2. Close quarters sneak takedown
        for g in self.guards:
            if not g["active"] or g["alert"]:
                continue
            if abs(self.px - g["x"]) < 1.0 and abs(self.py - g["y"]) < 1.0:
                g["active"] = False
                self.guards_neutralized += 1
                self.score += 500
                break

        # 3. Alerted guard hits player
        for g in self.guards:
            if not g["active"] or not g["alert"]:
                continue
            if abs(self.px - g["x"]) < 0.9 and abs(self.py - g["y"]) < 0.9:
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

        # 1. Metal floor
        for y in range(16):
            for x in range(16):
                set_pixel(x, y, 35, 45, 50)

        # 2. Walls and Crates
        for y in range(16):
            for x in range(16):
                if is_wall_or_crate(x, y, self.has_keycard):
                    if (x == 7 or x == 8) and y == 2:
                        if self.has_keycard:
                            set_pixel(x, y, 30, 220, 60)
                        else:
                            set_pixel(x, y, 220, 30, 30)
                    elif (x == 4 or x == 5) or (x == 10 or x == 11):
                        set_pixel(x, y, 140, 90, 40)
                    else:
                        set_pixel(x, y, 80, 90, 100)

        # 3. Goal terminal
        set_pixel(7, 1, 40, 240, 255)
        set_pixel(8, 1, 40, 240, 255)

        # 4. Keycard
        if not self.has_keycard:
            set_pixel(13, 13, 255, 215, 0)

        # 5. Guards
        for g in self.guards:
            if not g["active"]:
                continue
            gx = int(round(g["x"]))
            gy = int(round(g["y"]))

            set_pixel(gx, gy, 40, 140, 50)
            set_pixel(gx, gy - 1, 220, 180, 140)

            if g["alert"]:
                set_pixel(gx, gy - 2, 255, 30, 30)
            else:
                fx, fy = gx, gy
                if g["dir"] == 0:
                    fy -= 2
                elif g["dir"] == 1:
                    fx += 2
                elif g["dir"] == 2:
                    fy += 2
                else:
                    fx -= 2
                set_pixel(fx, fy, 180, 180, 70)

        # 6. Darts
        for d in self.darts:
            if not d["active"]:
                continue
            set_pixel(int(round(d["x"])), int(round(d["y"])), 200, 255, 255)

        # 7. Player
        if self.state != STATE_DEAD:
            px = int(round(self.px))
            py = int(round(self.py))
            if self.in_box:
                set_pixel(px, py, 190, 140, 60)
                set_pixel(px + 1, py, 170, 120, 45)
                set_pixel(px, py - 1, 190, 140, 60)
                set_pixel(px + 1, py - 1, 230, 100, 20)
            else:
                set_pixel(px, py, 60, 75, 90)
                set_pixel(px, py - 1, 220, 180, 140)
                set_pixel(px, py - 2, 40, 40, 40)
        else:
            px = int(round(self.px))
            py = int(round(self.py))
            set_pixel(px, py, 200, 40, 40)

        # 8. Alert HUD
        if self.alert_level == ALERT_EVASION:
            for x in range(16):
                if (int(self.state_timer * 10.0) + x) % 2 == 0:
                    set_pixel(x, 0, 255, 20, 20)
        else:
            if self.has_keycard:
                set_pixel(15, 0, 255, 215, 0)

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
            "in_box": self.in_box,
            "alert_level": self.alert_level,
            "has_keycard": self.has_keycard,
            "guards_neutralized": self.guards_neutralized,
        }
