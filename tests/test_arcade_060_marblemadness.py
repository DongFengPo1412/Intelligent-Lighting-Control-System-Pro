import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_060_marblemadness import (
    Game060MarbleMadness,
    STATE_START,
    STATE_PLAYING,
    STATE_SHATTERED,
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


class TestArcade060MarbleMadness(unittest.TestCase):
    def setUp(self):
        self.game = Game060MarbleMadness()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 60)
        self.assertEqual(self.game.english_name, "Marble Madness")
        self.assertEqual(self.game.release_year, 1984)
        cart = ArcadeRegistry.get_cartridge(60)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game060MarbleMadness)

    def test_downhill_slope_gravity(self):
        self.assertEqual(self.game.marble_vx, 0.0)
        self.assertEqual(self.game.marble_vy, 0.0)

        # No buttons, just downhill gravity slope
        self.game.update(0.1, 0, 0)
        self.assertGreater(self.game.marble_vx, 0.0)
        self.assertGreater(self.game.marble_vy, 0.0)

    def test_player_rolling_inputs(self):
        # Steer Left
        self.game.marble_vx = 0.0
        self.game.update(0.1, KEY_LEFT, 0)
        # Torque to left overcomes slight downhill gravity (ax = -14 + 1.8 = -12.2)
        self.assertLess(self.game.marble_vx, 0.0)

    def test_ice_friction_slip(self):
        # Place marble on ice bridge (x=6.0, y=7.0)
        self.game.marble_x = 6.0
        self.game.marble_y = 7.0
        self.game.marble_vx = 5.0
        self.game.marble_vy = 5.0

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.is_on_ice)
        self.assertGreater(self.game.marble_vx, 4.5)  # Very low friction loss!

    def test_cliff_fall_shatters_marble(self):
        # Position marble far off-track into the void (x=15.0, y=1.0)
        self.game.marble_x = 15.0
        self.game.marble_y = 1.0
        initial_time = self.game.time_remaining

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_SHATTERED)
        self.assertLess(self.game.time_remaining, initial_time)  # 5s time penalty

    def test_acid_puddle_dissolves_marble(self):
        self.game.marble_x = 8.5
        self.game.marble_y = 11.5

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_SHATTERED)

    def test_evil_marble_repulsion(self):
        self.game.marble_x = 8.0
        self.game.marble_y = 8.0
        self.game.evil_x = 8.2
        self.game.evil_y = 8.2

        self.game.update(0.02, 0, 0)
        # Collided and repelled violently
        self.assertLess(self.game.marble_vx, 0.0)
        self.assertLess(self.game.marble_vy, 0.0)

    def test_time_out_defeat(self):
        self.game.time_remaining = 0.05
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_goal_crossing_victory(self):
        self.game.marble_x = 12.5
        self.game.marble_y = 14.0

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 60)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
