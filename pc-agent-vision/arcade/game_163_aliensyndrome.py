"""
Game #163: 异型特警 (Alien Syndrome - 1987 Sega / Toru Nakayama)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released on Sega System 16 in 1987, Alien Syndrome defined the sci-fi horror run-and-gun subgenre.
Trapped inside an infested alien mothership, troopers Ricky and Mary must rescue captured comrades
held in cocoons, trigger the evacuation sequence before ship self-destruction, and defeat cosmic horrors.

Unique Mechanic (Strict Zero-Redundancy):
- Biomechanical Hostage Rescue: Locate and free all cocoons to unlock the blast doors.
- Timed Evacuation Alert: Rescuing the final comrade starts an emergency countdown to reach the exit airlock.
- Wall Pod Arsenal: Collect laser weapons from wall storage bays.
- Biomechanical Xenomorph Drones: Relentless swarming alien broods.
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
STATE_EVACUATION = 1
STATE_MISSION_CLEAR = 2
STATE_PLAYER_DIED = 3
STATE_GAME_OVER = 4

class Game163AlienSyndrome(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.level = 1
        self.state_timer = 0.0

        # Player Ricky state
        self.px = 2.0
        self.py = 2.0
        self.facing_dx = 1.0
        self.facing_dy = 0.0
        self.speed = 5.0
        self.has_laser = False
        self.fire_cooldown = 0.0

        # Comrades (Hostages trapped in cocoons)
        # list of {id, x, y, rescued}
        self.comrades: List[Dict[str, Any]] = []
        self.total_comrades = 4
        self.comrades_rescued = 0

        # Evacuation timer (starts when all comrades rescued)
        self.evac_timer = 15.0
        self.exit_open = False
        self.exit_x = 8.0
        self.exit_y = 0.0

        # Weapon Pods: {x, y, collected}
        self.weapon_pods: List[Dict[str, Any]] = []

        # Bullets: list of {x, y, vx, vy, is_laser}
        self.bullets: List[Dict[str, Any]] = []

        # Alien Enemies: list of {id, x, y, speed, hp, alive}
        self.aliens: List[Dict[str, Any]] = []
        self.alien_spawn_timer = 1.0

        self.init()

    @property
    def game_id(self) -> int:
        return 163

    @property
    def name(self) -> str:
        return "异型特警"

    @property
    def english_name(self) -> str:
        return "Alien Syndrome"

    @property
    def release_year(self) -> int:
        return 1987

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "异形母舰搜救被俘战友蚕茧、集齐开启气闸限时核爆倒计时撤离、强殖装甲激光突围"

    def get_name(self) -> str:
        return "Alien Syndrome (1987)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self._init_level()

    def _init_level(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 2.0
        self.py = 2.0
        self.facing_dx = 1.0
        self.facing_dy = 0.0
        self.has_laser = False
        self.fire_cooldown = 0.0
        self.exit_open = False
        self.evac_timer = 15.0

        self.bullets.clear()
        self.aliens.clear()
        self.comrades_rescued = 0

        # Setup 4 comrades
        self.comrades = [
            {"id": 0, "x": 13.0, "y": 2.0, "rescued": False},
            {"id": 1, "x": 2.0, "y": 13.0, "rescued": False},
            {"id": 2, "x": 13.0, "y": 13.0, "rescued": False},
            {"id": 3, "x": 8.0, "y": 8.0, "rescued": False},
        ]

        # Weapon pod at (8, 4)
        self.weapon_pods = [
            {"x": 8.0, "y": 4.0, "collected": False}
        ]

        # Initial aliens
        self.aliens = [
            {"id": 0, "x": 10.0, "y": 5.0, "speed": 2.2, "hp": 1, "alive": True},
            {"id": 1, "x": 5.0, "y": 10.0, "speed": 2.0, "hp": 1, "alive": True},
        ]
        self.alien_spawn_timer = 1.5

    def fire_weapon(self):
        if self.fire_cooldown > 0.0 or self.state not in (STATE_PLAYING, STATE_EVACUATION):
            return

        bx = self.px + self.facing_dx * 0.8
        by = self.py + self.facing_dy * 0.8
        b_speed = 15.0
        self.bullets.append({
            "x": bx,
            "y": by,
            "vx": self.facing_dx * b_speed,
            "vy": self.facing_dy * b_speed,
            "is_laser": self.has_laser,
            "life": 1.0
        })
        self.fire_cooldown = 0.15 if self.has_laser else 0.25

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_MISSION_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.level += 1
                self._init_level()
            return

        if self.state == STATE_PLAYER_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING if not self.exit_open else STATE_EVACUATION
                    self.px = 2.0
                    self.py = 2.0
                    self.has_laser = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Evacuation Countdown
        if self.state == STATE_EVACUATION:
            self.evac_timer -= dt
            if self.evac_timer <= 0.0:
                # Reactor Meltdown!
                self.lives -= 1
                self.state = STATE_PLAYER_DIED
                self.state_timer = 1.5
                return

        # Player Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:
            dx -= 1.0
            self.facing_dx = -1.0; self.facing_dy = 0.0
        elif keys_down & KEY_RIGHT:
            dx += 1.0
            self.facing_dx = 1.0; self.facing_dy = 0.0
        elif keys_down & KEY_UP:
            dy -= 1.0
            self.facing_dx = 0.0; self.facing_dy = -1.0
        elif keys_down & KEY_DOWN:
            dy += 1.0
            self.facing_dx = 0.0; self.facing_dy = 1.0

        if dx != 0.0 or dy != 0.0:
            self.px += dx * self.speed * dt
            self.py += dy * self.speed * dt

        self.px = max(1.0, min(14.0, self.px))
        self.py = max(1.0, min(14.0, self.py))

        # Action: Fire
        if keys_pressed & KEY_A:
            self.fire_weapon()

        # Action: Smart Flare (Key B)
        if (keys_pressed & KEY_B):
            # Flash destroys nearby aliens
            for a in self.aliens:
                if a["alive"] and math.hypot(a["x"] - self.px, a["y"] - self.py) < 4.0:
                    a["alive"] = False
                    self.score += 150

        # Weapon Pods Interaction
        for wp in self.weapon_pods:
            if not wp["collected"] and math.hypot(wp["x"] - self.px, wp["y"] - self.py) < 1.0:
                wp["collected"] = True
                self.has_laser = True
                self.score += 300

        # Comrade Cocoons Interaction
        for c in self.comrades:
            if not c["rescued"] and math.hypot(c["x"] - self.px, c["y"] - self.py) < 1.0:
                c["rescued"] = True
                self.comrades_rescued += 1
                self.score += 200

                # Check if all comrades rescued!
                if self.comrades_rescued >= self.total_comrades:
                    self.exit_open = True
                    self.state = STATE_EVACUATION
                    self.score += 1000

        # Check Exit Reach
        if self.exit_open and math.hypot(self.exit_x - self.px, self.exit_y - self.py) < 1.2:
            self.state = STATE_MISSION_CLEAR
            self.state_timer = 2.0
            self.score += int(self.evac_timer * 100) + 2000
            return

        # Bullets Update
        for b in list(self.bullets):
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["life"] -= dt

            if b["life"] <= 0 or b["x"] < 0 or b["x"] > 15 or b["y"] < 0 or b["y"] > 15:
                self.bullets.remove(b)
                continue

            for a in self.aliens:
                if a["alive"] and math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 1.0:
                    a["alive"] = False
                    self.score += 100
                    if not b["is_laser"]: # Normal bullet stops on hit; laser pierces
                        if b in self.bullets:
                            self.bullets.remove(b)
                    break

        # Spawn Aliens
        self.alien_spawn_timer -= dt
        if self.alien_spawn_timer <= 0.0 and len(self.aliens) < 5:
            self.aliens.append({
                "id": len(self.aliens),
                "x": 14.0 if (len(self.aliens) % 2 == 0) else 1.0,
                "y": 14.0 if (len(self.aliens) % 2 == 0) else 8.0,
                "speed": 2.2 + self.level * 0.3,
                "hp": 1,
                "alive": True
            })
            self.alien_spawn_timer = 2.0

        # Aliens Update & Chase
        for a in list(self.aliens):
            if not a["alive"]:
                self.aliens.remove(a)
                continue

            adx = self.px - a["x"]
            ady = self.py - a["y"]
            dist = math.hypot(adx, ady)
            if dist > 0.2:
                a["x"] += (adx / dist) * a["speed"] * dt
                a["y"] += (ady / dist) * a["speed"] * dt

            # Hit player
            if math.hypot(a["x"] - self.px, a["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_PLAYER_DIED
                self.state_timer = 1.0
                return

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

        # 1. Mothership Bio-Corridor Floor & Border Ribs
        for x in range(16):
            set_pixel(x, 0, 40, 20, 50)
            set_pixel(x, 15, 40, 20, 50)
        for y in range(16):
            set_pixel(0, y, 40, 20, 50)
            set_pixel(15, y, 40, 20, 50)

        # 2. Exit Airlock
        if self.exit_open:
            set_pixel(7, 0, 0, 255, 120)
            set_pixel(8, 0, 0, 255, 255) # Open green airlock
            set_pixel(9, 0, 0, 255, 120)
        else:
            set_pixel(8, 0, 180, 40, 40) # Locked red gate

        # 3. Weapon Pod
        for wp in self.weapon_pods:
            if not wp["collected"]:
                wx, wy = int(round(wp["x"])), int(round(wp["y"]))
                set_pixel(wx, wy, 255, 220, 0) # Gold pod

        # 4. Comrade Cocoons
        for c in self.comrades:
            if not c["rescued"]:
                cx, cy = int(round(c["x"])), int(round(c["y"]))
                set_pixel(cx, cy, 255, 180, 180) # Pale cocoon

        # 5. Alien Xenomorph Drones
        for a in self.aliens:
            if a["alive"]:
                ax, ay = int(round(a["x"])), int(round(a["y"]))
                set_pixel(ax, ay, 220, 30, 80) # Deep visceral red

        # 6. Bullets / Lasers
        for b in self.bullets:
            bx, by = int(round(b["x"])), int(round(b["y"]))
            if b["is_laser"]:
                set_pixel(bx, by, 0, 255, 255) # Cyan high-energy laser
            else:
                set_pixel(bx, by, 255, 255, 100) # Yellow bullet

        # 7. Ricky (Trooper)
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_EVACUATION, STATE_MISSION_CLEAR):
            if self.has_laser:
                set_pixel(px, py, 0, 240, 255) # Cyan powered suit
            else:
                set_pixel(px, py, 255, 255, 255) # White armored trooper
        elif self.state == STATE_PLAYER_DIED:
            set_pixel(px, py, 255, 80, 20)

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
            "comrades_rescued": self.comrades_rescued,
            "total_comrades": self.total_comrades,
            "exit_open": self.exit_open,
            "evac_timer": self.evac_timer,
            "has_laser": self.has_laser,
            "px": self.px,
            "py": self.py,
        }
