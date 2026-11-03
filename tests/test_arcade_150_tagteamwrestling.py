# -*- coding: utf-8 -*-
"""
test_arcade_150_tagteamwrestling.py —— 街机游戏 #150 双打职业摔角 (Tag Team Wrestling 1983 / Data East & Technos) 单元测试
验证元数据、围绳弹性反冲、飞扑冲撞、锁技角力极速连打、拍手换人交替回血、裁判三秒数秒决杀与渲染
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_150_tagteamwrestling import (
    Game150TagTeamWrestling,
    STATE_NEUTRAL,
    STATE_REBOUNDING,
    STATE_GRAPPLE,
    STATE_DOWNED,
    STATE_PINFALL,
    STATE_MATCH_WON,
    STATE_MATCH_LOST,
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


class TestGame150TagTeamWrestling(unittest.TestCase):
    def setUp(self):
        self.game = Game150TagTeamWrestling()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 150)
        self.assertIn("双打职业摔角", self.game.name)
        self.assertEqual(self.game.english_name, "Tag Team Wrestling")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_NEUTRAL)
        self.assertEqual(self.game.p_hp, 100.0)
        self.assertEqual(self.game.o_hp, 100.0)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 150)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["p_hp"], 100.0)

    def test_02_movement_and_elastic_rope_rebound(self):
        self.game.px = 2.6
        self.game.py = 8.0
        # Run into left rope
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.state, STATE_REBOUNDING)
        self.assertGreater(self.game.pvx, 0.0)  # Rebound slingshot to the right

    def test_03_rebound_clothesline_hits_opponent(self):
        self.game.px = 9.0
        self.game.py = 8.0
        self.game.ox = 10.0
        self.game.oy = 8.0
        self.game.pvx = 8.0
        self.game.state = STATE_REBOUNDING

        initial_score = self.game.score
        initial_o_hp = self.game.o_hp

        # Update rebound step into opponent
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_DOWNED)
        self.assertLess(self.game.o_hp, initial_o_hp)
        self.assertGreaterEqual(self.game.score, initial_score + 400)

    def test_04_grapple_collision_initiates_lockup(self):
        self.game.px = 7.0
        self.game.py = 8.0
        self.game.ox = 7.5
        self.game.oy = 8.0

        # Collision triggers lock-up
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_GRAPPLE)
        self.assertEqual(self.game.grapple_meter, 0.0)

    def test_05_grapple_button_mashing_suplex(self):
        self.game.state = STATE_GRAPPLE
        self.game.grapple_meter = 25.0
        initial_score = self.game.score
        initial_o_hp = self.game.o_hp

        # Press KEY_A to overpower opponent
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_DOWNED)
        self.assertEqual(self.game.o_hp, initial_o_hp - 20.0)
        self.assertGreaterEqual(self.game.score, initial_score + 500)

    def test_06_tag_corner_swaps_partner_and_rests(self):
        # Walk to player corner at (2.5, 2.5)
        self.game.px = 3.0
        self.game.py = 3.0
        self.game.p_hp = 40.0
        self.game.partner_hp = 100.0

        initial_score = self.game.score
        # Press KEY_B to tag partner
        self.game.update(0.016, KEY_B, 0)
        self.assertTrue(self.game.partner_active)
        self.assertEqual(self.game.p_hp, 100.0)
        self.assertEqual(self.game.partner_hp, 40.0)
        self.assertGreaterEqual(self.game.score, initial_score + 300)

    def test_07_apron_partner_hp_regeneration(self):
        self.game.partner_active = False
        self.game.partner_hp = 50.0

        # Advance 1.0 second, apron partner recovers hp
        self.game.update(1.0, 0, 0)
        self.assertGreater(self.game.partner_hp, 50.0)

    def test_08_pinfall_referee_three_count_victory(self):
        self.game.state = STATE_DOWNED
        self.game.pinning_player = True
        self.game.o_hp = 0.0  # Opponent completely knocked out
        self.game.px = 8.0
        self.game.py = 8.0
        self.game.ox = 8.0
        self.game.oy = 8.0

        # Press KEY_A to pin!
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PINFALL)

        # Referee counts to 3.0 seconds
        initial_score = self.game.score
        self.game.update(3.1, 0, 0)
        self.assertEqual(self.game.state, STATE_MATCH_WON)
        self.assertGreaterEqual(self.game.score, initial_score + 2500)

    def test_09_opponent_pin_kickout_when_high_hp(self):
        self.game.state = STATE_PINFALL
        self.game.pinning_player = True
        self.game.o_hp = 100.0  # Full health opponent will kick out!
        self.game.pin_count = 1.6

        self.game.update(0.1, 0, 0)
        # Opponent kicks out, returning to neutral
        self.assertEqual(self.game.state, STATE_NEUTRAL)

    def test_10_render_and_match_loss_reset(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))

        # Test match loss when player is pinned and count reaches 3
        self.game.state = STATE_PINFALL
        self.game.pinning_player = False
        self.game.p_hp = 0.0
        initial_lives = self.game.lives

        self.game.update(3.1, 0, 0)
        self.assertEqual(self.game.state, STATE_MATCH_LOST)
        self.assertEqual(self.game.lives, initial_lives - 1)


if __name__ == "__main__":
    unittest.main()

