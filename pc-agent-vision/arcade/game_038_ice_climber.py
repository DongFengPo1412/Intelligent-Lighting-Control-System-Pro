"""
Game #038: 敲冰块 (Ice Climber 1985 / Nintendo / Kazuaki Morita)
Vertical Tiered Mountain with Upward Hammer Ice Shattering, Seal Hole Patching & Summit Condor Grab.
"""

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

FLOOR_Y = [14, 11, 8, 5]


class Game038IceClimber(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.lives = 3

        self.player_x = 7.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.is_grounded = True
        self.hammer_timer = 0.0

        self.condor = {"x": -2.0, "y": 1.0, "vx": 3.5, "active": True}
        self.topis: List[Dict[str, Any]] = []
        self.ice_grid: List[List[int]] = [[0 for _ in range(16)] for _ in range(16)]

        self.reset()

    @property
    def game_id(self) -> int:
        return 38

    @property
    def name(self) -> str:
        return "敲冰块"

    @property
    def english_name(self) -> str:
        return "Ice Climber 1985"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "跃击举槌碎冰开洞 + 逐层攀登飞跃断崖 + 海豹极速补冰修洞 + 峰顶神鹰抓取"

    def init(self) -> None:
        self.reset()

    def init_mountain(self):
        self.ice_grid = [[0 for _ in range(16)] for _ in range(16)]

        # Floor 0: Ground (Solid base 1)
        for x in range(16):
            self.ice_grid[14][x] = 1
            self.ice_grid[15][x] = 1

        # Floor 1, 2, 3: Breakable Ice Blocks (2)
        for fy in FLOOR_Y[1:]:
            for x in range(1, 15):
                self.ice_grid[fy][x] = 2

        # Summit platform (Solid 1 at y = 2, x = 6..9)
        for x in range(6, 10):
            self.ice_grid[2][x] = 1

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.player_x = 7.0
        self.player_y = 13.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.is_grounded = True
        self.hammer_timer = 0.0

        self.init_mountain()

        self.condor = {"x": -2.0, "y": 1.0, "vx": 3.5, "active": True}
        self.topis = [
            {"x": 3.0, "floor_y": 11, "vx": 2.2, "active": True},
            {"x": 12.0, "floor_y": 8, "vx": -2.2, "active": True},
        ]

    def break_ice_at(self, x: int, y: int):
        if 0 <= x < 16 and 0 <= y < 16:
            if self.ice_grid[y][x] == 2:
                self.ice_grid[y][x] = 0
                self.score += 50
                if self.score > self.high_score:
                    self.high_score = self.score

    def get_current_floor(self) -> int:
        if self.player_y <= 2.0: return 4
        if self.player_y <= 5.0: return 3
        if self.player_y <= 8.0: return 2
        if self.player_y <= 11.0: return 1
        return 0

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.state_timer = 0.0
                    self.player_x = 7.0
                    self.player_y = 13.0
                    self.player_vx = 0.0
                    self.player_vy = 0.0
                    self.is_grounded = True
            return

        if self.state == STATE_VICTORY:
            if self.state_timer >= 2.5 and (buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self.update_player(dt, buttons, prev_buttons)
        self.update_topis(dt)
        self.update_condor(dt)
        self.check_collisions()

    def update_player(self, dt: float, buttons: int, prev_buttons: int):
        gravity = 22.0
        run_speed = 5.5

        # Horizontal
        self.player_vx = 0.0
        if buttons & KEY_LEFT:
            self.player_vx = -run_speed
        if buttons & KEY_RIGHT:
            self.player_vx = run_speed

        self.player_x += self.player_vx * dt
        if self.player_x < 0.0:
            self.player_x += 16.0
        elif self.player_x >= 16.0:
            self.player_x -= 16.0

        # Jump
        if (buttons & KEY_A) and not (prev_buttons & KEY_A) and self.is_grounded:
            self.player_vy = -10.0
            self.is_grounded = False

        # Hammer Swing
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.hammer_timer = 0.25
        if self.hammer_timer > 0.0:
            self.hammer_timer -= dt

        # Vertical
        if not self.is_grounded:
            self.player_vy += gravity * dt
            self.player_y += self.player_vy * dt

            # Upward Head-Butt
            if self.player_vy < 0.0:
                ceil_y = int(round(self.player_y - 0.45))
                head_x = int(round(self.player_x))
                if 0 <= ceil_y < 16 and 0 <= head_x < 16:
                    if self.ice_grid[ceil_y][head_x] == 2:
                        self.break_ice_at(head_x, ceil_y)
                        self.player_vy = 0.0
            # Downward Landing
            elif self.player_vy >= 0.0:
                floor_y = int(round(self.player_y + 1.0))
                foot_x = int(round(self.player_x))
                if 0 <= floor_y < 16 and 0 <= foot_x < 16:
                    if self.ice_grid[floor_y][foot_x] != 0 and self.player_y <= float(floor_y - 0.8):
                        self.player_y = float(floor_y - 1.0)
                        self.player_vy = 0.0
                        self.is_grounded = True
        else:
            floor_y = int(round(self.player_y + 1.0))
            foot_x = int(round(self.player_x))
            if 0 <= floor_y < 16 and 0 <= foot_x < 16:
                if self.ice_grid[floor_y][foot_x] == 0:
                    self.is_grounded = False

        if self.player_y > 15.0:
            self.lives -= 1
            self.state = STATE_DEAD
            self.state_timer = 0.0

    def update_topis(self, dt: float):
        for topi in self.topis:
            if not topi["active"]:
                continue

            topi["x"] += topi["vx"] * dt
            fy = topi["floor_y"]

            if topi["x"] <= 1.0:
                topi["x"] = 1.0
                topi["vx"] = -topi["vx"]
            elif topi["x"] >= 14.0:
                topi["x"] = 14.0
                topi["vx"] = -topi["vx"]

            tx = int(round(topi["x"]))
            if 1 <= tx <= 14:
                if self.ice_grid[fy][tx] == 0:
                    self.ice_grid[fy][tx] = 2 # Patch hole!

    def update_condor(self, dt: float):
        if not self.condor["active"]:
            return

        self.condor["x"] += self.condor["vx"] * dt
        if self.condor["vx"] > 0.0 and self.condor["x"] > 18.0:
            self.condor["x"] = 18.0
            self.condor["vx"] = -self.condor["vx"]
        elif self.condor["vx"] < 0.0 and self.condor["x"] < -3.0:
            self.condor["x"] = -3.0
            self.condor["vx"] = -self.condor["vx"]

        if self.player_y <= 2.5:
            dx = self.player_x - self.condor["x"]
            dy = self.player_y - self.condor["y"]
            if dx * dx + dy * dy <= 1.8:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 1000
                if self.score > self.high_score:
                    self.high_score = self.score

    def check_collisions(self):
        for topi in self.topis:
            if not topi["active"]:
                continue

            fy = topi["floor_y"]
            if abs(self.player_y - (fy - 1.0)) < 0.5:
                if abs(self.player_x - topi["x"]) < 0.8:
                    if self.hammer_timer > 0.0:
                        topi["active"] = False
                        self.score += 200
                        if self.score > self.high_score:
                            self.high_score = self.score
                    else:
                        self.lives -= 1
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

    def render(self) -> bytes:
        fb = bytearray([15, 23, 42] * 256)

        # Mountain Floors
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if self.ice_grid[y][x] == 1:
                    fb[idx:idx + 3] = bytes([52, 73, 94])
                elif self.ice_grid[y][x] == 2:
                    fb[idx:idx + 3] = bytes([0, 210, 255])

        # Condor
        if self.condor["active"]:
            cx = int(round(self.condor["x"]))
            cy = int(round(self.condor["y"]))
            if 0 <= cx < 16 and 0 <= cy < 16:
                idx = (cy * 16 + cx) * 3
                fb[idx:idx + 3] = bytes([255, 215, 0])
                if cx > 0:
                    fb[(cy * 16 + (cx - 1)) * 3:(cy * 16 + (cx - 1)) * 3 + 3] = bytes([241, 196, 15])

        # Topis
        for topi in self.topis:
            if not topi["active"]:
                continue
            tx = int(round(topi["x"]))
            ty = topi["floor_y"] - 1
            if 0 <= tx < 16 and 0 <= ty < 16:
                idx = (ty * 16 + tx) * 3
                fb[idx:idx + 3] = bytes([255, 182, 193])

        # Player
        px = int(round(self.player_x))
        py = int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx:idx + 3] = bytes([52, 152, 219])
            if self.hammer_timer > 0.0 and px < 15:
                h_idx = (py * 16 + (px + 1)) * 3
                fb[h_idx:h_idx + 3] = bytes([230, 126, 34])

        # HUD Hearts
        for l in range(min(self.lives, 3)):
            idx = (0 * 16 + l) * 3
            fb[idx:idx + 3] = bytes([231, 76, 60])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "lives": self.lives,
            "floor": self.get_current_floor(),
            "player_pos": (self.player_x, self.player_y),
            "is_grounded": self.is_grounded,
        }
