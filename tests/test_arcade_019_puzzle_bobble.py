# -*- coding: utf-8 -*-
"""
test_arcade_019_puzzle_bobble.py —— 像素泡泡龙 1994 完整单元测试
验证仰角瞄准、侧壁反弹、吸附碰撞、三连消除、悬空孤岛脱落与清屏通关判定
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_019_puzzle_bobble import Game019PuzzleBobble, BUBBLE_NONE, BUBBLE_RED, BUBBLE_BLUE
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_A,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_TWO_BUTTON,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame019PuzzleBobble(unittest.TestCase):
    def setUp(self):
        self.game = Game019PuzzleBobble()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 19)
        self.assertEqual(self.game.name, "像素泡泡龙")
        self.assertEqual(self.game.english_name, "Puzzle Bobble 1994")
        self.assertEqual(self.game.release_year, 1994)
        self.assertEqual(self.game.control_type, CTRL_TWO_BUTTON)

        cart = ArcadeRegistry.get_cartridge(19)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "像素泡泡龙")

    def test_pointer_rotation_and_clamping(self):
        """测试仰角瞄准在 [-60°, 60°] 区间平滑旋转"""
        self.assertEqual(self.game.angle_deg, 0.0)

        # 向左旋转
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.angle_deg, 0.0)

        # 极限旋转到左限位
        for _ in range(20):
            self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.angle_deg, -60.0)

        # 极限旋转到右限位
        for _ in range(50):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.angle_deg, 60.0)

    def test_fire_bubble_and_wall_bounce(self):
        """测试发射泡泡沿指定斜角飞行并触发侧壁弹性反弹"""
        self.assertFalse(self.game.flying.active)
        self.game.angle_deg = 45.0 # 向右斜上方发射

        self.game.update(0.02, 0, KEY_A)
        self.assertTrue(self.game.flying.active)
        self.assertGreater(self.game.flying.vx, 0.0)
        self.assertLess(self.game.flying.vy, 0.0)

        # 人工推进至右墙 (x >= 15.0)
        self.game.flying.x = 14.9
        self.game.update(0.02, 0, 0)
        # 反弹后 vx 变成负值向左飞
        self.assertLess(self.game.flying.vx, 0.0)

    def test_ceiling_attachment(self):
        """测试直冲天花板顶格吸附"""
        # 清空网格以保证 (0, 7) 为空位
        for y in range(14):
            for x in range(16):
                self.game.grid[y][x] = BUBBLE_NONE

        self.game.angle_deg = 0.0 # 垂直向上
        self.game.flying.active = True
        self.game.flying.x = 7.0
        self.game.flying.y = 1.0
        self.game.flying.vy = -18.0
        self.game.flying.color = BUBBLE_RED

        # 冲撞天花板
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.flying.active)
        self.assertEqual(self.game.grid[0][7], BUBBLE_RED)

    def test_cluster_match_three_pop(self):
        """测试同色泡泡三连对撞消解爆破"""
        # 预设在天花板有两个相连的红球 (0, 7) 与 (0, 8)
        for y in range(14):
            for x in range(16):
                self.game.grid[y][x] = BUBBLE_NONE
        self.game.grid[0][7] = BUBBLE_RED
        self.game.grid[0][8] = BUBBLE_RED

        initial_score = self.game.score
        # 第三颗红球吸附在 (1, 7)
        self.game.snap_and_resolve(7.0, 1.0, BUBBLE_RED)

        # 触发 3 连消除
        self.assertEqual(self.game.grid[0][7], BUBBLE_NONE)
        self.assertEqual(self.game.grid[0][8], BUBBLE_NONE)
        self.assertEqual(self.game.grid[1][7], BUBBLE_NONE)
        self.assertGreater(self.game.score, initial_score)

    def test_floating_island_drop_physics(self):
        """测试根基断开后悬空孤岛泡泡整体坠落"""
        # 清空网格
        for y in range(14):
            for x in range(16):
                self.game.grid[y][x] = BUBBLE_NONE

        # 构造天花板悬挂桥梁:
        # (0, 5)红, (0, 6)红
        # 下方挂着一串蓝球: (1, 6)蓝, (2, 6)蓝 (孤岛)
        self.game.grid[0][5] = BUBBLE_RED
        self.game.grid[0][6] = BUBBLE_RED
        self.game.grid[1][6] = BUBBLE_BLUE
        self.game.grid[2][6] = BUBBLE_BLUE

        initial_score = self.game.score
        # 射入第三颗红球到 (0, 7)，引爆天花板红球桥梁
        self.game.snap_and_resolve(7.0, 0.0, BUBBLE_RED)

        # 红球被消解
        self.assertEqual(self.game.grid[0][5], BUBBLE_NONE)
        self.assertEqual(self.game.grid[0][6], BUBBLE_NONE)

        # 下方失去天花板连通的蓝球应全数脱落消解
        self.assertEqual(self.game.grid[1][6], BUBBLE_NONE)
        self.assertEqual(self.game.grid[2][6], BUBBLE_NONE)
        # 且获得额外悬空脱落巨额奖励
        self.assertGreater(self.game.score, initial_score + 100)

    def test_breaching_baseline_causes_gameover(self):
        """测试泡泡触及底线警戒线 (y >= 13) 游戏失败"""
        self.assertEqual(self.game.state, STATE_PLAYING)
        # 将泡泡吸附在 y=13
        self.game.snap_and_resolve(7.0, 13.0, BUBBLE_RED)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_ceiling_descent_every_six_shots(self):
        """测试每发射 6 次后天花板下压一行"""
        for y in range(14):
            for x in range(16):
                self.game.grid[y][x] = BUBBLE_NONE

        # 放置一个黄色泡泡在 (0, 0)
        self.game.grid[0][0] = 4
        self.game.shots_fired = 6

        # 射入一颗红色泡泡到远端 (0, 10)
        self.game.snap_and_resolve(10.0, 0.0, BUBBLE_RED)
        # 压迫下沉后，原来的 (0, 0) 下移至 (1, 0)
        self.assertEqual(self.game.grid[1][0], 4)

    def test_victory_on_all_bubbles_cleared(self):
        """测试全屏泡泡清空通关"""
        for y in range(14):
            for x in range(16):
                self.game.grid[y][x] = BUBBLE_NONE
        # 仅剩最后两颗红球
        self.game.grid[0][0] = BUBBLE_RED
        self.game.grid[0][1] = BUBBLE_RED

        # 击出第三颗红球完成全场清屏
        self.game.snap_and_resolve(2.0, 0.0, BUBBLE_RED)
        self.assertEqual(self.game.count_remaining_bubbles(), 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
