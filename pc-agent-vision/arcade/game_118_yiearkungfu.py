"""
Game #118: 功夫小子 (Yie Ar Kung-Fu 1985 / Konami)
The definitive foundation of 1-on-1 fighting games:
8-way high/mid/low strike triad stances, flying jump kicks, low sweeping kicks,
projectile parrying & deflection, and health bar martial arts duels.
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

STATE_FIGHTING = 0
STATE_KO_VICTORY = 1
STATE_PLAYER_DEFEATED = 2
STATE_GAME_OVER = 3

STANCE_IDLE = 0
STANCE_MID_PUNCH = 1
STANCE_MID_KICK = 2
STANCE_HIGH_JUMP_KICK = 3
STANCE_LOW_SWEEP = 4

MAX_PROJECTILES = 2


class Game118YieArKungFu(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FIGHTING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1

        self.player: Dict[str, Any] = {
            "x": 4.0, "y": 13.0, "vy": 0.0, "hp": 100, "facing": 1,
            "stance": STANCE_IDLE, "stance_timer": 0.0, "hurt_timer": 0.0,
        }
        self.opponent: Dict[str, Any] = {
            "x": 12.0, "y": 13.0, "vy": 0.0, "hp": 100, "facing": -1,
            "stance": STANCE_IDLE, "stance_timer": 0.0, "hurt_timer": 0.0,
        }

        self.projectiles: List[Dict[str, Any]] = []
        self.ai_action_timer = 1.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 118

    @property
    def name(self) -> str:
        return "功夫小子"

    @property
    def english_name(self) -> str:
        return "Yie Ar Kung-Fu"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "八向摇杆上中下三路攻防架势、跳跃飞踢与扫堂腿、手里剑格挡招架与双血条对决"

    def get_name(self) -> str:
        return "Yie Ar Kung-Fu (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._init_match()

    def _init_match(self) -> None:
        self.state = STATE_FIGHTING
        self.state_timer = 0.0
        self.ai_action_timer = 1.0

        self.player = {
            "x": 4.0, "y": 13.0, "vy": 0.0, "hp": 100, "facing": 1,
            "stance": STANCE_IDLE, "stance_timer": 0.0, "hurt_timer": 0.0,
        }
        self.opponent = {
            "x": 12.0, "y": 13.0, "vy": 0.0, "hp": 100, "facing": -1,
            "stance": STANCE_IDLE, "stance_timer": 0.0, "hurt_timer": 0.0,
        }

        self.projectiles = []
        for _ in range(MAX_PROJECTILES):
            self.projectiles.append({"x": 0.0, "y": 0.0, "vx": 0.0, "active": False})

    def execute_player_attack(self, stance: int) -> None:
        if self.player["hurt_timer"] > 0.0:
            return
        self.player["stance"] = stance
        if stance == STANCE_MID_PUNCH:
            self.player["stance_timer"] = 0.22
        elif stance == STANCE_MID_KICK:
            self.player["stance_timer"] = 0.25
        elif stance == STANCE_HIGH_JUMP_KICK:
            self.player["stance_timer"] = 0.35
        elif stance == STANCE_LOW_SWEEP:
            self.player["stance_timer"] = 0.28

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

        if self.state == STATE_KO_VICTORY:
            if self.state_timer > 1.8:
                self.round += 1
                self.score += 1000
                self._init_match()
            return

        if self.state == STATE_PLAYER_DEFEATED:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self._init_match()
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_opponent_ai(dt)
        self._update_projectiles(dt)
        self._check_strikes_and_parries()

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.player["hurt_timer"] > 0.0:
            self.player["hurt_timer"] -= dt
            self.player["stance"] = STANCE_IDLE
            return

        if self.player["stance_timer"] > 0.0:
            self.player["stance_timer"] -= dt
            if self.player["stance_timer"] <= 0.0:
                self.player["stance"] = STANCE_IDLE

        if self.player["y"] < 13.0 or self.player["vy"] < 0.0:
            self.player["vy"] += 12.0 * dt
            self.player["y"] += self.player["vy"] * dt
            if self.player["y"] >= 13.0:
                self.player["y"] = 13.0
                self.player["vy"] = 0.0

        move_spd = 4.5
        if self.player["stance"] == STANCE_IDLE:
            if buttons & KEY_LEFT:
                self.player["x"] -= move_spd * dt
            if buttons & KEY_RIGHT:
                self.player["x"] += move_spd * dt

            if (buttons & KEY_UP) and self.player["y"] >= 13.0:
                self.player["vy"] = -4.2

        if self.player["x"] < self.opponent["x"]:
            self.player["facing"] = 1
        else:
            self.player["facing"] = -1

        self.player["x"] = max(1.5, min(14.5, self.player["x"]))

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.execute_player_attack(STANCE_MID_PUNCH)
        elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.player["y"] < 12.5 or (buttons & KEY_UP):
                if self.player["y"] >= 13.0:
                    self.player["vy"] = -4.0
                self.execute_player_attack(STANCE_HIGH_JUMP_KICK)
            elif buttons & KEY_DOWN:
                self.execute_player_attack(STANCE_LOW_SWEEP)
            else:
                self.execute_player_attack(STANCE_MID_KICK)

    def _update_opponent_ai(self, dt: float) -> None:
        if self.opponent["hurt_timer"] > 0.0:
            self.opponent["hurt_timer"] -= dt
            self.opponent["stance"] = STANCE_IDLE
            return

        if self.opponent["stance_timer"] > 0.0:
            self.opponent["stance_timer"] -= dt
            if self.opponent["stance_timer"] <= 0.0:
                self.opponent["stance"] = STANCE_IDLE

        if self.opponent["x"] < self.player["x"]:
            self.opponent["facing"] = 1
        else:
            self.opponent["facing"] = -1

        dx = self.player["x"] - self.opponent["x"]
        dist = abs(dx)

        self.ai_action_timer -= dt
        if self.ai_action_timer <= 0.0:
            self.ai_action_timer = 1.0

            if dist > 4.5:
                for p in self.projectiles:
                    if not p["active"]:
                        p["x"] = self.opponent["x"] + float(self.opponent["facing"]) * 0.8
                        p["y"] = 12.0
                        p["vx"] = float(self.opponent["facing"]) * 7.5
                        p["active"] = True
                        break
            elif dist <= 2.2:
                self.opponent["stance"] = STANCE_MID_PUNCH
                self.opponent["stance_timer"] = 0.25

        if self.opponent["stance"] == STANCE_IDLE:
            step = 2.8 * dt
            if dist > 2.0:
                self.opponent["x"] += float(self.opponent["facing"]) * step
            elif dist < 1.4:
                self.opponent["x"] -= float(self.opponent["facing"]) * step

        self.opponent["x"] = max(1.5, min(14.5, self.opponent["x"]))

    def _update_projectiles(self, dt: float) -> None:
        for p in self.projectiles:
            if not p["active"]:
                continue
            p["x"] += p["vx"] * dt
            if p["x"] < 0.5 or p["x"] > 15.5:
                p["active"] = False

    def _check_strikes_and_parries(self) -> None:
        # 1. Player parry against projectile
        if self.player["stance"] != STANCE_IDLE:
            for p in self.projectiles:
                if not p["active"]:
                    continue
                dx = abs(self.player["x"] - p["x"])
                dy = abs(self.player["y"] - p["y"])
                if dx < 1.4 and dy < 1.6:
                    p["active"] = False
                    self.score += 100

        # 2. Projectile hit player
        for p in self.projectiles:
            if not p["active"]:
                continue
            dx = abs(self.player["x"] - p["x"])
            dy = abs(self.player["y"] - p["y"])
            if dx < 0.8 and dy < 1.2:
                if self.player["stance"] == STANCE_LOW_SWEEP:
                    continue
                p["active"] = False
                self.player["hp"] -= 15
                self.player["hurt_timer"] = 0.3
                self.player["x"] -= float(self.player["facing"]) * 0.8
                if self.player["hp"] <= 0:
                    self.player["hp"] = 0
                    self.state = STATE_PLAYER_DEFEATED
                    self.state_timer = 0.0

        # 3. Player strike opponent
        if self.player["stance"] != STANCE_IDLE and self.opponent["hurt_timer"] <= 0.0:
            reach = 1.6
            damage = 10
            if self.player["stance"] == STANCE_MID_KICK:
                reach = 2.0
                damage = 15
            elif self.player["stance"] == STANCE_HIGH_JUMP_KICK:
                reach = 2.4
                damage = 25
            elif self.player["stance"] == STANCE_LOW_SWEEP:
                reach = 1.8
                damage = 18

            target_x = self.player["x"] + float(self.player["facing"]) * reach
            if abs(target_x - self.opponent["x"]) < 1.2 and abs(self.player["y"] - self.opponent["y"]) < 1.8:
                self.opponent["hp"] -= damage
                self.opponent["hurt_timer"] = 0.28
                self.opponent["x"] += float(self.player["facing"]) * 1.2
                self.score += damage * 10

                if self.opponent["hp"] <= 0:
                    self.opponent["hp"] = 0
                    self.state = STATE_KO_VICTORY
                    self.state_timer = 0.0

        # 4. Opponent strike player
        if self.opponent["stance"] != STANCE_IDLE and self.player["hurt_timer"] <= 0.0:
            reach = 1.8
            target_x = self.opponent["x"] + float(self.opponent["facing"]) * reach
            if abs(target_x - self.player["x"]) < 1.1 and abs(self.opponent["y"] - self.player["y"]) < 1.6:
                if self.player["stance"] == STANCE_LOW_SWEEP and self.opponent["stance"] == STANCE_MID_PUNCH:
                    pass
                else:
                    self.player["hp"] -= 12
                    self.player["hurt_timer"] = 0.28
                    self.player["x"] += float(self.opponent["facing"]) * 1.0
                    if self.player["hp"] <= 0:
                        self.player["hp"] = 0
                        self.state = STATE_PLAYER_DEFEATED
                        self.state_timer = 0.0

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Health bars
        p_bars = int((self.player["hp"] / 100.0) * 7.0)
        for i in range(p_bars):
            set_pixel(i, 0, 40, 220, 80)

        o_bars = int((self.opponent["hp"] / 100.0) * 7.0)
        for i in range(o_bars):
            set_pixel(15 - i, 0, 255, 40, 30)

        # 2. Floor & Pillars
        for x in range(16):
            set_pixel(x, 14, 180, 100, 40)
            set_pixel(x, 15, 120, 60, 20)
        set_pixel(1, 13, 200, 40, 30)
        set_pixel(14, 13, 200, 40, 30)

        # 3. Projectiles
        for p in self.projectiles:
            if not p["active"]:
                continue
            set_pixel(int(round(p["x"])), int(round(p["y"])), 0, 255, 255)

        # 4. Opponent
        ox = int(round(self.opponent["x"]))
        oy = int(round(self.opponent["y"]))
        if self.opponent["hurt_timer"] > 0.0:
            set_pixel(ox, oy, 255, 255, 255)
            set_pixel(ox, oy - 1, 255, 80, 40)
        else:
            set_pixel(ox, oy, 220, 40, 30)
            set_pixel(ox, oy - 1, 255, 200, 140)
            set_pixel(ox, oy + 1, 40, 40, 50)
            if self.opponent["stance"] != STANCE_IDLE:
                set_pixel(ox + self.opponent["facing"], oy, 255, 200, 40)

        # 5. Player
        px = int(round(self.player["x"]))
        py = int(round(self.player["y"]))
        if self.player["hurt_timer"] > 0.0:
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px, py - 1, 255, 60, 40)
        elif self.player["stance"] == STANCE_LOW_SWEEP:
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px + self.player["facing"], py, 40, 100, 240)
            set_pixel(px + self.player["facing"] * 2, py, 255, 200, 140)
        elif self.player["stance"] == STANCE_HIGH_JUMP_KICK:
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px, py - 1, 255, 200, 140)
            set_pixel(px + self.player["facing"], py, 40, 100, 240)
        else:
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px, py - 1, 255, 200, 140)
            set_pixel(px, py + 1, 40, 100, 240)
            if self.player["stance"] == STANCE_MID_PUNCH:
                set_pixel(px + self.player["facing"], py, 255, 200, 140)
            elif self.player["stance"] == STANCE_MID_KICK:
                set_pixel(px + self.player["facing"], py, 40, 100, 240)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "round": self.round,
            "player_hp": self.player["hp"],
            "opponent_hp": self.opponent["hp"],
            "player_stance": self.player["stance"],
            "player_x": self.player["x"],
            "player_y": self.player["y"],
        }
