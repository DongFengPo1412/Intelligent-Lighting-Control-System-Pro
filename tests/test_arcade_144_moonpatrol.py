# -*- coding: utf-8 -*-
"""
test_arcade_144_moonpatrol.py —— 街机游戏 #144 月球巡逻车 (Moon Patrol 1982 / Irem & Williams) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_144_moonpatrol import (
    Game144MoonPatrol,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_BUGGY_CRASH,
    STATE_GAME_OVER,
    GROUND_Y,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame144MoonPatrol(unittest.TestCase):
    def setUp(self):
        self.game = Game144MoonPatrol()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 144)
        self.assertEqual(self.game.name, "月球巡逻车")
        self.assertEqual(self.game.english_name, "Moon Patrol")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.by, GROUND_Y)
        self.assertEqual(self.game.checkpoint_letter, 'A')
        self.assertEqual(len(self.game.ground_hazards), 6)
        self.assertEqual(len(self.game.ufos), 2)

    def test_02_speed_control_and_progression(self):
        """测试月面巡逻车加减速与里程推进"""
        old_speed = self.game.speed
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.speed, old_speed)
        self.assertGreater(self.game.distance, 0.0)
        self.assertGreater(self.game.score, 0)

        # Decelerate
        self.game.update(0.2, KEY_LEFT, 0)
        self.assertLess(self.game.speed, 9.0)

    def test_03_hydraulic_suspension_jump(self):
        """测试按键B液压跳跃腾空与重力落地"""
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.by, GROUND_Y)

        # Wait for landing
        for _ in range(25):
            self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.is_jumping)
        self.assertEqual(self.game.by, GROUND_Y)

    def test_04_dual_simultaneous_fire(self):
        """测试按键A前向激光与垂直防空导弹同时齐射"""
        self.assertEqual(len(self.game.forward_lasers), 0)
        self.assertEqual(len(self.game.upward_missiles), 0)

        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.forward_lasers), 1)
        self.assertEqual(len(self.game.upward_missiles), 1)

    def test_05_forward_laser_destroys_boulder(self):
        """测试前向激光粉碎月面岩石障碍并得分"""
        boulder = self.game.ground_hazards[1]  # boulder at x=30.0
        self.game.distance = 25.0
        # Boulder is now at hx = 30.0 - 25.0 = 5.0

        self.game.forward_lasers = [{"x": 4.8, "y": GROUND_Y - 0.2, "active": True}]
        old_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertFalse(boulder["alive"])
        self.assertEqual(self.game.score, old_score + 100)

    def test_06_upward_missile_destroys_ufo(self):
        """测试垂直导弹拦截摧毁空中小灰人飞碟"""
        ufo = self.game.ufos[0]
        ufo["x"] = 8.0
        ufo["y"] = 3.0
        ufo["alive"] = True

        self.game.upward_missiles = [{"x": 8.0, "y": 3.5, "active": True}]
        old_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertFalse(ufo["alive"])
        self.assertEqual(self.game.score, old_score + 200)

    def test_07_fall_into_crater_crash(self):
        """测试未起跳直接驶入陨石坑撞毁"""
        crater = self.game.ground_hazards[0]  # crater at x=18.0
        self.game.distance = 18.0 - self.game.bx
        self.game.is_jumping = False

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_BUGGY_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_08_jump_safely_over_crater(self):
        """测试跳跃腾空状态安全掠过陨石坑"""
        crater = self.game.ground_hazards[0]
        self.game.distance = 18.0 - self.game.bx
        self.game.is_jumping = True
        self.game.by = GROUND_Y - 3.0  # High in the air!

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, old_lives)

    def test_09_ufo_bomb_hits_buggy(self):
        """测试被空投飞碟炸弹命中损毁"""
        self.game.ufo_bombs = [{"x": self.game.bx, "y": self.game.by, "vy": 5.0, "active": True}]
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_BUGGY_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_10_target_distance_stage_clear(self):
        """测试完成月面赛道全程抵达终点通关"""
        self.game.distance = 119.8
        old_score = self.game.score
        old_level = self.game.level

        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, old_score + 1000)

        # Transition to next stage
        self.game.update(1.6, 0, 0)
        self.assertEqual(self.game.level, old_level + 1)
        self.assertEqual(self.game.state, STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
