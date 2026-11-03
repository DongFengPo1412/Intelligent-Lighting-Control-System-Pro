# -*- coding: utf-8 -*-
"""
test_arcade_142_mariner.py —— 街机游戏 #142 深海潜航者 (Mariner 1981 / Amenip) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_142_mariner import (
    Game142Mariner,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SUB_CRASH,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame142Mariner(unittest.TestCase):
    def setUp(self):
        self.game = Game142Mariner()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 142)
        self.assertEqual(self.game.name, "深海潜航者")
        self.assertEqual(self.game.english_name, "Mariner")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.oxygen, 100.0)
        self.assertEqual(len(self.game.enemies), 3)
        self.assertEqual(len(self.game.bubbles), 2)
        self.assertEqual(len(self.game.treasures), 1)

    def test_02_submarine_buoyancy_navigation(self):
        """测试潜艇浮力平移与潜深控制"""
        self.assertEqual(self.game.px, 3.0)
        self.assertEqual(self.game.py, 7.0)

        # Move forward (right) and dive (down)
        self.game.update(0.1, KEY_RIGHT | KEY_DOWN, 0)
        self.assertGreater(self.game.px, 3.0)
        self.assertGreater(self.game.py, 7.0)

    def test_03_oxygen_drain_and_suffocation(self):
        """测试氧气消耗与耗尽窒息沉没"""
        self.assertEqual(self.game.oxygen, 100.0)
        self.game.update(0.1, 0, 0)
        self.assertLess(self.game.oxygen, 100.0)

        # Drain oxygen completely
        self.game.oxygen = 0.05
        old_lives = self.game.lives
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_SUB_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_04_fire_horizontal_torpedo(self):
        """测试按键A发射水平鱼雷击沉敌方潜艇"""
        sub = self.game.enemies[1]
        sub["x"] = 8.0
        sub["y"] = 7.0
        sub["alive"] = True

        self.game.px = 3.0
        self.game.py = 7.0
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.torpedoes), 1)

        old_score = self.game.score
        # Update until torpedo strikes sub
        for _ in range(10):
            self.game.update(0.05, 0, 0)
        self.assertFalse(sub["alive"])
        self.assertEqual(self.game.score, old_score + 150)

    def test_05_fire_vertical_missile_hits_destroyer(self):
        """测试按键B发射垂直防空导弹击毁水面驱逐舰"""
        destroyer = self.game.enemies[0]
        destroyer["x"] = 6.0
        destroyer["y"] = 1.0
        destroyer["alive"] = True

        self.game.px = 6.0
        self.game.py = 6.0
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(len(self.game.vertical_missiles), 1)

        old_score = self.game.score
        for _ in range(10):
            self.game.update(0.05, 0, 0)
        self.assertFalse(destroyer["alive"])
        self.assertEqual(self.game.score, old_score + 300)

    def test_06_intercept_falling_depth_charge(self):
        """测试垂直导弹拦截下沉深水炸弹"""
        self.game.depth_charges = [{"x": 5.0, "y": 4.0, "vy": 3.0, "active": True}]
        self.game.vertical_missiles = [{"x": 5.0, "y": 5.0, "active": True}]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(len(self.game.depth_charges), 0)
        self.assertEqual(self.game.score, old_score + 80)

    def test_07_seabed_coral_collision(self):
        """测试触碰海底礁石触发触底损毁"""
        self.game.px = 5.0
        seabed_y = self.game.seabed[5]
        self.game.py = seabed_y - 0.2

        old_lives = self.game.lives
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.state, STATE_SUB_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_08_collect_oxygen_bubble_refills_tank(self):
        """测试捕获地热喷泉氧气泡回补氧气储备"""
        self.game.oxygen = 40.0
        bubble = self.game.bubbles[0]
        bubble["x"] = 4.0
        bubble["y"] = 6.0
        bubble["alive"] = True

        self.game.px = 4.0
        self.game.py = 6.0

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.oxygen, 40.0)
        self.assertEqual(self.game.score, old_score + 50)

    def test_09_salvage_sunken_treasure(self):
        """测试打捞海底沉船黄金宝箱获得高分"""
        tr = self.game.treasures[0]
        tr["x"] = 8.0
        tr["y"] = 8.0
        tr["collected"] = False

        self.game.px = 8.0
        self.game.py = 8.0

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertTrue(tr["collected"])
        self.assertEqual(self.game.score, old_score + 500)

    def test_10_clear_all_enemies_stage_clear(self):
        """测试全歼海域水面与水下敌舰顺利通关"""
        for e in self.game.enemies:
            e["alive"] = False

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
