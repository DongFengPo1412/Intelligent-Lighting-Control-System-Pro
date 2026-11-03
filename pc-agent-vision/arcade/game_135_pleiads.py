# -*- coding: utf-8 -*-
"""
Game #135: 疯狂小蜜蜂 (Pleiads 1981 / Tehkan)
街机历史上第一部具备三阶段递进战役与战舰泊机跑道的传奇射击游戏：
阶段一雷达屏障对垒、阶段二不死飞鸟俯冲截击、阶段三母舰核心轰破与航空跑道精准迫降。
按键A双联激光炮，按键B能量防护盾（每局限次）。
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
STATE_SHIP_HIT = 2
STATE_GAME_OVER = 3

PHASE_RADAR = 0
PHASE_BIRDS = 1
PHASE_LANDING = 2


class Game135Pleiads(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.phase = PHASE_RADAR
        self.px = 7.5
        self.py = 14.0
        self.shields_left = 3
        self.shield_active = False
        self.shield_timer = 0.0

        # Player bullets (max 2)
        self.bullets: List[Dict[str, Any]] = []

        # Alien enemies
        self.enemies: List[Dict[str, Any]] = []

        # Enemy bullets
        self.enemy_bullets: List[Dict[str, Any]] = []

        # Radar barriers (Phase 0)
        self.radar_barriers: List[Dict[str, Any]] = []

        # Mothership (Phase 2)
        self.mothership_hp = 3
        self.mothership_x = 7.5
        self.mothership_dir = 1.0
        self.mothership_destroyed = False

        self.reset()

    @property
    def game_id(self) -> int:
        return 135

    @property
    def name(self) -> str:
        return "疯狂小蜜蜂"

    @property
    def english_name(self) -> str:
        return "Pleiads"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "三阶段递进战役：雷达屏障战、幻影飞鸟弧线俯冲、母舰核心爆破与航母跑道迫降"

    def get_name(self) -> str:
        return "Pleiads (1981)"

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
        self.phase = PHASE_RADAR
        self.px = 7.5
        self.py = 14.0
        self.shields_left = 3
        self.shield_active = False
        self.shield_timer = 0.0

        self.bullets = []
        self.enemy_bullets = []
        self._init_phase_0()

    def _init_phase_0(self) -> None:
        self.phase = PHASE_RADAR
        self.enemies = []
        for i in range(4):
            self.enemies.append({
                "x": 2.5 + i * 3.5,
                "y": 3.0,
                "vx": 2.5,
                "alive": True,
                "shoot_timer": 1.2 + i * 0.5,
            })
        self.radar_barriers = [
            {"x": 3.0, "y": 9.0, "hp": 2},
            {"x": 6.5, "y": 9.0, "hp": 2},
            {"x": 10.0, "y": 9.0, "hp": 2},
            {"x": 13.5, "y": 9.0, "hp": 2},
        ]

    def _init_phase_1(self) -> None:
        self.phase = PHASE_BIRDS
        self.enemies = []
        for i in range(4):
            self.enemies.append({
                "x": 3.0 + i * 3.0,
                "y": 2.0,
                "base_x": 3.0 + i * 3.0,
                "swoop_timer": i * 0.7,
                "is_swooping": False,
                "alive": True,
                "shoot_timer": 1.5 + i * 0.6,
            })

    def _init_phase_2(self) -> None:
        self.phase = PHASE_LANDING
        self.mothership_hp = 3
        self.mothership_x = 7.5
        self.mothership_dir = 1.0
        self.mothership_destroyed = False
        self.enemies = []

    def update(self, dt: float, buttons: int, prev_buttons: int) -> None:
        if self.state == STATE_PLAYING:
            self._update_playing(dt, buttons, prev_buttons)
        elif self.state in (STATE_STAGE_CLEAR, STATE_SHIP_HIT):
            self.state_timer += dt
            if self.state_timer >= 1.5:
                if self.state == STATE_STAGE_CLEAR:
                    self.level += 1
                    self._init_level()
                elif self.state == STATE_SHIP_HIT:
                    if self.lives > 0:
                        self.px = 7.5
                        self.py = 14.0
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
        # 1. Shield handling (Key B)
        if (buttons & KEY_B) and not (prev_buttons & KEY_B):
            if self.shields_left > 0 and not self.shield_active:
                self.shield_active = True
                self.shield_timer = 1.5
                self.shields_left -= 1

        if self.shield_active:
            self.shield_timer -= dt
            if self.shield_timer <= 0.0:
                self.shield_active = False
                self.shield_timer = 0.0

        # 2. Movement
        move_speed = 8.0
        if buttons & KEY_LEFT:
            self.px = max(1.0, self.px - move_speed * dt)
        if buttons & KEY_RIGHT:
            self.px = min(14.0, self.px + move_speed * dt)

        # In Phase 2 after mothership destruction, vertical control enabled for landing
        if self.phase == PHASE_LANDING and self.mothership_destroyed:
            if buttons & KEY_UP:
                self.py = max(1.0, self.py - move_speed * 0.8 * dt)
            if buttons & KEY_DOWN:
                self.py = min(14.0, self.py + move_speed * 0.8 * dt)

            # Check successful landing on runway
            if self.py <= 2.2:
                # Landing strip is centered between 5.0 and 10.0
                if 5.0 <= self.px <= 10.0:
                    self.score += 500
                    self.state = STATE_STAGE_CLEAR
                    self.state_timer = 0.0
                    return
                else:
                    # Crashed outside runway beacons!
                    self._lose_life()
                    return

        # 3. Fire Laser (Key A)
        if (buttons & KEY_A) and not (prev_buttons & KEY_A):
            if not (self.phase == PHASE_LANDING and self.mothership_destroyed):
                if len(self.bullets) < 2:
                    self.bullets.append({"x": self.px, "y": self.py - 1.0, "active": True})

        # 4. Update Player Bullets
        for b in self.bullets:
            if b["active"]:
                b["y"] -= 16.0 * dt
                if b["y"] < 0.0:
                    b["active"] = False

                # Phase 0: Check radar barrier collisions
                if self.phase == PHASE_RADAR:
                    for barrier in self.radar_barriers:
                        if barrier["hp"] > 0:
                            if abs(b["x"] - barrier["x"]) < 1.0 and abs(b["y"] - barrier["y"]) < 0.8:
                                barrier["hp"] -= 1
                                b["active"] = False
                                break

                # Check enemy collisions
                if self.phase in (PHASE_RADAR, PHASE_BIRDS):
                    for enemy in self.enemies:
                        if enemy["alive"]:
                            if abs(b["x"] - enemy["x"]) < 1.0 and abs(b["y"] - enemy["y"]) < 1.0:
                                enemy["alive"] = False
                                b["active"] = False
                                self.score += 100
                                break

                # Phase 2: Check mothership collision
                if self.phase == PHASE_LANDING and not self.mothership_destroyed:
                    if abs(b["x"] - self.mothership_x) < 2.0 and b["y"] <= 3.0:
                        b["active"] = False
                        self.mothership_hp -= 1
                        if self.mothership_hp <= 0:
                            self.mothership_destroyed = True
                            self.score += 600
                        break

        self.bullets = [b for b in self.bullets if b["active"]]

        # 5. Phase-specific enemy logic
        if self.phase == PHASE_RADAR:
            alive_count = 0
            for enemy in self.enemies:
                if enemy["alive"]:
                    alive_count += 1
                    enemy["x"] += enemy["vx"] * dt
                    if enemy["x"] <= 1.5 or enemy["x"] >= 13.5:
                        enemy["vx"] = -enemy["vx"]

                    enemy["shoot_timer"] -= dt
                    if enemy["shoot_timer"] <= 0.0:
                        enemy["shoot_timer"] = 2.0
                        if len(self.enemy_bullets) < 4:
                            self.enemy_bullets.append({"x": enemy["x"], "y": enemy["y"] + 0.5, "active": True})
            if alive_count == 0:
                self.score += 300
                self._init_phase_1()

        elif self.phase == PHASE_BIRDS:
            alive_count = 0
            for enemy in self.enemies:
                if enemy["alive"]:
                    alive_count += 1
                    enemy["swoop_timer"] += dt
                    # Swooping sine pattern
                    if enemy["swoop_timer"] > 1.5:
                        enemy["y"] += 4.5 * dt
                        enemy["x"] = enemy["base_x"] + math.sin(enemy["y"] * 1.5) * 3.0
                        if enemy["y"] >= 15.0:
                            enemy["y"] = 2.0
                            enemy["swoop_timer"] = 0.0
                    else:
                        enemy["x"] = enemy["base_x"]

                    enemy["shoot_timer"] -= dt
                    if enemy["shoot_timer"] <= 0.0:
                        enemy["shoot_timer"] = 2.2
                        if len(self.enemy_bullets) < 4:
                            self.enemy_bullets.append({"x": enemy["x"], "y": enemy["y"] + 0.5, "active": True})

                    # Direct collision with player
                    if abs(enemy["x"] - self.px) < 1.0 and abs(enemy["y"] - self.py) < 1.0:
                        if not self.shield_active:
                            self._lose_life()
                            return
            if alive_count == 0:
                self.score += 400
                self._init_phase_2()

        elif self.phase == PHASE_LANDING:
            if not self.mothership_destroyed:
                self.mothership_x += self.mothership_dir * 3.5 * dt
                if self.mothership_x <= 3.0:
                    self.mothership_x = 3.0
                    self.mothership_dir = 1.0
                elif self.mothership_x >= 12.0:
                    self.mothership_x = 12.0
                    self.mothership_dir = -1.0

                if len(self.enemy_bullets) < 2 and int(self.mothership_x * 10) % 20 == 0:
                    self.enemy_bullets.append({"x": self.mothership_x, "y": 3.0, "active": True})

        # 6. Enemy bullets update
        for eb in self.enemy_bullets:
            if eb["active"]:
                eb["y"] += 6.5 * dt
                if eb["y"] >= 15.5:
                    eb["active"] = False

                # Barrier block in phase 0
                if self.phase == PHASE_RADAR:
                    for barrier in self.radar_barriers:
                        if barrier["hp"] > 0:
                            if abs(eb["x"] - barrier["x"]) < 1.0 and abs(eb["y"] - barrier["y"]) < 0.8:
                                eb["active"] = False
                                break

                # Player collision
                if abs(eb["x"] - self.px) < 0.9 and abs(eb["y"] - self.py) < 0.9:
                    eb["active"] = False
                    if not self.shield_active:
                        self._lose_life()
                        return

        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb["active"]]

    def _lose_life(self) -> None:
        self.lives -= 1
        self.state = STATE_SHIP_HIT
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

        # Phase 0: Render Radar Barriers
        if self.phase == PHASE_RADAR:
            for bar in self.radar_barriers:
                if bar["hp"] > 0:
                    bx = int(round(bar["x"]))
                    by = int(round(bar["y"]))
                    c = 220 if bar["hp"] == 2 else 120
                    set_pixel(bx, by, 30, c, 220)
                    set_pixel(bx - 1, by, 20, c // 2, 160)

        # Render Enemies
        for enemy in self.enemies:
            if enemy["alive"]:
                ex = int(round(enemy["x"]))
                ey = int(round(enemy["y"]))
                if self.phase == PHASE_RADAR:
                    # Alien radar pod (Yellow/Green)
                    set_pixel(ex, ey, 220, 200, 30)
                    set_pixel(ex, ey - 1, 180, 140, 20)
                elif self.phase == PHASE_BIRDS:
                    # Phoenix Bird (Cyan/Pink)
                    set_pixel(ex, ey, 255, 60, 160)
                    set_pixel(ex - 1, ey, 60, 220, 255)
                    set_pixel(ex + 1, ey, 60, 220, 255)

        # Phase 2: Mothership or Runway
        if self.phase == PHASE_LANDING:
            if not self.mothership_destroyed:
                mx = int(round(self.mothership_x))
                for ox in range(-2, 3):
                    set_pixel(mx + ox, 2, 220, 50, 50)
                set_pixel(mx, 1, 255, 200, 50)  # Core
            else:
                # Runway beacons (Green flashing landing strip)
                for y in range(0, 4):
                    set_pixel(4, y, 50, 220, 50)
                    set_pixel(11, y, 50, 220, 50)
                set_pixel(7, 1, 240, 240, 60)
                set_pixel(8, 1, 240, 240, 60)

        # Bullets
        for b in self.bullets:
            set_pixel(int(round(b["x"])), int(round(b["y"])), 255, 255, 255)

        for eb in self.enemy_bullets:
            set_pixel(int(round(eb["x"])), int(round(eb["y"])), 255, 60, 40)

        # Player Ship
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            if self.shield_active:
                # Glowing blue/white shield bubble
                set_pixel(px, py, 100, 220, 255)
                set_pixel(px - 1, py, 60, 180, 255)
                set_pixel(px + 1, py, 60, 180, 255)
                set_pixel(px, py - 1, 200, 255, 255)
            else:
                set_pixel(px, py, 60, 140, 255)
                set_pixel(px - 1, py, 40, 80, 200)
                set_pixel(px + 1, py, 40, 80, 200)
                set_pixel(px, py - 1, 255, 200, 50)
        elif self.state == STATE_SHIP_HIT:
            # Explosion
            set_pixel(px, py, 255, 220, 60)
            set_pixel(px - 1, py - 1, 255, 60, 20)
            set_pixel(px + 1, py + 1, 255, 60, 20)

        # Shield indicator dots at bottom row
        for s in range(min(self.shields_left, 3)):
            set_pixel(s * 2, 15, 60, 180, 255)

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "english_name": self.english_name,
            "state": self.state,
            "phase": self.phase,
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "px": self.px,
            "py": self.py,
            "shields_left": self.shields_left,
            "shield_active": self.shield_active,
            "mothership_hp": self.mothership_hp,
            "mothership_destroyed": self.mothership_destroyed,
        }
