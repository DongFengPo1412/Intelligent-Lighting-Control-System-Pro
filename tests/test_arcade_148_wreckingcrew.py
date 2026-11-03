# -*- coding: utf-8 -*-
"""
test_arcade_148_wreckingcrew.py —— 街机游戏 #148 拆迁队 (Wrecking Crew 1985 / Nintendo) 单元测试
验证元数据、无跳跃攀梯水平行走、重锤敲砖破柱、炸药桶整层爆破、巡逻怪伤害与拆迁全清过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_148_wreckingcrew import (
    Game148WreckingCrew,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_HIT,
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


class TestGame148WreckingCrew(unittest.TestCase):
    def setUp(self):
        self.game = Game148WreckingCrew()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 148)
        self.assertIn("拆迁队", self.game.name)
        self.assertEqual(self.game.english_name, "Wrecking Crew")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.px, 2.0)
        self.assertEqual(self.game.py, 14.0)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 148)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["walls_count"], 10)

    def test_02_floor_walking_and_facing(self):
        # Walk right on bottom floor
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 2.0)
        self.assertEqual(self.game.facing, 1)
        self.assertEqual(self.game.py, 14.0)

        # Walk left
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.facing, -1)

    def test_03_ladder_climbing(self):
        # Ladder #0 is at x=4, connecting y=14 to y=10
        self.game.px = 4.0
        self.game.py = 14.0

        # Press KEY_UP to climb
        self.game.update(0.2, KEY_UP, 0)
        self.assertLess(self.game.py, 14.0)
        self.assertGreaterEqual(self.game.py, 10.0)

    def test_04_hammer_strike_brick_wall(self):
        # Wall at x=6, y=14 is a brick wall with hp=1
        self.game.px = 5.2
        self.game.py = 14.0
        self.game.facing = 1

        initial_walls = len(self.game.walls)
        initial_score = self.game.score

        # Press KEY_A to strike hammer
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(len(self.game.walls), initial_walls - 1)
        self.assertEqual(self.game.score, initial_score + 100)
        self.assertGreater(self.game.hammer_timer, 0.0)

    def test_05_hammer_strike_stone_pillar(self):
        # Pillar at x=9, y=14 has hp=2
        self.game.px = 8.2
        self.game.py = 14.0
        self.game.facing = 1

        # First strike reduces hp to 1
        self.game.update(0.016, KEY_A, 0)
        pillar = [w for w in self.game.walls if w["x"] == 9 and w["y"] == 14][0]
        self.assertEqual(pillar["hp"], 1)

        # Second strike destroys pillar
        initial_score = self.game.score
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(len([w for w in self.game.walls if w["x"] == 9 and w["y"] == 14]), 0)
        self.assertEqual(self.game.score, initial_score + 250)

    def test_06_detonate_dynamite_barrel_clears_row(self):
        # Dynamite at x=8, y=14
        self.game.px = 7.2
        self.game.py = 14.0
        self.game.facing = 1

        initial_score = self.game.score
        # Hit dynamite
        self.game.update(0.016, KEY_B, 0)
        self.assertGreaterEqual(self.game.score, initial_score + 500)

        # All walls on floor 14 should be eliminated
        floor_14_walls = [w for w in self.game.walls if w["y"] == 14]
        self.assertEqual(len(floor_14_walls), 0)

    def test_07_dynamite_detonation_eliminates_enemies_on_same_floor(self):
        # Enemy 0 is on floor 14
        self.assertTrue(self.game.enemies[0]["alive"])
        self.game.px = 7.2
        self.game.py = 14.0
        self.game.facing = 1

        self.game.update(0.016, KEY_A, 0)
        self.assertFalse(self.game.enemies[0]["alive"])

    def test_08_enemy_touch_player_damages_player(self):
        self.game.px = 6.0
        self.game.py = 14.0
        e = self.game.enemies[0]
        e["x"] = 6.0
        e["y"] = 14.0
        e["alive"] = True

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)

    def test_09_demolishing_all_walls_clears_stage(self):
        self.game.walls.clear()
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2000)

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
