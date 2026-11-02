"""
Game #104: 挖金者二代 / 岛屿大塌方 (Dig Dug II 1985 / Namco)
Island fault-line jackhammering, tectonic peninsula fracturing,
and mass monster ocean drowning.
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

STATE_EXPLORING = 0
STATE_DRILLING_FAULT = 1
STATE_ISLAND_COLLAPSE = 2
STATE_PLAYER_DROWN = 3
STATE_STAGE_CLEAR = 4
STATE_GAME_OVER = 5

MAX_PEGS = 6
MAX_MONSTERS = 3


class Game104DigDug2(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_EXPLORING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.monsters_defeated = 0

        self.px = 8.0
        self.py = 8.0
        self.facing_x = 1
        self.facing_y = 0
        self.pump_timer = 0.0
        self.active_peg_idx = -1

        self.island_grid: List[List[bool]] = []
        self.collapse_mask: List[List[bool]] = []
        self.pegs: List[Dict[str, Any]] = []
        self.monsters: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 104

    @property
    def name(self) -> str:
        return "挖金者二代"

    @property
    def english_name(self) -> str:
        return "Dig Dug II"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "海岛地脉钉柱钻孔打桩、断层裂缝切割塌方、群怪坠海全歼"

    def get_name(self) -> str:
        return "Dig Dug II (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_island()

    def _init_island(self) -> None:
        self.state = STATE_EXPLORING
        self.state_timer = 0.0
        self.monsters_defeated = 0
        self.pump_timer = 0.0
        self.active_peg_idx = -1

        self.px = 8.0
        self.py = 8.0
        self.facing_x = 1
        self.facing_y = 0

        self.island_grid = [[False for _ in range(16)] for _ in range(16)]
        self.collapse_mask = [[False for _ in range(16)] for _ in range(16)]

        for y in range(2, 14):
            for x in range(2, 14):
                self.island_grid[y][x] = True

        peg_coords = [
            (4, 4), (8, 4), (11, 4),
            (4, 11), (8, 11), (11, 11)
        ]
        self.pegs = []
        for x, y in peg_coords:
            self.pegs.append({
                "x": x,
                "y": y,
                "drilled": False,
                "active": True,
            })

        self.monsters = [
            {
                "x": 3.0,
                "y": 3.0,
                "vx": 2.0,
                "vy": 0.0,
                "is_fygar": False,
                "stun_timer": 0.0,
                "active": True,
            },
            {
                "x": 12.0,
                "y": 12.0,
                "vx": -2.0,
                "vy": 0.0,
                "is_fygar": True,
                "stun_timer": 0.0,
                "active": True,
            },
            {
                "x": 10.0,
                "y": 3.0,
                "vx": 2.0,
                "vy": 0.0,
                "is_fygar": False,
                "stun_timer": 0.0,
                "active": True,
            },
        ]

    def trigger_drill_at_nearest_peg(self) -> None:
        for i, p in enumerate(self.pegs):
            if not p["active"] or p["drilled"]:
                continue
            dx = abs(self.px - p["x"])
            dy = abs(self.py - p["y"])
            if dx < 1.4 and dy < 1.4:
                self.active_peg_idx = i
                self.state = STATE_DRILLING_FAULT
                self.state_timer = 0.0
                break

    def execute_fault_line_break(self, peg_idx: int) -> None:
        if peg_idx < 0 or peg_idx >= MAX_PEGS:
            return
        self.pegs[peg_idx]["drilled"] = True
        px = self.pegs[peg_idx]["x"]
        py = self.pegs[peg_idx]["y"]

        self.collapse_mask = [[False for _ in range(16)] for _ in range(16)]

        if px <= 5:
            for y in range(16):
                for x in range(5):
                    if self.island_grid[y][x]:
                        self.collapse_mask[y][x] = True
        elif px >= 10:
            for y in range(16):
                for x in range(11, 16):
                    if self.island_grid[y][x]:
                        self.collapse_mask[y][x] = True
        elif py <= 6:
            for y in range(5):
                for x in range(16):
                    if self.island_grid[y][x]:
                        self.collapse_mask[y][x] = True
        else:
            for y in range(11, 16):
                for x in range(16):
                    if self.island_grid[y][x]:
                        self.collapse_mask[y][x] = True

        self.state = STATE_ISLAND_COLLAPSE
        self.state_timer = 0.0

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_PLAYER_DROWN:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_EXPLORING
                    self.state_timer = 0.0
                    self.px = 8.0
                    self.py = 8.0
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.2:
                self.stage += 1
                self._init_island()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_DRILLING_FAULT:
            if self.state_timer > 0.4:
                self.execute_fault_line_break(self.active_peg_idx)
            return

        if self.state == STATE_ISLAND_COLLAPSE:
            self._update_cracks_and_collapse(dt)
            return

        self._update_player(dt, buttons, prev_buttons)
        self._update_monsters(dt)
        self._check_collisions()

        if self.monsters_defeated >= MAX_MONSTERS and self.state != STATE_STAGE_CLEAR:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1500

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        move_spd = 5.0
        next_x = self.px
        next_y = self.py

        if buttons & KEY_LEFT:
            next_x -= move_spd * dt
            self.facing_x = -1
            self.facing_y = 0
        elif buttons & KEY_RIGHT:
            next_x += move_spd * dt
            self.facing_x = 1
            self.facing_y = 0
        elif buttons & KEY_UP:
            next_y -= move_spd * dt
            self.facing_x = 0
            self.facing_y = -1
        elif buttons & KEY_DOWN:
            next_y += move_spd * dt
            self.facing_x = 0
            self.facing_y = 1

        chk_x = int(round(next_x))
        chk_y = int(round(next_y))
        if 0 <= chk_x < 16 and 0 <= chk_y < 16:
            if self.island_grid[chk_y][chk_x]:
                self.px = next_x
                self.py = next_y
            else:
                self.state = STATE_PLAYER_DROWN
                self.state_timer = 0.0
                return

        # Button B: Drill
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.trigger_drill_at_nearest_peg()

        # Button A: Harpoon pump stun
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            pump_x = self.px + float(self.facing_x) * 1.8
            pump_y = self.py + float(self.facing_y) * 1.8
            for m in self.monsters:
                if not m["active"]:
                    continue
                if abs(m["x"] - pump_x) < 1.4 and abs(m["y"] - pump_y) < 1.4:
                    m["stun_timer"] = 2.0
                    self.score += 50

    def _update_monsters(self, dt: float) -> None:
        for m in self.monsters:
            if not m["active"]:
                continue
            if m["stun_timer"] > 0.0:
                m["stun_timer"] -= dt
                continue

            to_x = self.px - m["x"]
            to_y = self.py - m["y"]
            dist = math.hypot(to_x, to_y)
            if dist > 0.1:
                spd = 2.2 if m["is_fygar"] else 2.6
                next_mx = m["x"] + (to_x / dist) * spd * dt
                next_my = m["y"] + (to_y / dist) * spd * dt

                chk_x = int(round(next_mx))
                chk_y = int(round(next_my))
                if 0 <= chk_x < 16 and 0 <= chk_y < 16 and self.island_grid[chk_y][chk_x]:
                    m["x"] = next_mx
                    m["y"] = next_my

    def _update_cracks_and_collapse(self, dt: float) -> None:
        if self.state_timer > 0.6:
            drowned_count = 0
            for y in range(16):
                for x in range(16):
                    if self.collapse_mask[y][x]:
                        self.island_grid[y][x] = False

            for m in self.monsters:
                if not m["active"]:
                    continue
                mx = int(round(m["x"]))
                my = int(round(m["y"]))
                if 0 <= mx < 16 and 0 <= my < 16 and self.collapse_mask[my][mx]:
                    m["active"] = False
                    self.monsters_defeated += 1
                    drowned_count += 1

            if drowned_count == 1:
                self.score += 400
            elif drowned_count == 2:
                self.score += 1000
            elif drowned_count >= 3:
                self.score += 2000

            px = int(round(self.px))
            py = int(round(self.py))
            if 0 <= px < 16 and 0 <= py < 16 and self.collapse_mask[py][px]:
                self.state = STATE_PLAYER_DROWN
                self.state_timer = 0.0
                return

            self.state = STATE_EXPLORING
            self.state_timer = 0.0

    def _check_collisions(self) -> None:
        for m in self.monsters:
            if not m["active"] or m["stun_timer"] > 0.0:
                continue
            if abs(self.px - m["x"]) < 0.9 and abs(self.py - m["y"]) < 0.9:
                self.state = STATE_PLAYER_DROWN
                self.state_timer = 0.0
                return

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
            for x in range(16):
                if self.island_grid[y][x]:
                    if self.state == STATE_ISLAND_COLLAPSE and self.collapse_mask[y][x]:
                        set_pixel(x, y, 220, 160, 60)
                    else:
                        set_pixel(x, y, 40, 160, 50)
                else:
                    set_pixel(x, y, 10, 60, 160)

        for p in self.pegs:
            if not p["active"]:
                continue
            if p["drilled"]:
                set_pixel(p["x"], p["y"], 140, 80, 20)
            else:
                set_pixel(p["x"], p["y"], 240, 220, 120)

        if self.state == STATE_DRILLING_FAULT and self.active_peg_idx >= 0:
            ax = self.pegs[self.active_peg_idx]["x"]
            ay = self.pegs[self.active_peg_idx]["y"]
            set_pixel(ax, ay, 255, 255, 255)
            set_pixel(ax + 1, ay, 255, 200, 0)
            set_pixel(ax - 1, ay, 255, 200, 0)

        for m in self.monsters:
            if not m["active"]:
                continue
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            if m["stun_timer"] > 0.0:
                set_pixel(mx, my, 255, 255, 200)
                set_pixel(mx, my - 1, 255, 255, 100)
            elif m["is_fygar"]:
                set_pixel(mx, my, 30, 220, 60)
                set_pixel(mx + 1, my, 255, 100, 20)
            else:
                set_pixel(mx, my, 240, 40, 30)
                set_pixel(mx, my - 1, 255, 240, 50)

        tx = int(round(self.px))
        ty = int(round(self.py))
        if self.state == STATE_PLAYER_DROWN:
            set_pixel(tx, ty, 80, 140, 255)
            set_pixel(tx - 1, ty, 200, 240, 255)
            set_pixel(tx + 1, ty, 200, 240, 255)
        else:
            set_pixel(tx, ty, 240, 240, 250)
            set_pixel(tx, ty - 1, 230, 40, 30)
            set_pixel(tx + self.facing_x, ty + self.facing_y, 255, 220, 60)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 220, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "stage": self.stage,
            "monsters_defeated": self.monsters_defeated,
            "px": self.px,
            "py": self.py,
        }
