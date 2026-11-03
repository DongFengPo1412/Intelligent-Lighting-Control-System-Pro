# -*- coding: utf-8 -*-
"""
test_arcade_143_plotting.py —— 街机游戏 #143 翻转方块 (Plotting / Flipull 1989 / Taito) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_143_plotting import (
    Game143Plotting,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_NO_MOVES,
    STATE_GAME_OVER,
    COLOR_RED,
    COLOR_BLUE,
    COLOR_GREEN,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame143Plotting(unittest.TestCase):
    def setUp(self):
        self.game = Game143Plotting()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 143)
        self.assertEqual(self.game.name, "翻转方块")
        self.assertEqual(self.game.english_name, "Plotting")
        self.assertEqual(self.game.release_year, 1989)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.hand_block, COLOR_RED)
        self.assertEqual(self.game.wildcards_left, 2)
        self.assertGreater(self.game.target_blocks, 0)

    def test_02_paddle_vertical_movement(self):
        """测试升降台垂直滑轨对准不同目标行"""
        self.assertEqual(self.game.py, 6.0)
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.py, 6.0)

        self.game.update(0.2, KEY_DOWN, 0)
        self.assertGreater(self.game.py, 5.0)

    def test_03_launch_projectile_block(self):
        """测试按键A横向发射手牌方块"""
        self.assertIsNone(self.game.projectile)
        self.game.update(0.05, KEY_A, 0)
        self.assertIsNotNone(self.game.projectile)
        self.assertEqual(self.game.projectile["color"], COLOR_RED)
        self.assertFalse(self.game.projectile["is_wildcard"])

    def test_04_matching_hit_eliminates_cluster(self):
        """测试同色方块碰撞消除连通方块并计分"""
        # Set up a target row with two Red blocks at (7, 6) and (8, 6)
        self.game.py = 6.0
        self.game.hand_block = COLOR_RED
        self.game.board[6][7] = COLOR_RED
        self.game.board[6][8] = COLOR_RED
        self.game.board[6][9] = COLOR_BLUE

        self.game.update(0.05, KEY_A, 0)
        old_score = self.game.score
        old_cleared = self.game.blocks_cleared

        # Update until projectile travels and strikes (7, 6)
        for _ in range(10):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.board[6][7], 0)
        self.assertEqual(self.game.board[6][8], 0)
        self.assertEqual(self.game.blocks_cleared, old_cleared + 2)
        self.assertEqual(self.game.score, old_score + 100)
        # Behind them was Blue, so hand becomes Blue!
        self.assertEqual(self.game.hand_block, COLOR_BLUE)

    def test_05_mismatched_hit_swaps_hand_block(self):
        """测试异色方块碰撞触发手牌与目标方块置换"""
        self.game.py = 6.0
        self.game.hand_block = COLOR_RED
        self.game.board[6][7] = COLOR_GREEN

        self.game.update(0.05, KEY_A, 0)
        old_score = self.game.score

        for _ in range(10):
            self.game.update(0.05, 0, 0)

        # Board gets Red, hand gets Green!
        self.assertEqual(self.game.board[6][7], COLOR_RED)
        self.assertEqual(self.game.hand_block, COLOR_GREEN)
        self.assertEqual(self.game.score, old_score + 20)

    def test_06_wildcard_laser_clears_row(self):
        """测试按键B发射彩虹万能弹消除整行色块"""
        self.assertEqual(self.game.wildcards_left, 2)
        self.game.py = 5.0

        old_cleared = self.game.blocks_cleared
        old_score = self.game.score
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.wildcards_left, 1)

        for _ in range(15):
            self.game.update(0.05, 0, 0)

        self.assertGreater(self.game.blocks_cleared, old_cleared)
        self.assertGreater(self.game.score, old_score)

    def test_07_gravity_cascade_drop(self):
        """测试方块消除后上方色块重力级联崩落"""
        # Column 7: row 5 has Green, row 6 has Red
        self.game.board[5][7] = COLOR_GREEN
        self.game.board[6][7] = COLOR_RED
        self.game.board[7][7] = 0

        # Clear row 6
        self.game.board[6][7] = 0
        self.game._apply_gravity()

        # Green block should drop down to row 13 (bottom of stack)
        self.assertEqual(self.game.board[13][7], COLOR_GREEN)
        self.assertEqual(self.game.board[5][7], 0)

    def test_08_quota_reached_stage_clear(self):
        """测试消除数量达到过关配额顺利通关"""
        self.game.blocks_cleared = self.game.target_blocks - 1
        self.game.py = 6.0
        self.game.hand_block = COLOR_RED
        self.game.board[6][7] = COLOR_RED

        old_score = self.game.score
        self.game.update(0.05, KEY_A, 0)
        for _ in range(10):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, old_score + 1000)

    def test_09_time_depletion_loses_life(self):
        """测试倒计时耗尽扣除生命"""
        self.game.time_left = 0.05
        old_lives = self.game.lives
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_NO_MOVES)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_10_status_dict_reporting(self):
        """测试状态字典输出完整性"""
        status = self.game.get_status()
        self.assertEqual(status["game_id"], 143)
        self.assertEqual(status["name"], "翻转方块")
        self.assertEqual(status["english_name"], "Plotting")
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["hand_block"], COLOR_RED)
        self.assertEqual(status["wildcards"], 2)


if __name__ == "__main__":
    unittest.main()

