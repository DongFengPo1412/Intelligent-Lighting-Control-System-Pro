# -*- coding: utf-8 -*-
"""
Game #156: 西游降魔 (SonSon 1984 / Capcom)
街机历史上首款六层平台变轨跳跃与西游神话横版射击开山鼻祖：
小灵猴孙悟空在六层悬空竹简平台间敏捷上下变轨飞跃、
平射金箍棒法力魔弹击溃各层妖魔群落、吞食四溢瓜果盛宴挺进天竺胜境。
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

LANES = [4.0, 6.0, 8.0, 10.0, 12.0, 14.0]
MAX_DISTANCE = 100.0


class Game156SonSon(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.lives = 3
        self.level = 1

        self.px = 3.0
        self.lane_idx = 3  # Start on lane 3 (y=10.0)
        self.py = LANES[self.lane_idx]
        self.distance = 0.0

        # Projectiles
        self.shots: List[Dict[str, Any]] = []

        # Enemies on various lanes
        self.enemies: List[Dict[str, Any]] = []

        # Food / Fruits on lanes
        self.fruits: List[Dict[str, Any]] = []

        self.spawn_timer = 0.0

        self.reset()

    @property
    def game_id(self) -> int:
        return 156

    @property
    def name(self) -> str:
        return "西游降魔"

    @property
    def english_name(self) -> str:
        return "SonSon"

    @property
    def release_year(self) -> int:
        return 1984

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "六层平台竹简瞬间上下变轨跳跃、各层前向发射金箍棒魔弹、拾取散落瓜果蔬菜盛宴与西行天竺通关"

    def get_name(self) -> str:
        return "SonSon (1984)"

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
        self.px = 3.0
        self.lane_idx = 3
        self.py = LANES[self.lane_idx]
        self.distance = 0.0
        self.shots.clear()
        self.enemies.clear()
        self.fruits.clear()
        self.spawn_timer = 0.0

        # Initial wave of enemies
        self.enemies = [
            {"x": 14.0, "lane": 3, "vx": -3.5, "type": "bat", "alive": True, "respawn_timer": 0.0},
            {"x": 16.0, "lane": 1, "vx": -3.0, "type": "imp", "alive": True, "respawn_timer": 0.0},
            {"x": 18.0, "lane": 4, "vx": -2.8, "type": "boar", "alive": True, "respawn_timer": 0.0},
        ]

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
                        self.px = 3.0
                        self.lane_idx = 3
                        self.py = LANES[self.lane_idx]
                        self.shots.clear()
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
        # 1. Instant Vertical Lane Switching: Key UP and Key DOWN
        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            if self.lane_idx > 0:
                self.lane_idx -= 1
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            if self.lane_idx < len(LANES) - 1:
                self.lane_idx += 1

        # Smooth vertical snap
        target_y = LANES[self.lane_idx]
        self.py += (target_y - self.py) * min(1.0, dt * 20.0)

        # 2. Horizontal Running along platform
        speed = 4.5
        dx = 0.0
        if buttons & KEY_LEFT:
            dx -= speed
        elif buttons & KEY_RIGHT:
            dx += speed

        self.px = max(1.5, min(14.0, self.px + dx * dt))

        # Scroll advance
        scroll_speed = 3.0
        self.distance += scroll_speed * dt

        # 3. Fire Magical Energy Blast: Key A or Key B
        if (buttons & (KEY_A | KEY_B)) and not (prev_buttons & (KEY_A | KEY_B)):
            if len(self.shots) < 5:
                self.shots.append({
                    "x": self.px + 0.8,
                    "lane": self.lane_idx,
                    "y": self.py,
                    "vx": 14.0,
                })

        # 4. Update Shots
        for s in self.shots:
            s["x"] += s["vx"] * dt

        # Collision with enemies on same lane
        for s in self.shots:
            for e in self.enemies:
                if e["alive"] and e["lane"] == s["lane"]:
                    if abs(s["x"] - e["x"]) < 1.0:
                        e["alive"] = False
                        e["respawn_timer"] = 2.0
                        s["x"] = 100.0  # destroy shot
                        self.score += 150
                        # Chance to spawn fruit
                        if len(self.fruits) < 4:
                            self.fruits.append({
                                "x": e["x"],
                                "lane": e["lane"],
                                "y": LANES[e["lane"]],
                                "type": "peach" if e["lane"] % 2 == 0 else "melon"
                            })
                        break

        self.shots = [s for s in self.shots if s["x"] <= 15.5]

        # 5. Update Fruits (collecting them)
        for f in self.fruits:
            f["x"] -= scroll_speed * 0.5 * dt  # scrolls with landscape
            if f["lane"] == self.lane_idx and abs(self.px - f["x"]) < 0.9:
                f["x"] = -100.0
                self.score += 300 if f["type"] == "peach" else 500

        self.fruits = [f for f in self.fruits if f["x"] >= 0.5]

        # 6. Update Enemies
        for e in self.enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"] * dt

            # Enemy touches SonSon on same lane
            if e["lane"] == self.lane_idx and abs(self.px - e["x"]) < 0.8:
                self._lose_life()
                return

        # Recycle enemies
        for e in self.enemies:
            if not e["alive"]:
                e["respawn_timer"] -= dt
                if e["respawn_timer"] <= 0.0:
                    e["x"] = 16.5 + (len(self.enemies) * 2.0)
                    e["lane"] = (self.lane_idx + (int(self.distance) % 4)) % len(LANES)
                    e["alive"] = True
            elif e["x"] < -1.0:
                e["x"] = 16.5 + (len(self.enemies) * 2.0)
                e["lane"] = (self.lane_idx + (int(self.distance) % 4)) % len(LANES)

        # 7. Check Tianzhu Buddha Sanctuary Gate
        if self.distance >= MAX_DISTANCE:
            self.score += 2500
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

        # 1. Render 6 Bamboo Scroll Platform Tiers
        for ly in LANES:
            floor_y = int(ly) + 1
            if floor_y < 16:
                for x in range(16):
                    set_pixel(x, floor_y, 40, 140, 70)  # Green bamboo ledge

        # 2. Buddha Sanctuary Pagoda Gate at end
        if self.distance >= MAX_DISTANCE - 10.0:
            gx = int(round(15.0 - (MAX_DISTANCE - self.distance)))
            if 0 <= gx < 16:
                for y in range(2, 15):
                    set_pixel(gx, y, 240, 200, 40)

        # 3. Fruits (Peaches: Pink, Melons: Orange)
        for f in self.fruits:
            fx = int(round(f["x"]))
            fy = int(round(f["y"]))
            if f["type"] == "peach":
                set_pixel(fx, fy, 255, 120, 160)
            else:
                set_pixel(fx, fy, 255, 180, 30)

        # 4. Enemies (Bats: Purple, Boars: Red, Imps: Blue)
        for e in self.enemies:
            if e["alive"]:
                ex = int(round(e["x"]))
                ey = int(round(LANES[e["lane"]]))
                if e["type"] == "bat":
                    set_pixel(ex, ey, 180, 50, 220)
                elif e["type"] == "boar":
                    set_pixel(ex, ey, 240, 60, 40)
                else:
                    set_pixel(ex, ey, 40, 140, 240)

        # 5. Energy Blast Shots
        for s in self.shots:
            sx = int(round(s["x"]))
            sy = int(round(s["y"]))
            set_pixel(sx, sy, 255, 240, 80)
            if sx - 1 >= 0: set_pixel(sx - 1, sy, 255, 160, 40)

        # 6. SonSon (Monkey King: Golden body, Red headband & staff)
        px = int(round(self.px))
        py = int(round(self.py))
        if self.state in (STATE_PLAYING, STATE_STAGE_CLEAR):
            set_pixel(px, py, 240, 170, 40)       # Monkey fur
            set_pixel(px, py - 1, 240, 60, 40)   # Golden circlet / red cloth
            if px + 1 < 16:
                set_pixel(px + 1, py, 255, 220, 50)  # Power staff tip
        elif self.state == STATE_PLAYER_HIT:
            set_pixel(px, py, 255, 50, 50)

        # 7. Progress & Lives
        prog_dots = int((self.distance / MAX_DISTANCE) * 8.0)
        for i in range(prog_dots):
            set_pixel(8 + i, 0, 240, 200, 40)

        for l in range(min(self.lives, 3)):
            set_pixel(l * 2, 0, 240, 60, 40)

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
            "lane_idx": self.lane_idx,
            "distance": self.distance,
            "enemies_count": sum(1 for e in self.enemies if e["alive"]),
        }
