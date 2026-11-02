# -*- coding: utf-8 -*-
"""
test_arcade_004_doodle_jump.py —— 涂鸦跳跃 16 自动化单元测试
验证游戏生命周期、物理反弹、左右穿屏、摄像机卷轴与各类跳板机制
"""

import sys
import unittest
from pathlib import Path

# 添加 pc-agent-vision 到模块搜索路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
    KEY_A,
    CTRL_TWO_BUTTON,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)
from arcade.game_004_doodle_jump import (
    Game004DoodleJump,
    Platform,
    PLAT_NORMAL,
    PLAT_SPRING,
    PLAT_FRAGILE,
    PLAT_MOVING,
)
from arcade.arcade_registry import ArcadeRegistry

class TestArcade004DoodleJump(unittest.TestCase):
    def setUp(self):
        self.game = Game004DoodleJump()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册表信息"""
        self.assertEqual(self.game.game_id, 4)
        self.assertEqual(self.game.name, "涂鸦跳跃")
        self.assertEqual(self.game.release_year, 2009)
        self.assertEqual(self.game.control_type, CTRL_TWO_BUTTON)
        self.assertIn("接触刚体自动反弹", self.game.core_mechanic)

        # 检查注册表能够获取到该卡带
        cart = ArcadeRegistry.get_cartridge(4)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "涂鸦跳跃")

    def test_initial_render_and_dimensions(self):
        """测试初始帧渲染与尺寸"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 验证画面不是全黑 (午夜蓝背景 + 角色 + 踏板)
        non_zero = sum(1 for b in fb if b > 0)
        self.assertGreater(non_zero, 500)

    def test_gravity_and_movement(self):
        """测试重力下落与按键加速度响应"""
        self.game.player_vy = 0.0
        self.game.player_vx = 0.0
        old_y = self.game.player_y

        # 模拟一步自由落体
        self.game.update(0.033, 0, 0)
        self.assertGreater(self.game.player_vy, 0.0) # 速度向下增长
        self.assertGreater(self.game.player_y, old_y) # 位置下移

        # 模拟向左按键
        self.game.update(0.033, KEY_LEFT, 0)
        self.assertLess(self.game.player_vx, 0.0)
        self.assertFalse(self.game.facing_right)

        # 模拟向右按键
        self.game.update(0.033, KEY_RIGHT, 0)
        self.game.update(0.033, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_vx, -1.0) # 速度向右回拉

    def test_screen_wrap_around(self):
        """测试角色左右无限穿屏"""
        # 从左边界穿出
        self.game.player_x = -1.6
        self.game.update(0.016, 0, 0)
        self.assertGreater(self.game.player_x, 10.0) # 瞬间传送到右侧

        # 从右边界穿出
        self.game.player_x = 15.6
        self.game.update(0.016, 0, 0)
        self.assertLess(self.game.player_x, 2.0) # 瞬间传送到左侧

    def test_platform_bounce(self):
        """测试踩踏普通跳板自动起跳"""
        # 放置一个固定跳板在角色脚下
        self.game.platforms = [Platform(x=6.0, y=10.0, plat_type=PLAT_NORMAL)]
        self.game.player_x = 7.0
        self.game.player_y = 7.9
        self.game.player_vy = 10.0 # 向下落入平台

        self.game.update(0.02, 0, 0)
        # 碰撞后速度应变为负（向上弹起）
        self.assertLess(self.game.player_vy, 0.0)
        self.assertAlmostEqual(self.game.player_vy, -13.5, delta=1.5)

    def test_spring_platform_super_bounce(self):
        """测试踩踏金色弹簧跳板超级跳"""
        self.game.platforms = [Platform(x=6.0, y=10.0, plat_type=PLAT_SPRING)]
        self.game.player_x = 7.0
        self.game.player_y = 7.9
        self.game.player_vy = 10.0

        self.game.update(0.02, 0, 0)
        self.assertLess(self.game.player_vy, -18.0) # 超级大弹力

    def test_fragile_platform_breaks(self):
        """测试踩踏棕色脆弱跳板破碎断裂"""
        self.game.platforms = [Platform(x=6.0, y=10.0, plat_type=PLAT_FRAGILE)]
        self.game.player_x = 7.0
        self.game.player_y = 7.9
        self.game.player_vy = 10.0

        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.platforms[0].broken) # 标记断裂

    def test_camera_scroll_and_scoring(self):
        """测试当角色上升到上半屏时发生摄像机卷轴下移与高度得分"""
        initial_score = self.game.score
        # 强制将角色置于屏幕最顶部冲刺
        self.game.player_y = 4.0
        self.game.player_vy = -10.0
        self.game.update(0.033, 0, 0)

        # 摄像机应跟随滚动，玩家被锁定在卷轴阈值 7.0，高度和得分增加
        self.assertGreater(self.game.camera_altitude, 0.0)
        self.assertGreater(self.game.score, initial_score)

    def test_game_over_on_fall(self):
        """测试跌落屏幕底部游戏结束"""
        self.game.player_y = 17.0
        self.game.player_vy = 5.0
        self.game.update(0.033, 0, 0)

        self.assertEqual(self.game.state, STATE_GAMEOVER)
        st = self.game.get_status()
        self.assertEqual(st["lives"], 0)

    def test_pause_and_resume(self):
        """测试开始键暂停与继续"""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.game.update(0.033, 0, KEY_START)
        self.assertEqual(self.game.state, STATE_PAUSED)

        self.game.update(0.033, 0, KEY_START)
        self.assertEqual(self.game.state, STATE_PLAYING)

if __name__ == "__main__":
    unittest.main()
