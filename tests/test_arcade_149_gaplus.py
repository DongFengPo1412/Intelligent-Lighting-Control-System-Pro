# -*- coding: utf-8 -*-
"""
test_arcade_149_gaplus.py —— 街机游戏 #149 逆转大蜜蜂 (Gaplus 1984 / Namco) 单元测试
验证元数据、全向深区机动、反向牵引光束抓捕俘获、多联装僚机齐射、僚机防空装甲护盾与清屏通关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_149_gaplus import (
    Game149Gaplus,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_HIT,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestGame149Gaplus(unittest.TestCase):
    def setUp(self):
        self.game = Game149Gaplus()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 149)
        self.assertIn("逆转大蜜蜂", self.game.name)
        self.assertEqual(self.game.english_name, "Gaplus")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.px, 7.5)
        self.assertEqual(self.game.py, 13.0)
        self.assertEqual(self.game.escorts_count, 0)
        self.assertFalse(self.game.beam_active)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 149)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["enemies_count"], 8)

    def test_02_omni_movement_bounds(self):
        # Move up into deep lower zone
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.py, 13.0)
        self.assertGreaterEqual(self.game.py, 8.5)

        # Move right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 7.5)
        self.assertLessEqual(self.game.px, 14.5)

    def test_03_tractor_beam_activation_with_key_b(self):
        self.assertFalse(self.game.beam_active)
        # Hold KEY_B to activate beam
        self.game.update(0.1, KEY_B, 0)
        self.assertTrue(self.game.beam_active)
        self.assertLess(self.game.beam_energy, 1.0)

        # Release KEY_B
        self.game.update(0.1, 0, KEY_B)
        self.assertFalse(self.game.beam_active)

    def test_04_capturing_diving_enemy_with_tractor_beam(self):
        # Position diving enemy directly in front of player
        target = self.game.enemies[0]
        target["state"] = "diving"
        target["x"] = 7.5
        target["y"] = 10.0
        self.game.px = 7.5
        self.game.py = 13.0

        # Activate beam with KEY_B
        self.game.update(0.016, KEY_B, 0)
        self.assertEqual(target["state"], "captured_suck")

    def test_05_docking_captured_enemy_increases_escort_count(self):
        target = self.game.enemies[0]
        target["state"] = "captured_suck"
        target["x"] = 7.5
        target["y"] = 12.0
        self.game.px = 7.5
        self.game.py = 13.0

        initial_score = self.game.score
        # Update until docked
        self.game.update(0.1, 0, 0)
        self.assertFalse(target["alive"])
        self.assertEqual(self.game.escorts_count, 1)
        self.assertEqual(self.game.score, initial_score + 500)

    def test_06_simultaneous_escort_fan_barrage_with_key_a(self):
        self.game.escorts_count = 2
        self.assertEqual(len(self.game.lasers), 0)

        # Press KEY_A to fire: 1 main + 2 escorts = 3 lasers!
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(len(self.game.lasers), 3)

    def test_07_laser_kills_enemy(self):
        target = self.game.enemies[0]
        target["x"] = 7.5
        target["y"] = 6.0
        target["alive"] = True

        self.game.lasers.append({"x": 7.5, "y": 6.2, "vy": -14.0})
        initial_score = self.game.score

        self.game.update(0.016, 0, 0)
        self.assertFalse(target["alive"])
        self.assertGreaterEqual(self.game.score, initial_score + 150)

    def test_08_escort_ablative_shield_absorbs_bullet(self):
        self.game.escorts_count = 2
        initial_lives = self.game.lives

        # Spawn bullet hitting player's wing
        self.game.enemy_bullets.append({"x": 9.3, "y": 13.0, "vy": 7.0})

        self.game.update(0.016, 0, 0)
        # Escort was sacrificed as armor shield
        self.assertEqual(self.game.escorts_count, 1)
        self.assertEqual(self.game.lives, initial_lives)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_09_direct_hit_without_escorts_damages_player(self):
        self.game.escorts_count = 0
        initial_lives = self.game.lives

        self.game.enemy_bullets.append({"x": 7.5, "y": 13.0, "vy": 7.0})
        self.game.update(0.016, 0, 0)

        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)

    def test_10_wave_clear_and_rendering(self):
        for e in self.game.enemies:
            e["alive"] = False

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1500)

        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()

