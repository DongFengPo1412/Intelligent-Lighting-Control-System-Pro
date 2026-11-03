"""
Game #172: 伐木工 (Timber - 1984 Bally Midway)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released in 1984 by Bally Midway and created by Steve Meyer, Timber is an exhilarating,
hyper-paced arcade action classic. You play as a flannel-clad lumberjack furiously chopping
tall forest trees with rapid-fire axe swings while avoiding falling tree trunks, dodging
or swatting angry bees, and luring grizzly bears under crashing giant timber for bonus points!

Unique Core Mechanic (Strict Zero-Redundancy):
- Dual Tree Chopping: Work on twin massive timber trees flanking the arena (Left Tree & Right Tree).
- Falling Timber Hazard & Dodge: When tree trunk is fully chopped through, it tilts and crashes inward.
  Lumberjack must immediately sprint in reverse to avoid being squished by the massive falling trunk!
- Grizzly Bear Squishing: Prowling forest bears wander in; timing tree fells to crush the bear yields massive bonuses.
- Bee Swarm Swatting: Swarms of angry bees dive at the player and must be swatted with the axe or dodged.
- Stage Progression: Felling both trees advances the stage to denser timber and faster wildlife.
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
STATE_PLAYER_CRUSHED = 2
STATE_GAME_OVER = 3

TREE_STANDING = 0
TREE_FALLING = 1
TREE_FELLED = 2

class Game172Timber(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player Lumberjack
        self.px = 7.5
        self.py = 13.0
        self.facing = -1 # -1: facing left, 1: facing right
        self.axe_timer = 0.0 # Time remaining in axe swing animation

        # Trees (Left at x=2, Right at x=13)
        self.left_chops = 5
        self.right_chops = 5
        self.max_chops = 5
        self.left_tree_state = TREE_STANDING
        self.right_tree_state = TREE_STANDING
        self.left_fall_timer = 0.0
        self.right_fall_timer = 0.0

        # Forest wildlife: Bear
        self.bear_x = 7.5
        self.bear_alive = True
        self.bear_dir = 1.0
        self.bear_speed = 2.0

        # Bee swarm
        self.bee_x = 7.5
        self.bee_y = 1.0
        self.bee_alive = True
        self.bee_speed = 2.5

        self.init()

    @property
    def game_id(self) -> int:
        return 172

    @property
    def name(self) -> str:
        return "伐木工"

    @property
    def english_name(self) -> str:
        return "Timber"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "左右双向巨树快斧砍伐、落木倾倒反向闪避防砸、伐木压扁游荡黑熊与限时清林"

    def get_name(self) -> str:
        return "Timber (1984)"

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
        self.px = 7.5
        self.py = 13.0
        self.facing = -1
        self.axe_timer = 0.0

        self.max_chops = 5 + self.stage
        self.left_chops = self.max_chops
        self.right_chops = self.max_chops
        self.left_tree_state = TREE_STANDING
        self.right_tree_state = TREE_STANDING
        self.left_fall_timer = 0.0
        self.right_fall_timer = 0.0

        self.bear_x = 7.5
        self.bear_alive = True
        self.bear_dir = 1.0
        self.bear_speed = 2.0 + self.stage * 0.3

        self.bee_x = 8.0
        self.bee_y = 2.0
        self.bee_alive = True
        self.bee_speed = 2.2 + self.stage * 0.3

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_PLAYER_CRUSHED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.axe_timer = 0.0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Movement
        speed = 6.0
        if keys_down & KEY_LEFT:
            self.px -= speed * dt
            self.facing = -1
        if keys_down & KEY_RIGHT:
            self.px += speed * dt
            self.facing = 1

        # Bounds: between left tree trunk (x=2) and right tree trunk (x=13)
        self.px = max(3.0, min(12.0, self.px))

        if self.axe_timer > 0.0:
            self.axe_timer -= dt

        # Axe Swing: Button A (Chop)
        if keys_pressed & KEY_A:
            self.axe_timer = 0.2
            # Check if adjacent to left tree (x ~ 3.0) and facing left
            if self.px <= 3.6 and self.facing == -1:
                if self.left_tree_state == TREE_STANDING:
                    self.left_chops -= 1
                    self.score += 50
                    if self.left_chops <= 0:
                        self.left_tree_state = TREE_FALLING
                        self.left_fall_timer = 1.0 # 1.0 second falling animation

            # Check if adjacent to right tree (x ~ 12.0) and facing right
            elif self.px >= 11.4 and self.facing == 1:
                if self.right_tree_state == TREE_STANDING:
                    self.right_chops -= 1
                    self.score += 50
                    if self.right_chops <= 0:
                        self.right_tree_state = TREE_FALLING
                        self.right_fall_timer = 1.0

            # Also can swat bee if bee is within axe reach
            if self.bee_alive:
                if math.hypot(self.bee_x - (self.px + self.facing * 0.8), self.bee_y - self.py) < 1.4:
                    self.bee_alive = False
                    self.score += 300

        # Update Tree Falling Dynamics
        # Left tree falls towards right: danger zone x in [2.0, 7.0]
        if self.left_tree_state == TREE_FALLING:
            self.left_fall_timer -= dt
            # If player stays in danger zone when tree crashes (fall_timer < 0.3)
            if self.left_fall_timer < 0.3 and self.left_fall_timer > 0.0:
                if self.px <= 6.5:
                    self.lives -= 1
                    self.state = STATE_PLAYER_CRUSHED
                    self.state_timer = 1.2
                    return
                # Check if Bear is caught in crash zone
                if self.bear_alive and self.bear_x <= 6.5:
                    self.bear_alive = False
                    self.score += 800

            if self.left_fall_timer <= 0.0:
                self.left_tree_state = TREE_FELLED
                self.score += 500
                self._check_stage_clear()

        # Right tree falls towards left: danger zone x in [8.0, 13.0]
        if self.right_tree_state == TREE_FALLING:
            self.right_fall_timer -= dt
            if self.right_fall_timer < 0.3 and self.right_fall_timer > 0.0:
                if self.px >= 8.5:
                    self.lives -= 1
                    self.state = STATE_PLAYER_CRUSHED
                    self.state_timer = 1.2
                    return
                # Check if Bear is caught in crash zone
                if self.bear_alive and self.bear_x >= 8.5:
                    self.bear_alive = False
                    self.score += 800

            if self.right_fall_timer <= 0.0:
                self.right_tree_state = TREE_FELLED
                self.score += 500
                self._check_stage_clear()

        # Bear AI: patrols back and forth across x in [3.5, 11.5]
        if self.bear_alive:
            self.bear_x += self.bear_dir * self.bear_speed * dt
            if self.bear_x > 11.5:
                self.bear_x = 11.5
                self.bear_dir = -1.0
            elif self.bear_x < 3.5:
                self.bear_x = 3.5
                self.bear_dir = 1.0

            # Bear mauls lumberjack on direct collision (if player not currently crushing bear)
            if abs(self.bear_x - self.px) < 0.8:
                self.lives -= 1
                self.state = STATE_PLAYER_CRUSHED
                self.state_timer = 1.2
                return

        # Bee AI: descends down towards player
        if self.bee_alive:
            bdx = self.px - self.bee_x
            bdy = self.py - self.bee_y
            dist = math.hypot(bdx, bdy)
            if dist > 0.1:
                self.bee_x += (bdx / dist) * self.bee_speed * dt
                self.bee_y += (bdy / dist) * self.bee_speed * dt

            # Bee stings lumberjack
            if dist < 0.7:
                self.lives -= 1
                self.state = STATE_PLAYER_CRUSHED
                self.state_timer = 1.2
                return

    def _check_stage_clear(self):
        if self.left_tree_state == TREE_FELLED and self.right_tree_state == TREE_FELLED:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 2000

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

        # 1. Forest Ground at y=14..15
        for x in range(16):
            set_pixel(x, 14, 20, 100, 20) # Grass
            set_pixel(x, 15, 80, 50, 20)  # Earth

        # 2. Left Tree Trunk (x=2) & Canopy (y <= 3)
        if self.left_tree_state == TREE_STANDING:
            for y in range(0, 14):
                set_pixel(2, y, 120, 70, 30)
            for y in range(0, 4):
                set_pixel(1, y, 10, 140, 20)
                set_pixel(3, y, 10, 140, 20)
            # Notch indicator
            if self.left_chops < self.max_chops:
                set_pixel(3, 12, 255, 200, 50)
        elif self.left_tree_state == TREE_FALLING:
            # Falling tree slant across y=12..14
            progress = 1.0 - self.left_fall_timer
            crash_x = int(2 + progress * 5)
            for x in range(2, min(16, crash_x + 1)):
                set_pixel(x, 13, 160, 90, 40)
        elif self.left_tree_state == TREE_FELLED:
            # Stump at x=2, fallen log at bottom
            set_pixel(2, 13, 100, 50, 20)

        # 3. Right Tree Trunk (x=13) & Canopy
        if self.right_tree_state == TREE_STANDING:
            for y in range(0, 14):
                set_pixel(13, y, 120, 70, 30)
            for y in range(0, 4):
                set_pixel(12, y, 10, 140, 20)
                set_pixel(14, y, 10, 140, 20)
            if self.right_chops < self.max_chops:
                set_pixel(12, 12, 255, 200, 50)
        elif self.right_tree_state == TREE_FALLING:
            progress = 1.0 - self.right_fall_timer
            crash_x = int(13 - progress * 5)
            for x in range(max(0, crash_x), 14):
                set_pixel(x, 13, 160, 90, 40)
        elif self.right_tree_state == TREE_FELLED:
            set_pixel(13, 13, 100, 50, 20)

        # 4. Bear
        if self.bear_alive:
            bx = int(round(self.bear_x))
            set_pixel(bx, 13, 100, 40, 20)
            set_pixel(bx, 12, 140, 60, 30) # Bear head

        # 5. Bee Swarm
        if self.bee_alive:
            beex = int(round(self.bee_x))
            beey = int(round(self.bee_y))
            set_pixel(beex, beey, 255, 240, 30)

        # 6. Lumberjack Player
        px = int(round(self.px))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, 13, 30, 80, 200) # Blue denim pants
            set_pixel(px, 12, 220, 40, 30)  # Red plaid shirt
            set_pixel(px, 11, 240, 180, 140) # Face / Yellow cap
            # Axe swing
            if self.axe_timer > 0.0:
                ax = px + self.facing
                set_pixel(ax, 12, 220, 220, 230) # Silver axe head
        elif self.state == STATE_PLAYER_CRUSHED:
            set_pixel(px, 13, 255, 100, 0)
            set_pixel(px, 12, 255, 0, 0)

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
            "px": self.px,
            "left_chops": self.left_chops,
            "right_chops": self.right_chops,
            "left_tree_state": self.left_tree_state,
            "right_tree_state": self.right_tree_state,
            "bear_alive": self.bear_alive,
            "bee_alive": self.bee_alive,
        }

