"""
Game #103: 大金刚二代 / 小金刚 (Donkey Kong Jr. 1982 / Nintendo)
Single vs dual vine climbing speed differential, dropping fruit traps to crush Snapjaws,
and shoving 4 key shackles to break open Papa Donkey Kong's cage.
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

STATE_CLIMBING = 0
STATE_KEY_INSERTED = 1
STATE_STAGE_CLEAR = 2
STATE_FALL_DOWN = 3
STATE_GAME_OVER = 4

VINE_X = [2.0, 6.0, 10.0, 14.0]
NUM_VINES = 4
MAX_SNAPJAWS = 3
MAX_FRUITS = 2
TOTAL_KEYS = 4


class Game103DKJr(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_CLIMBING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.keys_inserted = 0

        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.current_vine = 0
        self.on_ground = True
        self.gripping_two_vines = False
        self.facing = 1

        self.snapjaws: List[Dict[str, Any]] = []
        self.fruits: List[Dict[str, Any]] = []
        self.keys_unlocked: List[bool] = [False] * TOTAL_KEYS

        self.reset()

    @property
    def game_id(self) -> int:
        return 103

    @property
    def name(self) -> str:
        return "大金刚二代"

    @property
    def english_name(self) -> str:
        return "Donkey Kong Jr."

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "单双藤蔓攀爬升降差速、高空摘果砸落夹子鳄、救父顶开四重牢笼锁链"

    def get_name(self) -> str:
        return "Donkey Kong Jr. (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self._reset_stage()

    def _reset_stage(self) -> None:
        self.state = STATE_CLIMBING
        self.state_timer = 0.0
        self.keys_inserted = 0

        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.current_vine = 0
        self.on_ground = True
        self.gripping_two_vines = False
        self.facing = 1

        self.keys_unlocked = [False] * TOTAL_KEYS

        self.fruits = [
            {"x": VINE_X[1], "y": 5.0, "vine_idx": 1, "falling": False, "vy": 0.0, "active": True},
            {"x": VINE_X[2], "y": 6.0, "vine_idx": 2, "falling": False, "vy": 0.0, "active": True},
        ]

        self.snapjaws = []
        for i in range(MAX_SNAPJAWS):
            v_idx = (i + 1) % NUM_VINES
            self.snapjaws.append({
                "x": VINE_X[v_idx],
                "y": 2.5 + float(i * 3.5),
                "vy": 2.2 + float(i) * 0.4,
                "vine_idx": v_idx,
                "is_red": (i % 2 == 0),
                "active": True,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_FALL_DOWN:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_CLIMBING
                    self.state_timer = 0.0
                    self.px = 2.0
                    self.py = 13.0
                    self.vx = 0.0
                    self.vy = 0.0
                    self.on_ground = True
                    self.gripping_two_vines = False
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.5:
                self._reset_stage()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_junior(dt, buttons, prev_buttons)
        self._update_snapjaws(dt)
        self._update_fruits(dt)
        self._check_collisions()

        if self.keys_inserted >= TOTAL_KEYS and self.state != STATE_STAGE_CLEAR:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 2000

    def _update_junior(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Jump
        if (buttons & KEY_A) and not (prev_buttons & KEY_A) and (self.on_ground or not self.gripping_two_vines):
            self.vy = -6.0
            if buttons & KEY_LEFT:
                self.vx = -4.5
            elif buttons & KEY_RIGHT:
                self.vx = 4.5
            else:
                self.vx = float(self.facing) * 3.0
            self.on_ground = False

        if not self.on_ground and self.vy != 0.0:
            self.py += self.vy * dt
            self.px += self.vx * dt
            self.vy += 14.0 * dt

            for v in range(NUM_VINES):
                if v != self.current_vine and abs(self.px - VINE_X[v]) < 0.6 and 2.0 <= self.py <= 13.0:
                    self.px = VINE_X[v]
                    self.vx = 0.0
                    self.vy = 0.0
                    self.current_vine = v
                    self.gripping_two_vines = False
                    break

            for v in range(NUM_VINES - 1):
                mid_x = (VINE_X[v] + VINE_X[v + 1]) * 0.5
                if abs(self.px - mid_x) < 0.6 and 2.0 <= self.py <= 13.0:
                    self.px = mid_x
                    self.vx = 0.0
                    self.vy = 0.0
                    self.current_vine = v
                    self.gripping_two_vines = True
                    break

            if self.py >= 13.0:
                self.py = 13.0
                self.vy = 0.0
                self.vx = 0.0
                self.on_ground = True
        else:
            if self.py >= 13.0:
                self.on_ground = True
                if buttons & KEY_LEFT:
                    self.px = max(1.0, self.px - 5.0 * dt)
                    self.facing = -1
                elif buttons & KEY_RIGHT:
                    self.px = min(15.0, self.px + 5.0 * dt)
                    self.facing = 1

                if buttons & KEY_UP:
                    for v in range(NUM_VINES):
                        if abs(self.px - VINE_X[v]) < 0.8:
                            self.px = VINE_X[v]
                            self.current_vine = v
                            self.on_ground = False
                            self.gripping_two_vines = False
                            self.py -= 0.5
                            break
            else:
                self.on_ground = False
                if buttons & KEY_LEFT:
                    self.facing = -1
                    if self.gripping_two_vines:
                        self.px = VINE_X[self.current_vine]
                        self.gripping_two_vines = False
                    elif self.current_vine > 0:
                        self.current_vine -= 1
                        self.px = (VINE_X[self.current_vine] + VINE_X[self.current_vine + 1]) * 0.5
                        self.gripping_two_vines = True
                elif buttons & KEY_RIGHT:
                    self.facing = 1
                    if not self.gripping_two_vines and self.current_vine < NUM_VINES - 1:
                        self.px = (VINE_X[self.current_vine] + VINE_X[self.current_vine + 1]) * 0.5
                        self.gripping_two_vines = True
                    elif self.gripping_two_vines:
                        self.current_vine += 1
                        self.px = VINE_X[self.current_vine]
                        self.gripping_two_vines = False

                # Climb UP speed: 2 vines = 6.0, 1 vine = 3.0
                # Slide DOWN speed: 2 vines = 2.5, 1 vine = 7.5
                climb_up_spd = 6.0 if self.gripping_two_vines else 3.0
                slide_down_spd = 2.5 if self.gripping_two_vines else 7.5

                if buttons & KEY_UP:
                    self.py = max(2.0, self.py - climb_up_spd * dt)
                elif buttons & KEY_DOWN:
                    self.py += slide_down_spd * dt
                    if self.py >= 13.0:
                        self.py = 13.0
                        self.on_ground = True

                if self.py <= 2.2 and not self.gripping_two_vines:
                    if not self.keys_unlocked[self.current_vine]:
                        self.keys_unlocked[self.current_vine] = True
                        self.keys_inserted += 1
                        self.score += 500
                        self.py = 2.8

    def _update_snapjaws(self, dt: float) -> None:
        for i, s in enumerate(self.snapjaws):
            if not s["active"]:
                s["active"] = True
                s["vine_idx"] = (i * 2 + 1) % NUM_VINES
                s["x"] = VINE_X[s["vine_idx"]]
                s["y"] = 1.5
                s["vy"] = 2.4
                continue

            s["y"] += s["vy"] * dt
            if s["y"] >= 14.0:
                if s["is_red"]:
                    s["active"] = False
                else:
                    s["vy"] = -abs(s["vy"])
            elif s["y"] <= 2.0 and s["vy"] < 0.0:
                s["vy"] = abs(s["vy"])

    def _update_fruits(self, dt: float) -> None:
        for f in self.fruits:
            if not f["active"]:
                continue
            if f["falling"]:
                f["y"] += f["vy"] * dt
                f["vy"] += 12.0 * dt
                for s in self.snapjaws:
                    if not s["active"]:
                        continue
                    if abs(f["x"] - s["x"]) < 0.8 and abs(f["y"] - s["y"]) < 1.2:
                        s["active"] = False
                        self.score += 400
                if f["y"] >= 14.0:
                    f["active"] = False
            else:
                if abs(self.px - f["x"]) < 1.0 and abs(self.py - f["y"]) < 1.0:
                    f["falling"] = True
                    f["vy"] = 2.0
                    self.score += 100

    def _check_collisions(self) -> None:
        for s in self.snapjaws:
            if not s["active"]:
                continue
            if abs(self.px - s["x"]) < 0.9 and abs(self.py - s["y"]) < 1.0:
                self.state = STATE_FALL_DOWN
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

        # Mario platform at y=1
        for x in range(16):
            set_pixel(x, 1, 180, 50, 40)
        set_pixel(7, 0, 160, 80, 40)
        set_pixel(8, 0, 180, 100, 50)
        set_pixel(9, 0, 160, 80, 40)
        set_pixel(13, 0, 220, 20, 20)
        set_pixel(14, 0, 20, 40, 220)

        # 4 Key Shackles
        for k in range(TOTAL_KEYS):
            kx = int(VINE_X[k])
            if self.keys_unlocked[k]:
                set_pixel(kx, 2, 255, 220, 0)
            else:
                set_pixel(kx, 2, 100, 100, 120)

        # 4 Vines
        for v in range(NUM_VINES):
            vx = int(VINE_X[v])
            for y in range(3, 14):
                set_pixel(vx, y, 30, 180 if (y % 2 == 0) else 130, 40)

        # Ground
        for x in range(16):
            set_pixel(x, 14, 80, 140, 40)
            set_pixel(x, 15, 60, 40, 20)

        # Fruits
        for f in self.fruits:
            if not f["active"]:
                continue
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            set_pixel(fx, fy, 255, 200, 20)
            set_pixel(fx, fy - 1, 20, 200, 40)

        # Snapjaws
        for s in self.snapjaws:
            if not s["active"]:
                continue
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            if s["is_red"]:
                set_pixel(sx, sy, 255, 50, 40)
            else:
                set_pixel(sx, sy, 40, 120, 255)
            set_pixel(sx, sy - 1, 255, 255, 255)

        # Junior
        jx = int(round(self.px))
        jy = int(round(self.py))

        if self.state == STATE_FALL_DOWN:
            set_pixel(jx, jy, 255, 80, 40)
            set_pixel(jx, jy - 1, 255, 200, 0)
        else:
            set_pixel(jx, jy, 210, 120, 40)
            set_pixel(jx, jy - 1, 230, 150, 70)
            if self.gripping_two_vines:
                set_pixel(jx - 1, jy, 210, 120, 40)
                set_pixel(jx + 1, jy, 210, 120, 40)
            else:
                set_pixel(jx + self.facing, jy - 1, 210, 120, 40)

        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 200, 50)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "keys_inserted": self.keys_inserted,
            "px": self.px,
            "py": self.py,
            "gripping_two_vines": self.gripping_two_vines,
            "current_vine": self.current_vine,
            "on_ground": self.on_ground,
        }
