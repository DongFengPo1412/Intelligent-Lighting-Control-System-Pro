# -*- coding: utf-8 -*-
"""game_005_lode_runner.py —— 目标 #005 挖洞夺金 (Lode Runner)
平台攀梯 + 左右掘砖坑诱捕守卫 + 砖块定时再生 + 夺金开启逃生梯
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
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

LR_AIR    = 0
LR_BRICK  = 1
LR_SOLID  = 2
LR_LADDER = 3
LR_BAR    = 4
LR_HOLE   = 5


class LodeGold:
    def __init__(self, x: int = 0, y: int = 0, collected: bool = False):
        self.x = x
        self.y = y
        self.collected = collected


class LodeHole:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.timer = 0.0
        self.active = False


class LodeGuard:
    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y
        self.spawn_x = x
        self.spawn_y = y
        self.move_timer = 0.0
        self.trap_timer = 0.0
        self.trapped = False
        self.active = True


class Game005LodeRunner(BaseCartridge):
    NUM_LEVELS = 2
    MAX_GOLD = 3
    MAX_HOLES = 6
    MAX_GUARDS = 2

    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self.level_idx = 0
        self.lives = 3
        self.player_x = 6
        self.player_y = 10
        self.player_dir = 1
        self.move_cooldown = 0.0
        self.fall_timer = 0.0
        self.escape_revealed = False
        self.escape_x = 1
        self._score = 0
        self._high_score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.grid: List[List[int]] = [[LR_AIR] * 16 for _ in range(16)]
        self.golds: List[LodeGold] = []
        self.holes: List[LodeHole] = [LodeHole() for _ in range(self.MAX_HOLES)]
        self.guards: List[LodeGuard] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 5

    @property
    def name(self) -> str:
        return "挖洞夺金"

    @property
    def english_name(self) -> str:
        return "Lode Runner"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "左右掘砖陷坑困敌与夺金攀梯逃脱"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _respawn_actors(self) -> None:
        self.player_x = 6
        self.player_y = 10
        self.player_dir = 1
        self.move_cooldown = 0.0
        self.fall_timer = 0.0

        for h in self.holes:
            if h.active:
                self.grid[h.y][h.x] = LR_BRICK
                h.active = False

        for g in self.guards:
            g.x = g.spawn_x
            g.y = g.spawn_y
            g.move_timer = 0.0
            g.trap_timer = 0.0
            g.trapped = False

    def load_level(self, level_idx: int) -> None:
        self.level_idx = level_idx
        self.grid = [[LR_AIR] * 16 for _ in range(16)]
        for h in self.holes:
            h.active = False
        self.escape_revealed = False

        for x in range(16):
            self.grid[15][x] = LR_SOLID

        if level_idx == 0:
            for x in range(0, 13):
                self.grid[11][x] = LR_BRICK
            for x in range(3, 16):
                self.grid[7][x] = LR_BRICK
            for x in range(0, 12):
                self.grid[3][x] = LR_BRICK

            for y in range(11, 15):
                self.grid[y][11] = LR_LADDER
            for y in range(7, 11):
                self.grid[y][4] = LR_LADDER
            for y in range(3, 7):
                self.grid[y][9] = LR_LADDER

            for x in range(10, 14):
                self.grid[5][x] = LR_BAR

            self.golds = [LodeGold(2, 10, False), LodeGold(14, 6, False), LodeGold(5, 2, False)]
            self.escape_x = 1
            self.guards = [LodeGuard(14, 14), LodeGuard(13, 6)]
        else:
            for x in range(2, 16):
                self.grid[11][x] = LR_BRICK
            for x in range(0, 13):
                self.grid[7][x] = LR_BRICK
            for x in range(3, 16):
                self.grid[3][x] = LR_BRICK

            for y in range(11, 15):
                self.grid[y][3] = LR_LADDER
            for y in range(7, 11):
                self.grid[y][11] = LR_LADDER
            for y in range(3, 7):
                self.grid[y][5] = LR_LADDER

            for x in range(1, 5):
                self.grid[5][x] = LR_BAR

            self.golds = [LodeGold(13, 10, False), LodeGold(2, 6, False), LodeGold(12, 2, False)]
            self.escape_x = 14
            self.guards = [LodeGuard(1, 14), LodeGuard(2, 6)]

        self._respawn_actors()

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.load_level(0)
        self._state = STATE_TITLE

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.load_level(0)
            self._state = STATE_PLAYING

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _can_walk(self, x: int, y: int) -> bool:
        if x < 0 or x >= 16 or y < 0 or y >= 16:
            return False
        return self.grid[y][x] in (LR_AIR, LR_LADDER, LR_BAR, LR_HOLE)

    def _can_fall(self, x: int, y: int) -> bool:
        if y >= 14:
            return False
        cur = self.grid[y][x]
        if cur in (LR_LADDER, LR_BAR):
            return False
        below = self.grid[y + 1][x]
        if below in (LR_SOLID, LR_BRICK, LR_LADDER):
            return False
        if below in (LR_AIR, LR_HOLE):
            for g in self.guards:
                if g.active and g.trapped and g.x == x and g.y == y + 1:
                    return False
            return True
        return False

    def _try_dig_at(self, hx: int, hy: int) -> bool:
        if hx < 0 or hx >= 16 or hy < 1 or hy >= 16:
            return False
        if self.grid[hy][hx] != LR_BRICK:
            return False
        if self.grid[hy - 1][hx] not in (LR_AIR, LR_BAR):
            return False
        for h in self.holes:
            if not h.active:
                h.active = True
                h.x = hx
                h.y = hy
                h.timer = 4.0
                self.grid[hy][hx] = LR_HOLE
                self._add_score(10)
                return True
        return False

    def _dig_side(self, preferred_dx: int) -> None:
        hy = self.player_y + 1
        if self._try_dig_at(self.player_x + preferred_dx, hy):
            return
        if preferred_dx == -1 and self.player_dir != -1:
            self._try_dig_at(self.player_x + self.player_dir, hy)

    def _update_holes(self, dt: float) -> None:
        for h in self.holes:
            if not h.active:
                continue
            h.timer -= dt
            if h.timer <= 0.0:
                hx, hy = h.x, h.y
                h.active = False
                self.grid[hy][hx] = LR_BRICK

                for g in self.guards:
                    if g.active and g.x == hx and g.y == hy:
                        g.trapped = False
                        g.trap_timer = 0.0
                        g.x = 7
                        g.y = 1
                        self._add_score(100)

                if self.player_x == hx and self.player_y == hy:
                    if self.lives > 1:
                        self.lives -= 1
                        self._respawn_actors()
                        return
                    else:
                        self.lives = 0
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

    def _update_guards(self, dt: float) -> None:
        for g in self.guards:
            if not g.active:
                continue
            gx, gy = g.x, g.y

            if g.trapped:
                g.trap_timer -= dt
                if g.trap_timer <= 0.0:
                    g.trapped = False
                    if gy > 0 and self._can_walk(gx, gy - 1):
                        g.y = gy - 1
                continue

            if self.grid[gy][gx] == LR_HOLE:
                g.trapped = True
                g.trap_timer = 3.2
                self._add_score(50)
                continue

            if self._can_fall(gx, gy):
                g.move_timer += dt
                if g.move_timer >= 0.12:
                    g.move_timer = 0.0
                    g.y += 1
                    if self.grid[g.y][g.x] == LR_HOLE:
                        g.trapped = True
                        g.trap_timer = 3.2
                        self._add_score(50)
                continue

            g.move_timer += dt
            if g.move_timer >= 0.28:
                g.move_timer = 0.0
                dx, dy = 0, 0
                if gy < self.player_y and (
                    self.grid[gy][gx] == LR_LADDER
                    or (gy + 1 < 16 and self.grid[gy + 1][gx] == LR_LADDER)
                    or self.grid[gy][gx] == LR_BAR
                ):
                    dy = 1
                elif gy > self.player_y and self.grid[gy][gx] == LR_LADDER:
                    dy = -1
                elif gx < self.player_x:
                    dx = 1
                elif gx > self.player_x:
                    dx = -1

                if dy != 0 and self._can_walk(gx, gy + dy):
                    g.y = gy + dy
                elif dx != 0 and self._can_walk(gx + dx, gy):
                    g.x = gx + dx

            if not g.trapped and g.x == self.player_x and g.y == self.player_y:
                if self.lives > 1:
                    self.lives -= 1
                    self._respawn_actors()
                    return
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN):
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

            if self.move_cooldown > 0.0:
                self.move_cooldown = max(0.0, self.move_cooldown - dt)

            if keys_pressed & KEY_A:
                self._dig_side(-1)
            if keys_pressed & KEY_B:
                self._dig_side(1)

            if self._can_fall(self.player_x, self.player_y):
                self.fall_timer += dt
                if self.fall_timer >= 0.09:
                    self.fall_timer = 0.0
                    self.player_y += 1
            else:
                self.fall_timer = 0.0
                dir_press = keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)
                if dir_press != 0 or self.move_cooldown <= 0.0:
                    dx, dy = 0, 0
                    src = dir_press if dir_press != 0 else keys_down
                    if src & KEY_UP:
                        dy = -1
                    elif src & KEY_DOWN:
                        dy = 1
                    elif src & KEY_LEFT:
                        dx = -1
                    elif src & KEY_RIGHT:
                        dx = 1

                    if dx != 0 or dy != 0:
                        if dy < 0:
                            if self.grid[self.player_y][self.player_x] == LR_LADDER and self._can_walk(
                                self.player_x, self.player_y - 1
                            ):
                                self.player_y -= 1
                                self.move_cooldown = 0.13
                        elif dy > 0:
                            can_descend = (
                                self.grid[self.player_y][self.player_x] in (LR_LADDER, LR_BAR)
                                or (self.player_y + 1 < 16 and self.grid[self.player_y + 1][self.player_x] == LR_LADDER)
                            )
                            if can_descend and self._can_walk(self.player_x, self.player_y + 1):
                                self.player_y += 1
                                self.move_cooldown = 0.13
                        elif dx != 0:
                            self.player_dir = 1 if dx > 0 else -1
                            if self._can_walk(self.player_x + dx, self.player_y):
                                self.player_x += dx
                                self.move_cooldown = 0.13

            all_gold = True
            for g in self.golds:
                if not g.collected:
                    if self.player_x == g.x and self.player_y == g.y:
                        g.collected = True
                        self._add_score(100)
                    else:
                        all_gold = False

            if all_gold and not self.escape_revealed:
                self.escape_revealed = True
                for y in range(0, 4):
                    self.grid[y][self.escape_x] = LR_LADDER
                self._add_score(150)

            if self.escape_revealed and self.player_x == self.escape_x and self.player_y == 0:
                self._add_score(200)
                if self.level_idx + 1 < self.NUM_LEVELS:
                    self.load_level(self.level_idx + 1)
                else:
                    self._add_score(300)
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                return

            self._update_holes(dt)
            if self._state != STATE_PLAYING:
                return
            self._update_guards(dt)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        for y in range(16):
            for x in range(16):
                t = self.grid[y][x]
                if t == LR_BRICK:
                    set_pixel(fb, x, y, 185, 78, 38)
                elif t == LR_SOLID:
                    set_pixel(fb, x, y, 110, 125, 135)
                elif t == LR_LADDER:
                    set_pixel(fb, x, y, 52, 160, 225)
                elif t == LR_BAR:
                    set_pixel(fb, x, y, 200, 190, 90)
                elif t == LR_HOLE:
                    set_pixel(fb, x, y, 28, 16, 12)
                else:
                    set_pixel(fb, x, y, 8, 10, 18)

        for g in self.golds:
            if not g.collected:
                set_pixel(fb, g.x, g.y, 255, 215, 0)

        for g in self.guards:
            if not g.active:
                continue
            if g.trapped:
                set_pixel(fb, g.x, g.y, 180, 50, 160)
            else:
                set_pixel(fb, g.x, g.y, 235, 65, 55)

        if self.lives > 0:
            set_pixel(fb, self.player_x, self.player_y, 255, 255, 255)

        for i in range(min(3, self.lives)):
            set_pixel(fb, 15 - i, 0, 46, 230, 120)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        gathered = sum(1 for g in self.golds if g.collected)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": 100
            if self._state == STATE_VICTORY
            else ((self.level_idx * self.MAX_GOLD + gathered) * 100) // (self.NUM_LEVELS * self.MAX_GOLD),
        }
