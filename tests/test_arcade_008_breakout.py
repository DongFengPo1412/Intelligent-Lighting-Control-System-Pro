# -*- coding: utf-8 -*-
"""
test_arcade_008_breakout.py —— 经典打砖块 1976 完整单元测试
验证打砖块的挡板移动、小球折射、砖块敲碎、耐久度、生命损耗与通关逻辑
"""

import unittest
import sys
import os

# 将 pc-agent-vision 加入系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_008_breakout import Game008Breakout
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_START,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_TWO_BUTTON,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame008Breakout(unittest.TestCase):
    def setUp(self):
        self.game = Game008Breakout()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 8)
        self.assertEqual(self.game.name, "经典打砖块")
        self.assertEqual(self.game.english_name, "Breakout 1976")
        self.assertEqual(self.game.release_year, 1976)
        self.assertEqual(self.game.control_type, CTRL_TWO_BUTTON)

        cart = ArcadeRegistry.get_cartridge(8)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "经典打砖块")

    def test_brick_grid_initialization(self):
        """测试砖块网格初始化: 4排8列共32块，顶排耐久2，其余耐久1"""
        self.assertEqual(len(self.game.bricks), 4)
        self.assertEqual(len(self.game.bricks[0]), 8)
        self.assertEqual(self.game.remaining_bricks, 32)

        # 顶排为红色，耐久 2
        for col in range(8):
            self.assertEqual(self.game.bricks[0][col].hp, 2)
            self.assertEqual(self.game.bricks[0][col].r, 231)

        # 其他排耐久 1
        for row in range(1, 4):
            for col in range(8):
                self.assertEqual(self.game.bricks[row][col].hp, 1)

    def test_paddle_movement_and_clamping(self):
        """测试挡板左右移动与边界限制 [0, 16-paddle_w]"""
        self.assertEqual(self.game.paddle_x, 6.0)

        # 向左移动
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.paddle_x, 6.0)

        # 移出左边界
        for _ in range(20):
            self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.paddle_x, 0.0)

        # 移出右边界 (16 - 4 = 12)
        for _ in range(30):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.paddle_x, 12.0)

    def test_ball_launch_from_paddle(self):
        """测试发球机制：初始吸附在挡板上，按开球键发射"""
        self.assertTrue(self.game.ball_stuck)
        self.game.paddle_x = 4.0
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.ball_x, 4.0 + 2.0)

        # 按 A 发射
        self.game.update(0.02, 0, KEY_A)
        self.assertFalse(self.game.ball_stuck)
        self.assertLess(self.game.ball_vy, 0) # 向上发射

    def test_wall_and_ceiling_bounces(self):
        """测试左、右、顶墙壁反弹"""
        self.game.ball_stuck = False

        # 左墙反弹
        self.game.ball_x = 0.1
        self.game.ball_vx = -5.0
        self.game.ball_y = 10.0
        self.game.ball_vy = -5.0
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.ball_vx, 0)

        # 右墙反弹
        self.game.ball_x = 14.9
        self.game.ball_vx = 5.0
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.ball_vx, 0)

        # 天花板反弹
        self.game.ball_y = 0.1
        self.game.ball_vy = -5.0
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.ball_vy, 0)

    def test_paddle_hit_and_deflection(self):
        """测试挡板命中反弹及不同击球点的角度偏折"""
        self.game.ball_stuck = False
        self.game.paddle_x = 6.0
        self.game.paddle_w = 4.0 # 中心位于 8.0

        # 球向挡板中心落下
        self.game.ball_x = 8.0
        self.game.ball_y = 13.5
        self.game.ball_vy = 8.0
        self.game.ball_vx = 0.0

        self.game.update(0.02, 0, 0)
        # 应向上反弹
        self.assertLess(self.game.ball_vy, 0)
        self.assertAlmostEqual(self.game.ball_vx, 0.0, delta=1.0)

        # 球向挡板右侧边缘落下 (偏折向右)
        self.game.ball_x = 9.5
        self.game.ball_y = 13.5
        self.game.ball_vy = 8.0
        self.game.update(0.02, 0, 0)
        self.assertGreater(self.game.ball_vx, 0)

    def test_brick_collision_and_break(self):
        """测试砖块碰撞、生命削减、计分与反弹"""
        self.game.ball_stuck = False
        # 针对 Row 3 (y=5, 黄色耐久1), Col 2 (x=4~5)
        self.game.ball_x = 4.0
        self.game.ball_y = 5.2
        self.game.ball_vy = -6.0

        initial_bricks = self.game.remaining_bricks
        initial_score = self.game.score

        self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.bricks[3][2].hp, 0)
        self.assertEqual(self.game.remaining_bricks, initial_bricks - 1)
        self.assertGreater(self.game.score, initial_score)
        self.assertGreater(self.game.ball_vy, 0) # 碰砖向下反弹

    def test_double_durability_red_brick(self):
        """测试顶排红色砖块需要敲击两次才碎裂"""
        self.game.ball_stuck = False
        # Row 0 (y=2), Col 3 (x=6~7)
        self.assertEqual(self.game.bricks[0][3].hp, 2)

        # 第1次敲击
        self.game.ball_x = 6.0
        self.game.ball_y = 2.0
        self.game.ball_vy = -5.0
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.bricks[0][3].hp, 1)
        self.assertEqual(self.game.remaining_bricks, 32) # 未碎裂

        # 第2次敲击
        self.game.ball_x = 6.0
        self.game.ball_y = 2.0
        self.game.ball_vy = -5.0
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.bricks[0][3].hp, 0)
        self.assertEqual(self.game.remaining_bricks, 31) # 彻底碎裂

    def test_bottom_fall_and_life_loss(self):
        """测试小球坠落底部损失生命并重置"""
        self.game.ball_stuck = False
        self.game.ball_vy = 6.0
        self.assertEqual(self.game.lives, 3)

        self.game.ball_y = 15.6
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertTrue(self.game.ball_stuck) # 恢复吸附状态

        # 再次坠落两次触发 GameOver
        self.game.ball_stuck = False
        self.game.ball_vy = 6.0
        self.game.ball_y = 15.6
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 1)

        self.game.ball_stuck = False
        self.game.ball_vy = 6.0
        self.game.ball_y = 15.6
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_victory_condition(self):
        """测试击碎所有砖块触发通关"""
        self.game.ball_stuck = False
        # 手动将只剩最后 1 块砖
        self.game.remaining_bricks = 1
        for r in range(4):
            for c in range(8):
                self.game.bricks[r][c].hp = 0
        self.game.bricks[3][0].hp = 1 # 仅剩一块

        self.game.ball_x = 0.5
        self.game.ball_y = 5.0
        self.game.ball_vy = -5.0

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.remaining_bricks, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
