"""
Game #162: 翻滚战机1942 (1942 - 1984 Capcom / Yoshiki Okamoto)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Capcom's 1984 masterpiece '1942' set the definitive blueprint for WWII vertical scrolling shooters.
Piloting the legendary Lockheed P-38 Lightning over the Pacific, it introduced the historic
'Loop-the-Loop' (空中大回旋) emergency evasion maneuver and side-wing escort fighters.

Unique Mechanic (Strict Zero-Redundancy):
- Loop-the-Loop Evasion (Button B): 3 emergency rolls per life granting full invulnerability.
- Escort Wingmen Synergy: Twin auxiliary fighters attach to flanks, tripling firepower and acting as shields.
- Red Formation Interception: Eliminating an entire red squadron spawns a POW upgrade.
- Heavy Super Bomber Clashes: Pacific fleet mega-bombers requiring concentrated tactical firepower.
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
STATE_PLAYER_EXPLODING = 2
STATE_GAME_OVER = 3

class Game162Roll1942(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0

        # Player P-38 state
        self.px = 8.0
        self.py = 13.0
        self.speed = 6.0
        self.loops_left = 3
        self.is_looping = False
        self.loop_timer = 0.0
        self.loop_duration = 0.8
        self.has_wingmen = False
        self.fire_cooldown = 0.0

        # Bullets: list of {x, y, vy, active}
        self.player_bullets: List[Dict[str, float]] = []
        self.enemy_bullets: List[Dict[str, float]] = []

        # Enemies: list of {id, x, y, vx, vy, hp, is_red, is_boss, active}
        self.enemies: List[Dict[str, Any]] = []
        self.enemy_spawn_timer = 0.5
        self.red_squadron_count = 0
        self.red_squadron_killed = 0

        # POW items: list of {x, y, vy, type}
        self.pow_items: List[Dict[str, float]] = []

        # Boss
        self.boss_active = False
        self.boss_hp = 0

        self.init()

    @property
    def game_id(self) -> int:
        return 162

    @property
    def name(self) -> str:
        return "翻滚战机1942"

    @property
    def english_name(self) -> str:
        return "1942"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "空中大回旋特技绝对无敌闪避、双联装双翼僚机合体与三联弹幕、全歼红色编队夺取POW"

    def get_name(self) -> str:
        return "1942 (1984)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.stage = 1
        self.state_timer = 0.0
        self._respawn_player()
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.enemies.clear()
        self.pow_items.clear()
        self.enemy_spawn_timer = 0.5
        self.boss_active = False

    def _respawn_player(self):
        self.px = 8.0
        self.py = 13.0
        self.loops_left = 3
        self.is_looping = False
        self.loop_timer = 0.0
        self.has_wingmen = False
        self.fire_cooldown = 0.0

    def trigger_loop_the_loop(self):
        """Button B: Aerial Loop-the-loop maneuver."""
        if self.loops_left > 0 and not self.is_looping and self.state == STATE_PLAYING:
            self.loops_left -= 1
            self.is_looping = True
            self.loop_timer = self.loop_duration
            self.score += 50

    def fire_cannons(self):
        """Button A: Fire P-38 heavy nose cannons (+ wingmen cannons if active)."""
        if self.fire_cooldown > 0.0 or self.is_looping or self.state != STATE_PLAYING:
            return

        # Center gun
        self.player_bullets.append({"x": self.px, "y": self.py - 0.8, "vy": -14.0})

        # Wingmen guns
        if self.has_wingmen:
            self.player_bullets.append({"x": self.px - 1.5, "y": self.py - 0.4, "vy": -14.0})
            self.player_bullets.append({"x": self.px + 1.5, "y": self.py - 0.4, "vy": -14.0})

        self.fire_cooldown = 0.18

    def spawn_red_formation(self):
        """Spawn a squadron of 4 red scout planes."""
        for i in range(4):
            self.enemies.append({
                "id": len(self.enemies) + i,
                "x": 3.0 + i * 3.0,
                "y": 1.0 + i * 1.2,
                "vx": 0.0,
                "vy": 3.0,
                "hp": 1,
                "is_red": True,
                "is_boss": False,
                "active": True
            })
        self.red_squadron_count = 4
        self.red_squadron_killed = 0

    def spawn_boss(self):
        """Spawn Pacific Fleet Mega-Bomber Ayako."""
        self.boss_active = True
        self.boss_hp = 12
        self.enemies.append({
            "id": 999,
            "x": 8.0,
            "y": 1.0,
            "vx": 1.5,
            "vy": 0.3,
            "hp": self.boss_hp,
            "is_red": False,
            "is_boss": True,
            "active": True
        })

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.stage += 1
                self.state = STATE_PLAYING
                self.enemies.clear()
                self.enemy_bullets.clear()
            return

        if self.state == STATE_PLAYER_EXPLODING:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self._respawn_player()
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        # Cooldowns & Timers
        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        if self.is_looping:
            self.loop_timer -= dt
            if self.loop_timer <= 0.0:
                self.is_looping = False

        # Player Movement
        if not self.is_looping:
            dx, dy = 0.0, 0.0
            if keys_down & KEY_LEFT:  dx -= 1.0
            if keys_down & KEY_RIGHT: dx += 1.0
            if keys_down & KEY_UP:    dy -= 1.0
            if keys_down & KEY_DOWN:  dy += 1.0

            if dx != 0.0 or dy != 0.0:
                length = math.hypot(dx, dy)
                self.px += (dx / length) * self.speed * dt
                self.py += (dy / length) * self.speed * dt

            self.px = max(1.5, min(14.5, self.px))
            self.py = max(2.0, min(14.5, self.py))

        # Action Keys
        if keys_pressed & KEY_A:
            self.fire_cannons()
        if keys_pressed & KEY_B:
            self.trigger_loop_the_loop()

        # Update Player Bullets
        for b in list(self.player_bullets):
            b["y"] += b["vy"] * dt
            if b["y"] < -1.0:
                self.player_bullets.remove(b)
                continue

            # Hit enemies
            for e in self.enemies:
                if e["active"] and math.hypot(e["x"] - b["x"], e["y"] - b["y"]) < (1.8 if e["is_boss"] else 1.1):
                    e["hp"] -= 1
                    if b in self.player_bullets:
                        self.player_bullets.remove(b)

                    if e["hp"] <= 0:
                        e["active"] = False
                        self.score += 500 if e["is_boss"] else 100
                        if e["is_red"]:
                            self.red_squadron_killed += 1
                            if self.red_squadron_killed >= self.red_squadron_count:
                                # Full red squadron wiped out: spawn POW item!
                                self.pow_items.append({"x": e["x"], "y": e["y"], "vy": 1.5})
                                self.score += 1000
                        if e["is_boss"]:
                            self.boss_active = False
                            self.state = STATE_STAGE_CLEAR
                            self.state_timer = 2.0
                            self.score += 3000
                    break

        # Update Enemy Bullets
        for eb in list(self.enemy_bullets):
            eb["y"] += eb["vy"] * dt
            if eb["y"] > 16.0:
                self.enemy_bullets.remove(eb)
                continue

            # Check hit player
            if not self.is_looping and math.hypot(eb["x"] - self.px, eb["y"] - self.py) < 0.9:
                self.enemy_bullets.remove(eb)
                if self.has_wingmen:
                    self.has_wingmen = False # Wingman sacrificed!
                else:
                    self.lives -= 1
                    self.state = STATE_PLAYER_EXPLODING
                    self.state_timer = 1.0
                    return

        # Update POW Items
        for pow_item in list(self.pow_items):
            pow_item["y"] += pow_item["vy"] * dt
            if pow_item["y"] > 16.0:
                self.pow_items.remove(pow_item)
                continue

            if math.hypot(pow_item["x"] - self.px, pow_item["y"] - self.py) < 1.2:
                self.pow_items.remove(pow_item)
                self.has_wingmen = True
                self.loops_left = min(3, self.loops_left + 1)
                self.score += 500

        # Spawn Regular & Red Enemies
        if not self.boss_active:
            self.enemy_spawn_timer -= dt
            if self.enemy_spawn_timer <= 0.0:
                # Random regular or red formation
                if len(self.enemies) == 0 and self.stage % 2 == 1:
                    self.spawn_red_formation()
                    self.enemy_spawn_timer = 4.0
                elif len(self.enemies) == 0 and self.stage % 2 == 0:
                    self.spawn_boss()
                    self.enemy_spawn_timer = 10.0
                else:
                    # Single scout plane
                    self.enemies.append({
                        "id": len(self.enemies),
                        "x": 2.0 + (len(self.enemies) * 4.0) % 12.0,
                        "y": 0.0,
                        "vx": 0.0,
                        "vy": 3.2,
                        "hp": 1,
                        "is_red": False,
                        "is_boss": False,
                        "active": True
                    })
                    self.enemy_spawn_timer = 1.2

        # Update Enemies
        for e in list(self.enemies):
            if not e["active"]:
                self.enemies.remove(e)
                continue

            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt

            if e["is_boss"]:
                if e["x"] <= 3.0 or e["x"] >= 13.0:
                    e["vx"] = -e["vx"]
                # Boss periodic fire
                if int(e["y"] * 10) % 25 == 0:
                    self.enemy_bullets.append({"x": e["x"], "y": e["y"] + 1.2, "vy": 5.0})
            else:
                if e["y"] > 16.5:
                    self.enemies.remove(e)
                    continue

            # Collision with player plane
            if not self.is_looping and math.hypot(e["x"] - self.px, e["y"] - self.py) < 1.0:
                e["active"] = False
                if self.has_wingmen:
                    self.has_wingmen = False
                else:
                    self.lives -= 1
                    self.state = STATE_PLAYER_EXPLODING
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

        # 1. Background Ocean Waves (subtle deep blue with occasional crests)
        for y in range(16):
            for x in range(16):
                if (x + y * 3) % 19 == 0:
                    set_pixel(x, y, 10, 40, 110)

        # 2. POW Items
        for p in self.pow_items:
            px, py = int(round(p["x"])), int(round(p["y"]))
            set_pixel(px, py, 255, 120, 0)
            set_pixel(px, py - 1, 255, 220, 0)

        # 3. Enemies
        for e in self.enemies:
            if e["active"]:
                ex, ey = int(round(e["x"])), int(round(e["y"]))
                if e["is_boss"]:
                    # Large Mega-Bomber Ayako (3x2 body)
                    for bx in range(-2, 3):
                        set_pixel(ex + bx, ey, 90, 110, 90)
                        set_pixel(ex + bx, ey - 1, 120, 140, 120)
                elif e["is_red"]:
                    set_pixel(ex, ey, 255, 30, 30)
                else:
                    set_pixel(ex, ey, 140, 150, 160)

        # 4. Enemy Bullets
        for eb in self.enemy_bullets:
            bx, by = int(round(eb["x"])), int(round(eb["y"]))
            set_pixel(bx, by, 255, 60, 60)

        # 5. Player Bullets
        for b in self.player_bullets:
            bx, by = int(round(b["x"])), int(round(b["y"]))
            set_pixel(bx, by, 255, 255, 100)

        # 6. P-38 Lightning Fighter
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.is_looping:
                # Inverted golden flash during barrel loop
                set_pixel(px, py, 255, 255, 255)
                set_pixel(px - 1, py, 255, 215, 0)
                set_pixel(px + 1, py, 255, 215, 0)
            else:
                # Normal P-38 twin-boom silver body
                set_pixel(px, py, 0, 220, 255)
                set_pixel(px, py - 1, 240, 240, 240) # Nose
                set_pixel(px - 1, py, 0, 150, 220)  # Left wing
                set_pixel(px + 1, py, 0, 150, 220)  # Right wing

                # Wingmen escort fighters
                if self.has_wingmen:
                    set_pixel(px - 2, py + 1, 0, 255, 140)
                    set_pixel(px + 2, py + 1, 0, 255, 140)

        elif self.state == STATE_PLAYER_EXPLODING:
            set_pixel(px, py, 255, 80, 0)
            set_pixel(px - 1, py, 255, 200, 0)
            set_pixel(px + 1, py, 255, 200, 0)

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
            "loops_left": self.loops_left,
            "is_looping": self.is_looping,
            "has_wingmen": self.has_wingmen,
            "px": self.px,
            "py": self.py,
        }
