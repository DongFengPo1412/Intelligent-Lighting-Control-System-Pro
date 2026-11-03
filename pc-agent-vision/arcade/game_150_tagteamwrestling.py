# -*- coding: utf-8 -*-
"""
Game #150: 双打职业摔角 (Tag Team Wrestling 1983 / Data East & Technos)
街机历史上摔角格斗游戏的奠基鼻祖：
擂台围绳弹性反弹冲撞、缠斗角力极速按键拼力摔投、
边绳拍手换人交替休息恢复体力、击倒压制裁判三秒数秒绝杀取胜。
"""

from typing import List, Dict, Any, Optional
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

STATE_NEUTRAL = 0
STATE_REBOUNDING = 1
STATE_GRAPPLE = 2
STATE_DOWNED = 3
STATE_PINFALL = 4
STATE_MATCH_WON = 5
STATE_MATCH_LOST = 6


class Game150TagTeamWrestling(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_NEUTRAL
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        # Player Team
        self.px = 6.0
        self.py = 8.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.p_hp = 100.0
        self.p_stamina = 100.0
        self.partner_hp = 100.0
        self.partner_active = False

        # Opponent Team
        self.ox = 10.0
        self.oy = 8.0
        self.ovx = 0.0
        self.ovy = 0.0
        self.o_hp = 100.0
        self.o_stamina = 100.0

        # Grapple tug-of-war meter (-50 to +50)
        self.grapple_meter = 0.0

        # Pinfall referee count
        self.pin_count = 0.0
        self.pinning_player = True  # True if player is pinning opponent

        self.reset()

    @property
    def game_id(self) -> int:
        return 150

    @property
    def name(self) -> str:
        return "双打职业摔角"

    @property
    def english_name(self) -> str:
        return "Tag Team Wrestling"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "擂台围绳弹射反冲、锁技角力连续按键拼力摔投、擂台边缘拍手换人接力救场与压制三秒数秒"

    def get_name(self) -> str:
        return "Tag Team Wrestling (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_match()

    def _init_match(self) -> None:
        self.state = STATE_NEUTRAL
        self.state_timer = 0.0

        self.px = 5.0
        self.py = 8.0
        self.pvx = 0.0
        self.pvy = 0.0
        self.p_hp = 100.0
        self.p_stamina = 100.0
        self.partner_hp = 100.0
        self.partner_active = False

        self.ox = 11.0
        self.oy = 8.0
        self.ovx = 0.0
        self.ovy = 0.0
        self.o_hp = 100.0
        self.o_stamina = 100.0

        self.grapple_meter = 0.0
        self.pin_count = 0.0
        self.pinning_player = True

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Regenerate partner on apron
        if not self.partner_active:
            self.partner_hp = min(100.0, self.partner_hp + dt * 4.0)
        else:
            self.p_hp = min(100.0, self.p_hp + dt * 4.0)

        if self.state == STATE_NEUTRAL:
            self._update_neutral(dt, buttons, prev_buttons)
        elif self.state == STATE_REBOUNDING:
            self._update_rebound(dt, buttons, prev_buttons)
        elif self.state == STATE_GRAPPLE:
            self._update_grapple(dt, buttons, prev_buttons)
        elif self.state == STATE_DOWNED:
            self._update_downed(dt, buttons, prev_buttons)
        elif self.state == STATE_PINFALL:
            self._update_pinfall(dt, buttons, prev_buttons)
        elif self.state in (STATE_MATCH_WON, STATE_MATCH_LOST):
            self.state_timer += dt
            if self.state_timer >= 2.0:
                if self.state == STATE_MATCH_WON:
                    self.level += 1
                    self._init_match()
                elif self.state == STATE_MATCH_LOST:
                    if self.lives > 0:
                        self._init_match()
                    else:
                        if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                            self.reset()

    def _update_neutral(self, dt: float, buttons: int, prev_buttons: int) -> None:
        speed = 5.0
        dx = 0.0
        dy = 0.0
        if buttons & KEY_LEFT:
            dx -= speed
        if buttons & KEY_RIGHT:
            dx += speed
        if buttons & KEY_UP:
            dy -= speed
        if buttons & KEY_DOWN:
            dy += speed

        # 1. Tag corner check: corner (2.5, 2.5) with Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.px <= 3.5 and self.py <= 3.5:
                # TAG PARTNER!
                self.partner_active = not self.partner_active
                # Swap current wrestler HP with partner HP
                self.p_hp, self.partner_hp = self.partner_hp, self.p_hp
                self.score += 300
                self.px = 4.5
                self.py = 4.5
                return

        # 2. Rope rebound trigger
        # Running into ropes gives slingshot momentum!
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            # Sprint towards rope or execute dropkick
            if dx != 0.0 or dy != 0.0:
                self.pvx = dx * 1.8
                self.pvy = dy * 1.8
                self.state = STATE_REBOUNDING
                return

        self.px += dx * dt
        self.py += dy * dt

        # Ring boundaries (Ropes: x in [2.5, 13.5], y in [2.5, 13.5])
        if self.px <= 2.5:
            self.px = 2.5
            if dx < 0:
                self.pvx = 9.0  # Elastic rope rebound!
                self.state = STATE_REBOUNDING
        elif self.px >= 13.5:
            self.px = 13.5
            if dx > 0:
                self.pvx = -9.0
                self.state = STATE_REBOUNDING

        if self.py <= 2.5:
            self.py = 2.5
            if dy < 0:
                self.pvy = 9.0
                self.state = STATE_REBOUNDING
        elif self.py >= 13.5:
            self.py = 13.5
            if dy > 0:
                self.pvy = -9.0
                self.state = STATE_REBOUNDING

        # Opponent AI tracks player
        odx = self.px - self.ox
        ody = self.py - self.oy
        dist = math.hypot(odx, ody)
        if dist > 0.8:
            o_speed = 3.2
            self.ox += (odx / dist) * o_speed * dt
            self.oy += (ody / dist) * o_speed * dt

        # Check grapple collision
        if math.hypot(self.px - self.ox, self.py - self.oy) < 0.9:
            self.state = STATE_GRAPPLE
            self.state_timer = 0.0
            self.grapple_meter = 0.0

    def _update_rebound(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.px += self.pvx * dt
        self.py += self.pvy * dt

        # Decay rebound velocity
        self.pvx *= 0.92
        self.pvy *= 0.92

        # Check flying clothesline collision with opponent
        if math.hypot(self.px - self.ox, self.py - self.oy) < 1.2:
            self.o_hp = max(0.0, self.o_hp - 25.0)
            self.score += 400
            self.ox = max(2.5, min(13.5, self.ox + (self.pvx * 0.3)))
            self.state = STATE_DOWNED
            self.state_timer = 0.0
            self.pinning_player = True
            return

        if abs(self.pvx) < 1.0 and abs(self.pvy) < 1.0:
            self.state = STATE_NEUTRAL

    def _update_grapple(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Rapid button mashing increases player grapple meter!
        if ((buttons & KEY_A) and not (prev_buttons & KEY_A)) or \
           ((buttons & KEY_B) and not (prev_buttons & KEY_B)):
            self.grapple_meter += 12.0

        # Opponent pushes back
        self.grapple_meter -= dt * 18.0

        if self.grapple_meter >= 35.0:
            # Player executes massive Brainbuster / Suplex!
            self.o_hp = max(0.0, self.o_hp - 20.0)
            self.score += 500
            self.state = STATE_DOWNED
            self.state_timer = 0.0
            self.pinning_player = True
        elif self.grapple_meter <= -35.0:
            # Opponent slams player!
            self.p_hp = max(0.0, self.p_hp - 20.0)
            self.state = STATE_DOWNED
            self.state_timer = 0.0
            self.pinning_player = False

    def _update_downed(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.state_timer += dt

        # If opponent is downed, player can pin them by standing close and pressing Key A!
        if self.pinning_player:
            # Player can walk to opponent
            if buttons & KEY_LEFT:
                self.px -= 4.0 * dt
            if buttons & KEY_RIGHT:
                self.px += 4.0 * dt
            if buttons & KEY_UP:
                self.py -= 4.0 * dt
            if buttons & KEY_DOWN:
                self.py += 4.0 * dt

            if (buttons & KEY_A) and not (prev_buttons & KEY_A):
                if math.hypot(self.px - self.ox, self.py - self.oy) < 1.4:
                    self.state = STATE_PINFALL
                    self.pin_count = 0.0
                    return

            # Opponent gets back up after 2.5 seconds
            if self.state_timer >= 2.5:
                self.state = STATE_NEUTRAL
        else:
            # Player is downed, gets up after 2.0 seconds
            if self.state_timer >= 2.0:
                self.state = STATE_NEUTRAL

    def _update_pinfall(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.pin_count += dt

        if self.pinning_player:
            # Referee counts: ONE... TWO... THREE!
            # Opponent tries to kick out if hp > 0
            kickout_chance = self.o_hp / 120.0
            if self.pin_count > 1.5 and kickout_chance > 0.4:
                # Opponent kicked out!
                self.state = STATE_NEUTRAL
                return

            if self.pin_count >= 3.0:
                # 3-COUNT! VICTORY BY PINFALL!
                self.score += 2500
                self.state = STATE_MATCH_WON
                self.state_timer = 0.0
        else:
            # Player is being pinned! Mash buttons to kick out!
            if ((buttons & KEY_A) and not (prev_buttons & KEY_A)) or \
               ((buttons & KEY_B) and not (prev_buttons & KEY_B)):
                if self.p_hp > 15.0:
                    self.state = STATE_NEUTRAL
                    return

            if self.pin_count >= 3.0:
                self.lives -= 1
                self.state = STATE_MATCH_LOST
                self.state_timer = 0.0

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(16 * 16 * 3):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Ring Canvas Mat (Light Blue Canvas)
        for y in range(3, 14):
            for x in range(3, 14):
                set_pixel(x, y, 40, 70, 110)

        # 2. Ring Elastic Ropes (White/Red ring borders)
        for x in range(2, 15):
            set_pixel(x, 2, 220, 220, 240)
            set_pixel(x, 14, 220, 220, 240)
        for y in range(2, 15):
            set_pixel(2, y, 220, 50, 50)
            set_pixel(14, y, 220, 50, 50)

        # 3. Corner Turnbuckles & Tag Apron
        set_pixel(2, 2, 50, 220, 50)   # Player tag corner!
        set_pixel(14, 2, 220, 50, 50)  # Opponent corner
        set_pixel(2, 14, 220, 220, 50)
        set_pixel(14, 14, 220, 220, 50)

        # 4. Waiting Apron Partner
        set_pixel(1, 2, 60, 180, 255)

        # 5. Active Opponent (Red Mask / Trunks)
        ox = int(round(self.ox))
        oy = int(round(self.oy))
        set_pixel(ox, oy, 230, 40, 40)
        set_pixel(ox, oy - 1, 240, 170, 130)  # Skin tone

        # 6. Active Player Wrestler (Blue Trunks & Boots)
        px = int(round(self.px))
        py = int(round(self.py))
        set_pixel(px, py, 30, 100, 240)
        set_pixel(px, py - 1, 240, 180, 140)

        # 7. Referee / Pinfall Indicator
        if self.state == STATE_PINFALL:
            # Referee counting on the mat
            ref_count = int(self.pin_count) + 1
            set_pixel(8, 8, 255, 255, 255)
            # Count dots
            for c in range(min(ref_count, 3)):
                set_pixel(7 + c, 7, 255, 220, 30)
        elif self.state == STATE_GRAPPLE:
            # Lock-up spark at center
            mid_x = int(round((self.px + self.ox) * 0.5))
            mid_y = int(round((self.py + self.oy) * 0.5))
            set_pixel(mid_x, mid_y, 255, 240, 50)

        # 8. Health Bars in top margin
        p_bar = int((self.p_hp / 100.0) * 5)
        for i in range(p_bar):
            set_pixel(i, 0, 40, 160, 255)

        o_bar = int((self.o_hp / 100.0) * 5)
        for i in range(o_bar):
            set_pixel(15 - i, 0, 255, 40, 40)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "px": self.px,
            "py": self.py,
            "p_hp": self.p_hp,
            "o_hp": self.o_hp,
            "partner_hp": self.partner_hp,
            "partner_active": self.partner_active,
            "grapple_meter": self.grapple_meter,
            "pin_count": self.pin_count,
        }

