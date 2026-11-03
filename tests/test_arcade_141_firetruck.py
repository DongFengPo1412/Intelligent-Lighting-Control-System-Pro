# -*- coding: utf-8 -*-
"""
test_arcade_141_firetruck.py —— 街机游戏 #141 消防云梯车 (Fire Truck 1978 / Atari) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_141_firetruck import (
    Game141FireTruck,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_CRASH,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame141FireTruck(unittest.TestCase):
    def setUp(self):
        self.game = Game141FireTruck()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始铰接状态"""
        self.assertEqual(self.game.game_id, 141)
        self.assertEqual(self.game.name, "消防云梯车")
        self.assertEqual(self.game.english_name, "Fire Truck")
        self.assertEqual(self.game.release_year, 1978)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.distance, 0.0)
        self.assertEqual(self.game.cx, 7.5)
        self.assertEqual(self.game.tx, 7.5)
        self.assertEqual(self.game.hitch_angle, 0.0)
        self.assertEqual(len(self.game.obstacles), 4)

    def test_02_acceleration_and_distance_accumulation(self):
        """测试油门加速与出警行程累加"""
        old_speed = self.game.speed
        self.game.update(0.1, KEY_UP, 0)
        self.assertGreater(self.game.speed, old_speed)
        self.assertGreater(self.game.distance, 0.0)
        self.assertGreater(self.game.score, 0)

    def test_03_braking_and_speed_reduction(self):
        """测试刹车减速控制"""
        self.game.speed = 8.0
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertLess(self.game.speed, 8.0)

    def test_04_cab_steering_and_hitch_swing(self):
        """测试车头转向驱动后部挂车铰链角度摆动"""
        self.assertEqual(self.game.cx, 7.5)
        # Steer cab left
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.cx, 7.5)
        # Hitch angle should diverge as trailer lags
        self.assertNotEqual(self.game.hitch_angle, 0.0)

    def test_05_rear_tiller_counter_steering(self):
        """测试按键A/B独立操纵后桥舵轮主动纠偏"""
        self.game.cx = 7.0
        self.game.tx = 7.5
        # Trailer tx is larger than cx. Use Key A to steer trailer left!
        tx_before = self.game.tx
        self.game.update(0.1, KEY_A, 0)
        self.assertLess(self.game.tx, tx_before)

    def test_06_jackknife_spinout_crash(self):
        """测试剧烈甩尾导致折叠绞盘失控事故扣除生命"""
        # Manually create severe jackknife
        self.game.cx = 10.0
        self.game.tx = 4.0
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_07_cab_hits_curb_building(self):
        """测试前车头擦碰路边路肩导致碰撞"""
        self.game.cx = 15.0  # Far outside curb
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_08_trailer_clips_curb_building(self):
        """测试车头虽在路中但挂车尾部甩出路肩引发擦碰"""
        self.game.cx = 8.0   # Cab inside road center
        self.game.tx = 14.5  # Trailer swung out onto curb
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_09_collision_with_parked_vehicle(self):
        """测试路面碰撞违停社会车辆事故"""
        car = self.game.obstacles[0]
        car["type"] = "car"
        car["x"] = 7.5
        car["y"] = self.game.cy
        car["alive"] = True

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_10_target_distance_fire_scene_clear(self):
        """测试顺利跨越城市街道赶抵火场通关得分"""
        self.game.distance = 99.8
        old_score = self.game.score
        old_level = self.game.level

        self.game.update(0.1, KEY_UP, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, old_score + 1000)

        # Transition to next level
        self.game.update(1.6, 0, 0)
        self.assertEqual(self.game.level, old_level + 1)
        self.assertEqual(self.game.state, STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
