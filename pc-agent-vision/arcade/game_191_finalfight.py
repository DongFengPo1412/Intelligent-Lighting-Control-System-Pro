"""
Game #191: 快打旋风 (Final Fight - 1989 Capcom / Yoshiki Okamoto & Akira Nishitani)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Released by Capcom in December 1989 on the CP System arcade hardware, Final Fight revolutionized
and defined the golden age of side-scrolling beat 'em ups. Starring pro-wrestler Mayor Mike Haggar,
the game introduced the invincible health-draining desperation spin, visceral close-up grapple
throws (Spinning Piledriver), breakable environmental props, and massive urban gang battles.

Unique Core Mechanic (Strict Zero-Redundancy):
- Close-Quarter Grab & Spinning Piledriver (Button A):
  * When closing within grappling range, Haggar grabs the thug.
  * Pressing Button A launches Haggar into a soaring aerial corkscrew, driving the victim's head
    straight into the pavement for devastating direct and splash shockwave damage!
- Invincible Spinning Clothesline (Button B):
  * Haggar's iconic desperation attack: consumes 8 HP to spin with extended fists, granting 100%
    invincibility and sweeping all surrounding thugs off their feet!
- Breakable Oil Drums & Phone Booths:
  * Punching or slamming enemies into wooden barrels/phone booths shatters them, dropping
    a whole Roast Chicken to restore vital health!
- Metro City Slum Boss Battle: Face Mad Gear lieutenant Damnd and his leaping ambush reinforcements!
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
STATE_STAGE_CLEAR = 1
STATE_HAGGAR_KO = 2
STATE_GAME_OVER = 3

class Game191FinalFight(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Mayor Mike Haggar
        self.px = 3.0
        self.py = 11.0
        self.facing = 1 # 1: right, -1: left
        self.speed = 5.0
        self.hp = 100.0
        self.max_hp = 100.0

        # Actions & Timers
        self.is_punching = False
        self.punch_timer = 0.0
        self.is_spinning = False # Desperation Clothesline
        self.spin_timer = 0.0

        # Grapple State
        self.grabbed_enemy_idx: Optional[int] = None
        self.is_piledriving = False
        self.piledrive_timer = 0.0
        self.piledrive_height = 0.0

        # Enemies [{x, y, vx, vy, hp, max_hp, type: "thug"|"boss", alive, state: "normal"|"knockdown"|"grabbed", kd_timer}]
        self.enemies: List[Dict[str, Any]] = []

        # Breakable Barrel & Item {x, y, broken, item: "chicken"|"none", item_x, item_y, item_active}
        self.barrel: Dict[str, Any] = {}

        self.init()

    @property
    def game_id(self) -> int:
        return 191

    @property
    def name(self) -> str:
        return "快打旋风"

    @property
    def english_name(self) -> str:
        return "Final Fight"

    @property
    def release_year(self) -> int:
        return 1989

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "近身抓投螺旋打桩机、消耗生命值释放旋风双截拳绝对无敌击飞、破坏铁桶获取烤鸡"

    def get_name(self) -> str:
        return "Final Fight (1989)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.stage = 1
        self._init_stage()

    def _init_stage(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 3.0
        self.py = 11.0
        self.facing = 1
        self.hp = 100.0
        self.is_punching = False
        self.is_spinning = False
        self.grabbed_enemy_idx = None
        self.is_piledriving = False

        # Enemies
        self.enemies = [
            {"x": 8.0,  "y": 10.0, "vx": 0.0, "vy": 0.0, "hp": 25.0, "max_hp": 25.0, "type": "thug", "alive": True, "state": "normal", "kd_timer": 0.0},
            {"x": 12.0, "y": 12.0, "vx": 0.0, "vy": 0.0, "hp": 25.0, "max_hp": 25.0, "type": "thug", "alive": True, "state": "normal", "kd_timer": 0.0},
            {"x": 14.0, "y": 10.5, "vx": 0.0, "vy": 0.0, "hp": 60.0 + self.stage * 20.0, "max_hp": 60.0 + self.stage * 20.0, "type": "boss", "alive": True, "state": "normal", "kd_timer": 0.0},
        ]

        # Breakable Barrel
        self.barrel = {
            "x": 6.0,
            "y": 12.0,
            "broken": False,
            "item_active": False,
            "item_x": 6.0,
            "item_y": 12.0,
        }

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self._init_stage()
            return

        if self.state == STATE_HAGGAR_KO:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 3.0
                    self.py = 11.0
                    self.hp = 100.0
                    self.is_punching = False
                    self.is_spinning = False
                    self.grabbed_enemy_idx = None
                    self.is_piledriving = False
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Check Haggar KO
        if self.hp <= 0.0:
            self.hp = 0.0
            self.lives -= 1
            self.state = STATE_HAGGAR_KO
            self.state_timer = 1.5
            return

        # 1. Piledriver Action Update
        if self.is_piledriving:
            self.piledrive_timer -= dt
            if self.piledrive_timer > 0.2:
                # Ascent phase
                self.piledrive_height = min(3.0, self.piledrive_height + 15.0 * dt)
            else:
                # Slam descent phase
                self.piledrive_height = max(0.0, self.piledrive_height - 25.0 * dt)

            if self.piledrive_timer <= 0.0:
                self.is_piledriving = False
                self.piledrive_height = 0.0
                # Impact Slam on grabbed victim!
                if self.grabbed_enemy_idx is not None and self.grabbed_enemy_idx < len(self.enemies):
                    victim = self.enemies[self.grabbed_enemy_idx]
                    victim["hp"] -= 40.0 # Heavy damage
                    victim["state"] = "knockdown"
                    victim["kd_timer"] = 1.0
                    victim["x"] = self.px + self.facing * 0.8
                    victim["y"] = self.py
                    self.score += 1500
                    if victim["hp"] <= 0.0:
                        victim["alive"] = False
                        self.score += 3000 if victim["type"] == "boss" else 1000

                    # Splash shockwave damage to all nearby enemies!
                    for e in self.enemies:
                        if e != victim and e["alive"] and math.hypot(e["x"] - self.px, e["y"] - self.py) < 2.0:
                            e["hp"] -= 15.0
                            e["state"] = "knockdown"
                            e["kd_timer"] = 0.8
                            if e["hp"] <= 0.0:
                                e["alive"] = False

                self.grabbed_enemy_idx = None
            return # Locked in piledriver animation

        # 2. Spinning Clothesline Action Update
        if self.is_spinning:
            self.spin_timer -= dt
            # Knocks down all nearby enemies
            for e in self.enemies:
                if e["alive"] and e["state"] == "normal" and math.hypot(e["x"] - self.px, e["y"] - self.py) < 2.2:
                    e["hp"] -= 18.0
                    e["state"] = "knockdown"
                    e["kd_timer"] = 1.0
                    # Knockback
                    e["x"] += 1.5 if e["x"] > self.px else -1.5
                    self.score += 500
                    if e["hp"] <= 0.0:
                        e["alive"] = False
                        self.score += 3000 if e["type"] == "boss" else 1000

            if self.spin_timer <= 0.0:
                self.is_spinning = False

        # 3. Punch Timer
        if self.is_punching:
            self.punch_timer -= dt
            if self.punch_timer <= 0.0:
                self.is_punching = False

        # 4. Movement (when not locked in action)
        if not self.is_spinning and not self.is_punching:
            dx, dy = 0.0, 0.0
            if keys_down & KEY_LEFT:  dx -= 1.0; self.facing = -1
            if keys_down & KEY_RIGHT: dx += 1.0; self.facing = 1
            if keys_down & KEY_UP:    dy -= 1.0
            if keys_down & KEY_DOWN:  dy += 1.0

            if dx != 0.0 or dy != 0.0:
                inv = 1.0 / math.hypot(dx, dy)
                self.px += dx * inv * self.speed * dt
                self.py += dy * inv * self.speed * dt

            self.px = max(1.0, min(14.5, self.px))
            self.py = max(8.0, min(14.0, self.py)) # 2.5D belt arena

        # 5. Check Grapple Catch (within very close range 0.6)
        if self.grabbed_enemy_idx is None and not self.is_spinning and not self.is_punching:
            for idx, e in enumerate(self.enemies):
                if e["alive"] and e["state"] == "normal" and math.hypot(e["x"] - self.px, e["y"] - self.py) < 0.6:
                    self.grabbed_enemy_idx = idx
                    e["state"] = "grabbed"
                    break

        # 6. Button A: Punch OR Spinning Piledriver (if grabbing)
        if keys_pressed & KEY_A:
            if self.grabbed_enemy_idx is not None:
                # Launch Spinning Piledriver!
                self.is_piledriving = True
                self.piledrive_timer = 0.45
                self.piledrive_height = 0.0
            elif not self.is_punching and not self.is_spinning:
                # Normal 3-Hit Punch
                self.is_punching = True
                self.punch_timer = 0.2
                # Check punch hit
                hit_x = self.px + self.facing * 1.0
                hit_y = self.py
                # Hit enemies
                for e in self.enemies:
                    if e["alive"] and e["state"] == "normal" and math.hypot(e["x"] - hit_x, e["y"] - hit_y) < 1.0:
                        e["hp"] -= 10.0
                        self.score += 200
                        if e["hp"] <= 0.0:
                            e["alive"] = False
                            e["state"] = "knockdown"
                            self.score += 3000 if e["type"] == "boss" else 1000
                        break

                # Punch breakable barrel
                if not self.barrel["broken"] and math.hypot(self.barrel["x"] - hit_x, self.barrel["y"] - hit_y) < 1.2:
                    self.barrel["broken"] = True
                    self.barrel["item_active"] = True
                    self.barrel["item_x"] = self.barrel["x"] + self.facing * 1.5
                    self.barrel["item_y"] = self.barrel["y"]
                    self.score += 300

        # 7. Button B: Desperation Spinning Clothesline (Consumes 8 HP)
        if (keys_pressed & KEY_B) and not self.is_spinning and not self.is_piledriving:
            if self.hp > 8.0:
                self.hp -= 8.0
                self.is_spinning = True
                self.spin_timer = 0.4
                # Release any held grab
                if self.grabbed_enemy_idx is not None:
                    self.enemies[self.grabbed_enemy_idx]["state"] = "normal"
                    self.grabbed_enemy_idx = None
                # Immediate clothesline hit check
                for e in self.enemies:
                    if e["alive"] and e["state"] == "normal" and math.hypot(e["x"] - self.px, e["y"] - self.py) < 2.2:
                        e["hp"] -= 18.0
                        e["state"] = "knockdown"
                        e["kd_timer"] = 1.0
                        e["x"] += 1.5 if e["x"] > self.px else -1.5
                        self.score += 500
                        if e["hp"] <= 0.0:
                            e["alive"] = False
                            self.score += 3000 if e["type"] == "boss" else 1000

        # 8. Collect Roast Chicken Item
        if self.barrel["item_active"]:
            if math.hypot(self.barrel["item_x"] - self.px, self.barrel["item_y"] - self.py) < 0.9:
                self.barrel["item_active"] = False
                self.hp = min(self.max_hp, self.hp + 35.0) # Meat roast chicken health recovery!
                self.score += 1000

        # 9. Update Enemies AI & Knockdown Recovery
        for idx, e in enumerate(self.enemies):
            if not e["alive"]:
                continue

            if e["state"] == "knockdown":
                e["kd_timer"] -= dt
                if e["kd_timer"] <= 0.0:
                    e["state"] = "normal"
                continue

            if e["state"] == "grabbed":
                e["x"] = self.px + self.facing * 0.6
                e["y"] = self.py
                continue

            # Move towards Haggar
            edx = self.px - e["x"]
            edy = self.py - e["y"]
            dist = math.hypot(edx, edy)
            if dist > 0.8:
                e_spd = 2.5 if e["type"] == "thug" else 3.5
                e["x"] += (edx / dist) * e_spd * dt
                e["y"] += (edy / dist) * e_spd * dt
            else:
                # Strike Haggar (unless Haggar is spinning or piledriving!)
                if not self.is_spinning and not self.is_piledriving:
                    self.hp -= 15.0 * dt
                    if self.hp <= 0.0:
                        self.hp = 0.0
                        self.lives -= 1
                        self.state = STATE_HAGGAR_KO
                        self.state_timer = 1.5
                        return

        # Check Boss Defeated
        boss = [e for e in self.enemies if e["type"] == "boss"][0]
        if not boss["alive"]:
            self.state = STATE_STAGE_CLEAR
            self.state_timer = 2.0
            self.score += 10000

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

        # 1. Metro City Slum Street & Brick Wall
        for y in range(16):
            for x in range(16):
                if y <= 7:
                    set_pixel(x, y, 120, 50, 40)   # Red brick graffiti slum wall
                else:
                    set_pixel(x, y, 70, 70, 75)    # Asphalt pavement road

        # 2. Breakable Barrel & Roasted Chicken
        if not self.barrel["broken"]:
            bx, by = int(round(self.barrel["x"])), int(round(self.barrel["y"]))
            set_pixel(bx, by, 140, 80, 30)         # Wooden barrel
            set_pixel(bx, by - 1, 110, 60, 20)
        elif self.barrel["item_active"]:
            ix, iy = int(round(self.barrel["item_x"])), int(round(self.barrel["item_y"]))
            set_pixel(ix, iy, 255, 160, 40)        # Golden roasted chicken!
            set_pixel(ix + 1, iy, 255, 230, 180)   # Bone

        # 3. Enemies
        for e in self.enemies:
            if e["alive"]:
                ex, ey = int(round(e["x"])), int(round(e["y"]))
                if e["state"] == "knockdown":
                    set_pixel(ex, ey, 100, 100, 100) # Lying prone on road
                elif e["type"] == "boss":
                    # Damnd (Mad Gear Lieutenant with dreadlocks)
                    set_pixel(ex, ey, 240, 40, 40)       # Red jacket
                    set_pixel(ex, ey - 1, 230, 210, 50)  # Yellow dreadlocks
                    set_pixel(ex, ey + 1, 40, 40, 120)   # Blue jeans
                else: # Mad Gear Thug
                    set_pixel(ex, ey, 220, 140, 40)      # Orange shirt
                    set_pixel(ex, ey - 1, 220, 180, 140) # Bandana
                    set_pixel(ex, ey + 1, 50, 90, 50)    # Green pants

        # 4. Mayor Mike Haggar
        hx = int(round(self.px))
        hy = int(round(self.py - self.piledrive_height))

        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.is_spinning:
                # Spinning clothesline whirlwind
                set_pixel(hx, hy, 160, 100, 50)          # Torso
                set_pixel(hx - 1, hy, 255, 255, 100)     # Extended fist whirl
                set_pixel(hx + 1, hy, 255, 255, 100)
                set_pixel(hx, hy - 1, 60, 40, 20)        # Mustache head
            elif self.is_piledriving:
                # Aerial corkscrew slam
                set_pixel(hx, hy, 160, 100, 50)
                set_pixel(hx, hy - 1, 160, 100, 50)
                set_pixel(hx, hy + 1, 200, 160, 40)      # Victim upside down!
            else:
                set_pixel(hx, hy, 180, 120, 70)          # Bare muscular chest & strap
                set_pixel(hx, hy - 1, 90, 60, 30)        # Mustache head
                set_pixel(hx, hy + 1, 40, 90, 40)        # Olive green wrestler trousers
                if self.is_punching:
                    set_pixel(hx + self.facing, hy, 255, 220, 80) # Fist jab
        elif self.state == STATE_HAGGAR_KO:
            set_pixel(hx, hy, 255, 50, 0)

        # 5. Health Bar at top row (y = 0)
        hp_pixels = int(round((self.hp / self.max_hp) * 14.0))
        for x in range(hp_pixels):
            set_pixel(x + 1, 0, 40, 220, 40) # Green health bar

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
            "hp": self.hp,
            "px": self.px,
            "py": self.py,
            "is_spinning": self.is_spinning,
            "is_piledriving": self.is_piledriving,
            "barrel_broken": self.barrel["broken"],
        }
