# -*- coding: utf-8 -*-
"""
test_arcade_155_roadfighter.py —— 街机游戏 #155 公路争霸 (Road Fighter 1984 / Konami) 单元测试
验证元数据、两档变速轰油400km/h、擦碰侧滑甩尾、极限反向打盘救车、踩油渍打滑、彩虹车燃油补给与千米冲线过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_155_roadfighter import (
    Game155RoadFighter,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_CAR_CRASHED,
    STATE_GAME_OVER,
    ROAD_LEFT,
    ROAD_RIGHT,
    TOTAL_DISTANCE,
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


class TestGame155RoadFighter(unittest.TestCase):
    def setUp(self):
        self.game = Game155RoadFighter()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 155)
        self.assertIn("公路争霸", self.game.name)
        self.assertEqual(self.game.english_name, "Road Fighter")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.fuel, 100.0)
        self.assertFalse(self.game.is_slipping)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 155)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["fuel"], 100.0)

    def test_02_low_gear_acceleration_with_key_b(self):
        self.game.speed = 50.0
        # Hold KEY_B (Low gear)
        self.game.update(0.5, KEY_B, 0)
        self.assertGreater(self.game.speed, 50.0)
        self.assertLessEqual(self.game.speed, 200.0)

    def test_03_high_gear_turbo_with_key_a(self):
        self.game.speed = 200.0
        # Hold KEY_A (High gear)
        self.game.update(0.5, KEY_A, 0)
        self.assertGreater(self.game.speed, 200.0)
        self.assertLessEqual(self.game.speed, 400.0)

    def test_04_steering_left_and_right(self):
        initial_px = self.game.px

        # Steer right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, initial_px)

        # Steer left
        self.game.update(0.2, KEY_LEFT, 0)
        self.assertLess(self.game.px, initial_px + 0.5)

    def test_05_grazing_civilian_car_triggers_fish_tail_slip(self):
        car = self.game.traffic[0]
        car["x"] = 7.5
        car["y"] = 13.0
        self.game.px = 7.4
        self.assertFalse(self.game.is_slipping)

        self.game.update(0.016, 0, 0)
        self.assertTrue(self.game.is_slipping)
        self.assertNotEqual(self.game.slip_dir, 0.0)

    def test_06_counter_steering_saves_car_from_slip(self):
        self.game.is_slipping = True
        self.game.slip_dir = 1.0  # Slipping right
        self.game.px = 7.5
        initial_score = self.game.score

        # Counter-steer LEFT for 0.25 seconds
        for _ in range(15):
            self.game.update(0.02, KEY_LEFT, 0)

        # Car was saved and straightened out!
        self.assertFalse(self.game.is_slipping)
        self.assertEqual(self.game.slip_dir, 0.0)
        self.assertGreaterEqual(self.game.score, initial_score + 200)

    def test_07_oil_slick_triggers_immediate_slip(self):
        oil = self.game.oil_slicks[0]
        oil["x"] = 7.5
        oil["y"] = 13.0
        self.game.px = 7.5
        self.assertFalse(self.game.is_slipping)

        self.game.update(0.016, 0, 0)
        self.assertTrue(self.game.is_slipping)

    def test_08_hitting_guardrail_crashes_car(self):
        self.game.px = ROAD_LEFT - 0.2
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_CAR_CRASHED)
        self.assertEqual(self.game.speed, 0.0)

    def test_09_rainbow_car_refuels_gas_tank(self):
        self.game.rainbow_car["x"] = 7.5
        self.game.rainbow_car["y"] = 13.0
        self.game.rainbow_car["active"] = True
        self.game.px = 7.5
        self.game.fuel = 50.0

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertFalse(self.game.rainbow_car["active"])
        self.assertAlmostEqual(self.game.fuel, 80.0, delta=0.5)
        self.assertGreaterEqual(self.game.score, initial_score + 1000)

    def test_10_crossing_finish_line_clears_stage_and_render(self):
        self.game.distance = TOTAL_DISTANCE + 1.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 3000)

        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()
