"""
Game #178: 弹珠回旋环 (Puzz Loop - 1998 Mitchell Corporation)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Mitchell Corporation in 1998, Puzz Loop pioneered the legendary spiral marble
shooting genre that later inspired worldwide phenomena like Zuma and Luxor. With a revolving
central cannon turret firing colored gems into an incoming train of spiraling marbles,
it introduced color matching insertion, magnetic pullback chain reactions, and center drain survival.

Unique Core Mechanic (Strict Zero-Redundancy):
- Revolving Central Turret: Aim 360 degrees outward from the arena center (7.5, 7.5).
- Spiraling Marble Chain: Colored marbles advance along a winding spiral track towards the center drain hole.
- Insertion & Match-3 Pop: Fired marbles insert directly into the train; 3 or more matching colors vanish!
- Magnetic Pullback Cascades: Gaps collapse when flanking colors match, pulling the train backwards
  and setting off cascade chain combos!
- Color Swap (Button B): Switch between current active bullet marble and the reserve standby marble.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

STATE_PLAYING = 0
STATE_STAGE_CLEAR = 1
STATE_DRAIN_LOST = 2
STATE_GAME_OVER = 3

COLOR_RED = 1
COLOR_GREEN = 2
COLOR_BLUE = 3
COLOR_YELLOW = 4

class Game178PuzzLoop(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Turret
        self.aim_angle = 0.0 # Radians
        self.cur_color = COLOR_RED
        self.next_color = COLOR_GREEN

        # Fired bullet {active, x, y, vx, vy, color}
        self.bullet = {"active": False, "x": 7.5, "y": 7.5, "vx": 0.0, "vy": 0.0, "color": COLOR_RED}

        # Track waypoints from outer spiral into center (42 waypoints)
        self.track = self._generate_spiral_track()

        # Marble train: list of colors (length up to 24)
        self.train: List[int] = []
        self.train_progress = 0.0 # Float progress index along track
        self.train_speed = 1.0

        self.init()

    @property
    def game_id(self) -> int:
        return 178

    @property
    def name(self) -> str:
        return "弹珠回旋环"

    @property
    def english_name(self) -> str:
        return "Puzz Loop"

    @property
    def release_year(self) -> int:
        return 1998

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "螺旋轨道滚珠链向心推进、中心旋转炮台定向弹射填缝、三色消灭与磁吸回拉级联连锁"

    def get_name(self) -> str:
        return "Puzz Loop (1998)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def _generate_spiral_track(self) -> List[Tuple[float, float]]:
        # Archimedean spiral coordinates from outer border inward to (7.5, 7.5)
        waypoints = []
        steps = 45
        for i in range(steps):
            # Theta spirals from 0 to 4*pi
            theta = (steps - 1 - i) * (3.5 * math.pi / steps)
            r = 1.2 + ((steps - 1 - i) / steps) * 5.8
            x = 7.5 + math.cos(theta) * r
            y = 7.5 + math.sin(theta) * r
            waypoints.append((x, y))
        # Final point is drain center
        waypoints.append((7.5, 7.5))
        return waypoints

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.aim_angle = -math.pi / 2.0 # Aiming up
        self.cur_color = COLOR_RED
        self.next_color = COLOR_BLUE
        self.bullet["active"] = False

        # Build initial train of 16-20 marbles with structured patterns
        palette = [COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW]
        self.train = []
        pattern = [COLOR_RED, COLOR_RED, COLOR_GREEN, COLOR_GREEN, COLOR_BLUE, COLOR_BLUE, COLOR_YELLOW, COLOR_YELLOW]
        for _ in range(2 + self.stage):
            self.train.extend(pattern[:6])

        self.train_progress = 0.0
        self.train_speed = 0.8 + self.stage * 0.15

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_DRAIN_LOST:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.train_progress = 0.0
                    self.bullet["active"] = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Turret Rotation
        rot_speed = 4.5
        if keys_down & KEY_LEFT:  self.aim_angle -= rot_speed * dt
        if keys_down & KEY_RIGHT: self.aim_angle += rot_speed * dt

        # Swap Marble Color (Button B)
        if keys_pressed & KEY_B:
            self.cur_color, self.next_color = self.next_color, self.cur_color

        # Shoot Marble (Button A)
        if (keys_pressed & KEY_A) and not self.bullet["active"]:
            self.bullet["active"] = True
            self.bullet["x"] = 7.5
            self.bullet["y"] = 7.5
            b_spd = 14.0
            self.bullet["vx"] = math.cos(self.aim_angle) * b_spd
            self.bullet["vy"] = math.sin(self.aim_angle) * b_spd
            self.bullet["color"] = self.cur_color
            # Reload
            self.cur_color = self.next_color
            import random
            self.next_color = ((self.cur_color % 4) + 1)

        # Advance Train
        self.train_progress += self.train_speed * dt

        # Check Drain Loss (Head of train reaches track end)
        head_idx = int(self.train_progress) + len(self.train) - 1
        if head_idx >= len(self.track) - 1 and len(self.train) > 0:
            self.lives -= 1
            self.state = STATE_DRAIN_LOST
            self.state_timer = 1.2
            return

        # Update Fired Bullet
        if self.bullet["active"]:
            self.bullet["x"] += self.bullet["vx"] * dt
            self.bullet["y"] += self.bullet["vy"] * dt

            # Offscreen despawn
            if not (0.0 <= self.bullet["x"] <= 15.0 and 0.0 <= self.bullet["y"] <= 15.0):
                self.bullet["active"] = False

            # Check collision with marble train
            elif len(self.train) > 0:
                hit_index = -1
                for i, color in enumerate(self.train):
                    t_idx = int(self.train_progress) + i
                    if 0 <= t_idx < len(self.track):
                        tx, ty = self.track[t_idx]
                        if math.hypot(tx - self.bullet["x"], ty - self.bullet["y"]) < 0.9:
                            hit_index = i
                            break

                if hit_index != -1:
                    # Insert bullet into marble train at hit_index
                    self.train.insert(hit_index, self.bullet["color"])
                    self.bullet["active"] = False
                    self.score += 20
                    self._check_match_3(hit_index)

    def _check_match_3(self, idx: int):
        if idx >= len(self.train):
            return

        target_color = self.train[idx]
        left = idx
        while left > 0 and self.train[left - 1] == target_color:
            left -= 1

        right = idx
        while right < len(self.train) - 1 and self.train[right + 1] == target_color:
            right += 1

        match_count = right - left + 1
        if match_count >= 3:
            # Pop matching marbles!
            del self.train[left:right + 1]
            self.score += match_count * 100

            # Magnetic Pullback: check if flanking ends match
            if left > 0 and left < len(self.train):
                if self.train[left - 1] == self.train[left]:
                    # Pull rear train backward (giving breathing room!)
                    self.train_progress = max(0.0, self.train_progress - 2.0)
                    self.score += 300
                    # Recursive cascade check!
                    self._check_match_3(left)

            # Check Stage Clear
            if len(self.train) == 0:
                self.state = STATE_STAGE_CLEAR
                self.state_timer = 2.0
                self.score += 3000

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

        # 1. Spiral Track Groove (dim gray/indigo path)
        for (tx, ty) in self.track:
            set_pixel(int(round(tx)), int(round(ty)), 30, 30, 45)

        # 2. Central Drain (Black Hole with glowing orange rim)
        set_pixel(7, 7, 255, 60, 0)
        set_pixel(8, 7, 255, 60, 0)
        set_pixel(7, 8, 255, 60, 0)
        set_pixel(8, 8, 255, 60, 0)

        # 3. Marbles along Track
        color_palette = {
            COLOR_RED: (255, 30, 30),
            COLOR_GREEN: (40, 240, 50),
            COLOR_BLUE: (40, 120, 255),
            COLOR_YELLOW: (255, 230, 30),
        }

        for i, color in enumerate(self.train):
            t_idx = int(self.train_progress) + i
            if 0 <= t_idx < len(self.track):
                mx, my = self.track[t_idx]
                r, g, b = color_palette.get(color, (255, 255, 255))
                set_pixel(int(round(mx)), int(round(my)), r, g, b)

        # 4. Fired Bullet
        if self.bullet["active"]:
            bx = int(round(self.bullet["x"]))
            by = int(round(self.bullet["y"]))
            r, g, b = color_palette.get(self.bullet["color"], (255, 255, 255))
            set_pixel(bx, by, r, g, b)

        # 5. Central Revolving Turret (7.5, 7.5) with aim barrel and loaded gem
        cr, cg, cb = color_palette.get(self.cur_color, (255, 255, 255))
        set_pixel(7, 7, cr, cg, cb) # Center active gem

        # Turret barrel pointing along aim_angle
        ax = int(round(7.5 + math.cos(self.aim_angle) * 1.5))
        ay = int(round(7.5 + math.sin(self.aim_angle) * 1.5))
        set_pixel(ax, ay, 240, 240, 240)

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
            "train_len": len(self.train),
            "train_progress": self.train_progress,
            "aim_angle": self.aim_angle,
            "cur_color": self.cur_color,
            "next_color": self.next_color,
            "bullet_active": self.bullet["active"],
        }

