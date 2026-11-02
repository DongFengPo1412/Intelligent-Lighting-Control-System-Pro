# -*- coding: utf-8 -*-
"""
test_arcade_005_flappy_bird.py —— 飞翔小鸟 16 自动化单元测试
验证重力加速度、单键瞬时拍翅脉冲、双段管道碰撞检测、过关计分与状态机
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_TAP_SINGLE,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)
from arcade.game_005_flappy_bird import Game005FlappyBird, PipeObstacle
from arcade.arcade_registry import ArcadeRegistry

class TestArcade005FlappyBird(unittest.TestCase):
    def setUp(self):
        self.game = Game005FlappyBird()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册表信息"""
        self.assertEqual(self.game.game_id, 5)
        self.assertEqual(self.game.name, "飞翔小鸟")
        self.assertEqual(self.game.release_year, 2013)
        self.assertEqual(self.game.control_type, CTRL_TAP_SINGLE)
        self.assertIn("单键轻触", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(5)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "飞翔小鸟")

    def test_initial_render_and_dimensions(self):
        """测试初始帧渲染非黑有效性与天空/地面/管道图元"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查非全黑像素数量
        non_zero = sum(1 for b in fb if b > 0)
        self.assertGreater(non_zero, 600)

    def test_gravity_and_tap_impulse(self):
        """测试持续重力下落与单键脉冲拍翅冲量"""
        self.game.bird_y = 6.0
        self.game.bird_vy = 0.0

        # 一步重力下落
        self.game.update(0.033, 0, 0)
        self.assertGreater(self.game.bird_vy, 0.0) # 向下速度增长
        self.assertGreater(self.game.bird_y, 6.0)  # 位置向下位移

        # 单键轻点 (无论是 KEY_A, KEY_B, KEY_UP, KEY_DOWN 任意键)
        self.game.update(0.033, 0, KEY_A)
        self.assertLess(self.game.bird_vy, 0.0) # 速度转为向上冲刺
        self.assertAlmostEqual(self.game.bird_vy, -11.0, delta=1.5)
        self.assertTrue(self.game.flap_anim)

    def test_pipe_horizontal_scrolling(self):
        """测试管道向左卷轴推进"""
        old_x0 = self.game.pipes[0].x
        self.game.update(0.033, 0, 0)
        self.assertLess(self.game.pipes[0].x, old_x0)

    def test_score_increment_on_pipe_pass(self):
        """测试小鸟飞越管道列后计分递增"""
        initial_score = self.game.score
        # 将第 0 根管道放置在小鸟右前方
        self.game.pipes[0] = PipeObstacle(x=3.5, gap_y=5, gap_height=5)
        self.game.bird_x = 3.0
        self.game.bird_y = 6.0 # 处于安全间隙内

        # 步进让管道移过小鸟 (x < 1.0)
        for _ in range(20):
            self.game.update(0.033, 0, 0)
            if self.game.state == STATE_GAMEOVER:
                break

        self.assertEqual(self.game.score, initial_score + 1)

    def test_collision_with_ceiling_and_ground(self):
        """测试撞击天花板或撞击地面死亡"""
        # 1. 撞击地面
        self.game.bird_y = 14.0
        self.game.bird_vy = 5.0
        self.game.update(0.033, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

        # 2. 撞击天花板
        self.game.reset()
        self.game.bird_y = -0.5
        self.game.bird_vy = -5.0
        self.game.update(0.033, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_collision_with_upper_pipe(self):
        """测试撞击上半截管道死亡"""
        # 管道缝隙在 y=6~11，将小鸟放在 y=2 (撞击上方管道)
        self.game.pipes[0] = PipeObstacle(x=3.0, gap_y=6, gap_height=5)
        self.game.bird_x = 3.0
        self.game.bird_y = 2.0
        self.game.bird_vy = 0.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_collision_with_lower_pipe(self):
        """测试撞击下半截管道死亡"""
        # 管道缝隙在 y=2~7，将小鸟放在 y=9 (撞击下方管道)
        self.game.pipes[0] = PipeObstacle(x=3.0, gap_y=2, gap_height=5)
        self.game.bird_x = 3.0
        self.game.bird_y = 9.0
        self.game.bird_vy = 0.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_safe_passage_through_gap(self):
        """测试小鸟位于安全空隙内平稳穿过不碰撞"""
        # 管道缝隙在 y=4~9，小鸟放在 y=5.5，完美处于缝隙中
        self.game.pipes[0] = PipeObstacle(x=3.0, gap_y=4, gap_height=5)
        self.game.bird_x = 3.0
        self.game.bird_y = 5.5
        self.game.bird_vy = 0.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_pause_and_reset(self):
        """测试暂停与重新开局"""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.game.update(0.033, 0, KEY_START)
        self.assertEqual(self.game.state, STATE_PAUSED)

        self.game.update(0.033, 0, KEY_START)
        self.assertEqual(self.game.state, STATE_PLAYING)

if __name__ == "__main__":
    unittest.main()
