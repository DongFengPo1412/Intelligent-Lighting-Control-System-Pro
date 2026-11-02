import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_083_puyopuyo import (
    Game083PuyoPuyo,
    STATE_PLAYING,
    STATE_CHAIN_RESOLVE,
    STATE_GAME_OVER,
    PUYO_EMPTY,
    PUYO_RED,
    PUYO_GREEN,
    PUYO_BLUE,
    PUYO_YELLOW,
    PUYO_GARBAGE,
    COLS,
    ROWS,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)


class TestGame083PuyoPuyo(unittest.TestCase):
    def setUp(self):
        self.game = Game083PuyoPuyo()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 83)
        self.assertEqual(self.game.name, "魔法气泡")
        self.assertEqual(self.game.english_name, "Puyo Puyo")
        self.assertEqual(self.game.release_year, 1991)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("四连邻接粘合消除", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["score"], 0)
        self.assertEqual(status["cur_col"], 2)
        self.assertEqual(self.game.get_cell(2, 12), PUYO_EMPTY)

    def test_lateral_shifting(self):
        # Shift right
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.cur_col, 3)

        # Shift left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.cur_col, 2)

    def test_rotations(self):
        # Initial: sub is above (0, -1)
        self.assertEqual(self.game.sub_offset_x, 0)
        self.assertEqual(self.game.sub_offset_y, -1)

        # Rotate CW (A): should become (1, 0)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.sub_offset_x, 1)
        self.assertEqual(self.game.sub_offset_y, 0)

        # Rotate CCW (B): should return to (0, -1)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.sub_offset_x, 0)
        self.assertEqual(self.game.sub_offset_y, -1)

    def test_soft_drop_and_landing(self):
        # Fast drop to floor
        for _ in range(40):
            self.game.update(0.1, KEY_DOWN, KEY_DOWN)
            if self.game.state == STATE_CHAIN_RESOLVE:
                break

        self.assertEqual(self.game.state, STATE_CHAIN_RESOLVE)
        # Bottom row 12 should now have puyo
        self.assertNotEqual(self.game.grid[ROWS - 1][2], PUYO_EMPTY)

    def test_gravity_fall(self):
        self.game.clear_board()
        # Place floating puyo at row 5, col 1
        self.game.grid[5][1] = PUYO_RED
        self.assertEqual(self.game.grid[ROWS - 1][1], PUYO_EMPTY)

        fell = self.game.apply_gravity()
        self.assertTrue(fell)
        self.assertEqual(self.game.grid[5][1], PUYO_EMPTY)
        self.assertEqual(self.game.grid[ROWS - 1][1], PUYO_RED)

    def test_4_connected_match_clear(self):
        self.game.clear_board()
        # Form 4-puyo block at bottom right
        self.game.grid[ROWS - 1][3] = PUYO_RED
        self.game.grid[ROWS - 1][4] = PUYO_RED
        self.game.grid[ROWS - 2][3] = PUYO_RED
        self.game.grid[ROWS - 2][4] = PUYO_RED

        cleared = self.game.check_matches()
        self.assertTrue(cleared)
        # All 4 should be popped
        self.assertEqual(self.game.grid[ROWS - 1][3], PUYO_EMPTY)
        self.assertEqual(self.game.grid[ROWS - 1][4], PUYO_EMPTY)

    def test_chain_cascade_combo(self):
        self.game.clear_board()
        # Setup genuine 2-chain cascade:
        # Col 0: 2 reds
        # Col 1: 2 reds, with 1 green suspended on top
        # Col 2: 2 greens
        # Col 3: 1 green
        self.game.grid[ROWS - 1][0] = PUYO_RED
        self.game.grid[ROWS - 2][0] = PUYO_RED

        self.game.grid[ROWS - 1][1] = PUYO_RED
        self.game.grid[ROWS - 2][1] = PUYO_RED
        self.game.grid[ROWS - 3][1] = PUYO_GREEN  # suspended above reds

        self.game.grid[ROWS - 1][2] = PUYO_GREEN
        self.game.grid[ROWS - 2][2] = PUYO_GREEN

        self.game.grid[ROWS - 1][3] = PUYO_GREEN

        # Step 1: match reds (4 reds pop)
        m1 = self.game.check_matches()
        self.assertTrue(m1)

        # Step 2: gravity falls suspended green into row -1
        f1 = self.game.apply_gravity()
        self.assertTrue(f1)
        self.assertEqual(self.game.grid[ROWS - 1][1], PUYO_GREEN)

        # Step 3: match greens (chain 2 pops!)
        m2 = self.game.check_matches()
        self.assertTrue(m2)

    def test_garbage_neighbor_clear(self):
        self.game.clear_board()
        # 4 reds adjacent to garbage
        self.game.grid[ROWS - 1][0] = PUYO_RED
        self.game.grid[ROWS - 1][1] = PUYO_RED
        self.game.grid[ROWS - 1][2] = PUYO_RED
        self.game.grid[ROWS - 2][0] = PUYO_RED
        self.game.grid[ROWS - 1][3] = PUYO_GARBAGE  # adjacent garbage

        self.game.check_matches()
        # Both reds and garbage should be cleared!
        self.assertEqual(self.game.grid[ROWS - 1][3], PUYO_EMPTY)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
