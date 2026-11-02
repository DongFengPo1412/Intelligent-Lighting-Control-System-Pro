import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_081_rampage import (
    Game081Rampage,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_MONSTER_DEAD,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)


class TestGame081Rampage(unittest.TestCase):
    def setUp(self):
        self.game = Game081Rampage()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 81)
        self.assertEqual(self.game.name, "狂暴巨兽")
        self.assertEqual(self.game.english_name, "Rampage")
        self.assertEqual(self.game.release_year, 1986)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("巨兽大楼攀爬", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["monster_hp"], 100)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["buildings_standing"], 3)
        self.assertEqual(self.game.mx, 1.0)
        self.assertEqual(self.game.my, 14.0)

    def test_horizontal_movement(self):
        # Walk right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.mx, 1.0)
        self.assertEqual(self.game.facing, 1)

    def test_building_wall_climbing(self):
        # Position at building 0 left wall (x = 1.0)
        self.game.mx = 1.0
        self.game.my = 13.0
        self.game.update(0.1, KEY_UP, 0)
        self.assertTrue(self.game.on_wall)
        self.assertEqual(self.game.current_building, 0)

        # Climb higher
        old_y = self.game.my
        self.game.update(0.1, KEY_UP, KEY_UP)
        self.assertLess(self.game.my, old_y)

    def test_wall_punch_and_hp_reduction(self):
        # Monster on wall of building 0
        self.game.mx = 1.0
        self.game.my = 10.0
        self.game.on_wall = True
        self.game.current_building = 0

        old_hp = self.game.buildings[0]["hp"]
        old_score = self.game.score

        # Punch wall with A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.buildings[0]["hp"], old_hp - 1)
        self.assertGreater(self.game.score, old_score)

    def test_building_collapse_mechanic(self):
        self.game.mx = 1.0
        self.game.my = 10.0
        self.game.on_wall = True
        self.game.current_building = 0
        self.game.buildings[0]["hp"] = 1

        # Final strike
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.buildings[0]["collapsed"])
        self.assertFalse(self.game.on_wall)

    def test_helicopter_swat(self):
        self.game.mx = 5.0
        self.game.my = 5.0
        self.game.heli["x"] = 5.5
        self.game.heli["y"] = 5.0
        self.game.heli["active"] = True

        old_score = self.game.score
        # Punch heli
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.heli["active"])
        self.assertGreater(self.game.score, old_score)

    def test_city_leveling_stage_clear(self):
        for b in self.game.buildings:
            b["collapsed"] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)

    def test_monster_damage_and_death(self):
        self.game.monster_hp = 5
        self.game.heli["x"] = self.game.mx
        self.game.heli["y"] = self.game.my
        self.game.heli["active"] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.monster_hp, 100)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
