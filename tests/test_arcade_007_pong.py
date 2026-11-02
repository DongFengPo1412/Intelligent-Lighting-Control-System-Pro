# -*- coding: utf-8 -*-
"""
test_arcade_007_pong.py —— 双人乒乓 1972 自动化单元测试
验证刚体小球反弹、挡板切角斜率、速度阶梯递增、双人与AI交互、积分制胜与状态机
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_VERSUS_DUAL,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)
from arcade.game_007_pong import Game007Pong
from arcade.arcade_registry import ArcadeRegistry

class TestArcade007Pong(unittest.TestCase):
    def setUp(self):
        self.game = Game007Pong()

    def test_metadata_and_registry(self):
        """测试卡带元数据与双人手柄类型"""
        self.assertEqual(self.game.game_id, 7)
        self.assertEqual(self.game.name, "双人乒乓")
        self.assertEqual(self.game.release_year, 1972)
        self.assertEqual(self.game.control_type, CTRL_VERSUS_DUAL)
        self.assertIn("刚体小球双向反弹", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(7)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "双人乒乓")

    def test_initial_render_and_dimensions(self):
        """测试初始帧渲染非黑有效性与中线/双侧挡板呈现"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查左右挡板各有像素
        p1_pixels = sum(1 for y in range(16) if fb[(y * 16 + 1) * 3 + 2] > 0)
        p2_pixels = sum(1 for y in range(16) if fb[(y * 16 + 14) * 3] > 0)
        self.assertGreaterEqual(p1_pixels, 3)
        self.assertGreaterEqual(p2_pixels, 3)

    def test_wall_bounces(self):
        """测试小球碰触天花板与地板的刚体弹性反弹"""
        self.game.serve_delay = 0.0
        # 向上撞击天花板 y=0
        self.game.ball_y = 0.2
        self.game.ball_vy = -5.0
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.ball_vy, 0.0) # 反弹向下

        # 向下撞击地板 y=15
        self.game.ball_y = 14.8
        self.game.ball_vy = 5.0
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.ball_vy, 0.0) # 反弹向上

    def test_p1_paddle_bounce_and_speedup(self):
        """测试左侧 P1 挡板精准拦截与对拉提速"""
        self.game.serve_delay = 0.0
        self.game.p1_y = 6.0
        self.game.ball_x = 1.8
        self.game.ball_y = 7.5
        self.game.ball_vx = -8.0
        old_speed = abs(self.game.ball_vx)

        self.game.update(0.02, 0, 0)
        # 反弹后速度应转正 (向右飞) 且速度增加 5%
        self.assertGreater(self.game.ball_vx, 0.0)
        self.assertGreater(abs(self.game.ball_vx), old_speed)

    def test_p2_paddle_bounce(self):
        """测试右侧 P2 挡板拦截反弹"""
        self.game.serve_delay = 0.0
        self.game.p2_y = 6.0
        self.game.ball_x = 13.3
        self.game.ball_y = 7.5
        self.game.ball_vx = 8.0

        self.game.update(0.02, 0, 0)
        # 反弹后速度应转负 (向左飞)
        self.assertLess(self.game.ball_vx, 0.0)

    def test_paddle_hit_angle_modulation(self):
        """测试击中挡板边缘产生更陡峭斜率，击中中心产生平直反弹"""
        self.game.serve_delay = 0.0
        self.game.p1_y = 6.0
        # 击中 P1 顶部边缘 (y=6.0, 中心为 8.0)
        self.game.ball_x = 1.8
        self.game.ball_y = 6.1
        self.game.ball_vx = -8.0
        self.game.update(0.02, 0, 0)
        vy_edge = self.game.ball_vy

        # 击中 P1 中心 (y=8.0)
        self.game.ball_x = 1.8
        self.game.ball_y = 8.0
        self.game.ball_vx = -8.0
        self.game.update(0.02, 0, 0)
        vy_center = self.game.ball_vy

        # 边缘击球的绝对倾角速度应明显大于中心平推
        self.assertLess(vy_edge, 0.0) # 向上斜飞
        self.assertAlmostEqual(vy_center, 0.0, delta=1.0) # 接近水平

    def test_p1_scoring(self):
        """测试球越过右边界 P1 得分"""
        self.game.serve_delay = 0.0
        self.game.ball_x = 15.2
        self.game.ball_vx = 5.0
        self.game.p1_score = 0
        self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.p1_score, 1)

    def test_p2_scoring(self):
        """测试球越过左边界 P2 得分"""
        self.game.serve_delay = 0.0
        self.game.ball_x = -0.5
        self.game.ball_vx = -5.0
        self.game.p2_score = 0
        self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.p2_score, 1)

    def test_match_victory_state(self):
        """测试率先达到 5 分获胜判定"""
        self.game.serve_delay = 0.0
        self.game.p1_score = 4
        self.game.ball_x = 15.2
        self.game.ball_vx = 5.0
        self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.p1_score, 5)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_dual_paddle_controls(self):
        """测试 P1 上下移动与 P2 独立接管"""
        old_p1_y = self.game.p1_y
        self.game.update(0.05, KEY_UP, 0)
        self.assertLess(self.game.p1_y, old_p1_y)

        # 按 KEY_B 接管 P2 向下
        old_p2_y = self.game.p2_y
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.p2_y, old_p2_y)
        self.assertFalse(self.game.p2_is_ai)

if __name__ == "__main__":
    unittest.main()
