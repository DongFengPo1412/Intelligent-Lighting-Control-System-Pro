"""
Game #032: 疯狂过马路 (Crossy Road 2014 / Hipster Whale)
Endless Procedural Multi-Lane Hopping with Highway Cars, River Logs, Express Trains & Penalty Eagle Swoop.
"""

import random
from typing import List, Dict, Any
from .base_cartridge import (
    BaseCartridge,
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
)

STATE_START = 0
STATE_PLAYING = 1
STATE_DEAD = 2

NUM_LANES = 24
MAX_OBSTACLES = 32

LANE_GRASS = 0
LANE_ROAD = 1
LANE_RIVER = 2
LANE_RAIL = 3


class Game032CrossyRoad(BaseCartridge):
    def __init__(self):
        super().__init__()
        self.state = STATE_START
        self.state_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.max_distance = 0

        self.player_x = 7.0
        self.player_world_y = 0
        self.camera_world_y = 0
        self.idle_timer = 0.0
        self.eagle_striking = False
        self.eagle_y = 0.0

        self.lanes: List[Dict[str, Any]] = []
        self.obstacles: List[Dict[str, Any]] = []

        self.init_world()

    @property
    def game_id(self) -> int:
        return 32

    @property
    def name(self) -> str:
        return "疯狂过马路"

    @property
    def english_name(self) -> str:
        return "Crossy Road 2014"

    @property
    def release_year(self) -> int:
        return 2014

    @property
    def control_type(self) -> int:
        return CTRL_DPAD_4WAY

    @property
    def core_mechanic(self) -> str:
        return "无限单向纵向跳跃 + 动态多地形推进 + 停留超时老鹰天降扑杀 + 极速列车避让"

    def init(self) -> None:
        self.reset()

    def generate_lane(self, lane_idx: int, world_y: int):
        lane = {
            "type": LANE_GRASS,
            "world_y": world_y,
            "speed": 0.0,
            "spawn_timer": 0.0,
            "spawn_interval": 999.0,
            "train_timer": 0.0,
            "train_warning": False,
            "train_passing": False,
            "train_x": -10.0,
        }

        if world_y <= 2:
            lane["type"] = LANE_GRASS
            lane["speed"] = 0.0
            lane["spawn_interval"] = 999.0
        else:
            pattern = world_y % 10
            if pattern in (3, 7):
                lane["type"] = LANE_RAIL
                lane["speed"] = 22.0
                lane["train_timer"] = 2.0 + random.uniform(0.0, 3.0)
            elif pattern in (4, 5, 8):
                lane["type"] = LANE_RIVER
                to_right = (world_y % 2 == 0)
                lane["speed"] = (1.0 if to_right else -1.0) * (2.2 + random.uniform(0.0, 1.5))
                lane["spawn_interval"] = 2.2
            elif pattern in (0, 9):
                lane["type"] = LANE_GRASS
                lane["speed"] = 0.0
                lane["spawn_interval"] = 999.0
            else:
                lane["type"] = LANE_ROAD
                to_right = (world_y % 2 == 0)
                lane["speed"] = (1.0 if to_right else -1.0) * (3.5 + random.uniform(0.0, 2.5))
                lane["spawn_interval"] = 1.8

        if lane_idx < len(self.lanes):
            self.lanes[lane_idx] = lane
        else:
            self.lanes.append(lane)

    def init_world(self):
        self.lanes = []
        self.obstacles = []
        for i in range(NUM_LANES):
            self.generate_lane(i, i)

    def trigger_eagle_strike(self):
        self.eagle_striking = True
        self.eagle_y = 0.0

    def reset(self):
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.score = 0
        self.max_distance = 0
        self.player_x = 7.0
        self.player_world_y = 0
        self.camera_world_y = 0
        self.idle_timer = 0.0
        self.eagle_striking = False
        self.eagle_y = 0.0
        self.init_world()

    def update(self, dt: float, buttons: int, prev_buttons: int = 0):
        self.state_timer += dt

        if self.state == STATE_START:
            if buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT):
                self.reset()
            return

        if self.state == STATE_DEAD:
            if self.state_timer >= 1.5 and (buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)):
                self.reset()
            return

        # Player Hopping Input
        if (buttons & KEY_UP) and not (prev_buttons & KEY_UP):
            self.player_world_y += 1
            self.idle_timer = 0.0 # Reset eagle
            if self.player_world_y > self.max_distance:
                self.max_distance = self.player_world_y
                self.score = self.max_distance * 10
                if self.score > self.high_score:
                    self.high_score = self.score
        elif (buttons & KEY_DOWN) and not (prev_buttons & KEY_DOWN):
            if self.player_world_y > self.camera_world_y:
                self.player_world_y -= 1
        elif (buttons & KEY_LEFT) and not (prev_buttons & KEY_LEFT):
            self.player_x = max(0.0, self.player_x - 1.0)
        elif (buttons & KEY_RIGHT) and not (prev_buttons & KEY_RIGHT):
            self.player_x = min(15.0, self.player_x + 1.0)

        # Camera follow
        target_cam_y = self.player_world_y - 8
        if target_cam_y > self.camera_world_y:
            self.camera_world_y = target_cam_y

        # Recycle lanes ahead
        for i in range(len(self.lanes)):
            if self.lanes[i]["world_y"] < self.camera_world_y:
                highest_y = self.camera_world_y
                for l in self.lanes:
                    if l["world_y"] > highest_y:
                        highest_y = l["world_y"]
                self.generate_lane(i, highest_y + 1)

        self.update_lanes_and_obstacles(dt)
        self.check_eagle(dt)
        self.check_collisions()

    def update_lanes_and_obstacles(self, dt: float):
        for i, l in enumerate(self.lanes):
            if l["type"] in (LANE_ROAD, LANE_RIVER):
                l["spawn_timer"] += dt
                if l["spawn_timer"] >= l["spawn_interval"]:
                    l["spawn_timer"] = 0.0
                    self.obstacles.append({
                        "active": True,
                        "lane_idx": i,
                        "is_log": (l["type"] == LANE_RIVER),
                        "length": 3.5 if l["type"] == LANE_RIVER else 2.2,
                        "x": -3.0 if l["speed"] > 0.0 else 18.0,
                    })
            elif l["type"] == LANE_RAIL:
                if not l["train_warning"] and not l["train_passing"]:
                    l["train_timer"] -= dt
                    if l["train_timer"] <= 0.0:
                        l["train_warning"] = True
                        l["train_timer"] = 0.8
                elif l["train_warning"]:
                    l["train_timer"] -= dt
                    if l["train_timer"] <= 0.0:
                        l["train_warning"] = False
                        l["train_passing"] = True
                        l["train_x"] = -8.0
                elif l["train_passing"]:
                    l["train_x"] += l["speed"] * dt
                    if l["train_x"] > 24.0:
                        l["train_passing"] = False
                        l["train_timer"] = 3.5 + random.uniform(0.0, 3.0)

        # Move obstacles
        for ob in self.obstacles:
            if not ob["active"]:
                continue
            l = self.lanes[ob["lane_idx"]]
            ob["x"] += l["speed"] * dt
            if (l["speed"] > 0.0 and ob["x"] > 20.0) or (l["speed"] < 0.0 and ob["x"] < -5.0):
                ob["active"] = False

        self.obstacles = [o for o in self.obstacles if o["active"]]

    def check_eagle(self, dt: float):
        self.idle_timer += dt

        if not self.eagle_striking and self.idle_timer >= 3.5:
            self.trigger_eagle_strike()

        if self.eagle_striking:
            self.eagle_y += 28.0 * dt
            player_screen_y = 15 - (self.player_world_y - self.camera_world_y)
            if self.eagle_y >= float(player_screen_y):
                self.state = STATE_DEAD
                self.state_timer = 0.0
                self.eagle_striking = False

    def check_collisions(self):
        if self.state != STATE_PLAYING:
            return

        cur_lane = None
        cur_lane_idx = -1
        for i, l in enumerate(self.lanes):
            if l["world_y"] == self.player_world_y:
                cur_lane = l
                cur_lane_idx = i
                break

        if not cur_lane:
            return

        # 1. Road Car Collision
        if cur_lane["type"] == LANE_ROAD:
            for ob in self.obstacles:
                if ob["active"] and ob["lane_idx"] == cur_lane_idx:
                    ox = ob["x"]
                    o_len = ob["length"]
                    if (ox - 0.4) <= self.player_x <= (ox + o_len + 0.4):
                        self.state = STATE_DEAD
                        self.state_timer = 0.0
                        return

        # 2. River & Logs
        if cur_lane["type"] == LANE_RIVER:
            on_log = False
            for ob in self.obstacles:
                if ob["active"] and ob["lane_idx"] == cur_lane_idx:
                    ox = ob["x"]
                    o_len = ob["length"]
                    if (ox - 0.3) <= self.player_x <= (ox + o_len + 0.3):
                        on_log = True
                        self.player_x += cur_lane["speed"] * (1.0 / 30.0)
                        break

            if not on_log or self.player_x < 0.0 or self.player_x > 15.0:
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

        # 3. Train
        if cur_lane["type"] == LANE_RAIL and cur_lane["train_passing"]:
            if (cur_lane["train_x"] - 0.5) <= self.player_x <= (cur_lane["train_x"] + 8.0):
                self.state = STATE_DEAD
                self.state_timer = 0.0
                return

    def render(self) -> bytes:
        fb = bytearray(16 * 16 * 3)

        for screen_y in range(16):
            world_y = self.camera_world_y + (15 - screen_y)
            l = None
            l_idx = -1
            for i, lane in enumerate(self.lanes):
                if lane["world_y"] == world_y:
                    l = lane
                    l_idx = i
                    break

            bg_r, bg_g, bg_b = 39, 174, 96
            if l:
                if l["type"] == LANE_ROAD:
                    bg_r, bg_g, bg_b = 44, 62, 80
                elif l["type"] == LANE_RIVER:
                    bg_r, bg_g, bg_b = 41, 128, 185
                elif l["type"] == LANE_RAIL:
                    bg_r, bg_g, bg_b = 90, 95, 100

            for x in range(16):
                idx = (screen_y * 16 + x) * 3
                fb[idx:idx + 3] = bytes([bg_r, bg_g, bg_b])

            if not l:
                continue

            # Rail
            if l["type"] == LANE_RAIL:
                if l["train_warning"]:
                    blink = (int(self.state_timer * 10.0) % 2 == 0)
                    if blink:
                        idx_l = (screen_y * 16 + 0) * 3
                        idx_r = (screen_y * 16 + 15) * 3
                        fb[idx_l:idx_l + 3] = bytes([255, 0, 0])
                        fb[idx_r:idx_r + 3] = bytes([255, 0, 0])
                elif l["train_passing"]:
                    tx_start = int(l["train_x"])
                    for tx in range(tx_start, tx_start + 7):
                        if 0 <= tx < 16:
                            idx = (screen_y * 16 + tx) * 3
                            fb[idx:idx + 3] = bytes([231, 76, 60])

            # Obstacles
            for ob in self.obstacles:
                if ob["active"] and ob["lane_idx"] == l_idx:
                    ox_start = int(ob["x"])
                    ox_end = ox_start + int(ob["length"])
                    for x in range(ox_start, ox_end):
                        if 0 <= x < 16:
                            idx = (screen_y * 16 + x) * 3
                            if ob["is_log"]:
                                fb[idx:idx + 3] = bytes([160, 82, 45])
                            else:
                                fb[idx:idx + 3] = bytes([241, 196, 15])

        # Player
        player_screen_y = 15 - (self.player_world_y - self.camera_world_y)
        px = int(round(self.player_x))

        if 0 <= player_screen_y < 16 and 0 <= px < 16:
            idx = (player_screen_y * 16 + px) * 3
            if self.state == STATE_DEAD:
                fb[idx:idx + 3] = bytes([231, 76, 60])
            else:
                fb[idx:idx + 3] = bytes([250, 250, 250])
                if player_screen_y > 0:
                    comb_idx = ((player_screen_y - 1) * 16 + px) * 3
                    fb[comb_idx:comb_idx + 3] = bytes([231, 76, 60])

        # Eagle
        if self.eagle_striking:
            ey = int(self.eagle_y)
            if 0 <= ey < 16 and 0 <= px < 16:
                e_idx = (ey * 16 + px) * 3
                fb[e_idx:e_idx + 3] = bytes([80, 40, 20])

        return bytes(fb)

    def get_status(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "state": self.state,
            "score": self.score,
            "high_score": self.high_score,
            "max_distance": self.max_distance,
            "player_x": self.player_x,
            "player_world_y": self.player_world_y,
            "camera_world_y": self.camera_world_y,
            "idle_timer": self.idle_timer,
        }
