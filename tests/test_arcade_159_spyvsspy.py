# -*- coding: utf-8 -*-
"""
test_arcade_159_spyvsspy.py —— 街机游戏 #159 间谍大战 (Spy vs Spy 1984 / First Star & Sega) 单元测试
验证元数据、使馆四舱室门禁穿梭、家具搜寻机密文件公文包、布置定时炸弹暗算黑间谍、徒手格斗与机场登机撤离
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_159_spyvsspy import (
    Game159SpyVsSpy,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SPY_BLOWN_UP,
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


class TestGame159SpyVsSpy(unittest.TestCase):
    def setUp(self):
        self.game = Game159SpyVsSpy()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 159)
        self.assertIn("间谍大战", self.game.name)
        self.assertEqual(self.game.english_name, "Spy vs Spy")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.rx, 0)
        self.assertEqual(self.game.ry, 0)
        self.assertFalse(self.game.has_briefcase)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 159)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["rx"], 0)

    def test_02_room_transition_doorways(self):
        # Walk right into door leading from (0,0) to (1,0)
        self.game.px = 14.2
        self.game.py = 7.5

        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.rx, 1)
        self.assertEqual(self.game.ry, 0)
        self.assertLess(self.game.px, 3.0)

    def test_03_search_furniture_finds_briefcase(self):
        # Desk is at (4.0, 5.0) in room (0,0)
        self.game.rx = 0
        self.game.ry = 0
        self.game.px = 4.0
        self.game.py = 5.0
        self.assertFalse(self.game.has_briefcase)

        initial_score = self.game.score
        # Press KEY_A to search desk
        self.game.update(0.016, KEY_A, 0)
        self.assertTrue(self.game.has_briefcase)
        self.assertEqual(self.game.score, initial_score + 500)

    def test_04_search_furniture_finds_item(self):
        # Coat rack is at (11.0, 11.0) in room (0,0), containing "money"
        self.game.rx = 0
        self.game.ry = 0
        self.game.px = 11.0
        self.game.py = 11.0

        initial_score = self.game.score
        self.game.update(0.016, KEY_A, 0)
        self.assertIn("money", self.game.items_found)
        self.assertEqual(self.game.score, initial_score + 250)

    def test_05_lay_booby_trap_with_key_b(self):
        # Safe is at (11.0, 5.0) in room (1,0)
        self.game.rx = 1
        self.game.ry = 0
        self.game.px = 11.0
        self.game.py = 5.0

        cur_key = self.game._get_current_key()
        safe = [f for f in self.game.furniture[cur_key] if f["name"] == "safe"][0]
        self.assertIsNone(safe["trap"])

        initial_score = self.game.score
        # Press KEY_B to lay bomb trap
        self.game.update(0.016, KEY_B, 0)
        self.assertEqual(safe["trap"], "bomb")
        self.assertEqual(self.game.score, initial_score + 100)

    def test_06_rival_black_spy_triggers_trap(self):
        # Safe in room (1,0) has bomb trap
        cur_key = "1_0"
        safe = [f for f in self.game.furniture[cur_key] if f["name"] == "safe"][0]
        safe["trap"] = "bomb"

        self.game.rx = 1
        self.game.ry = 0
        self.game.px = 2.0  # Player away from safe
        self.game.py = 2.0

        # Move Black Spy onto safe
        self.game.rival_rx = 1
        self.game.rival_ry = 0
        self.game.rival_x = 11.0
        self.game.rival_y = 5.0
        self.game.rival_alive = True

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertFalse(self.game.rival_alive)
        self.assertGreaterEqual(self.game.score, initial_score + 1000)

    def test_07_player_triggers_trapped_furniture_loses_life(self):
        cur_key = self.game._get_current_key()
        desk = self.game.furniture[cur_key][0]
        desk["trap"] = "bomb"

        self.game.px = desk["x"]
        self.game.py = desk["y"]

        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_SPY_BLOWN_UP)

    def test_08_melee_combat_with_black_spy(self):
        self.game.px = 7.5
        self.game.py = 7.5
        self.game.rival_rx = self.game.rx
        self.game.rival_ry = self.game.ry
        self.game.rival_x = 7.5
        self.game.rival_y = 7.8
        self.game.rival_alive = True

        initial_score = self.game.score
        # Press KEY_A to strike rival
        self.game.update(0.016, KEY_A, 0)
        self.assertFalse(self.game.rival_alive)
        self.assertGreaterEqual(self.game.score, initial_score + 500)

    def test_09_airport_gate_escape_with_all_items_clears_stage(self):
        self.game.rx = 1
        self.game.ry = 1
        self.game.px = 12.0
        self.game.py = 12.0
        self.game.has_briefcase = True
        self.game.items_found = {"plans", "passport", "money", "key"}

        initial_score = self.game.score
        # Press KEY_A to escape through airport gate
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, initial_score + 3000)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))

        # Check game over after 3 lives lost
        self.game.lives = 0
        self.game.state = STATE_SPY_BLOWN_UP
        self.game.state_timer = 2.0
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Press A to reset
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()

