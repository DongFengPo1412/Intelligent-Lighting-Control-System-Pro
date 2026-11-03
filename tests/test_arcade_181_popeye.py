# -*- coding: utf-8 -*-
import unittest
from arcade.game_181_popeye import (
    Game181Popeye,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_POPEYE_DEFEATED,
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

class TestArcade181Popeye(unittest.TestCase):
    def setUp(self):
        self.game = Game181Popeye()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 181)
        self.assertEqual(self.game.name, "大力水手")
        self.assertEqual(self.game.english_name, "Popeye")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertTrue(self.game.spinach_available)
        self.assertEqual(self.game.spinach_timer, 0.0)

    def test_02_popeye_lateral_movement_and_bounds(self):
        self.game.px = 7.5
        # Move right
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.px, 7.5)

        # Left Clamp
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 1.0)

    def test_03_ladder_climbing_between_decks(self):
        # Move to left ladder at x=2.0
        self.game.px = 2.0
        self.game.py = 12.0 # Bottom deck
        # Climb Up
        self.game.update(0.2, keys_down=KEY_UP)
        self.assertLess(self.game.py, 12.0)

    def test_04_target_hearts_collected_stage_clear(self):
        self.game.hearts_collected = self.game.target_hearts - 1
        # Place heart directly on Popeye
        self.game.hearts.append({
            "x": self.game.px,
            "y": self.game.py,
            "vx": 0.0,
            "vy": 0.0,
            "on_floor": False,
            "floor_timer": 5.0,
        })
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 2000)

    def test_05_punch_spinach_can_activates_rage(self):
        # Stand near spinach can at (1.0, 8.0)
        self.game.px = 1.2
        self.game.py = 8.0
        self.assertTrue(self.game.spinach_available)
        initial_score = self.game.score

        # Punch (Button A)
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertFalse(self.game.spinach_available)
        self.assertGreater(self.game.spinach_timer, 0.0)
        self.assertEqual(self.game.score, initial_score + 200)

    def test_06_spinach_rage_punches_bluto(self):
        self.game.spinach_timer = 5.0
        self.game.px = 5.0
        self.game.py = 8.0
        self.game.bx = 5.2
        self.game.by = 8.0
        initial_score = self.game.score

        self.game.update(0.01)
        # Bluto punched away and stunned!
        self.assertGreater(self.game.bluto_stun, 0.0)
        self.assertEqual(self.game.score, initial_score + 1000)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_07_bluto_clobbers_unpowered_popeye(self):
        self.game.spinach_timer = 0.0
        self.game.px = 5.0
        self.game.py = 8.0
        self.game.bx = 5.2
        self.game.by = 8.0
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_POPEYE_DEFEATED)

    def test_08_catch_fluttering_heart_scores(self):
        self.game.px = 7.0
        self.game.py = 8.0
        self.game.hearts.append({
            "x": 7.1,
            "y": 8.0,
            "vx": 0.0,
            "vy": 0.0,
            "on_floor": False,
            "floor_timer": 5.0,
        })
        initial_score = self.game.score
        initial_collected = self.game.hearts_collected

        self.game.update(0.01)
        self.assertEqual(self.game.hearts_collected, initial_collected + 1)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_09_spoiled_floor_heart_costs_life(self):
        self.game.hearts = [{
            "x": 10.0,
            "y": 13.0,
            "vx": 0.0,
            "vy": 0.0,
            "on_floor": True,
            "floor_timer": 0.05,
        }]
        self.game.px = 2.0 # Far away
        self.game.py = 4.0
        initial_lives = self.game.lives

        self.game.update(0.1)
        # Heart spoiled, life deducted
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_POPEYE_DEFEATED)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_POPEYE_DEFEATED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
