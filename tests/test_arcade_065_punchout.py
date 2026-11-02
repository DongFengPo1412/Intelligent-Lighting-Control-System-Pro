import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_065_punchout import (
    Game065PunchOut,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    ACT_IDLE,
    ACT_DODGE_LEFT,
    ACT_DODGE_RIGHT,
    ACT_DUCK,
    ACT_BLOCK,
    ACT_PUNCH_LEFT,
    ACT_PUNCH_RIGHT,
    ACT_DOWN,
    OPP_IDLE,
    OPP_PREP_LEFT_HOOK,
    OPP_PREP_RIGHT_HOOK,
    OPP_PREP_BULL_CHARGE,
    OPP_SWING,
    OPP_STUNNED,
    OPP_HURT,
    OPP_DOWN,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade065PunchOut(unittest.TestCase):
    def setUp(self):
        self.game = Game065PunchOut()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 65)
        self.assertEqual(self.game.english_name, "Punch-Out!!")
        self.assertEqual(self.game.release_year, 1983)
        cart = ArcadeRegistry.get_cartridge(65)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game065PunchOut)

    def test_dodge_left_and_right(self):
        self.game.update(0.02, KEY_LEFT, 0)
        self.assertEqual(self.game.player_action, ACT_DODGE_LEFT)
        self.assertLess(self.game.dodge_offset_x, 0)

        # Let action expire back to idle
        self.game.update(0.40, 0, 0)
        self.assertEqual(self.game.player_action, ACT_IDLE)

        self.game.update(0.02, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_action, ACT_DODGE_RIGHT)
        self.assertGreater(self.game.dodge_offset_x, 0)

    def test_duck_and_block(self):
        self.game.update(0.02, KEY_DOWN, 0)
        self.assertEqual(self.game.player_action, ACT_DUCK)
        self.assertGreater(self.game.duck_offset_y, 0)

        self.game.update(0.40, 0, 0)
        self.assertEqual(self.game.player_action, ACT_IDLE)

        self.game.update(0.02, KEY_UP, 0)
        self.assertEqual(self.game.player_action, ACT_BLOCK)

    def test_punch_blocked_when_opponent_guarding(self):
        self.game.opp_action = OPP_IDLE
        initial_opp_stamina = self.game.opp_stamina
        initial_score = self.game.score

        # Player throws left jab
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(self.game.player_action, ACT_PUNCH_LEFT)
        # Blocked: stamina unaffected, small score
        self.assertEqual(self.game.opp_stamina, initial_opp_stamina)
        self.assertGreater(self.game.score, initial_score)

    def test_dodge_opponent_hook_causes_stun(self):
        # Opponent telegraphs right hook (which swings toward player's right, evadable by dodge left or duck)
        self.game.opp_action = OPP_PREP_RIGHT_HOOK
        self.game.opp_attack_type = 2
        self.game.opp_timer = 0.05

        # Player dodges left
        self.game.update(0.02, KEY_LEFT, 0)
        self.assertEqual(self.game.player_action, ACT_DODGE_LEFT)

        # Advance time so opponent punch executes during dodge
        self.game.update(0.04, 0, 0)
        self.assertEqual(self.game.opp_action, OPP_STUNNED)
        self.assertGreater(self.game.opp_timer, 0.5)

    def test_counter_punch_during_stun_damages_opponent(self):
        self.game.opp_action = OPP_STUNNED
        self.game.opp_timer = 0.7
        self.game.player_action = ACT_IDLE
        initial_stamina = self.game.opp_stamina

        # Punch stunned opponent
        self.game.punch(0)
        self.assertLess(self.game.opp_stamina, initial_stamina)
        self.assertEqual(self.game.opp_action, OPP_HURT)
        self.assertGreaterEqual(self.game.score, 100)

    def test_star_accumulation_and_super_uppercut(self):
        self.assertEqual(self.game.stars, 0)
        # Perfect counter punch while opponent is preparing attack grants a star!
        self.game.opp_action = OPP_PREP_BULL_CHARGE
        self.game.player_action = ACT_IDLE
        self.game.punch(0)
        self.assertGreaterEqual(self.game.stars, 1)

        # Throw right super uppercut with star
        stamina_before = self.game.opp_stamina
        self.game.opp_action = OPP_STUNNED
        self.game.player_action = ACT_IDLE
        self.game.punch(1)
        self.assertEqual(self.game.opp_stamina, stamina_before - 40)  # Super damage!
        self.assertEqual(self.game.stars, 0)  # Star consumed

    def test_player_hit_and_knockdown_recovery(self):
        self.game.player_stamina = 10
        self.game.opp_action = OPP_PREP_BULL_CHARGE
        self.game.opp_attack_type = 3
        self.game.opp_timer = 0.01
        self.game.player_action = ACT_IDLE  # No dodge!

        # Opponent charge lands
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.player_action, ACT_DOWN)
        self.assertEqual(self.game.player_downs, 1)

        # Player taps A repeatedly to get back up
        for _ in range(4):
            self.game.update(0.02, KEY_A, 0)
            self.game.update(0.02, 0, KEY_A)
        self.assertEqual(self.game.player_action, ACT_IDLE)
        self.assertGreaterEqual(self.game.player_stamina, 50)

    def test_opponent_knockdown_and_tko_victory(self):
        self.game.opp_downs = 2
        self.game.opp_stamina = 10
        self.game.opp_action = OPP_STUNNED
        self.game.player_action = ACT_IDLE

        # Final knockdown for 3rd knockdown TKO!
        self.game.punch(0)
        self.assertEqual(self.game.opp_downs, 3)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 3000)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 65)
        self.assertEqual(status["name"], "超级拳击")


if __name__ == "__main__":
    unittest.main()
