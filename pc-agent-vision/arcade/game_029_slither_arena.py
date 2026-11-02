# -*- coding: utf-8 -*-
"""
game_029_slither_arena.py —— 像素贪吃蛇大作战 2016 (Slither Arena 2016)
编号: #029
年代: 2016
核心独占机制: 多蛇竞技追尾拦截 + 蛇头触身暴毙粉碎 + 残骸爆裂光子化吞食 + 损躯超速冲刺超车
手柄类型: CTRL_ARCADE_AB (方向键转向 + A键损躯超速冲刺)
"""

import random
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

DX = [0, 1, 0, -1]  # UP, RIGHT, DOWN, LEFT
DY = [-1, 0, 1, 0]


class Game029SlitherArena(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.player_body: List[Dict[str, int]] = []
        self.player_dir: int = 1
        self.player_timer: float = 0.0
        self.player_boosting: bool = False
        self.player_boost_cost_timer: float = 0.0
        self.lives: int = 3

        self.ai_body: List[Dict[str, int]] = []
        self.ai_dir: int = 3
        self.ai_timer: float = 0.0
        self.ai_alive: bool = True
        self.ai_respawn_timer: float = 0.0

        self.orbs: List[Dict[str, Any]] = []
        self.kill_count: int = 0

        self.score: int = 0
        self.high_score: int = 0
        self.state: int = STATE_TITLE
        self.state_timer: float = 0.0
        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return 29

    @property
    def name(self) -> str:
        return "蛇蛇大作战"

    @property
    def english_name(self) -> str:
        return "Slither Arena 2016"

    @property
    def release_year(self) -> int:
        return 2016

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多蛇竞技追尾拦截 + 蛇头触身暴毙粉碎 + 残骸爆裂光子化吞食 + 损躯超速冲刺超车"

    def init(self) -> None:
        self.reset()

    def spawn_random_orb(self):
        if len(self.orbs) < 18:
            self.orbs.append({
                "active": True,
                "x": random.randint(1, 14),
                "y": random.randint(1, 14),
                "value": 1,
            })

    def dissolve_snake(self, is_player: bool):
        body = self.player_body if is_player else self.ai_body
        for seg in body:
            if len(self.orbs) < 18:
                self.orbs.append({
                    "active": True,
                    "x": seg["x"],
                    "y": seg["y"],
                    "value": 2,
                })

    def respawn_enemy_ai(self):
        self.ai_alive = True
        self.ai_dir = 3
        self.ai_timer = 0.0
        start_y = random.choice([3, 12])
        self.ai_body = [{"x": 13 + i, "y": start_y} for i in range(5)]

    def init_arena(self):
        self.player_dir = 1
        self.player_timer = 0.0
        self.player_boosting = False
        self.player_boost_cost_timer = 0.0

        self.player_body = [{"x": 6 - i, "y": 7} for i in range(5)]
        self.respawn_enemy_ai()

        self.orbs = []
        for _ in range(6):
            self.spawn_random_orb()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.kill_count = 0
        self.state_timer = 0.0
        self.init_arena()

    def update_player(self, dt: float, keys_down: int, keys_pressed: int):
        if (keys_pressed & KEY_UP) and self.player_dir != 2:
            self.player_dir = 0
        elif (keys_pressed & KEY_RIGHT) and self.player_dir != 3:
            self.player_dir = 1
        elif (keys_pressed & KEY_DOWN) and self.player_dir != 0:
            self.player_dir = 2
        elif (keys_pressed & KEY_LEFT) and self.player_dir != 1:
            self.player_dir = 3

        self.player_boosting = (keys_down & KEY_A) and (len(self.player_body) > 3)
        step_interval = 0.08 if self.player_boosting else 0.16

        if self.player_boosting:
            self.player_boost_cost_timer += dt
            if self.player_boost_cost_timer >= 0.35:
                self.player_boost_cost_timer = 0.0
                if len(self.player_body) > 3:
                    tail = self.player_body.pop()
                    if len(self.orbs) < 18:
                        self.orbs.append({"active": True, "x": tail["x"], "y": tail["y"], "value": 1})

        self.player_timer += dt
        if self.player_timer >= step_interval:
            self.player_timer = 0.0
            next_hx = self.player_body[0]["x"] + DX[self.player_dir]
            next_hy = self.player_body[0]["y"] + DY[self.player_dir]

            if not (0 <= next_hx < 16 and 0 <= next_hy < 16):
                self.dissolve_snake(True)
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
                else:
                    self.init_arena()
                    return

            for seg in self.player_body[1:]:
                if next_hx == seg["x"] and next_hy == seg["y"]:
                    self.dissolve_snake(True)
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return
                    else:
                        self.init_arena()
                        return

            grow = False
            for orb in self.orbs:
                if orb["active"] and orb["x"] == next_hx and orb["y"] == next_hy:
                    orb["active"] = False
                    grow = True
                    self.score += orb["value"] * 30
                    if self.score > self.high_score:
                        self.high_score = self.score
                    self.spawn_random_orb()
                    break

            new_head = {"x": next_hx, "y": next_hy}
            self.player_body.insert(0, new_head)
            if not grow:
                self.player_body.pop()
            elif len(self.player_body) > 28:
                self.player_body.pop()

    def update_enemy_ai(self, dt: float):
        if not self.ai_alive:
            self.ai_respawn_timer += dt
            if self.ai_respawn_timer >= 2.0:
                self.ai_respawn_timer = 0.0
                self.respawn_enemy_ai()
            return

        self.ai_timer += dt
        if self.ai_timer >= 0.18:
            self.ai_timer = 0.0

            hx = self.ai_body[0]["x"]
            hy = self.ai_body[0]["y"]

            target_x = self.player_body[-1]["x"]
            target_y = self.player_body[-1]["y"]
            min_dist = 999.0
            for orb in self.orbs:
                if orb["active"]:
                    dist = abs(orb["x"] - hx) + abs(orb["y"] - hy)
                    if dist < min_dist:
                        min_dist = dist
                        target_x = orb["x"]
                        target_y = orb["y"]

            best_dir = -1
            best_eval = 999.0

            for d in range(4):
                if (d + 2) % 4 == self.ai_dir:
                    continue

                nx = hx + DX[d]
                ny = hy + DY[d]

                if not (0 <= nx < 16 and 0 <= ny < 16):
                    continue

                if any(nx == seg["x"] and ny == seg["y"] for seg in self.ai_body[1:]):
                    continue

                if any(nx == seg["x"] and ny == seg["y"] for seg in self.player_body):
                    continue

                dist_to_target = abs(nx - target_x) + abs(ny - target_y)
                if dist_to_target < best_eval:
                    best_eval = dist_to_target
                    best_dir = d

            if best_dir != -1:
                self.ai_dir = best_dir

            next_hx = hx + DX[self.ai_dir]
            next_hy = hy + DY[self.ai_dir]

            if not (0 <= next_hx < 16 and 0 <= next_hy < 16):
                self.dissolve_snake(False)
                self.ai_alive = False
                return

            grow = False
            for orb in self.orbs:
                if orb["active"] and orb["x"] == next_hx and orb["y"] == next_hy:
                    orb["active"] = False
                    grow = True
                    self.spawn_random_orb()
                    break

            new_head = {"x": next_hx, "y": next_hy}
            self.ai_body.insert(0, new_head)
            if not grow:
                self.ai_body.pop()
            elif len(self.ai_body) > 28:
                self.ai_body.pop()

    def check_inter_snake_collisions(self):
        if not self.ai_alive:
            return

        phx = self.player_body[0]["x"]
        phy = self.player_body[0]["y"]
        ahx = self.ai_body[0]["x"]
        ahy = self.ai_body[0]["y"]

        # 玩家撞 AI 身躯
        for seg in self.ai_body[1:]:
            if phx == seg["x"] and phy == seg["y"]:
                self.dissolve_snake(True)
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
                else:
                    self.init_arena()
                    return

        # AI 撞玩家身躯 (玩家击杀 AI)
        for seg in self.player_body[1:]:
            if ahx == seg["x"] and ahy == seg["y"]:
                self.dissolve_snake(False)
                self.ai_alive = False
                self.kill_count += 1
                self.score += 500
                if self.score > self.high_score:
                    self.high_score = self.score

                if self.kill_count >= 3 or len(self.player_body) >= 16:
                    self.state = STATE_VICTORY
                    self.state_timer = 0.0
                return

        # 对撞
        if phx == ahx and phy == ahy:
            if len(self.player_body) > len(self.ai_body):
                self.dissolve_snake(False)
                self.ai_alive = False
                self.kill_count += 1
                self.score += 500
                if self.score > self.high_score:
                    self.high_score = self.score
            else:
                self.dissolve_snake(True)
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return
                else:
                    self.init_arena()
                    return

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

            self.update_player(dt, keys_down, keys_pressed)
            self.update_enemy_ai(dt)
            self.check_inter_snake_collisions()

            if len(self.player_body) >= 16 or self.kill_count >= 3:
                self.state = STATE_VICTORY
                self.state_timer = 0.0
                self.score += 1500
                if self.score > self.high_score:
                    self.high_score = self.score

    def render(self, target_buf: Optional[bytearray] = None) -> bytes:
        buf = target_buf if target_buf is not None else self.frame_buffer

        for i in range(16 * 16 * 3):
            buf[i] = 0

        # 地面网格
        for y in range(16):
            for x in range(16):
                if (x + y) % 4 == 0:
                    idx = (y * 16 + x) * 3
                    buf[idx:idx+3] = bytes([15, 20, 28])

        # 光子
        for orb in self.orbs:
            if not orb["active"]:
                continue
            idx = (orb["y"] * 16 + orb["x"]) * 3
            if orb["value"] == 2:
                buf[idx:idx+3] = bytes([255, 180, 50])
            else:
                buf[idx:idx+3] = bytes([241, 196, 15])

        # AI 蛇
        if self.ai_alive:
            for i in range(len(self.ai_body) - 1, -1, -1):
                seg = self.ai_body[i]
                idx = (seg["y"] * 16 + seg["x"]) * 3
                if i == 0:
                    buf[idx:idx+3] = bytes([255, 120, 80])
                else:
                    buf[idx:idx+3] = bytes([231, 76, 60])

        # 玩家蛇
        if self.lives > 0:
            for i in range(len(self.player_body) - 1, -1, -1):
                seg = self.player_body[i]
                idx = (seg["y"] * 16 + seg["x"]) * 3
                if i == 0:
                    buf[idx:idx+3] = bytes([0, 255, 255])
                elif self.player_boosting:
                    buf[idx:idx+3] = bytes([155, 89, 182])
                else:
                    buf[idx:idx+3] = bytes([46, 204, 113])

        # HUD
        for i in range(self.lives):
            idx = (0 * 16 + i) * 3
            buf[idx:idx+3] = bytes([0, 255, 255])

        for i in range(self.kill_count):
            idx = (0 * 16 + (15 - i)) * 3
            buf[idx:idx+3] = bytes([241, 196, 15])

        # 特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                buf[idx:idx+3] = bytes([231, 76, 60])

        return bytes(buf)

    def get_status(self) -> Dict[str, Any]:
        cur_len = len(self.player_body)
        prog = ((cur_len - 5) * 100) // 11
        prog = max(0, min(100, prog))
        return {
            "score": self.score,
            "lives": self.lives,
            "length": cur_len,
            "kills": self.kill_count,
            "state": self.state,
            "progress": prog,
        }
