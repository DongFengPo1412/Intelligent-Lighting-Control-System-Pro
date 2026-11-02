import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_077_windjammers import (
    Game077Windjammers,
    STATE_SERVE,
    STATE_RALLY,
    STATE_GOAL,
    STATE_MATCH_OVER,
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


class TestGame077Windjammers(unittest.TestCase):
    def setUp(self):
        self.game = Game077Windjammers()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 77)
        self.assertEqual(self.game.name, "泡泡飞盘")
        self.assertEqual(self.game.english_name, "Windjammers")
        self.assertEqual(self.game.release_year, 1994)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("双人球台飞盘弧线对掷", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_SERVE)
        self.assertEqual(status["player_score"], 0)
        self.assertEqual(status["ai_score"], 0)
        self.assertEqual(status["disc_held_by"], 1)  # Player serves
        self.assertEqual(status["match_timer"], 60.0)

    def test_player_movement_and_court_boundary(self):
        # Move right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 3.0)

        # Move far right - should be bounded by center line (x <= 7.0)
        for _ in range(30):
            self.game.update(0.1, KEY_RIGHT, KEY_RIGHT)
        self.assertLessEqual(self.game.px, 7.0)

    def test_player_throw_mechanic(self):
        self.assertEqual(self.game.disc_held_by, 1)
        # Press A to throw
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.disc_held_by, 0)
        self.assertEqual(self.game.state, STATE_RALLY)
        self.assertGreater(self.game.disc_vx, 0.0)

    def test_player_curve_throw(self):
        self.game.reset()
        # Throw with UP held for curve
        self.game.update(0.05, KEY_A | KEY_UP, 0)
        self.assertEqual(self.game.disc_held_by, 0)
        self.assertLess(self.game.disc_vy, 0.0)  # Curving upwards

    def test_slide_dash_intercept(self):
        # First throw disc away so player is not holding it
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.disc_held_by, 0)

        # Press B with direction to slide dash
        old_x = self.game.px
        self.game.update(0.05, KEY_B | KEY_RIGHT, 0)
        self.assertGreater(self.game.p_dash_timer, 0.0)

        # Update during dash: should move faster than normal speed
        self.game.update(0.1, 0, 0)
        self.assertGreater(self.game.px, old_x + 0.5)

    def test_super_shot_charging(self):
        self.game.reset()
        self.assertEqual(self.game.disc_held_by, 1)
        
        # Hold disc for 0.7s to build charge
        self.game.update(0.7, 0, 0)
        self.assertGreaterEqual(self.game.player_charge, 0.95)

        # Throw charged super shot!
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.disc_is_super)
        self.assertEqual(self.game.disc_vx, 16.0)

    def test_wall_rebound_physics(self):
        self.game.reset()
        self.game.disc_held_by = 0
        self.game.disc_x = 8.0
        self.game.disc_y = 1.0
        self.game.disc_vx = 5.0
        self.game.disc_vy = -6.0  # moving up towards ceiling

        self.game.update(0.15, 0, 0)
        self.assertGreater(self.game.disc_vy, 0.0)  # bounced back down

    def test_goal_scoring_and_points(self):
        self.game.reset()
        self.game.disc_held_by = 0
        self.game.disc_x = 14.5
        self.game.disc_y = 7.5  # Red zone (5 points)
        self.game.disc_vx = 10.0
        self.game.disc_vy = 0.0

        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_GOAL)
        self.assertEqual(self.game.player_score, 5)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
