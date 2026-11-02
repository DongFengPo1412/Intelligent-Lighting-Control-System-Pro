"""
Game #048: 疯狂电梯 (Elevator Action 1983 / Taito)
Skyscraper Infiltration with Elevators, Elevator Crush Traps, Red Secret Doors, Light Fixture Shootouts & Pistol Duels.
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

NUM_FLOORS = 4
MAX_BULLETS = 4
MAX_ENEMIES = 3
NUM_RED_DOORS = 2
FLOOR_Y = [3, 7, 11, 15]


class Game048ElevatorAction(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.docs_collected = 0

        self.player_x = 2.0
        self.player_y = 3.0
        self.player_vx = 0.0
        self.player_facing = 1
        self.is_crouching = False
        self.in_elevator = False

        self.elevator_y = 3.0
        self.elevator_vy = 0.0
        self.blackout_timer = 0.0

        self.bullets: List[Dict[str, Any]] = []
        self.enemies: List[Dict[str, Any]] = []
        self.red_doors: List[Dict[str, Any]] = []
        self.lights: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 48

    @property
    def name(self) -> str:
        return "疯狂电梯"

    @property
    def english_name(self) -> str:
        return "Elevator Action (1983)"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "摩天大楼升降机垂直升降操控 + 电梯悬挂压杀 + 红色机密门潜入与击落顶灯断电"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.docs_collected = 0
        self.player_x = 2.0
        self.player_y = 3.0
        self.player_vx = 0.0
        self.player_facing = 1
        self.is_crouching = False
        self.in_elevator = False
        self.elevator_y = 3.0
        self.elevator_vy = 0.0
        self.blackout_timer = 0.0

        self.bullets = []
        self.init_building()

    def init_building(self):
        self.red_doors = [
            {"floor": 1, "col": 3, "collected": False},
            {"floor": 2, "col": 12, "collected": False},
        ]
        self.lights = [
            {"floor": f, "col": 4 if f % 2 == 0 else 11, "active": True}
            for f in range(NUM_FLOORS)
        ]
        self.enemies = [
            {"x": 12.0, "floor": 0, "vx": -2.5, "active": True, "shoot_timer": 1.2},
            {"x": 13.0, "floor": 1, "vx": -2.5, "active": True, "shoot_timer": 1.8},
            {"x": 4.0, "floor": 2, "vx": 2.5, "active": True, "shoot_timer": 1.5},
        ]

    def get_documents_remaining(self) -> int:
        return NUM_RED_DOORS - self.docs_collected

    def fire_pistol(self, is_player: bool, x: float, y: float, dir_x: float):
        active_bullets = sum(1 for b in self.bullets if b["active"])
        if active_bullets < MAX_BULLETS:
            self.bullets.append({
                "x": x,
                "y": y,
                "vx": dir_x * 14.0,
                "is_player": is_player,
                "active": True,
            })

    def update_elevator(self, dt: float, buttons: int):
        elevator_speed = 4.2
        self.elevator_vy = 0.0

        if self.in_elevator:
            if buttons & KEY_UP:
                self.elevator_vy = -elevator_speed
            if buttons & KEY_DOWN:
                self.elevator_vy = elevator_speed

        self.elevator_y += self.elevator_vy * dt
        self.elevator_y = max(3.0, min(15.0, self.elevator_y))

        if self.in_elevator:
            self.player_y = self.elevator_y

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        walk_speed = 5.5

        if 6.5 <= self.player_x <= 8.5 and abs(self.player_y - self.elevator_y) <= 0.85:
            self.in_elevator = True
        else:
            self.in_elevator = False

        if not self.in_elevator and (buttons & KEY_DOWN):
            self.is_crouching = True
            self.player_vx = 0.0
        else:
            self.is_crouching = False
            self.player_vx = 0.0
            if buttons & KEY_LEFT:
                self.player_vx = -walk_speed
                self.player_facing = -1
            if buttons & KEY_RIGHT:
                self.player_vx = walk_speed
                self.player_facing = 1

        self.player_x += self.player_vx * dt
        self.player_x = max(0.5, min(15.0, self.player_x))

        if not self.in_elevator:
            nearest_f = min(range(NUM_FLOORS), key=lambda f: abs(self.player_y - FLOOR_Y[f]))
            self.player_y = float(FLOOR_Y[nearest_f])

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            shoot_y = (self.player_y + 0.3) if self.is_crouching else (self.player_y - 0.2)
            self.fire_pistol(True, self.player_x + self.player_facing * 0.8, shoot_y, float(self.player_facing))

        for rd in self.red_doors:
            if not rd["collected"]:
                door_y = float(FLOOR_Y[rd["floor"]])
                if abs(self.player_y - door_y) <= 0.5 and abs(self.player_x - rd["col"]) <= 0.8:
                    rd["collected"] = True
                    self.docs_collected += 1
                    self.score += 200
                    if self.score > self.high_score:
                        self.high_score = self.score

        if self.docs_collected >= NUM_RED_DOORS and self.player_y >= 14.5 and self.player_x <= 3.0:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 1000
            if self.score > self.high_score:
                self.high_score = self.score

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"]:
                continue
            if self.blackout_timer > 0.0:
                continue

            e["x"] += e["vx"] * dt
            if e["x"] < 1.0:
                e["x"] = 1.0
                e["vx"] = -e["vx"]
            elif e["x"] > 15.0:
                e["x"] = 15.0
                e["vx"] = -e["vx"]

            e["shoot_timer"] -= dt
            if e["shoot_timer"] <= 0.0:
                e["shoot_timer"] = 2.2
                ey = float(FLOOR_Y[e["floor"]])
                dir_x = 1.0 if self.player_x > e["x"] else -1.0
                self.fire_pistol(False, e["x"] + dir_x * 0.8, ey - 0.2, dir_x)

    def update_bullets(self, dt: float):
        for b in self.bullets:
            if not b["active"]:
                continue
            b["x"] += b["vx"] * dt
            if b["x"] < 0.0 or b["x"] > 16.0:
                b["active"] = False

    def check_collisions(self):
        # 1. Bullets vs Lights
        for b in self.bullets:
            if not b["active"] or not b["is_player"]:
                continue
            for l in self.lights:
                if not l["active"]:
                    continue
                ly = float(FLOOR_Y[l["floor"]] - 2)
                if abs(b["x"] - l["col"]) <= 0.85 and abs(b["y"] - ly) <= 1.0:
                    b["active"] = False
                    l["active"] = False
                    self.blackout_timer = 3.5
                    self.score += 100
                    if self.score > self.high_score:
                        self.high_score = self.score
                    break

        # 2. Player Bullets vs Enemies
        for b in self.bullets:
            if not b["active"] or not b["is_player"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue
                ey = float(FLOOR_Y[e["floor"]])
                if abs(b["x"] - e["x"]) <= 0.82 and abs(b["y"] - ey) <= 0.7:
                    b["active"] = False
                    e["active"] = False
                    self.score += 100
                    if self.score > self.high_score:
                        self.high_score = self.score
                    break

        # 3. Enemy Bullets vs Player
        for b in self.bullets:
            if not b["active"] or b["is_player"]:
                continue
            if abs(b["x"] - self.player_x) <= 0.75 and abs(b["y"] - self.player_y) <= 0.65:
                if not self.is_crouching:
                    b["active"] = False
                    self.lives -= 1
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return

        # 4. Elevator Crush Mechanic
        if self.elevator_vy > 0.0:
            for e in self.enemies:
                if not e["active"]:
                    continue
                if 6.5 <= e["x"] <= 8.5:
                    ey = float(FLOOR_Y[e["floor"]])
                    if self.elevator_y < ey <= self.elevator_y + 1.2:
                        e["active"] = False
                        self.score += 150
                        if self.score > self.high_score:
                            self.high_score = self.score

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt
        if self.blackout_timer > 0.0:
            self.blackout_timer -= dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 2.0
                    self.player_y = 3.0
                    self.elevator_y = 3.0
                    self.in_elevator = False
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_elevator(dt, buttons)
        self.update_enemies(dt)
        self.update_bullets(dt)
        self.check_collisions()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        bg_val = 2 if self.blackout_timer > 0.0 else 15
        for i in range(256):
            fb[i * 3 + 0] = bg_val
            fb[i * 3 + 1] = bg_val
            fb[i * 3 + 2] = bg_val

        # 2. Floors
        for f in range(NUM_FLOORS):
            y = FLOOR_Y[f]
            for x in range(16):
                if x in (7, 8):
                    continue
                idx = (y * 16 + x) * 3
                fb[idx + 0] = 86
                fb[idx + 1] = 101
                fb[idx + 2] = 115

        # 3. Red Doors
        for rd in self.red_doors:
            if not rd["collected"]:
                rx = rd["col"]
                ry = FLOOR_Y[rd["floor"]] - 1
                idx = (ry * 16 + rx) * 3
                fb[idx + 0] = 231
                fb[idx + 1] = 76
                fb[idx + 2] = 60

        # 4. Overhead Lights
        for l in self.lights:
            if l["active"]:
                lx = l["col"]
                ly = FLOOR_Y[l["floor"]] - 2
                if ly >= 0:
                    idx = (ly * 16 + lx) * 3
                    fb[idx + 0] = 241
                    fb[idx + 1] = 196
                    fb[idx + 2] = 15

        # 5. Elevator Cabin
        ey = int(round(self.elevator_y))
        for x in (7, 8):
            if 0 <= ey < 16:
                idx = (ey * 16 + x) * 3
                fb[idx + 0] = 52
                fb[idx + 1] = 152
                fb[idx + 2] = 219

        # 6. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = FLOOR_Y[e["floor"]] - 1
            if 0 <= ex < 16 and 0 <= ey < 16:
                idx = (ey * 16 + ex) * 3
                fb[idx + 0] = 142
                fb[idx + 1] = 68
                fb[idx + 2] = 173

        # 7. Bullets
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                fb[idx + 0] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 255

        # 8. Player Otto
        px = int(round(self.player_x))
        py = int(round(self.player_y)) - 1
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx + 0] = 39
            fb[idx + 1] = 174
            fb[idx + 2] = 96

        # 9. Getaway Car
        c1 = (14 * 16 + 1) * 3
        c2 = (14 * 16 + 2) * 3
        fb[c1 + 0] = 230
        fb[c1 + 1] = 126
        fb[c1 + 2] = 34
        fb[c2 + 0] = 230
        fb[c2 + 1] = 126
        fb[c2 + 2] = 34

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "docs_remaining": self.get_documents_remaining(),
            "player_x": self.player_x,
            "player_y": self.player_y,
            "elevator_y": self.elevator_y,
            "in_elevator": self.in_elevator,
            "is_crouching": self.is_crouching,
            "blackout_active": (self.blackout_timer > 0.0),
        }
