# -*- coding: utf-8 -*-
"""
test_arcade_151_spacedungeon.py —— 街机游戏 #151 空间地牢 (Space Dungeon 1981 / Taito) 单元测试
验证元数据、多舱室门禁穿梭、激光射击无人机、珍宝背包拾取、神偷盗窃与击毙缴获、升降舱撤离结算与过关
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_151_spacedungeon import (
    Game151SpaceDungeon,
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


class TestGame151SpaceDungeon(unittest.TestCase):
    def setUp(self):
        self.game = Game151SpaceDungeon()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 151)
        self.assertIn("空间地牢", self.game.name)
        self.assertEqual(self.game.english_name, "Space Dungeon")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.rx, 1)
        self.assertEqual(self.game.ry, 1)
        self.assertEqual(self.game.treasures_carried, 0)
        self.assertEqual(self.game.treasures_banked, 0)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 151)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["rx"], 1)

    def test_02_room_transition_doorways(self):
        # Move right towards door at x=15, y=7.5
        self.game.px = 14.2
        self.game.py = 7.5
        self.game.rx = 1
        self.game.ry = 1

        self.game.update(0.1, KEY_RIGHT, 0)
        # Should transition into Room (2, 1) and appear at left doorway
        self.assertEqual(self.game.rx, 2)
        self.assertEqual(self.game.ry, 1)
        self.assertLess(self.game.px, 3.0)

    def test_03_laser_shooting_and_drone_kill(self):
        cur_key = self.game._get_current_key()
        drone = self.game.room_enemies[cur_key][0]
        drone["x"] = 7.5
        drone["y"] = 4.0
        drone["alive"] = True

        self.game.px = 7.5
        self.game.py = 7.5
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0

        # Set drone stationary for clean test
        drone["vx"] = 0.0
        drone["vy"] = 0.0

        initial_score = self.game.score
        # Fire laser with KEY_A
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(len(self.game.lasers), 1)

        # Update frame by frame until laser reaches drone
        for _ in range(15):
            self.game.update(0.02, 0, 0)
        self.assertFalse(drone["alive"])
        self.assertGreaterEqual(self.game.score, initial_score + 150)

    def test_04_treasure_pickup_into_backpack(self):
        cur_key = self.game._get_current_key()
        treasure = self.game.room_treasures[cur_key][0]
        treasure["x"] = 7.5
        treasure["y"] = 7.5
        treasure["collected"] = False

        self.game.px = 7.5
        self.game.py = 7.5

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertTrue(treasure["collected"])
        self.assertEqual(self.game.treasures_carried, 1)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_05_roaming_thief_pickpockets_player(self):
        self.game.treasures_carried = 2
        # Place thief in current room overlapping player
        self.game.thief["rx"] = self.game.rx
        self.game.thief["ry"] = self.game.ry
        self.game.thief["x"] = self.game.px
        self.game.thief["y"] = self.game.py
        self.game.thief["stolen_loot"] = 0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.treasures_carried, 1)
        self.assertEqual(self.game.thief["stolen_loot"], 1)

    def test_06_shooting_thief_drops_stolen_treasures(self):
        self.game.thief["rx"] = self.game.rx
        self.game.thief["ry"] = self.game.ry
        self.game.thief["x"] = 7.5
        self.game.thief["y"] = 5.0
        self.game.thief["stolen_loot"] = 1
        self.game.thief["alive"] = True

        self.game.lasers.append({"x": 7.5, "y": 5.2, "vx": 0.0, "vy": -14.0})
        initial_score = self.game.score

        self.game.update(0.016, 0, 0)
        self.assertFalse(self.game.thief["alive"])
        self.assertGreaterEqual(self.game.score, initial_score + 500)
        # Dropped treasure added back to room
        cur_key = self.game._get_current_key()
        self.assertTrue(any(t["x"] == 7.5 for t in self.game.room_treasures[cur_key]))

    def test_07_elevator_room_banks_treasures(self):
        # Go to Collect-o-matic room (2, 2)
        self.game.rx = 2
        self.game.ry = 2
        self.game.px = 7.5
        self.game.py = 7.5
        self.game.treasures_carried = 2
        self.game.treasures_banked = 0

        initial_score = self.game.score
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.treasures_banked, 2)
        self.assertEqual(self.game.treasures_carried, 0)
        self.assertEqual(self.game.score, initial_score + 1000)

    def test_08_death_drops_unbanked_treasures(self):
        self.game.treasures_carried = 2
        cur_key = self.game._get_current_key()
        drone = self.game.room_enemies[cur_key][0]
        drone["x"] = self.game.px
        drone["y"] = self.game.py
        drone["alive"] = True

        initial_treasures_in_room = len(self.game.room_treasures[cur_key])
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)
        self.assertEqual(self.game.treasures_carried, 0)
        self.assertEqual(len(self.game.room_treasures[cur_key]), initial_treasures_in_room + 2)

    def test_09_escape_elevator_stage_clear(self):
        self.game.rx = 2
        self.game.ry = 2
        self.game.px = 7.5
        self.game.py = 7.5
        self.game.treasures_carried = 0
        self.game.treasures_banked = 4

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
