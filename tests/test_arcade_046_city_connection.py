"""
Comprehensive Unit Tests for Arcade Cartridge #046: 城市快车 (City Connection 1985 / Jaleco)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_046_city_connection import (
    Game046CityConnection,
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


class TestArcade046CityConnection(unittest.TestCase):
    def setUp(self):
        self.game = Game046CityConnection()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 46)
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "城市快车")
        self.assertIn("City Connection", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(46)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game046CityConnection)

    def test_initial_state_and_highways(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.oil_ammo, 6)
        self.assertEqual(self.game.unpainted_tiles, 64)
        self.assertEqual(self.game.player_tier, 3)
        self.assertFalse(self.game.is_jumping)
        self.assertEqual(len(self.game.police), 3)

    def test_highway_painting_and_score(self):
        self.assertFalse(self.game.painted[3][1])
        # Player at x=1.0, tier=3
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.painted[3][1])
        self.assertEqual(self.game.unpainted_tiles, 63)
        self.assertEqual(self.game.score, 10)

    def test_jump_physics_and_leap_to_upper_tier(self):
        self.game.player_tier = 3
        # Press KEY_A to jump
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertGreater(self.game.jump_y_offset, 0.0)

        # In mid-air peak, press KEY_UP
        self.game.jump_y_offset = 3.9
        self.game.jump_vy = 2.0
        self.game.update(0.05, KEY_UP, 0)

        # Leaped to tier 2!
        self.assertEqual(self.game.player_tier, 2)
        self.assertFalse(self.game.is_jumping)

    def test_tier_drop_down(self):
        self.game.player_tier = 1
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.player_tier, 2)

    def test_fire_oil_can_and_dizzy_police(self):
        self.assertEqual(self.game.oil_ammo, 6)
        self.game.player_x = 5.0
        self.game.player_tier = 2
        self.game.player_dir = 1

        # Place police car at x=8.0, tier 2
        self.game.police[2]["x"] = 8.0
        self.game.police[2]["tier"] = 2
        self.game.police[2]["is_dizzy"] = False

        # Fire oil can (KEY_B)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.oil_ammo, 5)
        self.assertEqual(len(self.game.oil_shots), 1)

        # Advance oil can until it hits police
        for _ in range(10):
            self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.police[2]["is_dizzy"])
        self.assertGreater(self.game.police[2]["dizzy_timer"], 0.0)
        self.assertGreaterEqual(self.game.score, 50)

    def test_ram_dizzy_police_knocks_off_overpass(self):
        self.game.player_x = 5.0
        self.game.player_tier = 2
        self.game.police[2]["x"] = 5.0
        self.game.police[2]["tier"] = 2
        self.game.police[2]["active"] = True
        self.game.police[2]["is_dizzy"] = True

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.police[2]["active"])
        self.assertEqual(self.game.score, prev_score + 100)

    def test_collision_with_active_police_causes_crash(self):
        self.game.player_x = 5.0
        self.game.player_tier = 2
        self.game.police[2]["x"] = 5.0
        self.game.police[2]["tier"] = 2
        self.game.police[2]["active"] = True
        self.game.police[2]["is_dizzy"] = False

        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_victory_condition(self):
        # Paint almost all tiles
        self.game.unpainted_tiles = 1
        for t in range(4):
            for c in range(16):
                self.game.painted[t][c] = True
        self.game.painted[3][5] = False

        self.game.player_x = 5.0
        self.game.player_tier = 3
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.unpainted_tiles, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check dark asphalt at tier 0 (y=3, x=0): (52, 73, 94)
        idx = (3 * 16 + 0) * 3
        self.assertEqual(fb[idx + 0], 52)
        self.assertEqual(fb[idx + 1], 73)
        self.assertEqual(fb[idx + 2], 94)


if __name__ == "__main__":
    unittest.main()
