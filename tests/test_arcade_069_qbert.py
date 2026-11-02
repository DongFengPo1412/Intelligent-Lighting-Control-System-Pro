import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_069_qbert import (
    Game069Qbert,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    TOTAL_CUBES,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade069Qbert(unittest.TestCase):
    def setUp(self):
        self.game = Game069Qbert()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 69)
        self.assertEqual(self.game.english_name, "Q*bert")
        self.assertEqual(self.game.release_year, 1982)
        cart = ArcadeRegistry.get_cartridge(69)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game069Qbert)

    def test_diagonal_jumping_and_bounds(self):
        self.assertEqual(self.game.player_row, 0)
        self.assertEqual(self.game.player_col, 0)

        # Jump Down-Right (row 1, col 1) with KEY_DOWN
        self.game.update(0.02, KEY_DOWN, 0)
        self.assertEqual(self.game.player_row, 1)
        self.assertEqual(self.game.player_col, 1)

        # Let jump animation timer settle
        self.game.update(0.25, 0, 0)

        # Jump Up-Left (row 0, col 0) with KEY_UP
        self.game.update(0.02, KEY_UP, 0)
        self.assertEqual(self.game.player_row, 0)
        self.assertEqual(self.game.player_col, 0)

    def test_cube_color_flipping(self):
        self.assertEqual(self.game.cubes_flipped, 1)  # (0, 0) starts flipped
        # Jump to (1, 0) with KEY_LEFT
        self.game.update(0.02, KEY_LEFT, 0)
        self.assertEqual(self.game.player_row, 1)
        self.assertEqual(self.game.player_col, 0)
        self.assertEqual(self.game.cubes_flipped, 2)
        self.assertGreater(self.game.score, 0)

    def test_jumping_off_edge_is_fatal(self):
        # At (0, 0), jumping UP-LEFT jumps into empty space!
        self.game.jump(-1, -1)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_left_escape_disc_transports_and_tricks_coily(self):
        # Position at (2, 0)
        self.game.player_row = 2
        self.game.player_col = 0
        self.game.jump_anim_timer = 0.0

        self.game.coily["active"] = True
        self.game.coily["is_hatched"] = True

        # Jump left toward disc at (-1 on col)
        self.game.jump(0, -1)
        # Should teleport to apex (0, 0)
        self.assertEqual(self.game.player_row, 0)
        self.assertEqual(self.game.player_col, 0)
        self.assertFalse(self.game.disc_left_active)
        self.assertFalse(self.game.coily["active"])  # Tricked Coily plunged off pyramid!
        self.assertGreaterEqual(self.game.score, 1000)

    def test_right_escape_disc_transports_and_tricks_coily(self):
        # Position at (2, 2)
        self.game.player_row = 2
        self.game.player_col = 2
        self.game.jump_anim_timer = 0.0

        self.game.coily["active"] = True
        self.game.coily["is_hatched"] = True

        # Jump right toward disc at col=3
        self.game.jump(0, 1)
        self.assertEqual(self.game.player_row, 0)
        self.assertEqual(self.game.player_col, 0)
        self.assertFalse(self.game.disc_right_active)
        self.assertFalse(self.game.coily["active"])

    def test_coily_egg_to_snake_hatching_and_chase(self):
        self.game.coily["active"] = True
        self.assertFalse(self.game.coily["is_hatched"])
        # Move egg down to row 4
        self.game.coily["row"] = 3
        self.game.coily["jump_timer"] = 0.01
        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.coily["is_hatched"])

    def test_coily_collision_causes_death(self):
        self.game.coily["row"] = self.game.player_row
        self.game.coily["col"] = self.game.player_col
        self.game.coily["active"] = True

        self.game.check_collisions()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_green_ball_freezes_time(self):
        self.game.balls.append({
            "row": self.game.player_row,
            "col": self.game.player_col,
            "jump_timer": 1.0,
            "is_green": True,
            "active": True,
        })
        self.game.check_collisions()
        self.assertGreater(self.game.freeze_timer, 0.0)
        self.assertGreater(self.game.score, 0)

    def test_full_pyramid_flip_victory_and_render(self):
        # Flip 14 cubes
        for i in range(TOTAL_CUBES - 1):
            self.game.cube_flipped[i] = True
        self.game.cubes_flipped = TOTAL_CUBES - 1

        # Jump onto final cube (4, 4) (idx 14)
        self.game.player_row = 4
        self.game.player_col = 3
        self.game.jump_anim_timer = 0.0

        self.game.jump(0, 1)  # Land on (4, 4)
        self.assertEqual(self.game.cubes_flipped, TOTAL_CUBES)
        self.assertEqual(self.game.state, STATE_VICTORY)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
