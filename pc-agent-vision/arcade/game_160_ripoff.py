"""
Game #160: 碰碰抢夺 / 燃料守卫 (Rip Off - 1979 Cinematronics / Tim Skelly)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Rip Off (1979) was the very first arcade game to introduce cooperative/competitive
objective defense and "theft" behavior. Enemies do not just attack the player;
their primary mission is to tractor-beam fuel canisters from the central depot
and drag/tow them off the edge of the screen!

Unique Mechanic (Strict Zero-Redundancy):
- Central Fuel Depot: 4 fuel canisters at center (7,7), (8,7), (7,8), (8,8).
- Pirate Raider Tanks: Invade from screen perimeters to grapple and tow canisters away.
- Ballistic Interception: Destroy pirate tanks to release towed canisters.
- Infinite Ship Respawn tied to Fuel Reserves: The game continues until all fuel is stolen.
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
STATE_GAME_OVER = 2

class Game160RipOff(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.wave = 1

        # Player state
        self.player_x = 8.0
        self.player_y = 12.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.facing_dx = 0.0
        self.facing_dy = -1.0
        self.player_alive = True
        self.respawn_timer = 0.0
        self.respawn_cooldown = 1.0

        # Bullets: list of dicts {x, y, vx, vy, life}
        self.bullets: List[Dict[str, float]] = []
        self.bullet_speed = 14.0
        self.fire_cooldown = 0.0

        # Fuel canisters: 4 in central depot
        self.canisters: List[Dict[str, Any]] = [
            {"id": 0, "x": 7.0, "y": 7.0, "home_x": 7.0, "home_y": 7.0, "status": "at_base", "carrier_id": -1},
            {"id": 1, "x": 8.0, "y": 7.0, "home_x": 8.0, "home_y": 7.0, "status": "at_base", "carrier_id": -1},
            {"id": 2, "x": 7.0, "y": 8.0, "home_x": 7.0, "home_y": 8.0, "status": "at_base", "carrier_id": -1},
            {"id": 3, "x": 8.0, "y": 8.0, "home_x": 8.0, "home_y": 8.0, "status": "at_base", "carrier_id": -1},
        ]

        # Pirate raiders: list of dicts {id, x, y, speed, target_canister, towing_canister, alive}
        self.pirates: List[Dict[str, Any]] = []
        self.max_pirates = 2
        self.pirates_killed_in_wave = 0
        self.pirates_needed_for_wave = 6
        self.spawn_timer = 0.5
        self.next_pirate_id = 0

        # Visual explosion particles: {x, y, timer}
        self.explosions: List[Dict[str, Any]] = []

    @property
    def game_id(self) -> int:
        return 160

    @property
    def name(self) -> str:
        return "碰碰抢夺"

    @property
    def english_name(self) -> str:
        return "Rip Off"

    @property
    def release_year(self) -> int:
        return 1979

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "中央燃料堆守卫、海盗战车挂钩拖拽盗窃、击毁敌坦截获掉落物资、磁吸回收与无限战机续命"

    def get_name(self) -> str:
        return "Rip Off (1979)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = STATE_PLAYING
        self.score = 0
        self.wave = 1
        self.player_x = 8.0
        self.player_y = 12.0
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.facing_dx = 0.0
        self.facing_dy = -1.0
        self.player_alive = True
        self.respawn_timer = 0.0
        self.fire_cooldown = 0.0
        self.bullets.clear()
        self.pirates.clear()
        self.explosions.clear()
        self.pirates_killed_in_wave = 0
        self.pirates_needed_for_wave = 6
        self.spawn_timer = 0.5
        self.next_pirate_id = 0
        for i, c in enumerate(self.canisters):
            c["x"] = c["home_x"]
            c["y"] = c["home_y"]
            c["status"] = "at_base"
            c["carrier_id"] = -1

    def remaining_fuel_count(self) -> int:
        return sum(1 for c in self.canisters if c["status"] != "stolen")

    def fire_laser(self):
        if not self.player_alive or self.fire_cooldown > 0.0:
            return
        if len(self.bullets) >= 3:
            return

        bx = self.player_x + self.facing_dx * 0.8
        by = self.player_y + self.facing_dy * 0.8
        bvx = self.facing_dx * self.bullet_speed
        bvy = self.facing_dy * self.bullet_speed

        self.bullets.append({
            "x": bx,
            "y": by,
            "vx": bvx,
            "vy": bvy,
            "life": 1.2
        })
        self.fire_cooldown = 0.22

    def magnet_recover_canisters(self):
        """Magnetic tractor beam pulls nearby dropped canisters instantly back to base."""
        for c in self.canisters:
            if c["status"] == "dropped":
                dist = math.hypot(c["x"] - self.player_x, c["y"] - self.player_y)
                if dist < 4.0:
                    c["x"] = c["home_x"]
                    c["y"] = c["home_y"]
                    c["status"] = "at_base"
                    self.score += 25

    def spawn_pirate(self):
        if len(self.pirates) >= self.max_pirates:
            return

        side = self.next_pirate_id % 4
        px, py = 0.0, 0.0
        if side == 0:    # Top
            px, py = 4.0 + (self.next_pirate_id * 3) % 8, 0.0
        elif side == 1:  # Right
            px, py = 15.0, 4.0 + (self.next_pirate_id * 3) % 8
        elif side == 2:  # Bottom
            px, py = 4.0 + (self.next_pirate_id * 3) % 8, 15.0
        else:            # Left
            px, py = 0.0, 4.0 + (self.next_pirate_id * 3) % 8

        pirate = {
            "id": self.next_pirate_id,
            "x": float(px),
            "y": float(py),
            "speed": 2.2 + self.wave * 0.35,
            "target_canister": -1,
            "towing_canister": -1,
            "alive": True
        }
        self.next_pirate_id += 1
        self.pirates.append(pirate)

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_GAME_OVER:
            if ((keys_pressed & KEY_A) or (keys_pressed & KEY_B)):
                self.reset()
            return

        # Particle explosions update
        for exp in list(self.explosions):
            exp["timer"] -= dt
            if exp["timer"] <= 0:
                self.explosions.remove(exp)

        # Fire cooldown
        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Player respawn logic
        if not self.player_alive:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                if self.remaining_fuel_count() > 0:
                    self.player_alive = True
                    self.player_x = 8.0
                    self.player_y = 12.0
                    self.player_vx = 0.0
                    self.player_vy = 0.0
                else:
                    self.state = STATE_GAME_OVER
                    return
        else:
            speed = 5.5
            if keys_down & KEY_UP:
                self.player_vx = 0.0
                self.player_vy = -speed
                self.facing_dx = 0.0
                self.facing_dy = -1.0
            elif keys_down & KEY_DOWN:
                self.player_vx = 0.0
                self.player_vy = speed
                self.facing_dx = 0.0
                self.facing_dy = 1.0
            elif keys_down & KEY_LEFT:
                self.player_vx = -speed
                self.player_vy = 0.0
                self.facing_dx = -1.0
                self.facing_dy = 0.0
            elif keys_down & KEY_RIGHT:
                self.player_vx = speed
                self.player_vy = 0.0
                self.facing_dx = 1.0
                self.facing_dy = 0.0
            else:
                self.player_vx = 0.0
                self.player_vy = 0.0

            if keys_pressed & KEY_A:
                self.fire_laser()
            if keys_pressed & KEY_B:
                self.magnet_recover_canisters()

            self.player_x += self.player_vx * dt
            self.player_y += self.player_vy * dt
            self.player_x = max(0.0, min(15.0, self.player_x))
            self.player_y = max(0.0, min(15.0, self.player_y))

            # Touch dropped canister to return it
            for c in self.canisters:
                if c["status"] == "dropped":
                    if math.hypot(c["x"] - self.player_x, c["y"] - self.player_y) < 1.0:
                        c["x"] = c["home_x"]
                        c["y"] = c["home_y"]
                        c["status"] = "at_base"
                        self.score += 50

        # Bullets update
        for b in list(self.bullets):
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["life"] -= dt
            if b["life"] <= 0 or b["x"] < 0 or b["x"] > 15 or b["y"] < 0 or b["y"] > 15:
                self.bullets.remove(b)
                continue

            # Hit detection against pirates
            for p in self.pirates:
                if p["alive"] and math.hypot(p["x"] - b["x"], p["y"] - b["y"]) < 1.1:
                    p["alive"] = False
                    self.bullets.remove(b)
                    self.score += 100
                    self.pirates_killed_in_wave += 1
                    self.explosions.append({"x": p["x"], "y": p["y"], "timer": 0.3})

                    # If pirate was towing a canister, drop it
                    if p["towing_canister"] != -1:
                        cid = p["towing_canister"]
                        self.canisters[cid]["status"] = "dropped"
                        self.canisters[cid]["carrier_id"] = -1
                        p["towing_canister"] = -1
                    break

        # Spawn pirates
        if len(self.pirates) < self.max_pirates and self.pirates_killed_in_wave < self.pirates_needed_for_wave:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_pirate()
                self.spawn_timer = 1.0

        # Update pirates
        for p in list(self.pirates):
            if not p["alive"]:
                self.pirates.remove(p)
                continue

            # Collision with player
            if self.player_alive and math.hypot(p["x"] - self.player_x, p["y"] - self.player_y) < 1.0:
                self.player_alive = False
                self.respawn_timer = self.respawn_cooldown
                p["alive"] = False
                self.explosions.append({"x": self.player_x, "y": self.player_y, "timer": 0.4})
                self.explosions.append({"x": p["x"], "y": p["y"], "timer": 0.4})
                if p["towing_canister"] != -1:
                    cid = p["towing_canister"]
                    self.canisters[cid]["status"] = "dropped"
                    self.canisters[cid]["carrier_id"] = -1
                self.pirates.remove(p)
                if self.remaining_fuel_count() == 0:
                    self.state = STATE_GAME_OVER
                continue

            # Behavior AI
            if p["towing_canister"] == -1:
                avail = [c for c in self.canisters if c["status"] in ("at_base", "dropped")]
                if avail:
                    target = min(avail, key=lambda c: math.hypot(c["x"] - p["x"], c["y"] - p["y"]))
                    dx = target["x"] - p["x"]
                    dy = target["y"] - p["y"]
                    dist = math.hypot(dx, dy)
                    if dist > 0.4:
                        p["x"] += (dx / dist) * p["speed"] * dt
                        p["y"] += (dy / dist) * p["speed"] * dt
                    else:
                        p["towing_canister"] = target["id"]
                        target["status"] = "towed"
                        target["carrier_id"] = p["id"]
                else:
                    if self.player_alive:
                        dx = self.player_x - p["x"]
                        dy = self.player_y - p["y"]
                        dist = math.hypot(dx, dy)
                        if dist > 0.1:
                            p["x"] += (dx / dist) * p["speed"] * dt
                            p["y"] += (dy / dist) * p["speed"] * dt
            else:
                cid = p["towing_canister"]
                canister = self.canisters[cid]

                d_left = p["x"]
                d_right = 15.0 - p["x"]
                d_top = p["y"]
                d_bottom = 15.0 - p["y"]
                min_d = min(d_left, d_right, d_top, d_bottom)

                esc_dx, esc_dy = 0.0, 0.0
                if min_d == d_left:
                    esc_dx = -1.0
                elif min_d == d_right:
                    esc_dx = 1.0
                elif min_d == d_top:
                    esc_dy = -1.0
                else:
                    esc_dy = 1.0

                p["x"] += esc_dx * p["speed"] * dt
                p["y"] += esc_dy * p["speed"] * dt

                canister["x"] = p["x"] - esc_dx * 0.8
                canister["y"] = p["y"] - esc_dy * 0.8

                if p["x"] <= -0.5 or p["x"] >= 15.5 or p["y"] <= -0.5 or p["y"] >= 15.5:
                    canister["status"] = "stolen"
                    canister["carrier_id"] = -1
                    self.pirates.remove(p)

                    if self.remaining_fuel_count() == 0:
                        self.state = STATE_GAME_OVER
                    continue

        # Check wave progression
        if self.pirates_killed_in_wave >= self.pirates_needed_for_wave and len(self.pirates) == 0:
            self.wave += 1
            self.pirates_killed_in_wave = 0
            self.pirates_needed_for_wave = 6 + self.wave * 2
            self.score += 500 * self.remaining_fuel_count()
            for c in self.canisters:
                if c["status"] == "dropped":
                    c["x"] = c["home_x"]
                    c["y"] = c["home_y"]
                    c["status"] = "at_base"

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

        # Draw Fuel Canisters
        for c in self.canisters:
            cx, cy = int(round(c["x"])), int(round(c["y"]))
            if c["status"] == "at_base":
                set_pixel(cx, cy, 0, 220, 255)
            elif c["status"] == "dropped":
                set_pixel(cx, cy, 255, 180, 0)
            elif c["status"] == "towed":
                set_pixel(cx, cy, 255, 255, 0)

        # Draw Pirates
        for p in self.pirates:
            if p["alive"]:
                px, py = int(round(p["x"])), int(round(p["y"]))
                if p["towing_canister"] == -1:
                    set_pixel(px, py, 255, 30, 80)
                else:
                    set_pixel(px, py, 255, 80, 20)

        # Draw Player
        if self.player_alive:
            px, py = int(round(self.player_x)), int(round(self.player_y))
            set_pixel(px, py, 0, 255, 120)

        # Draw Bullets
        for b in self.bullets:
            bx, by = int(round(b["x"])), int(round(b["y"]))
            set_pixel(bx, by, 255, 255, 255)

        # Draw Explosions
        for exp in self.explosions:
            ex, ey = int(round(exp["x"])), int(round(exp["y"]))
            set_pixel(ex, ey, 255, 200, 50)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "wave": self.wave,
            "remaining_fuel": self.remaining_fuel_count(),
            "player_alive": self.player_alive,
            "player_x": self.player_x,
            "player_y": self.player_y,
            "active_pirates": len([p for p in self.pirates if p["alive"]]),
        }
