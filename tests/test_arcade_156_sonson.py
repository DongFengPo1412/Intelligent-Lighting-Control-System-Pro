# -*- coding: utf-8 -*-
"""
test_arcade_156_sonson.py —— 街机游戏 #156 西游降魔 (SonSon 1984 / Capcom) 单元测试
验证元数据、六层平台瞬间上下变轨、分层横向射击击灭妖魔、瓜果蔬菜盛宴收集、妖怪碰撞与西行天竺过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_156_sonson import (
    Game156SonSon,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_HIT,
    STATE_GAME_OVER,
    LANES,
    MAX_DISTANCE,
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


class TestGame156SonSon(unittest.TestCase):
    def setUp(self):
        self.game = Game156SonSon()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 156)
        self.assertIn("西游降魔", self.game.name)
        self.assertEqual(self.game.english_name, "SonSon")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lane_idx, 3)
        self.assertEqual(self.game.px, 3.0)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 156)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["lane_idx"], 3)

    def test_02_instant_vertical_lane_switching(self):
        self.assertEqual(self.game.lane_idx, 3)

        # Press KEY_UP to jump up to lane 2
        self.game.update(0.016, KEY_UP, 0)
        self.assertEqual(self.game.lane_idx, 2)

        # Press KEY_DOWN to drop to lane 3
        self.game.update(0.016, KEY_DOWN, 0)
        self.assertEqual(self.game.lane_idx, 3)

    def test_03_horizontal_running_and_scroll(self):
        initial_px = self.game.px
        initial_dist = self.game.distance

        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, initial_px)
        self.assertGreater(self.game.distance, initial_dist)

    def test_04_fire_shot_along_active_lane(self):
        self.game.lane_idx = 2
        self.assertEqual(len(self.game.shots), 0)

        # Press KEY_A to fire
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(len(self.game.shots), 1)
        self.assertEqual(self.game.shots[0]["lane"], 2)

    def test_05_shot_kills_enemy_on_same_lane(self):
        self.game.lane_idx = 3
        enemy = self.game.enemies[0]
        enemy["lane"] = 3
        enemy["x"] = 8.0
        enemy["alive"] = True

        self.game.shots.append({"x": 7.5, "lane": 3, "y": LANES[3], "vx": 14.0})
        initial_score = self.game.score

        self.game.update(0.016, 0, 0)
        self.assertFalse(enemy["alive"])
        self.assertGreaterEqual(self.game.score, initial_score + 150)
        self.assertGreater(len(self.game.fruits), 0)

    def test_06_shot_ignores_enemy_on_different_lane(self):
        enemy = self.game.enemies[0]
        enemy["lane"] = 1  # Enemy on lane 1
        enemy["x"] = 8.0
        enemy["alive"] = True

        # Shot on lane 3
        self.game.shots.append({"x": 8.0, "lane": 3, "y": LANES[3], "vx": 14.0})

        self.game.update(0.016, 0, 0)
        self.assertTrue(enemy["alive"])

    def test_07_collecting_fruit_feast(self):
        self.game.lane_idx = 2
        self.game.px = 6.0
        self.game.fruits.append({"x": 6.0, "lane": 2, "y": LANES[2], "type": "peach"})

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertGreaterEqual(self.game.score, initial_score + 300)

    def test_08_enemy_collision_on_same_lane_damages_player(self):
        self.game.lane_idx = 3
        self.game.px = 5.0
        enemy = self.game.enemies[0]
        enemy["lane"] = 3
        enemy["x"] = 5.0
        enemy["alive"] = True

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)

    def test_09_tianzhu_buddha_sanctuary_clears_stage(self):
        self.game.distance = MAX_DISTANCE + 1.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2500)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))

        # Check game over after 3 lives lost
        self.game.lives = 0
        self.game.state = STATE_PLAYER_HIT
        self.game.state_timer = 2.0
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Press A to reset
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()

