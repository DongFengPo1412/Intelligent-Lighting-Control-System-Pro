import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_058_paperboy import (
    Game058Paperboy,
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


class TestArcade058Paperboy(unittest.TestCase):
    def setUp(self):
        self.game = Game058Paperboy()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 58)
        self.assertEqual(self.game.english_name, "Paperboy")
        self.assertEqual(self.game.release_year, 1984)
        cart = ArcadeRegistry.get_cartridge(58)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game058Paperboy)

    def test_bicycle_steering_and_speed(self):
        initial_x = self.game.player_x
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, initial_x)

        # Accelerate Up
        initial_speed = self.game.speed
        self.game.update(0.2, KEY_UP, 0)
        self.assertGreater(self.game.speed, initial_speed)

        # Brake Down
        self.game.update(0.4, KEY_DOWN, 0)
        self.assertLess(self.game.speed, 9.0)

    def test_throw_paper_mechanic(self):
        self.assertEqual(self.game.papers_remaining, 10)
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(self.game.papers_remaining, 9)
        self.assertEqual(len(self.game.papers), 1)
        self.assertLess(self.game.papers[0]["vx"], 0.0)  # Thrown left towards houses

    def test_out_of_papers_prevents_throw(self):
        self.game.papers_remaining = 0
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.papers), 0)

    def test_subscriber_mailbox_delivery(self):
        house = self.game.houses[0]
        self.assertTrue(house["is_subscriber"])
        self.assertFalse(house["delivered"])
        house["y"] = 10.0

        # Throw paper directly at mailbox (x=4.0, y=10.0)
        self.game.papers.append({
            "x": 4.0,
            "y": 10.0,
            "vx": -1.0,
            "vy": 0.0,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertTrue(house["delivered"])
        self.assertEqual(self.game.delivered_count, 1)
        self.assertGreater(self.game.score, 0)

    def test_non_subscriber_window_vandalism(self):
        house = self.game.houses[1]
        self.assertFalse(house["is_subscriber"])
        self.assertFalse(house["window_broken"])
        house["y"] = 10.0

        # Throw paper at window (x=2.0, y=10.0)
        self.game.papers.append({
            "x": 2.0,
            "y": 10.0,
            "vx": -1.0,
            "vy": 0.0,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertTrue(house["window_broken"])
        self.assertGreater(self.game.score, 0)

    def test_hazard_crash_causes_death(self):
        hazard = self.game.hazards[0]
        hazard["x"] = 8.0
        hazard["y"] = 12.5
        hazard["active"] = True
        self.game.player_x = 8.0
        self.game.player_y = 12.5

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_route_completion_victory(self):
        self.game.route_progress = 44.9
        self.game.speed = 5.0
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_paper_flight_decay(self):
        self.game.papers.append({
            "x": -0.5,
            "y": 5.0,
            "vx": -5.0,
            "vy": 0.0,
            "active": True
        })
        self.game.update(0.02, 0, 0)
        self.assertEqual(len(self.game.papers), 0)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 58)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
