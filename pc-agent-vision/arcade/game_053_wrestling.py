"""
Game #053: 摔跤霸王 / 热血摔角 (The Main Event 1988 / Konami)
Pro Wrestling Ring Battle with Ropes Springboard Clotheslines, Collar Tie-Up Grapples & 1-2-3 Referee Pin Falls.
"""

import math
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
STATE_DEAD = 2
STATE_VICTORY = 3

MODE_NEUTRAL = 0
MODE_ROPE_BOUNCE = 1
MODE_GRAPPLE = 2
MODE_DOWNED = 3
MODE_PINNING = 4


class Game053Wrestling(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 3000

        self.player_x = 4.0
        self.player_y = 7.5
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_mode = MODE_NEUTRAL
        self.player_stamina = 100
        self.player_down_timer = 0.0

        self.opp_x = 11.0
        self.opp_y = 7.5
        self.opp_vx = 0.0
        self.opp_vy = 0.0
        self.opp_mode = MODE_NEUTRAL
        self.opp_stamina = 100
        self.opp_down_timer = 0.0
        self.opp_ai_timer = 0.0

        self.grapple_advantage = 0
        self.grapple_timer = 0.0
        self.pin_timer = 0.0
        self.referee_count = 0

        self.reset()

    @property
    def game_id(self) -> int:
        return 53

    @property
    def name(self) -> str:
        return "摔跤霸王"

    @property
    def english_name(self) -> str:
        return "The Main Event"

    @property
    def release_year(self) -> int:
        return 1988

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "封闭擂台绳圈反弹冲刺 + 贴身抓抱压制锁头 + 倒地 1-2-3 数秒绝杀"

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.init_match()

    def init_match(self):
        self.player_x = 4.0
        self.player_y = 7.5
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_mode = MODE_NEUTRAL
        self.player_stamina = 100
        self.player_down_timer = 0.0

        self.opp_x = 11.0
        self.opp_y = 7.5
        self.opp_vx = 0.0
        self.opp_vy = 0.0
        self.opp_mode = MODE_NEUTRAL
        self.opp_stamina = 100
        self.opp_down_timer = 0.0
        self.opp_ai_timer = 0.0

        self.grapple_advantage = 0
        self.grapple_timer = 0.0
        self.pin_timer = 0.0
        self.referee_count = 0

    def trigger_grapple_overpower(self):
        self.grapple_advantage = 3

    def trigger_pin_attempt(self):
        if self.opp_mode == MODE_DOWNED:
            self.player_mode = MODE_PINNING
            self.pin_timer = 0.0
            self.referee_count = 0

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_DEAD:
            if self.state_timer > 2.0:
                self.state = STATE_START
            return

        if self.state == STATE_VICTORY:
            if self.state_timer > 2.5:
                self.state = STATE_PLAYING
                self.state_timer = 0.0
                self.init_match()
            return

        if self.player_mode == MODE_GRAPPLE:
            self.update_grapple(dt, buttons, prev_buttons)
        elif self.player_mode == MODE_PINNING or self.opp_mode == MODE_PINNING:
            self.update_pinning(dt)
        else:
            self.update_player(dt, buttons, prev_buttons)
            self.update_opponent(dt)

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        if self.player_mode == MODE_DOWNED:
            self.player_down_timer -= dt
            if self.player_down_timer <= 0.0:
                self.player_mode = MODE_NEUTRAL
            return

        if self.player_mode == MODE_ROPE_BOUNCE:
            self.player_x += self.player_vx * dt
            self.player_y += self.player_vy * dt

            dist = math.hypot(self.player_x - self.opp_x, self.player_y - self.opp_y)
            if dist < 1.4 and self.opp_mode != MODE_DOWNED:
                self.opp_stamina -= 30
                self.opp_mode = MODE_DOWNED
                self.opp_down_timer = 3.0
                self.score += 150
                self.player_mode = MODE_NEUTRAL
                self.player_vx = 0.0
                self.player_vy = 0.0
                return

            self.player_down_timer += dt
            if self.player_down_timer > 0.6 or self.player_x < 2.5 or self.player_x > 12.5:
                self.player_mode = MODE_NEUTRAL
                self.player_vx = 0.0
                self.player_vy = 0.0
            return

        speed = 5.0
        self.player_vx = 0.0
        self.player_vy = 0.0

        if buttons & KEY_LEFT:  self.player_vx = -speed
        if buttons & KEY_RIGHT: self.player_vx = speed
        if buttons & KEY_UP:    self.player_vy = -speed
        if buttons & KEY_DOWN:  self.player_vy = speed

        self.player_x += self.player_vx * dt
        self.player_y += self.player_vy * dt

        # Rope bounce
        if self.player_x <= 2.5 and self.player_vx < 0.0:
            self.player_x = 2.5
            self.player_vx = 12.0
            self.player_mode = MODE_ROPE_BOUNCE
            self.player_down_timer = 0.0
            return
        elif self.player_x >= 12.5 and self.player_vx > 0.0:
            self.player_x = 12.5
            self.player_vx = -12.0
            self.player_mode = MODE_ROPE_BOUNCE
            self.player_down_timer = 0.0
            return

        self.player_x = max(2.5, min(12.5, self.player_x))
        self.player_y = max(2.5, min(12.5, self.player_y))

        dist = math.hypot(self.player_x - self.opp_x, self.player_y - self.opp_y)

        # Pin attempt
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.opp_mode == MODE_DOWNED and dist < 1.8:
                self.player_mode = MODE_PINNING
                self.pin_timer = 0.0
                self.referee_count = 0
                return

        # Grapple attempt
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.opp_mode == MODE_NEUTRAL and dist < 1.6:
                self.player_mode = MODE_GRAPPLE
                self.opp_mode = MODE_GRAPPLE
                self.grapple_advantage = 0
                self.grapple_timer = 0.0

    def update_opponent(self, dt: float):
        if self.opp_mode == MODE_DOWNED:
            self.opp_down_timer -= dt
            if self.opp_down_timer <= 0.0:
                self.opp_mode = MODE_NEUTRAL
            return

        if self.opp_mode == MODE_ROPE_BOUNCE:
            self.opp_x += self.opp_vx * dt
            self.opp_y += self.opp_vy * dt

            dist = math.hypot(self.opp_x - self.player_x, self.opp_y - self.player_y)
            if dist < 1.4 and self.player_mode != MODE_DOWNED:
                self.player_stamina -= 30
                self.player_mode = MODE_DOWNED
                self.player_down_timer = 3.0
                self.opp_mode = MODE_NEUTRAL
                self.opp_vx = 0.0
                self.opp_vy = 0.0
                return

            self.opp_down_timer += dt
            if self.opp_down_timer > 0.6 or self.opp_x < 2.5 or self.opp_x > 12.5:
                self.opp_mode = MODE_NEUTRAL
                self.opp_vx = 0.0
                self.opp_vy = 0.0
            return

        dx = self.player_x - self.opp_x
        dy = self.player_y - self.opp_y
        dist = math.hypot(dx, dy)

        if dist > 0.5:
            self.opp_x += (dx / dist) * 3.5 * dt
            self.opp_y += (dy / dist) * 3.5 * dt

        if self.player_mode == MODE_DOWNED and dist < 1.5:
            self.opp_mode = MODE_PINNING
            self.pin_timer = 0.0
            self.referee_count = 0

        self.opp_x = max(2.5, min(12.5, self.opp_x))
        self.opp_y = max(2.5, min(12.5, self.opp_y))

    def update_grapple(self, dt: float, buttons: int, prev_buttons: int):
        self.grapple_timer += dt

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.grapple_advantage += 1

        if self.grapple_timer >= 0.25:
            self.grapple_timer = 0.0
            self.grapple_advantage -= 1

        if self.grapple_advantage >= 3:
            self.opp_stamina -= 25
            self.opp_mode = MODE_DOWNED
            self.opp_down_timer = 3.0
            self.player_mode = MODE_NEUTRAL
            self.score += 100
            self.grapple_advantage = 0
        elif self.grapple_advantage <= -3:
            self.player_stamina -= 25
            self.player_mode = MODE_DOWNED
            self.player_down_timer = 3.0
            self.opp_mode = MODE_NEUTRAL
            self.grapple_advantage = 0

    def update_pinning(self, dt: float):
        self.pin_timer += dt
        if self.pin_timer >= 0.8:
            self.pin_timer = 0.0
            self.referee_count += 1

            if self.player_mode == MODE_PINNING:
                if self.referee_count < 3 and self.opp_stamina > 30:
                    self.opp_mode = MODE_NEUTRAL
                    self.player_mode = MODE_NEUTRAL
                    self.referee_count = 0
                    return
                if self.referee_count >= 3:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                    self.score += 1000
                    if self.score > self.high_score:
                        self.high_score = self.score
            elif self.opp_mode == MODE_PINNING:
                if self.referee_count < 3 and self.player_stamina > 30:
                    self.player_mode = MODE_NEUTRAL
                    self.opp_mode = MODE_NEUTRAL
                    self.referee_count = 0
                    return
                if self.referee_count >= 3:
                    self.state = STATE_DEAD
                    self.state_timer = 0.0

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if 2 <= x <= 13 and 2 <= y <= 13:
                    fb[idx] = 20
                    fb[idx + 1] = 40
                    fb[idx + 2] = 80
                    if x == 2 or x == 13 or y == 2 or y == 13:
                        fb[idx] = 200
                        fb[idx + 1] = 30
                        fb[idx + 2] = 30
                    if (x == 2 or x == 13) and (y == 2 or y == 13):
                        fb[idx] = 255
                        fb[idx + 1] = 255
                        fb[idx + 2] = 255
                else:
                    fb[idx] = 10
                    fb[idx + 1] = 10
                    fb[idx + 2] = 15

        # Opponent
        ox = int(round(self.opp_x))
        oy = int(round(self.opp_y))
        if 0 <= ox < 16 and 0 <= oy < 16:
            idx = (oy * 16 + ox) * 3
            if self.opp_mode == MODE_DOWNED:
                fb[idx] = 180
                fb[idx + 1] = 20
                fb[idx + 2] = 20
            else:
                fb[idx] = 255
                fb[idx + 1] = 50
                fb[idx + 2] = 50

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            if self.player_mode == MODE_DOWNED:
                fb[idx] = 180
                fb[idx + 1] = 160
                fb[idx + 2] = 20
            else:
                fb[idx] = 255
                fb[idx + 1] = 220
                fb[idx + 2] = 30

            if self.player_mode == MODE_GRAPPLE:
                fb[idx] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 255

        # Referee count
        if self.player_mode == MODE_PINNING or self.opp_mode == MODE_PINNING:
            for c in range(min(self.referee_count, 3)):
                idx = (7 + c) * 3
                fb[idx] = 255
                fb[idx + 1] = 255
                fb[idx + 2] = 0

        # Stamina HUD
        p_bars = (self.player_stamina * 5) // 100
        for i in range(min(p_bars, 5)):
            idx = (15 * 16 + i) * 3
            fb[idx] = 0
            fb[idx + 1] = 255
            fb[idx + 2] = 0

        o_bars = (self.opp_stamina * 5) // 100
        for i in range(min(o_bars, 5)):
            idx = (15 * 16 + (15 - i)) * 3
            fb[idx] = 255
            fb[idx + 1] = 0
            fb[idx + 2] = 0

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "player_mode": self.player_mode,
            "opp_mode": self.opp_mode,
            "player_stamina": self.player_stamina,
            "opp_stamina": self.opp_stamina,
            "referee_count": self.referee_count,
        }
