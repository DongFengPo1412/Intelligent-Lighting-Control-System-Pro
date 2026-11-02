import unittest
from arcade.game_103_dkjr import (
    Game103DKJr,
    STATE_CLIMBING,
    STATE_STAGE_CLEAR,
    STATE_FALL_DOWN,
    STATE_GAME_OVER,
    VINE_X,
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


class TestGame103DKJr(unittest.TestCase):
    def setUp(self):
        self.game = Game103DKJr()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 103)
        self.assertEqual(self.game.name, "大金刚二代")
        self.assertEqual(self.game.english_name, "Donkey Kong Jr.")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("单双藤蔓攀爬升降差速", self.game.core_mechanic)

    def test_ground_locomotion(self):
        self.assertTrue(self.game.on_ground)
        init_x = self.game.px
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, init_x)

    def test_single_vine_climb_rates(self):
        # Place Junior on single vine 0 at (2.0, 10.0)
        self.game.px = 2.0
        self.game.py = 10.0
        self.game.current_vine = 0
        self.game.on_ground = False
        self.game.gripping_two_vines = False

        # Climb UP (speed = 3.0)
        self.game.update(0.05, KEY_UP, 0)
        self.assertAlmostEqual(self.game.py, 10.0 - 3.0 * 0.05, places=3)

        # Slide DOWN (speed = 7.5)
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertAlmostEqual(self.game.py, 10.0 - 3.0 * 0.05 + 7.5 * 0.05, places=3)

    def test_dual_vine_grip_and_rates(self):
        # Place Junior on single vine 0 at y=8.0, then press RIGHT to grab dual vine
        self.game.px = 2.0
        self.game.py = 8.0
        self.game.current_vine = 0
        self.game.on_ground = False
        self.game.gripping_two_vines = False

        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertTrue(self.game.gripping_two_vines)
        self.assertEqual(self.game.px, (VINE_X[0] + VINE_X[1]) * 0.5)

        # Dual vine climb UP is fast (6.0)
        init_y = self.game.py
        self.game.update(0.05, KEY_UP, 0)
        self.assertAlmostEqual(self.game.py, init_y - 6.0 * 0.05, places=3)

        # Dual vine slide DOWN is slow (2.5)
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertAlmostEqual(self.game.py, init_y - 6.0 * 0.05 + 2.5 * 0.05, places=3)

    def test_jump_between_vines(self):
        # Place on vine 0 at y=8.0
        self.game.px = 2.0
        self.game.py = 8.0
        self.game.current_vine = 0
        self.game.on_ground = False
        self.game.gripping_two_vines = False

        # Jump to right
        self.game.update(0.05, KEY_A | KEY_RIGHT, 0)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.vy, 0.0)
        self.assertGreater(self.game.vx, 0.0)

    def test_fruit_dislodge_and_crush_snapjaw(self):
        fruit = self.game.fruits[0]
        self.assertFalse(fruit["falling"])

        # Junior touches fruit at (VINE_X[1], 5.0)
        self.game.px = fruit["x"]
        self.game.py = fruit["y"]

        # Place Snapjaw beneath fruit at (VINE_X[1], 8.0)
        self.game.snapjaws[0]["active"] = True
        self.game.snapjaws[0]["x"] = fruit["x"]
        self.game.snapjaws[0]["y"] = 8.0

        init_score = self.game.score
        # Dislodge fruit
        self.game.update(0.05, 0, 0)
        self.assertTrue(fruit["falling"])
        self.assertEqual(self.game.score, init_score + 100)

        # Let fruit fall onto snapjaw
        fruit["y"] = 8.0
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.snapjaws[0]["active"])
        self.assertEqual(self.game.score, init_score + 100 + 400)

    def test_snapjaw_collision_kills_junior(self):
        self.game.px = 6.0
        self.game.py = 6.0
        self.game.snapjaws[0]["active"] = True
        self.game.snapjaws[0]["x"] = 6.0
        self.game.snapjaws[0]["y"] = 6.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_FALL_DOWN)

    def test_push_key_shackle(self):
        self.game.px = VINE_X[0]
        self.game.py = 2.3
        self.game.current_vine = 0
        self.game.on_ground = False
        self.game.gripping_two_vines = False
        self.assertFalse(self.game.keys_unlocked[0])

        init_score = self.game.score
        # Push key at y <= 2.2
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.keys_unlocked[0])
        self.assertEqual(self.game.keys_inserted, 1)
        self.assertEqual(self.game.score, init_score + 500)

    def test_stage_clear_all_keys(self):
        self.game.keys_inserted = 3
        self.game.keys_unlocked[0] = True
        self.game.keys_unlocked[1] = True
        self.game.keys_unlocked[2] = True
        self.game.keys_unlocked[3] = False

        # Push 4th key on vine 3
        self.game.px = VINE_X[3]
        self.game.py = 2.3
        self.game.current_vine = 3
        self.game.on_ground = False
        self.game.gripping_two_vines = False

        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.keys_inserted, 4)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
