import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_067_snowbros import (
    Game067SnowBros,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    SNOW_NONE,
    SNOW_LIGHT,
    SNOW_MEDIUM,
    SNOW_FULL_BALL,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade067SnowBros(unittest.TestCase):
    def setUp(self):
        self.game = Game067SnowBros()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 67)
        self.assertEqual(self.game.english_name, "Snow Bros.")
        self.assertEqual(self.game.release_year, 1990)
        cart = ArcadeRegistry.get_cartridge(67)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game067SnowBros)

    def test_movement_facing_and_jump(self):
        initial_x = self.game.px
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, initial_x)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.facing, -1)

        # Jump with Button A
        self.assertTrue(self.game.on_ground)
        self.game.update(0.02, KEY_A, 0)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.pvy, 0)

    def test_throw_snow_projectile(self):
        self.assertEqual(len(self.game.shots), 0)
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.shots), 1)
        self.assertGreater(self.game.shots[0]["vx"], 0)

    def test_snow_stages_on_enemy(self):
        enemy = self.game.enemies[0]
        self.assertEqual(enemy["snow_stage"], SNOW_NONE)

        # Hit 1
        self.game.shots.append({"x": enemy["x"], "y": enemy["y"], "vx": 10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(enemy["snow_stage"], SNOW_LIGHT)

        # Hit 2
        self.game.shots.append({"x": enemy["x"], "y": enemy["y"], "vx": 10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(enemy["snow_stage"], SNOW_MEDIUM)

        # Hit 3 -> Full giant snowball
        self.game.shots.append({"x": enemy["x"], "y": enemy["y"], "vx": 10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(enemy["snow_stage"], SNOW_FULL_BALL)

    def test_kick_giant_snowball_into_rolling(self):
        enemy = self.game.enemies[0]
        enemy["snow_stage"] = SNOW_FULL_BALL
        enemy["is_rolling"] = False
        enemy["x"] = 5.0
        enemy["y"] = 14.0

        # Player touches giant snowball from left
        self.game.px = 4.0
        self.game.py = 14.0
        self.game.check_collisions()

        self.assertTrue(enemy["is_rolling"])
        self.assertGreater(enemy["roll_vx"], 0)  # Rolls to the right!
        self.assertGreater(self.game.score, 0)

    def test_rolling_snowball_crushes_other_enemies(self):
        snowball = self.game.enemies[0]
        snowball["is_rolling"] = True
        snowball["x"] = 6.0
        snowball["y"] = 14.0

        target_enemy = self.game.enemies[1]
        target_enemy["x"] = 6.2
        target_enemy["y"] = 14.0
        target_enemy["active"] = True

        self.game.check_collisions()
        self.assertFalse(target_enemy["active"])
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_crushed_enemies_drop_potions(self):
        snowball = self.game.enemies[0]
        snowball["is_rolling"] = True
        snowball["x"] = 6.0
        snowball["y"] = 14.0

        target_enemy = self.game.enemies[1]
        target_enemy["x"] = 6.2
        target_enemy["y"] = 14.0
        target_enemy["active"] = True

        self.game.check_collisions()
        self.assertGreater(len(self.game.potions), 0)

    def test_collecting_potions_enhances_player(self):
        self.assertFalse(self.game.has_speed_potion)
        # Drop Red speed potion on player
        self.game.potions.append({"x": self.game.px, "y": self.game.py, "type": 0, "active": True})
        self.game.check_collisions()
        self.assertTrue(self.game.has_speed_potion)

        # Drop Blue power potion on player
        self.game.potions.append({"x": self.game.px, "y": self.game.py, "type": 1, "active": True})
        self.game.check_collisions()
        self.assertTrue(self.game.has_power_potion)

    def test_unfrozen_enemy_hurts_player(self):
        enemy = self.game.enemies[0]
        enemy["snow_stage"] = SNOW_NONE
        enemy["x"] = self.game.px
        enemy["y"] = self.game.py
        enemy["is_rolling"] = False

        self.game.check_collisions()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_stage_clear_victory_and_render(self):
        self.game.enemies_defeated = 5
        snowball = self.game.enemies[0]
        snowball["is_rolling"] = True
        snowball["x"] = 8.0
        snowball["y"] = 14.0

        target = self.game.enemies[1]
        target["x"] = 8.1
        target["y"] = 14.0
        target["active"] = True

        self.game.check_collisions()
        self.assertEqual(self.game.enemies_defeated, 6)
        self.assertEqual(self.game.state, STATE_VICTORY)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
