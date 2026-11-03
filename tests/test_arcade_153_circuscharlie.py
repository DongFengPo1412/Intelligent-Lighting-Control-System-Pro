# -*- coding: utf-8 -*-
"""
test_arcade_153_circuscharlie.py —— 街机游戏 #153 马戏团 (Circus Charlie 1984 / Konami) 单元测试
验证元数据、驯狮奔腾控速勒缰进退、跃过火盆烈焰、移动火圈中心穿心、叼取金币钱袋与登顶领奖台过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_153_circuscharlie import (
    Game153CircusCharlie,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_CHARLIE_DOWN,
    STATE_GAME_OVER,
    GROUND_Y,
    COURSE_LENGTH,
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


class TestGame153CircusCharlie(unittest.TestCase):
    def setUp(self):
        self.game = Game153CircusCharlie()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 153)
        self.assertIn("马戏团", self.game.name)
        self.assertEqual(self.game.english_name, "Circus Charlie")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.track_pos, 0.0)
        self.assertEqual(self.game.y, GROUND_Y)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 153)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["track_pos"], 0.0)

    def test_02_lion_gallop_and_reins_control(self):
        # Gallop forward with KEY_RIGHT
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.track_pos, 0.4)

        # Pull back reins with KEY_LEFT
        pos = self.game.track_pos
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.track_pos, pos)

    def test_03_jump_arc_and_gravity_landing(self):
        self.assertEqual(self.game.y, GROUND_Y)
        self.assertFalse(self.game.is_jumping)

        # Press KEY_A to jump
        self.game.update(0.016, KEY_A, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.vy, 0.0)

        # Over time, lion reaches jump peak then lands back on ground
        for _ in range(30):
            self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.y, GROUND_Y)
        self.assertFalse(self.game.is_jumping)

    def test_04_fire_pot_ground_collision_scorches_charlie(self):
        # Fire pot #0 is at track pos 16.0
        self.game.track_pos = 15.8
        self.game.y = GROUND_Y

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_CHARLIE_DOWN)

    def test_05_leaping_over_fire_pot_safely(self):
        # Jump over fire pot at pos 16.0
        self.game.track_pos = 16.0
        self.game.y = 10.0  # Jumping high in air
        self.game.is_jumping = True

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_06_fire_hoop_approaches_charlie(self):
        hoop = self.game.fire_hoops[0]
        initial_pos = hoop["track_pos"]

        self.game.update(0.1, 0, 0)
        self.assertLess(hoop["track_pos"], initial_pos)

    def test_07_clean_leap_through_fire_hoop_center(self):
        hoop = self.game.fire_hoops[1]  # No money bag
        hoop["track_pos"] = 20.0
        self.game.track_pos = 20.0
        self.game.y = 10.5  # In hoop vertical center
        self.game.is_jumping = True

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_08_catching_bonus_money_bag(self):
        hoop = self.game.fire_hoops[0]  # has_money = True
        hoop["track_pos"] = 10.0
        hoop["money_taken"] = False
        self.game.track_pos = 10.0
        self.game.y = 10.5
        self.game.is_jumping = True

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertTrue(hoop["money_taken"])
        self.assertGreaterEqual(self.game.score, initial_score + 500)

    def test_09_circus_podium_finish_clears_stage(self):
        self.game.track_pos = COURSE_LENGTH - 1.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2000)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))

        # Check game over after 3 lives lost
        self.game.lives = 0
        self.game.state = STATE_CHARLIE_DOWN
        self.game.state_timer = 2.0
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Press A to reset
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()

