import unittest
from arcade.game_111_leaguebowling import (
    Game111LeagueBowling,
    STATE_AIMING,
    STATE_POWER_GAUGE,
    STATE_BALL_ROLLING,
    STATE_FRAME_RESULT,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestGame111LeagueBowling(unittest.TestCase):
    def setUp(self):
        self.game = Game111LeagueBowling()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 111)
        self.assertEqual(self.game.name, "街机保龄球")
        self.assertEqual(self.game.english_name, "League Bowling")
        self.assertEqual(self.game.release_year, 1990)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("十瓶", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_AIMING)
        self.assertEqual(self.game.current_frame, 1)
        self.assertEqual(self.game.current_roll, 1)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(len(self.game.pins), 10)
        self.assertTrue(all(p["standing"] for p in self.game.pins))
        self.assertEqual(self.game.hook_spin, 0)

    def test_bowler_lateral_movement_and_clamping(self):
        self.assertEqual(self.game.bowler_x, 7.5)

        # Move left
        for _ in range(30):
            self.game.update(0.05, KEY_LEFT, 0)
        self.assertAlmostEqual(self.game.bowler_x, 4.0, delta=0.01)

        # Move right past maximum clamp
        for _ in range(60):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertAlmostEqual(self.game.bowler_x, 11.0, delta=0.01)

    def test_hook_spin_selection(self):
        self.assertEqual(self.game.hook_spin, 0)

        # Press B -> -1 (Left hook)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.hook_spin, -1)

        # Press B again -> 1 (Right hook)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.hook_spin, 1)

        # Press B again -> 0 (Straight)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.hook_spin, 0)

    def test_power_gauge_oscillation(self):
        # Press A to start power gauge
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_POWER_GAUGE)
        self.assertAlmostEqual(self.game.gauge_val, 0.2, delta=0.01)

        # Gauge increases
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.gauge_val, 0.2)

    def test_throw_release(self):
        # Start gauge
        self.game.update(0.05, KEY_A, 0)
        # Release ball with A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_BALL_ROLLING)
        self.assertLess(self.game.ball_vy, -5.0)
        self.assertEqual(self.game.ball_y, 13.0)

    def test_gutter_detection(self):
        self.game.bowler_x = 4.0
        # Left spin hook from edge goes into gutter
        self.game.force_throw(power=10.0, hook=-1)
        self.assertEqual(self.game.state, STATE_BALL_ROLLING)

        # Run ball update
        for _ in range(15):
            self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.in_gutter)
        self.assertLessEqual(self.game.ball_x, 2.8)

    def test_pin_collision_and_domino_chain(self):
        self.game.bowler_x = 7.5
        # Direct straight throw at headpin (7.5, 5.0)
        self.game.force_throw(power=10.0, hook=0)

        # Roll until impact
        while self.game.ball_y > 5.0 and self.game.state == STATE_BALL_ROLLING:
            self.game.update(0.02, 0, 0)

        # Pin impact triggers collision and domino scatter
        self.assertGreater(self.game.pins_knocked_down, 0)
        self.assertGreater(self.game.score, 0)
        # Headpin (pin 0) knocked down
        self.assertFalse(self.game.pins[0]["standing"])

    def test_strike_bonus(self):
        # Manually simulate all pins knocked down on roll 1
        for p in self.game.pins:
            p["standing"] = False
        self.game.pins_knocked_down = 10
        self.game.ball_y = 0.5
        self.game.state = STATE_BALL_ROLLING
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_FRAME_RESULT)
        # 10 pins * 10 pts + 300 strike bonus = 400 pts minimum
        self.assertGreaterEqual(self.game.score, 300)

    def test_spare_and_frame_progression(self):
        self.game.pins_knocked_down = 5
        self.game.current_roll = 1
        self.game.ball_y = 0.5
        self.game.state = STATE_BALL_ROLLING
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_FRAME_RESULT)
        # Wait for result timer to trigger roll 2
        for _ in range(40):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.current_roll, 2)
        self.assertEqual(self.game.state, STATE_AIMING)


if __name__ == "__main__":
    unittest.main()
