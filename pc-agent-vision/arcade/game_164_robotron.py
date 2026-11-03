"""
Game #164: 机器人大战2084 (Robotron: 2084 - 1982 Williams / Eugene Jarvis & Larry DeMar)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Robotron: 2084 (1982) revolutionized arcade action as the archetypal twin-stick arena shooter.
Defending the last human family against a robot rebellion, it introduced frantic survival
where indestructible Hulks crush civilians and Grunts swarm in overwhelming waves.

Unique Mechanic (Strict Zero-Redundancy):
- Humanoid Civilian Rescue: Touch wandering clone humans (Mom, Dad, Mikey) before they are crushed.
- Indestructible Roaming Hulks: Hulks cannot be killed by lasers; shots only knock them back.
- High-Density Swarm Annihilation: Eradicate Grunts while evading unstoppable walking tanks.
- Emergency EMP Blast (Key B): Screen-clearing electromagnetic pulse for dire corners.
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
STATE_WAVE_CLEAR = 1
STATE_PLAYER_DIED = 2
STATE_GAME_OVER = 3

class Game164Robotron(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.wave = 1
        self.state_timer = 0.0

        # Player state
        self.px = 7.5
        self.py = 7.5
        self.facing_dx = 0.0
        self.facing_dy = -1.0
        self.speed = 5.5
        self.fire_cooldown = 0.0
        self.emp_charges = 1

        # Lasers: list of {x, y, vx, vy, life}
        self.lasers: List[Dict[str, float]] = []

        # Humans: list of {id, x, y, vx, vy, alive, rescued}
        self.humans: List[Dict[str, Any]] = []

        # Hulks (Indestructible enemies): list of {x, y, vx, vy}
        self.hulks: List[Dict[str, float]] = []

        # Grunts (Destructible swarming robots): list of {x, y, speed, alive}
        self.grunts: List[Dict[str, Any]] = []

        self.init()

    @property
    def game_id(self) -> int:
        return 164

    @property
    def name(self) -> str:
        return "机器人大战2084"

    @property
    def english_name(self) -> str:
        return "Robotron: 2084"

    @property
    def release_year(self) -> int:
        return 1982

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "竞技场双摇杆式全向射击、搜救人类克隆家族、遭遇无敌浩克巨怪撞击击退与全屏EMP脉冲"

    def get_name(self) -> str:
        return "Robotron: 2084 (1982)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.wave = 1
        self._init_wave()

    def _init_wave(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 7.5
        self.facing_dx = 0.0
        self.facing_dy = -1.0
        self.fire_cooldown = 0.0
        self.emp_charges = 1

        self.lasers.clear()

        # Spawn 3 humans (Mommy, Daddy, Mikey)
        self.humans = [
            {"id": 0, "x": 3.0, "y": 4.0, "vx": 1.2, "vy": 0.8, "alive": True, "rescued": False},
            {"id": 1, "x": 12.0, "y": 4.0, "vx": -1.0, "vy": 1.1, "alive": True, "rescued": False},
            {"id": 2, "x": 7.5, "y": 12.0, "vx": 1.1, "vy": -1.0, "alive": True, "rescued": False},
        ]

        # Spawn 2 Indestructible Hulks
        self.hulks = [
            {"x": 2.0, "y": 2.0, "vx": 0.8, "vy": 0.6},
            {"x": 13.0, "y": 13.0, "vx": -0.7, "vy": -0.8},
        ]

        # Spawn Grunt robots (6 + wave * 2)
        num_grunts = min(12, 6 + self.wave * 2)
        self.grunts.clear()
        for i in range(num_grunts):
            # Place around borders
            gx = 1.0 if (i % 2 == 0) else 14.0
            gy = 2.0 + (i * 2.5) % 12.0
            self.grunts.append({
                "id": i,
                "x": gx,
                "y": gy,
                "speed": 1.8 + self.wave * 0.25,
                "alive": True
            })

    def fire_laser(self):
        if self.fire_cooldown > 0.0 or self.state != STATE_PLAYING:
            return
        if len(self.lasers) >= 4:
            return

        bx = self.px + self.facing_dx * 0.8
        by = self.py + self.facing_dy * 0.8
        b_speed = 16.0
        self.lasers.append({
            "x": bx,
            "y": by,
            "vx": self.facing_dx * b_speed,
            "vy": self.facing_dy * b_speed,
            "life": 0.8
        })
        self.fire_cooldown = 0.16

    def trigger_emp(self):
        """Button B: Screen EMP Shockwave clears all Grunts."""
        if self.emp_charges > 0 and self.state == STATE_PLAYING:
            self.emp_charges -= 1
            for g in self.grunts:
                if g["alive"]:
                    g["alive"] = False
                    self.score += 100

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_WAVE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.wave += 1
                self._init_wave()
            return

        if self.state == STATE_PLAYER_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 7.5
                    self.emp_charges = 1
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Player Movement & Facing Direction
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0
        if keys_down & KEY_RIGHT: dx += 1.0
        if keys_down & KEY_UP:    dy -= 1.0
        if keys_down & KEY_DOWN:  dy += 1.0

        if dx != 0.0 or dy != 0.0:
            len_d = math.hypot(dx, dy)
            self.facing_dx = dx / len_d
            self.facing_dy = dy / len_d
            self.px += (dx / len_d) * self.speed * dt
            self.py += (dy / len_d) * self.speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(1.0, min(14.0, self.py))

        # Action: Fire Laser
        if keys_pressed & KEY_A:
            self.fire_laser()

        # Action: EMP Pulse
        if keys_pressed & KEY_B:
            self.trigger_emp()

        # Human Movement & Rescue
        for h in self.humans:
            if h["alive"] and not h["rescued"]:
                h["x"] += h["vx"] * dt
                h["y"] += h["vy"] * dt
                if h["x"] <= 1.0 or h["x"] >= 14.0: h["vx"] = -h["vx"]
                if h["y"] <= 1.0 or h["y"] >= 14.0: h["vy"] = -h["vy"]

                # Player rescues human!
                if math.hypot(h["x"] - self.px, h["y"] - self.py) < 1.0:
                    h["rescued"] = True
                    self.score += 1000

        # Hulks (Indestructible) Update & Human Crushing
        for hlk in self.hulks:
            hlk["x"] += hlk["vx"] * dt
            hlk["y"] += hlk["vy"] * dt
            if hlk["x"] <= 1.0 or hlk["x"] >= 14.0: hlk["vx"] = -hlk["vx"]
            if hlk["y"] <= 1.0 or hlk["y"] >= 14.0: hlk["vy"] = -hlk["vy"]

            # Hulk crushes humans!
            for h in self.humans:
                if h["alive"] and not h["rescued"]:
                    if math.hypot(hlk["x"] - h["x"], hlk["y"] - h["y"]) < 0.9:
                        h["alive"] = False # Crushed!

            # Hulk hits player!
            if math.hypot(hlk["x"] - self.px, hlk["y"] - self.py) < 0.9:
                self.lives -= 1
                self.state = STATE_PLAYER_DIED
                self.state_timer = 1.0
                return

        # Lasers Update
        for l in list(self.lasers):
            l["x"] += l["vx"] * dt
            l["y"] += l["vy"] * dt
            l["life"] -= dt
            if l["life"] <= 0 or l["x"] < 0 or l["x"] > 15 or l["y"] < 0 or l["y"] > 15:
                self.lasers.remove(l)
                continue

            # Hit Hulks (Knockback only, indestructible!)
            for hlk in self.hulks:
                if math.hypot(hlk["x"] - l["x"], hlk["y"] - l["y"]) < 1.0:
                    # Push Hulk back along laser direction
                    hlk["x"] += (l["vx"] / 16.0) * 0.6
                    hlk["y"] += (l["vy"] / 16.0) * 0.6
                    hlk["x"] = max(1.0, min(14.0, hlk["x"]))
                    hlk["y"] = max(1.0, min(14.0, hlk["y"]))
                    if l in self.lasers:
                        self.lasers.remove(l)
                    break

            # Hit Grunts (Destroyed)
            for g in self.grunts:
                if g["alive"] and math.hypot(g["x"] - l["x"], g["y"] - l["y"]) < 1.0:
                    g["alive"] = False
                    self.score += 100
                    if l in self.lasers:
                        self.lasers.remove(l)
                    break

        # Grunts Update & Swarm Player
        active_grunts = 0
        for g in self.grunts:
            if not g["alive"]:
                continue
            active_grunts += 1

            gdx = self.px - g["x"]
            gdy = self.py - g["y"]
            g_dist = math.hypot(gdx, gdy)
            if g_dist > 0.1:
                g["x"] += (gdx / g_dist) * g["speed"] * dt
                g["y"] += (gdy / g_dist) * g["speed"] * dt

            # Hit player
            if math.hypot(g["x"] - self.px, g["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_PLAYER_DIED
                self.state_timer = 1.0
                return

        # Check wave completion (all Grunts eliminated)
        if active_grunts == 0:
            self.state = STATE_WAVE_CLEAR
            self.state_timer = 1.5
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

        # 1. Neon Grid Arena Boundaries
        for x in range(16):
            set_pixel(x, 0, 80, 0, 180)
            set_pixel(x, 15, 80, 0, 180)
        for y in range(16):
            set_pixel(0, y, 80, 0, 180)
            set_pixel(15, y, 80, 0, 180)

        # 2. Humans (Cyan Mommy / Dad / Mikey)
        for h in self.humans:
            if h["alive"] and not h["rescued"]:
                hx, hy = int(round(h["x"])), int(round(h["y"]))
                set_pixel(hx, hy, 0, 240, 255)

        # 3. Indestructible Hulks (Heavy Green Behemoths)
        for hlk in self.hulks:
            kx, ky = int(round(hlk["x"])), int(round(hlk["y"]))
            set_pixel(kx, ky, 0, 220, 40)
            set_pixel(kx + 1, ky, 0, 160, 20)

        # 4. Grunt Swarms (Red mechanical walkers)
        for g in self.grunts:
            if g["alive"]:
                gx, gy = int(round(g["x"])), int(round(g["y"]))
                set_pixel(gx, gy, 255, 30, 30)

        # 5. Lasers
        for l in self.lasers:
            lx, ly = int(round(l["x"])), int(round(l["y"]))
            set_pixel(lx, ly, 255, 255, 120)

        # 6. Player (Enforcer / Robotron Hero: Bright White & Orange)
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_WAVE_CLEAR):
            set_pixel(px, py, 255, 255, 255)
            set_pixel(px, py - 1, 255, 140, 0)
        elif self.state == STATE_PLAYER_DIED:
            set_pixel(px, py, 255, 40, 0)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "wave": self.wave,
            "emp_charges": self.emp_charges,
            "grunts_alive": len([g for g in self.grunts if g["alive"]]),
            "humans_alive": len([h for h in self.humans if h["alive"] and not h["rescued"]]),
            "px": self.px,
            "py": self.py,
        }
