# -*- coding: utf-8 -*-
"""game_083_tower_defense.py —— 目标 #083 路径塔防 (Path Tower Defense)
机制: S形蜿蜒道路 + 三系防御塔建造/升级(激光/冰霜减速/火炮溅射) + 四波敌军攻防
"""

import math
from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen, set_pixel

WAYPOINTS = [
    (0, 2),
    (13, 2),
    (13, 7),
    (2, 7),
    (2, 13),
    (15, 13),
]

TOWER_COSTS = (25, 35, 45)
TOWER_RANGES = (3.6, 3.3, 3.8)
TOWER_INTERVALS = (0.40, 0.65, 0.95)
TOWER_DAMAGES = (14.0, 9.0, 24.0)


class TDTower:
    def __init__(self, x: int, y: int, ttype: int):
        self.active = True
        self.x = x
        self.y = y
        self.type = ttype  # 0=Laser Cyan, 1=Frost Blue, 2=Cannon Orange
        self.level = 1
        self.cooldown = 0.0
        self.beam_timer = 0.0
        self.target_x = float(x)
        self.target_y = float(y)


class TDEnemy:
    def __init__(self, hp: float, speed: float, reward: int, is_boss: bool = False):
        self.alive = True
        self.x = float(WAYPOINTS[0][0])
        self.y = float(WAYPOINTS[0][1])
        self.wp_idx = 1
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.slow_timer = 0.0
        self.reward = reward
        self.is_boss = is_boss


