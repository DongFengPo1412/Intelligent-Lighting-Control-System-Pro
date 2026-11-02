import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_055_ninjagaiden import (
    Game055NinjaGaiden,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    ACTION_IDLE,
    ACTION_SLASH,
    ACTION_WALL_JUMP,
    ACTION_BAR_SWING,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade055NinjaGaiden(unittest.TestCase):
    def setUp(self):
        self.game = Game055NinjaGaiden()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 55)
        self.assertEqual(self.game.english_name, "Ninja Gaiden")
        self.assertEqual(self.game.release_year, 1988)
        cart = ArcadeRegistry.get_cartridge(55)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game055NinjaGaiden)

    def test_belt_scroll_movement(self):
        initial_x = self.game.player_x
        # Move right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, initial_x)
        self.assertEqual(self.game.player_facing, 1)

        # Move up
        initial_y = self.game.player_y
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.player_y, initial_y)

    def test_dragon_sword_melee_slash(self):
        for e in self.game.enemies:
            e["active"] = False
        target = self.game.enemies[0]
        target["active"] = True
        target["x"] = 3.2
        target["y"] = 13.0
        target["health"] = 2
        self.game.player_x = 2.0
        self.game.player_y = 13.0
        self.game.player_facing = 1

        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(self.game.action, ACTION_SLASH)
        self.assertEqual(target["health"], 1)
        self.assertGreater(self.game.score, 0)

    def test_crate_pickup_and_throw(self):
        self.game.player_x = 6.0
        self.game.player_y = 13.0
        self.game.crate_x = 6.0
        self.game.crate_y = 13.0
        self.assertFalse(self.game.is_carrying_crate)

        # Pick up crate
        self.game.update(0.02, KEY_A, 0)
        self.assertTrue(self.game.is_carrying_crate)

        # Throw crate forward
        self.game.update(0.02, KEY_A, 0)
        self.assertFalse(self.game.is_carrying_crate)
        self.assertTrue(self.game.crate_thrown)
        self.assertGreater(self.game.crate_vx, 0.0)

    def test_horizontal_pipe_hang_and_whirling_kick(self):
        self.game.player_x = 6.0
        self.game.player_y = 13.0
        self.assertFalse(self.game.is_hanging_bar)

        # Press B beneath bar to grab
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.is_hanging_bar)
        self.assertEqual(self.game.action, ACTION_BAR_SWING)

        # Release into whirling flying kick
        self.game.update(0.02, KEY_A, 0)
        self.assertFalse(self.game.is_hanging_bar)
        self.assertEqual(self.game.action, ACTION_WALL_JUMP)
        self.assertGreater(self.game.player_vx, 0.0)

    def test_wall_triangular_rebound_jump(self):
        self.game.player_x = 1.0  # Near left wall
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(self.game.action, ACTION_WALL_JUMP)
        self.assertGreater(self.game.player_vx, 0.0)  # Rebounds rightward!

    def test_flying_kick_damages_enemies(self):
        self.game.player_x = 5.0
        self.game.player_y = 12.0
        self.game.action = ACTION_WALL_JUMP

        for e in self.game.enemies:
            e["active"] = False
        target = self.game.enemies[0]
        target["active"] = True
        target["x"] = 5.2
        target["y"] = 12.0
        target["health"] = 2

        self.game.update(0.02, 0, 0)
        self.assertFalse(target["active"])  # 2 damage kills health 2
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_enemy_damage_and_player_death(self):
        for e in self.game.enemies:
            e["active"] = False
        target = self.game.enemies[0]
        target["active"] = True
        target["x"] = 5.0
        target["y"] = 13.0
        self.game.player_x = 5.0
        self.game.player_y = 13.0
        self.game.player_health = 10

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_stage_clear_victory(self):
        self.game.enemies_defeated = 4
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 55)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
