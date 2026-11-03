# -*- coding: utf-8 -*-
"""
test_arcade_158_qix.py —— 街机游戏 #158 划线天蚕变 (Qix 1981 / Taito) 单元测试
验证元数据、边界巡弋、慢速与快速按键画线入内、空间切割闭合领地、Qix触线反噬与占领70%过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_158_qix import (
    Game158Qix,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_HIT,
    STATE_GAME_OVER,
    CELL_EMPTY,
    CELL_BORDER,
    CELL_CLAIMED,
    CELL_DRAWING,
    WIN_PERCENTAGE,
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


class TestGame158Qix(unittest.TestCase):
    def setUp(self):
        self.game = Game158Qix()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 158)
        self.assertIn("划线天蚕变", self.game.name)
        self.assertEqual(self.game.english_name, "Qix")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.px, 7)
        self.assertEqual(self.game.py, 15)
        self.assertFalse(self.game.is_drawing)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 158)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["percent_claimed"], 0.0)

    def test_02_border_patrolling_movement(self):
        # Walk along bottom border without buttons A/B
        self.game.update(0.016, KEY_LEFT, 0)
        self.assertEqual(self.game.px, 6)
        self.assertEqual(self.game.py, 15)
        self.assertFalse(self.game.is_drawing)

    def test_03_start_drawing_into_empty_space_with_key_a(self):
        # Hold KEY_A and move UP into (7, 14) which is empty
        self.game.px = 7
        self.game.py = 15
        self.game.update(0.016, KEY_UP | KEY_A, 0)

        self.assertTrue(self.game.is_drawing)
        self.assertTrue(self.game.draw_slow)
        self.assertEqual(self.game.px, 7)
        self.assertEqual(self.game.py, 14)
        self.assertEqual(self.game.grid[14][7], CELL_DRAWING)
        self.assertEqual(len(self.game.draw_path), 1)

    def test_04_drawing_path_accumulates(self):
        self.game.is_drawing = True
        self.game.px = 7
        self.game.py = 14
        self.game.grid[14][7] = CELL_DRAWING
        self.game.draw_path = [(7, 14)]

        # Move UP again into (7, 13)
        self.game.update(0.016, KEY_UP | KEY_A, 0)
        self.assertEqual(self.game.px, 7)
        self.assertEqual(self.game.py, 13)
        self.assertEqual(len(self.game.draw_path), 2)

    def test_05_closing_territory_flood_fill(self):
        # Draw a line at x=3 cutting off left slice (x=1,2)
        self.game.is_drawing = True
        self.game.draw_slow = True  # Slow Stix (2x multiplier)
        self.game.px = 3
        self.game.py = 1
        for y in range(1, 15):
            self.game.grid[y][3] = CELL_DRAWING
            self.game.draw_path.append((3, y))

        initial_score = self.game.score
        # Close connection at (3, 0) by moving UP into top border
        self.game.update(0.016, KEY_UP, 0)
        self.assertFalse(self.game.is_drawing)
        self.assertGreater(self.game.score, initial_score)
        self.assertGreater(self.game.percent_claimed, 0.0)

    def test_06_fast_stix_drawing_with_key_b(self):
        self.game.px = 7
        self.game.py = 15

        # Move UP with KEY_B (Fast Stix)
        self.game.update(0.016, KEY_UP | KEY_B, 0)
        self.assertTrue(self.game.is_drawing)
        self.assertFalse(self.game.draw_slow)

    def test_07_qix_motion_and_bouncing(self):
        initial_qx = self.game.qx
        self.game.update(0.1, 0, 0)
        self.assertNotEqual(self.game.qx, initial_qx)

    def test_08_qix_hitting_active_drawing_line_kills_player(self):
        self.game.is_drawing = True
        self.game.draw_path = [(7, 8)]
        self.game.grid[8][7] = CELL_DRAWING

        # Move Qix onto (7, 8)
        self.game.qx = 7.0
        self.game.qy = 8.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)

    def test_09_sparx_touch_player_on_border(self):
        self.game.px = 0
        self.game.py = 0
        self.game.is_drawing = False

        # Move Sparx 0 to (0, 0)
        self.game.sparx[0]["x"] = 0.0
        self.game.sparx[0]["y"] = 0.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)

    def test_10_reaching_70_percent_clears_stage_and_render(self):
        # Claim almost all cells
        for y in range(1, 15):
            for x in range(1, 12):
                self.game.grid[y][x] = CELL_CLAIMED

        self.game.percent_claimed = self.game._calc_percent()
        self.assertGreaterEqual(self.game.percent_claimed, WIN_PERCENTAGE)

        # Trigger check via closing
        self.game.is_drawing = True
        self.game.draw_path = [(13, 14)]
        self.game.grid[14][13] = CELL_DRAWING
        self.game.px = 13
        self.game.py = 14

        self.game.update(0.016, KEY_DOWN, 0)  # Reaches border (13, 15)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 3000)

        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()
