# -*- coding: utf-8 -*-
"""
test_arcade_135_pleiads.py —— 街机游戏 #135 疯狂小蜜蜂 (Pleiads 1981 / Tehkan) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_135_pleiads import (
    Game135Pleiads,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_HIT,
    STATE_GAME_OVER,
    PHASE_RADAR,
    PHASE_BIRDS,
    PHASE_LANDING,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame135Pleiads(unittest.TestCase):
    def setUp(self):
        self.game = Game135Pleiads()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 135)
        self.assertEqual(self.game.name, "疯狂小蜜蜂")
        self.assertEqual(self.game.english_name, "Pleiads")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.phase, PHASE_RADAR)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.shields_left, 3)
        self.assertEqual(len(self.game.enemies), 4)
        self.assertEqual(len(self.game.radar_barriers), 4)

    def test_02_horizontal_flight_and_clamping(self):
        """测试战机横向平移与边框阻挡"""
        self.assertEqual(self.game.px, 7.5)
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.px, 7.5)

        # Move far right
        for _ in range(30):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.px, 14.0)

    def test_03_shield_activation(self):
        """测试按键B展开能量护盾与持续时间消耗"""
        self.assertFalse(self.game.shield_active)
        self.assertEqual(self.game.shields_left, 3)

        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.shield_active)
        self.assertEqual(self.game.shields_left, 2)
        self.assertGreater(self.game.shield_timer, 0.0)

        # Wait for shield expiration
        self.game.update(1.6, 0, 0)
        self.assertFalse(self.game.shield_active)

    def test_04_laser_cannon_firing(self):
        """测试按键A发射激光炮弹与双发上限"""
        self.assertEqual(len(self.game.bullets), 0)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)

        # Fire second shot
        self.game.update(0.05, 0, KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 2)

    def test_05_phase0_radar_barrier_destructibility(self):
        """测试第一阶段雷达屏障阻挡炮弹并发生损耗"""
        barrier = self.game.radar_barriers[0]
        barrier["x"] = 5.0
        barrier["y"] = 9.0
        barrier["hp"] = 2

        # Spawn bullet on collision course
        self.game.bullets = [{"x": 5.0, "y": 9.5, "active": True}]
        self.game.update(0.05, 0, 0)

        self.assertEqual(barrier["hp"], 1)
        self.assertEqual(len(self.game.bullets), 0)

    def test_06_phase0_clear_advances_to_phase1(self):
        """测试歼灭第一阶段异星雷达站推进至第二阶段飞鸟战"""
        for e in self.game.enemies:
            e["alive"] = False

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.phase, PHASE_BIRDS)
        self.assertEqual(self.game.score, old_score + 300)
        self.assertEqual(len(self.game.enemies), 4)

    def test_07_phase1_birds_swoop_and_kill(self):
        """测试第二阶段飞鸟俯冲与击杀"""
        self.game._init_phase_1()
        bird = self.game.enemies[0]
        bird["x"] = 7.5
        bird["y"] = 6.0

        # Fire bullet hitting bird
        self.game.bullets = [{"x": 7.5, "y": 6.5, "active": True}]
        old_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertFalse(bird["alive"])
        self.assertEqual(self.game.score, old_score + 100)

    def test_08_phase1_clear_advances_to_mothership(self):
        """测试第二阶段飞鸟全灭后切入第三阶段母舰战"""
        self.game._init_phase_1()
        for e in self.game.enemies:
            e["alive"] = False

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.phase, PHASE_LANDING)
        self.assertEqual(self.game.score, old_score + 400)
        self.assertFalse(self.game.mothership_destroyed)

    def test_09_destroy_mothership_core(self):
        """测试第三阶段摧毁母舰核心解锁航母降落跑道"""
        self.game._init_phase_2()
        self.game.mothership_x = 7.5
        self.game.mothership_hp = 1

        # Hit core with bullet
        self.game.bullets = [{"x": 7.5, "y": 3.2, "active": True}]
        old_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.mothership_destroyed)
        self.assertEqual(self.game.score, old_score + 600)

    def test_10_safe_runway_landing_and_clear(self):
        """测试母舰摧毁后战机在跑道航标间安全着陆通关"""
        self.game._init_phase_2()
        self.game.mothership_destroyed = True
        self.game.px = 7.5
        self.game.py = 2.4

        old_score = self.game.score
        # Ascend into touchdown zone
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 500)


if __name__ == "__main__":
    unittest.main()

