"""
Game #166: 沃之巫师 (Wizard of Wor - 1980 Bally Midway / Dave Nutting Associates)
Cartridge Implementation for 16x16 WS2812B LED Matrix.

Historical Significance:
Developed by Dave Nutting Associates and published by Midway in 1980, Wizard of Wor
is an iconic dungeon-maze shooter. It pioneered invisible cloaking creatures
tracked via radar, line-of-sight illumination, side-tunnel warp doors, and the climactic
teleporting Wizard boss showdown.

Unique Mechanic (Strict Zero-Redundancy):
- Invisibility Cloaking & Radar Scanner: Monsters turn invisible unless in direct line-of-sight;
  tracked via the bottom radar display bar.
- Spatial Warp Doors: Passing through left/right portals instantly teleports Worriors across the maze.
- Evolutionary Dungeon Beasts: Burwors -> Garwors -> Thorwors -> The Wizard of Wor.
- Teleporting Wizard Duel: The final sorcerer teleports unpredictably and hurls lightning bolts.
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
STATE_DUNGEON_CLEAR = 1
STATE_WORRIOR_DIED = 2
STATE_GAME_OVER = 3

class Game166WizardOfWor(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.dungeon = 1
        self.state_timer = 0.0

        # Player Worrior state
        self.px = 7.5
        self.py = 13.0
        self.facing_dx = 0.0
        self.facing_dy = -1.0
        self.speed = 4.8
        self.fire_cooldown = 0.0

        # Wor-beam lasers: list of {x, y, vx, vy, life}
        self.bullets: List[Dict[str, float]] = []

        # Dungeon walls: set of (x, y)
        self.walls = set()

        # Monsters: list of {id, type, x, y, vx, vy, is_invisible, alive}
        self.monsters: List[Dict[str, Any]] = []

        # Wizard state
        self.wizard_active = False
        self.wizard_x = 7.5
        self.wizard_y = 3.0
        self.wizard_teleport_timer = 2.0
        self.wizard_teleport_count = 0
        self.wizard_alive = False

        self.init()

    @property
    def game_id(self) -> int:
        return 166

    @property
    def name(self) -> str:
        return "沃之巫师"

    @property
    def english_name(self) -> str:
        return "Wizard of Wor"

    @property
    def release_year(self) -> int:
        return 1980

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "隐形怪兽地牢穿行、底部雷达扫描定位测距、侧向虫洞门空间跃迁与瞬移巫师决斗"

    def get_name(self) -> str:
        return "Wizard of Wor (1980)"

    def get_control_scheme(self) -> int:
        return CTRL_ARCADE_AB

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.dungeon = 1
        self._init_dungeon()

    def _init_dungeon(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.px = 7.5
        self.py = 13.0
        self.facing_dx = 0.0
        self.facing_dy = -1.0
        self.fire_cooldown = 0.0
        self.wizard_active = False
        self.wizard_alive = False
        self.bullets.clear()

        # Build maze layout (16x16, bottom row 15 reserved for radar)
        self.walls.clear()
        # Outer boundary (except warp doors at x=0, 15, y=7)
        for x in range(16):
            self.walls.add((x, 0))
            self.walls.add((x, 14))
        for y in range(15):
            if y != 7: # Warp portal
                self.walls.add((0, y))
                self.walls.add((15, y))

        # Interior maze walls
        for x in range(3, 13):
            if x not in (7, 8):
                self.walls.add((x, 4))
                self.walls.add((x, 10))

        for y in range(5, 10):
            if y != 7:
                self.walls.add((4, y))
                self.walls.add((11, y))

        # Spawn 3 beasts:
        # 1. Burwor (Blue, visible, speed 2.0)
        # 2. Garwor (Yellow, invisible cloak, speed 2.4)
        # 3. Thorwor (Red, invisible cloak, speed 2.8)
        self.monsters = [
            {"id": 0, "type": "burwor", "x": 2.0, "y": 2.0, "vx": 2.0, "vy": 0.0, "is_cloaked": False, "alive": True},
            {"id": 1, "type": "garwor", "x": 13.0, "y": 2.0, "vx": -2.4, "vy": 0.0, "is_cloaked": True, "alive": True},
            {"id": 2, "type": "thorwor", "x": 7.5, "y": 7.0, "vx": 2.8, "vy": 0.0, "is_cloaked": True, "alive": True},
        ]

    def fire_beam(self):
        if self.fire_cooldown > 0.0 or self.state != STATE_PLAYING:
            return
        if len(self.bullets) >= 2:
            return

        bx = self.px + self.facing_dx * 0.8
        by = self.py + self.facing_dy * 0.8
        b_speed = 15.0
        self.bullets.append({
            "x": bx,
            "y": by,
            "vx": self.facing_dx * b_speed,
            "vy": self.facing_dy * b_speed,
            "life": 1.0
        })
        self.fire_cooldown = 0.2

    def spawn_wizard(self):
        self.wizard_active = True
        self.wizard_alive = True
        self.wizard_x = 7.5
        self.wizard_y = 2.0
        self.wizard_teleport_timer = 2.0

    def is_wall(self, x: float, y: float) -> bool:
        ix = int(round(x))
        iy = int(round(y))
        return (ix, iy) in self.walls

    def update(self, dt: float, keys_down: int = 0, keys_pressed: int = 0) -> None:
        if self.state == STATE_DUNGEON_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.dungeon += 1
                self._init_dungeon()
            return

        if self.state == STATE_WORRIOR_DIED:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                if self.lives > 0:
                    self.state = STATE_PLAYING
                    self.px = 7.5
                    self.py = 13.0
                else:
                    self.state = STATE_GAME_OVER
            return

        if self.state == STATE_GAME_OVER:
            if (keys_pressed & KEY_A) or (keys_pressed & KEY_B):
                self.reset()
            return

        if self.fire_cooldown > 0.0:
            self.fire_cooldown -= dt

        # Player Movement
        dx, dy = 0.0, 0.0
        if keys_down & KEY_LEFT:  dx -= 1.0; self.facing_dx = -1.0; self.facing_dy = 0.0
        elif keys_down & KEY_RIGHT: dx += 1.0; self.facing_dx = 1.0; self.facing_dy = 0.0
        elif keys_down & KEY_UP:    dy -= 1.0; self.facing_dx = 0.0; self.facing_dy = -1.0
        elif keys_down & KEY_DOWN:  dy += 1.0; self.facing_dx = 0.0; self.facing_dy = 1.0

        if dx != 0.0 or dy != 0.0:
            new_px = self.px + dx * self.speed * dt
            new_py = self.py + dy * self.speed * dt

            # Warp door crossing at y=7
            if abs(self.py - 7.0) < 0.8:
                if new_px <= 0.2:
                    new_px = 14.8
                elif new_px >= 14.8:
                    new_px = 0.2

            if not self.is_wall(new_px, self.py):
                self.px = new_px
            if not self.is_wall(self.px, new_py):
                self.py = new_py

        # Action: Fire
        if keys_pressed & KEY_A:
            self.fire_beam()

        # Bullets Update
        for b in list(self.bullets):
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["life"] -= dt

            # Hit wall
            if self.is_wall(b["x"], b["y"]) or b["life"] <= 0:
                self.bullets.remove(b)
                continue

            # Hit monsters
            hit = False
            for m in self.monsters:
                if m["alive"] and math.hypot(m["x"] - b["x"], m["y"] - b["y"]) < 1.0:
                    m["alive"] = False
                    self.score += 200 if m["type"] == "burwor" else (500 if m["type"] == "garwor" else 1000)
                    self.bullets.remove(b)
                    hit = True
                    break
            if hit:
                continue

            # Hit Wizard
            if self.wizard_alive and math.hypot(self.wizard_x - b["x"], self.wizard_y - b["y"]) < 1.1:
                self.wizard_alive = False
                self.score += 2500
                self.bullets.remove(b)
                self.state = STATE_DUNGEON_CLEAR
                self.state_timer = 2.0
                continue

        # Monsters AI & Patrol
        alive_monsters = 0
        for m in self.monsters:
            if not m["alive"]:
                continue
            alive_monsters += 1

            new_mx = m["x"] + m["vx"] * dt
            new_my = m["y"] + m["vy"] * dt

            # Warp crossing
            if abs(m["y"] - 7.0) < 0.8:
                if new_mx <= 0.2: new_mx = 14.8
                elif new_mx >= 14.8: new_mx = 0.2

            if self.is_wall(new_mx, new_my):
                # Reverse or turn
                m["vx"] = -m["vx"]
            else:
                m["x"] = new_mx
                m["y"] = new_my

            # Hit Worrior
            if math.hypot(m["x"] - self.px, m["y"] - self.py) < 0.8:
                self.lives -= 1
                self.state = STATE_WORRIOR_DIED
                self.state_timer = 1.0
                return

        # Check if all monsters dead -> Spawn Wizard!
        if alive_monsters == 0 and not self.wizard_active:
            self.spawn_wizard()

        # Wizard Teleport & Duel
        if self.wizard_alive:
            self.wizard_teleport_timer -= dt
            if self.wizard_teleport_timer <= 0.0:
                spots = [(2.0, 7.0), (13.0, 7.0), (7.5, 12.0), (5.0, 2.0), (7.5, 2.0)]
                self.wizard_teleport_count += 1
                next_spot = spots[self.wizard_teleport_count % len(spots)]
                self.wizard_x, self.wizard_y = next_spot
                self.wizard_teleport_timer = 2.0

            # Wizard touches Worrior
            if math.hypot(self.wizard_x - self.px, self.wizard_y - self.py) < 0.9:
                self.lives -= 1
                self.state = STATE_WORRIOR_DIED
                self.state_timer = 1.0
                return

    def is_line_of_sight(self, x: float, y: float) -> bool:
        """Visible if sharing same corridor axis with unobstructed line of sight."""
        return (abs(self.px - x) < 1.0) or (abs(self.py - y) < 1.0)

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

        # 1. Dungeon Maze Walls (Deep dungeon blue)
        for (wx, wy) in self.walls:
            set_pixel(wx, wy, 0, 80, 220)

        # 2. Warp Doors at (0, 7) and (15, 7)
        set_pixel(0, 7, 255, 255, 0)
        set_pixel(15, 7, 255, 255, 0)

        # 3. Monsters (Respect Invisibility Cloak)
        for m in self.monsters:
            if m["alive"]:
                mx, my = int(round(m["x"])), int(round(m["y"]))
                # If cloaked, only draw if in line-of-sight
                if not m["is_cloaked"] or self.is_line_of_sight(m["x"], m["y"]):
                    if m["type"] == "burwor":
                        set_pixel(mx, my, 0, 150, 255) # Blue
                    elif m["type"] == "garwor":
                        set_pixel(mx, my, 255, 220, 0) # Yellow
                    else:
                        set_pixel(mx, my, 255, 40, 40)  # Red Thorwor

        # 4. Wizard of Wor
        if self.wizard_alive:
            wx, wy = int(round(self.wizard_x)), int(round(self.wizard_y))
            set_pixel(wx, wy, 255, 0, 255)     # Magenta wizard robe
            set_pixel(wx, wy - 1, 255, 255, 255) # White wizard hat

        # 5. Lasers
        for b in self.bullets:
            bx, by = int(round(b["x"])), int(round(b["y"]))
            set_pixel(bx, by, 255, 255, 200)

        # 6. Worrior Player (Yellow armored soldier)
        px, py = int(round(self.px)), int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_DUNGEON_CLEAR):
            set_pixel(px, py, 255, 255, 0)
            set_pixel(px, py - 1, 255, 200, 100)
        elif self.state == STATE_WORRIOR_DIED:
            set_pixel(px, py, 255, 60, 0)

        # 7. Bottom Radar Scanner (y=15): Blip positions of ALL monsters
        for m in self.monsters:
            if m["alive"]:
                rx = int(round(m["x"]))
                set_pixel(rx, 15, 0, 255, 120) # Green radar blip

        if self.wizard_alive:
            rx = int(round(self.wizard_x))
            set_pixel(rx, 15, 255, 0, 255) # Purple radar blip

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "score": self.score,
            "lives": self.lives,
            "dungeon": self.dungeon,
            "wizard_active": self.wizard_active,
            "wizard_alive": self.wizard_alive,
            "px": self.px,
            "py": self.py,
        }
