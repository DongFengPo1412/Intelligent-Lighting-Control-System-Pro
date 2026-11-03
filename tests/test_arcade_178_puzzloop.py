# -*- coding: utf-8 -*-
import unittest
from arcade.game_178_puzzloop import (
    Game178PuzzLoop,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_DRAIN_LOST,
    STATE_GAME_OVER,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_BLUE,
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

class TestArcade178PuzzLoop(unittest.TestCase):
    def setUp(self):
        self.game = Game178PuzzLoop()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 178)
        self.assertEqual(self.game.name, "弹珠回旋环")
        self.assertEqual(self.game.english_name, "Puzz Loop")
        self.assertEqual(self.game.release_year, 1998)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(len(self.game.train), 0)
        self.assertGreater(len(self.game.track), 30)

    def test_02_turret_aim_rotation(self):
        init_angle = self.game.aim_angle
        # Rotate Right
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.aim_angle, init_angle)
        # Rotate Left
        self.game.update(0.2, keys_down=KEY_LEFT)
        self.assertLess(self.game.aim_angle, init_angle)

    def test_03_swap_marble_colors(self):
        cur = self.game.cur_color
        nxt = self.game.next_color
        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertEqual(self.game.cur_color, nxt)
        self.assertEqual(self.game.next_color, cur)

    def test_04_shoot_bullet_marble(self):
        self.assertFalse(self.game.bullet["active"])
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertTrue(self.game.bullet["active"])
        self.assertAlmostEqual(self.game.bullet["x"], 7.5, places=1)
        self.assertLess(self.game.bullet["y"], 7.5)

    def test_05_bullet_marble_insert_into_train(self):
        # Configure a simple train of 2 green marbles
        self.game.train = [COLOR_GREEN, COLOR_GREEN]
        self.game.train_progress = 10.0
        # Position of marble 0
        tx, ty = self.game.track[10]

        # Bullet incoming towards marble 0
        self.game.bullet = {
            "active": True,
            "x": tx,
            "y": ty,
            "vx": 0.0,
            "vy": 0.0,
            "color": COLOR_RED, # Different color, so won't pop
        }
        self.game.update(0.01)
        # Bullet should insert, increasing train length to 3
        self.assertFalse(self.game.bullet["active"])
        self.assertEqual(len(self.game.train), 3)

    def test_06_match_3_pop_marbles_and_score(self):
        # 2 Red marbles
        self.game.train = [COLOR_RED, COLOR_RED]
        self.game.train_progress = 10.0
        tx, ty = self.game.track[10]

        # Fire 3rd Red marble directly into them
        self.game.bullet = {
            "active": True,
            "x": tx,
            "y": ty,
            "vx": 0.0,
            "vy": 0.0,
            "color": COLOR_RED,
        }
        initial_score = self.game.score
        self.game.update(0.01)
        # 3 matching red marbles pop, clearing train!
        self.assertEqual(len(self.game.train), 0)
        self.assertGreater(self.game.score, initial_score + 300)

    def test_07_magnetic_pullback_cascade(self):
        # Pattern: [Red, Green, Green, Red]
        # Insert Green into the center to create 3 Greens: [Red, Green, Green, Green, Red]
        # Greens pop, leaving [Red, Red] which magnetically pulls back!
        self.game.train = [COLOR_RED, COLOR_GREEN, COLOR_GREEN, COLOR_RED]
        self.game.train_progress = 10.0
        tx, ty = self.game.track[11]

        self.game.bullet = {
            "active": True,
            "x": tx,
            "y": ty,
            "vx": 0.0,
            "vy": 0.0,
            "color": COLOR_GREEN,
        }
        initial_score = self.game.score
        self.game.update(0.01)

        # After greens pop and reds pull back, bonus awarded
        self.assertGreater(self.game.score, initial_score + 500)

    def test_08_drain_overrun_loses_life(self):
        self.game.train = [COLOR_RED]
        # Force progress near the drain at track end
        self.game.train_progress = float(len(self.game.track) - 1)
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_DRAIN_LOST)

    def test_09_all_marbles_cleared_stage_clear(self):
        self.game.train = [COLOR_BLUE, COLOR_BLUE]
        self.game.train_progress = 5.0
        tx, ty = self.game.track[5]

        # Insert 3rd blue
        self.game.bullet = {
            "active": True,
            "x": tx,
            "y": ty,
            "vx": 0.0,
            "vy": 0.0,
            "color": COLOR_BLUE,
        }
        self.game.update(0.01)
        self.assertEqual(len(self.game.train), 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 3000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_DRAIN_LOST
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
