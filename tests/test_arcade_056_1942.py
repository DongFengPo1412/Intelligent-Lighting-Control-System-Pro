import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_056_1942 import (
    Game056_1942,
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


class TestArcade056_1942(unittest.TestCase):
    def setUp(self):
        self.game = Game056_1942()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 56)
        self.assertEqual(self.game.english_name, "1942")
        self.assertEqual(self.game.release_year, 1984)
        cart = ArcadeRegistry.get_cartridge(56)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game056_1942)

    def test_player_movement(self):
        initial_x = self.game.player_x
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.player_x, initial_x)

        initial_y = self.game.player_y
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.player_y, initial_y)

    def test_loop_the_loop_invincibility(self):
        self.assertEqual(self.game.loops_remaining, 3)
        self.assertFalse(self.game.is_looping)

        # Trigger Loop with Button B
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.is_looping)
        self.assertEqual(self.game.loops_remaining, 2)

        # Incoming bullet directly at player
        self.game.bullets.append({
            "x": self.game.player_x,
            "y": self.game.player_y,
            "vx": 0.0,
            "vy": 5.0,
            "is_player": False,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)  # Invincible!
        self.assertEqual(self.game.lives, 3)

    def test_firing_twin_machine_guns(self):
        self.game.bullets.clear()
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertTrue(self.game.bullets[0]["is_player"])
        self.assertLess(self.game.bullets[0]["vy"], 0.0)

    def test_red_formation_defeat_gives_wingmen(self):
        self.assertFalse(self.game.has_wingmen)
        # Target red plane (type 1)
        red_plane = self.game.planes[2]
        self.assertEqual(red_plane["type"], 1)
        red_plane["x"] = 6.0
        red_plane["y"] = 6.0
        red_plane["health"] = 1
        red_plane["active"] = True

        self.game.bullets.append({
            "x": 6.0,
            "y": 6.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertFalse(red_plane["active"])
        self.assertTrue(self.game.has_wingmen)

    def test_wingmen_triple_stream_firing(self):
        self.game.has_wingmen = True
        self.game.bullets.clear()
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 3)

    def test_wingmen_sacrifice_shield(self):
        self.game.has_wingmen = True
        self.game.player_x = 7.0
        self.game.player_y = 7.0

        self.game.bullets.append({
            "x": 7.0,
            "y": 7.0,
            "vx": 0.0,
            "vy": 5.0,
            "is_player": False,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertFalse(self.game.has_wingmen)  # Wingmen absorb hit
        self.assertEqual(self.game.state, STATE_PLAYING)  # Still alive!
        self.assertEqual(self.game.lives, 3)

    def test_boss_spawn_and_defeat(self):
        self.game.planes_defeated = 4
        self.assertFalse(self.game.boss_active)

        # Defeat 5th plane
        p = self.game.planes[0]
        p["x"] = 5.0
        p["y"] = 5.0
        p["health"] = 1
        p["active"] = True

        self.game.bullets.append({
            "x": 5.0,
            "y": 5.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.boss_active)

        # Destroy boss
        self.game.boss_health = 1
        self.game.boss_x = 7.0
        self.game.boss_y = 4.0
        self.game.bullets.append({
            "x": 7.0,
            "y": 4.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1500)

    def test_player_death_unprotected(self):
        self.game.has_wingmen = False
        self.game.is_looping = False
        self.game.player_x = 7.0
        self.game.player_y = 7.0

        self.game.bullets.append({
            "x": 7.0,
            "y": 7.0,
            "vx": 0.0,
            "vy": 5.0,
            "is_player": False,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 56)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
