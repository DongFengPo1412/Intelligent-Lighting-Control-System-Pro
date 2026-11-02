# -*- coding: utf-8 -*-
"""
test_arcade_025_bubble_bobble.py —— 经典泡泡龙打怪 1986 完整单元测试
验证吐出气泡、包裹巡逻怪、气泡向上漂浮、跳跃踩破气泡秒杀、借泡反弹跳跃与通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_025_bubble_bobble import Game025BubbleBobble
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


class TestGame025BubbleBobble(unittest.TestCase):
    def setUp(self):
        self.game = Game025BubbleBobble()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 25)
        self.assertEqual(self.game.name, "经典泡泡龙打怪")
        self.assertEqual(self.game.english_name, "Bubble Bobble 1986")
        self.assertEqual(self.game.release_year, 1986)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("吐泡包裹怪物", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(25)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "经典泡泡龙打怪")

    def test_initial_level_and_entities(self):
        """测试初始关卡实体状态: 3 只怪物、玩家底层就位、3 条生命"""
        self.assertEqual(self.game.player_x, 2.0)
        self.assertEqual(self.game.player_y, 13.0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(len(self.game.enemies), 3)
        for e in self.game.enemies:
            self.assertTrue(e["active"])
            self.assertFalse(e["trapped"])

    def test_horizontal_movement_and_direction(self):
        """测试左右移动与面向方向切换"""
        self.assertEqual(self.game.player_dir, 1)

        # 向左移动
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player_dir, -1)
        self.assertLess(self.game.player_x, 2.0)

        # 向右移动
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_dir, 1)

    def test_jump_physics_and_platform_landing(self):
        """测试按 B 键跳跃腾空，并在落回横梁时平稳着陆"""
        self.assertFalse(self.game.is_jumping)

        # 按 B 起跳
        self.game.update(0.05, KEY_B, KEY_B)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.player_vy, 0.0)

        # 滞空下坠回到地面
        for _ in range(30):
            self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.is_jumping)
        self.assertEqual(self.game.player_y, 13.0)

    def test_spit_bubble_and_floating_physics(self):
        """测试按 A 吐出气泡，气泡前冲后随垂直气流向上漂浮"""
        self.assertEqual(len(self.game.bubbles), 0)

        # 吐出气泡
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertEqual(len(self.game.bubbles), 1)
        b = self.game.bubbles[0]
        self.assertGreater(b["vx"], 0.0)

        # 经过若干帧前冲衰减后，开始向上漂浮
        for _ in range(20):
            self.game.update(0.05, 0, 0)

        self.assertLess(b["vy"], 0.0) # 垂直向上浮力
        self.assertLess(b["y"], 13.0)

    def test_bubble_traps_enemy(self):
        """测试气泡撞击游弋怪物将其包裹在气泡内"""
        # 将气泡放置在怪物 0 身边
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 13.0
        self.game.bubbles.append({
            "active": True,
            "x": 6.2,
            "y": 13.0,
            "vx": 0.0,
            "vy": 0.0,
            "trapped_enemy": -1,
            "timer": 5.0,
        })

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.enemies[0]["trapped"])
        self.assertEqual(self.game.bubbles[0]["trapped_enemy"], 0)
        self.assertEqual(self.game.score, 50)

    def test_player_pops_trapped_bubble_defeats_enemy(self):
        """测试玩家跳跃触碰包裹怪物的气泡将其秒杀引爆"""
        self.game.enemies[0]["x"] = 4.0
        self.game.enemies[0]["y"] = 13.0
        self.game.enemies[0]["trapped"] = True

        self.game.bubbles.append({
            "active": True,
            "x": 4.0,
            "y": 13.0,
            "vx": 0.0,
            "vy": 0.0,
            "trapped_enemy": 0,
            "timer": 5.0,
        })

        # 玩家走向气泡并撞破
        self.game.player_x = 4.0
        self.game.player_y = 13.0
        self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.enemies[0]["active"]) # 怪物被秒杀
        self.assertEqual(len(self.game.bubbles), 0)      # 气泡破裂
        self.assertEqual(self.game.score, 300)

    def test_player_bounces_on_empty_bubble(self):
        """测试玩家自空中踩在普通空气泡上借泡反弹跳跃"""
        self.game.bubbles.append({
            "active": True,
            "x": 3.0,
            "y": 12.0,
            "vx": 0.0,
            "vy": 0.0,
            "trapped_enemy": -1,
            "timer": 5.0,
        })

        # 玩家在气泡上方下坠
        self.game.player_x = 3.0
        self.game.player_y = 11.5
        self.game.player_vy = 3.0 # 向下坠落

        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.player_vy, 0.0) # 反弹冲天！
        self.assertEqual(self.game.score, 20)

    def test_untrapped_enemy_damages_player(self):
        """测试未被包裹的怪物直接碰撞伤害玩家损命"""
        self.game.player_x = 8.0
        self.game.player_y = 13.0
        self.game.enemies[0]["x"] = 8.2
        self.game.enemies[0]["y"] = 13.0
        self.game.enemies[0]["trapped"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.player_x, 2.0) # 复位出生点

    def test_victory_on_all_enemies_defeated(self):
        """测试关卡所有怪物消灭后触发通关胜利"""
        for e in self.game.enemies:
            e["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertEqual(self.game.score, 1000)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 嫩草绿横梁 [46, 204, 113]
        self.assertEqual(fb[(14 * 16 + 0) * 3 + 0], 46)
        self.assertEqual(fb[(14 * 16 + 0) * 3 + 1], 204)
        self.assertEqual(fb[(14 * 16 + 0) * 3 + 2], 113)

        # 玩家纯白 [255, 255, 255]
        px = int(round(self.game.player_x))
        py = int(round(self.game.player_y))
        self.assertEqual(fb[(py * 16 + px) * 3 + 0], 255)
        self.assertEqual(fb[(py * 16 + px) * 3 + 1], 255)
        self.assertEqual(fb[(py * 16 + px) * 3 + 2], 255)

    def test_status_reporting(self):
        """测试状态字典与击杀进度输出"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)

        # 消灭 2 只怪
        self.game.enemies[0]["active"] = False
        self.game.enemies[1]["active"] = False
        st = self.game.get_status()
        self.assertEqual(st["progress"], 66)


if __name__ == "__main__":
    unittest.main()
