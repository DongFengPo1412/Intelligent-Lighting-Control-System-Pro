# -*- coding: utf-8 -*-
import unittest
from arcade.game_176_alpineski import (
    Game176AlpineSki,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_WIPEOUT,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

class TestArcade176AlpineSki(unittest.TestCase):
    def setUp(self):
        self.game = Game176AlpineSki()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 176)
        self.assertEqual(self.game.name, "高山滑雪")
        self.assertEqual(self.game.english_name, "Alpine Ski")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(self.game.time_left, 0.0)
        self.assertGreater(len(self.game.elements), 0)

    def test_02_steer_left_right_and_clamping(self):
        self.game.px = 7.5
        # Steer Left
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.px, 7.5)

        # Left Clamp
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 2.0)

        # Right Clamp
        for _ in range(50):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.px, 13.0)

    def test_03_tuck_acceleration_increases_speed(self):
        self.game.update(0.01) # Standard speed
        base_spd = self.game.speed

        self.game.update(0.01, keys_down=KEY_A) # Button A tuck
        self.assertGreater(self.game.speed, base_spd)

    def test_04_ski_jump_leap_in_air(self):
        self.assertFalse(self.game.in_air)
        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertTrue(self.game.in_air)
        self.assertGreater(self.game.jump_timer, 0.0)

        # Elapse jump timer
        self.game.update(0.7)
        self.assertFalse(self.game.in_air)

    def test_05_pass_slalom_gate_scores_and_adds_time(self):
        # Place gate at y=11.5, x1=6.0, x2=9.0
        self.game.elements = [{
            "y": 11.5,
            "type": "gate",
            "x": 6.0,
            "x2": 9.0,
            "cleared": False,
        }]
        self.game.px = 7.5
        initial_score = self.game.score
        initial_time = self.game.time_left

        self.game.update(0.05)
        self.assertTrue(self.game.elements[0]["cleared"])
        self.assertGreaterEqual(self.game.score, initial_score + 200)
        self.assertGreater(self.game.time_left, initial_time - 0.05) # Added +2.0 bonus

    def test_06_jump_ramp_launches_skier(self):
        self.game.elements = [{
            "y": 11.5,
            "type": "ramp",
            "x": 7.5,
            "cleared": False,
        }]
        self.game.px = 7.5
        self.assertFalse(self.game.in_air)

        self.game.update(0.05)
        self.assertTrue(self.game.elements[0]["cleared"])
        self.assertTrue(self.game.in_air)
        self.assertGreaterEqual(self.game.score, 300)

    def test_07_rock_collision_causes_wipeout_on_ground(self):
        self.game.elements = [{
            "y": 11.5,
            "type": "rock",
            "x": 7.5,
            "cleared": False,
        }]
        self.game.px = 7.5
        self.game.in_air = False
        initial_lives = self.game.lives

        self.game.update(0.05)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_WIPEOUT)

    def test_08_rock_leap_over_safely_when_in_air(self):
        self.game.elements = [{
            "y": 11.5,
            "type": "rock",
            "x": 7.5,
            "cleared": False,
        }]
        self.game.px = 7.5
        self.game.in_air = True
        self.game.jump_timer = 0.5
        initial_lives = self.game.lives

        self.game.update(0.05)
        # Should fly cleanly over rock without taking damage!
        self.assertEqual(self.game.lives, initial_lives)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_09_finish_line_reaches_stage_clear(self):
        self.game.elements.clear()
        self.game.distance = self.game.target_distance - 0.1

        self.game.update(0.05)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 2000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_WIPEOUT
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
