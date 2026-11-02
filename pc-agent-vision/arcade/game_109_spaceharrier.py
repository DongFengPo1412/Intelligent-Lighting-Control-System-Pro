"""
Game #109: 太空哈利 (Space Harrier 1985 / Sega)
Pseudo-3D forward scaling perspective over the rolling checkered horizon,
under-arm rocket plasma cannon, tree pillar dodging, and serpentine Uriah dragon boss battle.
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

STATE_FLYING = 0
STATE_BOSS_DRAGON = 1
STATE_HERO_HIT = 2
STATE_STAGE_CLEAR = 3
STATE_GAME_OVER = 4

MAX_SHOTS = 4
MAX_ENTITIES = 4


class Game109SpaceHarrier(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.horizon_scroll = 0.0
        self.enemies_defeated = 0

        self.hero_x = 8.0
        self.hero_y = 11.0
        self.shot_cooldown = 0.0
        self.roll_timer = 0.0

        self.dragon_x = 8.0
        self.dragon_y = 6.0
        self.dragon_z = 6.0
        self.dragon_hp = 8
        self.dragon_angle = 0.0

        self.shots: List[Dict[str, Any]] = []
        self.entities: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 109

    @property
    def name(self) -> str:
        return "太空哈利"

    @property
    def english_name(self) -> str:
        return "Space Harrier"

    @property
    def release_year(self) -> int:
        return 1985

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "伪3D纵深棋盘地平线飞行、巨型图腾柱树木回避、深空等离子重炮与远古神龙对决"

    def get_name(self) -> str:
        return "Space Harrier (1985)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_stage()

    def _init_stage(self) -> None:
        self.state = STATE_FLYING
        self.state_timer = 0.0
        self.horizon_scroll = 0.0
        self.enemies_defeated = 0

        self.hero_x = 8.0
        self.hero_y = 11.0
        self.shot_cooldown = 0.0
        self.roll_timer = 0.0

        self.shots = [
            {"x": 0.0, "y": 0.0, "z": 0.0, "active": False}
            for _ in range(MAX_SHOTS)
        ]

        self.entities = []
        for i in range(MAX_ENTITIES):
            self.entities.append({
                "x": 4.0 + float((i * 3) % 9),
                "y": 5.0 + float(i % 3),
                "z": 6.0 + float(i * 2.0),
                "type": 0 if (i % 2 == 0) else 1,
                "hp": 1,
                "active": True,
            })

    def spawn_dragon_boss(self) -> None:
        self.state = STATE_BOSS_DRAGON
        self.state_timer = 0.0
        self.dragon_x = 8.0
        self.dragon_y = 6.0
        self.dragon_z = 6.0
        self.dragon_hp = 8
        self.dragon_angle = 0.0
        for e in self.entities:
            e["active"] = False

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt
        self.horizon_scroll += 12.0 * dt

        if self.state == STATE_HERO_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self.state = STATE_FLYING
                    self.state_timer = 0.0
                    self.hero_x = 8.0
                    self.hero_y = 11.0
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.5:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        self._update_hero(dt, buttons, prev_buttons)
        self._update_shots(dt)

        if self.state == STATE_BOSS_DRAGON:
            self._update_dragon_boss(dt)
        else:
            self._update_entities(dt)
            if self.enemies_defeated >= 6:
                self.spawn_dragon_boss()

        self._check_collisions()

    def _update_hero(self, dt: float, buttons: int, prev_buttons: int) -> None:
        spd = 14.0 if (self.roll_timer > 0.0) else 9.0
        if buttons & KEY_LEFT:
            self.hero_x = max(2.0, self.hero_x - spd * dt)
        if buttons & KEY_RIGHT:
            self.hero_x = min(13.0, self.hero_x + spd * dt)
        if buttons & KEY_UP:
            self.hero_y = max(4.0, self.hero_y - spd * dt)
        if buttons & KEY_DOWN:
            self.hero_y = min(13.0, self.hero_y + spd * dt)

        # Button B: Dodge Roll
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.roll_timer = 0.35
        if self.roll_timer > 0.0:
            self.roll_timer -= dt

        # Button A: Plasma Cannon
        self.shot_cooldown -= dt
        if (buttons & KEY_A) and self.shot_cooldown <= 0.0:
            self.shot_cooldown = 0.2
            for s in self.shots:
                if not s["active"]:
                    s["active"] = True
                    s["x"] = self.hero_x
                    s["y"] = self.hero_y - 0.5
                    s["z"] = 0.5
                    break

    def _update_shots(self, dt: float) -> None:
        for s in self.shots:
            if not s["active"]:
                continue
            s["z"] += 16.0 * dt
            if s["z"] > 10.0:
                s["active"] = False

    def _update_entities(self, dt: float) -> None:
        approach_spd = 5.0
        for i, e in enumerate(self.entities):
            if not e["active"]:
                e["active"] = True
                e["x"] = 3.0 + float((i * 4 + self.enemies_defeated) % 10)
                e["y"] = 4.0 + float((i * 2) % 6)
                e["z"] = 10.0
                e["type"] = 0 if (i % 2 == 0) else 1
                e["hp"] = 1
                continue

            e["z"] -= approach_spd * dt
            if e["z"] <= 0.0:
                e["active"] = False
                self.score += 50

    def _update_dragon_boss(self, dt: float) -> None:
        self.dragon_angle += 2.5 * dt
        self.dragon_x = 8.0 + math.cos(self.dragon_angle) * 3.5
        self.dragon_y = 6.0 + math.sin(self.dragon_angle * 1.5) * 2.0
        self.dragon_z = 5.5 + math.sin(self.dragon_angle) * 1.5

    def _check_collisions(self) -> None:
        for s in self.shots:
            if not s["active"]:
                continue

            if self.state == STATE_BOSS_DRAGON:
                dx = abs(s["x"] - self.dragon_x)
                dy = abs(s["y"] - self.dragon_y)
                dz = abs(s["z"] - self.dragon_z)
                if dx < 1.6 and dy < 1.6 and dz < 1.6:
                    s["active"] = False
                    self.dragon_hp -= 1
                    self.score += 300
                    if self.dragon_hp <= 0:
                        self.state = STATE_STAGE_CLEAR
                        self.state_timer = 0.0
                        self.score += 5000
            else:
                for e in self.entities:
                    if not e["active"] or e["type"] == 1:
                        continue
                    dx = abs(s["x"] - e["x"])
                    dy = abs(s["y"] - e["y"])
                    dz = abs(s["z"] - e["z"])
                    if dx < 1.4 and dy < 1.4 and dz < 1.6:
                        s["active"] = False
                        e["active"] = False
                        self.score += 150
                        self.enemies_defeated += 1
                        break

        if self.state == STATE_FLYING and self.roll_timer <= 0.0:
            for e in self.entities:
                if not e["active"]:
                    continue
                if 0.0 <= e["z"] <= 1.2:
                    if abs(self.hero_x - e["x"]) < 1.2 and abs(self.hero_y - e["y"]) < 1.2:
                        self.state = STATE_HERO_HIT
                        self.state_timer = 0.0
                        return

        if self.state == STATE_BOSS_DRAGON and self.roll_timer <= 0.0:
            if self.dragon_z <= 2.0:
                if (
                    abs(self.hero_x - self.dragon_x) < 1.4
                    and abs(self.hero_y - self.dragon_y) < 1.4
                ):
                    self.state = STATE_HERO_HIT
                    self.state_timer = 0.0

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

        for y in range(8):
            for x in range(16):
                sr = 40 + y * 15
                sg = 10 + y * 8
                sb = 120 + y * 12
                set_pixel(x, y, sr, sg, sb)

        scroll_row = int(self.horizon_scroll) % 4
        for y in range(8, 16):
            for x in range(16):
                check_pat = ((x // 2) + (y - 8 + scroll_row)) % 2
                if check_pat == 0:
                    set_pixel(x, y, 40, 180, 50)
                else:
                    set_pixel(x, y, 220, 200, 30)

        for e in self.entities:
            if not e["active"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["z"] > 6.0:
                if e["type"] == 1:
                    set_pixel(ex, ey, 180, 80, 40)
                else:
                    set_pixel(ex, ey, 255, 60, 60)
            else:
                if e["type"] == 1:
                    set_pixel(ex, ey, 60, 160, 40)
                    set_pixel(ex - 1, ey, 40, 120, 30)
                    set_pixel(ex + 1, ey, 40, 120, 30)
                    set_pixel(ex, ey - 1, 80, 200, 50)
                    set_pixel(ex, ey + 1, 140, 80, 30)
                else:
                    set_pixel(ex, ey, 255, 40, 40)
                    set_pixel(ex - 1, ey, 200, 30, 80)
                    set_pixel(ex + 1, ey, 200, 30, 80)
                    set_pixel(ex, ey - 1, 255, 255, 255)

        if self.state == STATE_BOSS_DRAGON:
            dx = int(round(self.dragon_x))
            dy = int(round(self.dragon_y))
            set_pixel(dx, dy, 255, 200, 0)
            set_pixel(dx - 1, dy, 255, 60, 20)
            set_pixel(dx + 1, dy, 255, 255, 255)
            set_pixel(dx, dy + 1, 240, 140, 0)
            set_pixel(dx - 1, dy + 1, 220, 100, 0)
            set_pixel(dx - 2, dy + 1, 200, 60, 0)

        for s in self.shots:
            if not s["active"]:
                continue
            set_pixel(int(round(s["x"])), int(round(s["y"])), 0, 240, 255)

        hx = int(round(self.hero_x))
        hy = int(round(self.hero_y))

        if self.state == STATE_HERO_HIT:
            set_pixel(hx, hy, 255, 60, 30)
            set_pixel(hx - 1, hy, 255, 180, 0)
            set_pixel(hx + 1, hy, 255, 180, 0)
        else:
            if self.roll_timer > 0.0:
                set_pixel(hx, hy, 255, 220, 0)
                set_pixel(hx - 1, hy, 40, 120, 255)
                set_pixel(hx + 1, hy, 40, 120, 255)
            else:
                set_pixel(hx, hy, 240, 240, 250)
                set_pixel(hx, hy - 1, 255, 200, 140)
                set_pixel(hx, hy + 1, 40, 60, 180)
                set_pixel(hx + 1, hy, 160, 160, 180)
                set_pixel(hx - 1, hy, 220, 40, 30)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 255, 200, 0)

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
            "hero_x": self.hero_x,
            "hero_y": self.hero_y,
            "enemies_defeated": self.enemies_defeated,
            "dragon_hp": self.dragon_hp,
        }
