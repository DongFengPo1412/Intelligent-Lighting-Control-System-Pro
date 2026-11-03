# -*- coding: utf-8 -*-
"""
test_arcade_133_kangaroo.py —— 街机游戏 #133 袋鼠妈妈大冒险 (Kangaroo 1982 / Sun Electronics & Atari) 单元测试
"""

import unittest
from arcade.game_133_kangaroo import (
    Game133Kangaroo,
    STATE_PLAYING,
    STATE_LEVEL_CLEAR,
    STATE_MOM_DOWN,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame133Kangaroo(unittest.TestCase):
    def setUp(self):
        self.game = Game133Kangaroo()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 133)
        self.assertEqual(self.game.name, "袋鼠妈妈大冒险")
        self.assertEqual(self.game.english_name, "Kangaroo")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(len(self.game.monkeys), 3)
        self.assertEqual(len(self.game.fruits), 4)

    def test_02_walking_and_facing(self):
        """测试袋鼠妈妈横向行走与朝向翻转"""
        self.assertEqual(self.game.p_facing, 1) # Facing Right
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.p_facing, -1)
        self.assertLess(self.game.px, 2.0)

    def test_03_jump_and_gravity(self):
        """测试按键B腾空起跳与重力下落踏上平台"""
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.pvy, 0.0)

    def test_04_ladder_climb(self):
        """测试在树梯处上下攀爬"""
        self.game.px = 12.0
        self.game.py = 13.0
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.on_ladder)
        self.assertLess(self.game.py, 13.0)

    def test_05_boxing_punch_monkeys(self):
        """测试按键A挥拳击倒顽猴获得200分"""
        self.game.px = 7.0
        self.game.py = 10.0
        self.game.p_facing = 1
        monkey = self.game.monkeys[0]
        monkey["x"] = 8.0
        monkey["y"] = 10.0
        monkey["alive"] = True

        old_score = self.game.score
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.punch_timer > 0.0)
        self.assertFalse(monkey["alive"])
        self.assertEqual(self.game.score, old_score + 200)

    def test_06_boxing_punch_apples(self):
        """测试拳击手套凌空击碎下落苹果截击获得100分"""
        self.game.monkeys[0]["alive"] = False # Ensure no monkey in punch area
        self.game.px = 7.0
        self.game.py = 10.0
        self.game.p_facing = 1
        self.game.apples[0]["active"] = True
        self.game.apples[0]["x"] = 8.0
        self.game.apples[0]["y"] = 10.0

        old_score = self.game.score
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.apples[0]["active"])
        self.assertEqual(self.game.score, old_score + 100)

    def test_07_fruit_collection(self):
        """测试触碰水果收集获得150分"""
        fruit = self.game.fruits[0]
        self.assertFalse(fruit["collected"])
        self.game.px = fruit["x"]
        self.game.py = fruit["y"]

        old_score = self.game.score
        self.game._check_collisions()
        self.assertTrue(fruit["collected"])
        self.assertEqual(self.game.score, old_score + 150)

    def test_08_bell_ring_respawns_fruit(self):
        """测试跳跃撞响吊钟刷新全树水果获得100分与收集奖励"""
        for f in self.game.fruits:
            f["collected"] = True

        self.game.px = 11.0
        self.game.py = 4.5
        self.game.is_jumping = True

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.bell_rung)
        # 100 pts for bell ring + 150 pts for adjacent respawned fruit
        self.assertEqual(self.game.score, old_score + 250)

    def test_09_joey_rescue_level_clear(self):
        """测试登顶树冠触碰小袋鼠完成营救通关"""
        self.game.px = 2.0
        self.game.py = 2.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_LEVEL_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.level, 2)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_10_game_over_and_restart(self):
        """测试袋鼠妈妈受创生命耗尽及按键重开"""
        self.game.lives = 1
        self.game.state = STATE_MOM_DOWN
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
