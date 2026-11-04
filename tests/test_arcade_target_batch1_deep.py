# -*- coding: utf-8 -*-
"""test_arcade_target_batch1_deep.py —— 第一批 10 款目标游戏「完整对局」深度验证

原则: 尽量通过真实按键输入 (update(dt, keys_down, keys_pressed)) 驱动自动驾驶机器人
完整打完一局, 而不是直接篡改内部状态来"伪造"胜利。仅在需要构造特定碰撞场景时
(例如把敌人固定在某格) 才做最小化的场景布置, 并在注释中写明。

  #009 Flappy Bird   : 机器人穿越 >=15 根水管(进入窄缝阶段); 不操作则坠地 GAMEOVER
  #010 Stack         : 30 次完美落块连击; 偏移落块宽度被切; 完全错位 GAMEOVER
  #020 Pong          : 机器人 P1 以 5 分击败 AI 获得 VICTORY; 不操作 P1 被 AI 5:0 判负
  #021 Breakout      : 机器人清空全部 32 块砖 VICTORY; 红砖需两次独立撞击
  #026 Space Invaders: 机器人瞄准+躲避, 歼灭全部 12 名外星人 VICTORY
  #034 Pac-Man       : 迷宫全连通; 机器人吃光全部豆子 VICTORY; 能量豆反杀幽灵; 撞普通幽灵扣命
  #038 Bomberman     : 放炸弹-撤离-十字爆破炸砖; 炸死敌人 VICTORY; 原地自爆扣命; 残留火焰致死
  #054 Sokoban       : 纯按键推箱完整解出关卡 VICTORY; 推墙/推双箱被阻挡
  #074 Highway Racer : 机器人变道闪避跑满 1000m VICTORY; 连续撞护栏 3 次 GAMEOVER
  #097 Frogger       : 规划器跳过公路+河流填满 5 个洞 VICTORY; 上下来回跳不能刷分
"""

import random
import unittest
from collections import deque

from arcade.game_009_flappy_bird import Game009FlappyBird
from arcade.game_010_stack import Game010Stack
from arcade.game_020_pong import Game020Pong
from arcade.game_021_breakout import Game021Breakout
from arcade.game_026_space_invaders import Game026SpaceInvaders
from arcade.game_034_pacman import Game034Pacman, WALL_MAP, Ghost
from arcade.game_038_bomberman import Game038Bomberman, Enemy, TILE_EMPTY, TILE_SOFT_BRICK
from arcade.game_054_sokoban import Game054Sokoban, SOKOBAN_WALL
from arcade.game_074_highway_racer import Game074HighwayRacer, LANE_CENTERS
from arcade.game_097_frogger import Game097Frogger, HOME_X

from arcade.base_cartridge import (
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    KEY_A,
    KEY_B,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
)

DT = 0.016


def frame(g, down=0, pressed=0, dt=DT):
    g.update(dt, down, pressed)


