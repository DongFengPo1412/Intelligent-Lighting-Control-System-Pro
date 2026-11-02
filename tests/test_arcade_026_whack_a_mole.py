# -*- coding: utf-8 -*-
"""
test_arcade_026_whack_a_mole.py —— 像素打地鼠 1976 完整单元测试
验证 3x3 洞穴网格、准星快速移动、地鼠探头与超时缩回、普通/黄金/炸弹敲击判定与限时结算
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_026_whack_a_mole import (
    Game026WhackAMole,
    MOLE_NORMAL,
    MOLE_GOLDEN,
    MOLE_BOMB,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame026WhackAMole(unittest.TestCase):
    def setUp(self):
        self.game = Game026WhackAMole()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心集成"""
        self.assertEqual(self.game.game_id, 26)
        self.assertEqual(self.game.name, "像素打地鼠")
        self.assertEqual(self.game.english_name, "Whack-A-Mole 1976")
        self.assertEqual(self.game.release_year, 1976)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("地洞多态探头", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(26)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "像素打地鼠")

    def test_holes_initialization(self):
        """测试 3x3 共 9 个洞穴初始化就绪"""
        self.assertEqual(len(self.game.holes), 9)
        for h in self.game.holes:
            self.assertFalse(h["popped"])
            self.assertFalse(h["whacked"])

        self.assertEqual(self.game.cursor_row, 1)
        self.assertEqual(self.game.cursor_col, 1)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.time_remaining, 45.0)

    def test_cursor_navigation_and_clamping(self):
        """测试方向键控制准星在 3x3 矩阵洞穴间切换移动与边界限位"""
        self.assertEqual(self.game.cursor_row, 1)
        self.assertEqual(self.game.cursor_col, 1)

        # 向上移到 row=0
        self.game.update(0.05, 0, KEY_UP)
        self.assertEqual(self.game.cursor_row, 0)

        # 再次向上触发上限位限制
        self.game.update(0.05, 0, KEY_UP)
        self.assertEqual(self.game.cursor_row, 0)

        # 向左移到 col=0
        self.game.update(0.05, 0, KEY_LEFT)
        self.assertEqual(self.game.cursor_col, 0)

        # 向下向下移到 row=2
        self.game.update(0.05, 0, KEY_DOWN)
        self.game.update(0.05, 0, KEY_DOWN)
        self.assertEqual(self.game.cursor_row, 2)

    def test_whack_normal_mole_scoring(self):
        """测试挥锤击中冒头的普通地鼠奖励 100 分"""
        # 在准星当前所在洞穴 (row=1, col=1 -> idx=4) 放置普通地鼠
        idx = 4
        h = self.game.holes[idx]
        h["popped"] = True
        h["type"] = MOLE_NORMAL
        h["whacked"] = False
        h["pop_timer"] = 1.0

        self.assertEqual(self.game.score, 0)
        self.game.update(0.05, 0, KEY_A) # 挥锤！

        self.assertTrue(h["whacked"])
        self.assertEqual(self.game.score, 100)
        self.assertGreater(self.game.hammer_anim_timer, 0.1)

    def test_whack_golden_mole_bonus(self):
        """测试挥锤击中黄金地鼠奖励 300 分大奖"""
        idx = 4
        h = self.game.holes[idx]
        h["popped"] = True
        h["type"] = MOLE_GOLDEN
        h["whacked"] = False
        h["pop_timer"] = 1.0

        self.game.update(0.05, 0, KEY_A)
        self.assertTrue(h["whacked"])
        self.assertEqual(self.game.score, 300)

    def test_whack_bomb_mole_damage(self):
        """测试误敲刺球炸弹扣减生命，命尽触发 GAMEOVER"""
        idx = 4
        h = self.game.holes[idx]
        h["popped"] = True
        h["type"] = MOLE_BOMB
        h["whacked"] = False
        h["pop_timer"] = 1.0

        self.assertEqual(self.game.lives, 3)
        self.game.update(0.05, 0, KEY_A)
        self.assertEqual(self.game.lives, 2)

        # 连敲两次炸弹导致淘汰
        self.game.lives = 1
        h["whacked"] = False
        self.game.update(0.05, 0, KEY_A)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_whack_empty_hole_no_score(self):
        """测试敲击空洞穴挥空不计分"""
        idx = 4
        h = self.game.holes[idx]
        h["popped"] = False

        self.game.update(0.05, 0, KEY_A)
        self.assertEqual(self.game.score, 0)

    def test_mole_pop_and_auto_retract(self):
        """测试地鼠若未被击打在倒计时结束后自动缩回洞穴"""
        idx = 2
        h = self.game.holes[idx]
        h["popped"] = True
        h["pop_timer"] = 0.08
        h["whacked"] = False

        # 推进时间直至缩回
        for _ in range(4):
            self.game.update(0.05, 0, 0)

        self.assertFalse(h["popped"])

    def test_time_expiration_victory_or_loss(self):
        """测试 45s 时间耗尽时根据是否达到 1500 分进行胜负裁决"""
        self.game.time_remaining = 0.08
        self.game.score = 1600 # 达标

        for _ in range(4):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_VICTORY)

        # 未达标情况
        self.game.reset()
        self.game.time_remaining = 0.08
        self.game.score = 600

        for _ in range(4):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 顶部生命指示红心 [231, 76, 60]
        self.assertEqual(fb[0], 231)
        self.assertEqual(fb[1], 76)
        self.assertEqual(fb[2], 60)

        # 绿草地 [20, 50, 25] (第 1 行起)
        idx_grass = (1 * 16 + 0) * 3
        self.assertEqual(fb[idx_grass + 0], 20)
        self.assertEqual(fb[idx_grass + 1], 50)
        self.assertEqual(fb[idx_grass + 2], 25)

    def test_status_reporting(self):
        """测试状态字典与目标分数完成比率"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)

        self.game.score = 750
        st = self.game.get_status()
        self.assertEqual(st["progress"], 50)


if __name__ == "__main__":
    unittest.main()
