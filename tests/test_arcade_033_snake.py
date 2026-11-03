# -*- coding: utf-8 -*-
import unittest
from arcade.game_033_snake import Game033Snake
from arcade.base_cartridge import (
    CTRL_DPAD_4WAY,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_START,
)


class TestArcade033Snake(unittest.TestCase):
    def setUp(self):
        self.game = Game033Snake()
        self.game.init()

    def test_01_metadata(self):
        self.assertEqual(self.game.game_id, 33)
        self.assertEqual(self.game.name, "经典贪吃蛇")
        self.assertEqual(self.game.english_name, "Classic Snake")
        self.assertEqual(self.game.release_year, 1976)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)
        self.assertIn("转向", self.game.core_mechanic)

    def test_02_initial_state_and_render(self):
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["lives"], 1)

        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        # Verify snake head and food exist
        has_food = False
        has_snake = False
        for i in range(256):
            r, g, b = fb[i*3], fb[i*3+1], fb[i*3+2]
            if r > 200 and g < 50:
                has_food = True
            if g > 150 and r < 50:
                has_snake = True
        self.assertTrue(has_food, "Food must be rendered in red")
        self.assertTrue(has_snake, "Snake must be rendered in green")

    def test_03_crawl_and_turning(self):
        # Initial pos is (5, 7), moving right
        # Turn down
        self.game.update(0.01, KEY_DOWN, KEY_DOWN)
        # Advance 1 tick (0.35s)
        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game._snake[0], (5, 8))

        # Turn left
        self.game.update(0.01, KEY_LEFT, KEY_LEFT)
        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game._snake[0], (4, 8))

    def test_04_prevent_reverse_into_neck(self):
        # Moving right, pressing LEFT should be rejected
        self.game.update(0.01, KEY_LEFT, KEY_LEFT)
        self.game.update(0.36, 0, 0)
        # Should continue moving right to (6, 7)
        self.assertEqual(self.game._snake[0], (6, 7))

    def test_05_food_eating_and_growth(self):
        # Force food right in front of snake at (6, 7)
        self.game._food = (6, 7)
        prev_len = len(self.game._snake)
        self.game.update(0.36, 0, 0)
        self.assertEqual(len(self.game._snake), prev_len + 1)
        self.assertEqual(self.game.get_status()["score"], 10)

    def test_06_self_collision_gameover(self):
        # Make a loop to bite tail: right -> down -> left -> up
        self.game._snake = [(5, 7), (4, 7), (3, 7), (3, 8), (4, 8), (5, 8)]
        self.game._dir = (1, 0)
        self.game._next_dir = (1, 0)

        # Move down to (5, 8) which is already in snake body!
        self.game.update(0.01, KEY_DOWN, KEY_DOWN)
        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game.get_status()["state"], STATE_GAMEOVER)


if __name__ == "__main__":
    unittest.main()
