# -*- coding: utf-8 -*-
"""
test_arcade_012_highway_racer.py —— 极速变道赛车 1982 完整单元测试
验证三车道超车、油门加减速、护栏擦碰、追尾碰撞、里程积累与终点胜负
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_012_highway_racer import Game012HighwayRacer
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_TWO_BUTTON,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame012HighwayRacer(unittest.TestCase):
    def setUp(self):
        self.game = Game012HighwayRacer()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 12)
        self.assertEqual(self.game.name, "极速变道赛车")
        self.assertEqual(self.game.english_name, "Highway Racer 1982")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_TWO_BUTTON)

        cart = ArcadeRegistry.get_cartridge(12)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "极速变道赛车")

    def test_steering_and_lane_changing(self):
        """测试左右变道转向平滑移动"""
        self.assertEqual(self.game.car_x, 7.0)

        # 向左打方向
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.car_x, 7.0)

        # 向右打方向
        for _ in range(3):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.car_x, 7.0)

    def test_throttle_acceleration_and_braking(self):
        """测试油门加速、刹车制动与自然阻力回归"""
        base_speed = self.game.speed

        # 油门加速 (KEY_UP / KEY_A)
        for _ in range(10):
            self.game.update(0.05, KEY_UP, 0)
        self.assertGreater(self.game.speed, base_speed)
        self.assertLessEqual(self.game.speed, 28.0)

        # 刹车减速 (KEY_DOWN / KEY_B)
        for _ in range(25):
            self.game.update(0.05, KEY_DOWN, 0)
        self.assertLess(self.game.speed, base_speed)
        self.assertGreaterEqual(self.game.speed, 8.0)

    def test_road_verge_collision(self):
        """测试冲撞左/右护栏路肩导致翻车损命"""
        self.assertEqual(self.game.lives, 3)

        # 冲向左侧护栏 (x < 2.4)
        self.game.car_x = 2.2
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.car_x, 7.0) # 重新回到中央车道

        # 冲向右侧护栏 (x > 11.6)
        self.game.car_x = 11.8
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 1)

    def test_traffic_rear_end_collision(self):
        """测试追尾前方慢车导致翻车损命"""
        # 手动放置敌车在玩家正前方 (玩家位于 y=13..14, x=7.0)
        self.game.traffic[0].active = True
        self.game.traffic[0].x = 7.0
        self.game.traffic[0].y = 13.2
        self.game.traffic[0].height = 2
        self.game.traffic[0].speed = 5.0
        self.game.speed = 20.0

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.car_x, 7.0)

    def test_overtaking_traffic_score_bonus(self):
        """测试成功超车获取超车额外奖励积分"""
        initial_score = self.game.score
        # 放置敌车在玩家后方即将离开屏幕处
        self.game.traffic[0].active = True
        self.game.traffic[0].x = 3.5 # 在左车道，玩家在中车道
        self.game.traffic[0].y = 15.2
        self.game.traffic[0].speed = 5.0
        self.game.speed = 20.0

        # 敌车被甩至屏幕后方 y > 15.5
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.traffic[0].active)
        self.assertEqual(self.game.score, initial_score + 50)

    def test_odometer_distance_accumulation(self):
        """测试行驶里程随速度与时间平稳累加"""
        initial_dist = self.game.distance_m
        self.game.update(0.1, 0, 0)
        self.assertGreater(self.game.distance_m, initial_dist)

    def test_finish_line_victory(self):
        """测试累计行驶 1000 米冲线通关"""
        self.game.distance_m = 999.0
        self.game.speed = 20.0

        self.game.update(0.05, 0, 0)
        self.assertGreaterEqual(self.game.distance_m, 1000.0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_gameover_on_zero_lives(self):
        """测试 3 次撞车后游戏结束"""
        self.game.lives = 1
        self.game.crash_car()
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
