# -*- coding: utf-8 -*-
"""
game_019_puzzle_bobble.py —— 像素泡泡龙 1994 (Puzzle Bobble 1994)
编号: #019
年代: 1994 (太东 Taito)
核心独占机制: 仰角旋转发射 + 侧壁反弹吸附 + 三连同色拓扑消除 + 浮空孤岛脱落
手柄类型: CTRL_TWO_BUTTON (左右微调发射仰角 + A/B 发射)
"""

import math
import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    KEY_UP,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_TWO_BUTTON,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)

BUBBLE_NONE = 0
BUBBLE_RED = 1
BUBBLE_BLUE = 2
BUBBLE_GREEN = 3
BUBBLE_YELLOW = 4

COLOR_RGB = {
    BUBBLE_RED: (231, 76, 60),
    BUBBLE_BLUE: (52, 152, 219),
    BUBBLE_GREEN: (46, 204, 113),
    BUBBLE_YELLOW: (241, 196, 15),
}

class FlyingBubble:
    def __init__(self):
        self.active = False
        self.x = 7.5
        self.y = 14.0
        self.vx = 0.0
        self.vy = 0.0
        self.color = BUBBLE_RED

class Game019PuzzleBobble(BaseCartridge):
    def __init__(self):
        self._id = 19
        self._name = "像素泡泡龙"
        self._english_name = "Puzzle Bobble 1994"
        self._year = 1994
        self._control_type = CTRL_TWO_BUTTON
        self._core_mechanic = "仰角旋转发射 + 侧壁反弹吸附 + 三连同色拓扑消除 + 浮空孤岛脱落"

        self.state = STATE_TITLE
        self.grid: List[List[int]] = [[BUBBLE_NONE for _ in range(16)] for _ in range(16)]
        self.angle_deg = 0.0
        self.current_color = BUBBLE_RED
        self.next_color = BUBBLE_BLUE
        self.flying = FlyingBubble()
        self.shots_fired = 0
        self.score = 0
        self.high_score = 0
        self.state_timer = 0.0

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

    def count_remaining_bubbles(self) -> int:
        cnt = 0
        for y in range(14):
            for x in range(16):
                if self.grid[y][x] != BUBBLE_NONE:
                    cnt += 1
        return cnt

    def reset_level(self):
        self.grid = [[BUBBLE_NONE for _ in range(16)] for _ in range(16)]

        for y in range(3):
            for x in range(16):
                c = ((x // 3) + y) % 4 + 1
                self.grid[y][x] = c

        self.angle_deg = 0.0
        self.current_color = random.randint(1, 4)
        self.next_color = random.randint(1, 4)
        self.flying.active = False
        self.shots_fired = 0

    def init(self):
        self.reset()

    def reset(self):
        self.state = STATE_PLAYING
        self.score = 0
        self.state_timer = 0.0
        self.reset_level()

    def fire_bubble(self):
        if self.flying.active:
            return

        self.flying.active = True
        self.flying.x = 7.5
        self.flying.y = 14.0
        self.flying.color = self.current_color

        rad = (self.angle_deg - 90.0) * math.pi / 180.0
        speed = 18.0
        self.flying.vx = speed * math.cos(rad)
        self.flying.vy = speed * math.sin(rad)

        self.current_color = self.next_color
        self.next_color = random.randint(1, 4)
        self.shots_fired += 1

    def remove_floating_islands(self):
        connected = [[False for _ in range(16)] for _ in range(16)]
        queue = []

        for x in range(16):
            if self.grid[0][x] != BUBBLE_NONE:
                connected[0][x] = True
                queue.append((x, 0))

        dxs = [0, 0, -1, 1]
        dys = [-1, 1, 0, 0]

        head = 0
        while head < len(queue):
            cx, cy = queue[head]
            head += 1

            for i in range(4):
                nx, ny = cx + dxs[i], cy + dys[i]
                if 0 <= nx < 16 and 0 <= ny < 14:
                    if self.grid[ny][nx] != BUBBLE_NONE and not connected[ny][nx]:
                        connected[ny][nx] = True
                        queue.append((nx, ny))

        dropped = 0
        for y in range(14):
            for x in range(16):
                if self.grid[y][x] != BUBBLE_NONE and not connected[y][x]:
                    self.grid[y][x] = BUBBLE_NONE
                    dropped += 1

        if dropped > 0:
            self.score += dropped * 50
            if self.score > self.high_score:
                self.high_score = self.score

    def snap_and_resolve(self, fx: float, fy: float, color: int):
        self.flying.active = False
        sx = int(round(fx))
        sy = int(round(fy))
        sx = max(0, min(15, sx))
        sy = max(0, min(13, sy))

        if self.grid[sy][sx] != BUBBLE_NONE:
            found = False
            for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < 16 and 0 <= ny < 14:
                    if self.grid[ny][nx] == BUBBLE_NONE:
                        sx, sy = nx, ny
                        found = True
                        break
            if not found:
                self.state = STATE_GAMEOVER
                self.state_timer = 0.0
                return

        self.grid[sy][sx] = color
        self.flying.active = False

        if sy >= 13:
            self.state = STATE_GAMEOVER
            self.state_timer = 0.0
            return

        visited = [[False for _ in range(16)] for _ in range(16)]
        cluster = []
        queue = [(sx, sy)]
        visited[sy][sx] = True

        dxs = [0, 0, -1, 1]
        dys = [-1, 1, 0, 0]

        head = 0
        while head < len(queue):
            cx, cy = queue[head]
            head += 1
            cluster.append((cx, cy))

            for i in range(4):
                nx, ny = cx + dxs[i], cy + dys[i]
                if 0 <= nx < 16 and 0 <= ny < 14:
                    if self.grid[ny][nx] == color and not visited[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))

        if len(cluster) >= 3:
            for cx, cy in cluster:
                self.grid[cy][cx] = BUBBLE_NONE
            self.score += len(cluster) * 30
            if self.score > self.high_score:
                self.high_score = self.score

            self.remove_floating_islands()

        if self.shots_fired > 0 and (self.shots_fired % 6 == 0):
            for y in range(12, -1, -1):
                for x in range(16):
                    self.grid[y + 1][x] = self.grid[y][x]
            for x in range(16):
                self.grid[0][x] = random.randint(1, 4)

        if self.count_remaining_bubbles() == 0:
            self.state = STATE_VICTORY
            self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt

        if self.state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP):
                self.reset()
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)):
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

            rot_speed = 65.0
            if keys_down & KEY_LEFT:
                self.angle_deg = max(-60.0, self.angle_deg - rot_speed * dt)
            elif keys_down & KEY_RIGHT:
                self.angle_deg = min(60.0, self.angle_deg + rot_speed * dt)

            if keys_pressed & (KEY_A | KEY_B | KEY_UP):
                self.fire_bubble()

            if self.flying.active:
                self.flying.x += self.flying.vx * dt
                self.flying.y += self.flying.vy * dt

                if self.flying.x <= 0.0:
                    self.flying.x = 0.0
                    self.flying.vx = abs(self.flying.vx)
                elif self.flying.x >= 15.0:
                    self.flying.x = 15.0
                    self.flying.vx = -abs(self.flying.vx)

                if self.flying.y <= 0.5:
                    self.snap_and_resolve(self.flying.x, 0.0, self.flying.color)
                else:
                    collided = False
                    for y in range(14):
                        for x in range(16):
                            if self.grid[y][x] != BUBBLE_NONE:
                                dist_sq = (self.flying.x - x) ** 2 + (self.flying.y - y) ** 2
                                if dist_sq < 0.92:
                                    self.snap_and_resolve(self.flying.x, self.flying.y, self.flying.color)
                                    collided = True
                                    break
                        if collided:
                            break

    def render(self) -> bytes:
        for i in range(len(self.frame_buffer)):
            self.frame_buffer[i] = 0

        for y in range(14):
            for x in range(16):
                c = self.grid[y][x]
                if c in COLOR_RGB:
                    idx = (y * 16 + x) * 3
                    self.frame_buffer[idx:idx+3] = bytes(COLOR_RGB[c])

        if self.flying.active:
            fx = int(round(self.flying.x))
            fy = int(round(self.flying.y))
            if 0 <= fx < 16 and 0 <= fy < 16:
                idx = (fy * 16 + fx) * 3
                if self.flying.color in COLOR_RGB:
                    self.frame_buffer[idx:idx+3] = bytes(COLOR_RGB[self.flying.color])

        for x in range(0, 16, 2):
            idx = (13 * 16 + x) * 3
            self.frame_buffer[idx:idx+3] = bytes([192, 57, 43])

        cur_color = COLOR_RGB.get(self.current_color, (255, 255, 255))
        for x in (7, 8):
            idx = (15 * 16 + x) * 3
            self.frame_buffer[idx:idx+3] = bytes(cur_color)

        rad = (self.angle_deg - 90.0) * math.pi / 180.0
        aim_x = int(round(7.5 + 2.0 * math.cos(rad)))
        aim_y = int(round(14.0 + 2.0 * math.sin(rad)))
        if 0 <= aim_x < 16 and 0 <= aim_y < 16:
            idx = (aim_y * 16 + aim_x) * 3
            self.frame_buffer[idx:idx+3] = bytes([255, 255, 255])

        if self.state == STATE_VICTORY:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([46, 204, 113])
        elif self.state == STATE_GAMEOVER:
            for x in range(16):
                idx = (15 * 16 + x) * 3
                self.frame_buffer[idx:idx+3] = bytes([231, 76, 60])

        return bytes(self.frame_buffer)

    def get_status(self) -> Dict[str, Any]:
        remaining = self.count_remaining_bubbles()
        return {
            "score": self.score,
            "state": self.state,
            "remaining_bubbles": remaining,
            "angle_deg": self.angle_deg,
            "progress": 100 if remaining == 0 else max(0, 100 - remaining),
        }
