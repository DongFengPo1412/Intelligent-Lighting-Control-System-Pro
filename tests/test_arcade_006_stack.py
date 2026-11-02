# -*- coding: utf-8 -*-
"""
test_arcade_006_stack.py —— 堆叠大师 16 自动化单元测试
验证方块平移巡逻、单键切除多余边缘、对齐完美吸附、碎片掉落、彩虹色谱与卷轴下沉
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    CTRL_TAP_SINGLE,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
)
from arcade.game_006_stack import Game006Stack
from arcade.arcade_registry import ArcadeRegistry

class TestArcade006Stack(unittest.TestCase):
    def setUp(self):
        self.game = Game006Stack()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册表信息"""
        self.assertEqual(self.game.game_id, 6)
        self.assertEqual(self.game.name, "堆叠大师")
        self.assertEqual(self.game.release_year, 2016)
        self.assertEqual(self.game.control_type, CTRL_TAP_SINGLE)
        self.assertIn("切除", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(6)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "堆叠大师")

    def test_initial_render_and_dimensions(self):
        """测试初始帧渲染非黑有效性与底座呈现"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查底部底座有非零像素
        base_pixels = 0
        for x in range(16):
            idx = (15 * 16 + x) * 3
            if fb[idx] > 0 or fb[idx+1] > 0 or fb[idx+2] > 0:
                base_pixels += 1
        self.assertGreater(base_pixels, 6)

    def test_horizontal_block_movement(self):
        """测试活动方块在水平方向来回往返巡逻"""
        old_x = self.game.active_x
        self.game.update(0.05, 0, 0)
        self.assertNotEqual(self.game.active_x, old_x)

        # 步进让方块撞击右边界并掉头
        self.game.active_x = 15.8
        self.game.active_vx = 8.0
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.active_vx, 0.0) # 速度变为负数反向

    def test_perfect_alignment_snap(self):
        """测试完美对齐吸附与连击高光"""
        base_x = self.game.layers[-1].x
        # 强制将活动方块放在与基座极微小偏差位置 (< 0.42 像素)
        self.game.active_x = base_x + 0.2
        self.game.update(0.016, 0, KEY_A) # 单键轻触放置

        # 应完美对齐至 base_x，连击增加
        self.assertEqual(self.game.layers[-1].x, base_x)
        self.assertEqual(self.game.perfect_combo, 1)
        self.assertGreater(self.game.perfect_flash, 0.0)

    def test_slice_overhang_cut_right(self):
        """测试右侧多余悬空切除并收窄"""
        base_x = self.game.layers[-1].x
        base_w = self.game.layers[-1].w

        # 方块向右偏移 2 像素
        self.game.active_x = base_x + 2.0
        self.game.active_w = base_w
        self.game.update(0.016, 0, KEY_A)

        # 新层宽度应减少 2 像素
        new_w = self.game.layers[-1].w
        self.assertAlmostEqual(new_w, base_w - 2.0, delta=0.1)
        # 应产生掉落碎片
        self.assertGreater(len(self.game.debris), 0)

    def test_slice_overhang_cut_left(self):
        """测试左侧多余悬空切除并收窄"""
        base_x = self.game.layers[-1].x
        base_w = self.game.layers[-1].w

        # 方块向左偏移 2 像素
        self.game.active_x = base_x - 2.0
        self.game.active_w = base_w
        self.game.update(0.016, 0, KEY_A)

        # 新层宽度应减少 2 像素
        new_w = self.game.layers[-1].w
        self.assertAlmostEqual(new_w, base_w - 2.0, delta=0.1)
        self.assertEqual(self.game.layers[-1].x, base_x)

    def test_miss_completely_game_over(self):
        """测试方块完全未击中基座游戏结束"""
        # 将方块放在远离基座的位置 (x=15, 远脱离 base_x=3.5~12.5)
        self.game.active_x = 14.5
        self.game.active_w = 4.0
        self.game.update(0.016, 0, KEY_A)

        self.assertEqual(self.game.state, STATE_GAMEOVER)
        st = self.game.get_status()
        self.assertEqual(st["lives"], 0)

    def test_vertical_stacking_and_camera_scroll(self):
        """测试持续叠放上升与超过第5行时的摄像机下沉"""
        initial_score = self.game.score
        base_x = self.game.layers[-1].x

        # 连续完美放置 12 次
        for _ in range(12):
            self.game.active_x = base_x
            self.game.update(0.016, 0, KEY_A)

        self.assertEqual(self.game.score, initial_score + 12)
        # 应该限制在当前行 >= 5 且历史层数组正确维护
        self.assertGreaterEqual(self.game.current_row, 5)

    def test_hsv_rainbow_colors(self):
        """测试每层颜色呈彩虹色相循环流动渐变"""
        color0 = self.game._get_layer_color(0)
        color5 = self.game._get_layer_color(5)
        color10 = self.game._get_layer_color(10)
        # 验证不同高度具有明显色相差异
        self.assertNotEqual(color0, color5)
        self.assertNotEqual(color5, color10)

    def test_pause_and_reset(self):
        """测试暂停与重开"""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.game.update(0.033, 0, KEY_START)
        self.assertEqual(self.game.state, STATE_PAUSED)

        self.game.update(0.033, 0, KEY_START)
        self.assertEqual(self.game.state, STATE_PLAYING)

if __name__ == "__main__":
    unittest.main()
