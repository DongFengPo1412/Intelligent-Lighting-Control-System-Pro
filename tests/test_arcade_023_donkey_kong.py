# -*- coding: utf-8 -*-
"""
test_arcade_023_donkey_kong.py —— 经典大金刚 1981 完整单元测试
验证多层钢梁跑动、垂直梯子攀爬、起跳跨木桶、铁锤暴击砸桶、宝琳营救通关与命尽淘汰
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_023_donkey_kong import Game023DonkeyKong
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame023DonkeyKong(unittest.TestCase):
    def setUp(self):
        self.game = Game023DonkeyKong()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心集成"""
        self.assertEqual(self.game.game_id, 23)
        self.assertEqual(self.game.name, "经典大金刚")
        self.assertEqual(self.game.english_name, "Donkey Kong 1981")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("梯子垂直攀爬", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(23)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "经典大金刚")

    def test_initial_level_state(self):
        """测试初始关卡实体状态: 玩家底层出生、铁锤道具就绪、3 条生命"""
        self.assertEqual(self.game.player_x, 1.0)
        self.assertEqual(self.game.player_y, 13.0)
        self.assertEqual(self.game.lives, 3)
        self.assertTrue(self.game.hammer_available)
        self.assertEqual(self.game.hammer_x, 2)
        self.assertEqual(self.game.hammer_y, 9)
        self.assertFalse(self.game.is_climbing)
        self.assertFalse(self.game.is_jumping)

    def test_platform_movement_and_bounds(self):
        """测试横梁跑动位移与左右边界限位"""
        init_x = self.game.player_x

        # 向右跑动
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, init_x)

        # 压到左边缘限位 0.0
        for _ in range(40):
            self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player_x, 0.0)

        # 压到右边缘限位 15.0
        for _ in range(70):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_x, 15.0)

    def test_ladder_climbing(self):
        """测试玩家步入梯子区域后沿梯子垂直上下攀爬"""
        # 将玩家放置于梯子 1 (x=12, y=10..14)
        self.game.player_x = 12.0
        self.game.player_y = 13.0

        # 按 UP 触发攀爬
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.is_climbing)
        self.game.update(0.05, KEY_UP, 0)
        self.assertLess(self.game.player_y, 13.0)

        # 向上攀爬至层 1 (y=9.0) 脱离梯子
        for _ in range(25):
            self.game.update(0.05, KEY_UP, 0)

        self.assertFalse(self.game.is_climbing)
        self.assertEqual(self.game.player_y, 9.0)

    def test_jump_physics(self):
        """测试按下跳跃键腾空抛物线起跳并落地回稳"""
        self.assertFalse(self.game.is_jumping)
        init_y = self.game.player_y

        # 按 A 起跳
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertTrue(self.game.is_jumping)
        self.assertLess(self.game.player_vy, 0.0)

        # 腾空过程中高度上升 (y 变小)
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.player_y, init_y)

        # 重力下坠并落回地面
        for _ in range(30):
            self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.is_jumping)
        self.assertEqual(self.game.player_y, init_y)

    def test_hammer_pickup_and_timer(self):
        """测试拾取铁锤道具: 激活 5 秒暴走状态并获得 200 分"""
        self.game.player_x = 2.0
        self.game.player_y = 9.0
        self.assertTrue(self.game.hammer_available)
        self.assertEqual(self.game.score, 0)

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.hammer_available)
        self.assertGreater(self.game.hammer_timer, 4.9)
        self.assertEqual(self.game.score, 200)

    def test_hammer_smashes_barrel(self):
        """测试持锤状态迎面砸碎滚木桶获得 300 分奖励"""
        self.game.hammer_timer = 4.0
        self.game.player_x = 5.0
        self.game.player_y = 13.0

        # 木桶迎面滚来
        self.game.barrels.append({
            "active": True,
            "x": 5.2,
            "y": 13.0,
            "vx": -3.5,
            "layer": 0,
            "falling_ladder": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(len(self.game.barrels), 0) # 木桶被粉碎
        self.assertEqual(self.game.score, 300)
        self.assertEqual(self.game.lives, 3) # 玩家未受伤害

    def test_barrel_roll_and_layer_drop(self):
        """测试木桶顺坡横滚并自边缘跌落下层"""
        self.game.barrels.append({
            "active": True,
            "x": 10.8,
            "y": 2.0,
            "vx": 3.5,
            "layer": 3,
            "falling_ladder": False,
        })

        # 滚过 x=11 边缘跌落到层 2
        for _ in range(4):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.barrels[0]["layer"], 2)
        self.assertLess(self.game.barrels[0]["vx"], 0.0) # 反向向左滚

    def test_barrel_collision_damages_player(self):
        """测试无铁锤时被木桶撞击损命并重置至底层出生点"""
        self.game.hammer_timer = 0.0
        self.game.player_x = 6.0
        self.game.player_y = 13.0
        self.assertEqual(self.game.lives, 3)

        self.game.barrels.append({
            "active": True,
            "x": 6.2,
            "y": 13.0,
            "vx": -3.5,
            "layer": 0,
            "falling_ladder": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.player_x, 1.0) # 复位出生点

    def test_rescue_pauline_victory(self):
        """测试玩家登顶顶层成功触碰宝琳拯救获胜"""
        self.game.player_x = 9.5
        self.game.player_y = 1.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertEqual(self.game.score, 1000)

    def test_gameover_on_lives_exhausted(self):
        """测试生命耗尽触发 GAMEOVER"""
        self.game.lives = 1
        self.game.player_x = 6.0
        self.game.player_y = 13.0

        self.game.barrels.append({
            "active": True,
            "x": 6.2,
            "y": 13.0,
            "vx": -3.5,
            "layer": 0,
            "falling_ladder": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 钢梁红 [231, 76, 60]
        self.assertEqual(fb[(14 * 16 + 0) * 3 + 0], 231)
        self.assertEqual(fb[(14 * 16 + 0) * 3 + 1], 76)
        self.assertEqual(fb[(14 * 16 + 0) * 3 + 2], 60)

        # 梯子蓝 [52, 152, 219]
        self.assertEqual(fb[(12 * 16 + 12) * 3 + 0], 52)
        self.assertEqual(fb[(12 * 16 + 12) * 3 + 1], 152)
        self.assertEqual(fb[(12 * 16 + 12) * 3 + 2], 219)

    def test_status_reporting(self):
        """测试状态监控与攀登高度进度报告"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)
        self.assertFalse(st["has_hammer"])

        # 登到顶层
        self.game.player_y = 1.0
        st = self.game.get_status()
        self.assertEqual(st["progress"], 100)


if __name__ == "__main__":
    unittest.main()
