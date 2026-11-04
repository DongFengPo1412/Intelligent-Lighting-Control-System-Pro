# -*- coding: utf-8 -*-
"""game_066_battleship.py —— 目标 #066 海战棋 (Battleship, 1979)
双 8x8 海战雷达/己方舰队切换 + 四舰隐蔽部署 + 命中连射与击沉闪光 + 猎杀锁定 AI
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

GRID_SIZE = 8
NUM_SHIPS = 4
TOTAL_DECK_CELLS = 11
SHIP_LENGTHS = (4, 3, 2, 2)

SHOT_UNTARGETED = 0
SHOT_MISS = 1
SHOT_HIT = 2
SHOT_SUNK = 3


def _set_px(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


class NavalShip:
    def __init__(self, x: int = 0, y: int = 0, length: int = 2, horiz: bool = True):
        self.x = x
        self.y = y
        self.len = length
        self.horiz = 1 if horiz else 0
        self.hits = 0


class Game066Battleship(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.player_grid: List[List[int]] = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.ai_grid: List[List[int]] = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.player_shots: List[List[int]] = [[SHOT_UNTARGETED] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.ai_shots: List[List[int]] = [[SHOT_UNTARGETED] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.player_ships: List[NavalShip] = [NavalShip() for _ in range(NUM_SHIPS)]
        self.ai_ships: List[NavalShip] = [NavalShip() for _ in range(NUM_SHIPS)]
        self.cursor_x = 3
        self.cursor_y = 3
        self.player_hits = 0
        self.ai_hits = 0
        self.ai_ships_sunk = 0
        self.player_ships_sunk = 0
        self.player_turn = True
        self.hold_peek = False
        self.peek_timer = 0.0
        self.sink_flash_timer = 0.0
        self.ai_timer = 0.0
        self.rng_seed = 0x66BA771E
        self.match_count = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 66

    @property
    def name(self) -> str:
        return "海战棋"

    @property
    def english_name(self) -> str:
        return "Battleship"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "双海域隐蔽雷达索敌与猎杀锁定博弈"

    def _next_rand(self) -> int:
        self.rng_seed = (self.rng_seed * 1103515245 + 12345) & 0xFFFFFFFF
        return (self.rng_seed >> 16) & 0x7FFF

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    @staticmethod
    def _can_place_ship(grid: List[List[int]], x: int, y: int, length: int, horiz: bool) -> bool:
        if horiz:
            if x < 0 or x + length > GRID_SIZE or y < 0 or y >= GRID_SIZE:
                return False
            return all(grid[y][x + i] == 0 for i in range(length))
        if x < 0 or x >= GRID_SIZE or y < 0 or y + length > GRID_SIZE:
            return False
        return all(grid[y + i][x] == 0 for i in range(length))

    def _place_fleet(self, grid: List[List[int]], ships: List[NavalShip]) -> None:
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                grid[y][x] = 0

        for s in range(NUM_SHIPS):
            length = SHIP_LENGTHS[s]
            placed = False
            for _ in range(200):
                horiz = (self._next_rand() & 1) != 0
                x = self._next_rand() % GRID_SIZE
                y = self._next_rand() % GRID_SIZE
                if self._can_place_ship(grid, x, y, length, horiz):
                    ships[s] = NavalShip(x, y, length, horiz)
                    for i in range(length):
                        cx = (x + i) if horiz else x
                        cy = y if horiz else (y + i)
                        grid[cy][cx] = s + 1
                    placed = True
                    break
            if not placed:
                for h in range(2):
                    if placed:
                        break
                    horiz = (h == 0)
                    for y in range(GRID_SIZE):
                        if placed:
                            break
                        for x in range(GRID_SIZE):
                            if self._can_place_ship(grid, x, y, length, horiz):
                                ships[s] = NavalShip(x, y, length, horiz)
                                for i in range(length):
                                    cx = (x + i) if horiz else x
                                    cy = y if horiz else (y + i)
                                    grid[cy][cx] = s + 1
                                placed = True
                                break

    @staticmethod
    def _mark_ship_sunk(shots: List[List[int]], ship: NavalShip) -> None:
        for i in range(ship.len):
            cx = (ship.x + i) if ship.horiz else ship.x
            cy = ship.y if ship.horiz else (ship.y + i)
            if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE:
                shots[cy][cx] = SHOT_SUNK

    def _init_match(self) -> None:
        self.rng_seed = (0x66BA771E ^ ((self.match_count * 0x9E3779B9) & 0xFFFFFFFF)) & 0xFFFFFFFF
        self.player_shots = [[SHOT_UNTARGETED] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.ai_shots = [[SHOT_UNTARGETED] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.player_grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.ai_grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.player_ships = [NavalShip() for _ in range(NUM_SHIPS)]
        self.ai_ships = [NavalShip() for _ in range(NUM_SHIPS)]
        self._place_fleet(self.player_grid, self.player_ships)
        self._place_fleet(self.ai_grid, self.ai_ships)
        self.cursor_x = 3
        self.cursor_y = 3
        self.player_hits = 0
        self.ai_hits = 0
        self.ai_ships_sunk = 0
        self.player_ships_sunk = 0
        self.player_turn = True
        self.hold_peek = False
        self.peek_timer = 0.0
        self.sink_flash_timer = 0.0
        self.ai_timer = 0.0

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = STATE_TITLE
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.match_count = 0
        self._init_match()

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.match_count += 1
            self._init_match()

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _make_ai_shot(self) -> None:
        cands = []
        # 1. Aligned line extension on unsunk hits
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.ai_shots[y][x] != SHOT_HIT:
                    continue
                if x + 1 < GRID_SIZE and self.ai_shots[y][x + 1] == SHOT_HIT:
                    if x - 1 >= 0 and self.ai_shots[y][x - 1] == SHOT_UNTARGETED:
                        cands.append((x - 1, y))
                    if x + 2 < GRID_SIZE and self.ai_shots[y][x + 2] == SHOT_UNTARGETED:
                        cands.append((x + 2, y))
                if y + 1 < GRID_SIZE and self.ai_shots[y + 1][x] == SHOT_HIT:
                    if y - 1 >= 0 and self.ai_shots[y - 1][x] == SHOT_UNTARGETED:
                        cands.append((x, y - 1))
                    if y + 2 < GRID_SIZE and self.ai_shots[y + 2][x] == SHOT_UNTARGETED:
                        cands.append((x, y + 2))

        # 2. Orthogonal neighbors of any unsunk hit
        if not cands:
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    if self.ai_shots[y][x] != SHOT_HIT:
                        continue
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and self.ai_shots[ny][nx] == SHOT_UNTARGETED:
                            cands.append((nx, ny))

        # 3. Checkerboard hunt
        if not cands:
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    if ((x + y) % 2 == 0) and self.ai_shots[y][x] == SHOT_UNTARGETED:
                        cands.append((x, y))

        # 4. Remaining untargeted cells fallback
        if not cands:
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    if self.ai_shots[y][x] == SHOT_UNTARGETED:
                        cands.append((x, y))

        if cands:
            pick = self._next_rand() % len(cands)
            tx, ty = cands[pick]
            cell = self.player_grid[ty][tx]
            if cell > 0:
                s_idx = cell - 1
                self.ai_shots[ty][tx] = SHOT_HIT
                self.player_ships[s_idx].hits += 1
                self.ai_hits += 1
                if self.player_ships[s_idx].hits >= self.player_ships[s_idx].len:
                    self._mark_ship_sunk(self.ai_shots, self.player_ships[s_idx])
                    self.player_ships_sunk += 1
            else:
                self.ai_shots[ty][tx] = SHOT_MISS

        if self.ai_hits >= TOTAL_DECK_CELLS:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return
        self.player_turn = True

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt
        if self.sink_flash_timer > 0.0:
            self.sink_flash_timer = max(0.0, self.sink_flash_timer - dt)
        if self.peek_timer > 0.0:
            self.peek_timer = max(0.0, self.peek_timer - dt)

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
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

            self.hold_peek = (keys_down & KEY_B) != 0
            if keys_pressed & KEY_B:
                self.peek_timer = 0.0 if (self.peek_timer > 0.0 and not self.hold_peek) else 1.0

            if self.player_turn:
                if keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN | KEY_A):
                    if not self.hold_peek:
                        self.peek_timer = 0.0

                if keys_pressed & KEY_LEFT:
                    if self.cursor_x > 0:
                        self.cursor_x -= 1
                elif keys_pressed & KEY_RIGHT:
                    if self.cursor_x < GRID_SIZE - 1:
                        self.cursor_x += 1
                if keys_pressed & KEY_UP:
                    if self.cursor_y > 0:
                        self.cursor_y -= 1
                elif keys_pressed & KEY_DOWN:
                    if self.cursor_y < GRID_SIZE - 1:
                        self.cursor_y += 1

                if (keys_pressed & KEY_A) and (not self.hold_peek):
                    if self.player_shots[self.cursor_y][self.cursor_x] == SHOT_UNTARGETED:
                        cell = self.ai_grid[self.cursor_y][self.cursor_x]
                        if cell > 0:
                            s_idx = cell - 1
                            self.player_shots[self.cursor_y][self.cursor_x] = SHOT_HIT
                            self.ai_ships[s_idx].hits += 1
                            self.player_hits += 1
                            self._add_score(50)

                            if self.ai_ships[s_idx].hits >= self.ai_ships[s_idx].len:
                                self._mark_ship_sunk(self.player_shots, self.ai_ships[s_idx])
                                self.ai_ships_sunk += 1
                                self._add_score(100)
                                self.sink_flash_timer = 0.35

                            if self.player_hits >= TOTAL_DECK_CELLS:
                                self._add_score(300)
                                self._state = STATE_VICTORY
                                self.state_timer = 0.0
                                return
                        else:
                            self.player_shots[self.cursor_y][self.cursor_x] = SHOT_MISS
                            self.player_turn = False
                            self.ai_timer = 0.18
            else:
                self.ai_timer -= dt
                if self.ai_timer <= 0.0:
                    self._make_ai_shot()

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(16 * 16 * 3)
        show_own = (self._state == STATE_PLAYING) and (self.hold_peek or self.peek_timer > 0.0)

        if show_own:
            for cy in range(GRID_SIZE):
                for cx in range(GRID_SIZE):
                    px = cx * 2
                    py = cy * 2
                    even = ((cx + cy) % 2 == 0)
                    ship_id = self.player_grid[cy][cx]
                    st = self.ai_shots[cy][cx]

                    r = 10 if even else 14
                    g = 36 if even else 44
                    b = 48 if even else 58

                    if ship_id > 0:
                        r, g, b = 75, 185, 210
                    if st == SHOT_MISS:
                        r, g, b = 40, 95, 140
                    elif st in (SHOT_HIT, SHOT_SUNK):
                        r, g, b = 245, 50, 40

                    for dy in range(2):
                        for dx in range(2):
                            _set_px(fb, px + dx, py + dy, r, g, b)

            for s in range(NUM_SHIPS):
                alive = self.player_ships[s].hits < self.player_ships[s].len
                _set_px(fb, s * 4, 0, 50 if alive else 255, 245 if alive else 40, 100 if alive else 40)
        else:
            sink_flash = (self.sink_flash_timer > 0.0) and ((int(self.anim_timer * 16.0) % 2) == 0)
            for cy in range(GRID_SIZE):
                for cx in range(GRID_SIZE):
                    px = cx * 2
                    py = cy * 2
                    even = ((cx + cy) % 2 == 0)
                    st = self.player_shots[cy][cx]

                    if st == SHOT_UNTARGETED:
                        r = 8 if even else 12
                        g = 28 if even else 38
                        b = 52 if even else 66
                        for dy in range(2):
                            for dx in range(2):
                                _set_px(fb, px + dx, py + dy, r, g, b)
                    elif st == SHOT_MISS:
                        _set_px(fb, px, py, 70, 145, 205)
                        _set_px(fb, px + 1, py, 35, 95, 155)
                        _set_px(fb, px, py + 1, 35, 95, 155)
                        _set_px(fb, px + 1, py + 1, 25, 75, 130)
                    elif st == SHOT_HIT:
                        _set_px(fb, px, py, 255, 205, 50)
                        _set_px(fb, px + 1, py, 255, 100, 20)
                        _set_px(fb, px, py + 1, 255, 100, 20)
                        _set_px(fb, px + 1, py + 1, 220, 45, 15)
                    else:
                        r = 255 if sink_flash else 215
                        g = 240 if sink_flash else 30
                        b = 120 if sink_flash else 45
                        for dy in range(2):
                            for dx in range(2):
                                _set_px(fb, px + dx, py + dy, r, g, b)

            if self._state == STATE_PLAYING and self.player_turn:
                if (int(self.anim_timer * 6.0) % 2) == 0:
                    px = self.cursor_x * 2
                    py = self.cursor_y * 2
                    _set_px(fb, px, py, 100, 255, 120)
                    _set_px(fb, px + 1, py + 1, 100, 255, 120)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                _set_px(fb, 6, y, 250, 250, 250)
                _set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": NUM_SHIPS - self.player_ships_sunk,
            "state": self._state,
            "progress": (self.player_hits * 100) // TOTAL_DECK_CELLS,
        }
