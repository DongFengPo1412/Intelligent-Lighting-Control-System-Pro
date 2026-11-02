import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_061_battlecity import (
    Game061BattleCity,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    TILE_EMPTY,
    TILE_BRICK,
    TILE_STEEL,
    TILE_EAGLE,
    TILE_EAGLE_DEAD,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade061BattleCity(unittest.TestCase):
    def setUp(self):
        self.game = Game061BattleCity()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 61)
        self.assertEqual(self.game.english_name, "Battle City")
        self.assertEqual(self.game.release_year, 1980)
        cart = ArcadeRegistry.get_cartridge(61)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game061BattleCity)

    def test_tank_movement_and_collision(self):
        # Move up into clear corridor
        self.game.player_x = 4.0
        self.game.player_y = 12.0
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.player_y, 12.0)
        self.assertEqual(self.game.player_dir, 0)

        # Blocked by steel at (7, 7)
        self.assertFalse(self.game.can_move_to(7.0, 7.0))

    def test_shooting_destroys_brick(self):
        # Open tile at (2, 1), Brick at (2, 3)
        self.assertEqual(self.game.map[1][2], TILE_EMPTY)
        self.assertEqual(self.game.map[3][2], TILE_BRICK)
        self.game.player_x = 2.0
        self.game.player_y = 1.0
        self.game.player_dir = 2  # Down

        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.shells), 1)

        # Advance shell into brick
        for _ in range(10):
            self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.map[3][2], TILE_EMPTY)
        self.assertGreater(self.game.score, 0)

    def test_steel_resists_normal_shells(self):
        self.assertEqual(self.game.map[7][7], TILE_STEEL)
        self.game.player_x = 7.0
        self.game.player_y = 8.5
        self.game.player_dir = 0
        self.game.tank_tier = 1

        self.game.update(0.02, KEY_A, 0)
        for _ in range(10):
            self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.map[7][7], TILE_STEEL)  # Steel remains!

    def test_tier3_chips_steel(self):
        self.game.tank_tier = 3
        self.game.player_x = 7.0
        self.game.player_y = 8.5
        self.game.player_dir = 0

        self.game.update(0.02, KEY_A, 0)
        for _ in range(10):
            self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.map[7][7], TILE_EMPTY)

    def test_eagle_destruction_causes_immediate_defeat(self):
        self.assertTrue(self.game.eagle_alive)
        self.assertEqual(self.game.map[14][7], TILE_EAGLE)

        # Fire shell directly into eagle
        self.game.shells.append({
            "x": 7.5,
            "y": 13.8,
            "vx": 0.0,
            "vy": 10.0,
            "is_player": False,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertFalse(self.game.eagle_alive)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.map[14][7], TILE_EAGLE_DEAD)

    def test_shovel_reinforcement(self):
        self.assertEqual(self.game.map[13][7], TILE_BRICK)
        self.game.trigger_shovel_reinforce()
        self.assertEqual(self.game.map[13][7], TILE_STEEL)
        self.assertGreater(self.game.shovel_timer, 0.0)

    def test_enemy_defeat_and_quota(self):
        # Position in open corridor at x=4, y=4
        self.assertEqual(self.game.map[4][4], TILE_EMPTY)
        target = self.game.enemies[0]
        target["x"] = 4.0
        target["y"] = 4.0
        target["health"] = 1
        target["active"] = True

        self.game.shells.append({
            "x": 4.0,
            "y": 4.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
            "active": True
        })

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.enemies_defeated, 1)
        self.assertGreater(self.game.score, 0)

    def test_stage_victory(self):
        self.game.enemies_defeated = 6
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1500)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 61)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
