"""
Game #034: 疯狂水管工 (Pipe Dream / Pipe Mania 1989 / Lucasfilm Games)
Real-time Fluid Flow Countdown with Randomized Pipe Geometry, Cross Intersections & Drain Routing.
"""

import random
from typing import List, Dict, Any
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

GRID_W = 8
GRID_H = 8
QUEUE_SIZE = 4

PIPE_EMPTY = 0
PIPE_HORIZ = 1      # Left <-> Right
PIPE_VERT = 2       # Up <-> Down
PIPE_CORNER_UR = 3  # Up <-> Right
PIPE_CORNER_RD = 4  # Right <-> Down
PIPE_CORNER_DL = 5  # Down <-> Left
PIPE_CORNER_LU = 6  # Left <-> Up
PIPE_CROSS = 7      # Cross Double Bridge
PIPE_START = 8      # Source Tap
PIPE_END = 9        # Drain Tap

DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]


class Game034PipeDream(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.pipes_filled = 0
        self.required_pipes = 8

        self.cursor_x = 2
        self.cursor_y = 2

        self.flow_start_countdown = 6.0
        self.flow_step_timer = 0.0
        self.flow_step_interval = 1.0
        self.flow_x = 1
        self.flow_y = 1
        self.flow_dir = 1
        self.flow_started = False

        self.grid: List[List[Dict[str, Any]]] = []
        self.pipe_queue: List[int] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 34

    @property
    def name(self) -> str:
        return "疯狂水管工"

    @property
    def english_name(self) -> str:
        return "Pipe Dream 1989"

    @property
    def release_year(self) -> int:
        return 1989

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "原油粘稠动态流动倒计时 + 随机管道几何快速嵌接导流 + 双十字跨越与排水"

    def init(self) -> None:
        self.reset()

    def generate_random_pipe(self) -> int:
        return random.randint(1, 7)

    def push_queue(self):
        self.pipe_queue.pop(0)
        self.pipe_queue.append(self.generate_random_pipe())

    def init_board(self):
        self.grid = []
        for y in range(GRID_H):
            row = []
            for x in range(GRID_W):
                row.append({
                    "pipe": PIPE_EMPTY,
                    "filled": False,
                    "cross_h_filled": False,
                    "cross_v_filled": False,
                })
            self.grid.append(row)

        self.flow_x = 1
        self.flow_y = 1
        self.flow_dir = 1
        self.grid[self.flow_y][self.flow_x]["pipe"] = PIPE_START
        self.grid[self.flow_y][self.flow_x]["filled"] = True

        self.grid[6][6]["pipe"] = PIPE_END
        self.grid[6][6]["filled"] = False

        self.pipe_queue = [self.generate_random_pipe() for _ in range(QUEUE_SIZE)]

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.pipes_filled = 0
        self.required_pipes = 8
        self.cursor_x = 2
        self.cursor_y = 2
        self.flow_start_countdown = 6.0
        self.flow_step_timer = 0.0
        self.flow_step_interval = 1.0
        self.flow_started = False
        self.init_board()

    def can_connect(self, pipe: int, enter_dir: int) -> (bool, int):
        if pipe == PIPE_HORIZ:
            if enter_dir == 1: return True, 1
            if enter_dir == 3: return True, 3
            return False, 0
        elif pipe == PIPE_VERT:
            if enter_dir == 0: return True, 0
            if enter_dir == 2: return True, 2
            return False, 0
        elif pipe == PIPE_CORNER_UR:
            if enter_dir == 2: return True, 1
            if enter_dir == 3: return True, 0
            return False, 0
        elif pipe == PIPE_CORNER_RD:
            if enter_dir == 0: return True, 1
            if enter_dir == 3: return True, 2
            return False, 0
        elif pipe == PIPE_CORNER_DL:
            if enter_dir == 0: return True, 3
            if enter_dir == 1: return True, 2
            return False, 0
        elif pipe == PIPE_CORNER_LU:
            if enter_dir == 2: return True, 3
            if enter_dir == 1: return True, 0
            return False, 0
        elif pipe == PIPE_CROSS:
            return True, enter_dir
        elif pipe == PIPE_END:
            return True, enter_dir
        return False, 0

    def place_pipe(self) -> bool:
        cell = self.grid[self.cursor_y][self.cursor_x]
        if cell["filled"] or cell["pipe"] in (PIPE_START, PIPE_END):
            return False

        cell["pipe"] = self.pipe_queue[0]
        self.push_queue()
        return True

    def fast_forward_flow(self):
        if self.flow_started:
            self.flow_step_interval = 0.2
        else:
            self.flow_start_countdown = 0.0

    def advance_flow(self):
        nx = self.flow_x + DX[self.flow_dir]
        ny = self.flow_y + DY[self.flow_dir]

        if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        target = self.grid[ny][nx]
        can_c, next_dir = self.can_connect(target["pipe"], self.flow_dir)
        if not can_c:
            self.state = STATE_DEAD
            self.state_timer = 0.0
            return

        if target["filled"]:
            if target["pipe"] == PIPE_CROSS:
                is_horiz = (self.flow_dir in (1, 3))
                if (is_horiz and target["cross_h_filled"]) or (not is_horiz and target["cross_v_filled"]):
                    self.state = STATE_DEAD
                    self.state_timer = 0.0
                    return
            else:
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        self.flow_x = nx
        self.flow_y = ny
        self.flow_dir = next_dir
        self.pipes_filled += 1

        if target["pipe"] == PIPE_CROSS:
            is_horiz = (self.flow_dir in (1, 3))
            if is_horiz:
                target["cross_h_filled"] = True
            else:
                target["cross_v_filled"] = True

            if target["cross_h_filled"] and target["cross_v_filled"]:
                self.score += 400
            else:
                self.score += 100
            target["filled"] = True
        elif target["pipe"] == PIPE_END:
            target["filled"] = True
            if self.pipes_filled >= self.required_pipes:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 1000 + self.pipes_filled * 100
            else:
                self.state = STATE_DEAD
                self.state_timer = 0.0
            if self.score > self.high_score:
                self.high_score = self.score
            return
        else:
            target["filled"] = True
            self.score += 100

        if self.score > self.high_score:
            self.high_score = self.score

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_DEAD, STATE_VICTORY):
            if self.state_timer >= 2.0 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
            self.cursor_x = max(0, self.cursor_x - 1)
        elif (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
            self.cursor_x = min(GRID_W - 1, self.cursor_x + 1)
        elif (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            self.cursor_y = max(0, self.cursor_y - 1)
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            self.cursor_y = min(GRID_H - 1, self.cursor_y + 1)

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.place_pipe()

        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.fast_forward_flow()

        if not self.flow_started:
            self.flow_start_countdown = max(0.0, self.flow_start_countdown - dt)
            if self.flow_start_countdown <= 0.0:
                self.flow_started = True
                self.flow_step_timer = 0.0
        else:
            self.flow_step_timer += dt
            if self.flow_step_timer >= self.flow_step_interval:
                self.flow_step_timer = 0.0
                self.advance_flow()

    def render(self) -> bytes:
        fb = bytearray([30, 39, 46] * 256)

        for cy in range(GRID_H):
            for cx in range(GRID_W):
                c = self.grid[cy][cx]
                if c["pipe"] == PIPE_EMPTY:
                    continue

                px0 = cx * 2
                py0 = cy * 2
                pr, pg, pb = (46, 204, 113) if c["filled"] else (149, 165, 166)
                if c["pipe"] == PIPE_START:
                    pr, pg, pb = 0, 255, 128
                elif c["pipe"] == PIPE_END:
                    pr, pg, pb = 243, 156, 18

                p = c["pipe"]
                if p in (PIPE_HORIZ, PIPE_START):
                    for dx in range(2):
                        idx = (py0 * 16 + (px0 + dx)) * 3
                        fb[idx:idx + 3] = bytes([pr, pg, pb])
                elif p == PIPE_VERT:
                    for dy in range(2):
                        idx = ((py0 + dy) * 16 + px0) * 3
                        fb[idx:idx + 3] = bytes([pr, pg, pb])
                elif p == PIPE_CORNER_UR:
                    fb[(py0 * 16 + px0) * 3:(py0 * 16 + px0) * 3 + 3] = bytes([pr, pg, pb])
                    fb[(py0 * 16 + px0 + 1) * 3:(py0 * 16 + px0 + 1) * 3 + 3] = bytes([pr, pg, pb])
                elif p == PIPE_CORNER_RD:
                    fb[(py0 * 16 + px0 + 1) * 3:(py0 * 16 + px0 + 1) * 3 + 3] = bytes([pr, pg, pb])
                    fb[((py0 + 1) * 16 + px0 + 1) * 3:((py0 + 1) * 16 + px0 + 1) * 3 + 3] = bytes([pr, pg, pb])
                elif p == PIPE_CORNER_DL:
                    fb[((py0 + 1) * 16 + px0) * 3:((py0 + 1) * 16 + px0) * 3 + 3] = bytes([pr, pg, pb])
                    fb[((py0 + 1) * 16 + px0 + 1) * 3:((py0 + 1) * 16 + px0 + 1) * 3 + 3] = bytes([pr, pg, pb])
                elif p == PIPE_CORNER_LU:
                    fb[(py0 * 16 + px0) * 3:(py0 * 16 + px0) * 3 + 3] = bytes([pr, pg, pb])
                    fb[((py0 + 1) * 16 + px0) * 3:((py0 + 1) * 16 + px0) * 3 + 3] = bytes([pr, pg, pb])
                else: # CROSS, END
                    for dy in range(2):
                        for dx in range(2):
                            idx = ((py0 + dy) * 16 + (px0 + dx)) * 3
                            fb[idx:idx + 3] = bytes([pr, pg, pb])

        # Cursor
        if int(self.state_timer * 6.0) % 2 == 0:
            cur_px = self.cursor_x * 2
            cur_py = self.cursor_y * 2
            for dy in range(2):
                for dx in range(2):
                    idx = ((cur_py + dy) * 16 + (cur_px + dx)) * 3
                    fb[idx:idx + 3] = bytes([52, 152, 219])

        # Preview dot
        fb[(14 * 16 + 14) * 3:(14 * 16 + 14) * 3 + 3] = bytes([241, 196, 15])
        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "pipes_filled": self.pipes_filled,
            "required_pipes": self.required_pipes,
            "cursor": (self.cursor_x, self.cursor_y),
            "flow_countdown": self.flow_start_countdown,
            "flow_pos": (self.flow_x, self.flow_y),
        }
