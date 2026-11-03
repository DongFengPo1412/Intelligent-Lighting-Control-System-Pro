# -*- coding: utf-8 -*-
"""
test_arcade_129_starcastle.py —— 街机游戏 #129 星际要塞 (Star Castle 1980 / Cinematronics) 单元测试
"""

import unittest
import math
from arcade.game_129_starcastle import (
    Game129StarCastle,
    STATE_PLAYING,
    STATE_CASTLE_EXPLODING,
    STATE_PLAYER_EXPLODING,
    STATE_GAME_OVER,
    CENTER_X,
    CENTER_Y,
    RING_RADII,
    TWO_PI,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame129StarCastle(unittest.TestCase):
    def setUp(self):
        self.game = Game129StarCastle()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 129)
        self.assertEqual(self.game.name, "星际要塞")
        self.assertEqual(self.game.english_name, "Star Castle")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(len(self.game.shield_alive), 3)
        for r in range(3):
            self.assertEqual(len(self.game.shield_alive[r]), 8)
            self.assertTrue(all(self.game.shield_alive[r]))

    def test_02_ship_rotation_and_thrust(self):
        """测试战机旋转操控、推进惯性与逆向减速刹车"""
        init_angle = self.game.p_angle
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertNotEqual(self.game.p_angle, init_angle)

        self.game.update(0.05, KEY_UP, 0)
        speed = math.sqrt(self.game.pvx ** 2 + self.game.pvy ** 2)
        self.assertGreater(speed, 0.0)

        # Retro brake
        old_pvx = self.game.pvx
        self.game.update(0.05, KEY_B, 0)
        self.assertLess(abs(self.game.pvx), abs(old_pvx))

    def test_03_torpedo_fire(self):
        """测试按键A发射等离子鱼雷飞向深空"""
        self.game.p_angle = 0.0 # Facing East away from center
        self.game.update(0.05, KEY_A, 0)
        active_bullets = [b for b in self.game.bullets if b["active"]]
        self.assertEqual(len(active_bullets), 1)

    def test_04_shields_counter_rotation(self):
        """测试三层同心护盾环对向旋转"""
        init_angles = list(self.game.ring_angles)
        self.game.update(0.05, 0, 0)
        self.assertNotEqual(self.game.ring_angles[0], init_angles[0])
        self.assertNotEqual(self.game.ring_angles[1], init_angles[1])

    def test_05_bullet_blasts_shield_segment(self):
        """测试鱼雷击碎外环对应角度护盾扇区加20分"""
        r0 = RING_RADII[0]
        self.game.ring_angles[0] = 0.0
        # Bullet at angle 0.0 (x = 7.5 + r0, y = 7.5)
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = CENTER_X + r0
        self.game.bullets[0]["y"] = CENTER_Y

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(self.game.shield_alive[0][0])
        self.assertFalse(self.game.bullets[0]["active"])
        self.assertEqual(self.game.score, old_score + 20)

    def test_06_bullet_destroys_spark_mine(self):
        """测试拦截追踪电火花地雷获得50分"""
        self.game.sparks[0]["active"] = True
        self.game.sparks[0]["x"] = 5.0
        self.game.sparks[0]["y"] = 5.0

        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = 5.0
        self.game.bullets[0]["y"] = 5.0

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(self.game.sparks[0]["active"])
        self.assertEqual(self.game.score, old_score + 50)

    def test_07_core_penetration_explodes_castle(self):
        """测试直穿三重护盾间隙一击贯通中央核心要塞"""
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = CENTER_X
        self.game.bullets[0]["y"] = CENTER_Y + 0.5

        self.game._check_collisions()
        self.assertEqual(self.game.state, STATE_CASTLE_EXPLODING)

    def test_08_direct_line_of_sight_boss_blast(self):
        """测试护盾空隙对齐触发要塞主炮致命充能直射"""
        # Punch hole in all 3 rings at angle 0 (east)
        self.game.ring_angles = [0.0, 0.0, 0.0]
        self.game.ring_speeds = [0.0, 0.0, 0.0]
        self.game.shield_alive[0][0] = False
        self.game.shield_alive[1][0] = False
        self.game.shield_alive[2][0] = False

        self.assertTrue(self.game.has_direct_line_of_sight(0.0))

        # Position player east of castle
        self.game.px = 14.0
        self.game.py = CENTER_Y
        self.game.turret_fire_timer = 0.01

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.blast["active"])

    def test_09_boss_blast_hits_player(self):
        """测试要塞主炮击中自机引发爆炸"""
        self.game.blast["active"] = True
        self.game.blast["x"] = self.game.px
        self.game.blast["y"] = self.game.py

        self.game._check_collisions()
        self.assertEqual(self.game.state, STATE_PLAYER_EXPLODING)

    def test_10_game_over_and_restart(self):
        """测试自机耗尽游戏结束及按键重开"""
        self.game.lives = 1
        self.game.state = STATE_PLAYER_EXPLODING
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
