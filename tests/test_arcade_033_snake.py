# -*- coding: utf-8 -*-
import unittest
from arcade.game_033_snake import Game033Snake
from arcade.base_cartridge import (
    CTRL_DPAD_4WAY,
    STATE_TITLE,
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
        self.game = Game033Snake(wrap_walls=False)
        self.game.init()
        self.game.start()

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
        self.game.update(0.01, KEY_DOWN, KEY_DOWN)
        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game._snake[0], (5, 8))

        self.game.update(0.01, KEY_LEFT, KEY_LEFT)
        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game._snake[0], (4, 8))

    def test_04_prevent_reverse_into_neck(self):
        self.game.update(0.01, KEY_LEFT, KEY_LEFT)
        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game._snake[0], (6, 7))

    def test_05_food_eating_and_growth(self):
        self.game._food = (6, 7)
        prev_len = len(self.game._snake)
        self.game.update(0.36, 0, 0)
        self.assertEqual(len(self.game._snake), prev_len + 1)
        self.assertEqual(self.game.get_status()["score"], 10)

    def test_06_self_collision_gameover_and_result_screen(self):
        # Loop: bite tail
        self.game._snake = [(5, 7), (4, 7), (3, 7), (3, 8), (4, 8), (5, 8)]
        self.game._dir = (1, 0)
        self.game._next_dir = (1, 0)

        self.game.update(0.01, KEY_DOWN, KEY_DOWN)
        self.game.update(0.36, 0, 0)
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_GAMEOVER)

        # Verify result screen renders G O and score digits
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb), "Result screen must be rendered on Game Over")

    def test_07_deadly_wall_collision(self):
        # Classic dead wall: moving left at x=0 hits wall and dies
        self.game._snake = [(0, 7), (1, 7), (2, 7)]
        self.game._dir = (-1, 0)
        self.game._next_dir = (-1, 0)
        self.game.wrap_walls = False

        self.game.update(0.36, 0, 0)
        self.assertEqual(self.game.get_status()["state"], STATE_GAMEOVER)

    def test_08_rapid_double_key_reverse_blocked(self):
        # Force next_dir into neck to simulate rapid turn override
        self.game._next_dir = (-1, 0)
        self.game.update(0.36, 0, 0)
        # Should not have died by reversing into neck (4, 7)
        self.assertNotEqual(self.game.get_status()["state"], STATE_GAMEOVER)
        self.assertEqual(self.game._snake[0], (6, 7))



if __name__ == "__main__":
    unittest.main()
