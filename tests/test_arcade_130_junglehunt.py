# -*- coding: utf-8 -*-
"""
test_arcade_130_junglehunt.py —— 街机游戏 #130 丛林探险 (Jungle Hunt 1982 / Taito) 单元测试
"""

import unittest
import math
from arcade.game_130_junglehunt import (
    Game130JungleHunt,
    STAGE_VINES,
    STAGE_RIVER,
    STAGE_BOULDERS,
    STAGE_RESCUE,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_PLAYER_DYING,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame130JungleHunt(unittest.TestCase):
    def setUp(self):
        self.game = Game130JungleHunt()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 130)
        self.assertEqual(self.game.name, "丛林探险")
        self.assertEqual(self.game.english_name, "Jungle Hunt")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.stage, STAGE_VINES)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.progress, 0.0)

    def test_02_vine_swing_and_leap(self):
        """测试阶段一树冠摆藤脱手飞跃"""
        self.assertFalse(self.game.in_air)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.in_air)
        self.assertNotEqual(self.game.pvx, 0.0)

    def test_03_catch_next_vine(self):
        """测试飞跃成功抓住相邻第二根藤条增加探险进度"""
        self.game.in_air = True
        next_v = 1
        # Predict next vine tip at dt=0.05
        sway_spd = 3.5 + self.game.expedition_round * 0.2
        next_ang = math.sin(0.05 * sway_spd + 1.6) * 0.7
        v_tip_x = self.game.vine_x[next_v] + math.sin(next_ang) * 7.0
        v_tip_y = 2.0 + math.cos(next_ang) * 7.0

        self.game.pvx = 0.0
        self.game.pvy = 0.5
        self.game.px = v_tip_x
        self.game.py = v_tip_y - (0.5 * 0.05) # Compensate for 1 frame movement

        old_prog = self.game.progress
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.in_air)
        self.assertEqual(self.game.current_vine, next_v)
        self.assertGreater(self.game.progress, old_prog)

    def test_04_river_swimming_and_oxygen(self):
        """测试阶段二鳄鱼河潜水氧气消耗与浮上海面换气"""
        self.game._init_stage(STAGE_RIVER)
        self.assertEqual(self.game.oxygen, 30.0)
        self.game.py = 6.0 # Underwater

        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.oxygen, 30.0)

        # Surface to breathe
        self.game.py = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.oxygen, 30.0)

    def test_05_river_knife_stab_croc(self):
        """测试匕首刺杀闭嘴鳄鱼获得200分"""
        self.game._init_stage(STAGE_RIVER)
        self.game.px = 5.0
        self.game.py = 5.0
        self.game.is_stabbing = True
        self.game.stab_timer = 0.3

        self.game.croc_x[0] = 5.5
        self.game.croc_y[0] = 5.0
        self.game.croc_mouth_open[0] = False

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.score, old_score + 200)

    def test_06_river_croc_bite_player(self):
        """测试张嘴鳄鱼咬伤探险家引发战损"""
        self.game._init_stage(STAGE_RIVER)
        self.game.px = 5.0
        self.game.py = 5.0
        self.game.is_stabbing = False

        self.game.croc_x[0] = 5.2
        self.game.croc_y[0] = 5.0
        self.game.croc_mouth_open[0] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DYING)

    def test_07_boulder_jump_over_low_rock(self):
        """测试阶段三面对低空滚石起跳规避"""
        self.game._init_stage(STAGE_BOULDERS)
        self.assertFalse(self.game.is_jumping)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.pvy, 0.0)

    def test_08_boulder_duck_under_high_rock(self):
        """测试面对高空弹跳滚石下蹲俯身规避"""
        self.game._init_stage(STAGE_BOULDERS)
        self.game.px = 5.0
        self.game.py = 13.0
        self.game.boulder_x[0] = 5.0
        self.game.boulder_is_high[0] = True

        # Hold DOWN to duck
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertTrue(self.game.is_ducking)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_09_rescue_maiden_completes_cycle(self):
        """测试阶段四跃过土著矛兵飞扑营救受困少女"""
        self.game._init_stage(STAGE_RESCUE)
        self.game.px = 12.0
        self.game.py = 8.0
        self.game.is_jumping = True

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.maiden_rescued)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)

    def test_10_game_over_and_restart(self):
        """测试生命耗尽游戏结束及按键重置探险"""
        self.game.lives = 1
        self.game.state = STATE_PLAYER_DYING
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
