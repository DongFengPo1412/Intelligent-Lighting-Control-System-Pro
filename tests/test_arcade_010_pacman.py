# -*- coding: utf-8 -*-
"""
test_arcade_010_pacman.py —— 像素吃豆人 1980 完整单元测试
验证迷宫寻路、吃豆计分、穿梭隧道、幽灵巡逻、大力丸能量反噬与胜败逻辑
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_010_pacman import Game010Pacman, GHOST_CHASE, GHOST_FRIGHTENED
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

class TestGame010Pacman(unittest.TestCase):
    def setUp(self):
        self.game = Game010Pacman()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 10)
        self.assertEqual(self.game.name, "像素吃豆人")
        self.assertEqual(self.game.english_name, "Pac-Man 1980")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)

        cart = ArcadeRegistry.get_cartridge(10)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "像素吃豆人")

    def test_maze_dots_and_power_pellets(self):
        """测试迷宫初始化：四角大力丸与豆子总数"""
        self.assertGreater(self.game.remaining_dots, 50)
        # 验证四角大力丸
        self.assertEqual(self.game.grid[1][1], 2)
        self.assertEqual(self.game.grid[1][14], 2)
        self.assertEqual(self.game.grid[14][1], 2)
        self.assertEqual(self.game.grid[14][14], 2)

    def test_pacman_wall_collision(self):
        """测试吃豆人无法穿透墙壁"""
        # 初始位置 (8.0, 10.0), 向上是 (8, 9) 墙壁
        self.assertTrue(self.game.is_wall(8, 9))
        self.game.update(0.1, KEY_UP, 0)
        # 应被墙挡住停在原位或非常接近
        self.assertAlmostEqual(self.game.pac_y, 10.0, delta=0.1)

    def test_pacman_eats_dot(self):
        """测试吃普通小豆增加10分并削减剩余豆数"""
        # (8, 10) 起始处下方 (8, 11) 是墙，但左方 (7, 10) 是小豆
        initial_dots = self.game.remaining_dots
        initial_score = self.game.score

        # 向左连续移动直到踏入 (7, 10) 豆子格子
        for _ in range(6):
            self.game.update(0.04, KEY_LEFT, 0)
        self.assertLess(self.game.pac_x, 7.5)
        self.assertEqual(self.game.remaining_dots, initial_dots - 1)
        self.assertEqual(self.game.score, initial_score + 10)

    def test_power_pellet_triggers_frightened_mode(self):
        """测试吃下大力丸激活惊恐逃跑态与倒计时"""
        # 直接放置在 (1, 1) 大力丸上
        self.game.pac_x = 1.0
        self.game.pac_y = 1.0
        self.assertEqual(self.game.grid[1][1], 2)

        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.grid[1][1], 0)
        self.assertEqual(self.game.score, 50)
        self.assertGreater(self.game.frightened_timer, 5.0)

        # 所有幽灵进入惊恐态
        for g in self.game.ghosts:
            self.assertEqual(g.state, GHOST_FRIGHTENED)

    def test_horizontal_tunnel_wrap(self):
        """测试 Row 7 左右穿梭隧道瞬间循环对穿"""
        # 放置在隧道左边缘并向左飞奔
        self.game.pac_x = 0.1
        self.game.pac_y = 7.0
        self.game.pac_dir_x = -1
        self.game.pac_dir_y = 0

        self.game.update(0.05, KEY_LEFT, 0)
        # 穿过 0 应该瞬移到接近 15.0
        self.assertGreater(self.game.pac_x, 14.0)

    def test_ghost_kills_pacman_in_normal_mode(self):
        """测试正常模式下接触幽灵扣除1命并重置站位"""
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.ghosts[0].state, GHOST_CHASE)

        # 幽灵瞬移到吃豆人身上
        self.game.ghosts[0].x = self.game.pac_x
        self.game.ghosts[0].y = self.game.pac_y

        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.lives, 2)
        # 位置已重置
        self.assertEqual(self.game.pac_x, 8.0)
        self.assertEqual(self.game.pac_y, 10.0)

    def test_pacman_eats_frightened_ghost(self):
        """测试惊恐模式下吃豆人可反噬吞食幽灵并获200分"""
        self.game.frightened_timer = 5.0
        self.game.ghosts[0].state = GHOST_FRIGHTENED
        self.game.ghosts[0].x = self.game.pac_x
        self.game.ghosts[0].y = self.game.pac_y

        initial_score = self.game.score
        initial_lives = self.game.lives

        self.game.update(0.01, 0, 0)
        # 吃掉幽灵，不扣命，加 200 分
        self.assertEqual(self.game.lives, initial_lives)
        self.assertEqual(self.game.score, initial_score + 200)
        self.assertEqual(self.game.ghosts[0].state, GHOST_CHASE) # 幽灵重生

    def test_gameover_on_zero_lives(self):
        """测试 3 次丧命后游戏结束"""
        self.game.lives = 1
        self.game.ghosts[0].x = self.game.pac_x
        self.game.ghosts[0].y = self.game.pac_y

        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_victory_on_all_dots_cleared(self):
        """测试清空全图所有豆子后通关"""
        self.game.remaining_dots = 1
        for y in range(16):
            for x in range(16):
                self.game.grid[y][x] = 0
        # 仅剩当前所在位置一枚
        self.game.grid[10][8] = 1

        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.remaining_dots, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