class Game083TowerDefense(BaseCartridge):
    MAX_TOWERS = 16
    MAX_ENEMIES = 10

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.gold = 70
        self.base_hp = 5
        self.wave = 1
        self.spawned_in_wave = 0
        self.total_in_wave = 4
        self.spawn_timer = 0.6
        self.wave_delay = 0.0
        self.cursor_x = 5
        self.cursor_y = 4
        self.selected_tower_type = 0
        self.move_cooldown = 0.0
        self.towers: List[TDTower] = []
        self.enemies: List[TDEnemy] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 83

    @property
    def name(self) -> str:
        return "路径塔防"

    @property
    def english_name(self) -> str:
        return "Path Tower Defense"

    @property
    def release_year(self) -> int:
        return 2007

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "S形路径选址建塔与三系防御塔波次阻击"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def is_road(self, x: int, y: int) -> bool:
        if y == 2 and 0 <= x <= 13:
            return True
        if x == 13 and 2 <= y <= 7:
            return True
        if y == 7 and 2 <= x <= 13:
            return True
        if x == 2 and 7 <= y <= 13:
            return True
        if y == 13 and 2 <= x <= 15:
            return True
        return False

    def find_tower_at(self, x: int, y: int) -> int:
        for i, t in enumerate(self.towers):
            if t.active and t.x == x and t.y == y:
                return i
        return -1

    def _start_wave(self, w: int) -> None:
        self.wave = w
        self.spawned_in_wave = 0
        if w == 1:
            self.total_in_wave = 4
        elif w == 2:
            self.total_in_wave = 6
        elif w == 3:
            self.total_in_wave = 7
        else:
            self.total_in_wave = 8
        self.spawn_timer = 0.6
        self.wave_delay = 0.0

    def _setup_match(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.gold = 70
        self.base_hp = 5
        self.cursor_x = 5
        self.cursor_y = 4
        self.selected_tower_type = 0
        self.move_cooldown = 0.0
        self.towers = []
        self.enemies = []
        self._start_wave(1)

    def init(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._setup_match(STATE_TITLE)

    def start(self) -> None:
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._setup_match(STATE_PLAYING)

    def pause(self) -> None:
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self) -> None:
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _spawn_enemy(self) -> None:
        alive_cnt = sum(1 for e in self.enemies if e.alive)
        if alive_cnt >= self.MAX_ENEMIES:
            return
        boss = self.wave == 4 and self.spawned_in_wave == self.total_in_wave - 1
        base_hp, spd, rew = 28.0, 2.6, 12
        if self.wave == 2:
            base_hp, spd, rew = 42.0, 3.0, 14
        elif self.wave == 3:
            base_hp, spd, rew = 60.0, 3.3, 16
        elif self.wave >= 4:
            base_hp, spd, rew = 80.0, 3.5, 20
        if boss:
            base_hp, spd, rew = 160.0, 2.4, 35
        self.enemies.append(TDEnemy(base_hp, spd, rew, boss))
        self.spawned_in_wave += 1

    def _handle_build_or_upgrade(self) -> None:
        if self.cursor_y < 1 or self.is_road(self.cursor_x, self.cursor_y):
            return
        idx = self.find_tower_at(self.cursor_x, self.cursor_y)
        if idx >= 0:
            tw = self.towers[idx]
            if tw.level < 3:
                upg_cost = 20 * tw.level
                if self.gold >= upg_cost:
                    self.gold -= upg_cost
                    tw.level += 1
        elif len(self.towers) < self.MAX_TOWERS:
            cost = TOWER_COSTS[self.selected_tower_type]
            if self.gold >= cost:
                self.gold -= cost
                self.towers.append(TDTower(self.cursor_x, self.cursor_y, self.selected_tower_type))

    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        if dt > 0.05:
            dt = 0.05

        if self._state == STATE_PAUSED:
            if keys_pressed & KEY_START:
                self._state = STATE_PLAYING
            return

        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_A | KEY_B)):
                self.start()
            return

        if keys_pressed & KEY_START:
            self._state = STATE_PAUSED
            return

        if self.move_cooldown > 0.0:
            self.move_cooldown -= dt

        dpad_mask = KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN
        dpad_trigger = keys_pressed & dpad_mask
        if not dpad_trigger and self.move_cooldown <= 0.0 and (keys_down & dpad_mask):
            dpad_trigger = keys_down & dpad_mask
            self.move_cooldown = 0.14
        elif dpad_trigger:
            self.move_cooldown = 0.18

        if dpad_trigger & KEY_LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
        elif dpad_trigger & KEY_RIGHT:
            if self.cursor_x < 15:
                self.cursor_x += 1
        elif dpad_trigger & KEY_UP:
            if self.cursor_y > 1:
                self.cursor_y -= 1
        elif dpad_trigger & KEY_DOWN:
            if self.cursor_y < 15:
                self.cursor_y += 1

        if keys_pressed & KEY_B:
            self.selected_tower_type = (self.selected_tower_type + 1) % 3
        if keys_pressed & KEY_A:
            self._handle_build_or_upgrade()

        if self.spawned_in_wave < self.total_in_wave:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0.0:
                self._spawn_enemy()
                self.spawn_timer = max(0.75, 1.10 - (self.wave - 1) * 0.10)

        for e in self.enemies:
            if not e.alive:
                continue
            if e.slow_timer > 0.0:
                e.slow_timer = max(0.0, e.slow_timer - dt)
            spd = e.speed * (0.5 if e.slow_timer > 0.0 else 1.0)
            move_rem = spd * dt

            while move_rem > 0.0 and e.wp_idx < len(WAYPOINTS):
                tx, ty = float(WAYPOINTS[e.wp_idx][0]), float(WAYPOINTS[e.wp_idx][1])
                dx, dy = tx - e.x, ty - e.y
                dist = math.hypot(dx, dy)
                if dist <= move_rem:
                    e.x, e.y = tx, ty
                    move_rem -= dist
                    e.wp_idx += 1
                else:
                    e.x += (dx / dist) * move_rem
                    e.y += (dy / dist) * move_rem
                    move_rem = 0.0

            if e.wp_idx >= len(WAYPOINTS):
                e.alive = False
                if self.base_hp > 1:
                    self.base_hp -= 1
                else:
                    self.base_hp = 0
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0
                    return

        for tw in self.towers:
            if not tw.active:
                continue
            if tw.beam_timer > 0.0:
                tw.beam_timer -= dt
            if tw.cooldown > 0.0:
                tw.cooldown -= dt
            if tw.cooldown > 0.0:
                continue

            rng = TOWER_RANGES[tw.type] + (tw.level - 1) * 0.4
            best_e = -1
            best_prog = -1.0
            for idx, e in enumerate(self.enemies):
                if not e.alive:
                    continue
                dx = e.x - tw.x
                dy = e.y - tw.y
                if dx * dx + dy * dy <= rng * rng:
                    prog = e.wp_idx * 20.0
                    if e.wp_idx < len(WAYPOINTS):
                        wx = WAYPOINTS[e.wp_idx][0] - e.x
                        wy = WAYPOINTS[e.wp_idx][1] - e.y
                        prog -= math.hypot(wx, wy)
                    if prog > best_prog:
                        best_prog = prog
                        best_e = idx

            if best_e >= 0:
                target = self.enemies[best_e]
                dmg_mult = 1.0 + 0.5 * (tw.level - 1)
                dmg = TOWER_DAMAGES[tw.type] * dmg_mult
                tw.cooldown = TOWER_INTERVALS[tw.type] * (1.0 - 0.12 * (tw.level - 1))
                tw.beam_timer = 0.14
                tw.target_x = target.x
                tw.target_y = target.y

                if tw.type == 1:
                    target.slow_timer = 2.0

                if tw.type == 2:
                    cx, cy = target.x, target.y
                    for idx, e in enumerate(self.enemies):
                        if not e.alive:
                            continue
                        if idx == best_e:
                            e.hp -= dmg
                        elif (e.x - cx) ** 2 + (e.y - cy) ** 2 <= 1.8 * 1.8:
                            e.hp -= dmg * 0.65
                        if e.hp <= 0.0:
                            e.alive = False
                            self.gold += e.reward
                            self._add_score(20)
                else:
                    target.hp -= dmg
                    if target.hp <= 0.0:
                        target.alive = False
                        self.gold += target.reward
                        self._add_score(20)

        self.enemies = [e for e in self.enemies if e.alive]

        if self.spawned_in_wave >= self.total_in_wave and not self.enemies:
            if self.wave >= 4:
                self._add_score(100)
                self._state = STATE_VICTORY
                self.state_timer = 0.0
                return
            else:
                self.wave_delay += dt
                if self.wave_delay >= 1.2:
                    self.gold += 15
                    self._start_wave(self.wave + 1)

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)

        for y in range(1, 16):
            for x in range(16):
                if self.is_road(x, y):
                    if ((x + y) & 1) == 0:
                        set_pixel(fb, x, y, 125, 88, 46)
                    else:
                        set_pixel(fb, x, y, 108, 76, 40)
                else:
                    set_pixel(fb, x, y, 18, 46, 22)

        set_pixel(fb, 0, 2, 190, 55, 225)
        pulse = int((math.sin(self.anim_timer * 5.0) + 1.0) * 35.0)
        set_pixel(fb, 15, 13, 0, min(255, 180 + pulse), 255)

        for tw in self.towers:
            if not tw.active:
                continue
            tr, tg, tb = 0, 235, 255
            if tw.type == 1:
                tr, tg, tb = 65, 135, 255
            elif tw.type == 2:
                tr, tg, tb = 255, 135, 20
            if tw.level >= 2:
                tr = tr + (255 - tr) // 3
                tg = tg + (255 - tg) // 3
                tb = tb + (255 - tb) // 3
            set_pixel(fb, tw.x, tw.y, tr, tg, tb)
            if tw.beam_timer > 0.0:
                mx = int(round((tw.x + tw.target_x) * 0.5))
                my = int(round((tw.y + tw.target_y) * 0.5))
                set_pixel(fb, mx, my, tr, tg, tb)

        for e in self.enemies:
            if not e.alive:
                continue
            ex, ey = int(round(e.x)), int(round(e.y))
            if e.is_boss:
                set_pixel(fb, ex, ey, 255, 40, 200)
            elif e.slow_timer > 0.0:
                set_pixel(fb, ex, ey, 110, 200, 255)
            else:
                set_pixel(fb, ex, ey, 240, 50, 45)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            if (int(self.anim_timer * 6.0) % 2) == 0:
                if self.is_road(self.cursor_x, self.cursor_y):
                    set_pixel(fb, self.cursor_x, self.cursor_y, 220, 40, 40)
                else:
                    set_pixel(fb, self.cursor_x, self.cursor_y, 255, 255, 255)

        for h in range(5):
            if h < self.base_hp:
                set_pixel(fb, h, 0, 0, 225, 240)
            else:
                set_pixel(fb, h, 0, 55, 20, 20)

        gold_pips = min(6, self.gold // 15)
        for g in range(6):
            if g < gold_pips:
                set_pixel(fb, 6 + g, 0, 255, 205, 20)
            else:
                set_pixel(fb, 6 + g, 0, 45, 38, 12)

        set_pixel(fb, 13, 0, min(255, 60 * self.wave), 180, 90)
        if self.selected_tower_type == 0:
            set_pixel(fb, 15, 0, 0, 235, 255)
        elif self.selected_tower_type == 1:
            set_pixel(fb, 15, 0, 65, 135, 255)
        else:
            set_pixel(fb, 15, 0, 255, 135, 20)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        denom = self.total_in_wave if self.total_in_wave > 0 else 1
        prog = (self.wave - 1) * 25 + (self.spawned_in_wave * 25) // denom
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": self.base_hp,
            "state": self._state,
            "progress": min(100, prog),
        }
