import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_057_wonderboy import (
    Game057WonderBoy,
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


class TestArcade057WonderBoy(unittest.TestCase):
    def setUp(self):
        self.game = Game057WonderBoy()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 57)
        self.assertEqual(self.game.english_name, "Wonder Boy")
        self.assertEqual(self.game.release_year, 1986)
        cart = ArcadeRegistry.get_cartridge(57)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game057WonderBoy)

    def test_movement_and_jump(self):
        initial_x = self.game.player_x
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, initial_x)

        # Jump
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.player_vy, 0.0)

    def test_vitality_depletion_and_starvation(self):
        self.game.vitality = 1
        self.game.vitality_timer = 1.19
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.vitality, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_fruit_eating_restores_vitality(self):
        self.game.vitality = 5
        self.game.fruits[0]["x"] = 2.0
        self.game.fruits[0]["y"] = 13.0
        self.game.fruits[0]["type"] = 0  # Banana
        self.game.fruits[0]["active"] = True
        self.game.player_x = 2.0
        self.game.player_y = 13.0

        self.game.update(0.02, 0, 0)
        self.assertFalse(self.game.fruits[0]["active"])
        self.assertEqual(self.game.vitality, 8)  # 5 + 3 = 8
        self.assertGreater(self.game.score, 0)

    def test_stone_axe_throw_and_monster_kill(self):
        self.game.axes.clear()
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.axes), 1)

        # Hit monster with axe
        axe = self.game.axes[0]
        axe["x"] = 5.0
        axe["y"] = 13.0
        target = self.game.monsters[0]
        target["x"] = 5.0
        target["y"] = 13.0
        target["health"] = 1
        target["active"] = True

        self.game.update(0.02, 0, 0)
        self.assertFalse(target["active"])
        self.assertGreater(self.game.score, 0)

    def test_egg_hatching_gives_skateboard(self):
        self.assertFalse(self.game.has_skateboard)
        egg = self.game.fruits[1]
        self.assertEqual(egg["type"], 2)  # Skateboard egg
        egg["x"] = 2.0
        egg["y"] = 13.0
        egg["active"] = True
        self.game.player_x = 2.0
        self.game.player_y = 13.0

        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.has_skateboard)

    def test_skateboard_crash_shield(self):
        self.game.has_skateboard = True
        self.game.player_x = 2.0
        self.game.player_y = 13.0

        monster = self.game.monsters[0]
        monster["x"] = 2.0
        monster["y"] = 13.0
        monster["active"] = True

        self.game.update(0.02, 0, 0)
        self.assertFalse(self.game.has_skateboard)  # Skateboard sacrificed!
        self.assertEqual(self.game.state, STATE_PLAYING)  # Still alive!
        self.assertEqual(self.game.lives, 3)

    def test_fairy_invincibility(self):
        self.game.has_fairy = True
        self.game.fairy_timer = 3.0
        self.game.has_skateboard = False
        self.game.player_x = 2.0
        self.game.player_y = 13.0

        monster = self.game.monsters[0]
        monster["x"] = 2.0
        monster["y"] = 13.0
        monster["active"] = True

        self.game.update(0.02, 0, 0)
        self.assertFalse(monster["active"])  # Fairy destroyed monster!
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

    def test_stage_progression_and_victory(self):
        self.game.stage_progress = 49.9
        self.game.player_x = 8.5
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1500)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 57)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
