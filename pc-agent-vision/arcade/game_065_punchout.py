"""
Game #065: 超级拳击 (Punch-Out!! 1983 / Nintendo)
First-Person Wireframe Boxing Duel: Telegraph-Dodge Rhythms, Star Counter-Uppercuts & TKO Knockdowns.
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

STATE_START = 0
STATE_PLAYING = 1
STATE_ROUND_WIN = 2
STATE_DEAD = 3
STATE_VICTORY = 4

# Player Actions
ACT_IDLE = 0
ACT_DODGE_LEFT = 1
ACT_DODGE_RIGHT = 2
ACT_DUCK = 3
ACT_BLOCK = 4
ACT_PUNCH_LEFT = 5
ACT_PUNCH_RIGHT = 6
ACT_HURT = 7
ACT_DOWN = 8

# Opponent Actions
OPP_IDLE = 0
OPP_PREP_LEFT_HOOK = 1
OPP_PREP_RIGHT_HOOK = 2
OPP_PREP_BULL_CHARGE = 3
OPP_SWING = 4
OPP_STUNNED = 5
OPP_HURT = 6
OPP_DOWN = 7


class Game065PunchOut(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 5000

        # Player state
        self.player_stamina = 100
        self.player_action = ACT_IDLE
        self.action_timer = 0.0
        self.player_downs = 0
        self.stars = 0
        self.dodge_offset_x = 0.0
        self.duck_offset_y = 0.0

        # Opponent state
        self.opp_stamina = 100
        self.opp_action = OPP_IDLE
        self.opp_timer = 1.0
        self.opp_downs = 0
        self.opp_attack_type = 1
        self.ref_count_timer = 0.0
        self.count_num = 1

        self.reset()

    @property
    def game_id(self) -> int:
        return 65

    @property
    def name(self) -> str:
        return "超级拳击"

    @property
    def english_name(self) -> str:
        return "Punch-Out!!"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "背影视角对峙 + 观察预警左右摇摆闪避 + 破绽暴击攒星上勾拳与三倒TKO"

    def get_name(self) -> str:
        return "Punch-Out!! (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.player_downs = 0
        self.opp_downs = 0
        self.stars = 0
        self.init_round()

    def init_round(self):
        self.player_stamina = 100
        self.player_action = ACT_IDLE
        self.action_timer = 0.0
        self.dodge_offset_x = 0.0
        self.duck_offset_y = 0.0

        self.opp_stamina = 100
        self.opp_action = OPP_IDLE
        self.opp_timer = 1.0
        self.opp_attack_type = 1
        self.ref_count_timer = 0.0
        self.count_num = 1

    def dodge(self, direction: int):
        if self.player_action != ACT_IDLE and self.player_action != ACT_BLOCK:
            return

        if direction == -1:
            self.player_action = ACT_DODGE_LEFT
            self.dodge_offset_x = -3.0
            self.action_timer = 0.35
        elif direction == 1:
            self.player_action = ACT_DODGE_RIGHT
            self.dodge_offset_x = 3.0
            self.action_timer = 0.35
        elif direction == 0:
            self.player_action = ACT_DUCK
            self.duck_offset_y = 2.0
            self.action_timer = 0.35

    def punch(self, hand: int):
        if self.player_action != ACT_IDLE:
            return

        self.player_action = ACT_PUNCH_LEFT if hand == 0 else ACT_PUNCH_RIGHT
        self.action_timer = 0.22

        # Check hit on opponent
        if self.opp_action in (OPP_STUNNED, OPP_PREP_LEFT_HOOK, OPP_PREP_RIGHT_HOOK, OPP_PREP_BULL_CHARGE):
            is_star_punch = (self.stars > 0 and hand == 1)
            damage = 40 if is_star_punch else 20
            if is_star_punch:
                self.stars -= 1

            self.opp_stamina -= damage
            self.score += 300 if is_star_punch else 100

            if self.opp_action != OPP_STUNNED and self.stars < 3:
                self.stars += 1
                self.score += 150

            self.opp_action = OPP_HURT
            self.opp_timer = 0.28

            if self.opp_stamina <= 0:
                self.knockdown_opponent()
        elif self.opp_action == OPP_IDLE:
            # Blocked by opponent guard
            self.score += 10

    def knockdown_player(self):
        self.player_action = ACT_DOWN
        self.player_stamina = 0
        self.player_downs += 1
        self.action_timer = 0.0
        self.ref_count_timer = 0.0
        self.count_num = 1

        if self.player_downs >= 3:
            self.state = STATE_DEAD
            self.state_timer = 0.0

    def knockdown_opponent(self):
        self.opp_action = OPP_DOWN
        self.opp_stamina = 0
        self.opp_downs += 1
        self.opp_timer = 0.0
        self.ref_count_timer = 0.0
        self.count_num = 1
        self.score += 1000

        if self.opp_downs >= 3:
            self.state = STATE_VICTORY
            self.state_timer = 0.0
            self.score += 3000
            if self.score > self.high_score:
                self.high_score = self.score

    def update(self, dt: float, buttons: int, prev_buttons: int):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 3.0:
                self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 3.0:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_opponent(dt)

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        if self.player_action == ACT_DOWN:
            self.ref_count_timer += dt
            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.player_stamina += 15
                if self.player_stamina >= 50:
                    self.player_action = ACT_IDLE
                    self.dodge_offset_x = 0.0
                    self.duck_offset_y = 0.0
            if self.ref_count_timer >= 1.0:
                self.ref_count_timer = 0.0
                self.count_num += 1
                if self.count_num > 10 and self.player_action == ACT_DOWN:
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
            return

        if self.player_action != ACT_IDLE:
            self.action_timer -= dt
            if self.action_timer <= 0.0:
                self.player_action = ACT_IDLE
                self.dodge_offset_x = 0.0
                self.duck_offset_y = 0.0

        if self.player_action == ACT_IDLE:
            if buttons & KEY_LEFT:
                self.dodge(-1)
            elif buttons & KEY_RIGHT:
                self.dodge(1)
            elif buttons & KEY_DOWN:
                self.dodge(0)
            elif buttons & KEY_UP:
                self.player_action = ACT_BLOCK
                self.action_timer = 0.25
            elif (buttons & KEY_A) and not (prev_buttons & KEY_A):
                self.punch(0)
            elif (buttons & KEY_B) and not (prev_buttons & KEY_B):
                self.punch(1)

    def update_opponent(self, dt: float):
        if self.opp_action == OPP_DOWN:
            self.ref_count_timer += dt
            if self.ref_count_timer >= 1.0:
                self.ref_count_timer = 0.0
                self.count_num += 1
                if self.count_num >= 7 and self.opp_downs < 3:
                    self.opp_action = OPP_IDLE
                    self.opp_stamina = 60
                    self.opp_timer = 1.0
                elif self.count_num > 10:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 3000
                    if self.score > self.high_score:
                        self.high_score = self.score
            return

        self.opp_timer -= dt

        if self.opp_action == OPP_IDLE:
            if self.opp_timer <= 0.0:
                import random
                r = random.randint(0, 2)
                if r == 0:
                    self.opp_action = OPP_PREP_LEFT_HOOK
                    self.opp_attack_type = 1
                    self.opp_timer = 0.40
                elif r == 1:
                    self.opp_action = OPP_PREP_RIGHT_HOOK
                    self.opp_attack_type = 2
                    self.opp_timer = 0.40
                else:
                    self.opp_action = OPP_PREP_BULL_CHARGE
                    self.opp_attack_type = 3
                    self.opp_timer = 0.55
        elif self.opp_action in (OPP_PREP_LEFT_HOOK, OPP_PREP_RIGHT_HOOK, OPP_PREP_BULL_CHARGE):
            if self.opp_timer <= 0.0:
                self.opp_action = OPP_SWING
                self.opp_timer = 0.20

                evaded = False
                if self.opp_attack_type == 1 and self.player_action == ACT_DODGE_RIGHT:
                    evaded = True
                if self.opp_attack_type == 2 and self.player_action == ACT_DODGE_LEFT:
                    evaded = True
                if self.opp_attack_type == 3 and self.player_action in (ACT_DODGE_LEFT, ACT_DODGE_RIGHT):
                    evaded = True
                if self.player_action == ACT_DUCK:
                    evaded = True

                if evaded:
                    self.opp_action = OPP_STUNNED
                    self.opp_timer = 0.75
                elif self.player_action == ACT_BLOCK:
                    self.player_stamina -= 8
                    if self.player_stamina <= 0:
                        self.knockdown_player()
                else:
                    damage = 35 if self.opp_attack_type == 3 else 25
                    self.player_stamina -= damage
                    self.player_action = ACT_HURT
                    self.action_timer = 0.35
                    if self.player_stamina <= 0:
                        self.knockdown_player()
        elif self.opp_action == OPP_SWING:
            if self.opp_timer <= 0.0:
                self.opp_action = OPP_IDLE
                self.opp_timer = 0.8
        elif self.opp_action in (OPP_STUNNED, OPP_HURT):
            if self.opp_timer <= 0.0:
                self.opp_action = OPP_IDLE
                self.opp_timer = 0.7

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Boxing ring ropes & canvas
        for y in range(16):
            for x in range(16):
                if y == 1:
                    set_pixel(x, y, 200, 20, 20)
                elif y == 2:
                    set_pixel(x, y, 220, 220, 220)
                elif y == 3:
                    set_pixel(x, y, 20, 40, 180)
                elif y > 3:
                    set_pixel(x, y, 15, 30, 70)
                else:
                    set_pixel(x, y, 5, 5, 12)

        set_pixel(0, 1, 255, 255, 0)
        set_pixel(15, 1, 255, 255, 0)

        # 2. HUD
        p_bars = max(0, min(6, (self.player_stamina * 6) // 100))
        for i in range(p_bars):
            set_pixel(i, 0, 40, 220, 40)

        o_bars = max(0, min(6, (self.opp_stamina * 6) // 100))
        for i in range(o_bars):
            set_pixel(15 - i, 0, 220, 30, 30)

        for s in range(self.stars):
            set_pixel(7 + s, 0, 255, 215, 0)

        # 3. Opponent Rendering
        if self.opp_action == OPP_DOWN:
            for x in range(5, 12):
                set_pixel(x, 6, 220, 150, 120)
                set_pixel(x, 7, 180, 40, 40)
        else:
            opp_base_y = 4
            flash_prep = self.opp_action in (OPP_PREP_LEFT_HOOK, OPP_PREP_RIGHT_HOOK, OPP_PREP_BULL_CHARGE) and (int(self.state_timer * 20.0) % 2 == 0)
            flash_stun = (self.opp_action == OPP_STUNNED) and (int(self.state_timer * 15.0) % 2 == 0)

            skin_r = 255 if flash_prep else (240 if flash_stun else 210)
            skin_g = 220 if flash_prep else (240 if flash_stun else 140)
            skin_b = 30 if flash_prep else (255 if flash_stun else 100)

            for dy in range(3):
                for dx in range(7, 10):
                    set_pixel(dx, opp_base_y + dy, skin_r, skin_g, skin_b)

            set_pixel(7, opp_base_y + 2, 40, 20, 10)
            set_pixel(9, opp_base_y + 2, 40, 20, 10)

            for dy in range(3, 5):
                for dx in range(6, 11):
                    set_pixel(dx, opp_base_y + dy, max(0, skin_r - 20), max(0, skin_g - 20), skin_b)

            for dx in range(6, 11):
                set_pixel(dx, opp_base_y + 5, 200, 20, 20)

            if self.opp_action == OPP_SWING:
                if self.opp_attack_type == 1:
                    set_pixel(6, opp_base_y + 5, 255, 30, 30)
                    set_pixel(6, opp_base_y + 6, 255, 30, 30)
                else:
                    set_pixel(10, opp_base_y + 5, 255, 30, 30)
                    set_pixel(10, opp_base_y + 6, 255, 30, 30)
            else:
                set_pixel(5, opp_base_y + 3, 220, 20, 20)
                set_pixel(11, opp_base_y + 3, 220, 20, 20)

        # 4. Player Rendering
        if self.player_action == ACT_DOWN:
            for x in range(6, 11):
                set_pixel(x, 14, 40, 180, 60)
        else:
            px = 8 + int(round(self.dodge_offset_x))
            py = 12 + int(round(self.duck_offset_y))

            set_pixel(px - 1, py - 2, 20, 20, 20)
            set_pixel(px, py - 2, 20, 20, 20)
            set_pixel(px + 1, py - 2, 20, 20, 20)

            set_pixel(px - 1, py - 1, 30, 160, 50)
            set_pixel(px, py - 1, 40, 180, 60)
            set_pixel(px + 1, py - 1, 30, 160, 50)

            set_pixel(px - 1, py, 20, 120, 40)
            set_pixel(px, py, 20, 120, 40)
            set_pixel(px + 1, py, 20, 120, 40)

            if self.player_action == ACT_PUNCH_LEFT:
                set_pixel(px - 1, py - 4, 80, 255, 80)
                set_pixel(px - 1, py - 3, 40, 200, 50)
                set_pixel(px + 1, py - 1, 40, 200, 50)
            elif self.player_action == ACT_PUNCH_RIGHT:
                set_pixel(px + 1, py - 4, 80, 255, 80)
                set_pixel(px + 1, py - 3, 40, 200, 50)
                set_pixel(px - 1, py - 1, 40, 200, 50)
            elif self.player_action == ACT_BLOCK:
                set_pixel(px - 1, py - 3, 80, 255, 80)
                set_pixel(px + 1, py - 3, 80, 255, 80)
            else:
                set_pixel(px - 2, py - 1, 80, 255, 80)
                set_pixel(px + 2, py - 1, 80, 255, 80)

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "player_stamina": self.player_stamina,
            "opp_stamina": self.opp_stamina,
            "player_downs": self.player_downs,
            "opp_downs": self.opp_downs,
            "stars": self.stars,
            "player_action": self.player_action,
            "opp_action": self.opp_action,
        }
