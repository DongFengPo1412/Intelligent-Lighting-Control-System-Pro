# -*- coding: utf-8 -*-
"""
test_arcade_126_gyruss.py —— 街机游戏 #126 旋风巡航者 (Gyruss 1983 / Konami) 单元测试
"""

import unittest
import math
from arcade.game_126_gyruss import (
    Game126Gyruss,
    STATE_FLYING,
    STATE_WARPING,
    STATE_PLAYER_EXPLODING,
    STATE_GAME_OVER,
    ORBIT_RADIUS,
    PI,
)
from arcade.base_cartridge import KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame126Gyruss(unittest.TestCase):
    def setUp(self):
        self.game = Game126Gyruss()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 126)
        self.assertEqual(self.game.name, "旋风巡航者")
        self.assertEqual(self.game.english_name, "Gyruss")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.warp_stage, 0)
        self.assertEqual(self.game.remaining_dist, 20)

    def test_02_perimeter_orbital_rotation(self):
        """测试战机在外环360度圆周轨道上回旋顺时针/逆时针机动"""
        init_angle = self.game.player_angle
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertNotEqual(self.game.player_angle, init_angle)

        self.game.update(0.05, KEY_RIGHT, KEY_LEFT)
        self.assertGreater(self.game.player_angle, 0.0)

    def test_03_inward_bullet_firing(self):
        """测试按键A向心发射等离子火炮直扑星系质心"""
        self.game.update(0.05, KEY_A, 0)
        bullet = [b for b in self.game.bullets if b["active"]][0]
        # Spawns at ORBIT_RADIUS - 0.4 and moves inward by 16.0 * 0.05 = 0.8 during the frame
        self.assertAlmostEqual(bullet["radius"], ORBIT_RADIUS - 0.4 - 0.8, delta=0.1)
        initial_r = bullet["radius"]

        self.game.update(0.05, 0, 0)
        self.assertLess(bullet["radius"], initial_r)

    def test_04_barrel_roll_invulnerability(self):
        """测试按键B触发桶滚螺旋机动与冷却状态"""
        self.assertEqual(self.game.roll_timer, 0.0)
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.roll_timer, 0.0)
        self.assertGreater(self.game.roll_cooldown, 1.0)

    def test_05_bullet_hits_alien_fighter(self):
        """测试向心炮弹命中向外扩散的外星战机获得100分"""
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["radius"] = 3.0
        self.game.bullets[0]["angle"] = 1.0

        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["is_asteroid"] = False
        enemy["radius"] = 3.0
        enemy["angle"] = 1.0

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(enemy["active"])
        self.assertFalse(self.game.bullets[0]["active"])
        self.assertEqual(self.game.score, old_score + 100)

    def test_06_bullet_hits_asteroid(self):
        """测试向心炮弹击碎深空小行星获得200分"""
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["radius"] = 4.0
        self.game.bullets[0]["angle"] = 2.0

        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["is_asteroid"] = True
        enemy["radius"] = 4.0
        enemy["angle"] = 2.0

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(enemy["active"])
        self.assertEqual(self.game.score, old_score + 200)

    def test_07_alien_collision_destroys_player(self):
        """测试外环遭遇扩散敌机导致自机爆炸"""
        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["radius"] = ORBIT_RADIUS
        enemy["angle"] = self.game.player_angle

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_EXPLODING)

    def test_08_roll_avoids_alien_collision(self):
        """测试桶滚螺旋机动状态下免疫敌机撞击伤害"""
        self.game.roll_timer = 0.3
        enemy = self.game.enemies[0]
        enemy["active"] = True
        enemy["radius"] = ORBIT_RADIUS
        enemy["angle"] = self.game.player_angle

        self.game._check_collisions()
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_09_warp_arrival_transition(self):
        """测试行星跃迁距离归零触发跃迁冲刺进入下一阶段"""
        self.game.remaining_dist = 0
        for e in self.game.enemies:
            e["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_WARPING)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.warp_stage, 1)
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_10_game_over_and_restart(self):
        """测试生命耗尽游戏结束及按键重新投币复活"""
        self.game.lives = 1
        self.game.state = STATE_PLAYER_EXPLODING
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
