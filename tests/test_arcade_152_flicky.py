# -*- coding: utf-8 -*-
"""
test_arcade_152_flicky.py —— 街机游戏 #152 救难小鸟 (Flicky 1984 / Sega) 单元测试
验证元数据、扑翼浮空跳跃、多层跳台站立、雏鸟连环跟随长队、杂物投掷击倒恶猫、恶猫切断长龙与全员归巢过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_152_flicky import (
    Game152Flicky,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_FLICKY_DOWN,
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


class TestGame152Flicky(unittest.TestCase):
    def setUp(self):
        self.game = Game152Flicky()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 152)
        self.assertIn("救难小鸟", self.game.name)
        self.assertEqual(self.game.english_name, "Flicky")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(len(self.game.chicks), 6)
        self.assertEqual(len(self.game.cats), 2)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 152)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["rescued_count"], 0)

    def test_02_horizontal_running_and_facing(self):
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 8.0)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.facing, -1)

    def test_03_flap_jumping_and_platform_landing(self):
        self.game.px = 8.0
        self.game.py = 13.0
        self.assertTrue(self.game.is_grounded)

        # Flap jump with KEY_A
        self.game.update(0.016, KEY_A, 0)
        self.assertLess(self.game.pvy, 0.0)
        self.assertFalse(self.game.is_grounded)

        # Gravity pulls down over time and lands on ground y=13
        for _ in range(30):
            self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.py, 13.0)
        self.assertTrue(self.game.is_grounded)

    def test_04_chick_pickup_and_trailing_train(self):
        # Chick #0 is at (3.0, 13.0)
        self.game.px = 3.2
        self.game.py = 13.0
        initial_score = self.game.score

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.chicks[0]["state"], "following")
        self.assertEqual(self.game.chicks[0]["order"], 0)
        self.assertEqual(self.game.score, initial_score + 50)

    def test_05_multiple_chicks_convoy(self):
        # Pick up Chick 0
        self.game.px = 3.0
        self.game.py = 13.0
        self.game.update(0.016, 0, 0)

        # Pick up Chick 1
        self.game.px = 12.0
        self.game.py = 13.0
        self.game.update(0.016, 0, 0)

        following = [c for c in self.game.chicks if c["state"] == "following"]
        self.assertEqual(len(following), 2)

    def test_06_throw_item_with_key_b(self):
        # Throwable is at (6.0, 13.0)
        self.game.px = 6.0
        self.game.py = 13.0
        self.game.facing = 1

        self.game.update(0.016, KEY_B, 0)
        self.assertEqual(len(self.game.flying_items), 1)
        self.assertGreater(self.game.flying_items[0]["vx"], 0)

    def test_07_flying_item_knocks_out_cat(self):
        cat = self.game.cats[0]
        cat["x"] = 10.0
        cat["y"] = 13.0
        cat["alive"] = True

        self.game.flying_items.append({"x": 9.5, "y": 13.0, "vx": 10.0})
        initial_score = self.game.score

        self.game.update(0.02, 0, 0)
        self.assertFalse(cat["alive"])
        self.assertGreaterEqual(self.game.score, initial_score + 300)

    def test_08_cat_cuts_chick_convoy(self):
        # Set chick 0 following
        c0 = self.game.chicks[0]
        c0["state"] = "following"
        c0["order"] = 0
        c0["x"] = 7.0
        c0["y"] = 13.0

        # Move cat into chick 0
        cat = self.game.cats[0]
        cat["x"] = 7.0
        cat["y"] = 13.0
        cat["alive"] = True

        # Keep player safely away
        self.game.px = 12.0
        self.game.py = 13.0

        self.game.update(0.016, 0, 0)
        # Chick convoy should be cut, reverting chick 0 to idle
        self.assertEqual(c0["state"], "idle")

    def test_09_cat_touch_flicky_loses_life(self):
        self.game.px = 6.0
        self.game.py = 13.0
        cat = self.game.cats[0]
        cat["x"] = 6.0
        cat["y"] = 13.0
        cat["alive"] = True

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_FLICKY_DOWN)

    def test_10_nest_door_rescue_and_stage_clear_render(self):
        # Mark all chicks as following
        for i, c in enumerate(self.game.chicks):
            c["state"] = "following"
            c["order"] = i

        # Move player to nest door at (1.5, 13.0)
        self.game.px = 1.5
        self.game.py = 13.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.rescued_count, 6)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2500)

        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()
