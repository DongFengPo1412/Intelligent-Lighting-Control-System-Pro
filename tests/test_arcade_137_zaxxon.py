# -*- coding: utf-8 -*-
"""
test_arcade_137_zaxxon.py —— 街机游戏 #137 扎克松立体战机 (Zaxxon 1982 / Sega) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_137_zaxxon import (
    Game137Zaxxon,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_CRASH,
    STATE_GAME_OVER,
    MAX_ALTITUDE,
    MIN_ALTITUDE,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame137Zaxxon(unittest.TestCase):
    def setUp(self):
        self.game = Game137Zaxxon()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 137)
        self.assertEqual(self.game.name, "扎克松立体战机")
        self.assertEqual(self.game.english_name, "Zaxxon")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.fuel, 100.0)
        self.assertEqual(self.game.pz, 2.0)
        self.assertEqual(len(self.game.walls), 3)
        self.assertEqual(len(self.game.targets), 5)

    def test_02_altitude_climb_and_dive(self):
        """测试按键UP拉升海拔与按键DOWN俯冲潜低"""
        self.assertEqual(self.game.pz, 2.0)
        # Pull stick up (climb)
        self.game.update(0.1, KEY_UP, 0)
        self.assertGreater(self.game.pz, 2.0)

        # Dive down
        for _ in range(20):
            self.game.update(0.1, KEY_DOWN, 0)
        self.assertEqual(self.game.pz, MIN_ALTITUDE)

    def test_03_lateral_steering_and_clamp(self):
        """测试横向左右机动与边界约束"""
        self.assertEqual(self.game.px, 7.5)
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.px, 7.5)

        for _ in range(30):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.px, 13.5)

    def test_04_fuel_consumption_and_flameout(self):
        """测试燃油衰减与燃料耗尽坠毁"""
        self.assertEqual(self.game.fuel, 100.0)
        self.game.update(0.1, 0, 0)
        self.assertLess(self.game.fuel, 100.0)

        # Drain fuel
        self.game.fuel = 0.05
        old_lives = self.game.lives
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_SHIP_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_05_fire_blaster_at_altitude(self):
        """测试按键A发射激光炮与当前飞行海拔绑定"""
        self.game.pz = 3.2
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertEqual(self.game.bullets[0]["z"], 3.2)

    def test_06_low_altitude_fuel_tank_bombing(self):
        """测试超低空轰炸地面燃油罐回补燃料并得分"""
        target = self.game.targets[0]
        target["type"] = "fuel"
        target["x"] = 7.5
        target["y"] = 8.0
        self.game.fuel = 40.0

        # Bullet at low altitude z = 0.8
        self.game.bullets = [{
            "x": 7.5, "y": 8.5, "z": 0.8, "active": True
        }]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(target["alive"])
        self.assertGreater(self.game.fuel, 40.0)
        self.assertEqual(self.game.score, old_score + 150)

    def test_07_high_altitude_misses_ground_targets(self):
        """测试高空激光无法命中地面目标"""
        target = self.game.targets[0]
        target["x"] = 7.5
        target["y"] = 8.0
        target["alive"] = True

        # Bullet at high altitude z = 3.5
        self.game.bullets = [{
            "x": 7.5, "y": 8.5, "z": 3.5, "active": True
        }]

        self.game.update(0.05, 0, 0)
        self.assertTrue(target["alive"])

    def test_08_wall_altitude_gap_mismatch_crash(self):
        """测试穿越要塞城墙时海拔与开口不匹配撞墙坠毁"""
        wall = self.game.walls[0]
        wall["y"] = self.game.py - 0.2
        wall["gate_z"] = 3.0
        self.game.pz = 1.0  # Mismatch (gate is at 3.0)

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_SHIP_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_09_wall_altitude_gap_match_clear(self):
        """测试海拔高度精确契合城墙孔隙顺利穿梭得加分"""
        wall = self.game.walls[0]
        wall["y"] = self.game.py - 0.2
        wall["gate_z"] = 2.0
        self.game.pz = 2.0  # Exact match!

        old_score = self.game.score
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertTrue(wall["cleared"])
        self.assertEqual(self.game.lives, old_lives)
        self.assertEqual(self.game.score, old_score + 100)

    def test_10_boss_zaxxon_missile_and_destruction(self):
        """测试决战扎克松机甲BOSS命中弱点并通关"""
        self.game.distance_traveled = 36.0
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.boss_active)

        self.game.boss_hp = 1
        self.game.boss_y = 3.0
        # Bullet matching boss position and altitude
        self.game.bullets = [{
            "x": 7.5, "y": 3.5, "z": 2.0, "active": True
        }]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.boss_hp, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 300 + 1000)


if __name__ == "__main__":
    unittest.main()
