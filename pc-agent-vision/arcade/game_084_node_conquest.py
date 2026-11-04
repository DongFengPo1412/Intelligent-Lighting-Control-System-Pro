# -*- coding: utf-8 -*-
"""game_084_node_conquest.py —— 目标 #084 节点征服 (Node Conquest)
机制: 7节点实时兵力增殖 + 50%舰队分派与全军突击 + 节点攻占翻转对决
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

NODE_NEUTRAL = 0
NODE_PLAYER = 1
NODE_AI = 2

NODE_COORDS = [
    (1, 2),
    (7, 1),
    (2, 8),
    (7, 7),
    (12, 6),
    (6, 13),
    (13, 12),
]


class ConquestNode:
    def __init__(self, x: int, y: int, owner: int, troops: float):
        self.x = x
        self.y = y
        self.owner = owner
        self.troops = troops


class ConquestFleet:
    def __init__(
        self,
        owner: int,
        target_node: int,
        troops: float,
        x: float,
        y: float,
        vx: float,
        vy: float,
    ):
        self.active = True
        self.owner = owner
        self.target_node = target_node
        self.troops = troops
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


class Game084NodeConquest(BaseCartridge):
    NUM_NODES = 7
    MAX_FLEETS = 24

    def __init__(self):
        super().__init__()
        self._score = 0
        self._high_score = 0
        self._state = STATE_TITLE
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.cursor_node = 0
        self.selected_node = -1
        self.ai_timer = 2.8
        self.nodes: List[ConquestNode] = []
        self.fleets: List[ConquestFleet] = []
        self.reset()

    @property
    def game_id(self) -> int:
        return 84

    @property
    def name(self) -> str:
        return "节点征服"

    @property
    def english_name(self) -> str:
        return "Node Conquest"

    @property
    def release_year(self) -> int:
        return 2008

    @property
    def control_type(self) -> int:
        return CTRL_ARCADE_AB

    @property
    def core_mechanic(self) -> str:
        return "多节点实时增兵与舰队分派占领博弈"

    def _add_score(self, pts: int) -> None:
        self._score += pts
        if self._score > self._high_score:
            self._high_score = self._score

    def _setup_match(self, new_state: int) -> None:
        self._state = new_state
        self._score = 0
        self.state_timer = 0.0
        self.anim_timer = 0.0
        self.cursor_node = 0
        self.selected_node = -1
        self.ai_timer = 2.8
        init_troops = (20.0, 6.0, 6.0, 10.0, 6.0, 6.0, 16.0)
        init_owners = (
            NODE_PLAYER,
            NODE_NEUTRAL,
            NODE_NEUTRAL,
            NODE_NEUTRAL,
            NODE_NEUTRAL,
            NODE_NEUTRAL,
            NODE_AI,
        )
        self.nodes = [
            ConquestNode(NODE_COORDS[i][0], NODE_COORDS[i][1], init_owners[i], init_troops[i])
            for i in range(self.NUM_NODES)
        ]
        self.fleets = []

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

    def _move_cursor_dir(self, dx: int, dy: int) -> None:
        cx = self.nodes[self.cursor_node].x + 0.5
        cy = self.nodes[self.cursor_node].y + 0.5
        best_idx = -1
        best_metric = 1e9

        for i in range(self.NUM_NODES):
            if i == self.cursor_node:
                continue
            vx = (self.nodes[i].x + 0.5) - cx
            vy = (self.nodes[i].y + 0.5) - cy
            proj = vx * dx + vy * dy
            if proj > 0.5:
                perp = abs(vx * dy - vy * dx)
                metric = proj + perp * 1.6
                if metric < best_metric:
                    best_metric = metric
                    best_idx = i

        if best_idx >= 0:
            self.cursor_node = best_idx
        else:
            if dx > 0 or dy > 0:
                self.cursor_node = (self.cursor_node + 1) % self.NUM_NODES
            else:
                self.cursor_node = (self.cursor_node + self.NUM_NODES - 1) % self.NUM_NODES

    def dispatch_fleet(self, src_idx: int, dst_idx: int) -> None:
        if not (0 <= src_idx < self.NUM_NODES and 0 <= dst_idx < self.NUM_NODES):
            return
        if src_idx == dst_idx or len(self.fleets) >= self.MAX_FLEETS:
            return
        send = int(self.nodes[src_idx].troops * 0.5)
        if send < 1:
            return

        self.nodes[src_idx].troops -= float(send)
        sx = self.nodes[src_idx].x + 0.5
        sy = self.nodes[src_idx].y + 0.5
        tx = self.nodes[dst_idx].x + 0.5
        ty = self.nodes[dst_idx].y + 0.5
        dx = tx - sx
        dy = ty - sy
        dist = max(0.01, math.hypot(dx, dy))
        speed = 6.5
        self.fleets.append(
            ConquestFleet(
                self.nodes[src_idx].owner,
                dst_idx,
                float(send),
                sx,
                sy,
                (dx / dist) * speed,
                (dy / dist) * speed,
            )
        )

    def _update_ai(self, dt: float) -> None:
        self.ai_timer -= dt
        if self.ai_timer > 0.0:
            return
        self.ai_timer = 2.8

        best_src = -1
        max_troops = 13.0
        for i, nd in enumerate(self.nodes):
            if nd.owner == NODE_AI and nd.troops > max_troops:
                max_troops = nd.troops
                best_src = i
        if best_src < 0:
            return

        best_dst = -1
        best_cost = 1e9
        for j, nd in enumerate(self.nodes):
            if nd.owner == NODE_AI:
                continue
            dist = math.hypot(nd.x - self.nodes[best_src].x, nd.y - self.nodes[best_src].y)
            cost = nd.troops * 1.2 + dist * 0.8
            if cost < best_cost:
                best_cost = cost
                best_dst = j
        if best_dst >= 0:
            self.dispatch_fleet(best_src, best_dst)

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

        if self.selected_node >= 0 and self.nodes[self.selected_node].owner != NODE_PLAYER:
            self.selected_node = -1

        if keys_pressed & KEY_LEFT:
            self._move_cursor_dir(-1, 0)
        elif keys_pressed & KEY_RIGHT:
            self._move_cursor_dir(1, 0)
        elif keys_pressed & KEY_UP:
            self._move_cursor_dir(0, -1)
        elif keys_pressed & KEY_DOWN:
            self._move_cursor_dir(0, 1)

        if keys_pressed & KEY_A:
            if self.selected_node < 0:
                if self.nodes[self.cursor_node].owner == NODE_PLAYER:
                    self.selected_node = self.cursor_node
            else:
                if self.cursor_node == self.selected_node:
                    self.selected_node = -1
                else:
                    if self.nodes[self.selected_node].owner == NODE_PLAYER:
                        self.dispatch_fleet(self.selected_node, self.cursor_node)
                    self.selected_node = -1

        if keys_pressed & KEY_B:
            if self.selected_node >= 0 and self.cursor_node == self.selected_node:
                self.selected_node = -1
            else:
                for i in range(self.NUM_NODES):
                    if self.nodes[i].owner == NODE_PLAYER and i != self.cursor_node:
                        self.dispatch_fleet(i, self.cursor_node)
                self.selected_node = -1

        for nd in self.nodes:
            if nd.owner in (NODE_PLAYER, NODE_AI):
                nd.troops = min(50.0, nd.troops + 1.5 * dt)

        self._update_ai(dt)

        for fl in self.fleets:
            if not fl.active:
                continue
            fl.x += fl.vx * dt
            fl.y += fl.vy * dt
            dst = self.nodes[fl.target_node]
            tx = dst.x + 0.5
            ty = dst.y + 0.5
            if (tx - fl.x) ** 2 + (ty - fl.y) ** 2 <= 0.45 * 0.45:
                fl.active = False
                if dst.owner == fl.owner:
                    dst.troops = min(50.0, dst.troops + fl.troops)
                else:
                    dst.troops -= fl.troops
                    if dst.troops < 0.0:
                        dst.owner = fl.owner
                        dst.troops = min(50.0, -dst.troops)
                        if fl.owner == NODE_PLAYER:
                            self._add_score(50)

        self.fleets = [f for f in self.fleets if f.active]

        player_nodes = sum(1 for nd in self.nodes if nd.owner == NODE_PLAYER)
        ai_nodes = sum(1 for nd in self.nodes if nd.owner == NODE_AI)

        if ai_nodes == 0:
            self._add_score(500)
            self._state = STATE_VICTORY
            self.state_timer = 0.0
            return
        if player_nodes == 0:
            self._state = STATE_GAMEOVER
            self.state_timer = 0.0
            return

    def render(self) -> bytearray:
        if self._state in (STATE_GAMEOVER, STATE_VICTORY) and self.state_timer > 0.8:
            return ArcadeResultScreen.render(
                self._state == STATE_VICTORY, self._score, self._high_score, self.anim_timer
            )

        fb = bytearray(768)

        for y in range(16):
            for x in range(16):
                bg_b = 16 + ((x * 5 + y * 3) % 10)
                set_pixel(fb, x, y, 6, 10, bg_b)

        if 0 <= self.selected_node < self.NUM_NODES:
            sx = self.nodes[self.selected_node].x
            sy = self.nodes[self.selected_node].y
            for dy in range(-1, 3):
                for dx in range(-1, 3):
                    if dx in (-1, 2) or dy in (-1, 2):
                        set_pixel(fb, sx + dx, sy + dy, 40, 235, 90)

        if self._state in (STATE_PLAYING, STATE_TITLE):
            cx = self.nodes[self.cursor_node].x
            cy = self.nodes[self.cursor_node].y
            if (int(self.anim_timer * 6.0) % 2) == 0:
                set_pixel(fb, cx - 1, cy - 1, 255, 230, 80)
                set_pixel(fb, cx + 2, cy - 1, 255, 230, 80)
                set_pixel(fb, cx - 1, cy + 2, 255, 230, 80)
                set_pixel(fb, cx + 2, cy + 2, 255, 230, 80)

        for nd in self.nodes:
            ratio = max(0.0, min(1.0, nd.troops / 50.0))
            pulse = 0.85 + 0.15 * math.sin(self.anim_timer * (2.5 + ratio * 5.0))
            scale = (0.45 + 0.55 * ratio) * pulse
            nr, ng, nb = 140, 145, 155
            if nd.owner == NODE_PLAYER:
                nr, ng, nb = 20, 225, 255
            elif nd.owner == NODE_AI:
                nr, ng, nb = 255, 55, 55
            fr = min(255, int(nr * scale))
            fg = min(255, int(ng * scale))
            fb_c = min(255, int(nb * scale))
            for dy in range(2):
                for dx in range(2):
                    set_pixel(fb, nd.x + dx, nd.y + dy, fr, fg, fb_c)

        for fl in self.fleets:
            if not fl.active:
                continue
            fx, fy = int(round(fl.x)), int(round(fl.y))
            if fl.owner == NODE_PLAYER:
                set_pixel(fb, fx, fy, 120, 250, 255)
            else:
                set_pixel(fb, fx, fy, 255, 130, 90)

        p_cnt = sum(1 for nd in self.nodes if nd.owner == NODE_PLAYER)
        a_cnt = sum(1 for nd in self.nodes if nd.owner == NODE_AI)
        for k in range(min(7, p_cnt)):
            set_pixel(fb, k, 0, 0, 220, 255)
        for k in range(min(7, a_cnt)):
            set_pixel(fb, 15 - k, 0, 245, 50, 50)

        if self._state == STATE_PAUSED:
            for y in range(5, 9):
                set_pixel(fb, 6, y, 250, 250, 250)
                set_pixel(fb, 9, y, 250, 250, 250)

        return fb

    def get_status(self) -> Dict[str, Any]:
        p_cnt = sum(1 for nd in self.nodes if nd.owner == NODE_PLAYER)
        return {
            "game_id": self.game_id,
            "score": self._score,
            "high_score": self._high_score,
            "lives": p_cnt,
            "state": self._state,
            "progress": (p_cnt * 100) // self.NUM_NODES,
        }
