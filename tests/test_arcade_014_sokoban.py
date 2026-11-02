# -*- coding: utf-8 -*-
"""
test_arcade_014_sokoban.py —— 经典推箱子 1982 完整单元测试
验证离散推箱逻辑、单箱推动、双箱禁推、撞墙阻挡、槽位归位与通关判定
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_014_sokoban import Game014Sokoban, SOKOBAN_WALL, SOKOBAN_GOAL
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    STATE_PLAYING,
    STATE_VICTORY,
    CTRL_DPAD_4WAY,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame014Sokoban(unittest.TestCase):
    def setUp(self):
        self.game = Game014Sokoban()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 14)
        self.assertEqual(self.game.name, "经典推箱子")
        self.assertEqual(self.game.english_name, "Sokoban 1982")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)

        cart = ArcadeRegistry.get_cartridge(14)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "经典推箱子")

    def test_warehouse_layout_and_boxes(self):
        """测试仓库格局与箱子槽位初始分布"""
        self.assertEqual(len(self.game.boxes), 4)
        self.assertEqual(self.game.boxes_on_goal, 0)
        self.assertTrue(self.game.is_goal(4, 4))
        self.assertTrue(self.game.is_goal(11, 11))
        self.assertEqual(self.game.map[2][2], SOKOBAN_WALL)

    def test_player_floor_movement(self):
        """测试空地自由走步与步数累加"""
        self.assertEqual(self.game.player_x, 7)
        self.assertEqual(self.game.player_y, 8)
        self.assertEqual(self.game.moves, 0)

        # 向上走一步至 (7, 7) 空地 (避开箱子)
        # 初始箱子在 (5,6), (6,6), (9,9), (10,9)
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.player_y, 7)
        self.assertEqual(self.game.player_x, 7)
        self.assertEqual(self.game.moves, 1)

    def test_wall_blocks_player(self):
        """测试玩家无法穿透仓库砖墙"""
        self.game.player_x = 3
        self.game.player_y = 3
        # 左侧 x=2 是墙
        self.assertEqual(self.game.map[3][2], SOKOBAN_WALL)

        self.game.update(0.02, 0, KEY_LEFT)
        self.assertEqual(self.game.player_x, 3)

    def test_push_single_box(self):
        """测试推单个箱子前进一格"""
        # 箱子 0 位于 (5, 6)
        self.game.player_x = 5
        self.game.player_y = 7 # 位于箱子正下方

        # 向上推箱子
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.player_x, 5)
        self.assertEqual(self.game.player_y, 6)
        self.assertEqual(self.game.boxes[0].x, 5)
        self.assertEqual(self.game.boxes[0].y, 5) # 箱子被推到 (5, 5)

    def test_cannot_push_box_into_wall(self):
        """测试箱子贴墙时无法继续推挤"""
        # 将箱子贴紧墙壁 (3, 3), 左侧 (2, 3) 为墙
        self.game.boxes[0].x = 3
        self.game.boxes[0].y = 3
        self.game.player_x = 4
        self.game.player_y = 3

        # 向左推贴墙箱子
        self.game.update(0.02, 0, KEY_LEFT)
        # 被阻挡，箱子与玩家坐标保持不变
        self.assertEqual(self.game.boxes[0].x, 3)
        self.assertEqual(self.game.player_x, 4)

    def test_cannot_push_two_boxes_together(self):
        """测试双箱相叠时无法同时推动两个箱子"""
        # 放置箱子 0 在 (6, 6)，箱子 1 在 (5, 6)
        self.game.boxes[0].x = 6
        self.game.boxes[0].y = 6
        self.game.boxes[1].x = 5
        self.game.boxes[1].y = 6
        self.game.player_x = 7
        self.game.player_y = 6 # 玩家在箱子 0 右侧

        # 尝试向左推箱子 0 (其左侧也是箱子)
        self.game.update(0.02, 0, KEY_LEFT)
        self.assertEqual(self.game.player_x, 7)
        self.assertEqual(self.game.boxes[0].x, 6)
        self.assertEqual(self.game.boxes[1].x, 5)

    def test_box_on_goal_highlights(self):
        """测试箱子推入目标槽位高亮并计入归位数"""
        # 目标槽位在 (4, 4), (4, 5), (11, 10), (11, 11)
        self.game.boxes[0].x = 4
        self.game.boxes[0].y = 4
        self.game.check_victory()
        self.assertEqual(self.game.boxes_on_goal, 1)

    def test_reset_level_on_button(self):
        """测试按 A 键重置关卡解开死锁"""
        self.game.player_x = 3
        self.game.player_y = 3
        self.game.boxes[0].x = 3
        self.game.boxes[0].y = 4

        self.game.update(0.02, 0, KEY_A)
        # 恢复默认初始站位
        self.assertEqual(self.game.player_x, 7)
        self.assertEqual(self.game.player_y, 8)
        self.assertEqual(self.game.boxes[0].x, 5)
        self.assertEqual(self.game.boxes[0].y, 6)

    def test_victory_on_all_four_boxes_on_goals(self):
        """测试所有 4 个箱子完全归位触发通关"""
        # 人工设置前 3 个归位 (4, 4), (5, 4), (10, 11)
        self.game.boxes[0].x, self.game.boxes[0].y = 4, 4
        self.game.boxes[1].x, self.game.boxes[1].y = 5, 4
        self.game.boxes[2].x, self.game.boxes[2].y = 10, 11
        # 第 4 个位于 (11, 12)，玩家位于 (11, 13)
        self.game.boxes[3].x, self.game.boxes[3].y = 11, 12
        self.game.player_x, self.game.player_y = 11, 13

        # 向上推入最后一个目标点 (11, 11)
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.boxes_on_goal, 4)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 0)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
