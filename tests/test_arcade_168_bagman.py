"""
Unit tests for Game #168: 矿坑逃犯 (Bagman - 1982 Valadon Automation / Stern)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_168_bagman import (
    Game168Bagman,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_STAGE_CLEAR, STATE_BAGMAN_CAUGHT, STATE_GAME_OVER
)

class TestArcade168Bagman(unittest.TestCase):
    def setUp(self):
        self.game = Game168Bagman()

    def test_01_init_state_and_bags(self):
        """Verify initial state, lives=3, mine=1, Bagman at (2, 2), 2 gold bags in deep shaft."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.mine, 1)
        self.assertEqual(self.game.carrying_bag_idx, -1)
        self.assertEqual(len(self.game.bags), 2)
        self.assertEqual(self.game.bags_delivered, 0)
        self.assertAlmostEqual(self.game.px, 2.0)
        self.assertAlmostEqual(self.game.py, 2.0)

    def test_02_bagman_movement_and_ladder_climbing(self):
        """Walk along beam and climb down ladder at x=2 when not carrying bag."""
        self.game.update(0.1, keys_down=KEY_DOWN)
        self.assertGreater(self.game.py, 2.0)

        # Climb back up
        self.game.update(0.1, keys_down=KEY_UP)
        self.assertAlmostEqual(self.game.py, 2.0)

    def test_03_grab_and_drop_gold_bag(self):
        """Press KEY_A near bag to grab it, and press KEY_A again to drop it."""
        b = self.game.bags[0]
        self.game.px = b["x"]
        self.game.py = b["y"]

        # Grab bag
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(self.game.carrying_bag_idx, 0)

        # Drop bag
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(self.game.carrying_bag_idx, -1)
        self.assertAlmostEqual(b["x"], self.game.px)

    def test_04_heavy_gold_halves_speed(self):
        """Carrying gold bag reduces movement distance by 50% compared to empty handed."""
        self.game.px = 2.0
        self.game.py = 2.0
        self.game.update(0.1, keys_down=KEY_RIGHT)
        normal_dist = self.game.px - 2.0

        # Now pick up bag
        self.game.carrying_bag_idx = 0
        self.game.px = 2.0
        self.game.py = 2.0
        self.game.update(0.1, keys_down=KEY_RIGHT)
        burdened_dist = self.game.px - 2.0

        self.assertAlmostEqual(burdened_dist, normal_dist * 0.5, delta=0.05)

    def test_05_heavy_gold_prevents_ladder_climbing(self):
        """Carrying gold bag blocks ladder climbing until dropped."""
        self.game.carrying_bag_idx = 0
        self.game.px = 2.0 # At ladder
        self.game.py = 2.0

        self.game.update(0.1, keys_down=KEY_DOWN)
        self.assertAlmostEqual(self.game.py, 2.0) # Cannot climb down!

    def test_06_drop_bag_stuns_guard(self):
        """Dropping a gold bag onto guard below stuns the guard and awards 300 points."""
        self.game.carrying_bag_idx = 0
        self.game.px = 8.0
        self.game.py = 5.0
        guard = self.game.guards[0]
        guard["x"] = 8.0
        guard["y"] = 6.0
        old_score = self.game.score

        # Drop bag
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertGreater(guard["stunned_timer"], 2.5)
        self.assertEqual(self.game.score, old_score + 300)

    def test_07_pickaxe_guard_stun(self):
        """Collect pickaxe to stun guard on contact for 4.0 seconds (+400 score)."""
        self.game.px = 8.0
        self.game.py = 10.0
        self.game.update(0.02)
        self.assertTrue(self.game.has_pickaxe)

        # Walk into guard with pickaxe
        guard = self.game.guards[1]
        guard["x"] = 8.0
        guard["y"] = 10.0
        old_score = self.game.score

        self.game.update(0.02)
        self.assertGreater(guard["stunned_timer"], 3.0)
        self.assertEqual(self.game.score, old_score + 400)
        self.assertEqual(self.game.lives, 3)

    def test_08_rolling_ore_cart_hit(self):
        """Collision with rolling ore cart on track y=6 costs 1 life."""
        self.game.px = 5.0
        self.game.py = 6.0
        self.game.cart_x = 5.0

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_BAGMAN_CAUGHT)

    def test_09_deliver_all_bags_stage_clear(self):
        """Deliver both gold bags to the surface wheelbarrow, triggering stage clear."""
        # Deliver bag 0
        self.game.carrying_bag_idx = 0
        self.game.px = self.game.wheelbarrow_x
        self.game.py = self.game.wheelbarrow_y
        self.game.update(0.02)

        self.assertEqual(self.game.bags_delivered, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)

        # Deliver bag 1
        self.game.carrying_bag_idx = 1
        self.game.px = self.game.wheelbarrow_x
        self.game.py = self.game.wheelbarrow_y
        old_score = self.game.score
        self.game.update(0.02)

        self.assertEqual(self.game.bags_delivered, 2)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, old_score + 2500)

    def test_10_guard_catch_game_over_and_render(self):
        """Unarmed contact with guard costs life; 0 lives triggers game over; valid render."""
        self.game.lives = 1
        self.game.has_pickaxe = False
        guard = self.game.guards[0]
        guard["x"] = self.game.px
        guard["y"] = self.game.py
        guard["stunned_timer"] = 0.0

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_BAGMAN_CAUGHT)

        # Wait for caught animation
        self.game.update(1.2)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Render frame
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()

