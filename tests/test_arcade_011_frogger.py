# -*- coding: utf-8 -*-
"""
test_arcade_011_frogger.py —— 像素青蛙过河 1981 完整单元测试
验证离散跳跃、公路车祸、河流溺水、浮木漂移、五穴进驻与通关胜败逻辑
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_011_frogger import Game011Frogger
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

class TestGame011Frogger(unittest.TestCase):
    def setUp(self):
        self.game = Game011Frogger()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 11)
        self.assertEqual(self.game.name, "青蛙过河")
        self.assertEqual(self.game.english_name, "Frogger 1981")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)

        cart = ArcadeRegistry.get_cartridge(11)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "青蛙过河")

    def test_frog_discrete_movement_and_scoring(self):
        """测试离散网格跳跃及向前跳跃计分"""
        self.assertEqual(self.game.frog_x, 7.0)
        self.assertEqual(self.game.frog_y, 14)
        initial_score = self.game.score

        # 向上跳一步至 Row 13
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.frog_y, 13)
        self.assertEqual(self.game.score, initial_score + 10)

        # 向左跳一步
        self.game.update(0.02, 0, KEY_LEFT)
        self.assertEqual(self.game.frog_x, 6.0)

        # 向右跳一步
        self.game.update(0.02, 0, KEY_RIGHT)
        self.assertEqual(self.game.frog_x, 7.0)

    def test_highway_traffic_collision(self):
        """测试公路遭遇车辆撞击损命并重置"""
        # 将青蛙放置在公路车道 Row 7 (该车道有车位于 x=4.0 处)
        self.game.frog_y = 7
        self.game.frog_x = 4.0
        self.assertEqual(self.game.lives, 3)

        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.lives, 2)
        # 验证站位已被重置到底部站台
        self.assertEqual(self.game.frog_y, 14)
        self.assertEqual(self.game.frog_x, 7.0)

    def test_river_drowning_without_log(self):
        """测试跳入河流无浮木落脚点溺水"""
        # Row 3 (河流), 浮木位于 2.0..6.0 与 10.0..14.0
        # 将青蛙跳入空水域 x=8.0, y=3
        self.game.frog_y = 3
        self.game.frog_x = 8.0
        self.assertEqual(self.game.lives, 3)

        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.frog_y, 14)

    def test_river_floating_with_log(self):
        """测试安全站在浮木上随水流水平漂移"""
        # Row 3 浮木位于 2.0~6.0, 速度 +1.8 向右
        self.game.frog_y = 3
        self.game.frog_x = 3.5
        initial_x = self.game.frog_x

        self.game.update(0.05, 0, 0)
        # 活着且 X 坐标随浮木向右漂移
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.frog_y, 3)
        self.assertGreater(self.game.frog_x, initial_x)

    def test_river_drifting_offscreen_kills_frog(self):
        """测试被浮木带出屏幕边缘致死"""
        self.game.frog_y = 3
        self.game.frog_x = 15.7 # 接近右边缘
        self.game.lanes[3].items[0].x = 14.0 # 确保当前脚下有浮木
        self.game.lanes[3].items[0].width = 4.0

        # 向右漂移超出 15.8
        for _ in range(5):
            self.game.update(0.05, 0, 0)

        # 青蛙被冲走丧生
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.frog_y, 14)

    def test_home_occupation_and_score(self):
        """测试成功跳入荷叶空穴入驻得分"""
        # 终点洞穴在 Row 0, x=7 是中央第 3 个洞穴 (索引 2)
        self.game.frog_y = 1
        self.game.frog_x = 7.0
        # 确保安全站在 Row 1 浮木上
        self.game.lanes[1].items[0].x = 6.0
        self.game.lanes[1].items[0].width = 3.0

        # 按 UP 跳入 Row 0 洞穴
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.frog_y, 14) # 回到起点继续下一只
        self.assertTrue(self.game.homes[2])
        self.assertEqual(self.game.homes_occupied, 1)
        self.assertGreater(self.game.score, 200)

    def test_occupied_home_collision(self):
        """测试跳入已被占领的洞穴导致丧生"""
        self.game.homes[2] = True # 已被占领
        self.game.frog_y = 1
        self.game.frog_x = 7.0
        self.game.lanes[1].items[0].x = 6.0
        self.game.lanes[1].items[0].width = 3.0

        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.lives, 2) # 扣命

    def test_bush_collision_kills_frog(self):
        """测试跳入 Row 0 灌木丛林导致丧生"""
        self.game.frog_y = 1
        self.game.frog_x = 2.5 # 位于洞穴 1 与 4 之间的灌木区
        self.game.lanes[1].items[0].x = 1.0
        self.game.lanes[1].items[0].width = 4.0

        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.lives, 2)

    def test_round_timer_expiration(self):
        """测试时间耗尽导致丧生"""
        self.game.round_timer = 0.01
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 2)

    def test_gameover_on_zero_lives(self):
        """测试 3 次丧生后 Game Over"""
        self.game.lives = 1
        self.game.kill_frog()
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_victory_on_all_homes_filled(self):
        """测试填满全部 5 个荷叶洞穴取得胜利"""
        self.game.homes = [True, True, True, True, False]
        self.game.homes_occupied = 4

        # 跳入最后一个洞穴 (x=13, 索引 4)
        self.game.frog_y = 1
        self.game.frog_x = 13.0
        self.game.lanes[1].items[1].x = 12.0
        self.game.lanes[1].items[1].width = 3.0

        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.homes_occupied, 5)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
