"""
Game #115: 暴风雨 (Tempest 1981 / Atari)
3D polygonal perspective tube shooter, geometric rim crawling claw,
depth particle projectile blasting, perimeter flipper combat,
and the screen-vaporizing SuperZapper electric pulse.
"""

from typing import List, Dict, Any, Tuple
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
STATE_TUBE_WARP = 2
STATE_GAME_OVER = 3

NUM_SECTORS = 16
MAX_ENEMIES = 6
MAX_SHOTS = 4
PI = math.pi


def get_sector_pos(sector: int, depth: float) -> Tuple[float, float]:
    angle = float(sector) * (2.0 * PI / 16.0) - (PI * 0.5)
    r = 1.0 + depth * 6.2
    x = 7.5 + math.cos(angle) * r
    y = 7.5 + math.sin(angle) * r
    return x, y


class Game115Tempest(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.super_zappers = 1
        self.wave = 1

        self.player_sector = 0
        self.move_timer = 0.0
        self.spawn_timer = 0.5
        self.enemies_remaining = 0

        self.enemies: List[Dict[str, Any]] = []
        self.shots: List[Dict[str, Any]] = []

        self.reset()

    @property
    def game_id(self) -> int:
        return 115

    @property
    def name(self) -> str:
        return "暴风雨"

    @property
    def english_name(self) -> str:
        return "Tempest"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "3D透视几何管道外环爬行、深渊粒子射击、边缘翻转防御与超级电击清屏"

    def get_name(self) -> str:
        return "Tempest (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.wave = 1
        self._init_wave()

    def _init_wave(self) -> None:
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.super_zappers = 1
        self.player_sector = 0
        self.move_timer = 0.0
        self.spawn_timer = 0.5
        self.enemies_remaining = 6 + self.wave * 2

        self.enemies = []
        for _ in range(MAX_ENEMIES):
            self.enemies.append({
                "sector": 0, "depth": 0.0, "speed": 0.0, "on_rim": False, "active": False
            })

        self.shots = []
        for _ in range(MAX_SHOTS):
            self.shots.append({
                "sector": 0, "depth": 1.0, "speed": 0.0, "active": False
            })

    def trigger_super_zapper(self) -> None:
        if self.super_zappers <= 0 or self.state != STATE_PLAYING:
            return
        self.super_zappers -= 1

        for e in self.enemies:
            if e["active"]:
                e["active"] = False
                self.score += 150

    def fire_shot(self) -> None:
        for s in self.shots:
            if not s["active"]:
                s["sector"] = self.player_sector
                s["depth"] = 0.95
                s["speed"] = 3.8
                s["active"] = True
                break

    def spawn_enemy(self) -> None:
        if self.enemies_remaining <= 0:
            return

        for i, e in enumerate(self.enemies):
            if not e["active"]:
                e["sector"] = (self.player_sector + 4 + (i * 3)) % NUM_SECTORS
                e["depth"] = 0.05
                e["speed"] = 0.35 + float(self.wave) * 0.08
                e["on_rim"] = False
                e["active"] = True
                self.enemies_remaining -= 1
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
                    self.player_sector = 0
            return

        if self.state == STATE_TUBE_WARP:
            if self.state_timer > 1.5:
                self.wave += 1
                self._init_wave()
            return

        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            self.fire_shot()
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            self.trigger_super_zapper()

        self._update_player(dt, buttons, prev_buttons)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn_enemy()
            self.spawn_timer = 1.2

        self._update_enemies(dt)
        self._update_shots(dt)
        self._check_collisions()
        self._check_wave_clear()

    def _update_player(self, dt: float, buttons: int, prev_buttons: int) -> None:
        self.move_timer += dt
        repeat_rate = 0.12

        left_press = (buttons & KEY_LEFT) and (not (prev_buttons & KEY_LEFT) or self.move_timer > repeat_rate)
        right_press = (buttons & KEY_RIGHT) and (not (prev_buttons & KEY_RIGHT) or self.move_timer > repeat_rate)

        if left_press:
            self.player_sector = (self.player_sector - 1 + NUM_SECTORS) % NUM_SECTORS
            self.move_timer = 0.0
        elif right_press:
            self.player_sector = (self.player_sector + 1) % NUM_SECTORS
            self.move_timer = 0.0

    def _update_enemies(self, dt: float) -> None:
        for e in self.enemies:
            if not e["active"]:
                continue

            if e["on_rim"]:
                target = self.player_sector
                diff = (target - e["sector"] + NUM_SECTORS) % NUM_SECTORS
                step_dir = 1 if (diff <= 8) else -1

                e["depth"] += dt
                if e["depth"] >= 0.35:
                    e["depth"] = 0.0
                    e["sector"] = (e["sector"] + step_dir + NUM_SECTORS) % NUM_SECTORS

                if e["sector"] == self.player_sector:
                    self.state = STATE_PLAYER_DYING
                    self.state_timer = 0.0
            else:
                e["depth"] += e["speed"] * dt
                if e["depth"] >= 1.0:
                    e["depth"] = 0.0
                    e["on_rim"] = True
                    if e["sector"] == self.player_sector:
                        self.state = STATE_PLAYER_DYING
                        self.state_timer = 0.0

    def _update_shots(self, dt: float) -> None:
        for s in self.shots:
            if not s["active"]:
                continue
            s["depth"] -= s["speed"] * dt
            if s["depth"] <= 0.0:
                s["active"] = False

    def _check_collisions(self) -> None:
        for s in self.shots:
            if not s["active"]:
                continue
            for e in self.enemies:
                if not e["active"]:
                    continue

                if e["sector"] == s["sector"]:
                    if e["on_rim"] or abs(e["depth"] - s["depth"]) < 0.25:
                        s["active"] = False
                        e["active"] = False
                        self.score += (200 if e["on_rim"] else 150)
                        break

    def _check_wave_clear(self) -> None:
        if self.enemies_remaining > 0:
            return
        if any(e["active"] for e in self.enemies):
            return

        self.state = STATE_TUBE_WARP
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

        # 1. Vector wireframe 3D spokes
        for s in range(NUM_SECTORS):
            x1, y1 = get_sector_pos(s, 0.0)
            x2, y2 = get_sector_pos(s, 1.0)
            set_pixel(int(round(x1)), int(round(y1)), 15, 30, 80)
            set_pixel(int(round(x2)), int(round(y2)), 0, 140, 255)

        # 2. Shots
        for s in self.shots:
            if not s["active"]:
                continue
            sx, sy = get_sector_pos(s["sector"], s["depth"])
            set_pixel(int(round(sx)), int(round(sy)), 255, 255, 255)

        # 3. Enemies
        for e in self.enemies:
            if not e["active"]:
                continue
            d = 1.0 if e["on_rim"] else e["depth"]
            ex, ey = get_sector_pos(e["sector"], d)
            if e["on_rim"]:
                set_pixel(int(round(ex)), int(round(ey)), 255, 40, 20)
            else:
                set_pixel(int(round(ex)), int(round(ey)), 255, 180, 0)

        # 4. Player Claw
        if self.state in (STATE_PLAYING, STATE_TUBE_WARP):
            px, py = get_sector_pos(self.player_sector, 1.0)
            set_pixel(int(round(px)), int(round(py)), 255, 240, 0)

            p1x, p1y = get_sector_pos((self.player_sector + 1) % NUM_SECTORS, 0.95)
            p2x, p2y = get_sector_pos((self.player_sector - 1 + NUM_SECTORS) % NUM_SECTORS, 0.95)
            set_pixel(int(round(p1x)), int(round(p1y)), 220, 180, 0)
            set_pixel(int(round(p2x)), int(round(p2y)), 220, 180, 0)
        elif self.state == STATE_PLAYER_DYING:
            px, py = get_sector_pos(self.player_sector, 1.0)
            ipx = int(round(px))
            ipy = int(round(py))
            set_pixel(ipx, ipy, 255, 255, 255)
            set_pixel((ipx + 1) % 16, ipy, 255, 60, 20)
            set_pixel((ipx + 15) % 16, ipy, 255, 60, 20)
            set_pixel(ipx, (ipy + 1) % 16, 255, 200, 0)

        # 5. SuperZapper charge
        if self.super_zappers > 0:
            set_pixel(15, 0, 255, 0, 255)

        # 6. Lives HUD
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 255, 240, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "super_zappers": self.super_zappers,
            "wave": self.wave,
            "player_sector": self.player_sector,
            "enemies_remaining": self.enemies_remaining,
        }
