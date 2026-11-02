import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_052_gunsmoke import (
    Game052GunSmoke,
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


class TestArcade052GunSmoke(unittest.TestCase):
    def setUp(self):
        self.game = Game052GunSmoke()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 52)
        self.assertEqual(self.game.english_name, "Gun.Smoke")
        self.assertEqual(self.game.release_year, 1985)
        cart = ArcadeRegistry.get_cartridge(52)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game052GunSmoke)

    def test_player_movement_and_bounds(self):
        # Move Up and Left
        self.game.update(0.1, KEY_UP | KEY_LEFT, 0)
        self.assertLess(self.game.player_y, 13.5)
        self.assertLess(self.game.player_x, 7.5)

        # Boundary clamping
        self.game.player_x = 0.0
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.player_x, 1.0)

    def test_three_way_shooting(self):
        # 1. Fire Left with KEY_A
        self.game.bullets.clear()
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertLess(self.game.bullets[0]["vx"], 0.0)
        self.assertLess(self.game.bullets[0]["vy"], 0.0)

        # 2. Fire Right with KEY_B
        self.game.bullets.clear()
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertGreater(self.game.bullets[0]["vx"], 0.0)
        self.assertLess(self.game.bullets[0]["vy"], 0.0)

        # 3. Fire Straight Center with KEY_A + KEY_B
        self.game.bullets.clear()
        self.game.update(0.05, KEY_A | KEY_B, 0)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertEqual(self.game.bullets[0]["vx"], 0.0)
        self.assertLess(self.game.bullets[0]["vy"], 0.0)

    def test_barrel_destruction_and_horse_pickup(self):
        self.assertFalse(self.game.has_horse)
        # Position player bullet directly onto horse barrel
        barrel = self.game.barrels[0]
        self.assertTrue(barrel["has_horse"])
        barrel["y"] = 8.0
        barrel["x"] = 5.0

        self.game.bullets.append({
            "x": 5.0,
            "y": 8.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertFalse(barrel["active"])
        self.assertTrue(self.game.has_horse)
        self.assertEqual(self.game.horse_armor, 3)

    def test_horse_armor_absorbs_hit(self):
        self.game.has_horse = True
        self.game.horse_armor = 3
        self.game.player_x = 7.0
        self.game.player_y = 7.0

        # Incoming enemy bullet
        self.game.bullets.append({
            "x": 7.0,
            "y": 7.0,
            "vx": 0.0,
            "vy": 5.0,
            "is_player": False,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.horse_armor, 2)
        self.assertTrue(self.game.has_horse)
        self.assertEqual(self.game.state, STATE_PLAYING)  # Did not die!

    def test_player_death_without_horse(self):
        self.game.has_horse = False
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

    def test_stage_scrolling(self):
        initial_scroll = self.game.scroll_dist
        self.game.update(0.5, 0, 0)
        self.assertGreater(self.game.scroll_dist, initial_scroll)

    def test_bandit_defeat(self):
        bandit = self.game.bandits[0]
        bandit["x"] = 6.0
        bandit["y"] = 6.0
        bandit["health"] = 1
        bandit["active"] = True

        self.game.bullets.append({
            "x": 6.0,
            "y": 6.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertFalse(bandit["active"])
        self.assertGreater(self.game.score, 0)

    def test_boss_appearance_and_victory(self):
        self.game.scroll_dist = 39.5
        self.assertFalse(self.game.boss_active)

        # Advance past threshold
        self.game.update(0.2, 0, 0)
        self.assertTrue(self.game.boss_active)

        # Damage boss to defeat
        self.game.boss_health = 1
        self.game.boss_x = 8.0
        self.game.boss_y = 4.0

        self.game.bullets.append({
            "x": 8.0,
            "y": 4.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 52)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
