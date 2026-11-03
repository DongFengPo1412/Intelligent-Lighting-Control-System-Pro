# -*- coding: utf-8 -*-
"""
test_arcade_139_amidar.py —— 街机游戏 #139 阿米达格网 (Amidar 1981 / Konami & Stern) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_139_amidar import (
    Game139Amidar,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_CAUGHT,
    STATE_GAME_OVER,
    GRID_COLS,
    GRID_ROWS,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame139Amidar(unittest.TestCase):
    def setUp(self):
        self.game = Game139Amidar()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 139)
        self.assertEqual(self.game.name, "阿米达格网")
        self.assertEqual(self.game.english_name, "Amidar")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.jumps_left, 3)
        self.assertEqual(self.game.px, 2.0)
        self.assertEqual(self.game.py, 2.0)
        self.assertEqual(len(self.game.enemies), 3)

    def test_02_grid_line_walking_and_tracing(self):
        """测试沿横向网格线行走并实时描亮路径"""
        self.assertEqual(self.game.px, 2.0)
        self.assertEqual(self.game.py, 2.0)
        self.assertTrue(self.game.traced[2][2])

        # Walk right along row 2
        old_score = self.game.score
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 2.0)
        self.assertEqual(self.game.py, 2.0)
        self.assertTrue(self.game.traced[2][int(round(self.game.px))])
        self.assertGreater(self.game.score, old_score)

    def test_03_grid_turning_at_intersection(self):
        """测试在十字路口转弯沿纵向网格线向下行走"""
        # Place player at intersection (6, 2)
        self.game.px = 6.0
        self.game.py = 2.0

        # Press down
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertEqual(self.game.px, 6.0)
        self.assertGreater(self.game.py, 2.0)

    def test_04_dash_with_key_a(self):
        """测试按键A疾跑加速描边"""
        self.game.px = 2.0
        self.game.py = 2.0
        self.game.update(0.1, KEY_RIGHT, 0)
        dist_normal = self.game.px - 2.0

        # Reset and test with KEY_A
        self.game.px = 2.0
        self.game.update(0.1, KEY_RIGHT | KEY_A, 0)
        dist_dash = self.game.px - 2.0
        self.assertGreater(dist_dash, dist_normal)

    def test_05_jump_button_freezes_enemies(self):
        """测试按键B腾空跳跃消耗跳跃次数并定身敌人"""
        self.assertEqual(self.game.jumps_left, 3)
        self.assertFalse(self.game.jump_timer > 0.0)

        enemy = self.game.enemies[0]
        ex_before = enemy["x"]
        ey_before = enemy["y"]

        # Press Jump (Key B)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.jumps_left, 2)
        self.assertGreater(self.game.jump_timer, 0.0)

        # Enemies should be frozen while jumping
        self.game.update(0.05, 0, 0)
        self.assertEqual(enemy["x"], ex_before)
        self.assertEqual(enemy["y"], ey_before)

    def test_06_jump_avoids_enemy_collision(self):
        """测试在敌人重叠处起跳免受伤害"""
        self.game.px = 6.0
        self.game.py = 6.0
        enemy = self.game.enemies[0]
        enemy["x"] = 6.0
        enemy["y"] = 6.0

        self.game.jump_timer = 0.5  # In jump
        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, old_lives)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_07_caught_by_patrol_enemy(self):
        """测试在未起跳状态下被巡逻怪追上失命"""
        self.game.px = 6.0
        self.game.py = 6.0
        self.game.jump_timer = 0.0
        enemy = self.game.enemies[0]
        enemy["x"] = 6.0
        enemy["y"] = 6.0

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, old_lives - 1)
        self.assertEqual(self.game.state, STATE_CAUGHT)

    def test_08_box_closure_fills_area_and_scores(self):
        """测试四周描边闭合一个矩形方格触发涂色加分"""
        # Trace top box (0, 0): perimeter x in [2..6], y in [2..6]
        for x in range(2, 7):
            self.game.traced[2][x] = True
            self.game.traced[6][x] = True
        for y in range(2, 7):
            self.game.traced[y][2] = True
            self.game.traced[y][6] = True

        self.assertFalse(self.game.boxes[0][0])
        old_score = self.game.score
        self.game._check_boxes()
        self.assertTrue(self.game.boxes[0][0])
        self.assertEqual(self.game.score, old_score + 200)

    def test_09_all_boxes_filled_clears_stage(self):
        """测试九宫格全域闭合涂满通关升级"""
        # Fill all 9 boxes
        for by in range(3):
            for bx in range(3):
                self.game.boxes[by][bx] = True
        # Leave last box to be checked
        self.game.boxes[2][2] = False
        for x in range(10, 15):
            self.game.traced[10][x] = True
            self.game.traced[14][x] = True
        for y in range(10, 15):
            self.game.traced[y][10] = True
            self.game.traced[y][14] = True

        old_score = self.game.score
        self.game._check_boxes()
        self.assertTrue(self.game.boxes[2][2])
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 200 + 1000)

    def test_10_status_dict_reporting(self):
        """测试卡带状态数据字典输出完整性"""
        status = self.game.get_status()
        self.assertEqual(status["game_id"], 139)
        self.assertEqual(status["name"], "阿米达格网")
        self.assertEqual(status["english_name"], "Amidar")
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["jumps_left"], 3)
        self.assertFalse(status["is_jumping"])
        self.assertEqual(status["boxes_cleared"], 0)


if __name__ == "__main__":
    unittest.main()
