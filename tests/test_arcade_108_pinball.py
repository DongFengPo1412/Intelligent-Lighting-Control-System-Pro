import unittest
from arcade.game_108_pinball import (
    Game108Pinball,
    STATE_PLUNGER_READY,
    STATE_BALL_IN_PLAY,
    STATE_BALL_DRAINED,
    STATE_GAME_OVER,
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


class TestGame108Pinball(unittest.TestCase):
    def setUp(self):
        self.game = Game108Pinball()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 108)
        self.assertEqual(self.game.name, "街机弹珠台")
        self.assertEqual(self.game.english_name, "Pinball")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("左右双挡板重力反弹", self.game.core_mechanic)

    def test_plunger_charge_and_launch(self):
        self.assertEqual(self.game.state, STATE_PLUNGER_READY)
        # Pull plunger with KEY_DOWN
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertGreater(self.game.plunger_charge, 0.0)

        # Release KEY_DOWN
        self.game.update(0.05, 0, KEY_DOWN)
        self.assertEqual(self.game.state, STATE_BALL_IN_PLAY)
        self.assertLess(self.game.ball_vy, 0.0)

    def test_flipper_controls(self):
        # Press Button A
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.left_flipper_up)
        self.assertFalse(self.game.right_flipper_up)

        # Press Button B
        self.game.update(0.05, KEY_B, 0)
        self.assertFalse(self.game.left_flipper_up)
        self.assertTrue(self.game.right_flipper_up)

    def test_shooter_lane_curve_entry(self):
        self.game.state = STATE_BALL_IN_PLAY
        self.game.ball_x = 14.5
        self.game.ball_y = 1.6
        self.game.ball_vy = -8.0

        self.game.update(0.05, 0, 0)
        # Curved left into main table!
        self.assertLess(self.game.ball_x, 13.0)
        self.assertLess(self.game.ball_vx, 0.0)

    def test_bumper_collision_and_repulsion(self):
        self.game.state = STATE_BALL_IN_PLAY
        # Bumper 0 is at (5.0, 5.0)
        self.game.ball_x = 5.2
        self.game.ball_y = 5.5
        self.game.ball_vy = -4.0

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.score, init_score)
        self.assertGreater(self.game.bumpers[0]["flash_timer"], 0.0)
        self.assertGreater(self.game.ball_vy, 0.0)  # Repelled downward

    def test_flipper_strike(self):
        self.game.state = STATE_BALL_IN_PLAY
        # Ball falling onto left flipper at (5.5, 13.8)
        self.game.ball_x = 5.5
        self.game.ball_y = 13.8
        self.game.ball_vy = 4.0

        init_score = self.game.score
        # Press Button A (flip up)
        self.game.update(0.05, KEY_A, 0)
        self.assertLess(self.game.ball_vy, 0.0)  # Struck hard upwards!
        self.assertGreater(self.game.score, init_score)

    def test_rollover_lanes_multiplier_increase(self):
        self.game.state = STATE_BALL_IN_PLAY
        self.assertEqual(self.game.multiplier, 1)

        # Light rollover 0
        self.game.ball_x = 4.0
        self.game.ball_y = 3.0
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.rollovers[0]["lit"])

        # Light rollover 1
        self.game.ball_x = 7.0
        self.game.ball_y = 3.0
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.rollovers[1]["lit"])

        # Light rollover 2 -> Completes set!
        self.game.ball_x = 10.0
        self.game.ball_y = 3.0
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.multiplier, 2)
        # Rollovers reset for next bank
        self.assertFalse(self.game.rollovers[0]["lit"])

    def test_ball_drain_loss(self):
        self.game.state = STATE_BALL_IN_PLAY
        self.game.ball_x = 7.5  # Between flippers into drain
        self.game.ball_y = 15.6

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_BALL_DRAINED)

    def test_game_over_on_last_ball(self):
        self.game.state = STATE_BALL_DRAINED
        self.game.state_timer = 1.9
        self.game.balls_left = 1

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.balls_left, 0)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
