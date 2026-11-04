# -*- coding: utf-8 -*-
"""game_075_slalom_ski.py —— 目标 #075 滑雪绕旗 (Alpine Slalom, 1982)
平滑横向刻滑惯性 + 顺坡直线加速物理 + 红蓝双旗门穿越连击与漏门罚分
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_TWO_BUTTON,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen


class SlalomGate:
    def __init__(self, y: float, left_x: float, right_x: float, is_red_left: bool):
        self.y = y
        self.left_x = left_x
        self.right_x = right_x
        self.is_red_left = is_red_left
        self.judged = False
        self.passed = False
        self.active = True


class SlopeObstacle:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.type = 0  # 0 = pine tree, 1 = mogul bump
        self.active = False


class Game075SlalomSki(BaseCartridge):
    MAX_GATES = 3
    MAX_OBSTACLES = 4
    TARGET_GATES = 20

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.skier_x = 7.5
        self.skier_y = 3.5
        self.skier_vx = 0.0
        self.downhill_speed = 8.5
        self.snow_scroll = 0.0
        self.gates: List[SlalomGate] = []
        self.obstacles: List[SlopeObstacle] = []
        self.gate_seq = 0
        self.gates_passed = 0
        self.missed_gates = 0
        self.combo = 0
        self.lives = 3
        self.time_penalty_s = 0.0
        self.invuln_timer = 0.0
        self.green_flash_timer = 0.0
        self.red_flash_timer = 0.0
        self.finish_active = False
        self.finish_banner_y = 20.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_state = 0x75751982
        self.reset()

    @property
    def game_id(self) -> int:
        return 75

    @property
    def name(self) -> str:
        return "滑雪绕旗"

    @property
    def english_name(self) -> str:
        return "Alpine Slalom"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_TWO_BUTTON

    @property
    def core_mechanic(self) -> str:
        return "横向刻滑惯性切弯顺坡加速与红蓝双旗门绕行"

    def _next_rand(self) -> int:
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._rng_state >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _spawn_obstacle_for_gate(self, gate_y: float, gate_left: float, gate_right: float) -> None:
        slot = -1
        for i in range(self.MAX_OBSTACLES):
            if not self.obstacles[i].active:
                slot = i
                break
        if slot < 0:
            return

        if gate_left > 6.5:
            obs_x = 2.0 + float(self._next_rand() % 3)
        else:
            obs_x = 11.5 + float(self._next_rand() % 3)

        if gate_left - 1.2 <= obs_x <= gate_right + 1.2:
            return

        obs = self.obstacles[slot]
        obs.x = obs_x
        obs.y = gate_y + 4.5
        obs.type = self._next_rand() % 2
        obs.active = True

    def _spawn_next_gate(self, slot: int, start_y: float) -> None:
        left_side = (self.gate_seq % 2) == 0
        jitter = float(self._next_rand() % 3) * 0.8
        lx = (2.5 + jitter) if left_side else (7.4 + jitter)
        rx = lx + 4.5

        self.gates[slot] = SlalomGate(start_y, lx, rx, left_side)
        self.gate_seq += 1
        self._spawn_obstacle_for_gate(start_y, lx, rx)

    def _init_game_data(self) -> None:
        self.skier_x = 7.5
        self.skier_y = 3.5
        self.skier_vx = 0.0
        self.downhill_speed = 8.5
        self.snow_scroll = 0.0
        self.gate_seq = 0
        self.gates_passed = 0
        self.missed_gates = 0
        self.combo = 0
        self.lives = 3
        self.time_penalty_s = 0.0
        self.invuln_timer = 0.0
        self.green_flash_timer = 0.0
        self.red_flash_timer = 0.0
        self.finish_active = False
        self.finish_banner_y = 20.0
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._rng_state = 0x75751982

        self.obstacles = [SlopeObstacle() for _ in range(self.MAX_OBSTACLES)]
        self.gates = [SlalomGate(0.0, 2.5, 7.0, True) for _ in range(self.MAX_GATES)]
        for i in range(self.MAX_GATES):
            self._spawn_next_gate(i, 12.0 + float(i) * 9.5)

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._init_game_data()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._init_game_data()
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt

        if self.invuln_timer > 0.0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
        if self.green_flash_timer > 0.0:
            self.green_flash_timer = max(0.0, self.green_flash_timer - dt)
        if self.red_flash_timer > 0.0:
            self.red_flash_timer = max(0.0, self.red_flash_timer - dt)

        if self._state == STATE_TITLE:
            self.snow_scroll = (self.snow_scroll + 6.0 * dt) % 16.0
            self.skier_x = 7.5 + math.sin(self.anim_timer * 2.5) * 3.0
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
                self.start()
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            carve_accel = 28.0
            if keys_down & KEY_LEFT:
                self.skier_vx -= carve_accel * dt
            elif keys_down & KEY_RIGHT:
                self.skier_vx += carve_accel * dt
            else:
                self.skier_vx *= (1.0 - 4.5 * dt)

            self.skier_vx = max(-9.5, min(9.5, self.skier_vx))
            self.skier_x += self.skier_vx * dt
            if self.skier_x < 1.2:
                self.skier_x = 1.2
                self.skier_vx = 0.0
            elif self.skier_x > 14.2:
                self.skier_x = 14.2
                self.skier_vx = 0.0

            align = 1.0 - min(1.0, abs(self.skier_vx) / 8.0)
            target_vy = 6.2 + 5.8 * align
            self.downhill_speed += (target_vy - self.downhill_speed) * 4.2 * dt

            dy = self.downhill_speed * dt
            self.snow_scroll = (self.snow_scroll + dy) % 16.0

            if self.finish_active:
                self.finish_banner_y -= dy
                if self.finish_banner_y <= self.skier_y:
                    self._add_score(200)
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                return

            max_gate_y = max((g.y for g in self.gates if g.active), default=0.0)

            for i, gate in enumerate(self.gates):
                if not gate.active:
                    continue
                gate.y -= dy

                if not gate.judged and gate.y <= self.skier_y:
                    gate.judged = True
                    if gate.left_x <= self.skier_x <= gate.right_x:
                        gate.passed = True
                        self.combo += 1
                        self.gates_passed += 1
                        mult = min(4, self.combo)
                        self._add_score(50 * mult)
                        self.green_flash_timer = 0.22

                        if self.gates_passed >= self.TARGET_GATES:
                            self.finish_active = True
                            self.finish_banner_y = self.skier_y + 4.0
                            return
                    else:
                        self.combo = 0
                        self.missed_gates += 1
                        self.time_penalty_s += 3.0
                        self.downhill_speed = 4.5
                        self.red_flash_timer = 0.25

                        if self.missed_gates >= 3:
                            self.lives = 0
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return

                if gate.y < -1.5:
                    next_y = max(16.5, max_gate_y + 9.5)
                    max_gate_y = next_y
                    self._spawn_next_gate(i, next_y)

            for obs in self.obstacles:
                if not obs.active:
                    continue
                obs.y -= dy
                if obs.y < -2.0:
                    obs.active = False
                    continue

                if abs(self.skier_x - obs.x) < 0.90 and abs(self.skier_y - obs.y) < 0.85:
                    if obs.type == 0:
                        obs.active = False
                        if self.invuln_timer <= 0.0:
                            self.combo = 0
                            self.red_flash_timer = 0.30
                            if self.lives > 1:
                                self.lives -= 1
                                self.invuln_timer = 0.80
                                self.skier_vx = 0.0
                                self.downhill_speed = 5.0
                            else:
                                self.lives = 0
                                self._state = STATE_GAMEOVER
                                self.state_timer = 0.0
                                return
                    else:
                        obs.active = False
                        self.downhill_speed *= 0.80
                        self.skier_vx += 2.2 if self.skier_x >= obs.x else -2.2

    @staticmethod
    def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < 16 and 0 <= y < 16:
            idx = (y * 16 + x) * 3
            fb[idx] = r
            fb[idx + 1] = g
            fb[idx + 2] = b

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        scroll_i = int(math.floor(self.snow_scroll))
        for y in range(16):
            for x in range(16):
                if x in (0, 15):
                    dark = ((y + scroll_i) % 3) == 0
                    self._set_px(fb, x, y, 15, 75 if dark else 105, 35)
                else:
                    sparkle = ((x * 5 + y + scroll_i) % 7) == 0
                    r = 185 if sparkle else 215
                    g = 225 if sparkle else 235
                    b = 252
                    if self.green_flash_timer > 0.0 and y == 1:
                        r, g, b = 46, 230, 110
                    elif self.red_flash_timer > 0.0 and y == 1:
                        r, g, b = 240, 60, 60
                    self._set_px(fb, x, y, r, g, b)

        for obs in self.obstacles:
            if not obs.active:
                continue
            ox = int(round(obs.x))
            oy = int(round(obs.y))
            if obs.type == 0:
                self._set_px(fb, ox, oy - 1, 20, 145, 45)
                self._set_px(fb, ox, oy, 15, 110, 35)
                self._set_px(fb, ox, oy + 1, 110, 65, 25)
            else:
                self._set_px(fb, ox, oy, 130, 175, 225)
                self._set_px(fb, ox + 1, oy, 150, 195, 240)

        for gate in self.gates:
            if not gate.active:
                continue
            gy = int(round(gate.y))
            lx = int(round(gate.left_x))
            rx = int(round(gate.right_x))
            for gx in range(lx + 1, rx):
                if gate.passed:
                    self._set_px(fb, gx, gy, 100, 240, 140)
                else:
                    self._set_px(fb, gx, gy, 175, 210, 245)

            if gate.is_red_left:
                self._set_px(fb, lx, gy, 245, 35, 35)
                self._set_px(fb, lx, gy - 1, 255, 80, 60)
                self._set_px(fb, rx, gy, 30, 90, 250)
                self._set_px(fb, rx, gy - 1, 70, 140, 255)
            else:
                self._set_px(fb, lx, gy, 30, 90, 250)
                self._set_px(fb, lx, gy - 1, 70, 140, 255)
                self._set_px(fb, rx, gy, 245, 35, 35)
                self._set_px(fb, rx, gy - 1, 255, 80, 60)

        if self.finish_active:
            fy = int(round(self.finish_banner_y))
            for x in range(1, 15):
                if (x % 2) == 0:
                    self._set_px(fb, x, fy, 255, 45, 45)
                else:
                    self._set_px(fb, x, fy, 255, 215, 0)

        sx = int(round(self.skier_x))
        sy = int(round(self.skier_y))
        lean = -1 if self.skier_vx < -2.0 else (1 if self.skier_vx > 2.0 else 0)
        self._set_px(fb, sx - lean, sy - 2, 165, 200, 235)
        self._set_px(fb, sx, sy - 1, 255, 210, 40)
        if self.invuln_timer <= 0.0 or math.fmod(self.anim_timer, 0.16) < 0.08:
            self._set_px(fb, sx, sy, 235, 45, 35)
            self._set_px(fb, sx + lean, sy + 1, 40, 120, 220)

        for x in range(16):
            self._set_px(fb, x, 0, 15, 25, 40)
        for l in range(min(3, self.lives)):
            self._set_px(fb, 1 + l * 2, 0, 46, 220, 113)
        for m in range(min(3, self.missed_gates)):
            self._set_px(fb, 14 - m * 2, 0, 245, 50, 50)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = min(100, (self.gates_passed * 100) // self.TARGET_GATES)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": prog,
        }
