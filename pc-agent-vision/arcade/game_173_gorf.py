"""
Game #173: 高尔夫太空战 (Gorf - 1981 Bally Midway / Dave Nutting Associates)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released in 1981 by Bally Midway and created by Jamie Fenton (Dave Nutting Associates),
Gorf was an iconic milestone in arcade history. It was the first multi-mission sequential
campaign game in arcades, delivering diverse tactical phases culminating in a boss battle
against the giant Gorfian Flagship, complete with pioneering synthesized speech.

Unique Core Mechanic (Strict Zero-Redundancy):
- 3-Phase Sequential Campaign Chain:
  1. Laser Attack: Face high-threat enemy assault craft laying down continuous vertical laser beams.
  2. Space Warp Vortex: Hyperspace singularity at screen center where spiraling warp fighters emerge outward.
  3. Flagship Shield Breach & Reactor Sniping: Massive flagship shielded by an ablative energy barrier.
     Player must blast holes through the force field, then thread a laser bolt directly into the glowing
     vulnerable central reactor core to detonate the entire mothership!
- 2D Flight Maneuverability: Free directional movement in the lower defense sector.
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
STATE_PHASE_TRANSITION = 1
STATE_FLAGSHIP_EXPLODING = 2
STATE_PLAYER_DIED = 3
STATE_GAME_OVER = 4

PHASE_LASER_ATTACK = 0
PHASE_SPACE_WARP = 1
PHASE_FLAGSHIP_CORE = 2

class Game173Gorf(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.cycle = 1
        self.phase = PHASE_LASER_ATTACK
        self.state_timer = 0.0

        # Player Fighter
        self.px = 7.5
        self.py = 13.0
        self.laser_active = False
        self.lx = 0.0
        self.ly = 0.0
        self.laser_speed = 18.0

        # Phase 1: Laser Attack escorts [{x, y, vx, alive, laser_timer, firing_beam}]
        self.escorts: List[Dict[str, Any]] = []

        # Phase 2: Space Warp [{angle, radius, speed, alive}]
        self.warp_ships: List[Dict[str, Any]] = []

        # Phase 3: Flagship [{shield_mask: 8 bits, core_hp, core_x, core_y, ship_x, ship_dir}]
        self.shield_bits = 0xFF # 8 bits for columns x=4..11
        self.flagship_core_hp = 1
        self.flagship_x = 7.5
        self.flagship_dir = 1.0

        # Enemy projectiles
        self.bombs: List[Dict[str, float]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 173

    @property
    def name(self) -> str:
        return "高尔夫太空战"

    @property
    def english_name(self) -> str:
        return "Gorf"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "三阶段连环战役推进（激光护航突围、空间漩涡弹射、母舰力场凿孔穿刺核心反应堆爆破）"

    def get_name(self) -> str:
        return "Gorf (1981)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.cycle = 1
        self.phase = PHASE_LASER_ATTACK
        self._init_phase()

    def _init_phase(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 13.0
        self.laser_active = False
        self.bombs.clear()

        if self.phase == PHASE_LASER_ATTACK:
            self.escorts = [
                {"x": 2.5 + i * 3.2, "y": 2.5, "vx": 1.2 if i % 2 == 0 else -1.2, "alive": True, "laser_timer": 1.0 + i * 0.8, "firing_beam": 0.0}
                for i in range(4)
            ]
        elif self.phase == PHASE_SPACE_WARP:
            self.warp_ships = [
                {"angle": i * (math.pi / 3.0), "radius": 0.5, "speed": 1.4 + self.cycle * 0.2, "alive": True}
                for i in range(6)
            ]
        elif self.phase == PHASE_FLAGSHIP_CORE:
            self.shield_bits = 0xFF # 8 full shield blocks
            self.flagship_core_hp = 1
            self.flagship_x = 7.5
            self.flagship_dir = 1.0

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_PHASE_TRANSITION:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.phase == PHASE_FLAGSHIP_CORE:
                    # Advanced entire cycle
                    self.cycle += 1
                    self.phase = PHASE_LASER_ATTACK
                else:
                    self.phase += 1
                self._init_phase()
            return

        if self.state == STATE_FLAGSHIP_EXPLODING:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.state = STATE_PHASE_TRANSITION
                self.state_timer = 1.0
            return

        if self.state == STATE_PLAYER_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.0
                    self.laser_active = False
                    self.bombs.clear()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Player Movement (2D in lower zone y in [9.0, 14.0])
        speed = 7.0
        if keys_down & KEY_LEFT:  self.px -= speed * dt
        if keys_down & KEY_RIGHT: self.px += speed * dt
        if keys_down & KEY_UP:    self.py -= speed * dt
        if keys_down & KEY_DOWN:  self.py += speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(9.0, min(14.0, self.py))

        # Fire Quark Laser
        if keys_pressed & KEY_A:
            self.laser_active = True
            self.lx = self.px
            self.ly = self.py - 1.0

        # Update Player Laser
        if self.laser_active:
            self.ly -= self.laser_speed * dt
            if self.ly < 0.0:
                self.laser_active = False
            else:
                self._check_laser_hit()

        # Update Current Phase Mechanics
        if self.phase == PHASE_LASER_ATTACK:
            self._update_laser_attack(dt)
        elif self.phase == PHASE_SPACE_WARP:
            self._update_space_warp(dt)
        elif self.phase == PHASE_FLAGSHIP_CORE:
            self._update_flagship(dt)

        # Update Bombs
        for b in self.bombs[:]:
            b["y"] += 6.0 * dt
            if b["y"] > 15.0:
                self.bombs.remove(b)
            elif math.hypot(b["x"] - self.px, b["y"] - self.py) < 0.8:
                self.bombs.remove(b)
                self._kill_player()
                return

    def _check_laser_hit(self):
        if not self.laser_active:
            return

        if self.phase == PHASE_LASER_ATTACK:
            for e in self.escorts:
                if e["alive"] and math.hypot(e["x"] - self.lx, e["y"] - self.ly) < 1.0:
                    e["alive"] = False
                    self.laser_active = False
                    self.score += 200
                    if not any(esc["alive"] for esc in self.escorts):
                        self.state = STATE_PHASE_TRANSITION
                        self.state_timer = 1.0
                        self.score += 500
                    break

        elif self.phase == PHASE_SPACE_WARP:
            cx, cy = 7.5, 6.0
            for s in self.warp_ships:
                if not s["alive"]:
                    continue
                sx = cx + math.cos(s["angle"]) * s["radius"]
                sy = cy + math.sin(s["angle"]) * s["radius"]
                if math.hypot(sx - self.lx, sy - self.ly) < 1.0:
                    s["alive"] = False
                    self.laser_active = False
                    self.score += 150
                    if not any(w["alive"] for w in self.warp_ships):
                        self.state = STATE_PHASE_TRANSITION
                        self.state_timer = 1.0
                        self.score += 600
                    break

        elif self.phase == PHASE_FLAGSHIP_CORE:
            # 1. Check Shield Collision at row y=5, columns 4..11
            if 4.5 <= self.ly <= 5.5 and 3.5 <= self.lx <= 11.5:
                col = int(round(self.lx)) - 4
                if 0 <= col < 8:
                    bit_mask = (1 << col)
                    if self.shield_bits & bit_mask:
                        # Blast away shield segment!
                        self.shield_bits &= ~bit_mask
                        self.laser_active = False
                        self.score += 100
                        return

            # 2. Check Reactor Core Direct Snipe (core at x ~ 7.5, y ~ 3.0)
            if math.hypot(self.flagship_x - self.lx, 3.0 - self.ly) < 1.0:
                self.flagship_core_hp -= 1
                self.laser_active = False
                if self.flagship_core_hp <= 0:
                    # Detonate Flagship!
                    self.state = STATE_FLAGSHIP_EXPLODING
                    self.state_timer = 1.5
                    self.score += 2500

    def _update_laser_attack(self, dt: float):
        for e in self.escorts:
            if not e["alive"]:
                continue
            e["x"] += e["vx"] * dt
            if e["x"] > 14.0:
                e["x"] = 14.0
                e["vx"] = -abs(e["vx"])
            elif e["x"] < 1.5:
                e["x"] = 1.5
                e["vx"] = abs(e["vx"])

            e["laser_timer"] -= dt
            if e["laser_timer"] <= 0.0:
                e["firing_beam"] = 0.4 # Fire continuous beam for 0.4s
                e["laser_timer"] = 2.0

            if e["firing_beam"] > 0.0:
                e["firing_beam"] -= dt
                # Check beam collision: laser extends vertically down along e["x"]
                if abs(self.px - e["x"]) < 0.8 and self.py >= e["y"]:
                    self._kill_player()
                    return

    def _update_space_warp(self, dt: float):
        cx, cy = 7.5, 6.0
        for s in self.warp_ships:
            if not s["alive"]:
                continue
            s["angle"] += 3.0 * dt
            s["radius"] += s["speed"] * dt
            sx = cx + math.cos(s["angle"]) * s["radius"]
            sy = cy + math.sin(s["angle"]) * s["radius"]

            # If ship spirals outward and collides with player
            if math.hypot(sx - self.px, sy - self.py) < 0.9:
                self._kill_player()
                return

            # If reaches outer edge without being destroyed, wrap back to center
            if s["radius"] > 9.0:
                s["radius"] = 0.5
                s["angle"] += 1.0

    def _update_flagship(self, dt: float):
        # Flagship moves slowly side to side
        self.flagship_x += self.flagship_dir * 1.5 * dt
        if self.flagship_x > 9.0:
            self.flagship_x = 9.0
            self.flagship_dir = -1.0
        elif self.flagship_x < 6.0:
            self.flagship_x = 6.0
            self.flagship_dir = 1.0

        # Flagship drops tracking bombs
        if len(self.bombs) < 2 and (len(self.bombs) == 0 or self.bombs[-1]["y"] > 8.0):
            self.bombs.append({"x": self.flagship_x, "y": 4.5})

    def _kill_player(self):
        self.lives -= 1
        self.state = STATE_PLAYER_DIED
        self.state_timer = 1.0
        self.laser_active = False

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

        # Phase Rendering
        if self.phase == PHASE_LASER_ATTACK:
            for e in self.escorts:
                if e["alive"]:
                    ex, ey = int(round(e["x"])), int(round(e["y"]))
                    set_pixel(ex, ey, 255, 60, 60)
                    set_pixel(ex - 1, ey - 1, 200, 40, 40)
                    set_pixel(ex + 1, ey - 1, 200, 40, 40)
                    # Laser beam
                    if e["firing_beam"] > 0.0:
                        for by in range(ey + 1, 16):
                            set_pixel(ex, by, 80, 240, 255) # Cyan high-energy laser beam

        elif self.phase == PHASE_SPACE_WARP:
            # Singularity center
            cx, cy = 7.5, 6.0
            set_pixel(7, 6, 120, 40, 200)
            set_pixel(8, 6, 120, 40, 200)
            for s in self.warp_ships:
                if s["alive"]:
                    sx = int(round(cx + math.cos(s["angle"]) * s["radius"]))
                    sy = int(round(cy + math.sin(s["angle"]) * s["radius"]))
                    set_pixel(sx, sy, 255, 200, 40)

        elif self.phase == PHASE_FLAGSHIP_CORE:
            fx = int(round(self.flagship_x))
            if self.state == STATE_FLAGSHIP_EXPLODING:
                # Cataclysmic explosion
                for y in range(1, 6):
                    for x in range(3, 13):
                        if (x + y + int(self.state_timer * 10)) % 2 == 0:
                            set_pixel(x, y, 255, 120, 20)
                        else:
                            set_pixel(x, y, 255, 240, 40)
            else:
                # Flagship Hull
                for x in range(fx - 4, fx + 5):
                    set_pixel(x, 1, 140, 30, 160)
                    set_pixel(x, 2, 180, 40, 200)
                # Glowing Reactor Core (Snipe Target!)
                set_pixel(fx, 3, 255, 255, 255) # Pure white-hot center
                set_pixel(fx - 1, 3, 255, 100, 0)
                set_pixel(fx + 1, 3, 255, 100, 0)

                # Ablative Force Shield at row y=5
                for col in range(8):
                    if self.shield_bits & (1 << col):
                        set_pixel(4 + col, 5, 0, 180, 255) # Cyan energy barrier

        # Bombs
        for b in self.bombs:
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 120, 0)

        # Player Quark Laser
        if self.laser_active:
            lx, ly = int(round(self.lx)), int(round(self.ly))
            set_pixel(lx, ly, 255, 255, 80)
            set_pixel(lx, ly + 1, 255, 200, 0)

        # Player Fighter
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_PHASE_TRANSITION, STATE_FLAGSHIP_EXPLODING):
            set_pixel(px, py - 1, 80, 240, 255) # Cockpit
            set_pixel(px, py, 40, 120, 240)     # Main hull
            set_pixel(px - 1, py + 1, 200, 40, 40) # Left wing thruster
            set_pixel(px + 1, py + 1, 200, 40, 40) # Right wing thruster
        elif self.state == STATE_PLAYER_DIED:
            set_pixel(px, py, 255, 100, 0)
            set_pixel(px - 1, py, 255, 0, 0)
            set_pixel(px + 1, py, 255, 0, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "cycle": self.cycle,
            "phase": self.phase,
            "px": self.px,
            "py": self.py,
            "laser_active": self.laser_active,
            "shield_bits": bin(self.shield_bits),
            "flagship_core_hp": self.flagship_core_hp,
        }
