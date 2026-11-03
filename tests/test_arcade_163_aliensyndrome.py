"""
Unit tests for Game #163: 异型特警 (Alien Syndrome - 1987 Sega / Toru Nakayama)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_163_aliensyndrome import (
    Game163AlienSyndrome,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_EVACUATION, STATE_MISSION_CLEAR, STATE_PLAYER_DIED, STATE_GAME_OVER
)

class TestArcade163AlienSyndrome(unittest.TestCase):
    def setUp(self):
        self.game = Game163AlienSyndrome()

    def test_01_init_state_and_comrades(self):
        """Verify initial state, 4 comrades in cocoons, lives=3, level=1, exit locked."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(len(self.game.comrades), 4)
        self.assertEqual(self.game.comrades_rescued, 0)
        self.assertFalse(self.game.exit_open)
        self.assertFalse(self.game.has_laser)
        self.assertAlmostEqual(self.game.px, 2.0)
        self.assertAlmostEqual(self.game.py, 2.0)

    def test_02_player_movement_and_bounds(self):
        """Test directional movement and clamping inside boundary ribs."""
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.px, 2.0)
        self.assertEqual(self.game.facing_dx, 1.0)

        # Clamping left border
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 1.0)

    def test_03_weapon_firing_blaster(self):
        """Press KEY_A to fire standard blaster bullet with cooldown."""
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.bullets), 1)
        b = self.game.bullets[0]
        self.assertFalse(b["is_laser"])
        self.assertGreater(b["vx"], 0.0)

        # Spam fire blocked by cooldown
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.bullets), 1)

    def test_04_weapon_pod_pickup_laser(self):
        """Touch weapon pod at (8, 4) to collect high-energy piercing laser."""
        self.game.px = 8.0
        self.game.py = 4.0
        self.game.update(0.02)

        self.assertTrue(self.game.has_laser)
        self.assertTrue(self.game.weapon_pods[0]["collected"])
        self.assertGreater(self.game.score, 0)

    def test_05_comrade_rescue_progression(self):
        """Walk over cocoon at (13, 2) to rescue first comrade."""
        old_score = self.game.score
        self.game.px = 13.0
        self.game.py = 2.0
        self.game.update(0.02)

        self.assertTrue(self.game.comrades[0]["rescued"])
        self.assertEqual(self.game.comrades_rescued, 1)
        self.assertGreater(self.game.score, old_score)
        self.assertFalse(self.game.exit_open)

    def test_06_rescue_all_comrades_unlocks_evacuation(self):
        """Rescuing all 4 comrades triggers STATE_EVACUATION and unlocks exit airlock."""
        for c in self.game.comrades:
            self.game.px = c["x"]
            self.game.py = c["y"]
            self.game.update(0.02)

        self.assertEqual(self.game.comrades_rescued, 4)
        self.assertTrue(self.game.exit_open)
        self.assertEqual(self.game.state, STATE_EVACUATION)
        self.assertGreater(self.game.evac_timer, 0.0)

    def test_07_smart_flare_flash_kill(self):
        """Press KEY_B to detonate smart flare destroying nearby aliens."""
        target_alien = self.game.aliens[0]
        target_alien["x"] = 3.0
        target_alien["y"] = 2.0
        self.assertTrue(target_alien["alive"])

        self.game.update(0.02, keys_down=0, keys_pressed=KEY_B)
        self.assertFalse(target_alien["alive"])
        self.assertNotIn(target_alien, self.game.aliens)

    def test_08_evacuation_airlock_escape(self):
        """During evacuation, stepping onto exit airlock triggers mission clear."""
        self.game.exit_open = True
        self.game.state = STATE_EVACUATION
        self.game.px = self.game.exit_x
        self.game.py = self.game.exit_y
        self.game.update(0.02)

        self.assertEqual(self.game.state, STATE_MISSION_CLEAR)
        self.assertGreater(self.game.score, 2000)

    def test_09_alien_contact_costs_life(self):
        """Direct collision with alien bug costs 1 life and triggers death state."""
        self.game.aliens[0]["x"] = self.game.px
        self.game.aliens[0]["y"] = self.game.py
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_DIED)

    def test_10_evac_timeout_death_game_over_and_render(self):
        """Evac countdown expiring causes reactor meltdown; 0 lives triggers game over."""
        self.game.lives = 1
        self.game.state = STATE_EVACUATION
        self.game.evac_timer = 0.1
        self.game.update(0.2)

        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DIED)

        # Let death animation finish
        self.game.update(1.6)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Test frame rendering (768-byte bytearray)
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
