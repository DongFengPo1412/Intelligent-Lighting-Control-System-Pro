# -*- coding: utf-8 -*-
"""
test_arcade_136_vanguard.py —— 街机游戏 #136 宇宙巡航拦截者 (Vanguard 1981 / TOSE & SNK) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_136_vanguard import (
    Game136Vanguard,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_CRASH,
    STATE_GAME_OVER,
    ZONE_MOUNTAIN,
    ZONE_STRIPE,
    ZONE_GOND,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame136Vanguard(unittest.TestCase):
    def setUp(self):
        self.game = Game136Vanguard()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 136)
        self.assertEqual(self.game.name, "宇宙巡航拦截者")
        self.assertEqual(self.game.english_name, "Vanguard")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.zone, ZONE_MOUNTAIN)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.fuel, 100.0)
        self.assertEqual(len(self.game.enemies), 3)
        self.assertIsNotNone(self.game.energy_pod)

    def test_02_fuel_drain_and_depletion(self):
        """测试燃油持续消耗与耗尽坠机"""
        self.assertEqual(self.game.fuel, 100.0)
        self.game.update(0.1, 0, 0)
        self.assertLess(self.game.fuel, 100.0)

        # Deplete fuel completely
        self.game.fuel = 0.05
        old_lives = self.game.lives
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_SHIP_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_03_tunnel_navigation_and_heading(self):
        """测试隧道中平移与航向矢量动态变化"""
        self.assertEqual(self.game.p_heading, (1.0, 0.0))
        # Steer Up
        self.game.update(0.1, KEY_UP, 0)
        self.assertEqual(self.game.p_heading, (0.0, -1.0))
        self.assertLess(self.game.py, 7.5)

    def test_04_cavern_wall_crash(self):
        """测试撞击山洞上下石壁坠机"""
        self.game.px = 5.0
        # Ceiling at x=5 is top_walls[5]
        top_y = self.game.top_walls[5]
        self.game.py = top_y + 0.1

        old_lives = self.game.lives
        # Fly upward into ceiling
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.state, STATE_SHIP_CRASH)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_05_forward_and_reverse_laser_fire(self):
        """测试按键A前向激光与按键B反向拦截炮"""
        self.game.p_heading = (1.0, 0.0)  # Facing Right
        # Fire forward (Key A)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertGreater(self.game.bullets[0]["vx"], 0.0)

        # Fire reverse (Key B)
        self.game.update(0.05, 0, KEY_A)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(len(self.game.bullets), 2)
        self.assertLess(self.game.bullets[1]["vx"], 0.0)

    def test_06_laser_kills_enemy_and_refuels(self):
        """测试主炮击毁敌机并获得燃油补给与得分"""
        enemy = self.game.enemies[0]
        enemy["x"] = 8.0
        enemy["y"] = 6.0
        self.game.fuel = 50.0

        # Bullet hitting enemy
        self.game.bullets = [{
            "x": 8.0, "y": 6.0, "vx": 15.0, "vy": 0.0, "active": True
        }]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(enemy["alive"])
        self.assertEqual(self.game.score, old_score + 100)
        self.assertGreater(self.game.fuel, 50.0)

    def test_07_energy_pod_pickup_and_invulnerability(self):
        """测试拾取能量荚舱启动无敌彩虹冲撞与回满燃油"""
        self.game.energy_pod = {"x": 5.0, "y": 6.0, "collected": False}
        self.game.px = 5.0
        self.game.py = 6.0
        self.game.fuel = 20.0

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.energy_pod["collected"])
        self.assertGreater(self.game.invulnerable_timer, 0.0)
        self.assertEqual(self.game.fuel, 100.0)
        self.assertEqual(self.game.score, old_score + 200)

    def test_08_ramming_enemies_while_invulnerable(self):
        """测试无敌状态下直接冲撞歼灭敌机获得加分"""
        self.game.invulnerable_timer = 4.0
        enemy = self.game.enemies[0]
        enemy["x"] = 6.0
        enemy["y"] = 6.0
        self.game.px = 6.0
        self.game.py = 6.0

        old_score = self.game.score
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertFalse(enemy["alive"])
        self.assertEqual(self.game.lives, old_lives)
        self.assertEqual(self.game.score, old_score + 200)

    def test_09_zone_advancement_from_mountain_to_stripe(self):
        """测试山洞区域全歼敌机后切入竖井区域"""
        for e in self.game.enemies:
            e["alive"] = False

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.zone, ZONE_STRIPE)
        self.assertEqual(self.game.score, old_score + 300)
        self.assertEqual(len(self.game.enemies), 3)

    def test_10_gond_boss_eye_shot_and_stage_clear(self):
        """测试贡德核心之眼穿透旋转护盾被击破通关"""
        self.game._init_zone_gond()
        self.game.gond_hp = 1
        # Set shield angle such that the open window is aligned (e.g. angle = 1.5)
        self.game.gond_shield_angle = 1.5

        # Bullet hitting eye at (7.5, 3.5)
        self.game.bullets = [{
            "x": 7.5, "y": 3.5, "vx": 0.0, "vy": -15.0, "active": True
        }]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.gond_hp, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 300 + 1000)


if __name__ == "__main__":
    unittest.main()

