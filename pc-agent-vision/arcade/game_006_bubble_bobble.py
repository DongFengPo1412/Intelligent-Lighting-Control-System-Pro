# -*- coding: utf-8 -*-
"""game_006_bubble_bobble.py —— 目标 #006 泡泡捕敌 (Bubble Bobble)
平台跳跃 + 水平吐泡裹敌上浮 + 触碰戳破击杀掉水果 (严禁做成消除类泡泡龙!)
"""

from typing import Dict, Any, List, Tuple
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen, set_pixel

BUB_SHOOT = 0
BUB_FLOAT = 1


class BobbleEnemy:
    def __init__(self, x: float = 0.0, y: float = 0.0, vx: float = 0.0, jump_timer: float = 2.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = 0.0
        self.jump_timer = jump_timer
        self.on_ground = True
        self.trapped = False
        self.angry = False
        self.active = True


class BobbleShot:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.dist_left = 0.0
        self.timer = 0.0
        self.trapped_enemy = -1
        self.phase = BUB_SHOOT
        self.active = False


class BobbleFruit:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vy = 0.0
        self.timer = 0.0
        self.landed = False
        self.active = False


class Game006BubbleBobble(BaseCartridge):
    NUM_WAVES = 3
    MAX_ENEMIES = 3
    MAX_BUBBLES = 5
    MAX_FRUITS = 3

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self.wave_idx = 0
        self.lives = 3
        self.player_x = 2.0
        self.player_y = 13.0
        self.player_vy = 0.0
        self.facing_dir = 1
        self.on_ground = True
        self.shoot_cooldown = 0.0
        self.invuln_timer = 0.0
        self._score = 0
        self._high_score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.enemies: List[BobbleEnemy] = []
        self.bubbles: List[BobbleShot] = [BobbleShot() for _ in range(self.MAX_BUBBLES)]
        self.fruits: List[BobbleFruit] = [BobbleFruit() for _ in range(self.MAX_FRUITS)]
        self.reset()

    @property
    def game_id(self) -> int:
        return 6

    @property
    def name(self) -> str:
        return "泡泡捕敌"

    @property
    def english_name(self) -> str:
        return "Bubble Bobble"

    @property
    def release_year(self) -> int:
        return 1986

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "水平吐泡困敌上浮与触碰戳破变果"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _is_platform_top(self, x: int, plat_y: int) -> bool:
        if x < 1 or x > 14:
            return False
        if plat_y == 14:
            return True
        if plat_y == 10 and ((2 <= x <= 6) or (9 <= x <= 13)):
            return True
        if plat_y == 6 and (4 <= x <= 11):
            return True
        return False

    def _resolve_landing_y(self, x: float, old_y: float, new_y: float) -> Tuple[float, bool]:
        ix = int(round(x))
        for py in (6, 10, 14):
            stand_y = float(py - 1)
            if self._is_platform_top(ix, py) and old_y <= stand_y + 0.25 and new_y >= stand_y:
                return stand_y, True
        if new_y >= 13.0:
            return 13.0, True
        return new_y, False

    def load_wave(self, wave_idx: int, clear_fruits: bool = False) -> None:
        self.wave_idx = wave_idx
        for b in self.bubbles:
            b.active = False
        if clear_fruits:
            for f in self.fruits:
                f.active = False
            self.player_x = 2.0
            self.player_y = 13.0
            self.player_vy = 0.0
            self.facing_dir = 1
            self.on_ground = True

        self.shoot_cooldown = 0.0
        self.invuln_timer = 0.8

        if wave_idx == 0:
            self.enemies = [
                BobbleEnemy(6.0, 13.0, 2.2, 2.5),
                BobbleEnemy(10.0, 9.0, -2.2, 1.8),
            ]
        elif wave_idx == 1:
            self.enemies = [
                BobbleEnemy(12.0, 13.0, -2.6, 2.0),
                BobbleEnemy(4.0, 9.0, 2.5, 1.5),
                BobbleEnemy(8.0, 5.0, -2.5, 2.2),
            ]
        else:
            self.enemies = [
                BobbleEnemy(12.0, 13.0, -3.2, 1.6),
                BobbleEnemy(11.0, 9.0, -3.0, 1.2),
                BobbleEnemy(6.0, 5.0, 3.0, 1.9),
            ]

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.load_wave(0, True)
        self.invuln_timer = 0.0
        self._state = STATE_TITLE

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.load_wave(0, True)
            self.invuln_timer = 0.0
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _shoot_bubble(self) -> None:
        if self.shoot_cooldown > 0.0:
            return
        for b in self.bubbles:
            if not b.active:
                b.active = True
                bx = max(1.0, min(14.0, self.player_x + float(self.facing_dir) * 0.8))
                b.x = bx
                b.y = self.player_y
                b.vx = float(self.facing_dir) * 12.0
                b.dist_left = 5.0
                b.timer = 4.0
                b.trapped_enemy = -1
                b.phase = BUB_SHOOT
                self.shoot_cooldown = 0.22
                return

    def _spawn_fruit(self, x: float, y: float) -> None:
        for f in self.fruits:
            if not f.active:
                f.active = True
                f.x = x
                f.y = y
                f.vy = 0.0
                f.timer = 6.0
                f.landed = False
                return

    def _update_bubbles(self, dt: float) -> None:
        for b in self.bubbles:
            if not b.active:
                continue

            if b.phase == BUB_SHOOT:
                step = b.vx * dt
                b.x += step
                b.dist_left -= abs(step)
                if b.x <= 1.0:
                    b.x = 1.0
                    b.phase = BUB_FLOAT
                elif b.x >= 14.0:
                    b.x = 14.0
                    b.phase = BUB_FLOAT
                elif b.dist_left <= 0.0:
                    b.phase = BUB_FLOAT
            else:
                b.timer -= dt
                if b.timer <= 0.0:
                    if b.trapped_enemy >= 0:
                        e = self.enemies[b.trapped_enemy]
                        if e.active:
                            e.trapped = False
                            e.angry = True
                            e.x = b.x
                            e.y = b.y
                            e.vy = 0.0
                            e.on_ground = False
                            e.vx = 4.4 if e.vx >= 0.0 else -4.4
                    b.active = False
                    continue
                if b.y > 2.0:
                    b.y = max(2.0, b.y - 2.2 * dt)

            if b.trapped_enemy < 0:
                for idx, e in enumerate(self.enemies):
                    if e.active and not e.trapped:
                        if abs(b.x - e.x) <= 1.0 and abs(b.y - e.y) <= 1.0:
                            b.trapped_enemy = idx
                            b.phase = BUB_FLOAT
                            b.timer = 4.0
                            e.trapped = True
                            self._add_score(20)
                            break

            if b.trapped_enemy >= 0:
                e = self.enemies[b.trapped_enemy]
                e.x = b.x
                e.y = b.y

                if abs(self.player_x - b.x) <= 1.15 and abs(self.player_y - b.y) <= 1.15:
                    e.active = False
                    e.trapped = False
                    self._spawn_fruit(b.x, b.y)
                    b.active = False
                    self._add_score(100)
                    continue
            elif b.phase == BUB_FLOAT:
                if (
                    self.player_vy > 0.0
                    and abs(self.player_x - b.x) <= 0.9
                    and self.player_y < b.y
                    and (b.y - self.player_y) <= 1.15
                ):
                    self.player_vy = -13.5
                    self.on_ground = False
                    b.active = False

    def _update_fruits(self, dt: float) -> None:
        for f in self.fruits:
            if not f.active:
                continue
            f.timer -= dt
            if f.timer <= 0.0:
                f.active = False
                continue
            if not f.landed:
                old_y = f.y
                f.vy += 24.0 * dt
                new_y = f.y + f.vy * dt
                f.y, landed = self._resolve_landing_y(f.x, old_y, new_y)
                if landed:
                    f.landed = True
                    f.vy = 0.0
            if abs(self.player_x - f.x) <= 1.1 and abs(self.player_y - f.y) <= 1.1:
                f.active = False
                self._add_score(150)

    def _update_enemies(self, dt: float) -> None:
        alive_count = 0
        for e in self.enemies:
            if not e.active:
                continue
            alive_count += 1
            if e.trapped:
                continue

            e.x += e.vx * dt
            if e.x <= 1.0:
                e.x = 1.0
                e.vx = abs(e.vx)
            elif e.x >= 14.0:
                e.x = 14.0
                e.vx = -abs(e.vx)

            if e.on_ground:
                support_py = int(round(e.y)) + 1
                if not self._is_platform_top(int(round(e.x)), support_py):
                    e.on_ground = False
                else:
                    e.jump_timer -= dt
                    if e.jump_timer <= 0.0:
                        e.jump_timer = 1.4 if e.angry else 2.4
                        if self.player_y < e.y - 1.5:
                            e.vy = -15.2
                            e.on_ground = False

            if not e.on_ground:
                old_y = e.y
                e.vy += 28.0 * dt
                new_y = e.y + e.vy * dt
                if e.vy >= 0.0:
                    new_y, landed = self._resolve_landing_y(e.x, old_y, new_y)
                    if landed:
                        e.on_ground = True
                        e.vy = 0.0
                e.y = new_y

            if self.invuln_timer <= 0.0 and abs(self.player_x - e.x) <= 0.85 and abs(self.player_y - e.y) <= 0.85:
                if self.lives > 1:
                    self.lives -= 1
                    self.player_x = 2.0
                    self.player_y = 13.0
                    self.player_vy = 0.0
                    self.on_ground = True
                    self.invuln_timer = 1.2
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return

        if alive_count == 0:
            if self.wave_idx + 1 < self.NUM_WAVES:
                self.load_wave(self.wave_idx + 1, False)
            else:
                self._add_score(300)
                self._state = STATE_VICTORY
                self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
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

            if self.shoot_cooldown > 0.0:
                self.shoot_cooldown -= dt
            if self.invuln_timer > 0.0:
                self.invuln_timer -= dt

            move_speed = 6.8
            if keys_down & KEY_LEFT:
                self.player_x -= move_speed * dt
                self.facing_dir = -1
            elif keys_down & KEY_RIGHT:
                self.player_x += move_speed * dt
                self.facing_dir = 1
            self.player_x = max(1.0, min(14.0, self.player_x))

            if self.on_ground and (keys_pressed & (KEY_A | KEY_UP)):
                self.player_vy = -15.8
                self.on_ground = False

            if keys_pressed & KEY_B:
                self._shoot_bubble()

            if self.on_ground:
                support_py = int(round(self.player_y)) + 1
                if not self._is_platform_top(int(round(self.player_x)), support_py):
                    self.on_ground = False
                    self.player_vy = 0.0

            if not self.on_ground:
                old_y = self.player_y
                self.player_vy = min(14.0, self.player_vy + 28.0 * dt)
                new_y = self.player_y + self.player_vy * dt
                if new_y < 1.0:
                    new_y = 1.0
                    self.player_vy = 0.0
                if self.player_vy >= 0.0:
                    new_y, landed = self._resolve_landing_y(self.player_x, old_y, new_y)
                    if landed:
                        self.on_ground = True
                        self.player_vy = 0.0
                self.player_y = new_y

            self._update_bubbles(dt)
            self._update_fruits(dt)
            self._update_enemies(dt)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                if x in (0, 15):
                    set_pixel(fb, x, y, 95, 50, 130)
                else:
                    set_pixel(fb, x, y, 12, 10, 24)

        for x in range(1, 15):
            set_pixel(fb, x, 14, 155, 89, 182)
            set_pixel(fb, x, 15, 85, 45, 110)
            if self._is_platform_top(x, 10):
                set_pixel(fb, x, 10, 155, 89, 182)
            if self._is_platform_top(x, 6):
                set_pixel(fb, x, 6, 155, 89, 182)

        for f in self.fruits:
            if f.active:
                set_pixel(fb, int(round(f.x)), int(round(f.y)), 255, 165, 20)

        for e in self.enemies:
            if e.active and not e.trapped:
                ex, ey = int(round(e.x)), int(round(e.y))
                if e.angry:
                    set_pixel(fb, ex, ey, 255, 40, 40)
                else:
                    set_pixel(fb, ex, ey, 231, 95, 65)

        for b in self.bubbles:
            if not b.active:
                continue
            bx, by = int(round(b.x)), int(round(b.y))
            if b.trapped_enemy >= 0:
                set_pixel(fb, bx, by, 245, 220, 45)
            else:
                set_pixel(fb, bx, by, 70, 225, 255)

        if self.lives > 0 and (self.invuln_timer <= 0.0 or (int(self.anim_timer * 16.0) & 1) == 0):
            set_pixel(fb, int(round(self.player_x)), int(round(self.player_y)), 46, 240, 115)

        for i in range(min(3, self.lives)):
            set_pixel(fb, 1 + i, 0, 46, 240, 115)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": 100 if self._state == STATE_VICTORY else (self.wave_idx * 100) // self.NUM_WAVES,
        }
