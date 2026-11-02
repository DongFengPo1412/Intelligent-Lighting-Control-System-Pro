import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_074_donkeykong3 import (
    Game074DonkeyKong3,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade074DonkeyKong3(unittest.TestCase):
    def setUp(self):
        self.game = Game074DonkeyKong3()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 74)
        self.assertEqual(self.game.english_name, "Donkey Kong 3")
        self.assertEqual(self.game.release_year, 1983)
        cart = ArcadeRegistry.get_cartridge(74)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game074DonkeyKong3)

    def test_movement_and_platform_jump(self):
        initial_x = self.game.px
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, initial_x)

        # Jump with Button A
        self.assertTrue(self.game.on_ground)
        self.game.update(0.02, KEY_A, 0)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.pvy, 0)

    def test_spray_upward_trajectory(self):
        self.assertEqual(len(self.game.sprays), 0)
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.sprays), 1)
        self.assertLess(self.game.sprays[0]["vy"], 0)  # Sprays upward!

    def test_spraying_donkey_kong_pushes_upward(self):
        initial_dk_y = self.game.dk_y
        self.game.px = self.game.dk_x
        self.game.py = 10.0

        # Spray upward directly into DK
        self.game.spray_upward()
        self.game.sprays[0]["y"] = self.game.dk_y + 1.0  # Underneath DK
        self.game.check_collisions()

        self.assertLess(self.game.dk_y, initial_dk_y)  # Pushed upward!
        self.assertGreater(self.game.score, 0)

    def test_super_spray_can_pickup_and_boost(self):
        self.assertFalse(self.game.has_super_spray)
        # Trigger super can drop
        self.game.super_can_active = True
        self.game.super_can_x = self.game.px
        self.game.super_can_y = self.game.py

        self.game.check_collisions()
        self.assertFalse(self.game.super_can_active)
        self.assertTrue(self.game.has_super_spray)

        # Super spray pushes DK by 1.6 instead of 0.8
        self.game.px = self.game.dk_x
        dk_before = self.game.dk_y
        self.game.spray_upward()
        self.game.sprays[0]["y"] = self.game.dk_y + 1.0
        self.game.check_collisions()
        self.assertAlmostEqual(self.game.dk_y, dk_before - 1.6, delta=0.01)

    def test_donkey_kong_pushed_to_beehive_victory(self):
        self.game.dk_y = 2.0
        self.game.px = self.game.dk_x
        self.game.spray_upward()
        self.game.sprays[0]["y"] = self.game.dk_y + 1.0
        self.game.check_collisions()

        self.assertLessEqual(self.game.dk_y, 1.5)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 3500)

    def test_donkey_kong_slides_down_crushes_stanley(self):
        self.game.dk_y = 11.4
        self.game.update_donkey_kong(0.3)
        self.assertGreaterEqual(self.game.dk_y, 11.5)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_bug_steals_flower_and_rescue(self):
        self.assertEqual(self.game.get_flowers_remaining(), 4)
        bug = self.game.bugs[0]
        bug["x"] = 3.0
        bug["y"] = 14.0  # Flower at (3, 14)

        self.game.update_bugs(0.02)
        self.assertTrue(bug["has_flower"])
        self.assertEqual(self.game.get_flowers_remaining(), 3)

        # Shoot bug to rescue flower
        self.game.sprays.append({"x": bug["x"], "y": bug["y"], "vy": -10.0, "is_super": False, "active": True})
        self.game.check_collisions()
        self.assertFalse(bug["active"])
        self.assertEqual(self.game.get_flowers_remaining(), 4)  # Restored!

    def test_bug_stings_stanley_death(self):
        bug = self.game.bugs[0]
        bug["x"] = self.game.px
        bug["y"] = self.game.py

        self.game.check_collisions()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_render_framebuffer_and_status(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 74)
        self.assertEqual(status["name"], "灭虫专家")


if __name__ == "__main__":
    unittest.main()
