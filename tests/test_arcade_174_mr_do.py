# -*- coding: utf-8 -*-
import unittest
from arcade.game_174_mr_do import (
    Game174MrDo,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_DIED,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

class TestArcade174MrDo(unittest.TestCase):
    def setUp(self):
        self.game = Game174MrDo()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 174)
        self.assertEqual(self.game.name, "挖金子小丑")
        self.assertEqual(self.game.english_name, "Mr. Do!")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(len(self.game.apples), 3)
        self.assertEqual(len(self.game.monsters), 2)
        self.assertGreater(len(self.game.cherries), 0)

    def test_02_mr_do_movement_and_digging(self):
        # Initial position in pre-dug tunnel (7.5, 13.0)
        self.game.px = 6.0
        self.game.py = 13.0
        # Cell (5, 13) has dirt initially
        self.assertTrue(self.game.dirt[13][5])
        initial_score = self.game.score

        # Move left into cell (5, 13)
        for _ in range(5):
            self.game.update(0.05, keys_down=KEY_LEFT)

        self.assertLess(self.game.px, 6.0)
        self.assertFalse(self.game.dirt[13][5]) # Soil dug out!
        self.assertGreater(self.game.score, initial_score)

    def test_03_eat_cherry_scoring(self):
        cherry = next(iter(self.game.cherries))
        cx, cy = cherry
        # Clear dirt first to isolate cherry collection score
        self.game.dirt[cy][cx] = False
        self.game.px = float(cx)
        self.game.py = float(cy)
        initial_score = self.game.score
        initial_cherries = len(self.game.cherries)

        self.game.update(0.01, keys_down=KEY_UP)
        self.assertEqual(len(self.game.cherries), initial_cherries - 1)
        self.assertEqual(self.game.score, initial_score + 50)

    def test_04_throw_power_ball(self):
        self.assertFalse(self.game.ball["active"])
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertTrue(self.game.ball["active"])
        self.assertEqual(self.game.ball["x"], self.game.px)
        self.assertLess(self.game.ball["y"], self.game.py)

    def test_05_power_ball_ricochet_and_monster_kill(self):
        # Place monster at (8.0, 5.0)
        m = self.game.monsters[0]
        m["x"] = 8.0
        m["y"] = 5.0
        m["alive"] = True

        # Throw ball at monster
        self.game.ball["active"] = True
        self.game.ball["x"] = 8.0
        self.game.ball["y"] = 5.2
        self.game.ball["vx"] = 0.0
        self.game.ball["vy"] = -10.0
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(m["alive"])
        self.assertFalse(self.game.ball["active"]) # Ball recovered on impact
        self.assertEqual(self.game.score, initial_score + 500)

    def test_06_catch_power_ball_on_return(self):
        self.game.px = 7.0
        self.game.py = 7.0
        self.game.ball["active"] = True
        self.game.ball["cooldown"] = 0.0
        self.game.ball["x"] = 7.1
        self.game.ball["y"] = 7.1

        self.game.update(0.01)
        self.assertFalse(self.game.ball["active"]) # Caught by Mr. Do

    def test_07_push_apple_horizontally(self):
        # Apple at (8.0, 7.0)
        apple = self.game.apples[2]
        self.assertEqual(apple["x"], 8.0)
        self.assertEqual(apple["y"], 7.0)

        # Place Mr. Do to the left of apple and push right
        self.game.px = 7.4
        self.game.py = 7.0
        for _ in range(5):
            self.game.update(0.05, keys_down=KEY_RIGHT)

        self.assertGreater(apple["x"], 8.0)

    def test_08_apple_falls_and_crushes_monster(self):
        apple = self.game.apples[0]
        apple["x"] = 4.0
        apple["y"] = 4.0
        # Clear dirt shaft underneath apple for rows 5..8
        for y in range(5, 9):
            self.game.dirt[y][4] = False

        # Place monster below apple at (4.0, 7.0)
        m = self.game.monsters[0]
        m["x"] = 4.0
        m["y"] = 7.0
        m["speed"] = 0.0 # Stay in position
        m["alive"] = True
        self.game.px = 12.0 # Far away safe

        # Wobble
        self.game.update(0.5)
        self.assertTrue(apple["falling"])

        # Fall downwards onto monster
        for _ in range(15):
            self.game.update(0.05)

        self.assertFalse(m["alive"])
        self.assertGreaterEqual(self.game.score, 1000)

    def test_09_all_cherries_collected_stage_clear(self):
        self.game.cherries.clear()
        self.game.cherries.add((3, 3))
        self.game.px = 3.0
        self.game.py = 3.0

        self.game.update(0.01, keys_down=KEY_UP)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 3000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_PLAYER_DIED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
