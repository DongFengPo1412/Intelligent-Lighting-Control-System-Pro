# -*- coding: utf-8 -*-
"""
Game #149: 逆转大蜜蜂 (Gaplus 1984 / Namco)
街机历史上首款玩家逆转反捕敌机编队充当僚机护航的太空射击传奇：
玩家战机拥有纵深区域全向机动、按键B反向投射牵引光束抓捕俘获敌机收编为僚机、
按键A统领全队进行超宽多联装扇形齐射、僚机充当防空装甲护盾阻挡致命弹幕。
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
STATE_PLAYER_HIT = 2
STATE_GAME_OVER = 3


class Game149Gaplus(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 7.5
        self.py = 13.0

        # Tractor beam state
        self.beam_active = False
        self.beam_timer = 0.0
        self.beam_energy = 1.0  # 0.0 to 1.0

        # Captured escorts (docked alongside ship)
        self.escorts_count = 0  # 0 to 4
        self.max_escorts = 4

        # Lasers & Enemy bullets
        self.lasers: List[Dict[str, Any]] = []
        self.enemy_bullets: List[Dict[str, Any]] = []

        # Swarm enemies
        self.enemies: List[Dict[str, Any]] = []
        self.fleet_sway = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 149

    @property
    def name(self) -> str:
        return "逆转大蜜蜂"

    @property
    def english_name(self) -> str:
        return "Gaplus"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "逆转牵引光束抓捕敌机反向收编为护航僚机、多联装超大扇形僚机齐射弹幕、僚机充当装甲护盾与挑战关颠球杂技"

    def get_name(self) -> str:
        return "Gaplus (1984)"

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
        self.py = 13.0
        self.beam_active = False
        self.beam_timer = 0.0
        self.beam_energy = 1.0
        self.escorts_count = 0
        self.lasers.clear()
        self.enemy_bullets.clear()
        self.fleet_sway = 0.0

        # Spawn fleet formation (8 enemies: 2 rows of 4)
        self.enemies = []
        for r in range(2):
            for c in range(4):
                bx = 3.0 + c * 3.0
                by = 2.0 + r * 2.0
                self.enemies.append({
                    "base_x": bx,
                    "base_y": by,
                    "x": bx,
                    "y": by,
                    "state": "formation",  # "formation", "diving", "captured_suck"
                    "vx": 0.0,
                    "vy": 0.0,
                    "dive_t": 0.0,
                    "alive": True,
                })

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_PLAYER_HIT):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_PLAYER_HIT:
                    if self.lives > 0:
                        self.px = 7.5
                        self.py = 13.0
                        self.escorts_count = 0
                        self.beam_active = False
                        self.lasers.clear()
                        self.enemy_bullets.clear()
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
        # 1. 8-Way omni-movement within lower zone (y in [8.5, 14.5])
        move_speed = 6.0
        dx = 0.0
        dy = 0.0
        if buttons & KEY_LEFT:
            dx -= move_speed
        if buttons & KEY_RIGHT:
            dx += move_speed
        if buttons & KEY_UP:
            dy -= move_speed
        if buttons & KEY_DOWN:
            dy += move_speed

        self.px = max(1.5, min(14.5, self.px + dx * dt))
        self.py = max(8.5, min(14.5, self.py + dy * dt))

        # 2. Tractor Beam control: Hold Key B
        if buttons & KEY_B:
            if self.beam_energy > 0.05:
                self.beam_active = True
                self.beam_energy = max(0.0, self.beam_energy - dt * 0.4)
            else:
                self.beam_active = False
        else:
            self.beam_active = False
            self.beam_energy = min(1.0, self.beam_energy + dt * 0.3)

        # 3. Fire Lasers: Key A (Player main cannon + all escorts fire simultaneously!)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if len(self.lasers) < 10:
                # Main fighter laser
                self.lasers.append({"x": self.px, "y": self.py - 1.0, "vy": -14.0})
                # Escort wingmen lasers
                offsets = [-1.8, 1.8, -3.2, 3.2]
                for i in range(self.escorts_count):
                    ox = offsets[i]
                    self.lasers.append({"x": self.px + ox, "y": self.py - 0.5, "vy": -14.0})

        # 4. Update Player Lasers
        for l in self.lasers:
            l["y"] += l["vy"] * dt

        # Check laser hits on enemies
        for l in self.lasers:
            for e in self.enemies:
                if e["alive"] and e["state"] != "captured_suck":
                    if abs(l["x"] - e["x"]) < 0.9 and abs(l["y"] - e["y"]) < 0.9:
                        e["alive"] = False
                        l["y"] = -10.0  # Destroy laser
                        self.score += 150
                        break

        self.lasers = [l for l in self.lasers if l["y"] >= 0.0]

        # 5. Update Swarm & Diving Physics
        self.fleet_sway += dt * 2.0
        sway_offset = math.sin(self.fleet_sway) * 1.5

        # Check dive triggers
        diving_count = sum(1 for e in self.enemies if e["alive"] and e["state"] == "diving")
        if diving_count < 2:
            for e in self.enemies:
                if e["alive"] and e["state"] == "formation":
                    e["state"] = "diving"
                    e["dive_t"] = 0.0
                    break

        for e in self.enemies:
            if not e["alive"]:
                continue

            if e["state"] == "formation":
                e["x"] = e["base_x"] + sway_offset
                e["y"] = e["base_y"]
            elif e["state"] == "diving":
                e["dive_t"] += dt
                # Figure-8 / sinusoidal dive sweep towards player
                e["y"] += 4.5 * dt
                e["x"] += math.sin(e["dive_t"] * 4.0) * 5.0 * dt
                e["x"] = max(1.0, min(14.5, e["x"]))

                # Enemy fires bullet occasionally
                if 5.0 < e["y"] < 8.0 and len(self.enemy_bullets) < 4:
                    if int(e["dive_t"] * 10) % 7 == 0:
                        self.enemy_bullets.append({"x": e["x"], "y": e["y"] + 0.6, "vy": 7.0})

                # If dives off screen, return to top formation
                if e["y"] > 15.5:
                    e["y"] = 0.0
                    e["state"] = "formation"

                # Check if caught by Tractor Beam!
                if self.beam_active and self.escorts_count < self.max_escorts:
                    # Tractor beam cone: spreads upward from px
                    beam_half_w = 0.8 + (self.py - e["y"]) * 0.18
                    if abs(e["x"] - self.px) <= beam_half_w and e["y"] < self.py:
                        # Caught in beam!
                        e["state"] = "captured_suck"

            elif e["state"] == "captured_suck":
                # Pulled downward toward player docking bay
                e["x"] += (self.px - e["x"]) * min(1.0, dt * 8.0)
                e["y"] += 10.0 * dt
                if e["y"] >= self.py - 0.5:
                    # Successfully docked as an escort wingman!
                    e["alive"] = False
                    self.escorts_count = min(self.max_escorts, self.escorts_count + 1)
                    self.score += 500

        # 6. Update Enemy Bullets
        for b in self.enemy_bullets:
            b["y"] += b["vy"] * dt

            # Bullet collision with escorts first (escorts act as armor shield!)
            if self.escorts_count > 0:
                if abs(b["y"] - self.py) < 1.0 and abs(b["x"] - self.px) < 3.5:
                    self.escorts_count -= 1  # Lost an escort, player saved!
                    b["y"] = 20.0
                    continue

            # Bullet collision with main player
            if abs(b["x"] - self.px) < 0.8 and abs(b["y"] - self.py) < 0.8:
                self._lose_life()
                return

        self.enemy_bullets = [b for b in self.enemy_bullets if b["y"] <= 15.5]

        # 7. Enemy collision with Player / Escorts
        for e in self.enemies:
            if not e["alive"] or e["state"] == "captured_suck":
                continue

            # Escort shield absorbs collision
            if self.escorts_count > 0:
                if abs(e["y"] - self.py) < 1.0 and abs(e["x"] - self.px) < 3.0:
                    self.escorts_count -= 1
                    e["alive"] = False
                    self.score += 100
                    continue

            # Direct crash into player
            if abs(e["x"] - self.px) < 0.8 and abs(e["y"] - self.py) < 0.8:
                self._lose_life()
                return

        # 8. Wave Clear check
        alive_count = sum(1 for e in self.enemies if e["alive"])
        if alive_count == 0:
            self.score += 1500
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_PLAYER_HIT
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

        # 1. Background twinkling starfield
        set_pixel(3, 4, 30, 40, 80)
        set_pixel(12, 8, 30, 40, 80)
        set_pixel(6, 12, 40, 50, 90)

        # 2. Tractor Beam Projection (Pulsing Cyan Cone)
        if self.beam_active:
            py_int = int(round(self.py))
            px_int = int(round(self.px))
            for y in range(max(0, py_int - 8), py_int):
                half_w = int(0.8 + (py_int - y) * 0.25)
                for bx in range(px_int - half_w, px_int + half_w + 1):
                    set_pixel(bx, y, 20, 140, 255)

        # 3. Enemies
        for e in self.enemies:
            if not e["alive"]:
                continue
            ex = int(round(e["x"]))
            ey = int(round(e["y"]))
            if e["state"] == "captured_suck":
                set_pixel(ex, ey, 255, 255, 255)  # Hypnotized white
            elif e["state"] == "diving":
                set_pixel(ex, ey, 255, 50, 50)    # Diving red
            else:
                set_pixel(ex, ey, 220, 160, 40)   # Formation amber

        # 4. Player Lasers
        for l in self.lasers:
            lx = int(round(l["x"]))
            ly = int(round(l["y"]))
            set_pixel(lx, ly, 255, 255, 100)

        # 5. Enemy Bullets
        for b in self.enemy_bullets:
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            set_pixel(bx, by, 255, 60, 180)

        # 6. Escort Wingmen
        px = int(round(self.px))
        py = int(round(self.py))
        offsets = [-2, 2, -3, 3]
        for i in range(self.escorts_count):
            ox = offsets[i]
            set_pixel(px + ox, py, 60, 200, 255)

        # 7. Player Gaplus Fighter
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 255, 220, 40)      # Golden core
            set_pixel(px, py - 1, 240, 60, 40)   # Nose cone
            set_pixel(px - 1, py, 200, 40, 40)   # Left wing
            set_pixel(px + 1, py, 200, 40, 40)   # Right wing
        elif self.state == STATE_PLAYER_HIT:
            set_pixel(px, py, 255, 80, 20)

        # 8. Tractor Energy gauge on right border
        gauge_h = int(self.beam_energy * 6.0)
        for gy in range(gauge_h):
            set_pixel(15, 15 - gy, 40, 180, 255)

        # 9. Lives in top-left
        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 255, 220, 40)

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
            "escorts_count": self.escorts_count,
            "beam_active": self.beam_active,
            "beam_energy": self.beam_energy,
            "enemies_count": sum(1 for e in self.enemies if e["alive"]),
        }

