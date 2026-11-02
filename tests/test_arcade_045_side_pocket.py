"""
Comprehensive Unit Tests for Arcade Cartridge #045: 花式台球 (Side Pocket 1986 / Data East)
"""

import math
import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_045_side_pocket import (
    Game045SidePocket,
    STATE_START,
    STATE_AIMING,
    STATE_CHARGING,
    STATE_ROLLING,
    STATE_SCRATCH,
    STATE_VICTORY,
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


class TestArcade045SidePocket(unittest.TestCase):
    def setUp(self):
        self.game = Game045SidePocket()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 45)
        self.assertEqual(self.game.release_year, 1986)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "花式台球")
        self.assertIn("Side Pocket", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(45)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game045SidePocket)

    def test_initial_state_and_table_layout(self):
        self.assertEqual(self.game.state, STATE_AIMING)
        self.assertEqual(self.game.get_remaining_balls(), 5)
        self.assertEqual(self.game.balls[0]["x"], 4.0)
        self.assertEqual(self.game.balls[0]["y"], 7.5)
        self.assertTrue(self.game.balls[0]["is_cue"])
        self.assertEqual(self.game.aim_angle, 0.0)

    def test_aim_rotation_controls(self):
        # Rotate Right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.aim_angle, 0.0)

        # Rotate Left wrap around 0 -> 2*PI
        self.game.aim_angle = 0.1
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreater(self.game.aim_angle, 5.0)

    def test_charging_and_strike_cue_ball(self):
        # Press KEY_A to begin charging
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_CHARGING)

        # Release KEY_A to strike
        self.game.update(0.05, 0, KEY_A)
        self.assertEqual(self.game.state, STATE_ROLLING)
        self.assertGreater(self.game.balls[0]["vx"], 0.0)

    def test_cushion_elastic_bounce(self):
        self.game.balls[0]["x"] = 13.2
        self.game.balls[0]["vx"] = 5.0
        self.game.balls[0]["y"] = 7.5
        self.game.balls[0]["vy"] = 0.0

        self.game.check_cushion_collisions()
        # Bounced off right cushion at x=13.0
        self.assertLess(self.game.balls[0]["vx"], 0.0)

    def test_ball_ball_collision_momentum_transfer(self):
        # Cue ball moving right towards stationary object ball 1
        self.game.balls[0]["x"] = 8.8
        self.game.balls[0]["y"] = 7.5
        self.game.balls[0]["vx"] = 8.0
        self.game.balls[0]["vy"] = 0.0

        self.game.balls[1]["x"] = 9.5
        self.game.balls[1]["y"] = 7.5
        self.game.balls[1]["vx"] = 0.0
        self.game.balls[1]["vy"] = 0.0

        self.game.check_ball_ball_collisions()
        # Momentum transferred to ball 1
        self.assertGreater(self.game.balls[1]["vx"], 0.0)

    def test_object_ball_potted_in_pocket(self):
        # Place object ball 1 right next to top-left pocket at (2.0, 2.0)
        self.game.balls[1]["x"] = 2.1
        self.game.balls[1]["y"] = 2.1
        self.game.balls[1]["active"] = True

        prev_score = self.game.score
        self.game.check_pocket_collisions()

        self.assertFalse(self.game.balls[1]["active"])
        self.assertEqual(self.game.balls_potted, 1)
        self.assertEqual(self.game.score, prev_score + 150)

    def test_cue_ball_scratch_penalty(self):
        self.game.score = 200
        # Place cue ball in bottom-right pocket at (13.0, 13.0)
        self.game.balls[0]["x"] = 13.0
        self.game.balls[0]["y"] = 13.0

        self.game.check_pocket_collisions()
        self.assertEqual(self.game.state, STATE_SCRATCH)
        self.assertEqual(self.game.score, 150)  # Deducted 50 pts
        # Respawns at center
        self.assertEqual(self.game.balls[0]["x"], 4.0)
        self.assertEqual(self.game.balls[0]["y"], 7.5)

    def test_victory_condition(self):
        # Pot all 5 object balls
        for i in range(1, 6):
            self.game.balls[i]["active"] = False

        self.game.state = STATE_ROLLING
        self.game.balls[0]["vx"] = 0.0
        self.game.balls[0]["vy"] = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check green felt at center (5, 5): (25, 111, 61)
        idx = (5 * 16 + 5) * 3
        self.assertEqual(fb[idx + 0], 25)
        self.assertEqual(fb[idx + 1], 111)
        self.assertEqual(fb[idx + 2], 61)
        # Check pocket at (2, 2): (0, 0, 0)
        p_idx = (2 * 16 + 2) * 3
        self.assertEqual(fb[p_idx + 0], 0)
        self.assertEqual(fb[p_idx + 1], 0)
        self.assertEqual(fb[p_idx + 2], 0)


if __name__ == "__main__":
    unittest.main()
