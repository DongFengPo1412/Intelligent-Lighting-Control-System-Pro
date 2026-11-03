# -*- coding: utf-8 -*-
import unittest
from arcade.game_180_clowns import (
    Game180Clowns,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_ACROBAT_SPLAT,
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

class TestArcade180Clowns(unittest.TestCase):
    def setUp(self):
        self.game = Game180Clowns()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 180)
        self.assertEqual(self.game.name, "小丑跷跷板")
        self.assertEqual(self.game.english_name, "Clowns")
        self.assertEqual(self.game.release_year, 1977)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(len(self.game.balloons), 0)

    def test_02_seesaw_movement_and_clamping(self):
        self.game.sx = 7.5
        # Move left
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.sx, 7.5)

        # Clamping left
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.sx, 2.5)

        # Clamping right
        for _ in range(50):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.sx, 12.5)

    def test_03_acrobat_gravity_and_trajectory(self):
        self.game.ay = 5.0
        self.game.avy = 0.0
        self.game.update(0.1)
        self.assertGreater(self.game.avy, 0.0) # Gravity increased downwards
        self.assertGreater(self.game.ay, 5.0)

    def test_04_side_wall_bounce(self):
        self.game.ax = 1.1
        self.game.avx = -5.0
        self.game.update(0.05)
        # Bounced off left wall
        self.assertGreater(self.game.avx, 0.0)
        self.assertGreaterEqual(self.game.ax, 1.0)

    def test_05_ceiling_bounce(self):
        self.game.ay = 0.6
        self.game.avy = -6.0
        self.game.update(0.05)
        # Bounced off ceiling
        self.assertGreater(self.game.avy, 0.0)
        self.assertGreaterEqual(self.game.ay, 0.5)

    def test_06_pop_balloon_and_scoring(self):
        # Balloon at (5, 2) is green (+30)
        self.assertIn((5, 2), self.game.balloons)
        self.game.ax = 5.0
        self.game.ay = 2.0
        initial_score = self.game.score
        initial_count = len(self.game.balloons)

        self.game.update(0.01)
        self.assertNotIn((5, 2), self.game.balloons)
        self.assertEqual(len(self.game.balloons), initial_count - 1)
        self.assertEqual(self.game.score, initial_score + 30)

    def test_07_seesaw_landing_and_catapult_launch(self):
        # Seesaw at 7.5, acrobat falling on seesaw (ax=7.5, ay=13.4, avy=5.0)
        self.game.sx = 7.5
        self.game.ax = 7.5
        self.game.ay = 13.4
        self.game.avy = 5.0
        init_tilt = self.game.seesaw_tilt
        initial_score = self.game.score

        self.game.update(0.05)
        # Launched back into air with high upward velocity!
        self.assertLess(self.game.avy, 0.0)
        self.assertNotEqual(self.game.seesaw_tilt, init_tilt)
        self.assertEqual(self.game.score, initial_score + 20)

    def test_08_seesaw_miss_causes_splat_and_life_loss(self):
        # Seesaw far away at 2.5, acrobat falls at 10.0 to floor (ay=15.0)
        self.game.sx = 2.5
        self.game.ax = 10.0
        self.game.ay = 14.8
        self.game.avy = 10.0
        initial_lives = self.game.lives

        self.game.update(0.05)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_ACROBAT_SPLAT)

    def test_09_all_balloons_cleared_stage_clear(self):
        self.game.balloons = {(5, 1)}
        self.game.ax = 5.0
        self.game.ay = 1.0

        self.game.update(0.01)
        self.assertEqual(len(self.game.balloons), 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2500)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_ACROBAT_SPLAT
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
