"""
Game #112: 防卫者 (Defender 1981 / Williams Electronics)
Wrap-around horizontal radar scanner, multi-directional jet thrust,
laser cannon fire, alien lander abduction interception, mid-air humanoid catch & rescue,
and screen-clearing smart bomb detonators.
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
STATE_PLAYER_DYING = 1
STATE_WAVE_CLEAR = 2
STATE_GAME_OVER = 3

WORLD_WIDTH = 48.0
MAX_HUMANS = 4
MAX_ALIENS = 6
MAX_LASERS = 4


def wrap_x(x: float, width: float = WORLD_WIDTH) -> float:
    while x < 0.0:
        x += width
    while x >= width:
        x -= width
    return x


def wrap_dist_x(x1: float, x2: float, width: float = WORLD_WIDTH) -> float:
    dx = x1 - x2
    while dx > width * 0.5:
        dx -= width
    while dx < -width * 0.5:
        dx += width
    return dx


class Game112Defender(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.smart_bombs = 2
        self.wave = 1

        self.px = 8.0
        self.py = 7.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing_dir = 1
        self.carried_human_idx = -1

        self.humans: List[Dict[str, Any]] = []
        self.aliens: List[Dict[str, Any]] = []
        self.lasers: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 112

    @property
    def name(self) -> str:
        return "防卫者"

    @property
    def english_name(self) -> str:
        return "Defender"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "全景雷达雷达扫瞄、水平循环折返飞行、外星抓取绑架拦截与空中接力营救"

    def get_name(self) -> str:
        return "Defender (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.smart_bombs = 2
        self.wave = 1
        self._init_wave()

    def _init_wave(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 8.0
        self.py = 7.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing_dir = 1
        self.carried_human_idx = -1

        # Humanoids on surface
        self.humans = []
        for i in range(MAX_HUMANS):
            self.humans.append({
                "x": 6.0 + float(i) * 11.0,
                "y": 14.0,
                "alive": True,
                "being_abducted": False,
                "is_falling": False,
                "being_carried": False,
            })

        # Alien landers
        count = min(MAX_ALIENS, 3 + self.wave)
        self.aliens = []
        for i in range(MAX_ALIENS):
            if i < count:
                self.aliens.append({
                    "x": wrap_x(self.px + 12.0 + float(i) * 6.5),
                    "y": 2.0 + float(i % 3) * 1.5,
                    "vx": 2.5 if (i % 2 == 0) else -2.5,
                    "vy": 0.0,
                    "active": True,
                    "is_mutant": False,
                    "abducted_human_idx": -1,
                })
            else:
                self.aliens.append({
                    "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0,
                    "active": False, "is_mutant": False, "abducted_human_idx": -1,
                })

        self.lasers = []
        for _ in range(MAX_LASERS):
            self.lasers.append({"x": 0.0, "y": 0.0, "vx": 0.0, "active": False})

    def trigger_smart_bomb(self) -> None:
        if self.smart_bombs <= 0 or self.state != STATE_PLAYING:
            return
        self.smart_bombs -= 1

        for a in self.aliens:
            if a["active"]:
                dx = abs(wrap_dist_x(a["x"], self.px))
                if dx <= 8.5:  # On-screen blast radius
                    a["active"] = False
                    self.score += 150
                    h_idx = a["abducted_human_idx"]
                    if 0 <= h_idx < MAX_HUMANS and self.humans[h_idx]["alive"]:
                        self.humans[h_idx]["being_abducted"] = False
                        self.humans[h_idx]["is_falling"] = True

    def fire_laser(self) -> None:
        for l in self.lasers:
            if not l["active"]:
                l["x"] = self.px + float(self.facing_dir) * 1.0
                l["y"] = self.py
                l["vx"] = float(self.facing_dir) * 26.0
                l["active"] = True
                break

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05

        self.state_timer += dt

        if self.state == STATE_GAME_OVER:
            if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
                self.reset()
            return

        if self.state == STATE_PLAYER_DYING:
            if self.state_timer > 1.2:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAME_OVER
                else:
                    self.state = STATE_PLAYING
                    self.px = 8.0
                    self.py = 7.0
                    self.vx = 0.0
                    self.vy = 0.0
                    self.carried_human_idx = -1
            return

        if self.state == STATE_WAVE_CLEAR:
            if self.state_timer > 1.5:
                self.wave += 1
                if self.smart_bombs < 3:
                    self.smart_bombs += 1
                self._init_wave()
            return

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_laser()
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.trigger_smart_bomb()

        self._update_player(dt, buttons)
        self._update_aliens(dt)
        self._update_lasers(dt)
        self._update_humans(dt)
        self._check_collisions()
        self._check_wave_clear()

    def _update_player(self, dt: float, buttons: int) -> None:
        accel = 20.0
        drag = 0.90

        if buttons & KEY_LEFT:
            self.vx -= accel * dt
            self.facing_dir = -1
        if buttons & KEY_RIGHT:
            self.vx += accel * dt
            self.facing_dir = 1
        if buttons & KEY_UP:
            self.vy -= accel * dt
        if buttons & KEY_DOWN:
            self.vy += accel * dt

        self.vx *= drag
        self.vy *= drag

        self.px = wrap_x(self.px + self.vx * dt)
        self.py += self.vy * dt

        if self.py < 1.0:
            self.py = 1.0
            self.vy = 0.0
        if self.py > 14.0:
            self.py = 14.0
            self.vy = 0.0

        if self.carried_human_idx >= 0:
            h = self.carried_human_idx
            if self.py >= 13.5:
                self.humans[h]["being_carried"] = False
                self.humans[h]["y"] = 14.0
                self.humans[h]["is_falling"] = False
                self.carried_human_idx = -1
                self.score += 500  # Safe landing bonus
            else:
                self.humans[h]["x"] = self.px
                self.humans[h]["y"] = self.py + 1.0

    def _update_aliens(self, dt: float) -> None:
        for i, a in enumerate(self.aliens):
            if not a["active"]:
                continue

            if a["is_mutant"]:
                dx = wrap_dist_x(self.px, a["x"])
                dy = self.py - a["y"]
                a["vx"] = 6.5 if (dx > 0) else -6.5
                a["vy"] = 4.5 if (dy > 0) else -4.5
                a["x"] = wrap_x(a["x"] + a["vx"] * dt)
                a["y"] += a["vy"] * dt
                a["y"] = max(1.0, min(14.0, a["y"]))
            elif a["abducted_human_idx"] >= 0:
                h = a["abducted_human_idx"]
                a["vy"] = -2.8
                a["y"] += a["vy"] * dt
                a["x"] = wrap_x(a["x"] + a["vx"] * dt * 0.2)

                if 0 <= h < MAX_HUMANS and self.humans[h]["alive"]:
                    self.humans[h]["x"] = a["x"]
                    self.humans[h]["y"] = a["y"] + 0.8

                if a["y"] <= 1.2:
                    if 0 <= h < MAX_HUMANS:
                        self.humans[h]["alive"] = False
                        self.humans[h]["being_abducted"] = False
                    a["abducted_human_idx"] = -1
                    a["is_mutant"] = True
            else:
                a["x"] = wrap_x(a["x"] + a["vx"] * dt)

                target_h = -1
                min_dist = 999.0
                for h_idx, h_data in enumerate(self.humans):
                    if h_data["alive"] and not h_data["being_abducted"] and not h_data["being_carried"]:
                        dist = abs(wrap_dist_x(a["x"], h_data["x"]))
                        if dist < min_dist:
                            min_dist = dist
                            target_h = h_idx

                if target_h >= 0 and min_dist < 4.0:
                    a["vy"] = 2.0
                    a["y"] += a["vy"] * dt
                    if a["y"] >= 13.5:
                        a["abducted_human_idx"] = target_h
                        self.humans[target_h]["being_abducted"] = True
                else:
                    a["y"] += math.sin(self.state_timer * 2.0 + i) * 1.5 * dt
                    a["y"] = max(2.0, min(10.0, a["y"]))

    def _update_lasers(self, dt: float) -> None:
        for l in self.lasers:
            if not l["active"]:
                continue
            l["x"] = wrap_x(l["x"] + l["vx"] * dt)
            dist = abs(wrap_dist_x(l["x"], self.px))
            if dist > 9.0:
                l["active"] = False

    def _update_humans(self, dt: float) -> None:
        for i, h in enumerate(self.humans):
            if not h["alive"]:
                continue

            if h["is_falling"]:
                h["y"] += 4.5 * dt
                dist_p = abs(wrap_dist_x(h["x"], self.px))
                if dist_p < 1.1 and abs(h["y"] - self.py) < 1.1 and self.carried_human_idx == -1:
                    h["is_falling"] = False
                    h["being_carried"] = True
                    self.carried_human_idx = i
                    self.score += 500  # Catch bonus!
                elif h["y"] >= 14.0:
                    h["alive"] = False
                    h["is_falling"] = False

    def _check_collisions(self) -> None:
        # Laser vs Alien
        for l in self.lasers:
            if not l["active"]:
                continue
            for a in self.aliens:
                if not a["active"]:
                    continue

                dx = abs(wrap_dist_x(l["x"], a["x"]))
                dy = abs(l["y"] - a["y"])
                if dx < 0.9 and dy < 0.9:
                    l["active"] = False
                    a["active"] = False
                    self.score += (200 if a["is_mutant"] else 150)

                    h = a["abducted_human_idx"]
                    if 0 <= h < MAX_HUMANS and self.humans[h]["alive"]:
                        self.humans[h]["being_abducted"] = False
                        self.humans[h]["is_falling"] = True
                    break

        # Alien vs Player
        for a in self.aliens:
            if not a["active"]:
                continue
            dx = abs(wrap_dist_x(self.px, a["x"]))
            dy = abs(self.py - a["y"])
            if dx < 0.8 and dy < 0.8:
                self.state = STATE_PLAYER_DYING
                self.state_timer = 0.0
                if self.carried_human_idx >= 0:
                    self.humans[self.carried_human_idx]["being_carried"] = False
                    self.humans[self.carried_human_idx]["is_falling"] = True
                    self.carried_human_idx = -1
                break

    def _check_wave_clear(self) -> None:
        if not any(a["active"] for a in self.aliens):
            self.state = STATE_WAVE_CLEAR
            self.state_timer = 0.0
            self.score += 1000

    def render(self, fb: bytearray) -> bytearray:
        if not fb or len(fb) < 16 * 16 * 3:
            return fb

        def set_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
            if 0 <= x < 16 and 0 <= y < 16:
                idx = (y * 16 + x) * 3
                fb[idx] = r
                fb[idx + 1] = g
                fb[idx + 2] = b

        # 1. Radar minimap on top row
        for rx in range(16):
            set_pixel(rx, 0, 10, 20, 40)
        for h in self.humans:
            if h["alive"]:
                rx = int(h["x"] / WORLD_WIDTH * 16.0)
                set_pixel(rx, 0, 0, 255, 100)
        for a in self.aliens:
            if a["active"]:
                rx = int(a["x"] / WORLD_WIDTH * 16.0)
                if a["is_mutant"]:
                    set_pixel(rx, 0, 255, 30, 0)
                else:
                    set_pixel(rx, 0, 220, 180, 0)
        r_px = int(self.px / WORLD_WIDTH * 16.0)
        set_pixel(r_px, 0, 255, 255, 255)

        # 2. Martian surface terrain
        for sx in range(16):
            world_x = wrap_x(self.px - 7.5 + float(sx))
            h_var = int(math.sin(world_x * 0.4) * 1.2)
            set_pixel(sx, 15, 180, 50, 20)
            if h_var > 0:
                set_pixel(sx, 14, 140, 40, 15)

        # 3. Humans
        for h in self.humans:
            if not h["alive"]:
                continue
            sx = wrap_dist_x(h["x"], self.px) + 7.5
            isx = int(round(sx))
            isy = int(round(h["y"]))
            if 0 <= isx < 16 and 1 <= isy < 16:
                set_pixel(isx, isy, 0, 220, 255)
                set_pixel(isx, isy - 1, 255, 200, 160)

        # 4. Aliens
        for a in self.aliens:
            if not a["active"]:
                continue
            sx = wrap_dist_x(a["x"], self.px) + 7.5
            isx = int(round(sx))
            isy = int(round(a["y"]))
            if 0 <= isx < 16 and 1 <= isy < 15:
                if a["is_mutant"]:
                    set_pixel(isx, isy, 255, 40, 200)
                    set_pixel(isx - 1, isy, 255, 120, 0)
                    set_pixel(isx + 1, isy, 255, 120, 0)
                else:
                    set_pixel(isx, isy, 100, 255, 40)
                    set_pixel(isx, isy - 1, 220, 255, 120)
                    set_pixel(isx - 1, isy, 50, 180, 30)
                    set_pixel(isx + 1, isy, 50, 180, 30)

        # 5. Lasers
        for l in self.lasers:
            if not l["active"]:
                continue
            sx = wrap_dist_x(l["x"], self.px) + 7.5
            isx = int(round(sx))
            isy = int(round(l["y"]))
            if 0 <= isx < 16 and 1 <= isy < 15:
                set_pixel(isx, isy, 255, 240, 50)
                set_pixel(isx - 1, isy, 255, 100, 0)

        # 6. Ship
        if self.state == STATE_PLAYING:
            sx = 8
            sy = int(round(self.py))
            set_pixel(sx, sy, 255, 255, 255)
            set_pixel(sx - self.facing_dir, sy, 40, 120, 255)
            set_pixel(sx - self.facing_dir * 2, sy, 255, 100, 20)
            set_pixel(sx, sy - 1, 80, 160, 255)
        elif self.state == STATE_PLAYER_DYING:
            sx = 8
            sy = int(round(self.py))
            set_pixel(sx, sy, 255, 200, 50)
            set_pixel(sx - 1, sy - 1, 255, 40, 20)
            set_pixel(sx + 1, sy + 1, 255, 80, 0)
            set_pixel(sx + 1, sy - 1, 255, 255, 0)

        # 7. Lives & Bombs HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l, 1, 0, 255, 255)
        for b in range(min(self.smart_bombs, 3)):
            set_pixel(15 - b, 1, 255, 220, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "smart_bombs": self.smart_bombs,
            "wave": self.wave,
            "px": self.px,
            "py": self.py,
            "vx": self.vx,
            "vy": self.vy,
            "facing_dir": self.facing_dir,
            "carried_human_idx": self.carried_human_idx,
        }
