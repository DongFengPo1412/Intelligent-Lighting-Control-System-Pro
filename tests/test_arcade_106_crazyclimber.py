import unittest
from arcade.game_106_crazyclimber import (
    Game106CrazyClimber,
    STATE_CLIMBING,
    STATE_SLIPPED_ONE_HAND,
    STATE_FALL_OFF,
    STATE_ROOFTOP_CLEAR,
    STATE_GAME_OVER,
    WINDOW_X,
    WINDOW_Y,
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


class TestGame106CrazyClimber(unittest.TestCase):
    def setUp(self):
        self.game = Game106CrazyClimber()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 106)
        self.assertEqual(self.game.name, "疯狂攀爬者")
        self.assertEqual(self.game.english_name, "Crazy Climber")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("双手交替攀附摩天大楼", self.game.core_mechanic)

    def test_lateral_column_shifting(self):
        self.assertEqual(self.game.climber_col, 1)
        # Press KEY_RIGHT
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.climber_col, 2)
        # Press KEY_LEFT
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.climber_col, 1)

    def test_alternating_hand_climb(self):
        init_y = self.game.climber_y
        init_score = self.game.score

        # Left pull (Button A)
        self.game.update(0.05, KEY_A, 0)
        y_after_left = self.game.climber_y
        self.assertLess(y_after_left, init_y)

        # Right pull (Button B) - Alternating bonus!
        self.game.update(0.05, KEY_B, 0)
        y_after_right = self.game.climber_y
        self.assertLess(y_after_right, y_after_left)
        self.assertGreater(self.game.score, init_score + 10)

    def test_facade_scroll_and_altitude(self):
        self.game.climber_y = 3.2
        self.game.altitude = 10
        # Single pull takes it past y <= 3.0 threshold
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.altitude, 20)
        self.assertGreater(self.game.climber_y, 4.0)

    def test_window_shut_finger_pinch(self):
        # Climber at row 4, col 1 (WINDOW_Y[4] = 10)
        self.game.climber_col = 1
        self.game.climber_y = 10.0
        self.game.last_pull_hand = 1

        # Force window [4][1] to open, timer expires and shuts
        self.game.windows[4][1]["is_open"] = True
        self.game.windows[4][1]["toggle_timer"] = 0.02

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_SLIPPED_ONE_HAND)
        self.assertFalse(self.game.left_hand_grip)

    def test_slip_recovery(self):
        self.game.state = STATE_SLIPPED_ONE_HAND
        self.game.left_hand_grip = False
        self.game.right_hand_grip = True
        self.game.slip_recovery_timer = 1.0

        # Press Button A to regain left hand grip
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_CLIMBING)
        self.assertTrue(self.game.left_hand_grip)

    def test_slip_timeout_fall_off(self):
        self.game.state = STATE_SLIPPED_ONE_HAND
        self.game.slip_recovery_timer = 0.02

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_FALL_OFF)

    def test_falling_hazard_collision(self):
        # Climber at col 1 (WINDOW_X[1] = 6), y = 8.0
        self.game.climber_col = 1
        self.game.climber_y = 8.0

        # Falling hazard at (6.0, 7.8)
        self.game.hazards[0]["active"] = True
        self.game.hazards[0]["x"] = 6.0
        self.game.hazards[0]["y"] = 7.8

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_SLIPPED_ONE_HAND)

    def test_rooftop_helicopter_extraction(self):
        self.game.altitude = 80
        self.game.climber_y = 2.4

        # Pull to reach y <= 2.2
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_ROOFTOP_CLEAR)
        self.assertGreater(self.game.score, 2500)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
