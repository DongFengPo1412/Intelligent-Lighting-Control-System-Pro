# -*- coding: utf-8 -*-
"""game_085_lemmings_rescue.py —— 目标 #085 旅鼠拯救 (Lemmings Rescue)
机制: 多层地形自动行进 + 高空坠落致死(>6px)/熔岩陷阱 + 三大经典技能(拦截/搭梯/挖掘)
"""

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

LEM_EMPTY = 0
LEM_DIRT = 1
LEM_STEEL = 2
LEM_STAIR = 3
LEM_LAVA = 4

LEM_STATE_WALKING = 0
LEM_STATE_FALLING = 1
LEM_STATE_BLOCKER = 2
LEM_STATE_BUILDER = 3
LEM_STATE_DIGGER = 4


class LemmingUnit:
    def __init__(self, x: int, y: int):
        self.spawned = False
        self.alive = False
        self.saved = False
        self.x = x
        self.y = y
        self.dir = 1
        self.state = LEM_STATE_FALLING
        self.fall_cells = 0
        self.bricks_left = 0
        self.move_accum = 0.0
        self.skill_timer = 0.0


class Game085LemmingsRescue(BaseCartridge):
    difficulty_supported = True
    NUM_LEMMINGS = 5

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.stage = 1
        self.spawned_count = 0
        self.saved_count = 0
        self.dead_count = 0
        self.spawn_timer = 0.4
        self.stage_timer = (70.,55.,45.)[self.difficulty]
        self.hatch_x = 2
        self.hatch_y = 2
        self.exit_x = 13
        self.exit_y = 13
        self.cursor_x = 6
        self.cursor_y = 4
        self.selected_skill = 2  # 0=BLOCKER, 1=BUILDER, 2=DIGGER
        self.move_cooldown = 0.0
        self.terrain: List[List[int]] = [[LEM_EMPTY] * 16 for _ in range(16)]
        self.lemmings: List[LemmingUnit] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 85

    @property
    def name(self) -> str:
        return "旅鼠拯救"

    @property
    def english_name(self) -> str:
        return "Lemmings Rescue"

    @property
    def release_year(self) -> int:
        return 1991

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "群体自动寻路与拦截搭梯挖掘地形改造救援"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def is_solid(self, x: int, y: int) -> bool:
        if x < 0 or x >= 16 or y < 0 or y >= 16:
            return True
        return self.terrain[y][x] in (LEM_DIRT, LEM_STEEL, LEM_STAIR)

    def _has_blocker_at(self, x: int, y: int, ignore_idx: int) -> bool:
        for i, lm in enumerate(self.lemmings):
            if i == ignore_idx:
                continue
            if lm.alive and lm.state == LEM_STATE_BLOCKER:
                if lm.x == x and lm.y in (y, y - 1):
                    return True
        return False

    def load_stage(self, stg: int) -> None:
        self.stage = stg
        self.spawned_count = 0
        self.saved_count = 0
        self.dead_count = 0
        self.spawn_timer = 0.4
        self.stage_timer = (70.,55.,45.)[self.difficulty]

        self.terrain = [[LEM_EMPTY] * 16 for _ in range(16)]
        for y in range(1, 15):
            self.terrain[y][0] = LEM_STEEL
            self.terrain[y][15] = LEM_STEEL
        for x in range(16):
            self.terrain[15][x] = LEM_LAVA

        if stg == 1:
            self.hatch_x, self.hatch_y = 2, 2
            self.exit_x, self.exit_y = 13, 13
            self.cursor_x, self.cursor_y = 6, 4
            self.selected_skill = 2
            for x in range(1, 11):
                self.terrain[5][x] = LEM_DIRT
            for x in range(4, 10):
                self.terrain[9][x] = LEM_DIRT
            for x in range(8, 15):
                self.terrain[14][x] = LEM_STEEL
        elif stg == 2:
            self.hatch_x, self.hatch_y = 2, 8
            self.exit_x, self.exit_y = 13, 8
            self.cursor_x, self.cursor_y = 7, 11
            self.selected_skill = 1
            for x in range(1, 8):
                self.terrain[12][x] = LEM_STEEL
            for x in range(11, 15):
                self.terrain[9][x] = LEM_STEEL
        else:
            self.hatch_x, self.hatch_y = 4, 2
            self.exit_x, self.exit_y = 13, 9
            self.cursor_x, self.cursor_y = 6, 4
            self.selected_skill = 2
            for x in range(2, 9):
                self.terrain[5][x] = LEM_DIRT
            self.terrain[3][8] = LEM_STEEL
            self.terrain[4][8] = LEM_STEEL
            for x in range(4, 8):
                self.terrain[10][x] = LEM_STEEL
            self.terrain[8][4] = LEM_STEEL
            self.terrain[9][4] = LEM_STEEL
            for x in range(11, 15):
                self.terrain[10][x] = LEM_STEEL

        self.lemmings = [LemmingUnit(self.hatch_x, self.hatch_y) for _ in range(self.NUM_LEMMINGS)]

    def _setup_match(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.move_cooldown = 0.0
        self.load_stage(1)

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

    def _assign_skill_at_cursor(self) -> None:
        best_idx = -1
        best_d2 = 100
        for i, lm in enumerate(self.lemmings):
            if not lm.alive or lm.saved:
                continue
            if lm.state in (LEM_STATE_FALLING, LEM_STATE_BLOCKER):
                continue
            d2 = (lm.x - self.cursor_x) ** 2 + (lm.y - self.cursor_y) ** 2
            if d2 <= 6 and d2 < best_d2:
                best_d2 = d2
                best_idx = i
        if best_idx < 0:
            return

        self.emit_sound("action",self.selected_skill)
        lm = self.lemmings[best_idx]
        if self.selected_skill == 0:
            lm.state = LEM_STATE_BLOCKER
            lm.skill_timer = 0.0
        elif self.selected_skill == 1:
            lm.state = LEM_STATE_BUILDER
            lm.bricks_left = 4
            lm.skill_timer = 0.0
        elif self.selected_skill == 2:
            lm.state = LEM_STATE_DIGGER
            lm.skill_timer = 0.0

    def _update_lemming(self, idx: int, dt: float) -> None:
        lm = self.lemmings[idx]
        if not lm.alive or lm.saved:
            return

        if lm.x == self.exit_x and lm.y in (self.exit_y, self.exit_y - 1):
            lm.saved = True
            lm.alive = False
            self.saved_count += 1
            self._add_score(100)
            return

        if lm.y >= 15 or self.terrain[lm.y][lm.x] == LEM_LAVA:
            lm.alive = False
            self.dead_count += 1
            return

        if lm.state == LEM_STATE_FALLING:
            if self.is_solid(lm.x, lm.y + 1):
                if lm.fall_cells > 6:
                    lm.alive = False
                    self.dead_count += 1
                    return
                lm.fall_cells = 0
                lm.state = LEM_STATE_WALKING
                lm.move_accum = 0.0
                return

            lm.move_accum += 8.0 * dt
            while lm.move_accum >= 1.0:
                lm.move_accum -= 1.0
                lm.y += 1
                lm.fall_cells += 1
                if lm.y >= 15 or self.terrain[lm.y][lm.x] == LEM_LAVA:
                    lm.alive = False
                    self.dead_count += 1
                    return
                if lm.x == self.exit_x and lm.y in (self.exit_y, self.exit_y - 1) and lm.fall_cells <= 6:
                    lm.saved = True
                    lm.alive = False
                    self.saved_count += 1
                    self._add_score(100)
                    return
                if self.is_solid(lm.x, lm.y + 1):
                    if lm.fall_cells > 6:
                        lm.alive = False
                        self.dead_count += 1
                    else:
                        lm.fall_cells = 0
                        lm.state = LEM_STATE_WALKING
                        lm.move_accum = 0.0
                    return
            return

        if not self.is_solid(lm.x, lm.y + 1):
            lm.state = LEM_STATE_FALLING
            lm.fall_cells = 0
            lm.move_accum = 0.0
            return

        if lm.state == LEM_STATE_BLOCKER:
            return

        if lm.state == LEM_STATE_BUILDER:
            lm.skill_timer += dt
            if lm.skill_timer >= 0.28:
                lm.skill_timer -= 0.28
                bx = lm.x + lm.dir
                by = lm.y
                if bx <= 0 or bx >= 15 or self.is_solid(bx, by):
                    lm.state = LEM_STATE_WALKING
                    lm.move_accum = 0.0
                else:
                    self.terrain[by][bx] = LEM_STAIR
                    lm.bricks_left -= 1
                    if by - 1 >= 1 and not self.is_solid(bx, by - 1):
                        lm.x = bx
                        lm.y = by - 1
                        if lm.x == self.exit_x and lm.y in (self.exit_y, self.exit_y - 1):
                            lm.saved = True
                            lm.alive = False
                            self.saved_count += 1
                            self._add_score(100)
                            return
                        if lm.bricks_left <= 0:
                            lm.state = LEM_STATE_WALKING
                            lm.move_accum = 0.0
                    else:
                        lm.state = LEM_STATE_WALKING
                        lm.move_accum = 0.0
            return

        if lm.state == LEM_STATE_DIGGER:
            lm.skill_timer += dt
            if lm.skill_timer >= 0.30:
                lm.skill_timer -= 0.30
                if lm.y + 1 >= 15 or self.terrain[lm.y + 1][lm.x] == LEM_STEEL:
                    lm.state = LEM_STATE_WALKING
                    lm.move_accum = 0.0
                elif self.terrain[lm.y + 1][lm.x] in (LEM_DIRT, LEM_STAIR):
                    self.terrain[lm.y + 1][lm.x] = LEM_EMPTY
                    lm.y += 1
                    if not self.is_solid(lm.x, lm.y + 1):
                        lm.state = LEM_STATE_FALLING
                        lm.fall_cells = 0
                        lm.move_accum = 0.0
                else:
                    lm.state = LEM_STATE_FALLING
                    lm.fall_cells = 0
                    lm.move_accum = 0.0
            return

        lm.move_accum += 2.4 * dt
        if lm.move_accum >= 1.0:
            lm.move_accum -= 1.0
            nx = lm.x + lm.dir
            if nx <= 0 or nx >= 15 or self._has_blocker_at(nx, lm.y, idx):
                lm.dir = -lm.dir
            elif not self.is_solid(nx, lm.y):
                lm.x = nx
                if lm.x == self.exit_x and lm.y in (self.exit_y, self.exit_y - 1):
                    lm.saved = True
                    lm.alive = False
                    self.saved_count += 1
                    self._add_score(100)
                    return
                if not self.is_solid(lm.x, lm.y + 1):
                    lm.state = LEM_STATE_FALLING
                    lm.fall_cells = 0
                    lm.move_accum = 0.0
            else:
                if (
                    lm.y - 1 >= 1
                    and not self.is_solid(nx, lm.y - 1)
                    and not self.is_solid(lm.x, lm.y - 1)
                    and not self._has_blocker_at(nx, lm.y - 1, idx)
                ):
                    lm.x = nx
                    lm.y -= 1
                    if lm.x == self.exit_x and lm.y in (self.exit_y, self.exit_y - 1):
                        lm.saved = True
                        lm.alive = False
                        self.saved_count += 1
                        self._add_score(100)
                        return
                else:
                    lm.dir = -lm.dir

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
        dpad_trig = keys_pressed & dpad_mask
        if not dpad_trig and self.move_cooldown <= 0.0 and (keys_down & dpad_mask):
            dpad_trig = keys_down & dpad_mask
            self.move_cooldown = 0.14
        elif dpad_trig:
            self.move_cooldown = 0.18

        if dpad_trig & KEY_LEFT:
            if self.cursor_x > 1:
                self.cursor_x -= 1
        elif dpad_trig & KEY_RIGHT:
            if self.cursor_x < 14:
                self.cursor_x += 1
        elif dpad_trig & KEY_UP:
            if self.cursor_y > 1:
                self.cursor_y -= 1
        elif dpad_trig & KEY_DOWN:
            if self.cursor_y < 14:
                self.cursor_y += 1

        if keys_pressed & KEY_B:
            self.selected_skill = (self.selected_skill + 1) % 3
        if keys_pressed & KEY_A:
            self._assign_skill_at_cursor()

        if self.spawned_count < self.NUM_LEMMINGS:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0.0:
                lm = self.lemmings[self.spawned_count]
                lm.spawned = True
                lm.alive = True
                lm.saved = False
                lm.x = self.hatch_x
                lm.y = self.hatch_y
                lm.dir = 1
                lm.state = LEM_STATE_FALLING
                lm.fall_cells = 0
                lm.move_accum = 0.0
                lm.skill_timer = 0.0
                self.spawned_count += 1
                self.spawn_timer = 1.45

        for i in range(self.NUM_LEMMINGS):
            self._update_lemming(i, dt)

        if self.dead_count > self.NUM_LEMMINGS-(2,3,4)[self.difficulty]:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return

        self.stage_timer -= dt
        if self.stage_timer <= 0.0:
            if self.saved_count >= (2,3,4)[self.difficulty]:
                if self.stage >= 3:
                    self._state = STATE_VICTORY
                    self.state_timer = 0.0
                else:
                    self.load_stage(self.stage + 1)
            else:
                self._state = STATE_GAMEOVER
                self.state_timer = 0.0
            return

        if self.spawned_count >= self.NUM_LEMMINGS:
            active_mobile = sum(
                1 for lm in self.lemmings if lm.alive and lm.state != LEM_STATE_BLOCKER
            )
            if active_mobile == 0:
                if self.saved_count >= (2,3,4)[self.difficulty]:
                    if self.stage >= 3:
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
                    else:
                        self.load_stage(self.stage + 1)
                else:
                    self._state = STATE_GAMEOVER
                    self.state_timer = 0.0

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)

        for y in range(16):
            for x in range(16):
                set_pixel(fb, x, y, 12, 10, 24)

        for y in range(1, 16):
            for x in range(16):
                t = self.terrain[y][x]
                if t == LEM_DIRT:
                    if ((x + y) & 1) == 0:
                        set_pixel(fb, x, y, 150, 95, 45)
                    else:
                        set_pixel(fb, x, y, 128, 78, 36)
                elif t == LEM_STEEL:
                    set_pixel(fb, x, y, 95, 105, 120)
                elif t == LEM_STAIR:
                    set_pixel(fb, x, y, 245, 200, 45)
                elif t == LEM_LAVA:
                    flick = 120 + ((int(self.anim_timer * 8.0) + x) % 2) * 80
                    set_pixel(fb, x, y, 255, flick // 2, 15)

        set_pixel(fb, self.hatch_x, self.hatch_y - 1, 210, 120, 255)
        set_pixel(fb, self.hatch_x, self.hatch_y, 140, 70, 190)

        set_pixel(fb, self.exit_x, self.exit_y - 1, 255, 215, 40)
        set_pixel(fb, self.exit_x, self.exit_y, 40, 235, 220)

        for lm in self.lemmings:
            if not lm.alive or lm.saved:
                continue
            if lm.state == LEM_STATE_BLOCKER:
                set_pixel(fb, lm.x, lm.y, 255, 95, 35)
            elif lm.state == LEM_STATE_BUILDER:
                set_pixel(fb, lm.x, lm.y, 120, 255, 90)
            elif lm.state == LEM_STATE_DIGGER:
                set_pixel(fb, lm.x, lm.y, 50, 245, 255)
            else:
                set_pixel(fb, lm.x, lm.y, 60, 245, 85)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            if (int(self.anim_timer * 6.0) % 2) == 0:
                set_pixel(fb, self.cursor_x, self.cursor_y, 255, 255, 255)

        for s in range(5):
            if s < self.saved_count:
                set_pixel(fb, s, 0, 50, 245, 90)
            elif s >= 5 - self.dead_count:
                set_pixel(fb, s, 0, 180, 35, 35)
            else:
                set_pixel(fb, s, 0, 35, 50, 40)

        for k in range(3):
            if k < self.stage:
                set_pixel(fb, 8 + k, 0, 220, 190, 60)

        if self.selected_skill == 0:
            set_pixel(fb, 14, 0, 255, 90, 30)
            set_pixel(fb, 15, 0, 255, 90, 30)
        elif self.selected_skill == 1:
            set_pixel(fb, 14, 0, 250, 205, 35)
            set_pixel(fb, 15, 0, 250, 205, 35)
        else:
            set_pixel(fb, 14, 0, 0, 230, 255)
            set_pixel(fb, 15, 0, 0, 230, 255)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        prog = min(100, (self.stage - 1) * 33 + (self.saved_count * 34) // 3)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": max(0, self.NUM_LEMMINGS - self.dead_count),
            "state": self._state,
            "progress": prog,
        }
