# -*- coding: utf-8 -*-
import unittest
from arcade.game_182_magicaldrop import (
    Game182MagicalDrop,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_FLOOR_CRUSHED,
    STATE_GAME_OVER,
    COLOR_NONE,
    COLOR_RED,
    COLOR_BLUE,
    COLOR_GREEN,
    COLOR_YELLOW,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

class TestArcade182MagicalDrop(unittest.TestCase):
    def setUp(self):
        self.game = Game182MagicalDrop()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 182)
        self.assertEqual(self.game.name, "魔法水滴")
        self.assertEqual(self.game.english_name, "Magical Drop")
        self.assertEqual(self.game.release_year, 1995)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.held_count, 0)
        self.assertEqual(self.game.held_color, COLOR_NONE)

    def test_02_clown_lateral_movement_and_bounds(self):
        self.game.col = 7
        # Move left
        self.game.update(0.01, keys_pressed=KEY_LEFT)
        self.assertEqual(self.game.col, 6)

        # Clamp left at col 3
        for _ in range(10):
            self.game.update(0.01, keys_pressed=KEY_LEFT)
        self.assertEqual(self.game.col, 3)

        # Clamp right at col 12
        for _ in range(20):
            self.game.update(0.01, keys_pressed=KEY_RIGHT)
        self.assertEqual(self.game.col, 12)

    def test_03_pull_single_bubble(self):
        # Empty column 5 except row 0
        for y in range(16): self.game.grid[y][5] = COLOR_NONE
        self.game.grid[0][5] = COLOR_BLUE

        self.game.col = 5
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.held_color, COLOR_BLUE)
        self.assertEqual(self.game.held_count, 1)
        self.assertEqual(self.game.grid[0][5], COLOR_NONE) # Sucked down!

    def test_04_pull_contiguous_matching_bubbles_chain(self):
        # Stack 3 red bubbles in column 5
        for y in range(16): self.game.grid[y][5] = COLOR_NONE
        self.game.grid[0][5] = COLOR_RED
        self.game.grid[1][5] = COLOR_RED
        self.game.grid[2][5] = COLOR_RED

        self.game.col = 5
        self.game.update(0.01, keys_pressed=KEY_A)
        # Sucks down all 3 contiguous reds
        self.assertEqual(self.game.held_color, COLOR_RED)
        self.assertEqual(self.game.held_count, 3)
        self.assertEqual(self.game.grid[2][5], COLOR_NONE)

    def test_05_fling_bubbles_into_column(self):
        self.game.held_color = COLOR_GREEN
        self.game.held_count = 2
        for y in range(16): self.game.grid[y][6] = COLOR_NONE

        self.game.col = 6
        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertEqual(self.game.held_count, 0)
        self.assertEqual(self.game.held_color, COLOR_NONE)
        self.assertEqual(self.game.grid[0][6], COLOR_GREEN)
        self.assertEqual(self.game.grid[1][6], COLOR_GREEN)

    def test_06_match_3_vertical_pop_and_score(self):
        # Column 6 has 2 yellows at y=0, 1
        for y in range(16): self.game.grid[y][6] = COLOR_NONE
        self.game.grid[0][6] = COLOR_YELLOW
        self.game.grid[1][6] = COLOR_YELLOW

        # Clown holds 1 yellow
        self.game.held_color = COLOR_YELLOW
        self.game.held_count = 1

        self.game.col = 6
        initial_score = self.game.score
        # Fling yellow into column 6 to form 3 consecutive yellows
        self.game.update(0.01, keys_pressed=KEY_B)
        # 3 yellows pop!
        self.assertEqual(self.game.grid[0][6], COLOR_NONE)
        self.assertEqual(self.game.grid[1][6], COLOR_NONE)
        self.assertEqual(self.game.grid[2][6], COLOR_NONE)
        self.assertEqual(self.game.score, initial_score + 300)

    def test_07_cannot_pull_different_color_when_holding(self):
        self.game.held_color = COLOR_BLUE
        self.game.held_count = 1
        for y in range(16): self.game.grid[y][5] = COLOR_NONE
        self.game.grid[0][5] = COLOR_RED # Different color

        self.game.col = 5
        self.game.update(0.01, keys_pressed=KEY_A)
        # Cannot pull red while holding blue
        self.assertEqual(self.game.held_color, COLOR_BLUE)
        self.assertEqual(self.game.held_count, 1)
        self.assertEqual(self.game.grid[0][5], COLOR_RED)

    def test_08_ceiling_descent_shifts_grid_down(self):
        for y in range(16):
            for x in range(16):
                self.game.grid[y][x] = COLOR_NONE
        self.game.grid[2][5] = COLOR_RED

        # Elapse drop timer
        self.game.drop_timer = 0.05
        self.game.update(0.1)
        # Red shifted from y=2 to y=3
        self.assertEqual(self.game.grid[3][5], COLOR_RED)

    def test_09_bubbles_crossing_floor_causes_life_loss(self):
        # Bubble at row 12 shifts down to row 13 (crossing floor line)
        for y in range(16):
            for x in range(16):
                self.game.grid[y][x] = COLOR_NONE
        self.game.grid[12][5] = COLOR_RED
        self.game.drop_timer = 0.05
        initial_lives = self.game.lives

        self.game.update(0.1)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_FLOOR_CRUSHED)

    def test_10_target_cleared_stage_clear_and_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.bubbles_cleared = self.game.cleared_target - 3
        # Match 3 to complete stage target
        for y in range(16): self.game.grid[y][5] = COLOR_NONE
        self.game.grid[0][5] = COLOR_RED
        self.game.grid[1][5] = COLOR_RED
        self.game.held_color = COLOR_RED
        self.game.held_count = 1
        self.game.col = 5

        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 2500)

if __name__ == "__main__":
    unittest.main()

