# -*- coding: utf-8 -*-
"""
test_arcade_138_rocnrope.py —— 街机游戏 #138 索道探险家 (Roc'n Rope 1983 / Konami) 单元测试
"""

import os
import sys
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_138_rocnrope import (
    Game138RocnRope,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_FALLEN,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame138RocnRope(unittest.TestCase):
    def setUp(self):
        self.game = Game138RocnRope()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 138)
        self.assertEqual(self.game.name, "索道探险家")
        self.assertEqual(self.game.english_name, "Roc'n Rope")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.px, 2.0)
        self.assertEqual(self.game.py, 14.0)
        self.assertEqual(len(self.game.ledges), 6)
        self.assertEqual(len(self.game.enemies), 3)

    def test_02_ledge_walking_and_facing(self):
        """测试岩台行走与朝向翻转"""
        self.assertEqual(self.game.facing, 1)
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 2.0)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.facing, -1)

    def test_03_flashlight_stuns_enemies(self):
        """测试按键B强光手电眩晕穴居人并获取加分"""
        enemy = self.game.enemies[0]
        self.game.px = 2.0
        self.game.py = 10.0
        self.game.facing = 1

        enemy["x"] = 4.0
        enemy["y"] = 10.0
        enemy["stun_timer"] = 0.0

        old_score = self.game.score
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.flashlight_timer, 0.0)
        self.assertGreater(enemy["stun_timer"], 0.0)
        self.assertEqual(self.game.score, old_score + 50)

    def test_04_harpoon_anchors_cable(self):
        """测试按键A发射鱼叉成功锚定上方岩壁搭建缆绳"""
        # Stand at Tier 0, facing right towards Tier 1 ledge at y=10 (dy=4)
        self.game.px = 2.0
        self.game.py = 14.0
        self.game.facing = 1  # tx = 2 + 1 * 4 = 6.0, which is on ledge 1 (1.0 to 6.0)

        self.assertFalse(self.game.rope_active)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.rope_active)
        self.assertEqual(self.game.rope_start_x, 2.0)
        self.assertEqual(self.game.rope_start_y, 14.0)
        self.assertEqual(self.game.rope_end_x, 6.0)
        self.assertEqual(self.game.rope_end_y, 10.0)

    def test_05_mount_and_climb_rope(self):
        """测试按键UP登绳并沿索道攀登攀爬"""
        self.test_04_harpoon_anchors_cable()

        # Mount rope
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.on_rope)
        self.assertGreater(self.game.rope_t, 0.0)

        # Climb halfway
        for _ in range(5):
            self.game.update(0.05, KEY_UP, 0)
        self.assertGreater(self.game.rope_t, 0.2)
        self.assertLess(self.game.py, 14.0)
        self.assertGreater(self.game.px, 2.0)

    def test_06_dismount_at_top_ledge(self):
        """测试攀爬至索道顶端成功登上新高台"""
        self.test_04_harpoon_anchors_cable()
        self.game.on_rope = True
        self.game.rope_t = 0.95

        old_score = self.game.score
        # Final climb tick
        self.game.update(0.1, KEY_UP, 0)
        self.assertFalse(self.game.on_rope)
        self.assertFalse(self.game.rope_active)
        self.assertEqual(self.game.py, 10.0)
        self.assertEqual(self.game.px, 6.0)
        self.assertEqual(self.game.score, old_score + 100)

    def test_07_fall_off_cliff_when_walking_into_abyss(self):
        """测试悬崖失足跌落深渊坠毁扣除生命"""
        # Position at edge of platform and step off
        self.game.px = 6.0
        self.game.py = 10.0
        self.game.facing = 1

        # Walk off platform (ledge 1 ends at 6.0, gap until 9.0)
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 6.0)

        # Gravity pulls down
        old_lives = self.game.lives
        for _ in range(15):
            self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_FALLEN)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_08_caught_by_unstunned_enemy(self):
        """测试触碰未眩晕敌人丧失生命"""
        self.game.px = 4.0
        self.game.py = 10.0
        enemy = self.game.enemies[0]
        enemy["x"] = 4.0
        enemy["y"] = 10.0
        enemy["stun_timer"] = 0.0

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_FALLEN)
        self.assertEqual(self.game.lives, old_lives - 1)

    def test_09_touch_stunned_enemy_is_safe(self):
        """测试触碰已眩晕敌人安全无伤"""
        self.game.px = 4.0
        self.game.py = 10.0
        enemy = self.game.enemies[0]
        enemy["x"] = 4.0
        enemy["y"] = 10.0
        enemy["stun_timer"] = 2.0  # Stunned!

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, old_lives)

    def test_10_reach_golden_phoenix_clear_stage(self):
        """测试成功攀登至绝壁顶峰朝圣神圣金鸟通关"""
        # Anchor from Tier 2 (y=6, x=7.5) to Peak Tier 3 (y=2, dy=4, tx=7.5)
        self.game.py = 6.0
        self.game.px = 7.5
        self.game.rope_active = True
        self.game.rope_start_x = 7.5
        self.game.rope_start_y = 6.0
        self.game.rope_end_x = 7.5
        self.game.rope_end_y = 2.0
        self.game.on_rope = True
        self.game.rope_t = 0.95

        old_score = self.game.score
        self.game.update(0.1, KEY_UP, 0)
        self.assertEqual(self.game.py, 2.0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 100 + 1000)


if __name__ == "__main__":
    unittest.main()
