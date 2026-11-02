"""
Comprehensive Unit Tests for Arcade Cartridge #047: 热血快打 / 双截龙街机版 (Double Dragon 1987 / Technos)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_047_double_dragon import (
    Game047DoubleDragon,
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


class TestArcade047DoubleDragon(unittest.TestCase):
    def setUp(self):
        self.game = Game047DoubleDragon()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 47)
        self.assertEqual(self.game.release_year, 1987)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "热血快打")
        self.assertIn("Double Dragon", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(47)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game047DoubleDragon)

    def test_initial_state_and_arena(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.player_health, 100)
        self.assertEqual(self.game.enemies_defeated, 0)
        self.assertEqual(self.game.get_enemies_remaining(), 4)
        self.assertFalse(self.game.has_weapon)
        self.assertTrue(self.game.weapon["on_ground"])
        self.assertEqual(len(self.game.enemies), 3)

    def test_player_movement_and_street_bounds(self):
        # Walk up towards brick wall - clamped to y >= 8.0
        for _ in range(20):
            self.game.update(0.1, KEY_UP, 0)
        self.assertGreaterEqual(self.game.player_y, 8.0)

        # Walk down towards street edge - clamped to y <= 14.0
        for _ in range(20):
            self.game.update(0.1, KEY_DOWN, 0)
        self.assertLessEqual(self.game.player_y, 14.0)

    def test_punch_and_kick_moves(self):
        # KEY_A = Punch
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.attack_type, 1)
        self.assertGreater(self.game.attack_timer, 0.0)

        # Cool down
        self.game.attack_timer = 0.0

        # KEY_B = Kick
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.attack_type, 2)

    def test_elbow_smash_simultaneous_press(self):
        self.game.attack_timer = 0.0
        # KEY_A + KEY_B = Elbow
        self.game.update(0.05, KEY_A | KEY_B, 0)
        self.assertEqual(self.game.attack_type, 3)

    def test_weapon_pickup_enhances_combat(self):
        self.assertFalse(self.game.has_weapon)
        # Walk directly onto dropped bat at (7.0, 10.0)
        self.game.player_x = 7.0
        self.game.player_y = 10.0
        self.game.weapon["on_ground"] = True

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.has_weapon)
        self.assertFalse(self.game.weapon["on_ground"])
        self.assertGreaterEqual(self.game.score, 50)

    def test_attack_damages_enemy_and_causes_knockdown(self):
        # Place enemy right in front of player
        self.game.player_x = 5.0
        self.game.player_y = 10.0
        self.game.player_facing = 1
        self.game.enemies[0]["x"] = 5.8
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["health"] = 30
        self.game.enemies[0]["is_knocked_down"] = False

        prev_score = self.game.score
        # Kick attack
        self.game.attack_kick()
        self.game.check_hitboxes()

        self.assertLess(self.game.enemies[0]["health"], 30)
        self.assertTrue(self.game.enemies[0]["is_knocked_down"])
        self.assertGreater(self.game.score, prev_score)

    def test_enemy_attacks_player_and_causes_death(self):
        self.game.player_health = 10
        self.game.player_x = 5.0
        self.game.player_y = 10.0
        self.game.enemies[0]["x"] = 5.2
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["attack_cooldown"] = 0.0

        self.game.update_enemies(0.05)
        self.assertEqual(self.game.player_health, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_victory_condition(self):
        self.game.enemies_defeated = 3
        self.game.player_x = 5.0
        self.game.player_y = 10.0
        self.game.player_facing = 1
        self.game.enemies[0]["x"] = 5.8
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["health"] = 5  # Low HP
        self.game.enemies[0]["is_knocked_down"] = False

        self.game.attack_kick()
        self.game.check_hitboxes()

        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 4)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check brick wall at (0, 0): (50, 20, 20)
        idx = (0 * 16 + 0) * 3
        # Row 0 has health bar at x:0..7 (46, 204, 113)
        self.assertEqual(fb[idx + 0], 46)
        self.assertEqual(fb[idx + 1], 204)
        self.assertEqual(fb[idx + 2], 113)
        # Check asphalt ground at row 12, col 0: (30, 35, 40)
        g_idx = (12 * 16 + 0) * 3
        self.assertEqual(fb[g_idx + 0], 30)
        self.assertEqual(fb[g_idx + 1], 35)
        self.assertEqual(fb[g_idx + 2], 40)


if __name__ == "__main__":
    unittest.main()
