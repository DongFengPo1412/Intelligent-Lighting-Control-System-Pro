# -*- coding: utf-8 -*-
"""
test_arcade_146_butasan.py —— 街机游戏 #146 碰碰小猪 (Butasan 1987 / Jaleco) 单元测试
验证元数据、引信炸弹搬运举起、定向抛投、滑铲踢雷、连环殉爆、敌猪歼灭与过关逻辑
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_146_butasan import (
    Game146Butasan,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PIG_BLASTED,
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


class TestGame146Butasan(unittest.TestCase):
    def setUp(self):
        self.game = Game146Butasan()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 146)
        self.assertIn("碰碰小猪", self.game.name)
        self.assertEqual(self.game.english_name, "Butasan")
        self.assertEqual(self.game.release_year, 1987)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertIsNone(self.game.held_bomb)
        self.assertGreaterEqual(len(self.game.bombs), 3)
        self.assertGreaterEqual(len(self.game.enemies), 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 146)
        self.assertEqual(status["lives"], 3)
        self.assertFalse(status["held_bomb"])

    def test_02_player_movement_and_bounds(self):
        self.game.px = 7.5
        self.game.py = 7.5

        # Move right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 7.5)
        self.assertEqual(self.game.facing_x, 1.0)
        self.assertEqual(self.game.facing_y, 0.0)

        # Move up
        self.game.update(0.1, KEY_UP, 0)
        self.assertEqual(self.game.facing_x, 0.0)
        self.assertEqual(self.game.facing_y, -1.0)

        # Test bound clamping at arena edges
        self.game.px = 1.0
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.px, 1.5)

    def test_03_pick_up_bomb_with_key_a(self):
        self.game.px = 4.0
        self.game.py = 8.0
        # Bomb #0 is at (4.0, 8.0)
        self.assertIsNone(self.game.held_bomb)

        # Press Key A to pick up
        self.game.update(0.016, KEY_A, 0)
        self.assertIsNotNone(self.game.held_bomb)
        self.assertEqual(self.game.held_bomb["state"], "held")
        self.assertEqual(self.game.held_bomb["x"], 4.0)

    def test_04_throw_held_bomb_with_key_a(self):
        self.game.px = 4.0
        self.game.py = 8.0
        # Pick up
        self.game.update(0.016, KEY_A, 0)
        self.assertIsNotNone(self.game.held_bomb)

        # Face right and throw with Key A
        self.game.facing_x = 1.0
        self.game.facing_y = 0.0
        self.game.update(0.016, KEY_A, 0)

        self.assertIsNone(self.game.held_bomb)
        # Check flying bomb in arena
        flying_bombs = [b for b in self.game.bombs if b["state"] == "flying"]
        self.assertGreaterEqual(len(flying_bombs), 1)
        self.assertGreater(flying_bombs[0]["vx"], 0)

    def test_05_kick_ground_bomb_with_key_b(self):
        self.game.px = 3.5
        self.game.py = 8.0
        self.game.facing_x = 1.0
        self.game.facing_y = 0.0

        # Kick nearest bomb (at 4.0, 8.0) with Key B
        self.game.update(0.016, KEY_B, 0)
        sliding_bombs = [b for b in self.game.bombs if b["state"] == "sliding"]
        self.assertGreaterEqual(len(sliding_bombs), 1)
        self.assertEqual(sliding_bombs[0]["vx"], 14.0)

    def test_06_bomb_fuse_countdown_and_explosion(self):
        # Find a bomb and set fuse low
        b = self.game.bombs[0]
        b["x"] = 7.0
        b["y"] = 7.0
        b["fuse"] = 0.1

        # Update enough to expire fuse
        self.game.update(0.15, 0, 0)
        self.assertGreaterEqual(len(self.game.explosions), 5)  # Cross explosion pattern

    def test_07_bomb_chain_reaction(self):
        self.game.bombs.clear()
        self.game.bombs.append({"x": 5.0, "y": 5.0, "fuse": 0.02, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True})
        self.game.bombs.append({"x": 5.5, "y": 5.0, "fuse": 10.0, "state": "ground", "vx": 0.0, "vy": 0.0, "active": True})

        # Bomb 0 explodes with dt=0.025, triggering chain reaction that shortens Bomb 1's fuse to 0.05
        self.game.update(0.025, 0, 0)
        self.assertGreater(len(self.game.explosions), 0)
        chain_bombs = [b for b in self.game.bombs if b["x"] == 5.5 and b["fuse"] <= 0.05]
        self.assertEqual(len(chain_bombs), 1)

    def test_08_flying_bomb_direct_hit_kills_enemy(self):
        initial_score = self.game.score
        target_enemy = self.game.enemies[0]
        target_enemy["x"] = 8.0
        target_enemy["y"] = 8.0
        target_enemy["alive"] = True

        # Spawn flying bomb directly onto target enemy
        self.game.bombs.append({
            "x": 8.0, "y": 8.0, "fuse": 5.0, "state": "flying", "vx": 5.0, "vy": 0.0, "active": True
        })

        self.game.update(0.016, 0, 0)
        self.assertGreaterEqual(self.game.score, initial_score + 250)
        self.assertGreater(len(self.game.explosions), 0)

    def test_09_explosion_blast_kills_enemy_and_damages_player(self):
        initial_lives = self.game.lives

        # 1. Explosion kills enemy
        target_enemy = self.game.enemies[0]
        target_enemy["x"] = 3.0
        target_enemy["y"] = 3.0
        self.game.explosions.append({"x": 3, "y": 3, "timer": 0.4})
        self.game.update(0.016, 0, 0)
        self.assertFalse(target_enemy["alive"])

        # 2. Explosion damages player
        self.game.px = 8.0
        self.game.py = 8.0
        self.game.explosions.append({"x": 8, "y": 8, "timer": 0.4})
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_PIG_BLASTED)

    def test_10_stage_clear_when_all_enemies_eliminated_and_render(self):
        for e in self.game.enemies:
            e["alive"] = False

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

        # Verify rendering
        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()
