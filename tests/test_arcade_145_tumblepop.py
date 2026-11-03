# -*- coding: utf-8 -*-
"""
test_arcade_145_tumblepop.py —— 街机游戏 #145 吸尘器大冒险 (Tumblepop 1991 / Data East) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_145_tumblepop import (
    Game145Tumblepop,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_DOWN,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame145Tumblepop(unittest.TestCase):
    def setUp(self):
        self.game = Game145Tumblepop()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 145)
        self.assertEqual(self.game.name, "吸尘器大冒险")
        self.assertEqual(self.game.english_name, "Tumblepop")
        self.assertEqual(self.game.release_year, 1991)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.monsters_in_pack, 0)
        self.assertEqual(self.game.facing, 1)
        self.assertEqual(len(self.game.enemies), 4)

    def test_02_platform_movement_and_facing(self):
        """测试水平行走与朝向翻转"""
        self.assertEqual(self.game.facing, 1)
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 2.0)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.facing, -1)

    def test_03_jump_and_platform_landing(self):
        """测试按键UP跳跃与重力回落平台"""
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.pvy, 0.0)

    def test_04_vacuum_suction_activation(self):
        """测试按键A启动吸尘器产生风暴吸力"""
        self.assertFalse(self.game.is_vacuuming)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.is_vacuuming)

    def test_05_vacuum_sucks_and_packs_monster(self):
        """测试吸尘器吸入怪物并将其收纳打包入背包"""
        enemy = self.game.enemies[0]
        self.game.px = 2.0
        self.game.py = 14.0
        self.game.facing = 1  # Facing right

        enemy["x"] = 4.0
        enemy["y"] = 14.0
        enemy["alive"] = True

        self.assertEqual(self.game.monsters_in_pack, 0)
        old_score = self.game.score

        # Hold suction until monster enters pack
        for _ in range(10):
            self.game.update(0.05, KEY_A, 0)

        self.assertFalse(enemy["alive"])
        self.assertEqual(self.game.monsters_in_pack, 1)
        self.assertEqual(self.game.score, old_score + 100)

    def test_06_eject_monster_bowling_ball(self):
        """测试按键B将背包怪物以巨型肉球形式喷射发射"""
        self.game.monsters_in_pack = 2
        self.assertIsNone(self.game.rolling_ball)

        # Press B to launch ball
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.monsters_in_pack, 0)
        self.assertIsNotNone(self.game.rolling_ball)
        self.assertTrue(self.game.rolling_ball["active"])
        self.assertEqual(self.game.rolling_ball["power"], 2)

    def test_07_rolling_ball_wall_ricochet(self):
        """测试滚动怪兽肉球撞击边缘墙壁反弹"""
        self.game.rolling_ball = {
            "x": 14.0,
            "y": 14.0,
            "vx": 12.0,
            "bounces": 4,
            "power": 1,
            "active": True,
        }

        self.game.update(0.1, 0, 0)
        # Should have bounced off right wall (vx became negative)
        self.assertLess(self.game.rolling_ball["vx"], 0.0)
        self.assertEqual(self.game.rolling_ball["bounces"], 3)

    def test_08_bowling_strike_crushes_enemies(self):
        """测试滚动肉球如保龄球般碾碎沿途怪物获得加分"""
        enemy = self.game.enemies[1]
        enemy["x"] = 8.0
        enemy["y"] = 10.0
        enemy["alive"] = True

        self.game.rolling_ball = {
            "x": 7.5,
            "y": 10.0,
            "vx": 12.0,
            "bounces": 4,
            "power": 1,
            "active": True,
        }

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(enemy["alive"])
        self.assertEqual(self.game.score, old_score + 250)

    def test_09_enemy_collision_causes_death(self):
        """测试未开启吸尘器时触碰怪物丧失生命"""
        self.game.px = 6.0
        self.game.py = 14.0
        self.game.is_vacuuming = False

        enemy = self.game.enemies[0]
        enemy["x"] = 6.0
        enemy["y"] = 14.0
        enemy["being_sucked"] = False

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DOWN)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_10_clear_all_enemies_stage_clear(self):
        """测试全屏怪物全灭通关进入下一关"""
        for e in self.game.enemies:
            e["alive"] = False
        self.game.monsters_in_pack = 0
        self.game.rolling_ball = None

        old_score = self.game.score
        old_level = self.game.level
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 1000)

        # Transition to next stage
        self.game.update(1.6, 0, 0)
        self.assertEqual(self.game.level, old_level + 1)
        self.assertEqual(self.game.state, STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
