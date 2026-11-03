# -*- coding: utf-8 -*-
"""
test_arcade_131_solarfox.py —— 街机游戏 #131 太阳能战机 (Solar Fox 1981 / Bally Midway) 单元测试
"""

import unittest
from arcade.game_131_solarfox import (
    Game131SolarFox,
    STATE_FLYING,
    STATE_SHIP_EXPLODING,
    STATE_QUADRANT_CLEAR,
    STATE_GAME_OVER,
    ARENA_MIN,
    ARENA_MAX,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame131SolarFox(unittest.TestCase):
    def setUp(self):
        self.game = Game131SolarFox()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 131)
        self.assertEqual(self.game.name, "太阳能战机")
        self.assertEqual(self.game.english_name, "Solar Fox")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.quadrant, 1)
        self.assertGreater(self.game.remaining_cells, 0)
        self.assertEqual(len(self.game.sentinels), 4)

    def test_02_continuous_flight_and_steering(self):
        """测试战机恒定高速巡航与正交航向转向"""
        init_py = self.game.py
        # Ship starts heading UP
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.py, init_py)

        # Steer RIGHT
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.dir_x, 1)
        self.assertEqual(self.game.dir_y, 0)

    def test_03_hyperspeed_activation(self):
        """测试按键A激活超频极速巡航推进"""
        self.assertFalse(self.game.is_hyperspeed)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.is_hyperspeed)

    def test_04_deflector_shield_activation(self):
        """测试按键B激活偏折护盾与冷却机制"""
        self.assertEqual(self.game.shield_timer, 0.0)
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.shield_timer, 0.0)
        self.assertGreater(self.game.shield_cooldown, 0.0)

    def test_05_cell_harvesting_and_scoring(self):
        """测试掠过太阳能晶胞收割消除与双倍超频积分"""
        # Place ship at cell (4, 4) in screen coords -> matrix index (1, 1)
        self.game.cells[1][1] = True
        self.game.px = 4.0
        self.game.py = 4.0

        old_cells = self.game.remaining_cells
        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(self.game.cells[1][1])
        self.assertEqual(self.game.remaining_cells, old_cells - 1)
        self.assertEqual(self.game.score, old_score + 20)

    def test_06_perimeter_sentinels_patrol(self):
        """测试外围四向哨兵沿墙壁连续滑行巡逻"""
        s0_pos = self.game.sentinels[0]["pos"]
        self.game.update(0.05, 0, 0)
        self.assertNotEqual(self.game.sentinels[0]["pos"], s0_pos)

    def test_07_fireball_hits_shield_deflects(self):
        """测试开启偏折护盾弹开外围狙击火球获得50分"""
        self.game.shield_timer = 0.5
        self.game.fireballs[0]["active"] = True
        self.game.fireballs[0]["x"] = self.game.px
        self.game.fireballs[0]["y"] = self.game.py

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(self.game.fireballs[0]["active"])
        self.assertEqual(self.game.score, old_score + 50)
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_08_fireball_hits_unshielded_player(self):
        """测试无护盾状态下被火球击中导致战机解体"""
        self.game.shield_timer = 0.0
        self.game.fireballs[0]["active"] = True
        self.game.fireballs[0]["x"] = self.game.px
        self.game.fireballs[0]["y"] = self.game.py

        self.game._check_collisions()
        self.assertEqual(self.game.state, STATE_SHIP_EXPLODING)

    def test_09_quadrant_clear_transition(self):
        """测试收割清空全区晶胞跃迁下一象限"""
        self.game.remaining_cells = 0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_QUADRANT_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.quadrant, 2)
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_10_game_over_and_restart(self):
        """测试战机耗尽游戏结束及按键重新投币复活"""
        self.game.lives = 1
        self.game.state = STATE_SHIP_EXPLODING
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
