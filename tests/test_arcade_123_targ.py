# -*- coding: utf-8 -*-
"""
test_arcade_123_targ.py —— 街机游戏 #123 碰碰激光车 (Targ 1980 / Exidy) 单元测试
"""

import unittest
from arcade.game_123_targ import (
    Game123Targ,
    STATE_PLAYING,
    STATE_DYING,
    STATE_SECTOR_CLEAR,
    STATE_GAME_OVER,
    GRID_MIN,
    GRID_MAX,
    STREETS,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame123Targ(unittest.TestCase):
    def setUp(self):
        self.game = Game123Targ()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 123)
        self.assertEqual(self.game.name, "碰碰激光车")
        self.assertEqual(self.game.english_name, "Targ")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.sector, 1)
        self.assertEqual(self.game.enemies_remaining, 10)
        self.assertFalse(self.game.laser["active"])

    def test_02_grid_movement_and_bounds(self):
        """测试沿街道移动与网格边界限制"""
        self.game.px = 7.5
        self.game.py = 2.0
        self.game.p_dir_x = 0
        self.game.p_dir_y = -1
        # Move up towards top border
        for _ in range(5):
            self.game.update(0.05, KEY_UP, KEY_UP)
        self.assertGreaterEqual(self.game.py, GRID_MIN)

    def test_03_turning_at_intersections(self):
        """测试在街道十字路口执行90度转向"""
        self.game.px = 7.5
        self.game.py = 7.5
        self.game.p_dir_x = 0
        self.game.p_dir_y = -1
        # Try turning right
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.p_dir_x, 1)
        self.assertEqual(self.game.p_dir_y, 0)

    def test_04_laser_firing_and_range(self):
        """测试按键A发射激光炮并在出界后消亡"""
        self.game.px = 7.5
        self.game.py = 7.5
        self.game.p_dir_x = 0
        self.game.p_dir_y = -1
        # Fire laser
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.laser["active"])
        self.assertEqual(self.game.laser["dir_y"], -1)

        # Update until laser leaves boundary
        for _ in range(10):
            self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.laser["active"])

    def test_05_turbo_boost_activation(self):
        """测试按键B触发紧急氮气加速冲刺与冷却机制"""
        self.assertEqual(self.game.turbo_timer, 0.0)
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.turbo_timer, 0.0)
        self.assertGreater(self.game.turbo_cooldown, 0.0)

    def test_06_laser_hit_regular_enemy(self):
        """测试激光命中击毁走私敌车获得100分"""
        self.game.laser["active"] = True
        self.game.laser["x"] = 7.5
        self.game.laser["y"] = 6.0
        self.game.laser["dir_x"] = 0
        self.game.laser["dir_y"] = -1

        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["is_spectar"] = False
        enemy["x"] = 7.5
        enemy["y"] = 6.2

        self.game._check_collisions()
        self.assertFalse(enemy["active"])
        self.assertFalse(self.game.laser["active"])
        self.assertEqual(self.game.score, 100)
        self.assertEqual(self.game.enemies_remaining, 9)

    def test_07_laser_hit_spectar_boss(self):
        """测试激光击毁变身黄色Spectar领航战车获得500分"""
        self.game.laser["active"] = True
        self.game.laser["x"] = 4.5
        self.game.laser["y"] = 4.5
        self.game.laser["dir_x"] = 1
        self.game.laser["dir_y"] = 0

        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["is_spectar"] = True
        enemy["x"] = 4.5
        enemy["y"] = 4.5

        self.game._check_collisions()
        self.assertFalse(enemy["active"])
        self.assertEqual(self.game.score, 500)

    def test_08_player_enemy_collision(self):
        """测试敌车碰撞导致自机战损"""
        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["x"] = self.game.px
        enemy["y"] = self.game.py

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DYING)

    def test_09_sector_clear_transition(self):
        """测试清除全区走私敌车通关晋级下个街区"""
        self.game.enemies_remaining = 0
        for e in self.game.enemies:
            e["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_SECTOR_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.sector, 2)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_10_game_over_and_restart(self):
        """测试生命耗尽游戏结束与按键重新投币复活"""
        self.game.lives = 1
        self.game.state = STATE_DYING
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
