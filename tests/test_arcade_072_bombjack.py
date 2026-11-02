import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_072_bombjack import (
    Game072BombJack,
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


class TestArcade072BombJack(unittest.TestCase):
    def setUp(self):
        self.game = Game072BombJack()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 72)
        self.assertEqual(self.game.english_name, "Bomb Jack")
        self.assertEqual(self.game.release_year, 1984)
        cart = ArcadeRegistry.get_cartridge(72)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game072BombJack)

    def test_high_altitude_super_jump(self):
        self.assertTrue(self.game.on_ground)
        # Press A on ground
        self.game.update(0.02, KEY_A, 0)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.pvy, -10.0)  # Super jump velocity!

    def test_mid_air_glide_brake(self):
        self.game.py = 8.0
        self.game.on_ground = False
        self.game.pvy = 5.0  # Falling down

        # Tap A in mid-air
        self.game.update(0.02, KEY_A, 0)
        self.assertTrue(self.game.is_gliding)
        self.assertLess(self.game.pvy, 1.0)  # Air brake arrested fall!

    def test_mid_air_dive_stomp(self):
        self.game.py = 8.0
        self.game.on_ground = False
        self.game.pvy = -4.0

        # Press B in mid-air
        self.game.update(0.02, KEY_B, 0)
        self.assertGreater(self.game.pvy, 10.0)  # Rapid dive stomp!

    def test_normal_bomb_collection(self):
        bomb = self.game.bombs[1]  # Unlit bomb
        self.assertFalse(bomb["is_lit"])
        self.game.px = bomb["x"]
        self.game.py = bomb["y"]

        self.game.check_collisions()
        self.assertFalse(bomb["active"])
        self.assertEqual(self.game.combo_multiplier, 1)
        self.assertEqual(self.game.score, 100)

    def test_lit_fuse_bomb_sequential_chain(self):
        lit_bomb = self.game.bombs[0]
        self.assertTrue(lit_bomb["is_lit"])
        self.game.px = lit_bomb["x"]
        self.game.py = lit_bomb["y"]

        self.game.check_collisions()
        self.assertFalse(lit_bomb["active"])
        self.assertEqual(self.game.lit_bombs_collected, 1)
        self.assertEqual(self.game.combo_multiplier, 2)  # Multiplier increases!
        self.assertGreaterEqual(self.game.score, 200)

        # Another bomb should now be lit!
        lit_count = len([b for b in self.game.bombs if b["active"] and b["is_lit"]])
        self.assertEqual(lit_count, 1)

    def test_power_ball_spawn_and_collection(self):
        self.assertFalse(self.game.power_ball_spawned)
        self.game.lit_bombs_collected = 2

        # Collect 3rd lit bomb
        b = self.game.bombs[0]
        b["is_lit"] = True
        self.game.px = b["x"]
        self.game.py = b["y"]
        self.game.check_collisions()

        self.assertTrue(self.game.power_ball_spawned)

        # Collect power ball
        self.game.px = self.game.pb_x
        self.game.py = self.game.pb_y
        self.game.check_collisions()

        self.assertTrue(self.game.power_ball_timer > 0.0)
        self.assertTrue(self.game.enemies[0]["is_frozen"])  # Enemies converted to coins!

    def test_frozen_coin_enemy_consumption(self):
        enemy = self.game.enemies[0]
        enemy["is_frozen"] = True
        self.game.px = enemy["x"]
        self.game.py = enemy["y"]

        self.game.check_collisions()
        self.assertFalse(enemy["active"])
        self.assertGreaterEqual(self.game.score, 500)
        self.assertEqual(self.game.lives, 3)  # No damage taken!

    def test_normal_enemy_collision_death(self):
        enemy = self.game.enemies[0]
        enemy["is_frozen"] = False
        self.game.px = enemy["x"]
        self.game.py = enemy["y"]

        self.game.check_collisions()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_all_bombs_cleared_victory_and_render(self):
        for b in self.game.bombs:
            b["active"] = False

        # One bomb left
        self.game.bombs[0]["active"] = True
        self.game.px = self.game.bombs[0]["x"]
        self.game.py = self.game.bombs[0]["y"]
        self.game.check_collisions()

        self.assertEqual(self.game.get_bombs_remaining(), 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
