import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_078_karatechamp import (
    Game078KarateChamp,
    STATE_FIGHT,
    STATE_POINT_SCORED,
    STATE_ROUND_WIN,
    STATE_BONUS_STAGE,
    STATE_GAME_OVER,
    ATK_NONE,
    ATK_HIGH_KICK,
    ATK_MID_PUNCH,
    ATK_LOW_SWEEP,
    ATK_BLOCK,
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


class TestGame078KarateChamp(unittest.TestCase):
    def setUp(self):
        self.game = Game078KarateChamp()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 78)
        self.assertEqual(self.game.name, "经典空手道")
        self.assertEqual(self.game.english_name, "Karate Champ")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("双摇杆格斗鼻祖", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_FIGHT)
        self.assertEqual(status["player_points"], 0)
        self.assertEqual(status["cpu_points"], 0)
        self.assertEqual(status["dan_level"], 1)
        self.assertEqual(self.game.px, 4.0)
        self.assertEqual(self.game.cx, 11.0)

    def test_horizontal_movement_and_spacing(self):
        # Move forward (right)
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 4.0)

        # Ensure player cannot walk through CPU (minimum spacing constraint)
        self.game.cx = 6.0
        self.game.px = 5.0
        self.game.update(0.1, KEY_RIGHT, KEY_RIGHT)
        self.assertLessEqual(self.game.px, self.game.cx - 1.4)

    def test_mid_punch_waza_ari(self):
        # Close in distance
        self.game.px = 5.0
        self.game.cx = 7.0  # dist = 2.0 <= 2.2
        self.game.c_attack = ATK_NONE

        # Player inputs Mid Punch
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.p_attack, ATK_MID_PUNCH)

        # Advance tick to trigger hit detection
        self.game.update(0.08, 0, KEY_A)
        self.assertEqual(self.game.state, STATE_POINT_SCORED)
        self.assertEqual(self.game.player_points, 1)  # Waza-ari = 1 pt
        self.assertEqual(self.game.judge_call, "WAZA-ARI")

    def test_high_kick_ippon(self):
        self.game.reset()
        self.game.px = 5.0
        self.game.cx = 7.0
        self.game.c_attack = ATK_NONE

        # Player inputs High Kick (A + UP)
        self.game.update(0.05, KEY_A | KEY_UP, 0)
        self.assertEqual(self.game.p_attack, ATK_HIGH_KICK)

        # Advance tick to connect
        self.game.update(0.08, 0, KEY_A | KEY_UP)
        self.assertEqual(self.game.state, STATE_POINT_SCORED)
        self.assertEqual(self.game.player_points, 2)  # Ippon = 2 pts
        self.assertEqual(self.game.judge_call, "IPPON")

    def test_low_sweep_ippon(self):
        self.game.reset()
        self.game.px = 5.0
        self.game.cx = 7.0
        self.game.c_attack = ATK_NONE

        # Player inputs Low Sweep (B + DOWN)
        self.game.update(0.05, KEY_B | KEY_DOWN, 0)
        self.assertEqual(self.game.p_attack, ATK_LOW_SWEEP)

        # Connect
        self.game.update(0.08, 0, KEY_B | KEY_DOWN)
        self.assertEqual(self.game.state, STATE_POINT_SCORED)
        self.assertEqual(self.game.player_points, 2)
        self.assertEqual(self.game.judge_call, "IPPON")

    def test_block_stance_negates_hit(self):
        self.game.reset()
        self.game.px = 5.0
        self.game.cx = 7.0

        # CPU attacks with Mid Punch
        self.game.c_attack = ATK_MID_PUNCH
        self.game.c_atk_timer = 0.25

        # Player blocks (B)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.p_attack, ATK_BLOCK)

        # Next tick: attack is blocked, no score awarded to CPU
        self.game.update(0.08, KEY_B, KEY_B)
        self.assertEqual(self.game.cpu_points, 0)
        self.assertEqual(self.game.state, STATE_FIGHT)

    def test_round_win_and_dan_progression(self):
        self.game.reset()
        self.game.player_points = 2
        self.game.state = STATE_POINT_SCORED
        self.game.state_timer = 1.5

        # Update will trigger round win
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_ROUND_WIN)
        self.assertEqual(self.game.rounds_won, 1)

    def test_bonus_stage_breaking(self):
        self.game.start_bonus_stage()
        self.assertEqual(self.game.state, STATE_BONUS_STAGE)
        self.game.bonus_obj_x = 5.8
        self.game.px = 5.0

        # Strike flying ceramic vase
        old_score = self.game.score
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.bonus_obj_broken)
        self.assertGreater(self.game.score, old_score)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
