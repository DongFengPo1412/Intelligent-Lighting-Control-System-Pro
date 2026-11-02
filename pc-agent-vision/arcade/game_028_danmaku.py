# -*- coding: utf-8 -*-
"""
game_028_danmaku.py —— 蜂群极速弹幕 1997 (Danmaku / Dodonpachi 1997)
编号: #028
年代: 1997 (CAVE)
核心独占机制: 极小1像素Hitbox判定点 + 几何旋转同心螺旋弹幕 + 擦弹(Graze)险中求分 + 保命全屏清弹
手柄类型: CTRL_ARCADE_AB (方向键精密微操走位 + A键高频射击 + B键清屏炸弹)
"""

import math
from typing import Dict, Any, List, Optional
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)


class Game028Danmaku(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.player_x: float = 7.5
        self.player_y: float = 13.5
        self.lives: int = 3
        self.bombs: int = 2
        self.graze_count: int = 0
        self.shoot_timer: float = 0.0
        self.bomb_flash_timer: float = 0.0

        self.boss: Dict[str, Any] = {
            "active": True,
            "x": 7.5,
            "y": 2.5,
            "hp": 100,
            "max_hp": 100,
            "pattern_timer": 0.0,
            "pattern_phase": 0,
        }

        self.spiral_angle: float = 0.0
        self.bullets: List[Dict[str, Any]] = []

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 28

    @property
    def name(self) -> str:
        return "蜂群极速弹幕"

    @property
    def english_name(self) -> str:
        return "Danmaku 1997"

    @property
    def release_year(self) -> int:
        return 1997

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "极小1像素Hitbox判定点 + 几何旋转同心螺旋弹幕 + 擦弹(Graze)险中求分 + 保命全屏清弹"

    def init(self) -> None:
        self.reset()

    def init_boss(self):
        self.boss = {
            "active": True,
            "x": 7.5,
            "y": 2.5,
            "hp": 100,
            "max_hp": 100,
            "pattern_timer": 0.0,
            "pattern_phase": 0,
        }
        self.bullets = []
        self.player_x = 7.5
        self.player_y = 13.5
        self.lives = 3
        self.bombs = 2
        self.graze_count = 0
        self.shoot_timer = 0.0
        self.bomb_flash_timer = 0.0
        self.spiral_angle = 0.0

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.init_boss()

    def fire_player_shot(self):
        if self.shoot_timer > 0.0:
            return
        self.shoot_timer = 0.15

        if len(self.bullets) < 32:
            self.bullets.append({
                "active": True,
                "x": self.player_x,
                "y": self.player_y - 0.5,
                "vx": 0.0,
                "vy": -15.0,
                "is_player": True,
                "grazed": False,
            })

    def fire_spiral_pattern(self, angle_rad: float):
        speed = 4.2
        if len(self.bullets) < 32:
            self.bullets.append({
                "active": True,
                "x": self.boss["x"],
                "y": self.boss["y"],
                "vx": speed * math.cos(angle_rad),
                "vy": speed * math.sin(angle_rad),
                "is_player": False,
                "grazed": False,
            })

    def fire_ring_pattern(self, count: int):
        speed = 3.8
        step = (2.0 * math.pi) / count
        for c in range(count):
            if len(self.bullets) >= 32:
                break
            rad = c * step
            self.bullets.append({
                "active": True,
                "x": self.boss["x"],
                "y": self.boss["y"],
                "vx": speed * math.cos(rad),
                "vy": speed * math.sin(rad),
                "is_player": False,
                "grazed": False,
            })

    def use_bomb(self):
        if self.bombs <= 0:
            return
        self.bombs -= 1
        self.bomb_flash_timer = 0.25

        for b in self.bullets:
            if not b["is_player"]:
                b["active"] = False
                self.score += 10

        self.boss["hp"] -= 25
        self.score += 500
        if self.score > self.high_score:
            self.high_score = self.score

        if self.boss["hp"] <= 0:
            self.boss["active"] = False
            self.state = STATE_VICTORY
            self.state_timer = 0.0

    def update_boss(self, dt: float):
        if not self.boss["active"]:
            return

        self.boss["x"] = 7.5 + math.sin(self.state_timer * 2.0) * 3.5
        self.boss["pattern_timer"] += dt

        if self.boss["pattern_phase"] == 0:
            if self.boss["pattern_timer"] >= 0.12:
                self.boss["pattern_timer"] = 0.0
                self.fire_spiral_pattern(self.spiral_angle)
                self.fire_spiral_pattern(self.spiral_angle + math.pi)
                self.spiral_angle += 0.45
            if self.state_timer >= 12.0:
                self.boss["pattern_phase"] = 1
        else:
            if self.boss["pattern_timer"] >= 1.4:
                self.boss["pattern_timer"] = 0.0
                self.fire_ring_pattern(8)

    def update_bullets(self, dt: float):
        for b in self.bullets:
            if not b["active"]:
                continue

            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt

            if b["x"] < -1.0 or b["x"] > 17.0 or b["y"] < -1.0 or b["y"] > 17.0:
                b["active"] = False
                continue

            if b["is_player"]:
                if self.boss["active"]:
                    dist = abs(b["x"] - self.boss["x"]) + abs(b["y"] - self.boss["y"])
                    if dist <= 1.4:
                        b["active"] = False
                        self.boss["hp"] -= 1
                        self.score += 15
                        if self.score > self.high_score:
                            self.high_score = self.score

                        if self.boss["hp"] <= 0:
                            self.boss["active"] = False
                            self.state = STATE_VICTORY
                            self.state_timer = 0.0
                            self.score += 2000
                            if self.score > self.high_score:
                                self.high_score = self.score
                            return
            else:
                dist = abs(b["x"] - self.player_x) + abs(b["y"] - self.player_y)

                # 1 像素核心 Hitbox (dist <= 0.65)
                if dist <= 0.65:
                    b["active"] = False
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                    else:
                        for ob in self.bullets:
                            if not ob["is_player"]:
                                ob["active"] = False
                        self.player_x = 7.5
                        self.player_y = 13.5
                        return
                elif dist <= 1.4 and not b["grazed"]:
                    b["grazed"] = True
                    self.graze_count += 1
                    self.score += 20
                    if self.score > self.high_score:
                        self.high_score = self.score

        self.bullets = [b for b in self.bullets if b["active"]]

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        dt = min(dt, 0.05)
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
                self.reset()
            return

        if self.state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self.state = STATE_PAUSED
                return

            if self.shoot_timer > 0.0:
                self.shoot_timer -= dt
            if self.bomb_flash_timer > 0.0:
                self.bomb_flash_timer -= dt

            speed = 7.2
            if keys_down & KEY_LEFT:
                self.player_x -= speed * dt
            if keys_down & KEY_RIGHT:
                self.player_x += speed * dt
            if keys_down & KEY_UP:
                self.player_y -= speed * dt
            if keys_down & KEY_DOWN:
                self.player_y += speed * dt

            self.player_x = max(0.5, min(14.5, self.player_x))
            self.player_y = max(4.0, min(14.5, self.player_y))

            if keys_down & KEY_A:
                self.fire_player_shot()
            if keys_pressed & KEY_B:
                self.use_bomb()

            self.update_boss(dt)
            self.update_bullets(dt)

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        if self.bomb_flash_timer > 0.0:
            for i in range(16 * 16 * 3):
                buf[i] = 180

        # Boss
        if self.boss["active"]:
            bx = int(round(self.boss["x"]))
            by = int(round(self.boss["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                bidx = (by * 16 + bx) * 3
                buf[bidx + 0] = 231
                buf[bidx + 1] = 76
                buf[bidx + 2] = 60
                if bx > 0:
                    lidx = (by * 16 + (bx - 1)) * 3
                    buf[lidx + 0] = 155
                    buf[lidx + 1] = 89
                    buf[lidx + 2] = 182
                if bx < 15:
                    ridx = (by * 16 + (bx + 1)) * 3
                    buf[ridx + 0] = 155
                    buf[ridx + 1] = 89
                    buf[ridx + 2] = 182

        # 弹幕
        for b in self.bullets:
            if not b["active"]:
                continue
            bx = int(round(b["x"]))
            by = int(round(b["y"]))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                if b["is_player"]:
                    buf[idx + 0] = 255
                    buf[idx + 1] = 255
                    buf[idx + 2] = 255
                else:
                    buf[idx + 0] = 255
                    buf[idx + 1] = 40
                    buf[idx + 2] = 120

        # 战机
        if self.lives > 0:
            px = int(round(self.player_x))
            py = int(round(self.player_y))
            if 0 <= px < 16 and 0 <= py < 16:
                if px > 0:
                    lidx = (py * 16 + (px - 1)) * 3
                    buf[lidx + 0] = 0
                    buf[lidx + 1] = 200
                    buf[lidx + 2] = 255
                if px < 15:
                    ridx = (py * 16 + (px + 1)) * 3
                    buf[ridx + 0] = 0
                    buf[ridx + 1] = 200
                    buf[ridx + 2] = 255
                cidx = (py * 16 + px) * 3
                buf[cidx + 0] = 255
                buf[cidx + 1] = 50
                buf[cidx + 2] = 50

        # HUD
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx + 0] = 255
            buf[idx + 1] = 255
            buf[idx + 2] = 255

        for i in range(self.bombs):
            idx = (0 * 16 + (i + 4)) * 3
            buf[idx + 0] = 46
            buf[idx + 1] = 204
            buf[idx + 2] = 113

        # 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx + 0] = 46
                buf[idx + 1] = 204
                buf[idx + 2] = 113
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx + 0] = 231
                buf[idx + 1] = 76
                buf[idx + 2] = 60

        return bytes(buf)

    def get_status(self) -> Dict[str, Any]:
        prog = ((self.boss["max_hp"] - self.boss["hp"]) * 100) // self.boss["max_hp"]
        prog = max(0, min(100, prog))
        return {
            "score": self.score,
            "lives": self.lives,
            "bombs": self.bombs,
            "graze": self.graze_count,
            "boss_hp": self.boss["hp"],
            "state": self.state,
            "progress": prog,
        }
