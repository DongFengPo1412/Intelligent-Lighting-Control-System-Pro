"""
Game #105: 破坏者 / 经典打砖块进阶 (Arkanoid 1986 / Taito)
Vaus spaceship energy paddle, falling transformation capsules (Laser, Enlarge, Catch, Slow, Break),
multi-hit space bricks, and dimensional boss Doh showdown.
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

STATE_PLAYING = 0
STATE_BOSS_DOH = 1
STATE_BALL_LOST = 2
STATE_ROUND_CLEAR = 3
STATE_GAME_OVER = 4

CAPSULE_NONE = 0
CAPSULE_LASER = 1
CAPSULE_ENLARGE = 2
CAPSULE_CATCH = 3
CAPSULE_SLOW = 4
CAPSULE_BREAK = 5

BRICK_ROWS = 5
BRICK_COLS = 7
MAX_CAPSULES = 2
MAX_LASERS = 4


class Game105Arkanoid(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.round = 1
        self.bricks_remaining = 0

        self.paddle_x = 6.5
        self.paddle_width = 3
        self.active_powerup = CAPSULE_NONE
        self.laser_cooldown = 0.0

        self.ball_x = 7.5
        self.ball_y = 14.0
        self.ball_vx = 3.5
        self.ball_vy = -6.0
        self.ball_caught = True
        self.ball_catch_offset = 0.5

        self.bricks: List[List[int]] = []
        self.capsules: List[Dict[str, Any]] = []
        self.lasers: List[Dict[str, Any]] = []

        self.doh_hp = 12
        self.doh_x = 6.0
        self.doh_vx = 2.5
        self._cap_cycle = 0

        self.reset()

    @property
    def game_id(self) -> int:
        return 105

    @property
    def name(self) -> str:
        return "破坏者"

    @property
    def english_name(self) -> str:
        return "Arkanoid"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "激光飞船能量胶囊变异、磁性抓球蓄能发射、多诺巨像终极决战"

    def get_name(self) -> str:
        return "Arkanoid (1986)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.round = 1
        self._init_bricks()
        self._reset_ball()

    def _init_bricks(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.bricks_remaining = 0
        self.active_powerup = CAPSULE_NONE
        self.paddle_width = 3
        self.laser_cooldown = 0.0

        self.capsules = [
            {"x": 0.0, "y": 0.0, "type": CAPSULE_NONE, "active": False}
            for _ in range(MAX_CAPSULES)
        ]
        self.lasers = [
            {"x": 0.0, "y": 0.0, "active": False}
            for _ in range(MAX_LASERS)
        ]

        self.bricks = []
        for r in range(BRICK_ROWS):
            row = []
            for c in range(BRICK_COLS):
                if r == 0:
                    val = 9  # Silver
                elif r == 1:
                    val = 1  # Red
                elif r == 2:
                    val = 2  # Yellow
                elif r == 3:
                    val = 3  # Blue
                else:
                    val = 4  # Green
                row.append(val)
                self.bricks_remaining += 1
            self.bricks.append(row)

    def _reset_ball(self) -> None:
        self.paddle_x = 6.5
        self.ball_x = 7.5
        self.ball_y = 14.0
        self.ball_vx = 3.5
        self.ball_vy = -6.0
        self.ball_caught = True
        self.ball_catch_offset = 0.5

    def set_powerup(self, p_type: int) -> None:
        self.active_powerup = p_type
        if p_type == CAPSULE_ENLARGE:
            self.paddle_width = 5
        else:
            self.paddle_width = 3

        if p_type == CAPSULE_SLOW:
            self.ball_vx *= 0.6
            self.ball_vy *= 0.6

    def spawn_boss_doh(self) -> None:
        self.state = STATE_BOSS_DOH
        self.state_timer = 0.0
        self.doh_hp = 12
        self.doh_x = 6.0
        self.doh_vx = 2.5
        self.bricks = [[0 for _ in range(BRICK_COLS)] for _ in range(BRICK_ROWS)]
        self.bricks_remaining = 0

    def spawn_capsule(self, x: float, y: float) -> None:
        for cap in self.capsules:
            if not cap["active"]:
                cap["active"] = True
                cap["x"] = x
                cap["y"] = y
                cap["type"] = (self._cap_cycle % 5) + 1
                self._cap_cycle += 1
                break

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_BALL_LOST:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.active_powerup = CAPSULE_NONE
                    self.paddle_width = 3
                    self._reset_ball()
            return

        if self.state == STATE_ROUND_CLEAR:
            if self.state_timer > 2.2:
                self.round += 1
                if self.round >= 2:
                    self.spawn_boss_doh()
                else:
                    self._init_bricks()
                    self._reset_ball()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_paddle(dt, buttons, prev_buttons)
        self._update_ball(dt)
        self._update_capsules(dt)
        self._update_lasers(dt)

        if self.state == STATE_BOSS_DOH:
            self._update_boss_doh(dt)
        else:
            self._check_ball_brick_collision()
            self._check_laser_brick_collision()

            if self.bricks_remaining <= 0 and self.state != STATE_ROUND_CLEAR:
                self.state = STATE_ROUND_CLEAR
                self.state_timer = 0.0
                self.score += 1000

    def _update_paddle(self, dt: float, buttons: int, prev_buttons: int) -> None:
        move_spd = 12.0
        if buttons & KEY_LEFT:
            self.paddle_x = max(1.0, self.paddle_x - move_spd * dt)
        if buttons & KEY_RIGHT:
            max_x = 15.0 - float(self.paddle_width)
            self.paddle_x = min(max_x, self.paddle_x + move_spd * dt)

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.ball_caught:
                self.ball_caught = False
                self.ball_vy = -6.5
                self.ball_vx = (self.ball_catch_offset / (float(self.paddle_width) * 0.5)) * 4.5
            elif self.active_powerup == CAPSULE_LASER and self.laser_cooldown <= 0.0:
                self.laser_cooldown = 0.25
                for i in range(0, MAX_LASERS - 1, 2):
                    if not self.lasers[i]["active"] and not self.lasers[i + 1]["active"]:
                        self.lasers[i]["active"] = True
                        self.lasers[i]["x"] = self.paddle_x
                        self.lasers[i]["y"] = 14.0
                        self.lasers[i + 1]["active"] = True
                        self.lasers[i + 1]["x"] = self.paddle_x + float(self.paddle_width - 1)
                        self.lasers[i + 1]["y"] = 14.0
                        break

        self.laser_cooldown -= dt

    def _update_ball(self, dt: float) -> None:
        if self.ball_caught:
            self.ball_x = self.paddle_x + self.ball_catch_offset
            self.ball_y = 14.0
            return

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        if self.ball_x <= 1.0:
            self.ball_x = 1.0
            self.ball_vx = abs(self.ball_vx)
        elif self.ball_x >= 14.0:
            self.ball_x = 14.0
            self.ball_vx = -abs(self.ball_vx)

        if self.ball_y <= 1.0:
            self.ball_y = 1.0
            self.ball_vy = abs(self.ball_vy)

        if self.ball_y >= 15.5:
            self.state = STATE_BALL_LOST
            self.state_timer = 0.0
            return

        self._check_ball_paddle_collision()

    def _check_ball_paddle_collision(self) -> None:
        if self.ball_vy > 0.0 and 14.2 <= self.ball_y <= 15.2:
            rel_x = self.ball_x - self.paddle_x
            if -0.4 <= rel_x <= float(self.paddle_width) + 0.4:
                if self.active_powerup == CAPSULE_CATCH:
                    self.ball_caught = True
                    self.ball_catch_offset = max(0.0, min(float(self.paddle_width - 1), rel_x))
                    return

                self.ball_vy = -abs(self.ball_vy)
                center_diff = rel_x - (float(self.paddle_width) * 0.5)
                self.ball_vx = center_diff * 4.0
                if abs(self.ball_vx) < 1.0:
                    self.ball_vx = 1.5 if self.ball_vx >= 0.0 else -1.5

    def _check_ball_brick_collision(self) -> None:
        r = int(self.ball_y) - 2
        c = (int(self.ball_x) - 1) // 2
        if 0 <= r < BRICK_ROWS and 0 <= c < BRICK_COLS:
            if self.bricks[r][c] != 0:
                self.ball_vy = -self.ball_vy
                if self.bricks[r][c] == 9:
                    self.bricks[r][c] = 1
                    self.score += 50
                else:
                    self.bricks[r][c] = 0
                    self.bricks_remaining -= 1
                    self.score += 100
                    if (r + c) % 3 == 0:
                        self.spawn_capsule(float(c * 2 + 2), float(r + 2))

    def _check_laser_brick_collision(self) -> None:
        for l in self.lasers:
            if not l["active"]:
                continue
            r = int(l["y"]) - 2
            c = (int(l["x"]) - 1) // 2
            if 0 <= r < BRICK_ROWS and 0 <= c < BRICK_COLS:
                if self.bricks[r][c] != 0:
                    l["active"] = False
                    if self.bricks[r][c] == 9:
                        self.bricks[r][c] = 1
                    else:
                        self.bricks[r][c] = 0
                        self.bricks_remaining -= 1
                    self.score += 80

    def _update_capsules(self, dt: float) -> None:
        for cap in self.capsules:
            if not cap["active"]:
                continue
            cap["y"] += 4.0 * dt
            if 14.5 <= cap["y"] <= 15.5:
                if self.paddle_x - 0.5 <= cap["x"] <= self.paddle_x + float(self.paddle_width) + 0.5:
                    cap["active"] = False
                    self.score += 500
                    if cap["type"] == CAPSULE_BREAK:
                        self.state = STATE_ROUND_CLEAR
                        self.state_timer = 0.0
                    else:
                        self.set_powerup(cap["type"])
                    continue

            if cap["y"] > 16.0:
                cap["active"] = False

    def _update_lasers(self, dt: float) -> None:
        for l in self.lasers:
            if not l["active"]:
                continue
            l["y"] -= 20.0 * dt
            if l["y"] < 1.0:
                l["active"] = False

    def _update_boss_doh(self, dt: float) -> None:
        self.doh_x += self.doh_vx * dt
        if self.doh_x <= 3.0:
            self.doh_x = 3.0
            self.doh_vx = abs(self.doh_vx)
        elif self.doh_x >= 9.0:
            self.doh_x = 9.0
            self.doh_vx = -abs(self.doh_vx)

        if 2.0 <= self.ball_y <= 5.5:
            if self.doh_x - 0.5 <= self.ball_x <= self.doh_x + 5.0:
                self.ball_vy = abs(self.ball_vy)
                self.doh_hp -= 1
                self.score += 200
                if self.doh_hp <= 0:
                    self.state = STATE_ROUND_CLEAR
                    self.state_timer = 0.0
                    self.score += 5000

        for l in self.lasers:
            if not l["active"]:
                continue
            if 2.0 <= l["y"] <= 5.5:
                if self.doh_x <= l["x"] <= self.doh_x + 5.0:
                    l["active"] = False
                    self.doh_hp -= 1
                    self.score += 100
                    if self.doh_hp <= 0:
                        self.state = STATE_ROUND_CLEAR
                        self.state_timer = 0.0
                        self.score += 5000

    def render(self, fb: bytearray = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(len(fb)):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int):
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        for y in range(16):
            set_pixel(0, y, 160, 160, 180)
            set_pixel(15, y, 160, 160, 180)
        for x in range(16):
            set_pixel(x, 0, 160, 160, 180)

        for r in range(BRICK_ROWS):
            for c in range(BRICK_COLS):
                b = self.bricks[r][c]
                if b != 0:
                    bx = 1 + c * 2
                    by = 2 + r
                    br, bg, bb = 200, 40, 40
                    if b == 9:
                        br, bg, bb = 210, 210, 220
                    elif b == 2:
                        br, bg, bb = 240, 200, 20
                    elif b == 3:
                        br, bg, bb = 40, 100, 240
                    elif b == 4:
                        br, bg, bb = 30, 200, 50
                    set_pixel(bx, by, br, bg, bb)
                    set_pixel(bx + 1, by, br, bg, bb)

        if self.state == STATE_BOSS_DOH:
            dx = int(round(self.doh_x))
            for y in range(2, 6):
                for x in range(dx, dx + 4):
                    set_pixel(x, y, 180, 140, 100)
            set_pixel(dx + 1, 3, 255, 30, 20)
            set_pixel(dx + 2, 3, 255, 30, 20)

        for cap in self.capsules:
            if not cap["active"]:
                continue
            cx = int(round(cap["x"]))
            cy = int(round(cap["y"]))
            cr, cg, cb = 255, 255, 255
            if cap["type"] == CAPSULE_LASER:
                cr, cg, cb = 255, 40, 40
            elif cap["type"] == CAPSULE_ENLARGE:
                cr, cg, cb = 40, 120, 255
            elif cap["type"] == CAPSULE_CATCH:
                cr, cg, cb = 40, 220, 60
            elif cap["type"] == CAPSULE_SLOW:
                cr, cg, cb = 255, 160, 20
            elif cap["type"] == CAPSULE_BREAK:
                cr, cg, cb = 220, 40, 220
            set_pixel(cx, cy, cr, cg, cb)
            set_pixel(cx + 1, cy, cr, cg, cb)

        for l in self.lasers:
            if not l["active"]:
                continue
            lx = int(round(l["x"]))
            ly = int(round(l["y"]))
            set_pixel(lx, ly, 255, 40, 40)
            set_pixel(lx, ly + 1, 255, 180, 40)

        bx = int(round(self.ball_x))
        by = int(round(self.ball_y))
        set_pixel(bx, by, 255, 255, 255)

        px = int(round(self.paddle_x))
        for i in range(self.paddle_width):
            if self.active_powerup == CAPSULE_LASER:
                set_pixel(px + i, 15, 255, 40, 40)
            elif self.active_powerup == CAPSULE_ENLARGE:
                set_pixel(px + i, 15, 60, 140, 255)
            else:
                set_pixel(px + i, 15, 220, 220, 230)
        set_pixel(px + self.paddle_width // 2, 15, 255, 0, 0)

        for l in range(min(self.lives, 3)):
            set_pixel(2 + l * 2, 0, 255, 200, 0)

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
            "paddle_x": self.paddle_x,
            "paddle_width": self.paddle_width,
            "active_powerup": self.active_powerup,
            "ball_caught": self.ball_caught,
            "bricks_remaining": self.bricks_remaining,
            "doh_hp": self.doh_hp,
        }
