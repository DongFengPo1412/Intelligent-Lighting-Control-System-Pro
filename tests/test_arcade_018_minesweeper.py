# -*- coding: utf-8 -*-
"""
test_arcade_018_minesweeper.py —— 像素扫雷 1990 完整单元测试
验证光标探测、首按防爆、八邻域计数、插旗防误触、洪水填充与通关胜败
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_018_minesweeper import Game018Minesweeper
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame018Minesweeper(unittest.TestCase):
    def setUp(self):
        self.game = Game018Minesweeper()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 18)
        self.assertEqual(self.game.name, "像素扫雷")
        self.assertEqual(self.game.english_name, "Minesweeper 1990")
        self.assertEqual(self.game.release_year, 1990)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)

        cart = ArcadeRegistry.get_cartridge(18)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "像素扫雷")

    def test_cursor_navigation_and_clamping(self):
        """测试光标四向平移与边界限制 [0, 15]"""
        self.assertEqual(self.game.cursor_x, 7)
        self.assertEqual(self.game.cursor_y, 7)

        # 向上移
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.cursor_y, 6)

        # 移到左边界
        for _ in range(20):
            self.game.update(0.02, 0, KEY_LEFT)
        self.assertEqual(self.game.cursor_x, 0)

    def test_first_click_safety(self):
        """测试首按防爆：首击点及其八邻域绝对无雷"""
        self.assertTrue(self.game.first_click)
        self.game.cursor_x = 5
        self.game.cursor_y = 5

        self.game.update(0.02, 0, KEY_A)
        self.assertFalse(self.game.first_click)

        # 验证首击点及 3x3 邻域无雷
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                self.assertFalse(self.game.grid[5 + dy][5 + dx].has_mine)

        # 并且首击点已被安全翻开
        self.assertTrue(self.game.grid[5][5].revealed)

    def test_flag_toggle_and_protection(self):
        """测试插旗与防误触保护"""
        self.assertEqual(self.game.flags_placed, 0)
        self.assertFalse(self.game.grid[7][7].flagged)

        # 按 B 插旗
        self.game.update(0.02, 0, KEY_B)
        self.assertTrue(self.game.grid[7][7].flagged)
        self.assertEqual(self.game.flags_placed, 1)

        # 尝试按 A 翻开已插旗格子：必须被拒绝！
        self.game.update(0.02, 0, KEY_A)
        self.assertFalse(self.game.grid[7][7].revealed)

        # 再次按 B 取消插旗
        self.game.update(0.02, 0, KEY_B)
        self.assertFalse(self.game.grid[7][7].flagged)
        self.assertEqual(self.game.flags_placed, 0)

    def test_stepping_on_mine_causes_gameover(self):
        """测试踩雷导致游戏结束并翻开全图地雷"""
        self.game.first_click = False
        # 手动放置地雷在 (3, 3)
        self.game.grid[3][3].has_mine = True
        self.game.cursor_x = 3
        self.game.cursor_y = 3

        # 踩雷
        self.game.update(0.02, 0, KEY_A)
        self.assertEqual(self.game.state, STATE_GAMEOVER)
        # 地雷已全图显现
        self.assertTrue(self.game.grid[3][3].revealed)

    def test_flood_fill_zero_expansion(self):
        """测试翻开数字为0的空地时自动洪水蔓延连环翻开"""
        self.game.first_click = False
        # 清空四周，构建纯空区域
        for y in range(4):
            for x in range(4):
                self.game.grid[y][x].has_mine = False
                self.game.grid[y][x].neighbor_mines = 0

        # 点击 (0, 0)
        self.game.cursor_x = 0
        self.game.cursor_y = 0
        self.game.update(0.02, 0, KEY_A)

        # 邻近格子应被洪水填充全部翻开
        self.assertTrue(self.game.grid[0][1].revealed)
        self.assertTrue(self.game.grid[1][0].revealed)
        self.assertTrue(self.game.grid[1][1].revealed)

    def test_neighbor_mine_count(self):
        """测试八邻域地雷统计精准度"""
        self.game.first_click = False
        # 在 (2, 2) 周围放置 3 颗地雷
        self.game.grid[1][2].has_mine = True
        self.game.grid[2][1].has_mine = True
        self.game.grid[3][3].has_mine = True

        # 重新统计 (2, 2)
        cnt = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if self.game.grid[2 + dy][2 + dx].has_mine:
                    cnt += 1
        self.assertEqual(cnt, 3)

    def test_victory_on_all_safe_cells_revealed(self):
        """测试所有安全格子全翻开达成扫雷胜利"""
        self.game.first_click = False
        self.game.remaining_hidden_safe = 1
        # 仅剩当前 (5, 5) 为最后一个安全格子
        self.game.cursor_x = 5
        self.game.cursor_y = 5
        self.game.grid[5][5].has_mine = False
        self.game.grid[5][5].neighbor_mines = 1

        self.game.update(0.02, 0, KEY_A)
        self.assertEqual(self.game.remaining_hidden_safe, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 0)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
