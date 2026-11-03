"""
Unit tests for Game #161: 矿工2049 (Miner 2049er - 1982 Big Five Software / Bill Hogue)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_161_miner2049er import (
    Game161Miner2049er,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_STAGE_CLEAR, STATE_BOB_DIED, STATE_GAME_OVER
)

class TestArcade161Miner2049er(unittest.TestCase):
    def setUp(self):
        self.game = Game161Miner2049er()

    def test_01_init_state_and_platforms(self):
        """Verify initial state, lives=3, level=1, Bob at (1, 13), and initial tile colored."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.level, 1)
        self.assertAlmostEqual(self.game.px, 1.0)
        self.assertAlmostEqual(self.game.py, 13.0)
        self.assertIn((1, 14), self.game.colored_tiles)
        self.assertGreater(self.game.total_claimable, 50)
        self.assertGreater(self.game.coverage_percentage(), 0.0)

    def test_02_walk_horizontal_claims_platform_tiles(self):
        """Moving right across floor 0 claims tiles sequentially and increases score."""
        initial_claimed = len(self.game.colored_tiles)
        initial_score = self.game.score

        # Walk right for several frames
        for _ in range(10):
            self.game.update(0.1, keys_down=KEY_RIGHT)

        self.assertGreater(self.game.px, 1.0)
        self.assertGreater(len(self.game.colored_tiles), initial_claimed)
        self.assertGreater(self.game.score, initial_score)

    def test_03_jump_dynamics_and_landing(self):
        """Press KEY_A, Bob launches upward with gravity arc and lands back on platform."""
        self.assertTrue(self.game.on_ground)
        # Jump
        self.game.update(0.02, keys_down=0, keys_pressed=KEY_A)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.vy, 0.0)

        # Let gravity take over and land
        for _ in range(30):
            self.game.update(0.04)

        self.assertTrue(self.game.on_ground)
        self.assertAlmostEqual(self.game.py, 13.0, delta=0.2)

    def test_04_ladder_climbing(self):
        """Walk to ladder at x=2, press KEY_UP to climb upwards."""
        self.game.px = 2.0
        self.game.py = 13.0
        self.game.update(0.1, keys_down=KEY_UP)
        self.assertTrue(self.game.on_ladder)
        self.assertLess(self.game.py, 13.0)

        # Climb all the way up to platform y=10
        for _ in range(15):
            self.game.update(0.1, keys_down=KEY_UP)
        self.assertLessEqual(self.game.py, 10.0)

    def test_05_radioactive_slide_chute(self):
        """Stepping into slide chute at (14, 6) triggers forced slide down to floor 1."""
        self.game.px = 14.0
        self.game.py = 5.0
        self.game.update(0.05)
        self.assertTrue(self.game.sliding)

        # Let slide finish
        for _ in range(25):
            self.game.update(0.1)

        self.assertFalse(self.game.sliding)
        self.assertAlmostEqual(self.game.py, 9.0, delta=0.5)

    def test_06_mutant_patrol_rebound(self):
        """Mutants move horizontally and reverse at platform boundaries."""
        m = self.game.mutants[0]
        init_vx = m["vx"]
        # Push mutant to max_x
        m["x"] = m["max_x"] + 0.1
        self.game.update(0.05)
        self.assertLess(m["vx"], 0.0) # Reversed to left

    def test_07_mutant_collision_costs_life(self):
        """Bob colliding with mutant loses 1 life and enters STATE_BOB_DIED."""
        self.game.px = self.game.mutants[0]["x"]
        self.game.py = self.game.mutants[0]["y"]
        self.game.update(0.02)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_BOB_DIED)

    def test_08_death_respawn_after_cooldown(self):
        """Bob respawns at starting position when lives remain after timer."""
        self.game.lives = 2
        self.game.state = STATE_BOB_DIED
        self.game.state_timer = 1.0

        self.game.update(1.1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertAlmostEqual(self.game.px, 1.0)
        self.assertAlmostEqual(self.game.py, 13.0)

    def test_09_all_platforms_claimed_stage_clear(self):
        """When all scaffolding tiles are claimed, stage clear is achieved with score bonus."""
        old_score = self.game.score
        # Claim all tiles except the last one
        all_tiles = list(self.game.platforms)
        for t in all_tiles[:-1]:
            self.game._claim_tile(t[0], t[1])

        self.assertEqual(self.game.state, STATE_PLAYING)
        # Claim final tile
        last_t = all_tiles[-1]
        self.game._claim_tile(last_t[0], last_t[1])

        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.coverage_percentage(), 100.0)
        self.assertGreater(self.game.score, old_score + 1000)

    def test_10_game_over_and_rendering(self):
        """When lives drop to 0, transitions to GAME_OVER; frame is 768-byte bytearray."""
        self.game.lives = 0
        self.game.state = STATE_BOB_DIED
        self.game.state_timer = 0.5
        self.game.update(0.6)

        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Render frame
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
