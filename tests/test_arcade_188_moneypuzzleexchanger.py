"""
Unit Tests for Game #188: 钱币交换机 (Money Puzzle Exchanger - 1997 Face)
"""

import unittest
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    CTRL_ARCADE_AB,
)
from arcade.game_188_moneypuzzleexchanger import (
    Game188MoneyPuzzleExchanger,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_GAME_OVER,
    COIN_1,
    COIN_5,
    COIN_10,
    COIN_50,
    COIN_100,
    COIN_500,
)

class TestArcade188MoneyPuzzleExchanger(unittest.TestCase):
    def setUp(self):
        self.game = Game188MoneyPuzzleExchanger()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 188)
        self.assertEqual(self.game.name, "钱币交换机")
        self.assertEqual(self.game.english_name, "Money Puzzle Exchanger")
        self.assertEqual(self.game.release_year, 1997)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.stage, 1)
        self.assertEqual(self.game.cursor_col, 3)
        self.assertEqual(self.game.held_count, 0)
        self.assertGreater(sum(len(c) for c in self.game.grid), 0)

    def test_02_cursor_navigation_and_bounds(self):
        self.game.cursor_col = 3
        self.game.update(0.016, keys_pressed=KEY_LEFT)
        self.assertEqual(self.game.cursor_col, 2)

        # Clamping left
        for _ in range(10):
            self.game.cursor_cooldown = 0.0
            self.game.update(0.016, keys_pressed=KEY_LEFT)
        self.assertEqual(self.game.cursor_col, 0)

        # Clamping right
        for _ in range(15):
            self.game.cursor_cooldown = 0.0
            self.game.update(0.016, keys_pressed=KEY_RIGHT)
        self.assertEqual(self.game.cursor_col, 6)

    def test_03_suction_grab_coins_button_a(self):
        # Set col 0 with coins [5, 1, 1, 1]
        self.game.grid[0] = [5, 1, 1, 1]
        self.game.cursor_col = 0
        self.game.held_count = 0

        # Grab bottom coins
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.held_denom, 1)
        self.assertEqual(self.game.held_count, 3)
        # Remaining in column is only the [5]
        self.assertEqual(self.game.grid[0], [5])

    def test_04_toss_shoot_coins_button_b(self):
        self.game.grid[1] = [10]
        self.game.cursor_col = 1
        self.game.held_denom = 5
        self.game.held_count = 1

        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertEqual(self.game.held_count, 0)
        self.assertEqual(self.game.grid[1], [10, 5])

    def test_05_denomination_merge_five_1s_into_5(self):
        # Set col 2 with four 1s: [1, 1, 1, 1]
        self.game.grid[2] = [1, 1, 1, 1]
        self.game.cursor_col = 2
        self.game.held_denom = 1
        self.game.held_count = 1

        # Toss the 5th 1 into column 2
        self.game.update(0.016, keys_pressed=KEY_B)
        # Five 1s merge into a single 5-yen coin!
        self.assertEqual(self.game.grid[2], [5])
        self.assertEqual(self.game.score, 50)

    def test_06_denomination_merge_two_5s_into_10(self):
        # Set col 3 with one 5: [5]
        self.game.grid[3] = [5]
        self.game.cursor_col = 3
        self.game.held_denom = 5
        self.game.held_count = 1

        # Toss the second 5 into column 3
        self.game.update(0.016, keys_pressed=KEY_B)
        # Two 5s merge into one 10-yen coin!
        self.assertEqual(self.game.grid[3], [10])
        self.assertEqual(self.game.score, 100)

    def test_07_denomination_merge_two_500s_cashout_jackpot(self):
        self.game.grid[4] = [500]
        self.game.cursor_col = 4
        self.game.held_denom = 500
        self.game.held_count = 1

        self.game.update(0.016, keys_pressed=KEY_B)
        # Two 500s completely cash out and disappear!
        self.assertEqual(self.game.grid[4], [])
        self.assertEqual(self.game.score, 10000)

    def test_08_ceiling_descent_pushes_rows_down(self):
        init_heights = [len(col) for col in self.game.grid]
        self.game.drop_timer = 0.05
        self.game.update(0.1) # Triggers ceiling drop
        for c in range(self.game.cols):
            self.assertEqual(len(self.game.grid[c]), init_heights[c] + 1)

    def test_09_all_coins_cleared_stage_clear(self):
        # Clear all columns except one pair of 500s
        for c in range(self.game.cols):
            self.game.grid[c] = []
        self.game.grid[0] = [500]
        self.game.cursor_col = 0
        self.game.held_denom = 500
        self.game.held_count = 1

        self.game.update(0.016, keys_pressed=KEY_B)
        # Board is completely empty!
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 30000) # 10000 + 20000 stage clear

    def test_10_danger_threshold_overflow_game_over_reset(self):
        # Pile up column 0 to 13 non-matching coins
        self.game.grid[0] = [1, 5] * 6 # 12 alternating coins
        self.game.cursor_col = 0
        self.game.held_denom = 10
        self.game.held_count = 1

        self.game.update(0.016, keys_pressed=KEY_B)
        # Exceeds row threshold (len = 13 >= 13)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Reset on A
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)

        # Render test
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
