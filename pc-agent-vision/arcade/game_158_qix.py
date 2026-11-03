# -*- coding: utf-8 -*-
"""
Game #158: 划线天蚕变 (Qix 1981 / Taito)
街机历史上开创划线圈地与空间切割玩法的里程碑鼻祖：
沿边界谨慎推进、按键A慢速画线斩获双倍积分、按键B快速画线抢占先机、
切割封闭空间孤立游荡旋动光束Qix、规避巡界电火花占领75%领地胜出。
"""

from typing import List, Dict, Any, Optional
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
STATE_STAGE_CLEAR = 1
STATE_PLAYER_HIT = 2
STATE_GAME_OVER = 3

CELL_EMPTY = 0
CELL_BORDER = 1
CELL_CLAIMED = 2
CELL_DRAWING = 3

WIN_PERCENTAGE = 70.0  # Percentage of internal area to claim


class Game158Qix(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7
        self.py = 15
        self.is_drawing = False
        self.draw_slow = False  # True: 2x score, False: 1x score
        self.draw_path: List[tuple] = []

        # 16x16 grid: 0: empty, 1: border, 2: claimed, 3: drawing
        self.grid = [[CELL_EMPTY for _ in range(16)] for _ in range(16)]

        # Qix entity
        self.qx = 7.5
        self.qy = 7.5
        self.qvx = 2.4
        self.qvy = 1.8

        # Sparx (sparks patrolling border)
        self.sparx: List[Dict[str, Any]] = []

        self.percent_claimed = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 158

    @property
    def name(self) -> str:
        return "划线天蚕变"

    @property
    def english_name(self) -> str:
        return "Qix"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "闭合线框圈地切割空间、快慢双档绘制领地抗衡旋动游荡光束Qix、规避边界电火花并达到75%占领率"

    def get_name(self) -> str:
        return "Qix (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7
        self.py = 15
        self.is_drawing = False
        self.draw_slow = False
        self.draw_path.clear()
        self.percent_claimed = 0.0

        # Initialize grid with outer border
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    self.grid[y][x] = CELL_BORDER
                else:
                    self.grid[y][x] = CELL_EMPTY

        # Qix position
        self.qx = 7.5
        self.qy = 7.5
        self.qvx = 2.4 + (self.level * 0.3)
        self.qvy = 1.8 + (self.level * 0.2)

        # 2 Sparx on border
        self.sparx = [
            {"x": 0.0, "y": 0.0, "dir": 1},   # Clockwise
            {"x": 15.0, "y": 0.0, "dir": -1}, # Counter-clockwise
        ]

    def _calc_percent(self) -> float:
        total_internal = 14 * 14
        claimed_count = 0
        for y in range(1, 15):
            for x in range(1, 15):
                if self.grid[y][x] == CELL_CLAIMED:
                    claimed_count += 1
        return (claimed_count / total_internal) * 100.0

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_PLAYER_HIT):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_PLAYER_HIT:
                    if self.lives > 0:
                        # Clear drawing path
                        for dx, dy in self.draw_path:
                            self.grid[dy][dx] = CELL_EMPTY
                        self.draw_path.clear()
                        self.is_drawing = False
                        self.px = 7
                        self.py = 15
                        self.state = STATE_PLAYING
                        self.state_timer = 0.0
                    else:
                        self.state = STATE_GAME_OVER
                        self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.state_timer += dt
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()

    def _update_playing(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # 1. Player Navigation & Drawing
        dx = 0
        dy = 0
        if (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
            dx = -1
        elif (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
            dx = 1
        elif (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            dy = -1
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            dy = 1

        if dx != 0 or dy != 0:
            nx = self.px + dx
            ny = self.py + dy

            if 0 <= nx < 16 and 0 <= ny < 16:
                target_cell = self.grid[ny][nx]

                if not self.is_drawing:
                    # On border/claimed
                    if target_cell in (CELL_BORDER, CELL_CLAIMED):
                        # Free walking along border
                        self.px = nx
                        self.py = ny
                    elif target_cell == CELL_EMPTY:
                        # Enter empty space: requires holding Key A or Key B
                        if (buttons & KEY_A) or (buttons & KEY_B):
                            self.is_drawing = True
                            self.draw_slow = bool(buttons & KEY_A)
                            self.px = nx
                            self.py = ny
                            self.grid[ny][nx] = CELL_DRAWING
                            self.draw_path.append((nx, ny))
                else:
                    # Currently drawing
                    if target_cell == CELL_EMPTY:
                        self.px = nx
                        self.py = ny
                        self.grid[ny][nx] = CELL_DRAWING
                        self.draw_path.append((nx, ny))
                    elif target_cell in (CELL_BORDER, CELL_CLAIMED):
                        # Connected back to border/claimed: CLOSE TERRITORY!
                        self.px = nx
                        self.py = ny
                        self._claim_territory()

        # 2. Update Qix Motion & Collision
        self.qx += self.qvx * dt
        self.qy += self.qvy * dt

        # Bounce Qix off claimed cells / borders
        int_qx = int(round(self.qx))
        int_qy = int(round(self.qy))

        if int_qx <= 1 or int_qx >= 14 or self.grid[int_qy][int_qx] in (CELL_BORDER, CELL_CLAIMED):
            self.qvx = -self.qvx
            self.qx = max(1.5, min(13.5, self.qx))

        if int_qy <= 1 or int_qy >= 14 or self.grid[int_qy][int_qx] in (CELL_BORDER, CELL_CLAIMED):
            self.qvy = -self.qvy
            self.qy = max(1.5, min(13.5, self.qy))

        # Check Qix collision with active drawing line
        if self.is_drawing:
            for dpx, dpy in self.draw_path:
                if abs(self.qx - dpx) < 0.9 and abs(self.qy - dpy) < 0.9:
                    self._lose_life()
                    return

        # 3. Update Sparx on border
        sparx_speed = 3.5
        for sp in self.sparx:
            # Simple border patrol
            if sp["dir"] == 1:
                # Top -> Right -> Bottom -> Left
                if sp["y"] == 0 and sp["x"] < 15: sp["x"] += sparx_speed * dt
                elif sp["x"] >= 15 and sp["y"] < 15: sp["y"] += sparx_speed * dt
                elif sp["y"] >= 15 and sp["x"] > 0: sp["x"] -= sparx_speed * dt
                elif sp["x"] <= 0 and sp["y"] > 0: sp["y"] -= sparx_speed * dt
            else:
                if sp["y"] == 0 and sp["x"] > 0: sp["x"] -= sparx_speed * dt
                elif sp["x"] <= 0 and sp["y"] < 15: sp["y"] += sparx_speed * dt
                elif sp["y"] >= 15 and sp["x"] < 15: sp["x"] += sparx_speed * dt
                elif sp["x"] >= 15 and sp["y"] > 0: sp["y"] -= sparx_speed * dt

            sp["x"] = max(0.0, min(15.0, sp["x"]))
            sp["y"] = max(0.0, min(15.0, sp["y"]))

            # Spark touches player while player is on border
            if not self.is_drawing:
                if abs(self.px - sp["x"]) < 0.8 and abs(self.py - sp["y"]) < 0.8:
                    self._lose_life()
                    return

    def _claim_territory(self) -> None:
        """Flood fill from Qix position; all unreached empty cells are claimed!"""
        # Mark all draw path as border
        for dx, dy in self.draw_path:
            self.grid[dy][dx] = CELL_BORDER

        # Flood fill to find all empty cells connected to Qix
        visited = [[False for _ in range(16)] for _ in range(16)]
        q_start_x = max(1, min(14, int(round(self.qx))))
        q_start_y = max(1, min(14, int(round(self.qy))))

        queue = [(q_start_x, q_start_y)]
        visited[q_start_y][q_start_x] = True

        while queue:
            cx, cy = queue.pop(0)
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = cx + ox
                ny = cy + oy
                if 0 <= nx < 16 and 0 <= ny < 16:
                    if not visited[ny][nx] and self.grid[ny][nx] == CELL_EMPTY:
                        visited[ny][nx] = True
                        queue.append((nx, ny))

        # Any CELL_EMPTY cell that was NOT visited by flood fill is captured!
        newly_claimed = 0
        for y in range(1, 15):
            for x in range(1, 15):
                if self.grid[y][x] == CELL_EMPTY and not visited[y][x]:
                    self.grid[y][x] = CELL_CLAIMED
                    newly_claimed += 1

        mult = 2 if self.draw_slow else 1
        self.score += newly_claimed * 10 * mult

        self.draw_path.clear()
        self.is_drawing = False

        self.percent_claimed = self._calc_percent()

        if self.percent_claimed >= WIN_PERCENTAGE:
            self.score += 3000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_PLAYER_HIT
        self.state_timer = 0.0

    def render(self, fb: Optional[bytearray] = None) -> bytearray:
        if fb is None:
            fb = bytearray(16 * 16 * 3)
        else:
            for i in range(16 * 16 * 3):
                fb[i] = 0

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Render Grid
        for y in range(16):
            for x in range(16):
                c = self.grid[y][x]
                if c == CELL_CLAIMED:
                    set_pixel(x, y, 40, 100, 200)   # Solid blue claimed
                elif c == CELL_BORDER:
                    set_pixel(x, y, 120, 120, 140)  # Grey boundary
                elif c == CELL_DRAWING:
                    # Flashing red/yellow active stix
                    set_pixel(x, y, 255, 230, 40 if self.draw_slow else 80)

        # 2. Render Qix Helix (Multicolor vibrating stick)
        qx = int(round(self.qx))
        qy = int(round(self.qy))
        set_pixel(qx, qy, 255, 40, 180)
        if qx + 1 < 16: set_pixel(qx + 1, qy, 40, 255, 200)
        if qy - 1 >= 0: set_pixel(qx, qy - 1, 255, 220, 40)
        if qx - 1 >= 0: set_pixel(qx - 1, qy, 255, 80, 40)

        # 3. Render Sparx (Bright yellow electrical sparks)
        for sp in self.sparx:
            sx = int(round(sp["x"]))
            sy = int(round(sp["y"]))
            set_pixel(sx, sy, 255, 255, 100)

        # 4. Render Player Marker (Diamond diamond cursor)
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(self.px, self.py, 255, 50, 50)
        elif self.state == STATE_PLAYER_HIT:
            set_pixel(self.px, self.py, 255, 255, 255)

        # 5. Claimed Percentage gauge on top row
        pct_dots = int((self.percent_claimed / 100.0) * 8.0)
        for i in range(pct_dots):
            set_pixel(8 + i, 0, 40, 255, 120)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 255, 50, 50)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "px": self.px,
            "py": self.py,
            "is_drawing": self.is_drawing,
            "percent_claimed": self.percent_claimed,
        }

