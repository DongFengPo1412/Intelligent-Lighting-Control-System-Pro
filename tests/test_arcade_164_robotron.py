"""
Unit tests for Game #164: 机器人大战2084 (Robotron: 2084 - 1982 Williams / Eugene Jarvis & Larry DeMar)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_164_robotron import (
    Game164Robotron,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_WAVE_CLEAR, STATE_PLAYER_DIED, STATE_GAME_OVER
)

class TestArcade164Robotron(unittest.TestCase):
    def setUp(self):
        self.game = Game164Robotron()

    def test_01_init_state_and_entities(self):
        """Verify initial state, lives=3, wave=1, 3 humans, 2 hulks, grunts active, player at (7.5, 7.5)."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.wave, 1)
        self.assertEqual(len(self.game.humans), 3)
        self.assertEqual(len(self.game.hulks), 2)
        self.assertGreater(len(self.game.grunts), 5)
        self.assertAlmostEqual(self.game.px, 7.5)
        self.assertAlmostEqual(self.game.py, 7.5)

    def test_02_omnidirectional_movement_and_aim(self):
        """Moving orthogonal or diagonal updates position and calculates normalized facing vector."""
        self.game.update(0.1, keys_down=(KEY_UP | KEY_RIGHT))
        self.assertGreater(self.game.px, 7.5)
        self.assertLess(self.game.py, 7.5)
        self.assertGreater(self.game.facing_dx, 0.0)
        self.assertLess(self.game.facing_dy, 0.0)

    def test_03_laser_firing_and_cooldown(self):
        """Press KEY_A to fire laser in current facing direction with cooldown."""
        self.game.facing_dx = 1.0
        self.game.facing_dy = 0.0
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)

        self.assertEqual(len(self.game.lasers), 1)
        l = self.game.lasers[0]
        self.assertGreater(l["vx"], 0.0)
        self.assertAlmostEqual(l["vy"], 0.0)

        # Cooldown prevents immediate rapid fire
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.lasers), 1)

    def test_04_human_rescue_bonus(self):
        """Touch civilian human to rescue them and award 1000 points."""
        h = self.game.humans[0]
        self.game.px = h["x"]
        self.game.py = h["y"]
        old_score = self.game.score

        self.game.update(0.02)
        self.assertTrue(h["rescued"])
        self.assertEqual(self.game.score, old_score + 1000)

    def test_05_hulk_crushes_human(self):
        """Indestructible Hulk walking over human crushes and kills them."""
        h = self.game.humans[1]
        hlk = self.game.hulks[0]
        hlk["x"] = h["x"]
        hlk["y"] = h["y"]
        self.assertTrue(h["alive"])

        self.game.update(0.02)
        self.assertFalse(h["alive"])

    def test_06_laser_knocks_back_hulk(self):
        """Shooting an indestructible Hulk pushes it back without destroying it."""
        hlk = self.game.hulks[0]
        hlk["x"] = 5.0
        hlk["y"] = 5.0
        initial_x = hlk["x"]

        # Bullet moving right towards Hulk
        self.game.lasers.append({
            "x": 4.9, "y": 5.0, "vx": 16.0, "vy": 0.0, "life": 0.5
        })
        self.game.update(0.02)

        # Hulk was knocked back to the right
        self.assertGreater(hlk["x"], initial_x)
        self.assertEqual(len(self.game.lasers), 0)

    def test_07_laser_kills_grunt(self):
        """Shooting a Grunt robot destroys it and awards 100 score."""
        g = self.game.grunts[0]
        g["x"] = 8.0
        g["y"] = 8.0
        old_score = self.game.score

        self.game.lasers.append({
            "x": 8.0, "y": 8.0, "vx": 0.0, "vy": 16.0, "life": 0.5
        })
        self.game.update(0.02)

        self.assertFalse(g["alive"])
        self.assertEqual(self.game.score, old_score + 100)

    def test_08_emp_clears_all_grunts(self):
        """Trigger KEY_B to detonate EMP, consuming charge and killing all Grunts."""
        self.assertEqual(self.game.emp_charges, 1)
        self.game.update(0.02, keys_down=0, keys_pressed=KEY_B)

        self.assertEqual(self.game.emp_charges, 0)
        for g in self.game.grunts:
            self.assertFalse(g["alive"])

    def test_09_all_grunts_dead_wave_clear(self):
        """When all Grunts are eliminated, triggers STATE_WAVE_CLEAR and wave advances."""
        for g in self.game.grunts:
            g["alive"] = False

        self.game.update(0.02)
        self.assertEqual(self.game.state, STATE_WAVE_CLEAR)

        # Advance wave
        self.game.update(1.6)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.wave, 2)

    def test_10_hulk_or_grunt_kills_player_game_over_render(self):
        """Direct contact with Hulk or Grunt costs life; 0 lives triggers game over."""
        self.game.lives = 1
        hlk = self.game.hulks[0]
        hlk["x"] = self.game.px
        hlk["y"] = self.game.py

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DIED)

        # Death cooldown to game over
        self.game.update(1.1)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Test frame rendering
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
