import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_064_inthehunt import (
    Game064InTheHunt,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade064InTheHunt(unittest.TestCase):
    def setUp(self):
        self.game = Game064InTheHunt()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 64)
        self.assertEqual(self.game.english_name, "In The Hunt")
        self.assertEqual(self.game.release_year, 1993)
        cart = ArcadeRegistry.get_cartridge(64)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game064InTheHunt)

    def test_submarine_movement_and_clamping(self):
        initial_x = self.game.sub_x
        initial_y = self.game.sub_y
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.sub_x, initial_x)
        self.assertEqual(self.game.sub_facing, 1)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.sub_facing, -1)

        # Bounds test
        for _ in range(50):
            self.game.update(0.1, KEY_UP, 0)
        self.assertGreaterEqual(self.game.sub_y, 3.0)

    def test_torpedo_fire(self):
        self.assertEqual(len(self.game.torpedoes), 0)
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.torpedoes), 1)
        self.assertTrue(self.game.torpedoes[0]["is_player"])
        self.assertGreater(self.game.torpedoes[0]["vx"], 0)

    def test_surface_anti_air_missile_fire(self):
        # When submarine is near surface (y <= 6.0), pressing A fires torpedo AND surface missile
        self.game.sub_y = 4.0
        self.game.shoot_cooldown = 0.0
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.missiles), 1)
        self.assertLess(self.game.missiles[0]["vy"], 0)  # Ascends towards sky

    def test_depth_charge_drop(self):
        self.assertEqual(len(self.game.depth_charges), 0)
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.depth_charges), 1)
        self.assertTrue(self.game.depth_charges[0]["is_player"])
        self.assertGreater(self.game.depth_charges[0]["vy"], 0)  # Descends towards seabed

    def test_torpedo_destroys_enemy_sub(self):
        self.game.enemies = [
            {"x": 6.0, "y": 8.0, "vx": 0.0, "type": 1, "health": 1, "active": True, "shoot_cooldown": 99.0}
        ]
        self.game.sub_x = 2.0
        self.game.sub_y = 8.0
        self.game.shoot_cooldown = 0.0
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.torpedoes), 1)

        # Simulate torpedo moving forward and striking enemy sub
        self.game.torpedoes[0]["x"] = 5.9
        self.game.check_collisions()
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 1)
        self.assertGreater(self.game.score, 0)

    def test_anti_air_missile_destroys_gunboat(self):
        self.game.enemies = [
            {"x": 5.0, "y": 2.0, "vx": 0.0, "type": 0, "health": 1, "active": True, "shoot_cooldown": 99.0}
        ]
        self.game.sub_x = 5.0
        self.game.sub_y = 5.0
        self.game.shoot_cooldown = 0.0
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.missiles), 1)

        # Missile strikes surface boat
        self.game.missiles[0]["x"] = 5.0
        self.game.missiles[0]["y"] = 2.2
        self.game.check_collisions()
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_depth_charge_destroys_sea_mine(self):
        self.game.enemies = [
            {"x": 4.0, "y": 12.0, "vx": 0.0, "type": 2, "health": 1, "active": True, "shoot_cooldown": 99.0}
        ]
        self.game.sub_x = 4.0
        self.game.sub_y = 7.0
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.depth_charges), 1)

        # Depth charge falls on sea mine
        self.game.depth_charges[0]["x"] = 4.0
        self.game.depth_charges[0]["y"] = 11.8
        self.game.check_collisions()
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_boss_spawn_and_defeat(self):
        self.assertFalse(self.game.boss_active)
        self.game.enemies_defeated = 5
        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.boss_active)

        # Damage boss down to 0 health
        self.game.boss_health = 1
        self.game.torpedoes.append({
            "x": self.game.boss_x - 0.5,
            "y": self.game.boss_y,
            "vx": 10.0,
            "vy": 0.0,
            "is_player": True,
            "active": True,
        })
        self.game.check_collisions()
        self.assertFalse(self.game.boss_active)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_player_damage_and_render(self):
        initial_lives = self.game.lives
        # Spawn enemy torpedo right on top of player
        self.game.torpedoes.append({
            "x": self.game.sub_x,
            "y": self.game.sub_y,
            "vx": -10.0,
            "vy": 0.0,
            "is_player": False,
            "active": True,
        })
        self.game.check_collisions()
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_DEAD)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
