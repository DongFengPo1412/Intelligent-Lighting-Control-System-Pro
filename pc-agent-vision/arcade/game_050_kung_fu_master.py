"""
Game #050: 功夫大师 (Kung-Fu Master / Spartan X 1984 / Irem)
Pagoda Martial Arts Combat with Three-Tier Stance Strikes, Gripper Huggers & Dagger Interceptions.
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

MAX_ENEMIES = 4
MAX_DAGGERS = 2

TYPE_GRIPPER = 0
TYPE_KNIFE_THROWER = 1
TYPE_BOSS_STAFF = 2


class Game050KungFuMaster(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.player_health = 100
        self.enemies_defeated = 0
        self.total_stage_enemies = 5

        self.player_x = 2.0
        self.player_facing = 1
        self.is_crouching = False
        self.is_jumping = False
        self.jump_y_offset = 0.0
        self.jump_vy = 0.0

        self.attack_stance = 0  # 0: Idle, 1: Punch, 2: Mid Kick, 3: Low Sweep, 4: Jump Kick
        self.attack_timer = 0.0
        self.attack_duration = 0.18

        self.num_gripping = 0
        self.wiggle_counter = 0

        self.enemies: List[Dict[str, Any]] = []
        self.daggers: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 50

    @property
    def name(self) -> str:
        return "功夫大师"

    @property
    def english_name(self) -> str:
        return "Kung-Fu Master (1984)"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "五层恶霸武馆上中下三段格击 + 缠身小兵摇晃挣脱 + 半空截击飞刀暗器"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.player_health = 100
        self.enemies_defeated = 0
        self.total_stage_enemies = 5
        self.player_x = 2.0
        self.player_facing = 1
        self.is_crouching = False
        self.is_jumping = False
        self.jump_y_offset = 0.0
        self.jump_vy = 0.0
        self.attack_stance = 0
        self.attack_timer = 0.0
        self.num_gripping = 0
        self.wiggle_counter = 0

        self.daggers = []
        self.init_floor()

    def init_floor(self):
        self.enemies = [
            {"x": 14.0, "type": TYPE_GRIPPER, "vx": -3.2, "health": 15, "active": True, "is_gripping": False, "attack_timer": 0.0},
            {"x": 11.0, "type": TYPE_GRIPPER, "vx": -3.0, "health": 15, "active": True, "is_gripping": False, "attack_timer": 0.0},
            {"x": 15.0, "type": TYPE_KNIFE_THROWER, "vx": -2.0, "health": 20, "active": True, "is_gripping": False, "attack_timer": 1.2},
            {"x": 13.5, "type": TYPE_BOSS_STAFF, "vx": -1.8, "health": 60, "active": False, "is_gripping": False, "attack_timer": 0.8},
        ]

    def execute_punch(self):
        if self.attack_timer > 0.0:
            return
        self.attack_stance = 1
        self.attack_timer = self.attack_duration

    def execute_kick(self):
        if self.attack_timer > 0.0:
            return
        if self.is_jumping:
            self.attack_stance = 4
        elif self.is_crouching:
            self.attack_stance = 3
        else:
            self.attack_stance = 2
        self.attack_timer = self.attack_duration

    def shake_off_grippers(self):
        self.wiggle_counter += 1
        if self.wiggle_counter >= 3:
            for e in self.enemies:
                if e["active"] and e["is_gripping"]:
                    e["active"] = False
                    self.enemies_defeated += 1
                    self.score += 100
            self.num_gripping = 0
            self.wiggle_counter = 0
            if self.score > self.high_score:
                self.high_score = self.score

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        walk_speed = 5.2

        if self.num_gripping > 0:
            self.player_health -= int(12.0 * self.num_gripping * dt)
            if self.player_health <= 0:
                self.player_health = 0
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

            if (buttons & (KEY_LEFT | KEY_RIGHT)) and not (prev_buttons & (KEY_LEFT | KEY_RIGHT)):
                self.shake_off_grippers()
            return

        if self.attack_timer > 0.0:
            self.attack_timer -= dt
            if self.attack_timer <= 0.0:
                self.attack_stance = 0

        if self.is_jumping:
            gravity = 22.0
            self.jump_vy -= gravity * dt
            self.jump_y_offset += self.jump_vy * dt
            if self.jump_y_offset <= 0.0:
                self.jump_y_offset = 0.0
                self.jump_vy = 0.0
                self.is_jumping = False
        else:
            if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
                self.is_jumping = True
                self.jump_vy = 8.5

        if not self.is_jumping and (buttons & KEY_DOWN):
            self.is_crouching = True
        else:
            self.is_crouching = False

        if not self.is_crouching and self.attack_timer <= 0.0:
            vx = 0.0
            if buttons & KEY_LEFT:
                vx = -walk_speed
                self.player_facing = -1
            if buttons & KEY_RIGHT:
                vx = walk_speed
                self.player_facing = 1

            self.player_x += vx * dt
            self.player_x = max(0.5, min(15.0, self.player_x))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.execute_punch()
        elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.execute_kick()

    def update_enemies(self, dt: float):
        for e in self.enemies:
            if not e["active"]:
                continue

            if e["is_gripping"]:
                e["x"] = self.player_x + 0.3
                continue

            e["x"] += e["vx"] * dt
            if e["x"] < 0.5:
                e["x"] = 0.5
                e["vx"] = -e["vx"]
            elif e["x"] > 15.0:
                e["x"] = 15.0
                e["vx"] = -e["vx"]

            if e["type"] == TYPE_KNIFE_THROWER:
                e["attack_timer"] -= dt
                if e["attack_timer"] <= 0.0:
                    e["attack_timer"] = 2.0
                    active_daggers = sum(1 for d in self.daggers if d["active"])
                    if active_daggers < MAX_DAGGERS:
                        self.daggers.append({"x": e["x"] - 0.5, "y": 11.0, "vx": -8.5, "active": True})

            if e["type"] == TYPE_GRIPPER:
                if abs(self.player_x - e["x"]) <= 0.65 and not self.is_jumping:
                    e["is_gripping"] = True
                    self.num_gripping += 1

            if e["type"] == TYPE_BOSS_STAFF:
                e["attack_timer"] -= dt
                if e["attack_timer"] <= 0.0:
                    e["attack_timer"] = 1.4
                    if abs(self.player_x - e["x"]) <= 1.4 and not self.is_crouching:
                        self.player_health -= 20
                        if self.player_health <= 0:
                            self.player_health = 0
                            self.state = STATE_DEAD
                            self.state_timer = 0.0
                            return

    def update_daggers(self, dt: float):
        for d in self.daggers:
            if not d["active"]:
                continue
            d["x"] += d["vx"] * dt
            if d["x"] < 0.0 or d["x"] > 16.0:
                d["active"] = False

    def check_hitboxes(self):
        # 1. Daggers vs Player
        for d in self.daggers:
            if not d["active"]:
                continue
            if abs(d["x"] - self.player_x) <= 0.75:
                if not self.is_jumping and not self.is_crouching:
                    d["active"] = False
                    self.player_health -= 15
                    if self.player_health <= 0:
                        self.player_health = 0
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

        # 2. Player Attack Hitbox vs Enemies & Daggers
        if self.attack_stance == 0:
            return

        reach = 1.35 if self.attack_stance in (2, 4) else 1.0
        dmg = 15 if self.attack_stance == 1 else (20 if self.attack_stance == 2 else (25 if self.attack_stance == 3 else 30))

        # Dagger interception
        for d in self.daggers:
            if not d["active"]:
                continue
            dx = d["x"] - self.player_x
            if (self.player_facing > 0 and 0.0 <= dx <= reach) or (self.player_facing < 0 and -reach <= dx <= 0.0):
                d["active"] = False
                self.score += 100
                if self.score > self.high_score:
                    self.high_score = self.score

        # Strike enemies
        for e in self.enemies:
            if not e["active"] or e["is_gripping"]:
                continue

            dx = e["x"] - self.player_x
            in_front = (self.player_facing > 0 and 0.0 <= dx <= reach) or (self.player_facing < 0 and -reach <= dx <= 0.0)

            if in_front:
                e["health"] -= dmg
                self.score += (self.attack_stance * 50)
                if self.score > self.high_score:
                    self.high_score = self.score

                if e["health"] <= 0:
                    e["active"] = False
                    self.enemies_defeated += 1

                    if self.enemies_defeated == 3 and not self.enemies[3]["active"]:
                        self.enemies[3]["active"] = True
                        self.enemies[3]["x"] = 14.5
                        self.enemies[3]["health"] = 60

                    if self.enemies_defeated >= self.total_stage_enemies or (e["type"] == TYPE_BOSS_STAFF):
                        self.state = STATE_VICTORY
                        self.state_timer = 0.0
                        self.score += 1000
                        if self.score > self.high_score:
                            self.high_score = self.score
                        return

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_enemies(dt)
        self.update_daggers(dt)
        self.check_hitboxes()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        # 1. Pagoda Interior
        for y in range(8):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if x % 4 == 0:
                    fb[idx + 0] = 183
                    fb[idx + 1] = 149
                    fb[idx + 2] = 11
                else:
                    fb[idx + 0] = 60
                    fb[idx + 1] = 15
                    fb[idx + 2] = 15

        # HUD Health Bar
        hp_bars = (self.player_health * 7) // 100
        for x in range(8):
            idx = (0 * 16 + x) * 3
            if x < hp_bars:
                fb[idx + 0] = 46
                fb[idx + 1] = 204
                fb[idx + 2] = 113

        # 2. Wooden Floor
        for y in range(8, 16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx + 0] = 110
                fb[idx + 1] = 65
                fb[idx + 2] = 25

        # 3. Daggers
        for d in self.daggers:
            if not d["active"]:
                continue
            dx = int(round(d["x"]))
            dy = int(round(d["y"]))
            if 0 <= dx < 16 and 0 <= dy < 16:
                idx = (dy * 16 + dx) * 3
                fb[idx + 0] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 255

        # 4. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = 11
            if 0 <= ex < 16:
                idx = (ey * 16 + ex) * 3
                if e["type"] == TYPE_GRIPPER:
                    fb[idx + 0] = 41
                    fb[idx + 1] = 128
                    fb[idx + 2] = 185
                elif e["type"] == TYPE_KNIFE_THROWER:
                    fb[idx + 0] = 241
                    fb[idx + 1] = 196
                    fb[idx + 2] = 15
                else:
                    fb[idx + 0] = 155
                    fb[idx + 1] = 89
                    fb[idx + 2] = 182

        # 5. Player Thomas
        px = int(round(self.player_x))
        py = 11 - int(round(self.jump_y_offset))
        if self.is_crouching:
            py += 1

        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            if self.attack_stance != 0:
                fb[idx + 0] = 231
                fb[idx + 1] = 76
                fb[idx + 2] = 60
            else:
                fb[idx + 0] = 245
                fb[idx + 1] = 245
                fb[idx + 2] = 245

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "player_health": self.player_health,
            "enemies_defeated": self.enemies_defeated,
            "num_gripping": self.num_gripping,
            "player_x": self.player_x,
            "attack_stance": self.attack_stance,
            "is_crouching": self.is_crouching,
            "is_jumping": self.is_jumping,
        }
