import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_071_ghostsngoblins import (
    Game071GhostsNGoblins,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    ARMOR_STEEL,
    ARMOR_BOXERS,
    WEAPON_LANCE,
    WEAPON_TORCH,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade071GhostsNGoblins(unittest.TestCase):
    def setUp(self):
        self.game = Game071GhostsNGoblins()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 71)
        self.assertEqual(self.game.english_name, "Ghosts 'n Goblins")
        self.assertEqual(self.game.release_year, 1985)
        cart = ArcadeRegistry.get_cartridge(71)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game071GhostsNGoblins)

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

    def test_duck_and_duck_throw(self):
        self.assertFalse(self.game.is_ducking)
        self.game.update(0.02, KEY_DOWN, 0)
        self.assertTrue(self.game.is_ducking)

        # Throw weapon while ducking
        self.game.update(0.02, KEY_DOWN | KEY_B, KEY_DOWN)
        self.assertEqual(len(self.game.weapons), 1)

    def test_throw_straight_lance(self):
        self.game.weapon_type = WEAPON_LANCE
        self.assertEqual(len(self.game.weapons), 0)
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.weapons), 1)
        self.assertEqual(self.game.weapons[0]["type"], WEAPON_LANCE)
        self.assertGreater(self.game.weapons[0]["vx"], 0)
        self.assertEqual(self.game.weapons[0]["vy"], 0)

    def test_throw_torch_creates_ground_flame(self):
        self.game.weapon_type = WEAPON_TORCH
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.weapons), 1)
        self.assertLess(self.game.weapons[0]["vy"], 0)  # Lobbed arc

        # Simulate torch falling to ground
        self.game.weapons[0]["y"] = 14.0
        self.game.weapons[0]["vy"] = 5.0
        self.game.update_weapons(0.02)
        self.assertEqual(len(self.game.flames), 1)
        self.assertGreater(self.game.flames[0]["duration"], 1.0)

    def test_first_hit_breaks_armor_to_boxers(self):
        self.assertEqual(self.game.armor_stage, ARMOR_STEEL)
        enemy = self.game.enemies[0]
        enemy["x"] = self.game.px
        enemy["y"] = self.game.py

        self.game.check_collisions()
        # Armor shattered, Arthur enters boxers! Still has 3 lives!
        self.assertEqual(self.game.armor_stage, ARMOR_BOXERS)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_second_hit_in_boxers_is_fatal(self):
        self.game.armor_stage = ARMOR_BOXERS
        enemy = self.game.enemies[0]
        enemy["x"] = self.game.px
        enemy["y"] = self.game.py

        self.game.check_collisions()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_collecting_armor_jar_restores_steel_armor(self):
        self.game.armor_stage = ARMOR_BOXERS
        self.game.armor_drop_active = True
        self.game.armor_drop_x = self.game.px
        self.game.armor_drop_y = self.game.py

        self.game.check_collisions()
        self.assertFalse(self.game.armor_drop_active)
        self.assertEqual(self.game.armor_stage, ARMOR_STEEL)
        self.assertGreater(self.game.score, 0)

    def test_red_arremer_two_hits_and_score(self):
        arremer = self.game.enemies[3]
        self.assertEqual(arremer["type"], 1)
        self.assertEqual(arremer["health"], 2)

        # Hit 1
        self.game.weapons.append({"x": arremer["x"], "y": arremer["y"], "vx": 10.0, "vy": 0.0, "type": 0, "active": True})
        self.game.check_collisions()
        self.assertEqual(arremer["health"], 1)
        self.assertTrue(arremer["active"])

        # Hit 2
        self.game.weapons.append({"x": arremer["x"], "y": arremer["y"], "vx": 10.0, "vy": 0.0, "type": 0, "active": True})
        self.game.check_collisions()
        self.assertFalse(arremer["active"])
        self.assertGreaterEqual(self.game.score, 500)

    def test_stage_clear_victory_and_render(self):
        self.game.enemies_defeated = 7
        enemy = self.game.enemies[0]
        self.game.weapons.append({"x": enemy["x"], "y": enemy["y"], "vx": 10.0, "vy": 0.0, "type": 0, "active": True})
        self.game.check_collisions()

        self.assertEqual(self.game.enemies_defeated, 8)
        self.assertEqual(self.game.state, STATE_VICTORY)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
