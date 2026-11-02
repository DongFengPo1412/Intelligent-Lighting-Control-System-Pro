# -*- coding: utf-8 -*-
"""
test_arcade_030_submarine.py —— 潜艇鱼雷大战 1979 完整单元测试
验证深海潜艇左右潜航、垂直浮力鱼雷发射、前置量命中水面舰艇、游弋水雷拦截与击沉8艘通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_030_submarine import (
    Game030Submarine,
    SHIP_PT_BOAT,
    SHIP_DESTROYER,
    SHIP_CARRIER,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    STATE_PLAYING,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame030Submarine(unittest.TestCase):
    def setUp(self):
        self.game = Game030Submarine()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心集成"""
        self.assertEqual(self.game.game_id, 30)
        self.assertEqual(self.game.name, "深海鱼雷战")
        self.assertEqual(self.game.english_name, "Submarine 1979")
        self.assertEqual(self.game.release_year, 1979)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("浮力垂直鱼雷", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(30)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "深海鱼雷战")

    def test_ocean_initialization(self):
        """测试大洋深度分层与潜艇初始战位"""
        self.assertEqual(self.game.player_x, 7.0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.ships_sunk, 0)
        self.assertGreaterEqual(len(self.game.ships), 1)

    def test_submarine_horizontal_steering(self):
        """测试潜艇左右潜航与边界限位"""
        init_x = self.game.player_x

        # 左行
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.player_x, init_x)

        # 压到左限位 0.5
        for _ in range(30):
            self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player_x, 0.5)

        # 压到右限位 14.0
        for _ in range(50):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_x, 14.0)

    def test_torpedo_firing_and_upward_velocity(self):
        """测试发射直航鱼雷与垂直高速上浮"""
        self.game.torpedoes.clear()
        self.game.reload_timer = 0.0

        self.game.update(0.05, 0, KEY_A)
        self.assertEqual(len(self.game.torpedoes), 1)
        torp = self.game.torpedoes[0]
        self.assertLess(torp["vy"], 0.0) # 向上高速冲刺
        self.assertLess(torp["y"], 13.0)

        # 持续上浮位移
        prev_y = torp["y"]
        self.game.update(0.05, 0, 0)
        self.assertLess(torp["y"], prev_y)

    def test_torpedo_hits_pt_boat(self):
        """测试鱼雷命中高速鱼雷艇并击沉获得 100 分"""
        self.game.torpedoes.clear()
        self.game.ships.clear()
        self.game.mines.clear()

        # 放置鱼雷艇与正下方鱼雷
        self.game.ships.append({
            "active": True,
            "type": SHIP_PT_BOAT,
            "x": 6.0,
            "y": 2.0,
            "vx": 0.0,
            "hp": 1,
        })
        self.game.torpedoes.append({
            "active": True,
            "x": 6.0,
            "y": 2.5,
            "vy": -10.5,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.ships_sunk, 1)
        self.assertEqual(self.game.score, 100)
        self.assertEqual(len(self.game.torpedoes), 0) # 鱼雷消耗

    def test_torpedo_hits_destroyer_and_carrier(self):
        """测试命中驱逐舰与两发击沉大型航母"""
        self.game.torpedoes.clear()
        self.game.ships.clear()
        self.game.mines.clear()

        # 放置驱逐舰
        self.game.ships.append({
            "active": True,
            "type": SHIP_DESTROYER,
            "x": 8.0,
            "y": 3.5,
            "vx": 0.0,
            "hp": 1,
        })
        self.game.torpedoes.append({
            "active": True,
            "x": 8.0,
            "y": 4.0,
            "vy": -10.5,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.ships_sunk, 1)
        self.assertEqual(self.game.score, 200)

        # 放置大型航母 (HP=2)
        self.game.ships.append({
            "active": True,
            "type": SHIP_CARRIER,
            "x": 8.0,
            "y": 4.5,
            "vx": 0.0,
            "hp": 2,
        })
        # 第一发命中，航母未沉没
        self.game.torpedoes.append({"active": True, "x": 8.0, "y": 4.8, "vy": -10.5})
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.ships[0]["hp"], 1)

        # 第二发致命一击击沉
        self.game.torpedoes.append({"active": True, "x": 8.0, "y": 4.8, "vy": -10.5})
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.ships_sunk, 2)
        self.assertEqual(self.game.score, 600) # 200 + 400

    def test_torpedo_intercepted_by_sea_mine(self):
        """测试游弋水雷拦截鱼雷诱爆引信"""
        self.game.torpedoes.clear()
        self.game.mines.clear()

        self.game.mines.append({
            "active": True,
            "x": 7.0,
            "y": 8.0,
            "vx": 0.0,
        })
        self.game.torpedoes.append({
            "active": True,
            "x": 7.0,
            "y": 8.5,
            "vy": -10.5,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(len(self.game.mines), 0)     # 水雷引爆
        self.assertEqual(len(self.game.torpedoes), 0) # 鱼雷消耗
        self.assertEqual(self.game.score, 20)

    def test_eight_ships_sunk_victory(self):
        """测试击沉 8 艘敌舰达成制海权通关胜利"""
        self.game.ships_sunk = 7
        self.game.ships.clear()
        self.game.torpedoes.clear()

        self.game.ships.append({
            "active": True,
            "type": SHIP_PT_BOAT,
            "x": 5.0,
            "y": 2.0,
            "vx": 0.0,
            "hp": 1,
        })
        self.game.torpedoes.append({
            "active": True,
            "x": 5.0,
            "y": 2.5,
            "vy": -10.5,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.ships_sunk, 8)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 潜艇声呐绿 [46, 204, 113]
        px = int(round(self.game.player_x))
        pidx = (14 * 16 + px) * 3
        self.assertEqual(fb[pidx + 0], 46)
        self.assertEqual(fb[pidx + 1], 204)
        self.assertEqual(fb[pidx + 2], 113)

    def test_status_reporting(self):
        """测试状态字典与击沉进度报告"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["sunk"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)

        self.game.ships_sunk = 4
        st = self.game.get_status()
        self.assertEqual(st["progress"], 50)


if __name__ == "__main__":
    unittest.main()
