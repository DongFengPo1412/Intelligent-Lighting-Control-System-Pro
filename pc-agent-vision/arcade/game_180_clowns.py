"""
Game #180: 小丑跷跷板 (Clowns / Circus - 1977 Exidy / Midway)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released in 1977 by Exidy and licensed to Midway as Clowns, this classic pioneered
the seesaw / teeter-totter physics bounce game archetype. Preceding the golden age,
it captivated arcades with dual acrobat catapult mechanics, realistic gravity arcs,
and layered ceiling balloon popping.

Unique Core Mechanic (Strict Zero-Redundancy):
- Dual Acrobat Seesaw Catapult: When the airborne acrobat lands on the seesaw's depressed end,
  kinetic energy is transferred, propelling the waiting acrobat high into the arena rafters.
- Seesaw Positioning & Dynamic Tilt: Steer the seesaw horizontally along the floor to intercept
  the plummeting acrobat, flipping tilt state on each impact.
- 3-Layer Ceiling Balloon Ceiling: Pop through yellow, green, and blue balloon bands for progressive scores.
- Trajectory Deflection & Air Control: Landing closer to the seesaw edge imparts wider lateral angles.
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
STATE_ACROBAT_SPLAT = 2
STATE_GAME_OVER = 3

class Game180Clowns(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Seesaw at floor (y=14)
        self.sx = 7.5
        self.seesaw_tilt = -1 # -1: left low / right high, 1: right low / left high
        self.seesaw_speed = 7.5

        # Airborne Acrobat
        self.ax = 7.5
        self.ay = 4.0
        self.avx = 2.0
        self.avy = 0.0
        self.gravity = 16.0

        # Balloons grid: set of (x, y) for y in (1, 2, 3), x in (1..14)
        self.balloons = set()

        self.init()

    @property
    def game_id(self) -> int:
        return 180

    @property
    def name(self) -> str:
        return "小丑跷跷板"

    @property
    def english_name(self) -> str:
        return "Clowns"

    @property
    def release_year(self) -> int:
        return 1977

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "底座跷跷板接球抛投、双杂技小丑交替重力重力弹射、高空气球阵列逐层引爆清屏"

    def get_name(self) -> str:
        return "Clowns (1977)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

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
        self.sx = 7.5
        self.seesaw_tilt = -1

        # Airborne acrobat drops from top corner
        self.ax = 4.0
        self.ay = 4.0
        self.avx = 2.5
        self.avy = 0.0

        # Fill ceiling balloons
        self.balloons.clear()
        for y in (1, 2, 3):
            for x in range(2, 14):
                self.balloons.add((x, y))

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_ACROBAT_SPLAT:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.ax = 4.0
                    self.ay = 4.0
                    self.avx = 2.5
                    self.avy = 0.0
                    self.seesaw_tilt = -1
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Seesaw Movement
        if keys_down & KEY_LEFT:  self.sx -= self.seesaw_speed * dt
        if keys_down & KEY_RIGHT: self.sx += self.seesaw_speed * dt
        self.sx = max(2.5, min(12.5, self.sx))

        # Boost bounce if Button A pressed during landing
        boost = 1.2 if (keys_pressed & KEY_A) else 1.0

        # Airborne Acrobat Physics
        self.avy += self.gravity * dt
        self.ax += self.avx * dt
        self.ay += self.avy * dt

        # Wall bounces (left at x=1.0, right at x=14.0)
        if self.ax <= 1.0:
            self.ax = 1.0
            self.avx = abs(self.avx)
        elif self.ax >= 14.0:
            self.ax = 14.0
            self.avx = -abs(self.avx)

        # Ceiling bounce
        if self.ay <= 0.5:
            self.ay = 0.5
            self.avy = abs(self.avy)

        # Pop Balloons
        cell = (int(round(self.ax)), int(round(self.ay)))
        if cell in self.balloons:
            self.balloons.remove(cell)
            row = cell[1]
            if row == 1:   self.score += 50 # Blue
            elif row == 2: self.score += 30 # Green
            else:          self.score += 10 # Yellow
            # Bounce slightly on pop
            self.avy = abs(self.avy) * 0.8
            if len(self.balloons) == 0:
                self.state = STATE_STAGE_CLEAR
                self.state_timer = 2.0
                self.score += 2500
                return

        # Check Landing on Seesaw (y ~ 14.0)
        if self.ay >= 13.5 and self.avy > 0.0:
            # Seesaw spans [sx - 1.5, sx + 1.5]
            if abs(self.ax - self.sx) <= 1.5:
                # Successfully caught on seesaw!
                offset = (self.ax - self.sx) / 1.5 # -1.0 to +1.0
                # Launch waiting acrobat up into air!
                self.ay = 13.2
                self.avy = -(13.0 + self.stage * 0.5) * boost
                self.avx = offset * 6.0
                # Flip seesaw tilt
                self.seesaw_tilt = -self.seesaw_tilt
                self.score += 20
            elif self.ay >= 15.0:
                # Missed seesaw -> Splat on floor!
                self.lives -= 1
                self.state = STATE_ACROBAT_SPLAT
                self.state_timer = 1.2
                return

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

        # 1. Floor at y=15
        for x in range(16):
            set_pixel(x, 15, 60, 40, 20)

        # 2. Ceiling Balloons
        for (bx, by) in self.balloons:
            if by == 1:   set_pixel(bx, by, 40, 120, 255) # Blue balloons
            elif by == 2: set_pixel(bx, by, 40, 220, 60)  # Green balloons
            else:         set_pixel(bx, by, 255, 230, 40) # Yellow balloons

        # 3. Seesaw & Waiting Acrobat
        sx = int(round(self.sx))
        # Pivot
        set_pixel(sx, 14, 255, 200, 0)
        if self.seesaw_tilt == -1:
            # Left down (y=14), Right up (y=13)
            set_pixel(sx - 1, 14, 200, 160, 20)
            set_pixel(sx + 1, 13, 200, 160, 20)
            # Waiting acrobat sitting on right high end
            set_pixel(sx + 1, 12, 255, 60, 60) # Red clown
            set_pixel(sx + 1, 11, 255, 220, 140)
        else:
            # Left up (y=13), Right down (y=14)
            set_pixel(sx - 1, 13, 200, 160, 20)
            set_pixel(sx + 1, 14, 200, 160, 20)
            # Waiting acrobat sitting on left high end
            set_pixel(sx - 1, 12, 255, 60, 60)
            set_pixel(sx - 1, 11, 255, 220, 140)

        # 4. Airborne Flying Acrobat
        ax = int(round(self.ax))
        ay = int(round(self.ay))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(ax, ay, 255, 255, 255) # White clown outfit
            set_pixel(ax, ay - 1, 40, 180, 255) # Blue cap
            set_pixel(ax - 1, ay, 255, 60, 60) # Outstretched hands
            set_pixel(ax + 1, ay, 255, 60, 60)
        elif self.state == STATE_ACROBAT_SPLAT:
            set_pixel(ax, 15, 255, 80, 0)
            set_pixel(ax - 1, 15, 255, 0, 0)
            set_pixel(ax + 1, 15, 255, 0, 0)

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
            "sx": self.sx,
            "ax": self.ax,
            "ay": self.ay,
            "balloons_left": len(self.balloons),
            "seesaw_tilt": self.seesaw_tilt,
        }
