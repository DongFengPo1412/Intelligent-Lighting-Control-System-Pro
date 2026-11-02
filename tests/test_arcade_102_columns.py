import unittest
from arcade.game_102_columns import (
    Game102Columns,
    STATE_FALLING,
    STATE_FLASHING_MATCH,
    STATE_COLLAPSING,
    STATE_GAME_OVER,
    BOARD_COLS,
    BOARD_ROWS,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestGame102Columns(unittest.TestCase):
    def setUp(self):
        self.game = Game102Columns()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 102)
        self.assertEqual(self.game.name, "宝石方块")
        self.assertEqual(self.game.english_name, "Columns")
        self.assertEqual(self.game.release_year, 1990)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("三色宝石三联柱循环轮换", self.game.core_mechanic)

    def test_column_cycling(self):
        self.game.cur_gems = [1, 2, 3]  # [top, mid, bot]
        self.game.update(0.05, KEY_A, 0)
        # Shift: temp = bot(3), bot = mid(2), mid = top(1), top = temp(3) -> [3, 1, 2]
        self.assertEqual(self.game.cur_gems, [3, 1, 2])

    def test_lateral_movement(self):
        init_col = self.game.cur_col
        # Move right
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.cur_col, init_col + 1)

    def test_hard_drop(self):
        self.game.cur_col = 2
        self.game.cur_y = 2.0
        # Press Button B for hard drop
        self.game.update(0.05, KEY_B, 0)
        # Should lock at floor row (BOARD_ROWS - 1 = 12)
        self.assertNotEqual(self.game.board[12][2], 0)
        self.assertNotEqual(self.game.board[11][2], 0)
        self.assertNotEqual(self.game.board[10][2], 0)

    def test_horizontal_match_and_flash(self):
        # Place 3 identical rubies (gem=1) horizontally at row 12, cols 1, 2, 3
        self.game.board[12][1] = 1
        self.game.board[12][2] = 1
        self.game.board[12][3] = 1

        matches = self.game.find_matches()
        self.assertTrue(matches)
        self.assertTrue(self.game.matched_mask[12][1])
        self.assertTrue(self.game.matched_mask[12][2])
        self.assertTrue(self.game.matched_mask[12][3])

    def test_vertical_match(self):
        # Place 3 identical emeralds (gem=2) vertically at col 0, rows 10, 11, 12
        self.game.board[10][0] = 2
        self.game.board[11][0] = 2
        self.game.board[12][0] = 2

        matches = self.game.find_matches()
        self.assertTrue(matches)
        self.assertTrue(self.game.matched_mask[10][0])
        self.assertTrue(self.game.matched_mask[11][0])
        self.assertTrue(self.game.matched_mask[12][0])

    def test_diagonal_match(self):
        # Place 3 identical sapphires (gem=3) diagonally from (10, 1) down-right to (12, 3)
        self.game.board[10][1] = 3
        self.game.board[11][2] = 3
        self.game.board[12][3] = 3

        matches = self.game.find_matches()
        self.assertTrue(matches)
        self.assertTrue(self.game.matched_mask[10][1])
        self.assertTrue(self.game.matched_mask[11][2])
        self.assertTrue(self.game.matched_mask[12][3])

    def test_gravity_collapse_and_cascade(self):
        # Place a horizontal match of 3 gems at row 12, with a ruby sitting above at row 11
        self.game.board[12][1] = 1
        self.game.board[12][2] = 1
        self.game.board[12][3] = 1
        self.game.board[11][2] = 4  # Topaz above the middle ruby

        self.game.state = STATE_FLASHING_MATCH
        self.game.matched_mask[12][1] = True
        self.game.matched_mask[12][2] = True
        self.game.matched_mask[12][3] = True
        self.game.state_timer = 0.5  # Trigger clear and collapse

        self.game.update(0.05, 0, 0)
        # Matches cleared, Topaz collapses from row 11 down to row 12!
        self.assertEqual(self.game.board[12][2], 4)
        self.assertEqual(self.game.board[11][2], 0)
        self.assertGreater(self.game.score, 0)

    def test_game_over_overflow(self):
        # Fill col 2 all the way to ceiling
        for r in range(BOARD_ROWS):
            self.game.board[r][2] = 1

        self.game.spawn_new_column()
        self.assertEqual(self.game.state, STATE_GAME_OVER)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
