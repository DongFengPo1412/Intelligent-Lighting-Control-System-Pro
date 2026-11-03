"""game_026_space_invaders.py —— 目标 #026 太空侵略者 (Space Invaders 1978)
外星阵列编队下压 + 阵亡加速 + 激光炮台拦截
"""

import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen


class Alien:
    def __init__(self, r: int, g: int, b: int, score_val: int):
        self.alive = True
        self.r = r
        self.g = g
        self.b = b
        self.score_val = score_val


class Bullet:
    def __init__(self, x: float, y: float, vy: float):
        self.active = True
        self.x = x
        self.y = y
        self.vy = vy


class Game026SpaceInvaders(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.player_x = 7.0
        self.lives = 3
        self.fleet: List[List[Alien]] = []
        self.fleet_x = 1
        self.fleet_y = 1
        self.fleet_dir = 1
        self.fleet_step_timer = 0.0
        self.fleet_step_interval = 0.6
        self.remaining_aliens = 12
        self.bullets: List[Bullet] = []
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 26

    @property
    def name(self) -> str:
        return "太空侵略者"

    @property
    def english_name(self) -> str:
        return "Space Invaders 1978"

    @property
    def release_year(self) -> int:
        return 1978

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "外星编队下压加速与火炮拦截"

    def init(self) -> None:
        self.reset()

    def _reset_fleet(self):
        self.remaining_aliens = 12
        self.fleet = []
        colors = [
            (255, 0, 128, 30),
            (241, 196, 15, 20),
            (0, 255, 255, 10),
        ]
        for r in range(3):
            cr, cg, cb, val = colors[r]
            row = [Alien(cr, cg, cb, val) for _ in range(4)]
            self.fleet.append(row)
        self.fleet_x = 1
        self.fleet_y = 1
        self.fleet_dir = 1
        self.fleet_step_timer = 0.0
        self.fleet_step_interval = 0.6

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.player_x = 7.0
        self.bullets = []
        self._reset_fleet()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.player_x = 7.0
            self.bullets = []
            self._reset_fleet()

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _fire_player_bullet(self):
        for b in self.bullets:
            if b.active and b.vy < 0:
                return
        self.bullets.append(Bullet(self.player_x, 13.0, -18.0))

    def _spawn_alien_bomb(self):
        cols = []
        for c in range(4):
            for r in range(2, -1, -1):
                if self.fleet[r][c].alive:
                    cols.append(c)
                    break
        if not cols:
            return
        c = random.choice(cols)
        row = -1
        for r in range(2, -1, -1):
            if self.fleet[r][c].alive:
                row = r
                break
        if row != -1:
            self.bullets.append(Bullet(float(self.fleet_x + c * 3 + 1), float(self.fleet_y + row * 2 + 1), 9.0))

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            self.fleet_step_timer += dt
            if self.fleet_step_timer >= 0.5:
                self.fleet_step_timer = 0.0
                self.fleet_x += self.fleet_dir
                if self.fleet_x <= 0 or self.fleet_x >= 4:
                    self.fleet_dir = -self.fleet_dir
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
                self.start()
            return

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            speed = 11.0
            if keys_down & KEY_LEFT:
                self.player_x -= speed * dt
            elif keys_down & KEY_RIGHT:
                self.player_x += speed * dt
            self.player_x = max(1.0, min(14.0, self.player_x))

            if keys_pressed & (KEY_A | KEY_B | KEY_UP):
                self._fire_player_bullet()

            self.fleet_step_timer += dt
            if self.fleet_step_timer >= self.fleet_step_interval:
                self.fleet_step_timer = 0.0
                reach_wall = False
                for c in range(4):
                    for r in range(3):
                        if self.fleet[r][c].alive:
                            ax = self.fleet_x + c * 3
                            if (self.fleet_dir > 0 and ax >= 12) or (self.fleet_dir < 0 and ax <= 0):
                                reach_wall = True
                                break
                    if reach_wall:
                        break

                if reach_wall:
                    self.fleet_dir = -self.fleet_dir
                    self.fleet_y += 1
                    if self.fleet_y >= 10:
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                else:
                    self.fleet_x += self.fleet_dir

                if random.random() < 0.45:
                    self._spawn_alien_bomb()

            for b in self.bullets:
                if b.active:
                    b.y += b.vy * dt
                    if b.vy < 0:
                        for r in range(3):
                            for c in range(4):
                                if self.fleet[r][c].alive:
                                    ax = self.fleet_x + c * 3
                                    ay = self.fleet_y + r * 2
                                    if abs(b.x - ax) < 1.2 and abs(b.y - ay) < 1.0:
                                        self.fleet[r][c].alive = False
                                        b.active = False
                                        self.remaining_aliens -= 1
                                        self._score += self.fleet[r][c].score_val
                                        if self._score > self._high_score:
                                            self._high_score = self._score
                                        self.fleet_step_interval = 0.15 + self.remaining_aliens * 0.035
                                        if self.remaining_aliens <= 0:
                                            self._state = STATE_VICTORY
                                            self.state_timer = 0.0
                                            return
                                        break
                            if not b.active:
                                break
                    else:
                        if abs(b.x - self.player_x) < 1.4 and b.y >= 13.5:
                            b.active = False
                            if self.lives > 1:
                                self.lives -= 1
                            else:
                                self.lives = 0
                                self._state = STATE_GAMEOVER
                                self.state_timer = 0.0
                                return

                    if b.y < 0.0 or b.y > 15.5:
                        b.active = False

            self.bullets = [b for b in self.bullets if b.active]

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for r in range(3):
            for c in range(4):
                if self.fleet[r][c].alive:
                    ax = self.fleet_x + c * 3
                    ay = self.fleet_y + r * 2
                    if 0 <= ay < 16:
                        for dx in (0, 1):
                            x = ax + dx
                            if 0 <= x < 16:
                                idx = (ay * 16 + x) * 3
                                fb[idx : idx + 3] = bytes(
                                    [self.fleet[r][c].r, self.fleet[r][c].g, self.fleet[r][c].b]
                                )

        px = int(round(self.player_x))
        if 1 <= px < 15:
            idx_top = (14 * 16 + px) * 3
            fb[idx_top : idx_top + 3] = bytes([46, 204, 113])
            for dx in (-1, 0, 1):
                idx = (15 * 16 + (px + dx)) * 3
                fb[idx : idx + 3] = bytes([39, 174, 96])

        for b in self.bullets:
            if b.active:
                bx = int(round(b.x))
                by = int(round(b.y))
                if 0 <= bx < 16 and 0 <= by < 16:
                    idx = (by * 16 + bx) * 3
                    if b.vy < 0:
                        fb[idx : idx + 3] = bytes([255, 255, 255])
                    else:
                        fb[idx : idx + 3] = bytes([231, 76, 60])

        for i in range(min(3, self.lives)):
            idx = (i * 2) * 3
            fb[idx : idx + 3] = bytes([46, 204, 113])

        if self._state == STATE_PAUSED:
            for y in range(6, 10):
                for col in (6, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([250, 250, 250])

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (12 - self.remaining_aliens) * 100 // 12),
        }
