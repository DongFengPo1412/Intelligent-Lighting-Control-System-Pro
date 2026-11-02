"""
Game #089: 经典雪人兄弟2 / 四大精灵 (Snow Bros. 2: With New Elves 1994 / Toaplan)
Four elemental spirits (Snow/Water/Lightning/Wind), enemy inflation balloons & ricochet kick combos.
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

STATE_PLAYING = 0
STATE_HERO_HIT = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3

ELEM_SNOW = 0       # Nick
ELEM_WATER = 1      # Roy
ELEM_LIGHTNING = 2  # Ching
ELEM_WIND = 3       # Shin-Shin

MAX_PROJECTILES = 4
MAX_MONSTERS = 4


class Game089SnowBros2(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.monsters_defeated = 0

        # Hero Elf
        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = True
        self.current_element = ELEM_SNOW

        self.projectiles: List[Dict[str, Any]] = []
        self.monsters: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 89

    @property
    def name(self) -> str:
        return "雪人兄弟2"

    @property
    def english_name(self) -> str:
        return "Snow Bros. 2"

    @property
    def release_year(self) -> int:
        return 1994

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "四属性精灵吹气充气球与多属性踢飞弹射"

    def get_name(self) -> str:
        return "Snow Bros. 2 (1994)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.current_element = ELEM_SNOW
        self._reset_level(hard_reset=True)

    def _reset_level(self, hard_reset: bool = False) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.monsters_defeated = 0

        self.px = 2.0
        self.py = 13.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = True

        self.projectiles = [
            {"x": 0.0, "y": 0.0, "vx": 0.0, "elem": ELEM_SNOW, "active": False}
            for _ in range(MAX_PROJECTILES)
        ]

        self.monsters = []
        init_positions = [(12.0, 13.0, -1.5), (4.0, 9.0, 1.2), (11.0, 9.0, -1.2), (8.0, 5.0, 1.0)]
        for i in range(MAX_MONSTERS):
            pos = init_positions[i]
            self.monsters.append({
                "x": pos[0],
                "y": pos[1],
                "vx": pos[2],
                "inflate_level": 0,
                "sphere_elem": ELEM_SNOW,
                "is_kicked": False,
                "kick_vx": 0.0,
                "kick_vy": 0.0,
                "active": True,
                "respawn_timer": 0.0,
            })

    def update(self, dt: float, buttons: int = 0, prev_buttons: int = 0) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_HERO_HIT:
            if self.state_timer > 1.8:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                    self.state_timer = 0.0
                else:
                    self._reset_level(hard_reset=False)
            return

        if self.state == STATE_STAGE_CLEAR:
            if self.state_timer > 2.0:
                self.stage += 1
                self._reset_level(hard_reset=False)
            return

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        # STATE_PLAYING
        self._update_player(dt, buttons, prev_buttons)
        self._update_projectiles(dt)
        self._update_monsters(dt)
        self._check_combat()

        if self.monsters_defeated >= 6:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        # Cycle element: Down + Button B
        if (buttons & KEY_DOWN) and (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.current_element = (self.current_element + 1) % 4
            return

        speed = 6.0
        if buttons & KEY_LEFT:
            self.px -= speed * dt
            self.facing = -1
        if buttons & KEY_RIGHT:
            self.px += speed * dt
            self.facing = 1

        # Jump
        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            if self.on_ground:
                self.vy = -6.2
                self.on_ground = False

        if not self.on_ground:
            self.vy += 15.0 * dt
            self.py += self.vy * dt

        # Platforms collision
        if self.py >= 13.0:
            self.py = 13.0
            self.vy = 0.0
            self.on_ground = True
        else:
            self.on_ground = False
            if self.vy >= 0.0:
                if 8.8 <= self.py <= 9.3:
                    if (1.5 <= self.px <= 7.0) or (8.5 <= self.px <= 14.0):
                        self.py = 9.0
                        self.vy = 0.0
                        self.on_ground = True
                elif 4.8 <= self.py <= 5.3:
                    if 3.5 <= self.px <= 12.0:
                        self.py = 5.0
                        self.vy = 0.0
                        self.on_ground = True

        self.px = max(0.5, min(15.0, self.px))

        # Shoot Elemental Shot (Button A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            for p in self.projectiles:
                if not p["active"]:
                    p["active"] = True
                    p["x"] = self.px + self.facing * 0.8
                    p["y"] = self.py - 0.5
                    p["vx"] = self.facing * 9.5
                    p["elem"] = self.current_element
                    break

        # Kick Ball (Button B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B) and not (buttons & KEY_DOWN):
            for m in self.monsters:
                if m["active"] and m["inflate_level"] >= 3 and not m["is_kicked"]:
                    dx = abs(self.px - m["x"])
                    dy = abs(self.py - m["y"])
                    if dx < 1.6 and dy < 1.4:
                        m["is_kicked"] = True
                        m["kick_vx"] = float(self.facing) * 10.0
                        m["kick_vy"] = -4.0 if m["sphere_elem"] == ELEM_WIND else 0.0
                        self.score += 50
                        break

    def _update_projectiles(self, dt: float) -> None:
        for p in self.projectiles:
            if not p["active"]:
                continue
            p["x"] += p["vx"] * dt
            if p["x"] < -1.0 or p["x"] > 17.0:
                p["active"] = False

    def _update_monsters(self, dt: float) -> None:
        for idx, m in enumerate(self.monsters):
            if not m["active"]:
                if m["respawn_timer"] > 0.0:
                    m["respawn_timer"] -= dt
                else:
                    m["active"] = True
                    m["inflate_level"] = 0
                    m["is_kicked"] = False
                    m["x"] = 2.0 + (idx * 3.3) % 11.0
                    m["y"] = 9.0 if idx % 2 == 0 else 13.0
                    m["vx"] = 1.5 if idx % 2 == 0 else -1.5
                continue

            if m["is_kicked"]:
                m["x"] += m["kick_vx"] * dt
                m["y"] += m["kick_vy"] * dt

                if m["x"] <= 0.8:
                    m["x"] = 0.8
                    m["kick_vx"] = -m["kick_vx"]
                elif m["x"] >= 14.8:
                    m["x"] = 14.8
                    m["kick_vx"] = -m["kick_vx"]

                if m["sphere_elem"] == ELEM_WIND:
                    m["kick_vy"] += 9.8 * dt
                    if m["y"] >= 13.0:
                        m["y"] = 13.0
                        m["kick_vy"] = -4.0
                else:
                    if m["y"] < 13.0:
                        m["y"] += 6.0 * dt
                    if m["y"] >= 13.0:
                        m["y"] = 13.0

                m["respawn_timer"] += dt
                if m["respawn_timer"] >= 2.5:
                    m["active"] = False
                    m["is_kicked"] = False
                    m["respawn_timer"] = 2.0
                    self.score += 300
                    self.monsters_defeated += 1
                continue

            if 0 < m["inflate_level"] < 3:
                m["respawn_timer"] += dt
                if m["respawn_timer"] >= 3.0:
                    m["inflate_level"] -= 1
                    m["respawn_timer"] = 0.0
                continue

            if m["inflate_level"] >= 3:
                continue

            # Patrolling
            m["x"] += m["vx"] * dt
            if m["x"] <= 1.0:
                m["x"] = 1.0
                m["vx"] = abs(m["vx"])
            elif m["x"] >= 14.5:
                m["x"] = 14.5
                m["vx"] = -abs(m["vx"])

    def _check_combat(self) -> None:
        # Projectiles vs Monsters
        for p in self.projectiles:
            if not p["active"]:
                continue
            for m_idx, m in enumerate(self.monsters):
                if not m["active"] or m["is_kicked"]:
                    continue

                dx = abs(p["x"] - m["x"])
                dy = abs(p["y"] - m["y"])
                if dx < 1.2 and dy < 1.2:
                    p["active"] = False
                    m["inflate_level"] = min(3, m["inflate_level"] + 1)
                    m["sphere_elem"] = p["elem"]
                    m["respawn_timer"] = 0.0
                    self.score += 20

                    if p["elem"] == ELEM_LIGHTNING and m["inflate_level"] >= 2:
                        for o_idx, o in enumerate(self.monsters):
                            if o_idx != m_idx and o["active"] and not o["is_kicked"]:
                                if abs(m["x"] - o["x"]) < 3.0 and abs(m["y"] - o["y"]) < 1.5:
                                    o["inflate_level"] = min(3, o["inflate_level"] + 1)
                                    o["sphere_elem"] = ELEM_LIGHTNING
                                    self.score += 10
                    break

        # Kicked Ball vs other monsters
        for k_idx, km in enumerate(self.monsters):
            if not km["active"] or not km["is_kicked"]:
                continue
            for o_idx, om in enumerate(self.monsters):
                if o_idx == k_idx or not om["active"]:
                    continue
                dx = abs(km["x"] - om["x"])
                dy = abs(km["y"] - om["y"])
                if dx < 1.3 and dy < 1.3:
                    om["active"] = False
                    om["respawn_timer"] = 2.5
                    self.score += 200
                    self.monsters_defeated += 1

        # Monsters vs Hero
        for m in self.monsters:
            if not m["active"] or m["inflate_level"] >= 3 or m["is_kicked"]:
                continue
            dx = abs(self.px - m["x"])
            dy = abs(self.py - m["y"])
            if dx < 1.0 and dy < 1.0:
                self.state = STATE_HERO_HIT
                self.state_timer = 0.0
                break

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

        # Platforms
        for x in range(16):
            set_pixel(x, 14, 50, 120, 180)
            set_pixel(x, 15, 30, 70, 120)

        for x in range(2, 7):
            set_pixel(x, 10, 80, 140, 200)
        for x in range(9, 14):
            set_pixel(x, 10, 80, 140, 200)

        for x in range(4, 12):
            set_pixel(x, 6, 100, 160, 220)

        # Projectiles
        for p in self.projectiles:
            if not p["active"]:
                continue
            px = int(round(p["x"]))
            py = int(round(p["y"]))
            if p["elem"] == ELEM_SNOW:
                set_pixel(px, py, 230, 240, 255)
            elif p["elem"] == ELEM_WATER:
                set_pixel(px, py, 40, 150, 255)
            elif p["elem"] == ELEM_LIGHTNING:
                set_pixel(px, py, 255, 240, 40)
            else:
                set_pixel(px, py, 50, 255, 120)

        # Monsters
        for m in self.monsters:
            if not m["active"]:
                continue
            mx = int(round(m["x"]))
            my = int(round(m["y"]))
            if m["is_kicked"] or m["inflate_level"] >= 3:
                cr, cg, cb = 240, 240, 255
                if m["sphere_elem"] == ELEM_WATER:
                    cr, cg, cb = 30, 120, 240
                elif m["sphere_elem"] == ELEM_LIGHTNING:
                    cr, cg, cb = 255, 220, 20
                elif m["sphere_elem"] == ELEM_WIND:
                    cr, cg, cb = 40, 240, 100

                set_pixel(mx, my - 1, cr, cg, cb)
                set_pixel(mx + 1, my - 1, cr, cg, cb)
                set_pixel(mx, my, cr, cg, cb)
                set_pixel(mx + 1, my, cr, cg, cb)
            elif m["inflate_level"] > 0:
                set_pixel(mx, my, 220, 100, 140)
                set_pixel(mx, my - 1, 240, 180, 180)
            else:
                set_pixel(mx, my, 220, 40, 40)
                set_pixel(mx, my - 1, 255, 100, 60)

        # Hero
        hx = int(round(self.px))
        hy = int(round(self.py))

        if self.state == STATE_HERO_HIT:
            set_pixel(hx, hy, 255, 50, 50)
            set_pixel(hx, hy - 1, 255, 255, 0)
        else:
            r, g, b = 240, 240, 255
            if self.current_element == ELEM_WATER:
                r, g, b = 40, 180, 255
            elif self.current_element == ELEM_LIGHTNING:
                r, g, b = 255, 220, 40
            elif self.current_element == ELEM_WIND:
                r, g, b = 50, 230, 100

            set_pixel(hx, hy, r, g, b)
            set_pixel(hx, hy - 1, 250, 200, 160)
            set_pixel(hx + self.facing, hy - 1, r, g, b)

        # HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 0, 255, 100, 150)

        er, eg, eb = 255, 255, 255
        if self.current_element == ELEM_WATER:
            er, eg, eb = 0, 150, 255
        elif self.current_element == ELEM_LIGHTNING:
            er, eg, eb = 255, 240, 0
        elif self.current_element == ELEM_WIND:
            er, eg, eb = 0, 255, 100
        set_pixel(15, 0, er, eg, eb)

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
            "element": self.current_element,
            "monsters_defeated": self.monsters_defeated,
            "player_x": self.px,
            "player_y": self.py,
        }
