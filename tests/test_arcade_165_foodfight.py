"""
Unit tests for Game #165: 食物大战 (Food Fight - 1983 Atari / General Computer Corporation)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_165_foodfight import (
    Game165FoodFight,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_STAGE_CLEAR, STATE_CHARLEY_SPLAT, STATE_GAME_OVER
)

class TestArcade165FoodFight(unittest.TestCase):
    def setUp(self):
        self.game = Game165FoodFight()

    def test_01_init_state_and_cone(self):
        """Verify initial state, lives=3, level=1, Charley at (2, 8), cone at (14, 8)."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.food_ammo, 0)
        self.assertAlmostEqual(self.game.px, 2.0)
        self.assertAlmostEqual(self.game.py, 8.0)
        self.assertAlmostEqual(self.game.cone_x, 14.0)
        self.assertAlmostEqual(self.game.cone_y, 8.0)
        self.assertGreater(self.game.melt_timer, 10.0)

    def test_02_charley_movement_and_clamping(self):
        """Test directional movement and arena boundary clamping without interference."""
        self.game.chefs.clear()
        self.game.update(0.1, keys_down=KEY_UP)
        self.assertLess(self.game.py, 8.0)
        self.assertEqual(self.game.facing_dy, -1.0)

        # Clamp top
        for _ in range(40):
            self.game.update(0.1, keys_down=KEY_UP)
        self.assertEqual(self.game.py, 1.0)

        # Clamp left
        for _ in range(40):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 1.0)

    def test_03_food_pile_ammo_reload(self):
        """Step over food pile at (6, 4) to load up to 4 food ammo."""
        self.game.px = 6.0
        self.game.py = 4.0
        old_rem = self.game.food_piles[0]["remaining"]

        self.game.update(0.02)
        self.assertEqual(self.game.food_ammo, 4)
        self.assertEqual(self.game.food_piles[0]["remaining"], old_rem - 4)
        self.assertGreater(self.game.score, 0)

    def test_04_throw_food_projectile(self):
        """Press KEY_A with loaded ammo to hurl food projectile."""
        self.game.food_ammo = 2
        self.game.facing_dx = 1.0
        self.game.facing_dy = 0.0

        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(self.game.food_ammo, 1)
        self.assertEqual(len(self.game.projectiles), 1)
        p = self.game.projectiles[0]
        self.assertTrue(p["is_player"])
        self.assertGreater(p["vx"], 0.0)

    def test_05_splat_and_stun_chef(self):
        """Food projectile hitting chef stuns them for 3.0 seconds and awards 200 points."""
        chef = self.game.chefs[0]
        chef["x"] = 8.0
        chef["y"] = 8.0
        self.game.projectiles.append({
            "x": 8.0, "y": 8.0, "vx": 14.0, "vy": 0.0, "is_player": True
        })
        old_score = self.game.score

        self.game.update(0.02)
        self.assertGreater(chef["stunned_timer"], 2.5)
        self.assertEqual(self.game.score, old_score + 200)

    def test_06_chef_food_projectile_hits_charley(self):
        """Chef projectile hitting Charley causes splat and costs 1 life."""
        self.game.projectiles.append({
            "x": self.game.px, "y": self.game.py, "vx": 0.0, "vy": 8.0, "is_player": False
        })
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_CHARLEY_SPLAT)

    def test_07_eat_ice_cream_stage_clear(self):
        """Reaching ice cream cone triggers stage clear with time bonus."""
        self.game.px = self.game.cone_x
        self.game.py = self.game.cone_y
        self.game.update(0.02)

        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 1000)

    def test_08_ice_cream_meltdown_death(self):
        """If melt timer runs out before reaching cone, Charley loses a life."""
        self.game.melt_timer = 0.05
        self.game.update(0.1)

        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_CHARLEY_SPLAT)

    def test_09_chef_contact_costs_life(self):
        """Direct physical collision with chef costs 1 life."""
        chef = self.game.chefs[0]
        chef["x"] = self.game.px
        chef["y"] = self.game.py
        chef["stunned_timer"] = 0.0

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_CHARLEY_SPLAT)

    def test_10_game_over_and_rendering(self):
        """At 0 lives transitions to STATE_GAME_OVER; frame is 768-byte bytearray."""
        self.game.lives = 1
        self.game.melt_timer = 0.05
        self.game.update(0.1)

        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_CHARLEY_SPLAT)

        # Let splat animation conclude
        self.game.update(1.3)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Test frame rendering
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
