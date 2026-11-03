# -*- coding: utf-8 -*-
"""
Game #146: 碰碰小猪 (Butasan 1987 / Jaleco)
街机历史上最经典的数字引信炸弹搬运投掷与滑行飞踢对战动作游戏：
竞技场散落多秒倒计时炸弹、按键A双手举起炸弹并定向抛投、
按键B滑铲飞踢地面炸弹产生直线滑行冲击、连锁爆风清屏歼灭敌方小猪。
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
STATE_PIG_BLASTED = 2
STATE_GAME_OVER = 3


class Game146Butasan(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7.5
        self.py = 12.0
        self.facing_x = 0.0
        self.facing_y = -1.0  # Facing Up by default

        self.held_bomb: Optional[Dict[str, Any]] = None

        # Bombs in the arena
        self.bombs: List[Dict[str, Any]] = []

        # Explosions
        self.explosions: List[Dict[str, Any]] = []

        # Enemy pigs
        self.enemies: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 146

    @property
    def name(self) -> str:
        return "碰碰小猪"

    @property
    def english_name(self) -> str:
        return "Butasan"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "数字引信炸弹搬运抛投、滑铲踢雷直线冲撞、连环殉爆爆风波及与小猪乱斗竞技"

    def get_name(self) -> str:
        return "Butasan (1987)"

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
        self.px = 7.5
        self.py = 12.0
        self.facing_x = 0.0
        self.facing_y = -1.0
        self.held_bomb = None

        self.explosions = []

        # Spawn initial bombs
        self.bombs = [
            {"x": 4.0, "y": 8.0, "fuse": 10.0, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True},
            {"x": 11.0, "y": 8.0, "fuse": 10.0, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True},
            {"x": 7.5, "y": 5.0, "fuse": 5.0, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True},
            {"x": 7.5, "y": 10.0, "fuse": 15.0, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True},
        ]

        # Spawn enemy pigs
        self.enemies = [
            {"x": 3.0, "y": 3.0, "vx": 1.5, "vy": 0.0, "held_bomb": None, "alive": True},
            {"x": 12.0, "y": 3.0, "vx": -1.5, "vy": 0.0, "held_bomb": None, "alive": True},
            {"x": 7.5, "y": 2.0, "vx": 0.0, "vy": 1.5, "held_bomb": None, "alive": True},
        ]

    def _explode_bomb(self, bx: float, by: float) -> None:
        ix = int(round(bx))
        iy = int(round(by))
        # Create cross explosion pattern: center + 4 neighbors
        for ox, oy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            ex = ix + ox
            ey = iy + oy
            if 1 <= ex <= 14 and 1 <= ey <= 14:
                self.explosions.append({"x": ex, "y": ey, "timer": 0.4})

        # Chain reaction with nearby bombs
        for b in self.bombs:
            if b["active"] and b["state"] != "held":
                if abs(b["x"] - bx) <= 1.4 and abs(b["y"] - by) <= 1.4:
                    b["fuse"] = 0.05

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_PIG_BLASTED):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_PIG_BLASTED:
                    if self.lives > 0:
                        self.px = 7.5
                        self.py = 12.0
                        self.held_bomb = None
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
        # 1. Player Movement & Facing
        move_speed = 5.5 if self.held_bomb is None else 4.2
        dx = 0.0
        dy = 0.0
        if buttons & KEY_LEFT:
            dx -= move_speed
            self.facing_x = -1.0
            self.facing_y = 0.0
        elif buttons & KEY_RIGHT:
            dx += move_speed
            self.facing_x = 1.0
            self.facing_y = 0.0
        elif buttons & KEY_UP:
            dy -= move_speed
            self.facing_x = 0.0
            self.facing_y = -1.0
        elif buttons & KEY_DOWN:
            dy += move_speed
            self.facing_x = 0.0
            self.facing_y = 1.0

        self.px = max(1.5, min(13.5, self.px + dx * dt))
        self.py = max(1.5, min(13.5, self.py + dy * dt))

        # 2. Pick up or Throw Bomb: Key A
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if self.held_bomb is None:
                # Attempt to pick up nearest ground bomb
                closest_bomb = None
                min_d = 1.3
                for b in self.bombs:
                    if b["active"] and b["state"] in ("ground", "sliding"):
                        d = math.hypot(b["x"] - self.px, b["y"] - self.py)
                        if d < min_d:
                            min_d = d
                            closest_bomb = b
                if closest_bomb:
                    closest_bomb["state"] = "held"
                    self.held_bomb = closest_bomb
            else:
                # Throw held bomb forward!
                b = self.held_bomb
                b["state"] = "flying"
                b["x"] = self.px + self.facing_x * 0.8
                b["y"] = self.py + self.facing_y * 0.8
                b["vx"] = self.facing_x * 12.0
                b["vy"] = self.facing_y * 12.0
                self.held_bomb = None

        # 3. Kick Ground Bomb: Key B
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.held_bomb is None:
                for b in self.bombs:
                    if b["active"] and b["state"] in ("ground", "sliding"):
                        if abs(b["x"] - self.px) < 1.3 and abs(b["y"] - self.py) < 1.3:
                            b["state"] = "sliding"
                            b["vx"] = self.facing_x * 14.0
                            b["vy"] = self.facing_y * 14.0
                            break

        # 4. Update Held Bomb Position & Fuse
        if self.held_bomb:
            self.held_bomb["x"] = self.px
            self.held_bomb["y"] = self.py - 0.8

        # 5. Update Bombs
        for b in self.bombs:
            if not b["active"]:
                continue

            # Fuse countdown
            b["fuse"] -= dt
            if b["fuse"] <= 0.0:
                b["active"] = False
                if self.held_bomb == b:
                    self.held_bomb = None
                    self._lose_life()
                    return
                self._explode_bomb(b["x"], b["y"])
                continue

            # Flying / Sliding physics
            if b["state"] in ("flying", "sliding"):
                b["x"] += b["vx"] * dt
                b["y"] += b["vy"] * dt

                # Wall bounce
                if b["x"] <= 1.5:
                    b["x"] = 1.5
                    b["vx"] = -b["vx"] * 0.7
                    b["state"] = "ground"
                elif b["x"] >= 13.5:
                    b["x"] = 13.5
                    b["vx"] = -b["vx"] * 0.7
                    b["state"] = "ground"

                if b["y"] <= 1.5:
                    b["y"] = 1.5
                    b["vy"] = -b["vy"] * 0.7
                    b["state"] = "ground"
                elif b["y"] >= 13.5:
                    b["y"] = 13.5
                    b["vy"] = -b["vy"] * 0.7
                    b["state"] = "ground"

                # Check direct collision with enemy pigs
                for e in self.enemies:
                    if e["alive"]:
                        if abs(b["x"] - e["x"]) < 1.0 and abs(b["y"] - e["y"]) < 1.0:
                            b["active"] = False
                            self.score += 250
                            self._explode_bomb(b["x"], b["y"])
                            break

        self.bombs = [b for b in self.bombs if b["active"]]

        # Spawn extra bombs if less than 3
        if len(self.bombs) < 3:
            rx = 3.0 + (len(self.bombs) * 4.0) % 10.0
            ry = 4.0 + (len(self.bombs) * 3.5) % 8.0
            self.bombs.append({
                "x": rx, "y": ry, "fuse": 10.0, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True
            })

        # 6. Update Explosions
        for exp in self.explosions:
            exp["timer"] -= dt

            # Blast hits player
            if abs(self.px - exp["x"]) < 0.8 and abs(self.py - exp["y"]) < 0.8:
                self._lose_life()
                return

            # Blast hits enemies
            for e in self.enemies:
                if e["alive"]:
                    if abs(e["x"] - exp["x"]) < 0.8 and abs(e["y"] - exp["y"]) < 0.8:
                        e["alive"] = False
                        self.score += 200

        self.explosions = [exp for exp in self.explosions if exp["timer"] > 0.0]

        # 7. Update Enemy Pigs
        all_enemies_dead = True
        for e in self.enemies:
            if not e["alive"]:
                continue
            all_enemies_dead = False

            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["x"] <= 2.0 or e["x"] >= 13.0:
                e["vx"] = -e["vx"]
            if e["y"] <= 2.0 or e["y"] >= 13.0:
                e["vy"] = -e["vy"]

            # Enemy pig touches player directly
            if abs(self.px - e["x"]) < 0.8 and abs(self.py - e["y"]) < 0.8:
                self._lose_life()
                return

        # Stage clear
        if all_enemies_dead:
            self.score += 1000
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_PIG_BLASTED
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

        # 1. Arena Border Fence
        for x in range(16):
            set_pixel(x, 0, 100, 60, 40)
            set_pixel(x, 15, 100, 60, 40)
        for y in range(16):
            set_pixel(0, y, 100, 60, 40)
            set_pixel(15, y, 100, 60, 40)

        # 2. Bombs
        for b in self.bombs:
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if b["fuse"] < 3.0:
                # Urgent flashing red/yellow
                flash = int(b["fuse"] * 10) % 2
                if flash == 0:
                    set_pixel(bx, by, 255, 30, 20)
                else:
                    set_pixel(bx, by, 255, 240, 40)
            else:
                # Black bomb body with yellow fuse spark
                set_pixel(bx, by, 40, 40, 40)
                set_pixel(bx, by - 1, 255, 220, 50)

        # 3. Explosions (Yellow-Orange blast fire)
        for exp in self.explosions:
            set_pixel(exp["x"], exp["y"], 255, 160, 30)

        # 4. Enemy Pigs (Brown / Purple)
        for e in self.enemies:
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(e["y"]))
                set_pixel(ex, ey, 140, 80, 50)
                set_pixel(ex, ey - 1, 240, 160, 140)  # Snout

        # 5. Player Pig (Pink Piglet!)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 255, 160, 180)      # Pink body
            set_pixel(px, py - 1, 255, 120, 150)  # Ears/snout
            if self.held_bomb:
                # Holding bomb above head
                set_pixel(px, py - 2, 255, 40, 40)
        elif self.state == STATE_PIG_BLASTED:
            set_pixel(px, py, 255, 60, 30)

        # 6. Lives count
        for l in range(min(self.lives, 3)):
            set_pixel(1 + l * 2, 0, 255, 160, 180)

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
            "held_bomb": self.held_bomb is not None,
            "bombs_count": len(self.bombs),
            "explosions_count": len(self.explosions),
        }
