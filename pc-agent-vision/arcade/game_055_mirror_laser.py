# -*- coding: utf-8 -*-
"""game_055_mirror_laser.py —— 目标 #055 镜面激光 (Mirror Laser 1990)
7x7 光学网格实时光线追踪 + / 与 \\ 反射镜切换 + 棱镜充能与接收器通关
"""

from typing import Dict, Any, List, Tuple
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
    KEY_SELECT,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

GRID_SIZE = 7
NUM_STAGES = 4
MAX_BEAM_STEPS = 64

LASER_EMPTY = 0
LASER_WALL = 1
LASER_EMITTER = 2
LASER_MIRROR_SLASH = 3      # '/' : (dx, dy) -> (-dy, -dx)
LASER_MIRROR_BACKSLASH = 4  # '\' : (dx, dy) -> (dy, dx)
LASER_CRYSTAL = 5
LASER_RECEIVER = 6
LASER_BOMB = 7


class Game055MirrorLaser(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._state = STATE_TITLE
        self._score = 0
        self._high_score = 0
        self.stage = 0
        self.lives = 3
        self.cursor_x = 3
        self.cursor_y = 3
        self.emit_x = 0
        self.emit_y = 1
        self.emit_dx = 1
        self.emit_dy = 0
        self.total_crystals = 0
        self.lit_crystals = 0
        self.receiver_hit = False
        self.receiver_powered = False
        self.bomb_hit = False
        self.charge_timer = 0.0
        self.bomb_timer = 0.0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.grid: List[List[int]] = [[LASER_EMPTY] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.rotatable: List[List[bool]] = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.crystal_lit: List[List[bool]] = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.beam_path: List[Tuple[int, int]] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 55

    @property
    def name(self) -> str:
        return "镜面激光"

    @property
    def english_name(self) -> str:
        return "Mirror Laser"

    @property
    def release_year(self) -> int:
        return 1990

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "实时镜面正交折反射追踪与多棱镜光学串联充能"

    def init(self) -> None:
        self.reset()

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _load_stage(self, stage_idx: int) -> None:
        if not (0 <= stage_idx < NUM_STAGES):
            stage_idx = 0
        self.stage = stage_idx
        self.grid = [[LASER_EMPTY] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.rotatable = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]

        def put_mirror(x: int, y: int, init_type: int, can_rot: bool) -> None:
            self.grid[y][x] = init_type
            self.rotatable[y][x] = can_rot

        if self.stage == 0:
            self.emit_x, self.emit_y, self.emit_dx, self.emit_dy = 0, 1, 1, 0
            self.grid[1][0] = LASER_EMITTER
            put_mirror(5, 1, LASER_MIRROR_SLASH, True)
            self.grid[3][5] = LASER_CRYSTAL
            put_mirror(5, 5, LASER_MIRROR_BACKSLASH, True)
            self.grid[5][1] = LASER_RECEIVER
            self.grid[5][6] = LASER_BOMB
            self.grid[3][2] = LASER_WALL
            self.cursor_x, self.cursor_y = 5, 1
        elif self.stage == 1:
            self.emit_x, self.emit_y, self.emit_dx, self.emit_dy = 0, 0, 0, 1
            self.grid[0][0] = LASER_EMITTER
            self.grid[2][0] = LASER_CRYSTAL
            put_mirror(0, 4, LASER_MIRROR_SLASH, True)
            self.grid[2][3] = LASER_WALL
            put_mirror(4, 4, LASER_MIRROR_BACKSLASH, True)
            self.grid[2][4] = LASER_CRYSTAL
            put_mirror(4, 1, LASER_MIRROR_BACKSLASH, True)
            self.grid[1][6] = LASER_RECEIVER
            self.grid[6][4] = LASER_BOMB
            self.cursor_x, self.cursor_y = 0, 4
        elif self.stage == 2:
            self.emit_x, self.emit_y, self.emit_dx, self.emit_dy = 6, 0, -1, 0
            self.grid[0][6] = LASER_EMITTER
            put_mirror(1, 0, LASER_MIRROR_BACKSLASH, True)
            self.grid[3][1] = LASER_CRYSTAL
            put_mirror(1, 6, LASER_MIRROR_SLASH, True)
            put_mirror(5, 6, LASER_MIRROR_BACKSLASH, True)
            self.grid[4][5] = LASER_CRYSTAL
            put_mirror(5, 2, LASER_MIRROR_SLASH, True)
            self.grid[2][3] = LASER_RECEIVER
            self.grid[4][3] = LASER_WALL
            self.grid[2][6] = LASER_BOMB
            self.cursor_x, self.cursor_y = 1, 0
        else:
            self.emit_x, self.emit_y, self.emit_dx, self.emit_dy = 0, 6, 0, -1
            self.grid[6][0] = LASER_EMITTER
            self.grid[4][0] = LASER_CRYSTAL
            put_mirror(0, 1, LASER_MIRROR_BACKSLASH, True)
            put_mirror(3, 1, LASER_MIRROR_SLASH, True)
            self.grid[3][3] = LASER_CRYSTAL
            put_mirror(3, 5, LASER_MIRROR_SLASH, True)
            put_mirror(6, 5, LASER_MIRROR_BACKSLASH, True)
            self.grid[3][6] = LASER_CRYSTAL
            put_mirror(6, 0, LASER_MIRROR_SLASH, True)
            self.grid[0][2] = LASER_RECEIVER
            self.grid[5][1] = LASER_BOMB
            self.cursor_x, self.cursor_y = 0, 1

        self.total_crystals = sum(
            1 for y in range(GRID_SIZE) for x in range(GRID_SIZE) if self.grid[y][x] == LASER_CRYSTAL
        )
        self.charge_timer = 0.0
        self.bomb_timer = 0.0
        self.trace_beam()

    def trace_beam(self) -> None:
        self.crystal_lit = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.beam_path = []
        self.lit_crystals = 0
        self.receiver_hit = False
        self.bomb_hit = False

        cx, cy = self.emit_x, self.emit_y
        dx, dy = self.emit_dx, self.emit_dy

        for _ in range(MAX_BEAM_STEPS):
            cx += dx
            cy += dy
            if not (0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE):
                break
            self.beam_path.append((cx, cy))

            cell = self.grid[cy][cx]
            if cell == LASER_EMPTY:
                continue
            elif cell == LASER_CRYSTAL:
                if not self.crystal_lit[cy][cx]:
                    self.crystal_lit[cy][cx] = True
                    self.lit_crystals += 1
                continue
            elif cell == LASER_MIRROR_SLASH:
                dx, dy = -dy, -dx
            elif cell == LASER_MIRROR_BACKSLASH:
                dx, dy = dy, dx
            elif cell == LASER_RECEIVER:
                self.receiver_hit = True
                break
            elif cell == LASER_BOMB:
                self.bomb_hit = True
                break
            else:
                break

        self.receiver_powered = self.receiver_hit and (self.lit_crystals == self.total_crystals)

    def reset(self) -> None:
        self._state = STATE_TITLE
        self.lives = 3
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self._load_stage(0)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self.lives = 3
            self._score = 0
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self._load_stage(0)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

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

            if keys_pressed & (KEY_B | KEY_SELECT):
                self._load_stage(self.stage)
                return

            if keys_pressed & KEY_LEFT:
                if self.cursor_x > 0:
                    self.cursor_x -= 1
            elif keys_pressed & KEY_RIGHT:
                if self.cursor_x < GRID_SIZE - 1:
                    self.cursor_x += 1
            elif keys_pressed & KEY_UP:
                if self.cursor_y > 0:
                    self.cursor_y -= 1
            elif keys_pressed & KEY_DOWN:
                if self.cursor_y < GRID_SIZE - 1:
                    self.cursor_y += 1

            if keys_pressed & KEY_A:
                if self.rotatable[self.cursor_y][self.cursor_x]:
                    cur = self.grid[self.cursor_y][self.cursor_x]
                    if cur == LASER_MIRROR_SLASH:
                        self.grid[self.cursor_y][self.cursor_x] = LASER_MIRROR_BACKSLASH
                    elif cur == LASER_MIRROR_BACKSLASH:
                        self.grid[self.cursor_y][self.cursor_x] = LASER_MIRROR_SLASH
                    self.charge_timer = 0.0
                    self.bomb_timer = 0.0
                    self.trace_beam()

            if self.bomb_hit:
                self.bomb_timer += dt
                if self.bomb_timer >= 0.45:
                    if self.lives > 1:
                        self.lives -= 1
                        self._load_stage(self.stage)
                    else:
                        self.lives = 0
                        self._state = STATE_GAMEOVER
                        self.state_timer = 0.0
                    return
            else:
                self.bomb_timer = 0.0

            if self.receiver_powered:
                self.charge_timer += dt
                if self.charge_timer >= 0.40:
                    self._add_score(200)
                    if self.stage + 1 < NUM_STAGES:
                        self._load_stage(self.stage + 1)
                    else:
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
            else:
                self.charge_timer = 0.0

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
        for y in range(16):
            for x in range(16):
                if 1 <= x <= 14 and 1 <= y <= 14:
                    gx = (x - 1) // 2
                    gy = (y - 1) // 2
                    v = 20 if ((gx + gy) & 1) else 14
                    self._set_px(fb, x, y, v, v + 3, v + 10)
                else:
                    self._set_px(fb, x, y, 30, 36, 48)

        for i in range(self.lives):
            self._set_px(fb, 1 + i * 2, 0, 245, 70, 80)
        for s in range(NUM_STAGES):
            px = 9 + s * 2
            if s < self.stage:
                self._set_px(fb, px, 0, 46, 220, 100)
            elif s == self.stage:
                self._set_px(fb, px, 0, 255, 215, 35)

        lr, lg, lb = (80, 255, 140) if self.receiver_powered else (255, 45, 120)
        for bx, by in self.beam_path:
            px, py = 1 + bx * 2, 1 + by * 2
            for dy in range(2):
                for dx in range(2):
                    self._set_px(fb, px + dx, py + dy, lr, lg, lb)

        for gy in range(GRID_SIZE):
            for gx in range(GRID_SIZE):
                px, py = 1 + gx * 2, 1 + gy * 2
                cell = self.grid[gy][gx]
                if cell == LASER_WALL:
                    for dy in range(2):
                        for dx in range(2):
                            self._set_px(fb, px + dx, py + dy, 95, 108, 126)
                elif cell == LASER_EMITTER:
                    for dy in range(2):
                        for dx in range(2):
                            self._set_px(fb, px + dx, py + dy, 255, 95, 30)
                elif cell == LASER_MIRROR_SLASH:
                    self._set_px(fb, px, py + 1, 140, 235, 255)
                    self._set_px(fb, px + 1, py, 210, 250, 255)
                elif cell == LASER_MIRROR_BACKSLASH:
                    self._set_px(fb, px, py, 210, 250, 255)
                    self._set_px(fb, px + 1, py + 1, 140, 235, 255)
                elif cell == LASER_CRYSTAL:
                    lit = self.crystal_lit[gy][gx]
                    cr, cg, cb = (80, 255, 235) if lit else (25, 135, 175)
                    self._set_px(fb, px, py, cr, cg, cb)
                    self._set_px(fb, px + 1, py + 1, cr, cg, cb)
                elif cell == LASER_RECEIVER:
                    rr, rg, rb = (50, 245, 95) if self.receiver_powered else (235, 185, 25)
                    for dy in range(2):
                        for dx in range(2):
                            self._set_px(fb, px + dx, py + dy, rr, rg, rb)
                elif cell == LASER_BOMB:
                    br, bg, bb = (255, 120, 25) if self.bomb_hit else (175, 25, 25)
                    self._set_px(fb, px, py, br, bg, bb)
                    self._set_px(fb, px + 1, py, 90, 20, 20)
                    self._set_px(fb, px, py + 1, 90, 20, 20)
                    self._set_px(fb, px + 1, py + 1, br, bg, bb)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            if (int(self.anim_timer * 6.0) % 2) == 0:
                self._set_px(fb, 1 + self.cursor_x * 2, 1 + self.cursor_y * 2, 255, 255, 120)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                self._set_px(fb, 6, y, 250, 250, 250)
                self._set_px(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = self.stage * 25 + (20 if self.receiver_powered else 0)
        if self._state == STATE_VICTORY:
            prog = 100
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, prog),
        }
