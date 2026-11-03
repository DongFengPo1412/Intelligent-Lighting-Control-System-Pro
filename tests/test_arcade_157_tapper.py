# -*- coding: utf-8 -*-
"""
test_arcade_157_tapper.py —— 街机游戏 #157 酒吧侍应生 (Tapper 1983 / Bally Midway) 单元测试
验证元数据、四排吧台纵向穿梭、滑行斟酒推杯、酒客畅饮击退、滑回空杯精准接取防碎、台面小费收取与清场过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_157_tapper import (
    Game157Tapper,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_MUG_SHATTERED,
    STATE_GAME_OVER,
    BAR_LEFT,
    BAR_RIGHT,
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


class TestGame157Tapper(unittest.TestCase):
    def setUp(self):
        self.game = Game157Tapper()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 157)
        self.assertIn("酒吧侍应生", self.game.name)
        self.assertEqual(self.game.english_name, "Tapper")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.bar_idx, 1)
        self.assertEqual(self.game.bx, BAR_RIGHT)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 157)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["bar_idx"], 1)

    def test_02_vertical_lane_movement_and_counter_walk(self):
        self.assertEqual(self.game.bar_idx, 1)

        # Move UP to bar 0
        self.game.update(0.016, KEY_UP, 0)
        self.assertEqual(self.game.bar_idx, 0)

        # Move DOWN to bar 1
        self.game.update(0.016, KEY_DOWN, 0)
        self.assertEqual(self.game.bar_idx, 1)

        # Walk left along bar
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.bx, BAR_RIGHT)
        self.assertGreaterEqual(self.game.bx, 7.0)

    def test_03_pour_and_slide_beer_mug_with_key_a(self):
        self.game.bx = BAR_RIGHT
        self.game.bar_idx = 2
        self.assertEqual(len(self.game.mugs), 0)

        # Press KEY_A to slide beer mug
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(len(self.game.mugs), 1)
        self.assertEqual(self.game.mugs[0]["bar"], 2)
        self.assertFalse(self.game.mugs[0]["empty"])
        self.assertLess(self.game.mugs[0]["vx"], 0.0)

    def test_04_patron_catches_beer_and_pushes_back(self):
        self.game.patrons = [{"bar": 1, "x": 8.0, "speed": 1.0, "drinking": False, "active": True}]
        self.game.mugs = [{"bar": 1, "x": 8.5, "vx": -7.0, "empty": False, "active": True}]

        initial_score = self.game.score
        # Mug reaches patron
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.score, initial_score + 150)
        # Patron should have caught mug and slid backwards
        self.assertLess(self.game.patrons[0]["x"], 8.0)

    def test_05_patron_slides_empty_mug_back_right(self):
        self.game.patrons = [{"bar": 1, "x": 8.0, "speed": 1.0, "drinking": False, "active": True}]
        self.game.mugs = [{"bar": 1, "x": 8.2, "vx": -7.0, "empty": False, "active": True}]

        self.game.update(0.016, 0, 0)
        # Check empty mug was spawned sliding right
        empty_mugs = [m for m in self.game.mugs if m["empty"]]
        self.assertEqual(len(empty_mugs), 1)
        self.assertGreater(empty_mugs[0]["vx"], 0.0)

    def test_06_bartender_catches_returning_empty_mug(self):
        self.game.bar_idx = 1
        self.game.bx = BAR_RIGHT
        self.game.mugs = [{"bar": 1, "x": BAR_RIGHT - 0.2, "vx": 5.5, "empty": True, "active": True}]

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.score, initial_score + 100)
        self.assertEqual(len(self.game.mugs), 0)

    def test_07_empty_mug_falling_off_shatters_and_loses_life(self):
        # Bartender on bar 0, empty mug on bar 2 reaches right end
        self.game.bar_idx = 0
        self.game.mugs = [{"bar": 2, "x": BAR_RIGHT + 0.6, "vx": 5.5, "empty": True, "active": True}]

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_MUG_SHATTERED)

    def test_08_overpoured_mug_slides_off_left_end(self):
        # Full mug with no patrons on bar slides off left edge
        self.game.mugs = [{"bar": 1, "x": BAR_LEFT - 0.6, "vx": -7.0, "empty": False, "active": True}]
        self.game.patrons.clear()

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_MUG_SHATTERED)

    def test_09_collecting_tips_on_counter(self):
        self.game.bar_idx = 1
        self.game.tips = [{"bar": 1, "x": 10.0, "active": True}]
        self.game.bx = 10.2

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertEqual(len(self.game.tips), 0)
        self.assertEqual(self.game.score, initial_score + 250)

    def test_10_stage_clear_when_all_patrons_served_and_render(self):
        self.game.total_patrons_spawned = self.game.total_patrons_required
        self.game.patrons.clear()
        self.game.mugs.clear()

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2500)

        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()
