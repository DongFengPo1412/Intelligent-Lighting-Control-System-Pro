# -*- coding: utf-8 -*-
import unittest
from arcade.game_001_mario import Game001Mario
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
)


class TestArcade001Mario(unittest.TestCase):
    def setUp(self):
        self.game = Game001Mario()
        self.game.init()

    def test_01_metadata(self):
        self.assertEqual(self.game.game_id, 1)
        self.assertEqual(self.game.name, "超级马里奥")
        self.assertEqual(self.game.english_name, "Super Mario Bros.")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("跳跃", self.game.core_mechanic)

    def test_02_initial_state_and_render(self):
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_TITLE)
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb), "Title screen must render visible pixels")

    def test_03_title_to_ready_and_play(self):
        # Press A to start
        self.game.update(0.02, KEY_A, KEY_A)
        # Advance through READY animation frames (around 1.7-2.0s)
        for _ in range(100):
            self.game.update(0.02, 0, 0)
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_PLAYING)

    def test_04_run_and_jump_physics(self):
        # Start game into playing state
        self.game.update(0.02, KEY_A, KEY_A)
        for _ in range(100):
            self.game.update(0.02, 0, 0)

        # Move right and jump
        for _ in range(10):
            self.game.update(0.02, KEY_RIGHT | KEY_A, KEY_A)
        for _ in range(20):
            self.game.update(0.02, KEY_RIGHT, 0)

        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_PLAYING)

    def test_05_reset(self):
        self.game.update(0.02, KEY_A, KEY_A)
        for _ in range(100):
            self.game.update(0.02, 0, 0)
        self.game.reset()
        st = self.game.get_status()
        self.assertEqual(st["state"], STATE_TITLE)


if __name__ == "__main__":
    unittest.main()

