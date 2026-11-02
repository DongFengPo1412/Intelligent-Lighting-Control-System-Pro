import unittest
from arcade.game_099_joust import (
    Game099Joust,
    STATE_JOUSTING,
    STATE_KNIGHT_DOWN,
    STATE_WAVE_CLEAR,
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


class TestGame099Joust(unittest.TestCase):
    def setUp(self):
        self.game = Game099Joust()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 99)
        self.assertEqual(self.game.name, "鸵鸟骑士")
        self.assertEqual(self.game.english_name, "Joust")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("扑翼升空惯性滑翔", self.game.core_mechanic)

    def test_horizontal_locomotion_and_wraparound(self):
        self.game.px = 15.8
        self.game.vx = 4.0
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertLess(self.game.px, 2.0)  # Wrapped around to left edge

    def test_wing_flap_lift(self):
        self.assertTrue(self.game.on_platform)
        init_score = self.game.score
        # Press button A (flap)
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.on_platform)
        self.assertLess(self.game.vy, 0.0)
        self.assertEqual(self.game.score, init_score + 5)

    def test_platform_landing(self):
        self.game.on_platform = False
        self.game.px = 6.0
        self.game.py = 7.7
        self.game.vy = 2.0  # Falling down onto middle platform (y=8.0)
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.py, 8.0)
        self.assertEqual(self.game.vy, 0.0)
        self.assertTrue(self.game.on_platform)

    def test_joust_higher_altitude_wins(self):
        # Enemy at (8.0, 8.0)
        self.game.enemies[0]["x"] = 8.0
        self.game.enemies[0]["y"] = 8.0
        self.game.enemies[0]["active"] = True

        # Hero at (8.0, 7.3) -> higher than enemy by 0.7 units (smaller y)
        self.game.px = 8.0
        self.game.py = 7.3
        self.game.on_platform = False
        init_score = self.game.score

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertGreater(self.game.score, init_score)
        self.assertEqual(self.game.knights_defeated, 1)

    def test_joust_lower_altitude_loses(self):
        # Enemy at (8.0, 7.0)
        self.game.enemies[0]["x"] = 8.0
        self.game.enemies[0]["y"] = 7.0
        self.game.enemies[0]["active"] = True

        # Hero at (8.0, 7.8) -> lower than enemy (larger y)
        self.game.px = 8.0
        self.game.py = 7.8
        self.game.on_platform = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_KNIGHT_DOWN)

    def test_joust_equal_altitude_clang(self):
        # Enemy at (8.5, 7.0) moving left
        self.game.enemies[0]["x"] = 8.5
        self.game.enemies[0]["y"] = 7.0
        self.game.enemies[0]["vx"] = -2.0
        self.game.enemies[0]["active"] = True

        # Hero at (8.0, 7.0) moving right
        self.game.px = 8.0
        self.game.py = 7.0
        self.game.vx = 2.0
        self.game.on_platform = False

        self.game.update(0.05, 0, 0)
        # Clanged! Hero and enemy rebound
        self.assertLess(self.game.vx, 0.0)
        self.assertGreater(self.game.enemies[0]["vx"], 0.0)

    def test_egg_collection(self):
        self.game.eggs[0]["active"] = True
        self.game.eggs[0]["x"] = 5.0
        self.game.eggs[0]["y"] = 8.0
        self.game.eggs[0]["hatch_timer"] = 5.0

        self.game.px = 5.0
        self.game.py = 8.0
        init_score = self.game.score

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.eggs[0]["active"])
        self.assertEqual(self.game.score, init_score + 250)

    def test_lava_grab_and_escape(self):
        # Drop into lava pit (x=7.0, y=14.6)
        self.game.px = 7.0
        self.game.py = 14.6
        self.game.on_platform = False
        self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.grabbed_by_lava)

        # Flap 1
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.grabbed_by_lava)

        # Flap 2
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.grabbed_by_lava)

        # Flap 3 -> Escapes!
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.grabbed_by_lava)
        self.assertLess(self.game.vy, 0.0)

    def test_wave_clear_and_render(self):
        self.game.knights_defeated = 3
        # Defeat 4th knight
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 6.0
        self.game.enemies[0]["active"] = True
        self.game.px = 6.0
        self.game.py = 5.4
        self.game.on_platform = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_WAVE_CLEAR)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
