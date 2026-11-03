"""
Unit Tests for Game #186: 冠军棒球 (Champion Baseball - 1983 Sega)
"""

import unittest
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    CTRL_ARCADE_AB,
)
from arcade.game_186_championbaseball import (
    Game186ChampionBaseball,
    STATE_PITCHING,
    STATE_BALL_IN_PLAY,
    STATE_INNING_END,
    STATE_GAME_OVER,
)

class TestArcade186ChampionBaseball(unittest.TestCase):
    def setUp(self):
        self.game = Game186ChampionBaseball()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 186)
        self.assertEqual(self.game.name, "冠军棒球")
        self.assertEqual(self.game.english_name, "Champion Baseball")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PITCHING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.inning, 1)
        self.assertEqual(self.game.outs, 0)
        self.assertEqual(self.game.strikes, 0)
        self.assertEqual(self.game.balls, 0)
        self.assertEqual(self.game.bases, [False, False, False])

    def test_02_batter_stance_adjustment(self):
        init_x = self.game.batter_x
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.batter_x, init_x)

        # Clamping
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreaterEqual(self.game.batter_x, 5.0)

        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertLessEqual(self.game.batter_x, 10.0)

    def test_03_swing_timing_window(self):
        self.assertFalse(self.game.is_swinging)
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_swinging)
        self.assertGreater(self.game.swing_timer, 0.0)

        # Swing expires
        for _ in range(20):
            self.game.update(0.016)
        self.assertFalse(self.game.is_swinging)

    def test_04_bunt_mechanic_button_b(self):
        self.assertFalse(self.game.is_swinging)
        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertTrue(self.game.is_swinging)
        self.assertGreater(self.game.swing_timer, 0.25)

    def test_05_strike_called_when_pitch_crosses_plate(self):
        # Position ball in strike zone right above plate
        self.game.ball_active = True
        self.game.ball_x = 7.5
        self.game.ball_y = 14.0
        self.game.ball_vx = 0.0
        self.game.ball_vy = 10.0

        # Step forward so ball crosses y = 14.5
        self.game.update(0.1) # 14.0 + 1.0 = 15.0 >= 14.5
        self.assertEqual(self.game.strikes, 1)
        self.assertEqual(self.game.balls, 0)

    def test_06_three_strikes_strikeout_out_recorded(self):
        self.game.strikes = 2
        self.game.ball_active = True
        self.game.ball_x = 7.5
        self.game.ball_y = 14.0
        self.game.ball_vx = 0.0
        self.game.ball_vy = 10.0

        self.game.update(0.1)
        # Strike 3 = Out!
        self.assertEqual(self.game.outs, 1)
        self.assertEqual(self.game.strikes, 0)

    def test_07_four_balls_walk_runner_to_first(self):
        self.game.balls = 3
        # Ball thrown outside strike zone (e.g. ball_x = 4.0 < 6.0)
        self.game.ball_active = True
        self.game.ball_x = 4.0
        self.game.ball_y = 14.0
        self.game.ball_vx = 0.0
        self.game.ball_vy = 10.0

        self.game.update(0.1)
        # 4th ball = Walk to 1st base
        self.assertEqual(self.game.balls, 0)
        self.assertTrue(self.game.bases[0]) # 1st base occupied

    def test_08_bat_contact_sweet_spot_home_run(self):
        self.game.ball_active = True
        self.game.ball_x = 7.5
        self.game.ball_y = 12.5
        self.game.ball_vx = 0.0
        self.game.ball_vy = 10.0
        self.game.batter_x = 7.5

        # Swing bat at contact point
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_hit)
        self.assertEqual(self.game.state, STATE_BALL_IN_PLAY)
        self.assertLess(self.game.ball_vy, 0.0) # Flying into outfield

        # Let ball fly into deep outfield (y < 2.0)
        for _ in range(80):
            if self.game.state == STATE_PITCHING:
                break
            self.game.update(0.02)

        # Home run scores
        self.assertGreaterEqual(self.game.score, 1200)

    def test_09_three_outs_ends_half_inning(self):
        self.game.outs = 2
        self.game.strikes = 2
        self.game.ball_active = True
        self.game.ball_x = 7.5
        self.game.ball_y = 14.0
        self.game.ball_vx = 0.0
        self.game.ball_vy = 10.0

        self.game.update(0.1)
        self.assertEqual(self.game.outs, 3)
        self.assertEqual(self.game.state, STATE_INNING_END)

        # Advance through inning transition
        self.game.update(1.6)
        self.assertEqual(self.game.inning, 2)
        self.assertEqual(self.game.outs, 0)
        self.assertEqual(self.game.state, STATE_PITCHING)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.state = STATE_GAME_OVER
        self.game.score = 8000
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PITCHING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.inning, 1)

if __name__ == "__main__":
    unittest.main()
