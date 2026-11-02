# -*- coding: utf-8 -*-
"""
test_arcade_024_lode_runner.py —— 淘金者 1983 完整单元测试
验证左右掘坑陷阱、警卫跌入受困、踏头安全通过、砖块再生闭合活埋、全金收集逃生天梯与通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_024_lode_runner import (
    Game024LodeRunner,
    LODE_AIR,
    LODE_BRICK,
    LODE_SOLID,
    LODE_LADDER,
    LODE_HOLE,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame024LodeRunner(unittest.TestCase):
    def setUp(self):
        self.game = Game024LodeRunner()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心集成"""
        self.assertEqual(self.game.game_id, 24)
        self.assertEqual(self.game.name, "淘金者")
        self.assertEqual(self.game.english_name, "Lode Runner 1983")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("掘坑陷阱", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(24)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "淘金者")

    def test_level_layout_and_entities(self):
        """测试初始关卡布局: 基岩底层、砖块平台、3 块金矿与 2 名巡警"""
        for x in range(16):
            self.assertEqual(self.game.grid[15][x], LODE_SOLID)

        self.assertEqual(self.game.player_x, 1.0)
        self.assertEqual(self.game.player_y, 14.0)
        self.assertEqual(self.game.lives, 3)

        self.assertEqual(len(self.game.golds), 3)
        self.assertEqual(len(self.game.guards), 2)
        self.assertFalse(self.game.escape_ladder_revealed)

    def test_dig_left_and_right_holes(self):
        """测试 A 键左下掘坑、B 键右下掘坑，生成限时塌陷坑洞"""
        # 将玩家放置在砖块平台 (x=7, y=10) 上方 (下方左右 x=6, x=8 均为砖块)
        self.game.player_x = 7.0
        self.game.player_y = 10.0
        self.assertEqual(self.game.grid[11][6], LODE_BRICK)
        self.assertEqual(self.game.grid[11][8], LODE_BRICK)

        # 按 A 键向左下掘坑 (7-1, 10+1) = (6, 11)
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertEqual(self.game.grid[11][6], LODE_HOLE)
        self.assertEqual(self.game.score, 20)

        # 按 B 键向右下掘坑 (7+1, 10+1) = (8, 11)
        self.game.update(0.05, KEY_B, KEY_B)
        self.assertEqual(self.game.grid[11][8], LODE_HOLE)
        self.assertEqual(self.game.score, 40)

    def test_guard_falls_into_hole_trapped(self):
        """测试巡警走入被挖开的砖坑后被困住"""
        self.game.grid[11][5] = LODE_HOLE
        guard = self.game.guards[0]
        guard["x"] = 5.0
        guard["y"] = 11.0
        guard["trapped"] = False

        self.game.update(0.05, 0, 0)
        self.assertTrue(guard["trapped"])
        self.assertGreater(guard["trap_timer"], 3.0)
        self.assertGreaterEqual(self.game.score, 80)

    def test_walk_over_trapped_guard_head(self):
        """测试玩家可以安全踩在被困巡警头顶上走过而不掉落亦不损命"""
        self.game.grid[11][5] = LODE_HOLE
        guard = self.game.guards[0]
        guard["x"] = 5.0
        guard["y"] = 11.0
        guard["trapped"] = True
        guard["trap_timer"] = 3.0

        # 玩家站在被困巡警头上 (x=5, y=10)
        self.game.player_x = 5.0
        self.game.player_y = 10.0
        self.assertFalse(self.game.can_fall(5, 10)) # 不会掉落！

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 3) # 安全通过

    def test_brick_regeneration_buries_guard(self):
        """测试砖坑倒计时填埋再生，活埋困在其中的巡警并重生"""
        self.game.grid[11][5] = LODE_HOLE
        self.game.holes.append({"active": True, "x": 5, "y": 11, "timer": 0.08})

        guard = self.game.guards[0]
        guard["x"] = 5.0
        guard["y"] = 11.0
        guard["trapped"] = True
        guard["trap_timer"] = 3.0

        # 推进时间触发填埋 (循环多次确保计时归零)
        for _ in range(4):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.grid[11][5], LODE_BRICK) # 砖块恢复
        self.assertFalse(guard["trapped"])
        self.assertIn(guard["y"], (1.0, 2.0)) # 顶部重生并受重力下落至上层砖块
        self.assertGreaterEqual(self.game.score, 200)

    def test_gold_collection_and_ladder_reveal(self):
        """测试全金矿收集后显现逃生天梯"""
        self.assertFalse(self.game.escape_ladder_revealed)

        # 依次拾取 3 个金矿
        for i, g in enumerate(self.game.golds):
            self.game.player_x = float(g["x"])
            self.game.player_y = float(g["y"])
            self.game.update(0.05, 0, 0)
            self.assertTrue(g["collected"])

        # 全金收集完毕，逃生天梯在 x=2 处展开
        self.assertTrue(self.game.escape_ladder_revealed)
        for y in range(4):
            self.assertEqual(self.game.grid[y][2], LODE_LADDER)

    def test_escape_ladder_climb_and_victory(self):
        """测试登上逃生天梯登顶脱逃获得通关胜利"""
        self.game.escape_ladder_revealed = True
        self.game.player_x = 2.0
        self.game.player_y = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_guard_catches_player_loss(self):
        """测试未被困住的巡警抓捕玩家损命并淘汰"""
        self.game.lives = 1
        self.game.player_x = 4.0
        self.game.player_y = 14.0

        guard = self.game.guards[0]
        guard["x"] = 4.0
        guard["y"] = 14.0
        guard["trapped"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 基岩灰 [127, 140, 141]
        self.assertEqual(fb[(15 * 16 + 0) * 3 + 0], 127)
        self.assertEqual(fb[(15 * 16 + 0) * 3 + 1], 140)
        self.assertEqual(fb[(15 * 16 + 0) * 3 + 2], 141)

        # 玩家白 [255, 255, 255]
        px = int(round(self.game.player_x))
        py = int(round(self.game.player_y))
        self.assertEqual(fb[(py * 16 + px) * 3 + 0], 255)
        self.assertEqual(fb[(py * 16 + px) * 3 + 1], 255)
        self.assertEqual(fb[(py * 16 + px) * 3 + 2], 255)

    def test_status_reporting(self):
        """测试淘金进度字典与逃生梯状态"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)
        self.assertFalse(st["escape_ladder"])

        # 收集 2 块金矿
        self.game.golds[0]["collected"] = True
        self.game.golds[1]["collected"] = True
        st = self.game.get_status()
        self.assertEqual(st["progress"], 66)


if __name__ == "__main__":
    unittest.main()
