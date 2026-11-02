"""
Game #078: 经典空手道 / 格斗道场 (Karate Champ 1984 / Data East / Technos)
First 1-on-1 Fighting Game, Point Scoring (Ippon/Waza-ari), High/Mid/Low Tri-Level Combos & Bonus Breaking.
"""

from typing import Dict, Any
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

STATE_FIGHT = 0
STATE_POINT_SCORED = 1
STATE_ROUND_WIN = 2
STATE_BONUS_STAGE = 3
STATE_GAME_OVER = 4

ATK_NONE = 0
ATK_HIGH_KICK = 1
ATK_MID_PUNCH = 2
ATK_LOW_SWEEP = 3
ATK_BLOCK = 4


class Game078KarateChamp(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FIGHT
        self.state_timer = 0.0
        self.round_timer = 30.0
        self.player_points = 0
        self.cpu_points = 0
        self.rounds_won = 0
        self.dan_level = 1
        self.score = 0

        # Player
        self.px = 4.0
        self.p_attack = ATK_NONE
        self.p_atk_timer = 0.0

        # CPU
        self.cx = 11.0
        self.c_attack = ATK_NONE
        self.c_atk_timer = 0.0
        self.c_ai_think_timer = 0.5

        self.last_scorer = 0
        self.judge_call = ""

        # Bonus
        self.bonus_obj_x = 15.5
        self.bonus_obj_speed = 9.0
        self.bonus_obj_broken = False

        self.reset()

    @property
    def game_id(self) -> int:
        return 78

    @property
    def name(self) -> str:
        return "经典空手道"

    @property
    def english_name(self) -> str:
        return "Karate Champ"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双摇杆格斗鼻祖 + 上中下段判定得分制(一本/技有) + 破瓦碎罐奖励关"

    def get_name(self) -> str:
        return "Karate Champ (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_FIGHT
        self.state_timer = 0.0
        self.round_timer = 30.0
        self.player_points = 0
        self.cpu_points = 0
        self.rounds_won = 0
        self.dan_level = 1
        self.score = 0
        self.reset_round()

    def reset_round(self):
        self.px = 4.0
        self.p_attack = ATK_NONE
        self.p_atk_timer = 0.0

        self.cx = 11.0
        self.c_attack = ATK_NONE
        self.c_atk_timer = 0.0
        self.c_ai_think_timer = 0.5

        self.round_timer = 30.0

    def start_bonus_stage(self):
        self.state = STATE_BONUS_STAGE
        self.state_timer = 0.0
        self.px = 5.0
        self.p_attack = ATK_NONE
        self.p_atk_timer = 0.0
        self.bonus_obj_x = 15.5
        self.bonus_obj_speed = 9.0
        self.bonus_obj_broken = False

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if self.state_timer > 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_POINT_SCORED:
            if self.state_timer > 1.4:
                if self.player_points >= 2:
                    self.state = STATE_ROUND_WIN
                    self.state_timer = 0.0
                    self.rounds_won += 1
                    self.score += 2000
                elif self.cpu_points >= 2:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_FIGHT
                    self.state_timer = 0.0
                    self.reset_round()
            return

        if self.state == STATE_ROUND_WIN:
            if self.state_timer > 1.8:
                if self.rounds_won % 2 == 0:
                    self.start_bonus_stage()
                else:
                    self.dan_level += 1
                    self.player_points = 0
                    self.cpu_points = 0
                    self.state = STATE_FIGHT
                    self.state_timer = 0.0
                    self.reset_round()
            return

        if self.state == STATE_BONUS_STAGE:
            self.update_bonus(dt, buttons, prev_buttons)
            return

        self.update_fight(dt, buttons, prev_buttons)

    def update_fight(self, dt: float, buttons: int, prev_buttons: int):
        self.round_timer = max(0.0, self.round_timer - dt)
        if self.round_timer <= 0.0:
            if self.player_points > self.cpu_points:
                self.player_points = 2
            else:
                self.cpu_points = 2
            self.state = STATE_POINT_SCORED
            self.state_timer = 0.0
            return

        # Player Attack
        if self.p_atk_timer > 0.0:
            self.p_atk_timer -= dt
            if self.p_atk_timer <= 0.0:
                self.p_attack = ATK_NONE
        else:
            move_speed = 4.0
            if buttons & KEY_LEFT:
                self.px -= move_speed * dt
            if buttons & KEY_RIGHT:
                self.px += move_speed * dt

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                if buttons & KEY_UP:
                    self.p_attack = ATK_HIGH_KICK
                    self.p_atk_timer = 0.35
                else:
                    self.p_attack = ATK_MID_PUNCH
                    self.p_atk_timer = 0.25
            elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
                if buttons & KEY_DOWN:
                    self.p_attack = ATK_LOW_SWEEP
                    self.p_atk_timer = 0.35
                else:
                    self.p_attack = ATK_BLOCK
                    self.p_atk_timer = 0.30

        # CPU AI
        if self.c_atk_timer > 0.0:
            self.c_atk_timer -= dt
            if self.c_atk_timer <= 0.0:
                self.c_attack = ATK_NONE
        else:
            self.c_ai_think_timer -= dt
            dist = self.cx - self.px
            cpu_speed = 3.6
            if dist > 2.4:
                self.cx -= cpu_speed * dt
            elif dist < 1.8:
                self.cx += cpu_speed * dt

            if self.c_ai_think_timer <= 0.0:
                self.c_ai_think_timer = 0.6
                if dist < 2.8:
                    if self.p_attack in (ATK_HIGH_KICK, ATK_MID_PUNCH):
                        self.c_attack = ATK_BLOCK
                        self.c_atk_timer = 0.35
                    else:
                        self.c_attack = ATK_MID_PUNCH
                        self.c_atk_timer = 0.25

        self.px = max(1.0, min(self.cx - 1.4, self.px))
        self.cx = max(self.px + 1.4, min(14.5, self.cx))

        self.check_hits()

    def check_hits(self):
        dist = self.cx - self.px

        if self.p_atk_timer > 0.1 and dist <= 2.2:
            if self.p_attack == ATK_MID_PUNCH:
                if self.c_attack != ATK_BLOCK:
                    self.player_points += 1
                    self.score += 500
                    self.last_scorer = 1
                    self.judge_call = "WAZA-ARI"
                    self.state = STATE_POINT_SCORED
                    self.state_timer = 0.0
                    return
            elif self.p_attack == ATK_HIGH_KICK:
                if self.c_attack not in (ATK_BLOCK, ATK_LOW_SWEEP):
                    self.player_points += 2
                    self.score += 1000
                    self.last_scorer = 1
                    self.judge_call = "IPPON"
                    self.state = STATE_POINT_SCORED
                    self.state_timer = 0.0
                    return
            elif self.p_attack == ATK_LOW_SWEEP:
                if self.c_attack != ATK_HIGH_KICK:
                    self.player_points += 2
                    self.score += 1000
                    self.last_scorer = 1
                    self.judge_call = "IPPON"
                    self.state = STATE_POINT_SCORED
                    self.state_timer = 0.0
                    return

        if self.c_atk_timer > 0.1 and dist <= 2.2:
            if self.c_attack == ATK_MID_PUNCH:
                if self.p_attack != ATK_BLOCK:
                    self.cpu_points += 1
                    self.last_scorer = 2
                    self.judge_call = "WAZA-ARI"
                    self.state = STATE_POINT_SCORED
                    self.state_timer = 0.0
                    return
            elif self.c_attack == ATK_HIGH_KICK:
                if self.p_attack not in (ATK_BLOCK, ATK_LOW_SWEEP):
                    self.cpu_points += 2
                    self.last_scorer = 2
                    self.judge_call = "IPPON"
                    self.state = STATE_POINT_SCORED
                    self.state_timer = 0.0
                    return
            elif self.c_attack == ATK_LOW_SWEEP:
                if self.p_attack != ATK_HIGH_KICK:
                    self.cpu_points += 2
                    self.last_scorer = 2
                    self.judge_call = "IPPON"
                    self.state = STATE_POINT_SCORED
                    self.state_timer = 0.0
                    return

    def update_bonus(self, dt: float, buttons: int, prev_buttons: int):
        if not self.bonus_obj_broken:
            self.bonus_obj_x -= self.bonus_obj_speed * dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.p_attack = ATK_MID_PUNCH
                self.p_atk_timer = 0.25
                if abs(self.bonus_obj_x - self.px) < 1.6:
                    self.bonus_obj_broken = True
                    self.score += 1500

            if self.bonus_obj_x < 0.0:
                self.state = STATE_FIGHT
                self.state_timer = 0.0
                self.player_points = 0
                self.cpu_points = 0
                self.dan_level += 1
                self.reset_round()
        else:
            if self.state_timer > 1.5:
                self.state = STATE_FIGHT
                self.state_timer = 0.0
                self.player_points = 0
                self.cpu_points = 0
                self.dan_level += 1
                self.reset_round()

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Dojo Backdrop
        for y in range(13):
            for x in range(16):
                set_pixel(x, y, 40, 25, 20)

        # 2. Tatami Floor
        for y in range(13, 16):
            for x in range(16):
                set_pixel(x, y, 160, 140, 80)

        # 3. Referee
        set_pixel(7, 10, 220, 180, 140)
        set_pixel(7, 11, 20, 20, 20)
        set_pixel(8, 11, 20, 20, 20)
        set_pixel(7, 12, 40, 40, 40)
        set_pixel(8, 12, 40, 40, 40)

        if self.state == STATE_POINT_SCORED:
            if self.last_scorer == 1:
                set_pixel(6, 9, 255, 255, 255)
            else:
                set_pixel(9, 9, 255, 20, 20)

        # 4. Player
        px = int(round(self.px))
        set_pixel(px, 10, 240, 180, 140)
        set_pixel(px, 9, 20, 20, 20)

        if self.p_attack == ATK_HIGH_KICK:
            set_pixel(px, 11, 250, 250, 250)
            set_pixel(px + 1, 10, 250, 250, 250)
            set_pixel(px, 12, 240, 240, 240)
        elif self.p_attack == ATK_MID_PUNCH:
            set_pixel(px, 11, 250, 250, 250)
            set_pixel(px + 1, 11, 240, 180, 140)
            set_pixel(px, 12, 240, 240, 240)
        elif self.p_attack == ATK_LOW_SWEEP:
            set_pixel(px, 12, 250, 250, 250)
            set_pixel(px + 1, 12, 250, 250, 250)
        elif self.p_attack == ATK_BLOCK:
            set_pixel(px, 11, 250, 250, 250)
            set_pixel(px - 1, 11, 240, 180, 140)
            set_pixel(px, 12, 240, 240, 240)
        else:
            set_pixel(px, 11, 250, 250, 250)
            set_pixel(px, 12, 240, 240, 240)

        # 5. CPU
        cx = int(round(self.cx))
        set_pixel(cx, 10, 240, 180, 140)
        set_pixel(cx, 9, 20, 20, 20)

        if self.c_attack == ATK_HIGH_KICK:
            set_pixel(cx, 11, 220, 30, 30)
            set_pixel(cx - 1, 10, 220, 30, 30)
            set_pixel(cx, 12, 200, 20, 20)
        elif self.c_attack == ATK_MID_PUNCH:
            set_pixel(cx, 11, 220, 30, 30)
            set_pixel(cx - 1, 11, 240, 180, 140)
            set_pixel(cx, 12, 200, 20, 20)
        elif self.c_attack == ATK_LOW_SWEEP:
            set_pixel(cx, 12, 220, 30, 30)
            set_pixel(cx - 1, 12, 220, 30, 30)
        elif self.c_attack == ATK_BLOCK:
            set_pixel(cx, 11, 220, 30, 30)
            set_pixel(cx + 1, 11, 240, 180, 140)
            set_pixel(cx, 12, 200, 20, 20)
        else:
            set_pixel(cx, 11, 220, 30, 30)
            set_pixel(cx, 12, 200, 20, 20)

        # 6. Bonus Stage Object
        if self.state == STATE_BONUS_STAGE:
            ox = int(round(self.bonus_obj_x))
            if not self.bonus_obj_broken:
                set_pixel(ox, 11, 180, 100, 40)
                set_pixel(ox, 10, 220, 120, 50)
            else:
                set_pixel(ox - 1, 11, 255, 200, 0)
                set_pixel(ox + 1, 10, 255, 120, 0)

        # 7. Score HUD
        for i in range(self.player_points):
            set_pixel(i * 2 + 1, 0, 255, 255, 255)
        for i in range(self.cpu_points):
            set_pixel(14 - i * 2, 0, 255, 30, 30)
        set_pixel(7, 0, 20, 20, 20)
        set_pixel(8, 0, 200, 160, 20)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "player_points": self.player_points,
            "cpu_points": self.cpu_points,
            "dan_level": self.dan_level,
            "rounds_won": self.rounds_won,
            "score": self.score,
            "round_timer": self.round_timer,
            "px": self.px,
            "cx": self.cx,
            "p_attack": self.p_attack,
            "c_attack": self.c_attack,
        }
