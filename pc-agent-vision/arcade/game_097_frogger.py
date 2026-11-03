"""game_097_frogger.py —— 目标 #097 青蛙过河 (Frogger 1981)
公路车辆穿梭闪避 + 河流浮木动态附着漂移 + 5穴归巢全胜
"""

from typing import Dict, Any, List
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from .arcade_result_screen import ArcadeResultScreen

HOME_X = [1, 4, 7, 10, 13]


class LaneItem:
    def __init__(self, x: float, width: float):
        self.x = x
        self.width = width


class FrogLane:
    def __init__(
        self,
        speed: float,
        item_w: float,
        initial_xs: List[float],
        is_river: bool,
        r: int,
        g: int,
        b: int,
    ):
        self.speed = speed
        self.item_w = item_w
        self.items = [LaneItem(x, item_w) for x in initial_xs]
        self.is_river = is_river
        self.r = r
        self.g = g
        self.b = b


class Game097Frogger(BaseCartridge):
    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.frog_x = 7.0
        self.frog_y = 14
        self.lives = 3
        self.round_timer = 30.0
        self.homes = [False] * 5
        self.homes_occupied = 0
        self.lanes: Dict[int, FrogLane] = {}
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.reset()

    @property
    def game_id(self) -> int:
        return 97

    @property
    def name(self) -> str:
        return "青蛙过河"

    @property
    def english_name(self) -> str:
        return "Frogger 1981"

    @property
    def release_year(self) -> int:
        return 1981

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "公路穿梭闪避与河流浮木漂移"

    def init(self) -> None:
        self.reset()

    def _setup_lanes(self):
        self.lanes = {
            1: FrogLane(2.8, 3.0, [1.0, 9.0], True, 160, 82, 45),
            2: FrogLane(-2.5, 2.0, [0.0, 6.0, 12.0], True, 230, 126, 34),
            3: FrogLane(1.8, 4.0, [2.0, 10.0], True, 160, 82, 45),
            4: FrogLane(-3.2, 2.0, [3.0, 11.0], True, 230, 126, 34),
            5: FrogLane(2.4, 2.0, [1.0, 7.0, 13.0], True, 160, 82, 45),
            7: FrogLane(-4.5, 1.0, [4.0, 12.0], False, 231, 76, 60),
            8: FrogLane(2.2, 2.0, [2.0, 10.0], False, 236, 240, 241),
            9: FrogLane(-1.6, 3.0, [6.0], False, 241, 196, 15),
            10: FrogLane(3.8, 1.0, [3.0, 11.0], False, 155, 89, 182),
            11: FrogLane(-2.8, 2.0, [2.0, 9.0], False, 52, 152, 219),
            12: FrogLane(4.0, 1.0, [1.0, 7.0, 13.0], False, 230, 126, 34),
        }

    def _reset_frog(self):
        self.frog_x = 7.0
        self.frog_y = 14
        self.round_timer = 30.0

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.lives = 3
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.homes = [False] * 5
        self.homes_occupied = 0
        self._setup_lanes()
        self._reset_frog()

    def start(self):
        if self._state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self._state = STATE_PLAYING
            self._score = 0
            self.lives = 3
            self.state_timer = 0.0
            self.anim_timer = 0.0
            self.homes = [False] * 5
            self.homes_occupied = 0
            self._setup_lanes()
            self._reset_frog()

    def pause(self):
        if self._state == STATE_PLAYING:
            self._state = STATE_PAUSED

    def resume(self):
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING

    def _kill_frog(self):
        if self.lives > 1:
            self.lives -= 1
            self._reset_frog()
        else:
            self.lives = 0
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0

    def update(self, dt: float, keys_down: int, keys_pressed: int):
        if dt > 0.05:
            dt = 0.05
        self.state_timer += dt
        self.anim_timer += dt

        if self._state == STATE_TITLE:
            if keys_pressed & (KEY_START | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.start()
            return

        if self._state in (STATE_GAMEOVER, STATE_VICTORY):
            if self.state_timer > 0.5 and (keys_pressed & (KEY_START | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
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

            self.round_timer -= dt
            if self.round_timer <= 0.0:
                self._kill_frog()
                return

            if keys_pressed & KEY_UP:
                if self.frog_y > 0:
                    self.frog_y -= 1
                    self._score += 10
                    if self._score > self._high_score:
                        self._high_score = self._score
            elif keys_pressed & KEY_DOWN:
                if self.frog_y < 14:
                    self.frog_y += 1
            elif keys_pressed & KEY_LEFT:
                if self.frog_x > 0.5:
                    self.frog_x -= 1.0
            elif keys_pressed & KEY_RIGHT:
                if self.frog_x < 14.5:
                    self.frog_x += 1.0

            for lane in self.lanes.values():
                for item in lane.items:
                    item.x += lane.speed * dt
                    if lane.speed > 0 and item.x > 16.0:
                        item.x -= 16.0 + item.width + 2.0
                    elif lane.speed < 0 and (item.x + item.width) < 0.0:
                        item.x += 16.0 + item.width + 2.0

            if 1 <= self.frog_y <= 5:
                lane = self.lanes[self.frog_y]
                on_log = False
                for item in lane.items:
                    if (item.x - 0.4) <= self.frog_x <= (item.x + item.width - 0.6):
                        on_log = True
                        break
                if on_log:
                    self.frog_x += lane.speed * dt
                    if not (0.0 <= self.frog_x <= 15.0):
                        self._kill_frog()
                        return
                else:
                    self._kill_frog()
                    return

            if 7 <= self.frog_y <= 12:
                lane = self.lanes[self.frog_y]
                for item in lane.items:
                    if (item.x - 0.6) <= self.frog_x <= (item.x + item.width - 0.4):
                        self._kill_frog()
                        return

            if self.frog_y == 0:
                home_idx = -1
                for i, hx in enumerate(HOME_X):
                    if abs(self.frog_x - hx) < 0.8:
                        home_idx = i
                        break
                if home_idx >= 0 and not self.homes[home_idx]:
                    self.homes[home_idx] = True
                    self.homes_occupied += 1
                    self._score += 200 + int(self.round_timer) * 10
                    if self._score > self._high_score:
                        self._high_score = self._score
                    if self.homes_occupied >= 5:
                        self._state = STATE_VICTORY
                        self.state_timer = 0.0
                        return
                    else:
                        self._reset_frog()
                else:
                    self._kill_frog()
                    return

    def render(self) -> bytearray:
        fb = bytearray(16 * 16 * 3)

        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        for x in range(16):
            fb[x * 3 : x * 3 + 3] = bytes([34, 139, 34])
        for i, hx in enumerate(HOME_X):
            idx = hx * 3
            fb[idx : idx + 3] = bytes([46, 204, 113]) if self.homes[i] else bytes([20, 40, 80])

        for y in range(1, 6):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx : idx + 3] = bytes([15, 45, 135])

        for x in range(16):
            for y, c in [(6, (46, 139, 87)), (13, (46, 139, 87)), (14, (34, 139, 34))]:
                idx = (y * 16 + x) * 3
                fb[idx : idx + 3] = bytes(c)

        for y in range(7, 13):
            for x in range(16):
                idx = (y * 16 + x) * 3
                fb[idx : idx + 3] = bytes([25, 25, 28])

        for y, lane in self.lanes.items():
            for item in lane.items:
                x1 = int(round(item.x))
                x2 = int(round(item.x + item.width))
                for x in range(x1, x2):
                    if 0 <= x < 16:
                        idx = (y * 16 + x) * 3
                        fb[idx : idx + 3] = bytes([lane.r, lane.g, lane.b])

        fx = int(round(self.frog_x))
        fy = self.frog_y
        if 0 <= fx < 16 and 0 <= fy < 16:
            idx = (fy * 16 + fx) * 3
            fb[idx : idx + 3] = bytes([50, 255, 50])

        for i in range(min(3, self.lives)):
            idx = (15 * 16 + i * 2) * 3
            fb[idx : idx + 3] = bytes([46, 204, 113])

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
            "progress": min(100, (self.homes_occupied * 100 // 5)),
        }
