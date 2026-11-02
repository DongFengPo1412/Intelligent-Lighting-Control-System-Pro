import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_062_shadowwarriors import (
    Game062ShadowWarriors,
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


class TestArcade062ShadowWarriors(unittest.TestCase):
    def setUp(self):
        self.game = Game062ShadowWarriors()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 62)
        self.assertEqual(self.game.english_name, "Shadow Warriors")
        self.assertEqual(self.game.release_year, 1988)
        cart = ArcadeRegistry.get_cartridge(62)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game062ShadowWarriors)

    def test_movement_and_gravity(self):
        initial_x = self.game.player_x
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, initial_x)

        # Jump
        self.game.update(0.02, KEY_UP, 0)
        self.assertLess(self.game.player_vy, 0.0)

    def test_wall_clinging(self):
        self.game.player_x = 1.0
        self.game.update(0.1, KEY_LEFT | KEY_UP, 0)
        self.assertTrue(self.game.is_wall_clinging)
        self.assertLess(self.game.player_y, 13.0)

    def test_sword_slash(self):
        for e in self.game.enemies:
            e["active"] = False
        target = self.game.enemies[0]
        target["x"] = 3.2
        target["y"] = 13.0
        target["health"] = 1
        target["active"] = True

        self.game.player_x = 2.0
        self.game.player_y = 13.0
        self.game.player_facing = 1

        self.game.update(0.02, KEY_A, 0)
        self.assertTrue(self.game.is_slashing)
        self.assertFalse(target["active"])
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_shadow_clone_mirror_attack(self):
        self.game.num_clones = 1
        for e in self.game.enemies:
            e["active"] = False

        # Player slashes at x=4.0 facing right
        self.game.player_x = 4.0
        self.game.player_y = 13.0
        self.game.update(0.02, KEY_A | KEY_RIGHT, 0)

        # Player runs far away to the right (x > 8.0)
        for _ in range(8):
            self.game.update(0.02, KEY_RIGHT, 0)

        self.assertGreater(self.game.player_x, 5.0)

        # Place target at x=4.8, y=13.0 (in range of clone at x=4.0, out of reach of player)
        target = self.game.enemies[0]
        target["x"] = 4.8
        target["y"] = 13.0
        target["health"] = 1
        target["active"] = True

        # Advance frames so clone at x=4.0 slashes
        for _ in range(6):
            self.game.update(0.02, 0, 0)

        self.assertFalse(target["active"])  # Clone slash killed target!

    def test_summon_ninja_hound(self):
        self.assertFalse(self.game.dog_active)
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.dog_active)
        self.assertGreater(self.game.dog_vx, 0.0)

        # Hound pounces on enemy
        for e in self.game.enemies:
            e["active"] = False
        target = self.game.enemies[0]
        target["x"] = 4.0
        target["y"] = 13.0
        target["health"] = 2
        target["active"] = True

        self.game.dog_x = 3.5
        self.game.update(0.02, 0, 0)
        self.assertFalse(target["active"])  # 2 damage kills health 2
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_add_shadow_clone(self):
        self.assertEqual(self.game.num_clones, 1)
        self.game.add_shadow_clone()
        self.assertEqual(self.game.num_clones, 2)

    def test_player_damage_and_death(self):
        for e in self.game.enemies:
            e["active"] = False
        target = self.game.enemies[0]
        target["x"] = 5.0
        target["y"] = 13.0
        target["active"] = True

        self.game.player_x = 5.0
        self.game.player_y = 13.0
        self.game.player_health = 15

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_stage_clear_victory(self):
        self.game.enemies_defeated = 4
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1200)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 62)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
