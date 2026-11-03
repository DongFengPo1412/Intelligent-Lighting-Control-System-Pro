# -*- coding: utf-8 -*-
"""
test_arcade_154_pang.py —— 街机游戏 #154 魔法泡泡破裂者 (Pang / Buster Bros 1989 / Mitchell) 单元测试
验证元数据、地面横移走位、垂直铁锚抓钩射天、巨球抛物线重力弹跳、抓钩刺线级联二分分裂、弹球碰撞与全灭过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_154_pang import (
    Game154Pang,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_HIT,
    STATE_GAME_OVER,
    FLOOR_Y,
    CEILING_Y,
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


class TestGame154Pang(unittest.TestCase):
    def setUp(self):
        self.game = Game154Pang()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 154)
        self.assertIn("魔法泡泡破裂者", self.game.name)
        self.assertEqual(self.game.english_name, "Pang")
        self.assertEqual(self.game.release_year, 1989)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.px, 7.5)
        self.assertEqual(self.game.py, FLOOR_Y)
        self.assertFalse(self.game.harpoon_active)
        self.assertEqual(len(self.game.balls), 1)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 154)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["balls_count"], 1)

    def test_02_horizontal_walking_and_boundaries(self):
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 7.5)
        self.assertEqual(self.game.facing, 1)

        # Move to edge
        self.game.px = 1.2
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.px, 1.0)

    def test_03_fire_harpoon_wire_ascent(self):
        self.assertFalse(self.game.harpoon_active)

        # Press KEY_A to fire harpoon
        self.game.update(0.016, KEY_A, 0)
        self.assertTrue(self.game.harpoon_active)
        self.assertEqual(self.game.harpoon_x, self.game.px)
        self.assertLess(self.game.harpoon_tip_y, FLOOR_Y)

    def test_04_harpoon_anchors_at_ceiling(self):
        # Fire harpoon and let it reach ceiling
        self.game.harpoon_active = True
        self.game.harpoon_x = 7.5
        self.game.harpoon_tip_y = 2.0
        self.game.harpoon_anchored = False

        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.harpoon_tip_y, CEILING_Y)
        self.assertTrue(self.game.harpoon_anchored)

    def test_05_ball_parabolic_bouncing_physics(self):
        ball = self.game.balls[0]
        ball["x"] = 7.5
        ball["y"] = 6.0
        ball["vy"] = 0.0

        # Gravity pulls ball down
        self.game.update(0.1, 0, 0)
        self.assertGreater(ball["vy"], 0.0)
        self.assertGreater(ball["y"], 6.0)

    def test_06_huge_ball_split_into_two_medium_balls(self):
        # Place size 3 ball over harpoon
        self.game.balls = [{"x": 7.5, "y": 6.0, "vx": 0.0, "vy": 0.0, "size": 3}]
        self.game.harpoon_active = True
        self.game.harpoon_x = 7.5
        self.game.harpoon_tip_y = 2.0

        initial_score = self.game.score
        # Harpoon pops size 3 ball, splitting into two size 2 balls
        self.game.update(0.016, 0, 0)
        self.assertFalse(self.game.harpoon_active)
        self.assertEqual(len(self.game.balls), 2)
        self.assertEqual(self.game.balls[0]["size"], 2)
        self.assertEqual(self.game.balls[1]["size"], 2)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_07_medium_ball_split_into_two_small_balls(self):
        self.game.balls = [{"x": 7.5, "y": 6.0, "vx": 0.0, "vy": 0.0, "size": 2}]
        self.game.harpoon_active = True
        self.game.harpoon_x = 7.5
        self.game.harpoon_tip_y = 2.0

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertEqual(len(self.game.balls), 2)
        self.assertEqual(self.game.balls[0]["size"], 1)
        self.assertEqual(self.game.score, initial_score + 200)

    def test_08_small_ball_popped_and_destroyed(self):
        self.game.balls = [{"x": 7.5, "y": 6.0, "vx": 0.0, "vy": 0.0, "size": 1}]
        self.game.harpoon_active = True
        self.game.harpoon_x = 7.5
        self.game.harpoon_tip_y = 2.0

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        # Small ball pops completely without splitting
        self.assertEqual(len(self.game.balls), 0)
        self.assertEqual(self.game.score, initial_score + 400 + 2000)  # +2000 stage clear

    def test_09_ball_collision_with_player_loses_life(self):
        self.game.balls = [{"x": 7.5, "y": FLOOR_Y - 0.5, "vx": 0.0, "vy": 0.0, "size": 1}]
        self.game.px = 7.5
        self.game.py = FLOOR_Y

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)

    def test_10_clearing_all_balls_triggers_stage_clear_and_render(self):
        self.game.balls.clear()
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2000)

        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()

