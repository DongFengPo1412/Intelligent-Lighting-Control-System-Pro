"""
Unit tests for Game #167: 水晶城堡 (Crystal Castles - 1983 Atari / Franz Lanzinger)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_167_crystalcastles import (
    Game167CrystalCastles,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_STAGE_CLEAR, STATE_BENTLEY_DIED, STATE_GAME_OVER
)

class TestArcade167CrystalCastles(unittest.TestCase):
    def setUp(self):
        self.game = Game167CrystalCastles()

    def test_01_init_state_and_gems(self):
        """Verify initial state, lives=3, castle=1, 12 gems uncollected, honey pot active."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.castle, 1)
        self.assertEqual(self.game.remaining_gems_count(), 12)
        self.assertTrue(self.game.honey_pot["active"])
        self.assertFalse(self.game.is_jumping)
        self.assertAlmostEqual(self.game.px, 2.0)
        self.assertAlmostEqual(self.game.py, 13.0)

    def test_02_bentley_movement_and_clamping(self):
        """Test 4-directional movement and boundary clamping."""
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.px, 2.0)

        for _ in range(40):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 1.0)

    def test_03_jump_dynamics(self):
        """Press KEY_A to initiate vertical jump arc."""
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.vy, 0.0)

        # Let jump complete
        for _ in range(25):
            self.game.update(0.04)
        self.assertFalse(self.game.is_jumping)

    def test_04_archway_portal_warp(self):
        """Press KEY_B near lower archway (1.5, 13) teleports to summit archway (3.0, 1.5)."""
        self.game.px = 1.5
        self.game.py = 13.0
        self.game.update(0.02, keys_down=0, keys_pressed=KEY_B)

        self.assertAlmostEqual(self.game.px, 3.0)
        self.assertAlmostEqual(self.game.py, 1.5)

    def test_05_gem_collection_and_last_gem_bonus(self):
        """Collect gems; last gem awards 500 bonus and triggers stage clear."""
        # Collect first 11 gems
        for g in self.game.gems[:-1]:
            g["collected"] = True

        self.assertEqual(self.game.remaining_gems_count(), 1)
        last_g = self.game.gems[-1]
        self.game.px = last_g["x"]
        self.game.py = last_g["y"]
        old_score = self.game.score

        self.game.update(0.02)
        self.assertTrue(last_g["collected"])
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, old_score + 2000)

    def test_06_honey_pot_invulnerability(self):
        """Collect honey pot at (8, 1), grants 4.0s invulnerability timer."""
        self.game.px = self.game.honey_pot["x"]
        self.game.py = self.game.honey_pot["y"]
        self.game.update(0.02)

        self.assertFalse(self.game.honey_pot["active"])
        self.assertGreater(self.game.invulnerable_timer, 3.5)

    def test_07_jump_on_gem_eater_stomp(self):
        """Jumping onto crawling Gem Eater stomps it for 500 score."""
        self.game.gem_eater["x"] = 5.0
        self.game.gem_eater["y"] = 9.0
        self.game.px = 5.0
        self.game.py = 9.0
        self.game.is_jumping = True
        old_score = self.game.score

        self.game.update(0.02)
        self.assertFalse(self.game.gem_eater["alive"])
        self.assertEqual(self.game.score, old_score + 500)

    def test_08_invulnerable_banish_witch(self):
        """While invulnerable, touching Berthilda the Witch banishes her for 3000 score."""
        self.game.invulnerable_timer = 3.0
        self.game.witch["x"] = 8.0
        self.game.witch["y"] = 5.0
        self.game.px = 8.0
        self.game.py = 5.0
        old_score = self.game.score

        self.game.update(0.02)
        self.assertFalse(self.game.witch["alive"])
        self.assertEqual(self.game.score, old_score + 3000)

    def test_09_witch_or_caterpillar_touch_costs_life(self):
        """Normal contact without jumping or invulnerability costs life."""
        self.game.witch["x"] = self.game.px
        self.game.witch["y"] = self.game.py
        self.game.invulnerable_timer = 0.0
        self.game.is_jumping = False

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_BENTLEY_DIED)

    def test_10_game_over_and_rendering(self):
        """At 0 lives transitions to STATE_GAME_OVER; frame is 768-byte bytearray."""
        self.game.lives = 1
        self.game.witch["x"] = self.game.px
        self.game.witch["y"] = self.game.py
        self.game.invulnerable_timer = 0.0
        self.game.is_jumping = False
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 0)
        self.game.update(1.2)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Render frame
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
