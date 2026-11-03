# -*- coding: utf-8 -*-
"""
test_arcade_140_sinistar.py —— 街机游戏 #140 巨脸毁灭者 (Sinistar 1983 / Williams Electronics) 单元测试
"""

import os
import sys
import unittest
import math

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_140_sinistar import (
    Game140Sinistar,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_DEVOURED,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame140Sinistar(unittest.TestCase):
    def setUp(self):
        self.game = Game140Sinistar()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 140)
        self.assertEqual(self.game.name, "巨脸毁灭者")
        self.assertEqual(self.game.english_name, "Sinistar")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.sinibombs, 3)
        self.assertFalse(self.game.sinistar_alive)
        self.assertEqual(len(self.game.asteroids), 4)
        self.assertEqual(len(self.game.workers), 2)

    def test_02_rotation_and_inertia_thrust(self):
        """测试按键旋转航向与惯性推进漂移"""
        old_angle = self.game.angle
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.angle, old_angle)

        # Apply thrust
        self.game.update(0.1, KEY_UP, 0)
        self.assertTrue(abs(self.game.vx) > 0.0 or abs(self.game.vy) > 0.0)

    def test_03_fire_standard_laser(self):
        """测试按键A发射前向采矿激光炮"""
        self.assertEqual(len(self.game.bullets), 0)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)

    def test_04_mining_asteroid_ejects_crystal(self):
        """测试激光轰击小行星采矿萃取并弹出能量晶石"""
        asteroid = self.game.asteroids[0]
        asteroid["x"] = 5.0
        asteroid["y"] = 5.0
        asteroid["hp"] = 3

        # Spawn bullet hitting asteroid
        self.game.bullets = [{
            "x": 5.0, "y": 5.2, "vx": 0.0, "vy": -16.0, "active": True
        }]

        old_score = self.game.score
        self.assertEqual(len(self.game.crystals), 0)
        self.game.update(0.05, 0, 0)

        self.assertEqual(asteroid["hp"], 2)
        self.assertEqual(self.game.score, old_score + 20)
        self.assertEqual(len(self.game.crystals), 1)

    def test_05_collect_crystal_converts_to_sinibomb(self):
        """测试飞船吸收漂浮晶石合成西尼核弹"""
        self.game.crystals = [{"x": 7.5, "y": 7.5, "active": True}]
        self.game.px = 7.5
        self.game.py = 7.5
        self.game.sinibombs = 2

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.sinibombs, 3)
        self.assertEqual(self.game.score, old_score + 100)
        self.assertEqual(len(self.game.crystals), 0)

    def test_06_kill_worker_drone(self):
        """测试击毁拦截偷运晶石的工蜂战机"""
        worker = self.game.workers[0]
        worker["x"] = 6.0
        worker["y"] = 6.0
        worker["alive"] = True

        self.game.bullets = [{
            "x": 6.0, "y": 6.0, "vx": 0.0, "vy": -16.0, "active": True
        }]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(worker["alive"])
        self.assertEqual(self.game.score, old_score + 150)

    def test_07_sinistar_awakens_upon_construction(self):
        """测试工蜂运载晶石完成魔头组装触发西尼星君苏醒"""
        self.assertFalse(self.game.sinistar_alive)
        self.game.sinistar_pieces = 5

        worker = self.game.workers[0]
        worker["alive"] = True
        worker["has_crystal"] = True
        worker["x"] = self.game.sinistar_x
        worker["y"] = self.game.sinistar_y

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.sinistar_pieces, 6)
        self.assertTrue(self.game.sinistar_alive)

    def test_08_sinistar_pursuit_devours_ship(self):
        """测试西尼星君狂暴追击吞噬飞船"""
        self.game.sinistar_alive = True
        self.game.sinistar_x = 7.5
        self.game.sinistar_y = 7.5
        self.game.px = 7.5
        self.game.py = 7.5

        old_lives = self.game.lives
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, old_lives - 1)
        self.assertEqual(self.game.state, STATE_SHIP_DEVOURED)

    def test_09_fire_target_seeking_sinibomb(self):
        """测试按键B发射西尼追踪炸弹自动锁定巨脸追踪攻击"""
        self.game.sinibombs = 2
        self.game.sinistar_alive = True
        self.game.sinistar_x = 12.0
        self.game.sinistar_y = 2.0
        self.game.px = 7.5
        self.game.py = 7.5

        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.sinibombs, 1)
        self.assertEqual(len(self.game.active_bombs), 1)

        # Bomb tracks towards Sinistar
        bomb = self.game.active_bombs[0]
        self.game.update(0.05, 0, 0)
        self.assertGreater(bomb["vx"], 0.0)
        self.assertLess(bomb["vy"], 0.0)

    def test_10_sinibombs_destroy_sinistar_and_clear_stage(self):
        """测试西尼炸弹命中耗尽魔头血量引爆通关"""
        self.game.px = 2.0
        self.game.py = 2.0
        self.game.sinistar_alive = True
        self.game.sinistar_x = 8.0
        self.game.sinistar_y = 8.0
        self.game.sinistar_hp = 1

        self.game.active_bombs = [{
            "x": 8.0, "y": 8.0, "vx": 0.0, "vy": 0.0, "active": True
        }]

        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.sinistar_hp, 0)
        self.assertFalse(self.game.sinistar_alive)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, old_score + 400 + 2000)


if __name__ == "__main__":
    unittest.main()
