import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_085_renegade import (
    Game085Renegade,
    STATE_FIGHT,
    STATE_VICTORY,
    STATE_HERO_DEAD,
    ACT_IDLE,
    ACT_FRONT_PUNCH,
    ACT_BACK_ELBOW,
    ACT_GROUND_POUND,
    ACT_JUMP_KICK,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)


class TestGame085Renegade(unittest.TestCase):
    def setUp(self):
        self.game = Game085Renegade()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 85)
        self.assertEqual(self.game.name, "热血硬派")
        self.assertEqual(self.game.english_name, "Renegade")
        self.assertEqual(self.game.release_year, 1986)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("反手肘击与骑乘颜面猛揍", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_FIGHT)
        self.assertEqual(status["hero_hp"], 100)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["action"], ACT_IDLE)
        self.assertEqual(self.game.px, 4.0)
        self.assertEqual(self.game.py, 10.0)

    def test_horizontal_vertical_movement(self):
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 4.0)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.py, 10.0)

    def test_front_punch_and_knockdown(self):
        self.game.px = 4.0
        self.game.py = 10.0
        self.game.facing = 1

        self.game.thugs[0]["x"] = 5.0
        self.game.thugs[0]["y"] = 10.0
        self.game.thugs[0]["hp"] = 2
        self.game.thugs[0]["is_down"] = False
        self.game.thugs[0]["active"] = True

        # Front punch
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.action, ACT_FRONT_PUNCH)
        self.assertEqual(self.game.thugs[0]["hp"], 1)
        self.assertTrue(self.game.thugs[0]["is_down"])

    def test_mounted_ground_pound(self):
        self.game.px = 5.0
        self.game.py = 10.0
        self.game.thugs[0]["x"] = 5.0
        self.game.thugs[0]["y"] = 10.0
        self.game.thugs[0]["hp"] = 2
        self.game.thugs[0]["is_down"] = True
        self.game.thugs[0]["active"] = True

        # When over downed thug, A triggers ground pound!
        old_score = self.game.score
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.action, ACT_GROUND_POUND)
        self.assertEqual(self.game.thugs[0]["hp"], 0)
        self.assertFalse(self.game.thugs[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_backhand_elbow_strike(self):
        self.game.px = 8.0
        self.game.py = 10.0
        self.game.facing = 1  # facing right

        # Place thug behind hero at x = 7.0
        self.game.thugs[0]["x"] = 7.0
        self.game.thugs[0]["y"] = 10.0
        self.game.thugs[0]["hp"] = 3
        self.game.thugs[0]["active"] = True

        # Back elbow (B)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.action, ACT_BACK_ELBOW)
        self.assertEqual(self.game.thugs[0]["hp"], 1)
        self.assertLess(self.game.thugs[0]["x"], 7.0) # knocked backwards

    def test_jump_kick_knockback(self):
        self.game.px = 5.0
        self.game.py = 10.0
        self.game.facing = 1
        self.game.thugs[0]["x"] = 6.2
        self.game.thugs[0]["y"] = 10.0
        self.game.thugs[0]["active"] = True

        # Flying jump kick (A + B)
        self.game.update(0.05, KEY_A | KEY_B, 0)
        self.assertEqual(self.game.action, ACT_JUMP_KICK)
        self.assertGreaterEqual(self.game.thugs[0]["x"], 8.5)
        self.assertTrue(self.game.thugs[0]["is_down"])

    def test_track_hazard_train_crush(self):
        # Position thug on tracks (y = 14.0 >= 13.8)
        self.game.thugs[0]["x"] = 5.0
        self.game.thugs[0]["y"] = 14.0
        self.game.thugs[0]["active"] = True

        # Move train directly across thug's position
        self.game.train_x = 5.0
        old_score = self.game.score

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.thugs[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_thugs_cleared_victory(self):
        self.game.thugs_defeated = 8
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 8000)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
