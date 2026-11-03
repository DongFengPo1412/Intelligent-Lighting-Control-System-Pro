# -*- coding: utf-8 -*-
import unittest
from arcade.game_041_tetris import Game041Tetris, BOARD_LEFT, BOARD_RIGHT
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
)


class TestArcade041Tetris(unittest.TestCase):
    def setUp(self):
        self.game = Game041Tetris()
        self.game.init()
        self.game.start()

    def test_01_metadata(self):
        self.assertEqual(self.game.game_id, 41)
        self.assertEqual(self.game.name, "俄罗斯方块")
        self.assertEqual(self.game.english_name, "Tetris")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("四联方块", self.game.core_mechanic)

    def test_02_initial_state_and_render(self):
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["lives"], 1)

        fb = self.game.render()
        self.assertEqual(len(fb), 768)

        # Verify border rendering at BOARD_LEFT - 1 (col 2) and BOARD_RIGHT + 1 (col 13)
        for y in range(16):
            l_idx = (y * 16 + 2) * 3
            r_idx = (y * 16 + 13) * 3
            self.assertEqual((fb[l_idx], fb[l_idx+1], fb[l_idx+2]), (40, 40, 50))
            self.assertEqual((fb[r_idx], fb[r_idx+1], fb[r_idx+2]), (40, 40, 50))

    def test_03_move_and_rotation(self):
        self.game._piece_type = 2  # T type
        self.game._piece_x = 6
        self.game._piece_y = 5
        self.game._piece_rot = 0

        # Move left
        self.game.update(0.01, KEY_LEFT, KEY_LEFT)
        self.assertEqual(self.game._piece_x, 5)

        # Move right
        self.game.update(0.01, KEY_RIGHT, KEY_RIGHT)
        self.assertEqual(self.game._piece_x, 6)

        # Rotate
        self.game.update(0.01, KEY_A, KEY_A)
        self.assertEqual(self.game._piece_rot, 1)

    def test_04_soft_drop_and_lock(self):
        self.game._piece_type = 0  # O shape (2x2)
        self.game._piece_x = 6
        self.game._piece_y = 13
        self.game._piece_rot = 0

        # Soft drop 1 row
        self.game.update(0.06, KEY_DOWN, 0)
        self.assertEqual(self.game._piece_y, 14)

        # Next drop should lock piece at y=14
        self.game.update(0.06, KEY_DOWN, 0)
        self.assertGreater(self.game._field[14][6], 0)
        self.assertGreater(self.game._field[15][6], 0)

    def test_05_line_clear_and_scoring(self):
        for x in range(BOARD_LEFT, BOARD_RIGHT + 1):
            if x != 6:
                self.game._field[15][x] = 1

        self.game._piece_type = 0
        self.game._piece_x = 6
        self.game._piece_y = 14
        self.game._lock_piece()

        st = self.game.get_status()
        self.assertGreater(st["score"], 0)

    def test_06_game_over_and_result_screen(self):
        for x in range(BOARD_LEFT, BOARD_RIGHT + 1):
            self.game._field[0][x] = 1
            self.game._field[1][x] = 1

        self.game._spawn_piece()
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_GAMEOVER)

        # Verify result screen renders
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb), "Result screen must be rendered on Game Over")


if __name__ == "__main__":
    unittest.main()
