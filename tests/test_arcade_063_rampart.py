import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_063_rampart import (
    Game063Rampart,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    PHASE_BOMBARD,
    PHASE_REBUILD,
    CELL_OCEAN,
    CELL_LAND,
    CELL_CASTLE,
    CELL_WALL,
    CELL_CANNON,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade063Rampart(unittest.TestCase):
    def setUp(self):
        self.game = Game063Rampart()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 63)
        self.assertEqual(self.game.english_name, "Rampart")
        self.assertEqual(self.game.release_year, 1990)
        cart = ArcadeRegistry.get_cartridge(63)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game063Rampart)

    def test_bombard_crosshair_movement(self):
        self.assertEqual(self.game.phase, PHASE_BOMBARD)
        initial_y = self.game.cursor_y
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.cursor_y, initial_y)

    def test_fire_cannon_destroys_ship(self):
        ship = self.game.ships[0]
        ship["x"] = 12.0
        ship["y"] = 7.0
        ship["active"] = True

        self.game.cursor_x = 12
        self.game.cursor_y = 7
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.cannonballs), 1)

        # Advance cannonball until it lands on target
        for _ in range(20):
            self.game.update(0.02, 0, 0)

        self.assertFalse(ship["active"])
        self.assertGreater(self.game.score, 0)

    def test_rebuild_phase_wall_placement(self):
        self.game.phase = PHASE_REBUILD
        self.game.cursor_x = 3
        self.game.cursor_y = 3
        self.assertEqual(self.game.grid[3][3], CELL_LAND)

        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(self.game.grid[3][3], CELL_WALL)

    def test_enclosure_flood_fill_intact(self):
        self.game.check_enclosure()
        self.assertTrue(self.game.castle_enclosed)

    def test_enclosure_breach_detected(self):
        # Create a breach in top wall at (4, 6)
        self.game.grid[6][4] = CELL_LAND
        self.game.check_enclosure()
        self.assertFalse(self.game.castle_enclosed)

    def test_unrepaired_breach_causes_defeat(self):
        self.game.phase = PHASE_REBUILD
        self.game.phase_timer = 0.05
        # Create breach in top wall
        self.game.grid[6][4] = CELL_LAND

        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_repaired_castle_survives_round(self):
        self.game.phase = PHASE_REBUILD
        self.game.phase_timer = 0.05
        # Castle fully enclosed
        initial_round = self.game.round
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.round, initial_round + 1)
        self.assertEqual(self.game.phase, PHASE_BOMBARD)

    def test_three_rounds_victory(self):
        self.game.round = 3
        self.game.phase = PHASE_REBUILD
        self.game.phase_timer = 0.05

        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 63)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
