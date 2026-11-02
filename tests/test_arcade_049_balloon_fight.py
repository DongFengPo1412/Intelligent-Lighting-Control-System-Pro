"""
Comprehensive Unit Tests for Arcade Cartridge #049: 气球大战 (Balloon Fight 1984 / Nintendo)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_049_balloon_fight import (
    Game049BalloonFight,
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


class TestArcade049BalloonFight(unittest.TestCase):
    def setUp(self):
        self.game = Game049BalloonFight()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 49)
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "气球大战")
        self.assertIn("Balloon Fight", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(49)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game049BalloonFight)

    def test_initial_state_and_arena(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.player_balloons, 2)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.enemies_defeated, 0)
        self.assertEqual(self.game.get_enemies_remaining(), 4)
        self.assertEqual(len(self.game.enemies), 3)
        self.assertEqual(len(self.game.sparks), 2)

    def test_flapping_and_gravity(self):
        self.assertEqual(self.game.player_vy, 0.0)
        # Tap KEY_A to flap
        self.game.update(0.05, KEY_A, 0)
        self.assertLess(self.game.player_vy, 0.0)

        # Release to let gravity pull down
        for _ in range(15):
            self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.player_vy, 0.0)

    def test_horizontal_air_drift_and_screen_wrap(self):
        self.game.player_x = 15.5
        for _ in range(10):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertLess(self.game.player_x, 2.0)  # Wrapped right to left

    def test_platform_landing(self):
        # Platform at row 7 (cols 2..5)
        self.game.player_x = 3.0
        self.game.player_y = 6.2
        self.game.player_vy = 3.0

        self.game.update(0.05, 0, 0)
        # Settles onto platform
        self.assertAlmostEqual(self.game.player_y, 6.4, places=1)
        self.assertEqual(self.game.player_vy, 0.0)

    def test_higher_altitude_pops_enemy_balloon(self):
        # Position player above enemy 0
        self.game.player_x = 5.0
        self.game.player_y = 4.5  # Higher than enemy (lower y)
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 5.0
        self.game.enemies[0]["balloons"] = 1
        self.game.enemies[0]["on_parachute"] = False

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertEqual(self.game.enemies[0]["balloons"], 0)
        self.assertTrue(self.game.enemies[0]["on_parachute"])
        self.assertLess(self.game.player_vy, 0.0)  # Rebound upward
        self.assertGreater(self.game.score, prev_score)

    def test_lower_altitude_pops_player_balloon(self):
        # Position player below enemy 0
        self.game.player_x = 5.0
        self.game.player_y = 5.5  # Lower than enemy (higher y)
        self.game.player_balloons = 2
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 5.0

        self.game.check_collisions()
        # Lost 1 balloon
        self.assertEqual(self.game.player_balloons, 1)

    def test_zero_balloons_causes_player_death(self):
        self.game.player_x = 5.0
        self.game.player_y = 5.5
        self.game.player_balloons = 1
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 5.0

        self.game.check_collisions()
        self.assertEqual(self.game.player_balloons, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_kicking_parachuting_enemy_eliminates_thug(self):
        self.game.player_x = 5.0
        self.game.player_y = 4.5
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 5.0
        self.game.enemies[0]["balloons"] = 0
        self.game.enemies[0]["on_parachute"] = True
        self.game.enemies[0]["active"] = True

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 1)
        self.assertEqual(self.game.score, prev_score + 200)

    def test_water_splash_causes_death(self):
        self.game.player_y = 14.6
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_spark_collision_causes_death(self):
        self.game.player_x = 5.0
        self.game.player_y = 5.0
        self.game.sparks[0]["x"] = 5.0
        self.game.sparks[0]["y"] = 5.0
        self.game.sparks[0]["active"] = True

        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_victory_condition(self):
        self.game.enemies_defeated = 3
        self.game.player_x = 5.0
        self.game.player_y = 4.5
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 5.0
        self.game.enemies[0]["balloons"] = 0
        self.game.enemies[0]["on_parachute"] = True
        self.game.enemies[0]["active"] = True

        self.game.check_collisions()
        self.assertEqual(self.game.enemies_defeated, 4)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check water at row 15, col 0: Royal Blue (26, 82, 118)
        idx = (15 * 16 + 0) * 3
        self.assertEqual(fb[idx + 0], 26)
        self.assertEqual(fb[idx + 1], 82)
        self.assertEqual(fb[idx + 2], 118)
        # Check platform grass at row 7, col 2: Emerald Green (46, 204, 113)
        p_idx = (7 * 16 + 2) * 3
        self.assertEqual(fb[p_idx + 0], 46)
        self.assertEqual(fb[p_idx + 1], 204)
        self.assertEqual(fb[p_idx + 2], 113)


if __name__ == "__main__":
    unittest.main()
