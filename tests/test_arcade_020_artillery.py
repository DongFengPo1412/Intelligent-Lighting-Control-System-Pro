# -*- coding: utf-8 -*-
"""
test_arcade_020_artillery.py —— 像素百战天虫 1980 完整单元测试
验证抛物线弹道物理、侧风漂移、蓄力充能、可破坏弹坑地形、回合轮换与胜负结算
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_020_artillery import Game020Artillery
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_START,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame020Artillery(unittest.TestCase):
    def setUp(self):
        self.game = Game020Artillery()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心挂载"""
        self.assertEqual(self.game.game_id, 20)
        self.assertEqual(self.game.name, "像素百战天虫")
        self.assertEqual(self.game.english_name, "Artillery 1980")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("抛物线", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(20)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "像素百战天虫")

    def test_terrain_generation_and_tank_placement(self):
        """测试起伏山脉生成与双方坦克就位"""
        self.assertEqual(len(self.game.terrain), 16)
        for h in self.game.terrain:
            self.assertTrue(8 <= h <= 14)

        self.assertEqual(self.game.player["x"], 2)
        self.assertEqual(self.game.player["y"], self.game.terrain[2] - 1)
        self.assertEqual(self.game.player["hp"], 3)

        self.assertEqual(self.game.enemy["x"], 13)
        self.assertEqual(self.game.enemy["y"], self.game.terrain[13] - 1)
        self.assertEqual(self.game.enemy["hp"], 3)
        self.assertTrue(-2.5 <= self.game.wind <= 2.5)

    def test_angle_adjustment_and_clamping(self):
        """测试仰角在 [15°, 75°] 区间平滑调整"""
        self.assertEqual(self.game.player["angle_deg"], 45.0)

        # 调低仰角
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.player["angle_deg"], 45.0)

        # 压到最低限位 15°
        for _ in range(30):
            self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player["angle_deg"], 15.0)

        # 抬到最高限位 75°
        for _ in range(60):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player["angle_deg"], 75.0)

    def test_power_charging_and_firing(self):
        """测试按住 A 蓄力，松开 A 激发炮弹发射"""
        init_power = self.game.player["power"]

        # 按住 A 充能
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertTrue(self.game.charging_power)
        self.assertGreater(self.game.player["power"], init_power)

        # 松开 A 发射
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.charging_power)
        self.assertTrue(self.game.shell["active"])
        self.assertTrue(self.game.shell["is_player"])
        self.assertGreater(self.game.shell["vx"], 0.0) # 向右飞行
        self.assertLess(self.game.shell["vy"], 0.0)    # 向上腾空

    def test_ballistic_flight_and_wind_drift(self):
        """测试炮弹在重力和侧风作用下的抛物线加速度"""
        self.game.wind = 1.0 # 顺风
        self.game.fire_shell(True)
        init_vx = self.game.shell["vx"]
        init_vy = self.game.shell["vy"]

        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.shell["vx"], init_vx) # 顺风加速
        self.assertGreater(self.game.shell["vy"], init_vy) # 重力向下加速

    def test_crater_deformation_on_terrain_impact(self):
        """测试炮弹撞击地面产生弹坑地形凹陷"""
        gx = 6
        initial_h = self.game.terrain[gx]
        self.game.explode(float(gx), float(initial_h), True)

        # 弹坑处及两侧深度加深 (数值增大代表往屏幕下方凹陷)
        self.assertEqual(self.game.terrain[gx], min(15, initial_h + 1))

    def test_player_hits_enemy_damage_and_victory(self):
        """测试精准打击削减敌方生命并触发胜利判定"""
        self.assertEqual(self.game.enemy["hp"], 3)
        self.assertEqual(self.game.score, 0)

        # 第一次直接命中敌方坦克坐标
        self.game.explode(float(self.game.enemy["x"]), float(self.game.enemy["y"]), True)
        self.assertEqual(self.game.enemy["hp"], 2)
        self.assertEqual(self.game.score, 150)

        # 第二次命中
        self.game.explode(float(self.game.enemy["x"]), float(self.game.enemy["y"]), True)
        self.assertEqual(self.game.enemy["hp"], 1)

        # 第三次致命击毁
        self.game.explode(float(self.game.enemy["x"]), float(self.game.enemy["y"]), True)
        self.assertEqual(self.game.enemy["hp"], 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_enemy_ai_turn_and_retaliation(self):
        """测试回合轮转与敌方 AI 自动瞄准反击"""
        # 玩家炮弹飞出界，轮转到 AI
        self.game.shell["active"] = True
        self.game.shell["x"] = 20.0 # 飞出右边界
        self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.turn_player) # 切换至 AI 回合
        self.assertEqual(self.game.turn_timer, 0.0)

        # 经过 0.8s 延迟后 AI 发射
        for _ in range(18):
            self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.shell["active"])
        self.assertFalse(self.game.shell["is_player"])
        self.assertLess(self.game.shell["vx"], 0.0) # 向左朝向玩家飞来

    def test_enemy_hits_player_gameover(self):
        """测试敌方炮火击毁玩家坦克并判定游戏失败"""
        self.assertEqual(self.game.player["hp"], 3)

        self.game.explode(float(self.game.player["x"]), float(self.game.player["y"]), False)
        self.assertEqual(self.game.player["hp"], 2)

        self.game.explode(float(self.game.player["x"]), float(self.game.player["y"]), False)
        self.assertEqual(self.game.player["hp"], 1)

        self.game.explode(float(self.game.player["x"]), float(self.game.player["y"]), False)
        self.assertEqual(self.game.player["hp"], 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_rendering_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 验证玩家坦克青蓝光辉 [0, 255, 255]
        px = self.game.player["x"]
        py = self.game.player["y"]
        p_idx = (py * 16 + px) * 3
        self.assertEqual(fb[p_idx + 0], 0)
        self.assertEqual(fb[p_idx + 1], 255)
        self.assertEqual(fb[p_idx + 2], 255)

        # 验证敌方坦克猩红战车 [231, 76, 60]
        ex = self.game.enemy["x"]
        ey = self.game.enemy["y"]
        e_idx = (ey * 16 + ex) * 3
        self.assertEqual(fb[e_idx + 0], 231)
        self.assertEqual(fb[e_idx + 1], 76)
        self.assertEqual(fb[e_idx + 2], 60)

    def test_status_reporting(self):
        """测试状态监控结构体与关卡进度比率"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)


if __name__ == "__main__":
    unittest.main()
