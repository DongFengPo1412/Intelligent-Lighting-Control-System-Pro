import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_059_trackfield import (
    Game059TrackField,
    STATE_START,
    STATE_RUNNING,
    STATE_ANGLE_AIM,
    STATE_FLIGHT,
    STATE_FOUL,
    STATE_RESULT,
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


class TestArcade059TrackField(unittest.TestCase):
    def setUp(self):
        self.game = Game059TrackField()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 59)
        self.assertEqual(self.game.english_name, "Track & Field")
        self.assertEqual(self.game.release_year, 1983)
        cart = ArcadeRegistry.get_cartridge(59)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game059TrackField)

    def test_alternating_button_sprint(self):
        self.assertEqual(self.game.speed, 0.0)

        # Alternating presses A then B
        self.game.update(0.01, KEY_A, 0)
        self.game.update(0.01, KEY_B, KEY_A)
        self.assertGreater(self.game.speed, 0.0)

        self.game.update(0.01, KEY_A, KEY_B)
        self.game.update(0.01, KEY_B, KEY_A)
        self.assertGreater(self.game.speed, 3.0)

    def test_stumble_penalty(self):
        # Press A twice in a row
        self.game.speed = 5.0
        self.game.last_button_pressed = 1
        self.game.update(0.01, KEY_A, 0)
        self.assertLess(self.game.speed, 5.0)

    def test_angle_aiming(self):
        self.game.speed = 8.0
        self.game.athlete_x = 5.0
        self.game.update(0.02, KEY_UP, 0)
        self.assertEqual(self.game.state, STATE_ANGLE_AIM)
        self.assertGreater(self.game.throw_angle, 0.0)

    def test_optimal_launch_and_distance(self):
        self.game.speed = 10.0
        self.game.trigger_release(43.0)
        self.assertEqual(self.game.state, STATE_FLIGHT)
        self.assertGreater(self.game.throw_distance, 70.0)  # Over 70 meters!
        self.assertGreater(self.game.best_distance, 70.0)

    def test_foul_line_breach(self):
        self.game.athlete_x = 11.4
        self.game.speed = 5.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_FOUL)
        self.assertEqual(self.game.throw_distance, 0.0)

    def test_qualifying_mark_victory(self):
        self.game.throw_distance = 75.0
        self.game.state = STATE_RESULT
        self.game.state_timer = 1.85

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000)

    def test_three_failed_attempts_game_over(self):
        self.game.attempt = 3
        self.game.throw_distance = 50.0  # Below 65.0m threshold
        self.game.state = STATE_RESULT
        self.game.state_timer = 1.85

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_flight_landing(self):
        self.game.state = STATE_FLIGHT
        self.game.javelin_y = 12.9
        self.game.javelin_vy = 5.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_RESULT)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 59)
        self.assertEqual(status["state"], STATE_RUNNING)


if __name__ == "__main__":
    unittest.main()
