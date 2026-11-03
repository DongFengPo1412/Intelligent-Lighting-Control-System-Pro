"""
Game #186: 冠军棒球 (Champion Baseball - 1983 Sega / Alpha Denshi)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Sega in 1983 (developed by Alpha Denshi), Champion Baseball was the revolutionary
pioneer of modern video game baseball. It introduced the iconic pitcher-batter duel view,
nine-zone pitch trajectory, realistic balls/strikes count, base-running diamond tracking,
and authentic innings defense play.

Unique Core Mechanic (Strict Zero-Redundancy):
- Pitcher vs Batter Strike Zone Duel: Pitch curves and speeds towards home plate; batter adjusts
  stance in batter's box to anticipate trajectory.
- Contact Timing Bat Swing (Button A): Time swing precision when ball crosses the plate.
  Sweet spot contact produces line drives, grounders, and soaring home runs!
- Bunt & Contact Tap (Button B): Lay down a sacrificial bunt or squeeze play to advance base runners.
- Diamond Base Running & Outs: 3 strikes per out, 3 outs per half-inning. Runners advance around
  1st, 2nd, 3rd, and Home base to score runs!
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

STATE_PITCHING = 0
STATE_BALL_IN_PLAY = 1
STATE_INNING_END = 2
STATE_GAME_OVER = 3

class Game186ChampionBaseball(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PITCHING
        self.score = 0
        self.inning = 1
        self.outs = 0
        self.strikes = 0
        self.balls = 0
        self.state_timer = 0.0

        # Batter stance at home plate
        self.batter_x = 7.5
        self.batter_y = 13.0
        self.is_swinging = False
        self.swing_timer = 0.0

        # Pitcher & Ball
        self.pitcher_x = 7.5
        self.pitcher_y = 4.0
        self.ball_x = 7.5
        self.ball_y = 4.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_active = False
        self.ball_air_timer = 0.0
        self.is_hit = False

        # Diamond Bases: [1st, 2nd, 3rd] occupied booleans
        self.bases = [False, False, False]
        self.pitch_cooldown = 0.8

        self.init()

    @property
    def game_id(self) -> int:
        return 186

    @property
    def name(self) -> str:
        return "冠军棒球"

    @property
    def english_name(self) -> str:
        return "Champion Baseball"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "投打对决变化球速控投球、击球员分寸时机挥棒推打安打、全垒跑垒盗垒触杀与三振出局"

    def get_name(self) -> str:
        return "Champion Baseball (1983)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.inning = 1
        self.outs = 0
        self.strikes = 0
        self.balls = 0
        self.bases = [False, False, False]
        self._init_at_bat()

    def _init_at_bat(self):
        self.state = STATE_PITCHING
        self.state_timer = 0.0
        self.batter_x = 7.5
        self.batter_y = 13.0
        self.is_swinging = False
        self.swing_timer = 0.0

        self.ball_x = self.pitcher_x
        self.ball_y = self.pitcher_y
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_active = False
        self.is_hit = False
        self.pitch_cooldown = 0.6

    def _pitch_ball(self):
        self.ball_active = True
        self.ball_x = self.pitcher_x
        self.ball_y = self.pitcher_y
        # Slight variation in speed and curve
        curve = (float((self.strikes * 3 + self.balls * 7) % 5) - 2.0) * 0.4
        self.ball_vx = curve
        self.ball_vy = 12.0 + float(self.inning % 3) * 1.5

    def _advance_runners(self, bases_hit: int):
        # bases_hit: 1=Single, 2=Double, 3=Triple, 4=HomeRun
        runs = 0
        for b in range(2, -1, -1):
            if self.bases[b]:
                self.bases[b] = False
                target = b + bases_hit
                if target >= 3:
                    runs += 1
                else:
                    self.bases[target] = True

        # Batter advances
        if bases_hit >= 4:
            runs += 1
        else:
            self.bases[bases_hit - 1] = True

        self.score += runs * 1000 + bases_hit * 200

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_INNING_END:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.inning += 1
                if self.inning > 9:
                    self.state = STATE_GAME_OVER
                else:
                    self.outs = 0
                    self.strikes = 0
                    self.balls = 0
                    self.bases = [False, False, False]
                    self._init_at_bat()
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Batter Box Stance Adjustment (Left/Right)
        if keys_down & KEY_LEFT:
            self.batter_x = max(5.0, self.batter_x - 6.0 * dt)
        if keys_down & KEY_RIGHT:
            self.batter_x = min(10.0, self.batter_x + 6.0 * dt)

        # Swing Bat (Button A = Full Swing, Button B = Bunt)
        swing_type = 0
        if (keys_pressed & KEY_A) and not self.is_swinging:
            self.is_swinging = True
            self.swing_timer = 0.22 # Swing active window
            swing_type = 1 # Full swing
        elif (keys_pressed & KEY_B) and not self.is_swinging:
            self.is_swinging = True
            self.swing_timer = 0.35
            swing_type = 2 # Bunt tap

        if self.is_swinging:
            self.swing_timer -= dt
            if self.swing_timer <= 0.0:
                self.is_swinging = False

        # Pitching State
        if self.state == STATE_PITCHING:
            if not self.ball_active:
                self.pitch_cooldown -= dt
                if self.pitch_cooldown <= 0.0:
                    self._pitch_ball()
            else:
                # Ball travels towards home plate
                self.ball_x += self.ball_vx * dt
                self.ball_y += self.ball_vy * dt

                # Check Bat Contact
                if self.is_swinging and (12.0 <= self.ball_y <= 13.8):
                    dist = abs(self.ball_x - self.batter_x)
                    if dist <= 1.5:
                        # Ball Hit!
                        self.is_hit = True
                        self.state = STATE_BALL_IN_PLAY
                        # Calculate hit trajectory
                        offset = self.ball_x - self.batter_x
                        if swing_type == 2: # Bunt
                            self.ball_vx = offset * 2.0
                            self.ball_vy = -4.0
                            self.ball_air_timer = 0.8
                        else: # Full swing
                            self.ball_vx = offset * 8.0
                            self.ball_vy = -14.0
                            self.ball_air_timer = 1.4 if dist < 0.6 else 0.9 # Sweet spot = Long fly/Home run!
                        return

                # Ball crosses home plate without hit
                if self.ball_y >= 14.5:
                    self.ball_active = False
                    # Check strike or ball
                    if 6.0 <= self.ball_x <= 9.0:
                        self.strikes += 1
                        if self.strikes >= 3:
                            self.outs += 1
                            self.strikes = 0
                            self.balls = 0
                            if self.outs >= 3:
                                self.state = STATE_INNING_END
                                self.state_timer = 1.5
                            else:
                                self._init_at_bat()
                        else:
                            self._init_at_bat()
                    else:
                        self.balls += 1
                        if self.balls >= 4: # Walk
                            self.strikes = 0
                            self.balls = 0
                            self._advance_runners(1)
                            self._init_at_bat()
                        else:
                            self._init_at_bat()

        # Ball In Play State
        elif self.state == STATE_BALL_IN_PLAY:
            self.ball_air_timer -= dt
            self.ball_x += self.ball_vx * dt
            self.ball_y += self.ball_vy * dt

            if self.ball_air_timer <= 0.0:
                # Ball lands or caught!
                # If landing in outfield depth (y < 3.0) -> Home Run or Extra base!
                if self.ball_y < 2.0:
                    self._advance_runners(4) # Home Run!
                elif self.ball_y < 5.0:
                    self._advance_runners(2) # Double!
                elif self.ball_y < 9.0:
                    self._advance_runners(1) # Single!
                else:
                    # Ground out to pitcher/infield
                    self.outs += 1
                    if self.outs >= 3:
                        self.state = STATE_INNING_END
                        self.state_timer = 1.5
                        return

                self.strikes = 0
                self.balls = 0
                self._init_at_bat()

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

        # 1. Baseball Field Diamond & Grass
        for y in range(16):
            for x in range(16):
                if y <= 5:
                    set_pixel(x, y, 30, 110, 40)   # Outfield grass
                elif 6 <= y <= 11:
                    # Infield clay dirt
                    if 4 <= x <= 11:
                        set_pixel(x, y, 160, 100, 50)
                    else:
                        set_pixel(x, y, 30, 110, 40)
                else:
                    set_pixel(x, y, 140, 90, 40)    # Home plate clay

        # 2. Bases (White diamonds): Home(7, 13), 1st(12, 9), 2nd(7, 6), 3rd(2, 9)
        set_pixel(7, 13, 255, 255, 255) # Home plate
        set_pixel(12, 9, 255, 255, 0 if self.bases[0] else 255) # 1st base (Yellow if occupied)
        set_pixel(7, 6, 255, 255, 0 if self.bases[1] else 255)  # 2nd base
        set_pixel(2, 9, 255, 255, 0 if self.bases[2] else 255)  # 3rd base

        # 3. Pitcher on Mound
        px = int(round(self.pitcher_x))
        py = int(round(self.pitcher_y))
        set_pixel(px, py, 40, 100, 220)       # Blue pitcher cap
        set_pixel(px, py + 1, 230, 230, 230)  # White jersey

        # 4. Batter & Bat at Home Plate
        bx = int(round(self.batter_x))
        by = int(round(self.batter_y))
        set_pixel(bx, by, 220, 40, 40)        # Red batter helmet
        set_pixel(bx, by + 1, 240, 240, 240)  # Batter uniform
        if self.is_swinging:
            # Sweeping bat wooden pixel
            set_pixel(bx - 1, by, 200, 150, 60)
            set_pixel(bx + 1, by, 200, 150, 60)
        else:
            set_pixel(bx + 1, by - 1, 200, 150, 60) # Bat held upright

        # 5. Baseball
        if self.ball_active or self.state == STATE_BALL_IN_PLAY:
            ball_x = int(round(self.ball_x))
            ball_y = int(round(self.ball_y))
            set_pixel(ball_x, ball_y, 255, 255, 255)

        # 6. Strike / Ball / Out Count Indicators (Top corners)
        # Strikes: Red dots at (0, 0), (1, 0)
        for s in range(self.strikes):
            set_pixel(s, 0, 255, 50, 50)
        # Balls: Green dots at (14, 0), (15, 0)
        for bl in range(self.balls):
            set_pixel(15 - bl, 0, 50, 255, 50)
        # Outs: Orange dots at (0, 1), (1, 1)
        for o in range(self.outs):
            set_pixel(o, 1, 255, 140, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "inning": self.inning,
            "outs": self.outs,
            "strikes": self.strikes,
            "balls": self.balls,
            "bases": self.bases[:],
            "ball_active": self.ball_active,
        }
