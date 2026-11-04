"""game_038_bomberman.py —— 目标 #038 炸弹人 (Bomberman 1983)
定时炸弹放置 + 十字烈焰冲击波 + 软砖碎裂 + 巡逻怪爆破消灭
"""

import random
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

TILE_EMPTY = 0
TILE_HARD_WALL = 1
TILE_SOFT_BRICK = 2


class Bomb:
    def __init__(self, gx: int, gy: int, timer: float = 2.4, bomb_range: int = 2):
        self.active = True
        self.gx = gx
        self.gy = gy
        self.timer = timer
        self.range = bomb_range


class Flame:
    def __init__(self, x: int, y: int, timer: float = 0.45):
        self.x = x
        self.y = y
        self.timer = timer


class Enemy:
    def __init__(self, x: float, y: float, speed: float = 2.2):
        self.alive = True
        self.x = x
        self.y = y
        self.dir_x = 0
        self.dir_y = -1
        self.speed = speed


class Game038Bomberman(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.player_x = 1.0
        self.player_y = 1.0
        self.lives = 3
        self.map = [[TILE_EMPTY] * 16 for _ in range(16)]
        self.bomb: Bomb = None
        self.flames: List[Flame] = []
        self.enemies: List[Enemy] = []
        self.remaining_enemies = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 38

    @property
    def name(self) -> str:
        return "炸弹人"

    @property
    def english_name(self) -> str:
        return "Bomberman 1983"

    @property
    def release_year(self) -> int:
        return 1983

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "定时炸弹布置与十字爆破冲击"

    def init(self) -> None:
        self.reset()

    def _reset_player(self):
        self.player_x = 1.0
        self.player_y = 1.0
        self.bomb = None
        self.flames = []

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.remaining_enemies = 3

        self.map = [[TILE_EMPTY] * 16 for _ in range(16)]
        for y in range(16):
            for x in range(16):
                if x == 0 or x == 15 or y == 0 or y == 15:
                    self.map[y][x] = TILE_HARD_WALL
                elif x % 2 == 0 and y % 2 == 0:
                    self.map[y][x] = TILE_HARD_WALL
                else:
                    if x <= 2 and y <= 2:
                        self.map[y][x] = TILE_EMPTY
                    elif (x, y) in ((13, 1), (1, 13), (13, 13)):
                        self.map[y][x] = TILE_EMPTY
                    else:
                        self.map[y][x] = TILE_SOFT_BRICK if ((x * 7 + y * 13) % 10 < 5) else TILE_EMPTY

        self.enemies = [
            Enemy(13.0, 1.0, 2.4),
            Enemy(1.0, 13.0, 2.2),
            Enemy(13.0, 13.0, 2.0),
        ]
        self._reset_player()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.remaining_enemies = 3
            self.map = [[TILE_EMPTY] * 16 for _ in range(16)]
            for y in range(16):
                for x in range(16):
                    if x == 0 or x == 15 or y == 0 or y == 15:
                        self.map[y][x] = TILE_HARD_WALL
                    elif x % 2 == 0 and y % 2 == 0:
                        self.map[y][x] = TILE_HARD_WALL
                    else:
                        if x <= 2 and y <= 2:
                            self.map[y][x] = TILE_EMPTY
                        elif (x, y) in ((13, 1), (1, 13), (13, 13)):
                            self.map[y][x] = TILE_EMPTY
                        else:
                            self.map[y][x] = TILE_SOFT_BRICK if ((x * 7 + y * 13) % 10 < 5) else TILE_EMPTY
            self.enemies = [
                Enemy(13.0, 1.0, 2.4),
                Enemy(1.0, 13.0, 2.2),
                Enemy(13.0, 13.0, 2.0),
            ]
            self._reset_player()

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _is_walkable(self, gx: int, gy: int, allow_bomb: bool) -> bool:
        if gx < 0 or gx >= 16 or gy < 0 or gy >= 16:
            return False
        if self.map[gy][gx] in (TILE_HARD_WALL, TILE_SOFT_BRICK):
            return False
        if not allow_bomb and self.bomb and self.bomb.active and self.bomb.gx == gx and self.bomb.gy == gy:
            return False
        return True

    def _explode_bomb(self):
        if not self.bomb:
            return
        cx, cy = self.bomb.gx, self.bomb.gy
        self.bomb = None
        self.flames = [Flame(cx, cy)]

        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for dx, dy in dirs:
            for step in range(1, 3):
                tx = cx + dx * step
                ty = cy + dy * step
                if not (0 <= tx < 16 and 0 <= ty < 16):
                    break
                if self.map[ty][tx] == TILE_HARD_WALL:
                    break
                if self.map[ty][tx] == TILE_SOFT_BRICK:
                    self.map[ty][tx] = TILE_EMPTY
                    self.flames.append(Flame(tx, ty))
                    self._score += 20
                    if self._score > self._high_score:
                        self._high_score = self._score
                    break
                self.flames.append(Flame(tx, ty))

        self._apply_flame_damage()

    def _apply_flame_damage(self):
        """火焰存续期间(0.45s)持续致命: 走进残留火焰的玩家/敌人同样会被消灭。"""
        for fl in list(self.flames):
            for e in self.enemies:
                if e.alive and int(round(e.x)) == fl.x and int(round(e.y)) == fl.y:
                    e.alive = False
                    self.remaining_enemies -= 1
                    self._score += 100
                    if self._score > self._high_score:
                        self._high_score = self._score
                    if self.remaining_enemies <= 0:
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
                        return

            if int(round(self.player_x)) == fl.x and int(round(self.player_y)) == fl.y:
                if self.lives > 1:
                    self.lives -= 1
                    self._reset_player()  # 清空火焰并回到出生点, 本帧不再重复判定
                else:
                    self.lives = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                return

    def _move_enemy(self, e: Enemy, dt: float):
        move_step = e.speed * dt
        cgx, cgy = int(round(e.x)), int(round(e.y))
        if abs(e.x - cgx) < move_step and abs(e.y - cgy) < move_step:
            e.x = float(cgx)
            e.y = float(cgy)
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            valid = []
            for ndx, ndy in dirs:
                if ndx == -e.dir_x and ndy == -e.dir_y:
                    continue
                if self._is_walkable(cgx + ndx, cgy + ndy, False):
                    valid.append((ndx, ndy))
            if valid:
                e.dir_x, e.dir_y = random.choice(valid)
            else:
                e.dir_x, e.dir_y = -e.dir_x, -e.dir_y

        e.x += e.dir_x * move_step
        e.y += e.dir_y * move_step

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
                self.start()
            return

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        if self._state == STATE_PLAYING:
            if keys_pressed & KEY_START:
                self._state = STATE_PAUSED
                return

            p_speed = 3.6
            move_step = p_speed * dt
            gx, gy = int(round(self.player_x)), int(round(self.player_y))

            if keys_down & KEY_UP:
                if self._is_walkable(gx, gy - 1, True) or self.player_y > gy:
                    self.player_y -= move_step
            elif keys_down & KEY_DOWN:
                if self._is_walkable(gx, gy + 1, True) or self.player_y < gy:
                    self.player_y += move_step
            elif keys_down & KEY_LEFT:
                if self._is_walkable(gx - 1, gy, True) or self.player_x > gx:
                    self.player_x -= move_step
            elif keys_down & KEY_RIGHT:
                if self._is_walkable(gx + 1, gy, True) or self.player_x < gx:
                    self.player_x += move_step

            self.player_x = max(1.0, min(14.0, self.player_x))
            self.player_y = max(1.0, min(14.0, self.player_y))

            if (keys_pressed & (KEY_A | KEY_B)) and not self.bomb:
                self.bomb = Bomb(int(round(self.player_x)), int(round(self.player_y)))

            if self.bomb:
                self.bomb.timer -= dt
                if self.bomb.timer <= 0.0:
                    self._explode_bomb()

            for fl in self.flames:
                fl.timer -= dt
            self.flames = [fl for fl in self.flames if fl.timer > 0.0]
            if self.flames:
                self._apply_flame_damage()
                if self._state != STATE_PLAYING:
                    return

            for e in self.enemies:
                if e.alive:
                    self._move_enemy(e, dt)
                    if abs(e.x - self.player_x) < 0.7 and abs(e.y - self.player_y) < 0.7:
                        if self.lives > 1:
                            self.lives -= 1
                            self._reset_player()
                        else:
                            self.lives = 0
                            self._state = STATE_GAMEOVER
                            self.state_timer = 0.0
                            return

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 3
                if self.map[y][x] == TILE_HARD_WALL:
                    fb[idx : idx + 3] = bytes([70, 80, 95])
                elif self.map[y][x] == TILE_SOFT_BRICK:
                    fb[idx : idx + 3] = bytes([180, 100, 50])
                else:
                    fb[idx : idx + 3] = bytes([20, 30, 20])

        if self.bomb and self.bomb.active:
            idx = (self.bomb.gy * 16 + self.bomb.gx) * 3
            flash = int(self.bomb.timer * 6.0) % 2 == 0
            fb[idx : idx + 3] = bytes([255, 255, 255]) if flash else bytes([231, 76, 60])

        for fl in self.flames:
            if 0 <= fl.x < 16 and 0 <= fl.y < 16:
                idx = (fl.y * 16 + fl.x) * 3
                fb[idx : idx + 3] = bytes([255, 140, 0])

        for e in self.enemies:
            if e.alive:
                ex, ey = int(round(e.x)), int(round(e.y))
                if 0 <= ex < 16 and 0 <= ey < 16:
                    idx = (ey * 16 + ex) * 3
                    fb[idx : idx + 3] = bytes([255, 50, 80])

        px, py = int(round(self.player_x)), int(round(self.player_y))
        if 0 <= px < 16 and 0 <= py < 16:
            idx = (py * 16 + px) * 3
            fb[idx : idx + 3] = bytes([255, 255, 255])

        for i in range(min(3, self.lives)):
            idx = (i * 2 + 1) * 3
            fb[idx : idx + 3] = bytes([255, 255, 255])

        if self._state == STATE_PAUSED:
            for y in range(6, 10):
                for col in (6, 9):
                    idx = (y * 16 + col) * 3
                    fb[idx : idx + 3] = bytes([250, 250, 250])

        return fb

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.lives,
            "state": self._state,
            "progress": min(100, (3 - self.remaining_enemies) * 100 // 3),
        }
