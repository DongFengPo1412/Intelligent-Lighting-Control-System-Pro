# -*- coding: utf-8 -*-
import unittest
from arcade.game_171_ladybug import (
    Game171LadyBug,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_LADYBUG_DIED,
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

class TestArcade171LadyBug(unittest.TestCase):
    def setUp(self):
        self.game = Game171LadyBug()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 171)
        self.assertEqual(self.game.name, "瓢虫大冒险")
        self.assertEqual(self.game.english_name, "Lady Bug")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.multiplier, 1)
        self.assertGreater(self.game.remaining_dots(), 0)

    def test_02_ladybug_movement_and_bounds(self):
        initial_px = self.game.px
        initial_py = self.game.py
        # Move up
        self.game.update(0.1, keys_down=KEY_UP)
        self.assertLess(self.game.py, initial_py)
        # Move left
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.px, initial_px)

    def test_03_eat_dots_and_scoring(self):
        # Place ladybug right on an existing dot
        dot = next(iter(self.game.dots))
        self.game.px = float(dot[0])
        self.game.py = float(dot[1])
        initial_dots = self.game.remaining_dots()
        initial_score = self.game.score

        self.game.update(0.01) # Trigger dot eating
        self.assertEqual(self.game.remaining_dots(), initial_dots - 1)
        self.assertEqual(self.game.score, initial_score + 10)

    def test_04_collect_heart_multiplier(self):
        # Place ladybug on heart (7, 2)
        self.game.px = 7.0
        self.game.py = 2.0
        initial_mult = self.game.multiplier
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertEqual(self.game.multiplier, initial_mult + 1)
        self.assertEqual(self.game.score, initial_score + 300)
        self.assertNotIn((7, 2), self.game.hearts)

    def test_05_revolving_turnstile_flip(self):
        # Turnstile at (4, 5) initially "H"
        t = next(ts for ts in self.game.turnstiles if ts["x"] == 4 and ts["y"] == 5)
        self.assertEqual(t["ori"], "H")

        # Lady Bug moves into contact with turnstile (4, 5)
        self.game.px = 4.0
        self.game.py = 5.5
        initial_score = self.game.score
        self.game.update(0.1, keys_down=KEY_UP)

        # Orientation flipped to "V" and bonus points awarded
        self.assertEqual(t["ori"], "V")
        self.assertEqual(self.game.score, initial_score + 50)

    def test_06_beetle_turnstile_block(self):
        # Turnstile at (4, 5) orientation "H" blocks vertical movement
        t = next(ts for ts in self.game.turnstiles if ts["x"] == 4 and ts["y"] == 5)
        self.assertEqual(t["ori"], "H")

        # Place beetle at (4.0, 5.5) and player above at (4.0, 2.0)
        self.game.px = 4.0
        self.game.py = 2.0
        self.game.beetles[0]["x"] = 4.0
        self.game.beetles[0]["y"] = 5.5
        self.game.beetles[1]["alive"] = False

        prev_by = self.game.beetles[0]["y"]
        # Update AI - movement upwards towards y=2.0 is blocked by turnstile at y=5.0
        self.game.update(0.1)
        self.assertEqual(self.game.beetles[0]["y"], prev_by)

    def test_07_beetle_poison_skull_destruction(self):
        # Skull at (4, 8)
        # Place beetle directly on skull (4.0, 8.0)
        self.game.beetles[0]["x"] = 4.0
        self.game.beetles[0]["y"] = 8.0
        self.game.px = 1.0 # Far away
        self.game.py = 1.0
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(self.game.beetles[0]["alive"])
        self.assertEqual(self.game.score, initial_score + 1000)

    def test_08_ladybug_poison_skull_death(self):
        # Skull at (4, 8)
        # Place Lady Bug directly on skull
        self.game.px = 4.0
        self.game.py = 8.0
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_LADYBUG_DIED)

    def test_09_all_dots_stage_clear(self):
        self.game.dots.clear()
        # Add 1 remaining dot
        self.game.dots.add((2, 2))
        self.game.px = 2.0
        self.game.py = 2.0

        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 2000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_LADYBUG_DIED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
