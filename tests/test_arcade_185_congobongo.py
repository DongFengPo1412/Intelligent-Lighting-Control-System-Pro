"""
Unit Tests for Game #185: 丛林大金刚 (Congo Bongo - 1983 Sega)
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
from arcade.game_185_congobongo import (
    Game185CongoBongo,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_HUNTER_KILLED,
    STATE_GAME_OVER,
)

class TestArcade185CongoBongo(unittest.TestCase):
    def setUp(self):
        self.game = Game185CongoBongo()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 185)
        self.assertEqual(self.game.name, "丛林大金刚")
        self.assertEqual(self.game.english_name, "Congo Bongo")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertAlmostEqual(self.game.px, 2.0)
        self.assertAlmostEqual(self.game.py, 14.0)
        self.assertTrue(self.game.bongo_asleep)
        self.assertFalse(self.game.tail_ignited)

    def test_02_movement_and_bounds(self):
        # Move up-right
        init_px = self.game.px
        init_py = self.game.py
        self.game.update(0.1, keys_down=KEY_UP | KEY_RIGHT)
        self.assertGreater(self.game.px, init_px)
        self.assertLess(self.game.py, init_py)

        # Clamping at left boundary
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreaterEqual(self.game.px, 0.5)

    def test_03_jump_button_a_duration(self):
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_jumping)
        self.assertGreater(self.game.jump_timer, 0.0)

        # Advance until jump ends
        for _ in range(35):
            self.game.update(0.016)
        self.assertFalse(self.game.is_jumping)

    def test_04_jumping_leaps_over_rolling_boulders(self):
        self.game.px = 5.0
        self.game.py = 11.0
        # Put boulder on top of hunter
        self.game.boulders = [{"x": 5.0, "y": 11.0, "vx": 0.0, "vy": 0.0}]
        # Player jumps
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_jumping)

        # Update frame: hunter is jumping, should NOT die
        self.game.update(0.016)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

    def test_05_ground_boulder_collision_kills_hunter(self):
        self.game.px = 5.0
        self.game.py = 11.0
        self.game.is_jumping = False
        self.game.boulders = [{"x": 5.0, "y": 11.0, "vx": 0.0, "vy": 0.0}]

        # Hunter is on ground and hit by boulder
        self.game.update(0.016)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_HUNTER_KILLED)

    def test_06_river_log_drifting(self):
        # Place hunter securely on a river log (y = 8.0)
        self.game.logs = [{"x": 5.0, "y": 8.0, "speed": 3.0, "width": 3.0}]
        self.game.px = 6.0
        self.game.py = 8.0
        self.game.is_jumping = False

        init_x = self.game.px
        self.game.update(0.1)
        # Should drift to the right with the log
        self.assertGreater(self.game.px, init_x)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_07_river_water_drowning_without_log(self):
        # Place hunter in river without log
        self.game.logs = [{"x": 0.0, "y": 8.0, "speed": 1.0, "width": 1.0}]
        self.game.px = 12.0 # Far away from log
        self.game.py = 8.0
        self.game.is_jumping = False

        self.game.update(0.016)
        # Should drown in river
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_HUNTER_KILLED)

    def test_08_charging_rhino_patrol_collision(self):
        self.game.px = 7.0
        self.game.py = 5.0
        self.game.rhinos = [{"x": 7.0, "y": 5.0, "vx": 4.0}]

        self.game.update(0.016)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_HUNTER_KILLED)

    def test_09_sneak_summit_ignite_bongo_tail_stage_clear(self):
        # Move hunter close to Bongo at summit (bongo_x=12.0, bongo_y=2.0)
        self.game.px = 11.5
        self.game.py = 2.5
        self.assertTrue(self.game.bongo_asleep)

        # Press KEY_B to light match
        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertTrue(self.game.tail_ignited)
        self.assertFalse(self.game.bongo_asleep)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 3000)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Set game over state
        self.game.state = STATE_GAME_OVER
        self.game.score = 5000
        self.game.update(0.016, keys_pressed=KEY_A)
        # Should reset
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()

