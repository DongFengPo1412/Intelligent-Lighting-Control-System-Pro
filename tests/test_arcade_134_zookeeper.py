# -*- coding: utf-8 -*-
"""
test_arcade_134_zookeeper.py —— 街机游戏 #134 动物园管理员 (Zoo Keeper 1982 / Taito) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_134_zookeeper import (
    Game134ZooKeeper,
    STATE_PLAYING,
    STATE_LEVEL_CLEAR,
    STATE_CAUGHT,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame134ZooKeeper(unittest.TestCase):
    def setUp(self):
        self.game = Game134ZooKeeper()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 134)
        self.assertEqual(self.game.name, "动物园管理员")
        self.assertEqual(self.game.english_name, "Zoo Keeper")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(len(self.game.animals), 4)
        # Check initial wall presence at border
        self.assertTrue(self.game.walls[2][2])
        self.assertTrue(self.game.walls[13][13])

    def test_02_track_movement(self):
        """测试管理员外环巡逻移动"""
        self.assertEqual(self.game.track_pos, 0.0)
        self.assertEqual(self.game.px, 1.0)
        self.assertEqual(self.game.py, 1.0)
        # Move right on top ledge (clockwise)
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.track_pos, 0.0)
        self.assertGreater(self.game.px, 1.0)
        self.assertEqual(self.game.py, 1.0)

    def test_03_jump_over_obstacles(self):
        """测试按键B腾空起跳与跳跃计时"""
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertGreater(self.game.jump_timer, 0.0)

        # Update until jump expires
        self.game.update(0.6, 0, 0)
        self.assertFalse(self.game.is_jumping)
        self.assertEqual(self.game.jump_timer, 0.0)

    def test_04_repair_breached_wall(self):
        """测试按键A修补损坏砖墙并获得得分"""
        # Damage wall at (5, 2)
        self.game.walls[2][5] = False
        # Move Zeke to top track at x=5, y=1 (pos = 4.0)
        self.game.track_pos = 4.0
        self.game.px = 5.0
        self.game.py = 1.0

        old_score = self.game.score
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.walls[2][5])
        self.assertEqual(self.game.score, old_score + 15)

    def test_05_animal_wall_chipping_inside_cage(self):
        """测试猛兽撞击围墙产生破坏剥落"""
        animal = self.game.animals[0]
        animal["x"] = 6.0
        animal["y"] = 2.6
        animal["vy"] = -5.0  # Moving towards top wall
        self.game.walls[2][6] = True

        self.game.update(0.05, 0, 0)
        # Wall at (6, 2) should be destroyed and animal vy reversed
        self.assertFalse(self.game.walls[2][6])
        self.assertGreater(animal["vy"], 0.0)

    def test_06_animal_escape_through_gap(self):
        """测试猛兽从破坏缺口出逃到外环跑道"""
        animal = self.game.animals[0]
        animal["x"] = 6.0
        animal["y"] = 2.5
        animal["vy"] = -5.0
        self.game.walls[2][6] = False  # Gap already open

        self.game.update(0.05, 0, 0)
        self.assertTrue(animal["escaped"])

    def test_07_caught_by_escaped_animal(self):
        """测试未起跳时被出逃猛兽捕获扣除生命"""
        self.game.track_pos = 10.0
        self.game.px, self.game.py = self.game._track_pos_to_xy(10.0)
        self.game.is_jumping = False

        animal = self.game.animals[0]
        animal["escaped"] = True
        animal["track_pos"] = 10.0
        animal["x"], animal["y"] = self.game.px, self.game.py

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, old_lives - 1)
        self.assertEqual(self.game.state, STATE_CAUGHT)

    def test_08_jump_over_escaped_animal(self):
        """测试起跳状态下安全跨越猛兽获得额外避险加分"""
        self.game.track_pos = 10.0
        self.game.px, self.game.py = self.game._track_pos_to_xy(10.0)
        self.game.is_jumping = True
        self.game.jump_timer = 0.3

        animal = self.game.animals[0]
        animal["escaped"] = True
        animal["track_pos"] = 10.0
        animal["x"], animal["y"] = self.game.px, self.game.py

        old_score = self.game.score
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, old_lives)
        self.assertEqual(self.game.score, old_score + 50)

    def test_09_net_powerup_captures_animal(self):
        """测试拾取捕兽网后捕获猛兽回笼并获取奖励分"""
        # Collect net
        self.game.net_spawned = True
        self.game.net_pos = 10.0
        self.game.track_pos = 10.0
        self.game.px, self.game.py = self.game._track_pos_to_xy(10.0)

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.net_spawned)
        self.assertGreater(self.game.net_timer, 0.0)

        # Capture escaped animal
        animal = self.game.animals[0]
        animal["escaped"] = True
        animal["track_pos"] = 10.0
        animal["x"], animal["y"] = self.game.px, self.game.py

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(animal["escaped"])
        self.assertEqual(self.game.score, old_score + 250)

    def test_10_time_limit_level_clear(self):
        """测试坚守至防守时限耗尽通关升级"""
        self.game.time_left = 0.05
        old_level = self.game.level
        old_score = self.game.score

        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_LEVEL_CLEAR)
        self.assertEqual(self.game.score, old_score + 1000)

        # Transition to next level after timer
        self.game.update(1.6, 0, 0)
        self.assertEqual(self.game.level, old_level + 1)
        self.assertEqual(self.game.state, STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
