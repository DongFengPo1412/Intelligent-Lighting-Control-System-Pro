# -*- coding: utf-8 -*-
"""
game_009_space_invaders.py —— 太空侵略者 1978 (Space Invaders 1978)
编号: #009
年代: 1978 (太东 Taito / 西角友宏 Tomohiro Nishikado)
核心独占机制: 外星阵列编队平移下压 + 阵亡提速 + 掩体阻挡损毁 + 垂直防空阻击
手柄类型: CTRL_ARCADE_AB (左右移动炮台 + A/B 垂直开火)
"""

import math
import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
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

class Alien:
    def __init__(self, r: int, g: int, b: int, score_val: int):
        self.alive = True
        self.r = r
        self.g = g
        self.b = b
        self.score_val = score_val

class Bullet:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vy = 0.0

class BunkerPixel:
    def __init__(self):
        self.hp = 2

class Game009SpaceInvaders(BaseCartridge):
    def __init__(self):
        self._id = 9
        self._name = "太空侵略者"
        self._english_name = "Space Invaders 1978"
        self._year = 1978
        self._control_type = CTRL_ARCADE_AB
        self._core_mechanic = "外星阵列编队平移下压 + 阵亡提速 + 掩体阻挡损毁 + 垂直防空阻击"

        self.k_fleet_rows = 3
        self.k_fleet_cols = 4
        self.k_num_bunkers = 3
        self.k_max_alien_bombs = 2

        self.state = STATE_TITLE
        self.player_x = 7.0
        self.lives = 3
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0

        self.fleet: List[List[Alien]] = []
        self.fleet_x = 1
        self.fleet_y = 1
        self.fleet_dir = 1
        self.march_timer = 0.0
        self.march_interval = 0.6
        self.remaining_aliens = 12

        self.player_bullet = Bullet()
        self.alien_bombs = [Bullet() for _ in range(self.k_max_alien_bombs)]
        self.bomb_drop_timer = 0.0

        # 3座掩体，每座 2x2
        self.bunkers: List[List[List[BunkerPixel]]] = []

        self.frame_buffer = bytearray(16 * 16 * 3)
        self.reset()

    @property
    def game_id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def english_name(self) -> str:
        return self._english_name

    @property
    def release_year(self) -> int:
        return self._year

    @property
    def control_type(self) -> int:
        return self._control_type

    @property
    def core_mechanic(self) -> str:
        return self._core_mechanic

    def reset_fleet(self):
        self.remaining_aliens = self.k_fleet_rows * self.k_fleet_cols
        self.fleet = []
        for r in range(self.k_fleet_rows):
            row: List[Alien] = []
            if r == 0:
                cr, cg, cb, pts = 255, 0, 128, 30
            elif r == 1:
                cr, cg, cb, pts = 241, 196, 15, 20
            else:
                cr, cg, cb, pts = 0, 255, 255, 10

            for c in range(self.k_fleet_cols):
                row.append(Alien(cr, cg, cb, pts))
            self.fleet.append(row)

        self.fleet_x = 1
        self.fleet_y = 1
        self.fleet_dir = 1
        self.march_timer = 0.0
        self.march_interval = 0.6

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.player_x = 7.0

        self.player_bullet.active = False
        for b in self.alien_bombs:
            b.active = False

        self.bunkers = []
        for b in range(self.k_num_bunkers):
            bunker = [[BunkerPixel() for _ in range(2)] for _ in range(2)]
            self.bunkers.append(bunker)

        self.reset_fleet()

    def fire_player_bullet(self):
        if not self.player_bullet.active:
            self.player_bullet.active = True
            self.player_bullet.x = self.player_x
            self.player_bullet.y = 12.0
            self.player_bullet.vy = -18.0

    def spawn_alien_bomb(self):
        free_bomb = None
        for b in self.alien_bombs:
            if not b.active:
                free_bomb = b
                break
        if not free_bomb:
            return

        candidates = []
        for c in range(self.k_fleet_cols):
            for r in range(self.k_fleet_rows - 1, -1, -1):
                if self.fleet[r][c].alive:
                    candidates.append((r, c))
                    break
        if not candidates:
            return

        r, c = random.choice(candidates)
        free_bomb.active = True
        free_bomb.x = float(self.fleet_x + c * 2)
        free_bomb.y = float(self.fleet_y + r * 2 + 1)
        free_bomb.vy = 8.0

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT)):
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

            # 1. 玩家移动
            player_speed = 10.0
            if keys_down & KEY_LEFT:
                self.player_x -= player_speed * dt
            elif keys_down & KEY_RIGHT:
                self.player_x += player_speed * dt
            self.player_x = max(1.0, min(14.0, self.player_x))

            # 2. 开火
            if keys_pressed & (KEY_A | KEY_B | KEY_UP):
                self.fire_player_bullet()

            # 3. 玩家子弹更新
            if self.player_bullet.active:
                self.player_bullet.y += self.player_bullet.vy * dt
                bx = int(round(self.player_bullet.x))
                by = int(round(self.player_bullet.y))

                if self.player_bullet.y <= 0.0:
                    self.player_bullet.active = False
                else:
                    # 掩体阻挡
                    hit_bunker = False
                    for b_idx in range(self.k_num_bunkers):
                        bx_origin = 2 if b_idx == 0 else 7 if b_idx == 1 else 12
                        if bx_origin <= bx < bx_origin + 2 and 11 <= by <= 12:
                            br = by - 11
                            bc = bx - bx_origin
                            if self.bunkers[b_idx][br][bc].hp > 0:
                                self.bunkers[b_idx][br][bc].hp -= 1
                                self.player_bullet.active = False
                                hit_bunker = True
                                break

                    # 击中外星人
                    if not hit_bunker and self.player_bullet.active:
                        for r in range(self.k_fleet_rows):
                            for c in range(self.k_fleet_cols):
                                if self.fleet[r][c].alive:
                                    ax = self.fleet_x + c * 2
                                    ay = self.fleet_y + r * 2
                                    if abs(self.player_bullet.x - ax) < 0.9 and abs(self.player_bullet.y - ay) < 0.9:
                                        self.fleet[r][c].alive = False
                                        self.remaining_aliens -= 1
                                        self.score += self.fleet[r][c].score_val
                                        if self.score > self.high_score:
                                            self.high_score = self.score
                                        self.player_bullet.active = False

                                        self.march_interval = 0.12 + (0.48 * self.remaining_aliens) / 12.0

                                        if self.remaining_aliens <= 0:
                                            self.state = STATE_VICTORY
                                            self.state_timer = 0.0
                                            return
                                        break
                            if not self.player_bullet.active:
                                break

            # 4. 外星行军节拍
            self.march_timer += dt
            if self.march_timer >= self.march_interval:
                self.march_timer = 0.0

                min_c = self.k_fleet_cols
                max_c = -1
                max_r = -1
                for r in range(self.k_fleet_rows):
                    for c in range(self.k_fleet_cols):
                        if self.fleet[r][c].alive:
                            if c < min_c: min_c = c
                            if c > max_c: max_c = c
                            if r > max_r: max_r = r

                if max_c != -1:
                    next_edge_right = self.fleet_x + max_c * 2 + self.fleet_dir
                    next_edge_left = self.fleet_x + min_c * 2 + self.fleet_dir

                    if self.fleet_dir > 0 and next_edge_right >= 16:
                        self.fleet_y += 1
                        self.fleet_dir = -1
                    elif self.fleet_dir < 0 and next_edge_left < 0:
                        self.fleet_y += 1
                        self.fleet_dir = 1
                    else:
                        self.fleet_x += self.fleet_dir

                    if self.fleet_y + max_r * 2 >= 13:
                        self.state = STATE_GAMEOVER
                        self.state_timer = 0.0
                        return

            # 5. 敌机炸弹投放
            self.bomb_drop_timer += dt
            if self.bomb_drop_timer >= 1.2:
                self.bomb_drop_timer = 0.0
                self.spawn_alien_bomb()

            # 6. 敌机炸弹下落判定
            for bomb in self.alien_bombs:
                if bomb.active:
                    bomb.y += bomb.vy * dt
                    bx = int(round(bomb.x))
                    by = int(round(bomb.y))

                    # 炸毁掩体
                    hit_bunker = False
                    for b_idx in range(self.k_num_bunkers):
                        bx_origin = 2 if b_idx == 0 else 7 if b_idx == 1 else 12
                        if bx_origin <= bx < bx_origin + 2 and 11 <= by <= 12:
                            br = by - 11
                            bc = bx - bx_origin
                            if self.bunkers[b_idx][br][bc].hp > 0:
                                self.bunkers[b_idx][br][bc].hp -= 1
                                bomb.active = False
                                hit_bunker = True
                                break

                    # 击中玩家
                    if not hit_bunker and bomb.active and 13 <= by <= 14:
                        if abs(bomb.x - self.player_x) <= 1.2:
                            bomb.active = False
                            if self.lives > 0:
                                self.lives -= 1
                            if self.lives == 0:
                                self.state = STATE_GAMEOVER
                                self.state_timer = 0.0
                                return

                    # 出底界
                    if bomb.y >= 16.0:
                        bomb.active = False

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        # 生命点阵 (y=0)
        for i in range(self.lives):
            idx = (0 * 16 + (i * 2)) * 3
            self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])

        # 外星舰队
        for r in range(self.k_fleet_rows):
            for c in range(self.k_fleet_cols):
                if self.fleet[r][c].alive:
                    ax = self.fleet_x + c * 2
                    ay = self.fleet_y + r * 2
                    if 0 <= ax < 16 and 0 <= ay < 16:
                        idx = (ay * 16 + ax) * 3
                        self.frame_buffer[idx:idx+3] = bytes([self.fleet[r][c].r, self.fleet[r][c].g, self.fleet[r][c].b])

        # 掩体
        for b_idx in range(self.k_num_bunkers):
            bx_origin = 2 if b_idx == 0 else 7 if b_idx == 1 else 12
            for r in range(2):
                y = 11 + r
                for c in range(2):
                    x = bx_origin + c
                    hp = self.bunkers[b_idx][r][c].hp
                    if hp > 0:
                        idx = (y * 16 + x) * 3
                        color = [46, 204, 113] if hp == 2 else [30, 132, 73]
                        self.frame_buffer[idx:idx+3] = bytes(color)

        # 炸弹
        for bomb in self.alien_bombs:
            if bomb.active:
                bx = int(round(bomb.x))
                by = int(round(bomb.y))
                if 0 <= bx < 16 and 0 <= by < 16:
                    idx = (by * 16 + bx) * 3
                    self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        # 玩家炮台
        px = int(round(self.player_x))
        if 0 <= px < 16:
            idx = (13 * 16 + px) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 255, 255])
        for dx in (-1, 0, 1):
            x = px + dx
            if 0 <= x < 16:
                idx = (14 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])

        # 玩家子弹
        if self.player_bullet.active:
            bx = int(round(self.player_bullet.x))
            by = int(round(self.player_bullet.y))
            if 0 <= bx < 16 and 0 <= by < 16:
                idx = (by * 16 + bx) * 3
                self.frame_buffer[idx:idx+3] = bytes([255, 255, 255])

        # 状态特效
        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([52, 152, 219])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        progress = int(((self.k_fleet_rows * self.k_fleet_cols - self.remaining_aliens) * 100) / (self.k_fleet_rows * self.k_fleet_cols))
        return {
            "score": self.score,
            "lives": self.lives,
            "state": self.state,
            "progress": progress,
            "remaining_aliens": self.remaining_aliens,
        }
