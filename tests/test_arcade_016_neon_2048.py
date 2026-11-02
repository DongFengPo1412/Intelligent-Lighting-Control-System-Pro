# -*- coding: utf-8 -*-
"""
test_arcade_016_neon_2048.py —— 霓虹 2048 完整单元测试
验证4x4网格滑移、同阶数字对撞合并、积分倍增、单次滑动禁双重合并、死锁与2048通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_016_neon_2048 import Game016Neon2048
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_DPAD_4WAY,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame016Neon2048(unittest.TestCase):
    def setUp(self):
        self.game = Game016Neon2048()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 16)
        self.assertEqual(self.game.name, "霓虹 2048")
        self.assertEqual(self.game.english_name, "Neon 2048 2014")
        self.assertEqual(self.game.release_year, 2014)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)

        cart = ArcadeRegistry.get_cartridge(16)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "霓虹 2048")

    def test_initial_two_tiles_spawned(self):
        """测试初始状态下棋盘随机出现两颗方块"""
        non_zeros = sum(1 for r in range(4) for c in range(4) if self.game.board[r][c] != 0)
        self.assertEqual(non_zeros, 2)

    def test_slide_left_simple_movement(self):
        """测试简单滑移压实"""
        self.game.board = [
            [0, 1, 0, 0],
            [0, 0, 2, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        moved = self.game.slide(-1, 0)
        self.assertTrue(moved)
        self.assertEqual(self.game.board[0][0], 1)
        self.assertEqual(self.game.board[1][0], 2)

    def test_slide_and_merge_identical_tiles(self):
        """测试同阶对撞合并 (两枚2合并为4) 及加分"""
        self.game.board = [
            [1, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        initial_score = self.game.score
        moved = self.game.slide(-1, 0)
        self.assertTrue(moved)
        # 1+1 合并为 2 (即 4)
        self.assertEqual(self.game.board[0][0], 2)
        # 加分 2^2 = 4
        self.assertEqual(self.game.score, initial_score + 4)

    def test_no_double_merge_in_single_slide(self):
        """测试单次滑移不可连环合并 [1, 1, 1, 1] -> [2, 2, 0, 0] 而非 [3, 0, 0, 0]"""
        self.game.board = [
            [1, 1, 1, 1],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        self.game.slide(-1, 0)
        self.assertEqual(self.game.board[0][0], 2)
        self.assertEqual(self.game.board[0][1], 2)

    def test_vertical_slide_merging(self):
        """测试垂直上下滑动合并"""
        self.game.board = [
            [2, 0, 0, 0],
            [2, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        moved = self.game.slide(0, -1)
        self.assertTrue(moved)
        self.assertEqual(self.game.board[0][0], 3) # 4+4 合并为 8 (等级 3)

    def test_invalid_slide_does_not_spawn_tile(self):
        """测试不可滑移方向不产生新方块"""
        self.game.board = [
            [1, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        # 已经贴在最左上角，向左和向上滑无效
        moved = self.game.slide(-1, 0)
        self.assertFalse(moved)
        # 数量依然为 1
        non_zeros = sum(1 for r in range(4) for c in range(4) if self.game.board[r][c] != 0)
        self.assertEqual(non_zeros, 1)

    def test_deadlock_gameover(self):
        """测试棋盘全满且无任何可合并对子触发 Game Over"""
        # 棋盘无空槽且红黑交替无法合并
        self.game.board = [
            [1, 2, 1, 2],
            [2, 1, 2, 1],
            [1, 2, 1, 2],
            [2, 1, 2, 1]
        ]
        self.assertFalse(self.game.can_move())

        # 任何尝试移动都无法进行
        moved = self.game.slide(1, 0)
        self.assertFalse(moved)

    def test_victory_on_2048_tile(self):
        """测试合成出等级 11 (2048) 达成胜利"""
        self.game.board = [
            [10, 10, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        self.game.slide(-1, 0)
        self.assertEqual(self.game.board[0][0], 11) # 1024 + 1024 = 2048
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
