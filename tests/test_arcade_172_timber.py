# -*- coding: utf-8 -*-
import unittest
from arcade.game_172_timber import (
    Game172Timber,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_CRUSHED,
    STATE_GAME_OVER,
    TREE_STANDING,
    TREE_FALLING,
    TREE_FELLED,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

class TestArcade172Timber(unittest.TestCase):
    def setUp(self):
        self.game = Game172Timber()
        # Keep creatures disabled or parked away unless specifically tested
        self.game.bear_alive = False
        self.game.bee_alive = False

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 172)
        self.assertEqual(self.game.name, "伐木工")
        self.assertEqual(self.game.english_name, "Timber")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.left_tree_state, TREE_STANDING)
        self.assertEqual(self.game.right_tree_state, TREE_STANDING)
        self.assertGreater(self.game.left_chops, 0)

    def test_02_movement_and_boundary_clamping(self):
        # Move left
        self.game.px = 7.5
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.px, 7.5)
        self.assertEqual(self.game.facing, -1)

        # Move to extreme left boundary
        for _ in range(20):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 3.0)

        # Move to extreme right boundary
        for _ in range(40):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.px, 12.0)
        self.assertEqual(self.game.facing, 1)

    def test_03_chop_left_tree_reduces_chops_and_scores(self):
        self.game.px = 3.2
        self.game.facing = -1
        initial_chops = self.game.left_chops
        initial_score = self.game.score

        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.left_chops, initial_chops - 1)
        self.assertEqual(self.game.score, initial_score + 50)
        self.assertGreater(self.game.axe_timer, 0.0)

    def test_04_chop_right_tree_reduces_chops_and_scores(self):
        self.game.px = 11.8
        self.game.facing = 1
        initial_chops = self.game.right_chops
        initial_score = self.game.score

        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.right_chops, initial_chops - 1)
        self.assertEqual(self.game.score, initial_score + 50)

    def test_05_felled_tree_begins_falling(self):
        self.game.px = 3.2
        self.game.facing = -1
        self.game.left_chops = 1

        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.left_chops, 0)
        self.assertEqual(self.game.left_tree_state, TREE_FALLING)
        self.assertGreater(self.game.left_fall_timer, 0.0)

    def test_06_player_in_danger_zone_crushed_by_falling_tree(self):
        # Left tree is falling, player stays at x=3.2 (danger zone <= 6.5)
        self.game.left_tree_state = TREE_FALLING
        self.game.left_fall_timer = 0.25 # within danger window (<0.3)
        self.game.px = 3.2
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_PLAYER_CRUSHED)

    def test_07_player_escapes_danger_zone_tree_crashes_safely(self):
        # Left tree is falling, player flees right to x=8.0 (safe zone)
        self.game.left_tree_state = TREE_FALLING
        self.game.left_fall_timer = 0.05
        self.game.px = 8.0
        initial_score = self.game.score

        # Elapse the remaining fall timer
        self.game.update(0.1)
        self.assertEqual(self.game.left_tree_state, TREE_FELLED)
        self.assertEqual(self.game.score, initial_score + 500)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_08_falling_tree_crushes_bear(self):
        self.game.left_tree_state = TREE_FALLING
        self.game.left_fall_timer = 0.25
        self.game.px = 8.0 # Player safe
        self.game.bear_alive = True
        self.game.bear_x = 5.0 # Bear in crash zone
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(self.game.bear_alive)
        self.assertEqual(self.game.score, initial_score + 800)

    def test_09_swat_bee_with_axe(self):
        self.game.px = 7.0
        self.game.facing = 1
        self.game.bee_alive = True
        self.game.bee_x = 7.8
        self.game.bee_y = 13.0
        initial_score = self.game.score

        # Swing axe at bee
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertFalse(self.game.bee_alive)
        self.assertEqual(self.game.score, initial_score + 300)

    def test_10_both_trees_felled_triggers_stage_clear_and_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.left_tree_state = TREE_FELLED
        self.game.right_tree_state = TREE_FALLING
        self.game.right_fall_timer = 0.05
        self.game.px = 5.0 # Safe from right tree

        self.game.update(0.1)
        self.assertEqual(self.game.right_tree_state, TREE_FELLED)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 2000)

if __name__ == "__main__":
    unittest.main()