class TestArcadeBatch1Deep(unittest.TestCase):

    def setUp(self):
        random.seed(20261104)

    # ------------------------------------------------------------------ #009
    def test_01_flappy_bird_full_run(self):
        g = Game009FlappyBird()
        g.start()
        bird_h = 1.8
        for _ in range(int(120 / DT)):
            if g.state != STATE_PLAYING or g.score >= 15:
                break
            ahead = [p for p in g.pipes if p.x + 2.0 >= g.bird_x]
            p = min(ahead, key=lambda q: q.x)
            gap_bottom = p.gap_y + p.gap_height
            vy_next = min(14.0, g.bird_vy + 32.0 * DT)
            y_next = g.bird_y + vy_next * DT
            flap = KEY_A if y_next > gap_bottom - bird_h - 0.05 else 0
            frame(g, flap, flap)
        self.assertEqual(g.state, STATE_PLAYING, "Bot crashed before 15 pipes")
        self.assertGreaterEqual(g.score, 15, "Bot should pass >=15 pipes incl. narrow gap phase")
        self.assertTrue(all(p.gap_height in (4, 5) for p in g.pipes))

        # 不操作 -> 必然坠地
        g2 = Game009FlappyBird()
        g2.start()
        for _ in range(int(3 / DT)):
            frame(g2)
        self.assertEqual(g2.state, STATE_GAMEOVER, "Falling without flapping must end the game")

    # ------------------------------------------------------------------ #010
    def test_02_stack_perfect_combo_slice_and_miss(self):
        g = Game010Stack()
        g.start()

        def next_x():
            nx = g.active_x + g.active_vx * DT
            return max(0.0, min(16.0 - g.active_w, nx))

        placed = 0
        for _ in range(int(120 / DT)):
            if placed >= 30:
                break
            base = g.layers[-1]
            if abs(next_x() - base.x) < 0.3:
                frame(g, KEY_A, KEY_A)
                placed += 1
            else:
                frame(g)
        self.assertEqual(g.state, STATE_PLAYING)
        self.assertEqual(g.score, 30)
        self.assertGreaterEqual(g.perfect_combo, 30)
        self.assertAlmostEqual(g.layers[-1].w, 9.0, places=3, msg="Perfect drops must keep full width")

        # 偏移落块 -> 宽度被切, 连击清零
        base = g.layers[-1]
        for _ in range(int(10 / DT)):
            if 1.5 < abs(next_x() - base.x) < 2.5:
                break
            frame(g)
        w_before = g.active_w
        frame(g, KEY_A, KEY_A)
        self.assertEqual(g.perfect_combo, 0)
        self.assertLess(g.layers[-1].w, w_before, "Offset drop must slice the block")
        self.assertEqual(g.state, STATE_PLAYING)

        # 持续马虎落块(每次都偏差约 2 格) -> 方块越切越窄, 最终 GAMEOVER
        widths = [g.layers[-1].w]
        for _ in range(int(120 / DT)):
            if g.state != STATE_PLAYING:
                break
            base = g.layers[-1]
            if abs(next_x() - base.x) > 1.6:
                frame(g, KEY_A, KEY_A)
                if g.state == STATE_PLAYING:
                    widths.append(g.layers[-1].w)
            else:
                frame(g)
        self.assertEqual(g.state, STATE_GAMEOVER, "Sloppy stacking must eventually end the game")
        self.assertEqual(widths, sorted(widths, reverse=True), "Block width can only shrink when slicing")

    # ------------------------------------------------------------------ #020
    def test_03_pong_bot_beats_ai_and_idle_loses(self):
        g = Game020Pong()
        g.start()
        edge_sign = 1
        last_vx = g.ball_vx
        for _ in range(int(240 / DT)):
            if g.state != STATE_PLAYING:
                break
            if last_vx < 0 < g.ball_vx:
                edge_sign = -edge_sign  # 交替用挡板上/下沿击球, 制造大角度
            last_vx = g.ball_vx
            if g.ball_vx < 0:
                # 让球打在挡板边缘 (hit_offset≈±1.2) 获得最大纵向速度
                target = g.ball_y + 0.3 if edge_sign > 0 else g.ball_y - g.paddle_h + 0.7
            else:
                target = 6.0
            key = 0
            if g.p1_y < target - 0.1:
                key = KEY_DOWN
            elif g.p1_y > target + 0.1:
                key = KEY_UP
            frame(g, key, 0)
        self.assertEqual(g.state, STATE_VICTORY, f"Bot should beat AI, score {g.p1_score}:{g.p2_score}")
        self.assertEqual(g.p1_score, 5)
        self.assertEqual(g.score, 50)

        g2 = Game020Pong()
        g2.start()
        for _ in range(int(240 / DT)):
            if g2.state != STATE_PLAYING:
                break
            frame(g2)
        self.assertEqual(g2.state, STATE_GAMEOVER)
        self.assertEqual(g2.p2_score, 5)

        # 双人模式: 按 A/B 接管 P2, AI 关闭
        g3 = Game020Pong()
        g3.start()
        frame(g3, KEY_A, KEY_A)
        self.assertTrue(g3.p2_is_ai)
        self.assertTrue(g3.set_player_count(2))
        self.assertFalse(g3.p2_is_ai)

    # ------------------------------------------------------------------ #021
    def test_04_breakout_bot_clears_board(self):
        g = Game021Breakout()
        g.start()
        frame(g, KEY_A, KEY_A)
        self.assertFalse(g.ball_stuck)
        start_lives = g.lives
        for _ in range(int(400 / DT)):
            if g.state != STATE_PLAYING:
                break
            if g.ball_stuck:
                frame(g, KEY_A, KEY_A)
                continue
            cols = [c for r in range(4) for c in range(8) if g.bricks[r][c].hp > 0]
            mean_x = (sum(cols) / len(cols)) * 2 + 0.5 if cols else 8.0
            # 让球偏离挡板中心 1 格, 从而获得朝剩余砖块方向的水平速度
            offset = -1.0 if mean_x > g.ball_x else 1.0
            target_center = g.ball_x + offset
            center = g.paddle_x + g.paddle_w * 0.5
            key = 0
            if center < target_center - 0.15:
                key = KEY_RIGHT
            elif center > target_center + 0.15:
                key = KEY_LEFT
            frame(g, key, 0)
        self.assertEqual(g.state, STATE_VICTORY, f"Bot left {g.remaining_bricks} bricks")
        self.assertEqual(g.remaining_bricks, 0)
        self.assertGreaterEqual(g.lives, 1)
        self.assertLessEqual(g.lives, start_lives)
        self.assertEqual(g.score, 320)

    def test_05_breakout_red_brick_needs_two_separate_hits(self):
        g = Game021Breakout()
        g.start()
        frame(g, KEY_A, KEY_A)
        # 场景布置: 球从下方垂直飞向第 0 行(红砖, hp=2)的第 3 列
        g.bricks[1][3].hp = 0
        g.bricks[2][3].hp = 0
        g.bricks[3][3].hp = 0
        g.ball_x, g.ball_y, g.ball_vx, g.ball_vy = 6.5, 4.0, 0.0, -8.5
        for _ in range(int(0.5 / DT)):
            frame(g)
            if g.ball_vy > 0:
                break
        for _ in range(10):
            frame(g)
        self.assertEqual(g.bricks[0][3].hp, 1, "One contact must remove exactly 1 HP from a red brick")
        self.assertGreater(g.ball_vy, 0, "Ball must bounce back down after hitting the brick")

    # ------------------------------------------------------------------ #026
    def test_06_space_invaders_bot_clears_fleet(self):
        g = Game026SpaceInvaders()
        g.start()
        for _ in range(int(240 / DT)):
            if g.state != STATE_PLAYING:
                break
            key, fire = 0, 0
            threats = [b for b in g.bullets if b.vy > 0 and b.y > 7.5 and abs(b.x - g.player_x) < 2.0]
            if threats:
                t = min(threats, key=lambda b: abs(b.x - g.player_x))
                go_right = t.x <= g.player_x
                if go_right and g.player_x >= 13.5:
                    go_right = False
                elif not go_right and g.player_x <= 1.5:
                    go_right = True
                key = KEY_RIGHT if go_right else KEY_LEFT
            else:
                targets = []
                for c in range(4):
                    for r in range(2, -1, -1):
                        if g.fleet[r][c].alive:
                            targets.append(g.fleet_x + c * 3 + 0.5)
                            break
                tx = min(targets, key=lambda x: abs(x - g.player_x))
                if abs(tx - g.player_x) < 0.4:
                    fire = KEY_A
                elif tx > g.player_x:
                    key = KEY_RIGHT
                else:
                    key = KEY_LEFT
            frame(g, key | fire, fire)
        self.assertEqual(g.state, STATE_VICTORY, f"{g.remaining_aliens} aliens left, lives {g.lives}")
        self.assertEqual(g.remaining_aliens, 0)
        self.assertEqual(g.score, 4 * (30 + 20 + 10))

    # ------------------------------------------------------------------ #034
    @staticmethod
    def _pac_bfs(g, start, goal_fn):
        sx, sy = start
        prev = {start: None}
        q = deque([start])
        while q:
            cx, cy = q.popleft()
            if (cx, cy) != start and goal_fn(cx, cy):
                node = (cx, cy)
                while prev[node] != start:
                    node = prev[node]
                return node[0] - sx, node[1] - sy
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < 16 and 0 <= ny < 16 and WALL_MAP[ny][nx] == 0 and (nx, ny) not in prev:
                    prev[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))
        return None

    def _pac_drive(self, g, goal_fn, max_t):
        dir_key = {(1, 0): KEY_RIGHT, (-1, 0): KEY_LEFT, (0, 1): KEY_DOWN, (0, -1): KEY_UP}
        key = 0
        for _ in range(int(max_t / DT)):
            if g.state != STATE_PLAYING:
                return
            gx, gy = int(round(g.pac_x)), int(round(g.pac_y))
            if 0 <= gx < 16 and 0 <= gy < 16:
                if goal_fn(gx, gy) and abs(g.pac_x - gx) < 0.1 and abs(g.pac_y - gy) < 0.1:
                    return
                step = self._pac_bfs(g, (gx, gy), goal_fn)
                if step is None:
                    return
                key = dir_key[step]
            frame(g, key, key)

    def test_07_pacman_maze_connected_and_bot_clears(self):
        g = Game034Pacman()
        g.start()
        reach = set()
        q = deque([(8, 10)])
        reach.add((8, 10))
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < 16 and 0 <= ny < 16 and WALL_MAP[ny][nx] == 0 and (nx, ny) not in reach:
                    reach.add((nx, ny))
                    q.append((nx, ny))
        dots = {(x, y) for y in range(16) for x in range(16) if g.grid[y][x] in (1, 2)}
        self.assertTrue(dots <= reach, f"Unreachable dots: {sorted(dots - reach)}")

        # 场景布置: 移除幽灵, 验证仅靠方向键能吃光所有豆子并通关
        g.ghosts = []
        total = g.remaining_dots
        self._pac_drive(g, lambda x, y: g.grid[y][x] in (1, 2), 400)
        self.assertEqual(g.state, STATE_VICTORY, f"{g.remaining_dots}/{total} dots left")
        self.assertEqual(g.remaining_dots, 0)
        self.assertEqual(g.score, (total - 4) * 10 + 4 * 50)

    def test_08_pacman_energizer_and_ghost_contact(self):
        g = Game034Pacman()
        g.start()
        # 场景布置: 一只静止(速度0)的幽灵, 吃豆人主动撞上去 -> 扣命并重置位置
        g.ghosts = [Ghost(5.0, 10.0, 231, 76, 60, 0.0)]
        for _ in range(int(3 / DT)):
            if g.lives < 3:
                break
            frame(g, KEY_LEFT, KEY_LEFT)
        self.assertEqual(g.lives, 2, "Touching a normal ghost costs a life")
        self.assertEqual((g.pac_x, g.pac_y), (8.0, 10.0))

        # 走到能量豆 (1,14) -> 幽灵进入惊吓
        self._pac_drive(g, lambda x, y: (x, y) == (1, 14), 60)
        self.assertGreater(g.frightened_timer, 0.0, "Eating the energizer starts frightened mode")
        self.assertTrue(all(gh.is_frightened for gh in g.ghosts))

        # 惊吓幽灵放在右侧通道 (3,14), 吃豆人向右撞上去 -> +200 并送回巢穴
        g.ghosts = [Ghost(3.0, 14.0, 231, 76, 60, 0.0)]
        g.ghosts[0].is_frightened = True
        score_before = g.score
        for _ in range(int(2 / DT)):
            frame(g, KEY_RIGHT, KEY_RIGHT)
            if g.ghosts[0].x == 7.0:
                break
        self.assertEqual((g.ghosts[0].x, g.ghosts[0].y), (7.0, 7.0), "Eaten ghost returns to the house")
        self.assertGreaterEqual(g.score - score_before, 200)
        self.assertEqual(g.lives, 2)

    # ------------------------------------------------------------------ #038
    def _bomber_walk_down_to(self, g, ty):
        for _ in range(int(3 / DT)):
            if g.player_y >= ty - 0.05 or g.state != STATE_PLAYING:
                break
            frame(g, KEY_DOWN, 0)

    def test_09_bomberman_bomb_escape_and_brick(self):
        g = Game038Bomberman()
        g.start()
        g.enemies = []  # 场景布置: 先不放敌人, 只验证炸弹/撤离/炸砖
        g.remaining_enemies = 0
        self.assertEqual(g.map[1][3], TILE_SOFT_BRICK)
        frame(g, KEY_A, KEY_A)
        self.assertIsNotNone(g.bomb)
        self.assertEqual((g.bomb.gx, g.bomb.gy), (1, 1))
        self._bomber_walk_down_to(g, 4.0)
        self.assertEqual(int(round(g.player_y)), 4)
        for _ in range(int(3 / DT)):
            if g.bomb is None:
                break
            frame(g)
        self.assertIsNone(g.bomb)
        self.assertEqual(g.map[1][3], TILE_EMPTY, "Cross blast destroys the soft brick in range")
        self.assertEqual(g.score, 20)
        self.assertEqual(g.lives, 3, "Player hiding outside blast range survives")
        flame_cells = {(f.x, f.y) for f in g.flames}
        self.assertTrue({(1, 1), (2, 1), (3, 1), (1, 2), (1, 3)} <= flame_cells)

        # 残留火焰仍然致命: 立刻往回走进火焰
        for _ in range(int(0.4 / DT)):
            if g.lives < 3:
                break
            frame(g, KEY_UP, 0)
        self.assertEqual(g.lives, 2, "Walking into a lingering flame must cost a life")

    def test_10_bomberman_kill_enemy_victory_and_self_blast(self):
        g = Game038Bomberman()
        g.start()
        # 场景布置: 唯一敌人固定在 (2,1) (速度0), 处于炸弹爆炸十字内
        g.enemies = [Enemy(2.0, 1.0, 0.0)]
        g.remaining_enemies = 1
        frame(g, KEY_A, KEY_A)
        self._bomber_walk_down_to(g, 4.0)
        for _ in range(int(3 / DT)):
            if g.state != STATE_PLAYING:
                break
            frame(g)
        self.assertEqual(g.state, STATE_VICTORY, "Killing the last enemy wins the stage")
        self.assertFalse(g.enemies[0].alive)
        self.assertGreaterEqual(g.score, 100)

        g2 = Game038Bomberman()
        g2.start()
        g2.enemies = []
        g2.remaining_enemies = 0
        frame(g2, KEY_A, KEY_A)
        for _ in range(int(3 / DT)):
            if g2.lives < 3:
                break
            frame(g2)
        self.assertEqual(g2.lives, 2, "Standing on your own bomb costs a life")
        self.assertEqual((g2.player_x, g2.player_y), (1.0, 1.0))

    # ------------------------------------------------------------------ #054
    def _sok_walk_to(self, g, tx, ty):
        start = (g.player_x, g.player_y)
        boxes = {(b.x, b.y) for b in g.boxes}
        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == (tx, ty):
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cur[0] + dx, cur[1] + dy)
                if n in prev or g.map[n[1]][n[0]] == SOKOBAN_WALL or n in boxes:
                    continue
                prev[n] = cur
                q.append(n)
        self.assertIn((tx, ty), prev, f"Sokoban cell {(tx, ty)} unreachable")
        path = []
        node = (tx, ty)
        while prev[node] is not None:
            path.append(node)
            node = prev[node]
        keymap = {(1, 0): KEY_RIGHT, (-1, 0): KEY_LEFT, (0, 1): KEY_DOWN, (0, -1): KEY_UP}
        for n in reversed(path):
            k = keymap[(n[0] - g.player_x, n[1] - g.player_y)]
            frame(g, k, k)
            self.assertEqual((g.player_x, g.player_y), n)

    def _sok_push(self, g, key, times=1):
        for _ in range(times):
            moves = g.moves
            frame(g, key, key)
            self.assertEqual(g.moves, moves + 1, "Push was blocked unexpectedly")

    def test_11_sokoban_full_solve_by_keys(self):
        g = Game054Sokoban()
        g.start()
        self.assertEqual(sorted((b.x, b.y) for b in g.boxes), [(5, 6), (6, 6), (9, 9), (10, 9)])

        # 阻挡规则: 箱子(5,6)左推 -> 被(6,6)挡? 不, 先验证双箱不可推: 站在(7,6)左推
        self._sok_walk_to(g, 7, 6)
        moves = g.moves
        frame(g, KEY_LEFT, KEY_LEFT)
        self.assertEqual(g.moves, moves, "Two boxes in a row cannot be pushed")
        self.assertEqual((g.player_x, g.player_y), (7, 6))

        self._sok_walk_to(g, 6, 7)
        self._sok_push(g, KEY_UP, 2)        # (6,6)->(6,4)
        self._sok_walk_to(g, 7, 4)
        self._sok_push(g, KEY_LEFT, 2)      # (6,4)->(4,4) 目标
        self._sok_walk_to(g, 5, 7)
        self._sok_push(g, KEY_UP, 2)        # (5,6)->(5,4) 目标
        self.assertEqual(g.boxes_on_goal, 2)
        # 右下目标点为 (10,11) 与 (11,11)
        self._sok_walk_to(g, 10, 8)
        self._sok_push(g, KEY_DOWN, 2)      # (10,9)->(10,11)
        self._sok_walk_to(g, 9, 11)
        self._sok_push(g, KEY_RIGHT, 1)     # (10,11)->(11,11) 目标
        self.assertEqual(g.boxes_on_goal, 3)
        self._sok_walk_to(g, 9, 8)
        self._sok_push(g, KEY_DOWN, 2)      # (9,9)->(9,11)
        self._sok_walk_to(g, 8, 11)
        self._sok_push(g, KEY_RIGHT, 1)     # (9,11)->(10,11) 目标
        self.assertEqual(g.boxes_on_goal, 4)
        self.assertEqual(g.state, STATE_VICTORY)
        self.assertEqual(g.score, max(100, 1000 - g.moves * 5))

        # 推向墙壁被阻挡
        g2 = Game054Sokoban()
        g2.start()
        self._sok_walk_to(g2, 4, 4)
        moves = g2.moves
        frame(g2, KEY_UP, KEY_UP)
        frame(g2, KEY_UP, KEY_UP)
        self.assertEqual((g2.player_x, g2.player_y), (4, 3))
        frame(g2, KEY_UP, KEY_UP)
        self.assertEqual((g2.player_x, g2.player_y), (4, 3), "Player cannot walk into walls")

    # ------------------------------------------------------------------ #074
    def test_12_highway_racer_bot_reaches_1000m(self):
        g = Game074HighwayRacer()
        g.start()
        target_lane = 1

        def lane_tti(lane):
            best = 99.0
            for c in g.traffic:
                if c.lane != lane or c.y > 14.6:
                    continue
                rel = g.speed - c.speed
                gap = 12.0 - (c.y + c.height)
                if gap <= 0.3:
                    return 0.0
                if rel > 0.01:
                    best = min(best, gap / rel)
            return best

        for _ in range(int(120 / DT)):
            if g.state != STATE_PLAYING:
                break
            cur = min(range(3), key=lambda L: abs(LANE_CENTERS[L] - g.car_x))
            if abs(LANE_CENTERS[target_lane] - g.car_x) < 0.2:
                cands = [cur] + [L for L in (cur - 1, cur + 1) if 0 <= L <= 2]
                target_lane = max(cands, key=lambda L: (lane_tti(L), L == cur))
            key = 0
            dx = LANE_CENTERS[target_lane] - g.car_x
            if dx > 0.15:
                key |= KEY_RIGHT
            elif dx < -0.15:
                key |= KEY_LEFT
            if lane_tti(target_lane) < 0.8 or lane_tti(cur) < 0.6:
                key |= KEY_DOWN
            elif lane_tti(target_lane) > 2.0:
                key |= KEY_UP
            frame(g, key, 0)
        self.assertEqual(g.state, STATE_VICTORY, f"Bot stopped at {g.distance_m:.0f}m, lives {g.lives}")
        self.assertGreaterEqual(g.distance_m, 1000.0)
        self.assertGreaterEqual(g.score, 1000)

        g2 = Game074HighwayRacer()
        g2.start()
        crashes = 0
        for _ in range(int(20 / DT)):
            if g2.state != STATE_PLAYING:
                break
            lives = g2.lives
            frame(g2, KEY_LEFT, 0)
            if g2.lives < lives:
                crashes += 1
        self.assertEqual(g2.state, STATE_GAMEOVER, "Hitting the guardrail 3 times ends the game")
        self.assertEqual(crashes, 3)
        self.assertEqual(g2.lives, 0)

    # ------------------------------------------------------------------ #097
    @staticmethod
    def _frog_snap(g):
        return (
            g.frog_x, g.frog_y, g.lives, g._score, g.round_timer, list(g.homes),
            g.homes_occupied, g._state, getattr(g, "best_row", None), g.state_timer, g.anim_timer,
            [[it.x for it in g.lanes[k].items] for k in sorted(g.lanes)],
        )

    @staticmethod
    def _frog_restore(g, s):
        (g.frog_x, g.frog_y, g.lives, g._score, g.round_timer, homes, g.homes_occupied,
         g._state, best, g.state_timer, g.anim_timer, lanes) = s
        g.homes = list(homes)
        if best is not None:
            g.best_row = best
        for k, xs in zip(sorted(g.lanes), lanes):
            for it, x in zip(g.lanes[k].items, xs):
                it.x = x

    def _frog_plan(self, g, sub=5, dt=0.02, max_depth=250):
        """按时间分层的广度优先规划: 每 0.1s 选择一个动作, 同层按 (行, 列) 去重。"""
        actions = [KEY_UP, 0, KEY_LEFT, KEY_RIGHT, KEY_DOWN]
        root = self._frog_snap(g)
        homes0, lives0 = g.homes_occupied, g.lives
        layer = [(root, [])]
        for _ in range(max_depth):
            nxt = {}
            for snap, path in layer:
                for a in actions:
                    self._frog_restore(g, snap)
                    g.update(dt, a, a)
                    for _ in range(sub - 1):
                        if g.lives < lives0 or g.homes_occupied > homes0:
                            break
                        g.update(dt, 0, 0)
                    if g.lives < lives0 or g._state == STATE_GAMEOVER:
                        continue
                    if g.homes_occupied > homes0:
                        self._frog_restore(g, root)
                        return path + [a]
                    key = (g.frog_y, int(round(g.frog_x * 2)))
                    if key not in nxt:
                        nxt[key] = (self._frog_snap(g), path + [a])
            if not nxt:
                break
            best_y = min(k[0] for k in nxt)
            layer = [v for k, v in nxt.items() if k[0] <= best_y + 4]
        self._frog_restore(g, root)
        return None

    def test_13_frogger_planner_fills_all_homes(self):
        g = Game097Frogger()
        g.start()
        for home in range(5):
            plan = self._frog_plan(g)
            self.assertIsNotNone(plan, f"No safe route found for home #{home + 1}")
            for a in plan:
                g.update(0.02, a, a)
                for _ in range(4):
                    if g.homes_occupied > home:
                        break
                    g.update(0.02, 0, 0)
            self.assertEqual(g.homes_occupied, home + 1)
            self.assertEqual(g.lives, 3, "Planner route must not lose lives")
        self.assertEqual(g.state, STATE_VICTORY)
        self.assertTrue(all(g.homes))

    def test_14_frogger_no_score_farming_and_drowning(self):
        g = Game097Frogger()
        g.start()
        frame(g, KEY_UP, KEY_UP)
        self.assertEqual(g.score, 10)
        for _ in range(5):
            frame(g, KEY_DOWN, KEY_DOWN)
            frame(g, KEY_UP, KEY_UP)
        self.assertEqual(g.score, 10, "Hopping back and forth must not farm points")

        # 落水: 在河道(第 5 行)没有浮木的位置 -> 扣命
        g2 = Game097Frogger()
        g2.start()
        for _ in range(9):
            frame(g2, KEY_UP, KEY_UP)
            if g2.lives < 3:
                break
        # 不论是被车撞还是落水, 无脑一路往上冲最终一定会丢命
        for _ in range(int(5 / DT)):
            if g2.lives < 3:
                break
            frame(g2, KEY_UP, KEY_UP)
        self.assertLess(g2.lives, 3)
        self.assertEqual((g2.frog_x, g2.frog_y), (7.0, 14))


if __name__ == "__main__":
    unittest.main(verbosity=2)
