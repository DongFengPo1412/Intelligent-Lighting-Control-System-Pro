import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_054_antarctic import (
    Game054Antarctic,
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


class TestArcade054Antarctic(unittest.TestCase):
    def setUp(self):
        self.game = Game054Antarctic()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 54)
        self.assertEqual(self.game.english_name, "Antarctic Adventure")
        self.assertEqual(self.game.release_year, 1983)
        cart = ArcadeRegistry.get_cartridge(54)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game054Antarctic)

    def test_steering_and_speed_control(self):
        initial_lane = self.game.penguin_lane
        # Steer Right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.penguin_lane, initial_lane)

        # Accelerate Up
        initial_speed = self.game.speed
        self.game.update(0.2, KEY_UP, 0)
        self.assertGreater(self.game.speed, initial_speed)

        # Brake Down
        self.game.update(0.5, KEY_DOWN, 0)
        self.assertLess(self.game.speed, 24.0)

    def test_jump_mechanic(self):
        self.assertFalse(self.game.is_jumping)
        # Button A jump
        self.game.update(0.02, KEY_A, 0)
        self.assertTrue(self.game.is_jumping)

        # Advance until jump lands
        for _ in range(15):
            self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.is_jumping)

    def test_crevasse_jump_clearance(self):
        self.game.penguin_lane = 0.0
        self.game.crevasses[0]["z"] = 1.0
        self.game.crevasses[0]["lane"] = 0.0
        self.game.is_jumping = True
        self.game.jump_timer = 0.3

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.trip_stun_timer, 0.0)
        self.assertGreater(self.game.speed, 0.0)  # Jumped right over it!

    def test_crevasse_trip_and_stun(self):
        self.game.penguin_lane = 0.0
        self.game.crevasses[0]["z"] = 1.0
        self.game.crevasses[0]["lane"] = 0.0
        self.game.is_jumping = False

        self.game.update(0.02, 0, 0)
        self.assertGreater(self.game.trip_stun_timer, 0.0)
        self.assertEqual(self.game.speed, 0.0)

    def test_seal_bump_collision(self):
        self.game.penguin_lane = 0.4
        self.game.seals[0]["z"] = 1.0
        self.game.seals[0]["lane"] = 0.4

        self.game.update(0.02, 0, 0)
        self.assertGreater(self.game.trip_stun_timer, 0.0)
        self.assertEqual(self.game.speed, 0.0)

    def test_fish_catch_boost_and_bonus(self):
        self.game.penguin_lane = 0.0
        self.game.fishes[0]["z"] = 1.0
        self.game.fishes[0]["lane"] = 0.0
        initial_score = self.game.score
        initial_time = self.game.time_remaining

        self.game.update(0.02, 0, 0)
        self.assertFalse(self.game.fishes[0]["active"])
        self.assertGreater(self.game.score, initial_score)
        self.assertGreater(self.game.time_remaining, initial_time)
        self.assertEqual(self.game.fish_collected, 1)

    def test_distance_progression_and_victory(self):
        self.game.distance_remaining = 0.1
        self.game.speed = 10.0
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_time_out_defeat(self):
        self.game.time_remaining = 0.05
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 54)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
