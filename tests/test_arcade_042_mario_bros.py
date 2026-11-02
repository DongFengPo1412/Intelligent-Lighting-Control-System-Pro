"""
Comprehensive Unit Tests for Arcade Cartridge #042: 水管兄弟 (Mario Bros. 1983 / Nintendo)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_042_mario_bros import (
    Game042MarioBros,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade042MarioBros(unittest.TestCase):
    def setUp(self):
        self.game = Game042MarioBros()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 42)
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "水管兄弟")
        self.assertIn("Mario", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(42)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game042MarioBros)

    def test_initial_state_and_arena_layout(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.pow_hits, 3)
        self.assertEqual(self.game.enemies_defeated, 0)
        self.assertEqual(self.game.player_y, 13.0)
        self.assertTrue(self.game.is_grounded)
        self.assertEqual(len(self.game.enemies), 4)

        # Ground floor platforms check
        self.assertEqual(self.game.platform_grid[14][0], 2)
        self.assertEqual(self.game.platform_grid[15][15], 2)
        # POW block check
        self.assertEqual(self.game.platform_grid[12][7], 3)
        self.assertEqual(self.game.platform_grid[12][8], 3)

    def test_player_run_and_screen_wrap(self):
        self.game.player_x = 15.5
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertLess(self.game.player_x, 1.0)  # Wrapped from right to left

        self.game.player_x = 0.2
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreater(self.game.player_x, 15.0)  # Wrapped from left to right

    def test_player_jump_and_landing(self):
        self.game.player_x = 4.0
        self.game.player_y = 13.0
        self.game.is_grounded = True

        # Press KEY_A to jump
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.is_grounded)
        self.assertLess(self.game.player_vy, 0.0)
        self.assertLess(self.game.player_y, 13.0)

    def test_bump_ceiling_under_enemy_flips_turtle(self):
        # Enemy at x=5.0, standing on y=10.0 (platform y=11)
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["is_flipped"] = False

        # Bump platform under enemy from y=12
        self.game.bump_ceiling(5.0, 11.0)

        self.assertTrue(self.game.enemies[0]["is_flipped"])
        self.assertGreater(self.game.enemies[0]["flip_timer"], 0.0)
        self.assertGreaterEqual(self.game.score, 50)

    def test_pow_block_earthquake_flips_all_enemies(self):
        self.assertEqual(self.game.pow_hits, 3)
        self.game.hit_pow_block()

        self.assertEqual(self.game.pow_hits, 2)
        self.assertGreater(self.game.pow_shake_timer, 0.0)
        self.assertTrue(all(e["is_flipped"] for e in self.game.enemies))
        self.assertEqual(self.game.score, 100)

        # Deplete POW block
        self.game.hit_pow_block()
        self.game.hit_pow_block()
        self.assertEqual(self.game.pow_hits, 0)
        self.assertEqual(self.game.platform_grid[12][7], 0)
        self.assertEqual(self.game.platform_grid[12][8], 0)

    def test_kick_flipped_turtle_defeats_enemy(self):
        # Position flipped enemy right next to player
        self.game.enemies[0]["x"] = 4.0
        self.game.enemies[0]["y"] = 13.0
        self.game.enemies[0]["is_flipped"] = True
        self.game.player_x = 4.0
        self.game.player_y = 13.0

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 1)
        self.assertEqual(self.game.score, prev_score + 200)

    def test_touch_unflipped_turtle_causes_death(self):
        self.game.enemies[0]["x"] = 4.0
        self.game.enemies[0]["y"] = 13.0
        self.game.enemies[0]["is_flipped"] = False
        self.game.player_x = 4.0
        self.game.player_y = 13.0

        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_victory_condition(self):
        self.game.enemies_defeated = 5
        self.game.enemies[0]["x"] = 4.0
        self.game.enemies[0]["y"] = 13.0
        self.game.enemies[0]["is_flipped"] = True
        self.game.player_x = 4.0
        self.game.player_y = 13.0

        self.game.check_collisions()
        self.assertEqual(self.game.enemies_defeated, 6)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check non-empty rendering (ground platform at y=14, x=0 should be blue 41, 128, 185)
        idx = (14 * 16 + 0) * 3
        self.assertEqual(fb[idx + 0], 41)
        self.assertEqual(fb[idx + 1], 128)
        self.assertEqual(fb[idx + 2], 185)


if __name__ == "__main__":
    unittest.main()
