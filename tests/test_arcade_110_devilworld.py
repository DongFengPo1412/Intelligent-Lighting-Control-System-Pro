import unittest
from arcade.game_110_devilworld import (
    Game110DevilWorld,
    STATE_NAVIGATING,
    STATE_CRUSHED,
    STATE_ROUND_CLEAR,
    STATE_GAME_OVER,
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


class TestGame110DevilWorld(unittest.TestCase):
    def setUp(self):
        self.game = Game110DevilWorld()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 110)
        self.assertEqual(self.game.name, "魔鬼世界")
        self.assertEqual(self.game.english_name, "Devil World")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("大魔王顶部指点江山", self.game.core_mechanic)

    def test_tamagon_corridor_movement(self):
        # Open corridor at (8, 8)
        init_x = self.game.px
        # Move left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.px, init_x)
        self.assertEqual(self.game.facing_x, -1)

    def test_devil_points_and_shifts_maze(self):
        self.game.px = 8.0
        # Devil points Left (dir=1)
        self.game.set_devil_direction(1)
        self.game.update(0.05, 0, 0)
        # Shifted left
        self.assertLess(self.game.px, 8.0)

    def test_wall_crush_flattened(self):
        # Pushed to left edge against perimeter
        self.game.px = 0.5
        self.game.py = 8.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRUSHED)

    def test_pickup_holy_cross(self):
        self.assertFalse(self.game.has_cross)
        self.game.maze[12][8] = 0  # Clear pearl at cross position
        self.game.px = self.game.cross_x
        self.game.py = self.game.cross_y

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.has_cross)
        self.assertFalse(self.game.cross_spawned)
        self.assertEqual(self.game.score, init_score + 300)

    def test_fire_breath_fries_monster(self):
        self.game.maze[4][6] = 0  # Clear pearl
        self.game.has_cross = True
        self.game.px = 6.0
        self.game.py = 4.0
        self.game.facing_x = 1
        self.game.facing_y = 0

        # Monster ahead at (7.5, 4.0)
        self.game.monsters[0]["active"] = True
        self.game.monsters[0]["x"] = 7.5
        self.game.monsters[0]["y"] = 4.0
        self.game.monsters[0]["is_fried_egg"] = False

        init_score = self.game.score
        # Press Button A to breathe fire
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.monsters[0]["is_fried_egg"])
        self.assertEqual(self.game.score, init_score + 100)

    def test_devour_fried_egg(self):
        self.game.maze[4][6] = 0  # Clear pearl
        self.game.monsters[0]["active"] = True
        self.game.monsters[0]["is_fried_egg"] = True
        self.game.monsters[0]["egg_timer"] = 5.0
        self.game.monsters[0]["x"] = 6.0
        self.game.monsters[0]["y"] = 4.0

        self.game.px = 6.0
        self.game.py = 4.0

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.monsters[0]["active"])
        self.assertEqual(self.game.score, init_score + 400)

    def test_monster_touches_tamagon_kills(self):
        self.game.monsters[0]["active"] = True
        self.game.monsters[0]["is_fried_egg"] = False
        self.game.monsters[0]["x"] = 8.0
        self.game.monsters[0]["y"] = 8.0

        self.game.px = 8.0
        self.game.py = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRUSHED)

    def test_eat_all_pearls_round_clear(self):
        self.game.pearls_remaining = 0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
