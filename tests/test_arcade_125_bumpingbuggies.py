# -*- coding: utf-8 -*-
"""
test_arcade_125_bumpingbuggies.py —— 街机游戏 #125 碰碰车大乱斗 (Bumping Buggies 1981 / Sanritsu & Sega) 单元测试
"""

import unittest
import math
from arcade.game_125_bumpingbuggies import (
    Game125BumpingBuggies,
    STATE_PLAYING,
    STATE_PLAYER_CRASHED,
    STATE_ROUND_CLEAR,
    STATE_GAME_OVER,
    ARENA_MIN,
    ARENA_MAX,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame125BumpingBuggies(unittest.TestCase):
    def setUp(self):
        self.game = Game125BumpingBuggies()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 125)
        self.assertEqual(self.game.name, "碰碰车大乱斗")
        self.assertEqual(self.game.english_name, "Bumping Buggies")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.round, 1)
        self.assertEqual(self.game.get_active_opponents(), 3)

    def test_02_steering_and_throttle(self):
        """测试碰碰车转向操舵与油门推进动力学"""
        init_angle = self.game.player["angle"]
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.player["angle"], init_angle)

        self.game.update(0.05, KEY_UP, 0)
        speed = math.sqrt(self.game.player["vx"] ** 2 + self.game.player["vy"] ** 2)
        self.assertGreater(speed, 0.0)

    def test_03_ramming_surge_button_a(self):
        """测试按键A触发大扭矩蓄力猛撞与冷却机制"""
        self.assertEqual(self.game.ram_cooldown, 0.0)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.player["is_ramming"])
        self.assertGreater(self.game.ram_cooldown, 1.0)

    def test_04_handbrake_drift_button_b(self):
        """测试按键B触发手刹漂移与滑动低阻状态"""
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.drift_timer, 0.0)

    def test_05_elastic_collision_impulse(self):
        """测试碰碰车间橡胶保险杠动量反弹"""
        opp = self.game.opponents[0]
        self.game.player["x"] = 7.0
        self.game.player["y"] = 7.0
        self.game.player["vx"] = 3.0
        self.game.player["vy"] = 0.0

        opp["x"] = 8.0
        opp["y"] = 7.0
        opp["vx"] = -3.0
        opp["vy"] = 0.0

        self.game._handle_buggy_collision(self.game.player, opp)
        # Bounced away
        self.assertLess(self.game.player["vx"], 0.0)
        self.assertGreater(opp["vx"], 0.0)

    def test_06_oil_slick_spinout(self):
        """测试碾过地面油渍触发失控打滑旋转"""
        slick = self.game.slicks[0]
        self.game.player["x"] = slick["x"]
        self.game.player["y"] = slick["y"]

        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.player["spin_timer"], 0.0)

    def test_07_ramming_opponent_into_fence(self):
        """测试将对手撞击至高压电网围栏处决获得500分"""
        opp = self.game.opponents[0]
        opp["x"] = ARENA_MIN - 0.1
        opp["y"] = 7.0
        opp["vx"] = -4.0
        opp["vy"] = 0.0

        old_score = self.game.score
        self.game._check_wall_and_hazards()
        self.assertFalse(opp["active"])
        self.assertEqual(self.game.score, old_score + 500)

    def test_08_player_perimeter_crash(self):
        """测试自机超速猛撞电网围栏发生高压触电战损"""
        self.game.player["x"] = ARENA_MAX + 0.1
        self.game.player["y"] = 7.0
        self.game.player["vx"] = 6.0
        self.game.player["vy"] = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_CRASHED)

    def test_09_round_clear_and_bonus(self):
        """测试淘汰全部对手通关晋级下一轮"""
        for opp in self.game.opponents:
            opp["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.round, 2)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_10_game_over_and_restart(self):
        """测试生命耗尽游戏结束及按键重置"""
        self.game.lives = 1
        self.game.state = STATE_PLAYER_CRASHED
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
