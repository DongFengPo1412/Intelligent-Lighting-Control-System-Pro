# -*- coding: utf-8 -*-
"""
game_026_whack_a_mole.py —— 像素打地鼠 1976 (Whack-A-Mole 1976)
编号: #026
年代: 1976 (南梦宫 Namco)
核心独占机制: 3x3 地洞多态探头 + 黄金地鼠与红刺炸弹鉴别 + 瞬时定点挥锤击打 + 倒计时反应力测试
手柄类型: CTRL_ARCADE_AB (方向键移动准星 + A/B键快速挥锤击打)
"""

import random
from typing import Dict, Any, List, Optional
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

MOLE_NORMAL = 0
MOLE_GOLDEN = 1
MOLE_BOMB = 2

HOLE_X = [3, 8, 13]
HOLE_Y = [3, 8, 13]


class Game026WhackAMole(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.cursor_row: int = 1
        self.cursor_col: int = 1
        self.hammer_anim_timer: float = 0.0
        self.lives: int = 3
        self.time_remaining: float = 45.0
        self.spawn_cooldown: float = 0.5

        self.holes: List[Dict[str, Any]] = []

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 26

    @property
    def name(self) -> str:
        return "像素打地鼠"

    @property
    def english_name(self) -> str:
        return "Whack-A-Mole 1976"

    @property
    def release_year(self) -> int:
        return 1976

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "3x3 地洞多态探头 + 黄金地鼠与红刺炸弹鉴别 + 瞬时定点挥锤击打 + 倒计时反应力测试"

    def init(self) -> None:
        self.reset()

    def init_holes(self):
        self.holes = []
        for r in range(3):
            for c in range(3):
                self.holes.append({
                    "cx": HOLE_X[c],
                    "cy": HOLE_Y[r],
                    "popped": False,
                    "type": MOLE_NORMAL,
                    "pop_timer": 0.0,
                    "whacked": False,
                })

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.time_remaining = 45.0
        self.cursor_row = 1
        self.cursor_col = 1
        self.hammer_anim_timer = 0.0
        self.spawn_cooldown = 0.5
        self.state_timer = 0.0
        self.init_holes()

    def spawn_mole(self):
        available = [i for i, h in enumerate(self.holes) if not h["popped"]]
        if available:
            idx = random.choice(available)
            h = self.holes[idx]
            h["popped"] = True
            h["whacked"] = False
            h["pop_timer"] = 1.0 + (random.randint(0, 4) / 10.0)

            roll = random.randint(0, 99)
            if roll < 65:
                h["type"] = MOLE_NORMAL
            elif roll < 80:
                h["type"] = MOLE_GOLDEN
            else:
                h["type"] = MOLE_BOMB

    def strike_hammer(self):
        self.hammer_anim_timer = 0.18
        idx = self.cursor_row * 3 + self.cursor_col
        h = self.holes[idx]

        if h["popped"] and not h["whacked"]:
            h["whacked"] = True
            if h["type"] == MOLE_NORMAL:
                self.score += 100
                if self.score > self.high_score:
                    self.high_score = self.score
            elif h["type"] == MOLE_GOLDEN:
                self.score += 300
                if self.score > self.high_score:
                    self.high_score = self.score
            elif h["type"] == MOLE_BOMB:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
                self.reset()
            return

        if self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            self.time_remaining -= dt
            if self.time_remaining <= 0.0:
                self.time_remaining = 0.0
                if self.score >= 1500:
                    self.state = STATE_VICTORY
                else:
                    self.state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

            if keys_pressed & KEY_UP:
                if self.cursor_row > 0:
                    self.cursor_row -= 1
            if keys_pressed & KEY_DOWN:
                if self.cursor_row < 2:
                    self.cursor_row += 1
            if keys_pressed & KEY_LEFT:
                if self.cursor_col > 0:
                    self.cursor_col -= 1
            if keys_pressed & KEY_RIGHT:
                if self.cursor_col < 2:
                    self.cursor_col += 1

            if self.hammer_anim_timer > 0.0:
                self.hammer_anim_timer -= dt

            if keys_pressed & (KEY_A | KEY_B):
                self.strike_hammer()

            self.spawn_cooldown -= dt
            if self.spawn_cooldown <= 0.0:
                self.spawn_cooldown = 0.65 + (random.randint(0, 3) / 10.0)
                self.spawn_mole()

            for h in self.holes:
                if h["popped"]:
                    h["pop_timer"] -= dt
                    if h["pop_timer"] <= 0.0:
                        h["popped"] = False
                        h["whacked"] = False

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        # 1. 草地
        for i in range(16 * 16):
            idx = i * 3
            buf[idx + 0] = 20
            buf[idx + 1] = 50
            buf[idx + 2] = 25

        # 2. 9 个洞穴与地鼠
        for r in range(3):
            for c in range(3):
                cx = HOLE_X[c]
                cy = HOLE_Y[r]
                idx = r * 3 + c
                h = self.holes[idx]

                for dy in (-1, 0):
                    for dx in (-1, 0):
                        px = cx + dx
                        py = cy + dy
                        if 0 <= px < 16 and 0 <= py < 16:
                            pidx = (py * 16 + px) * 3
                            buf[pidx + 0] = 35
                            buf[pidx + 1] = 25
                            buf[pidx + 2] = 18

                if h["popped"]:
                    if h["whacked"]:
                        cr, cg, cb = 255, 255, 255
                    elif h["type"] == MOLE_NORMAL:
                        cr, cg, cb = 180, 100, 40
                    elif h["type"] == MOLE_GOLDEN:
                        cr, cg, cb = 255, 215, 0
                    else:
                        cr, cg, cb = 231, 76, 60

                    px = cx - 1
                    py = cy - 1
                    pidx = (py * 16 + px) * 3
                    buf[pidx + 0] = cr
                    buf[pidx + 1] = cg
                    buf[pidx + 2] = cb

        # 3. 准星
        cur_cx = HOLE_X[self.cursor_col]
        cur_cy = HOLE_Y[self.cursor_row]

        hr = 255 if self.hammer_anim_timer > 0.0 else 0
        hg = 255
        hb = 50 if self.hammer_anim_timer > 0.0 else 255

        p1 = (cur_cy * 16 + cur_cx) * 3
        buf[p1 + 0] = hr
        buf[p1 + 1] = hg
        buf[p1 + 2] = hb

        # 4. HUD
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx + 0] = 231
            buf[idx + 1] = 76
            buf[idx + 2] = 60

        timer_len = int((self.time_remaining / 45.0) * 10.0)
        for i in range(timer_len):
            idx = (0 * 16 + (15 - i)) * 3
            buf[idx + 0] = 241
            buf[idx + 1] = 196
            buf[idx + 2] = 15

        # 5. 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx + 0] = 46
                buf[idx + 1] = 204
                buf[idx + 2] = 113
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx + 0] = 231
                buf[idx + 1] = 76
                buf[idx + 2] = 60

        return bytes(buf)

    def get_status(self) -> Dict[str, Any]:
        prog = int((self.score * 100) / 1500)
        prog = min(100, prog)
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": prog,
            "time_remaining": round(self.time_remaining, 1),
        }
