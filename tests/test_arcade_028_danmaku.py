# -*- coding: utf-8 -*-
"""
test_arcade_028_danmaku.py —— 蜂群极速弹幕 1997 完整单元测试
验证 1 像素核心 Hitbox、擦弹(Graze)高险得分、全屏清弹 Bomb、螺旋弹幕与击沉 Boss 通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_028_danmaku import Game028Danmaku
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


class TestGame028Danmaku(unittest.TestCase):
    def setUp(self):
        self.game = Game028Danmaku()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心挂载"""
        self.assertEqual(self.game.game_id, 28)
        self.assertEqual(self.game.name, "蜂群极速弹幕")
        self.assertEqual(self.game.english_name, "Danmaku 1997")
        self.assertEqual(self.game.release_year, 1997)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("1像素Hitbox", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(28)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "蜂群极速弹幕")

    def test_boss_and_player_initial_state(self):
        """测试 Boss 与战机初始就绪属性"""
        self.assertEqual(self.game.boss["hp"], 100)
        self.assertEqual(self.game.player_x, 7.5)
        self.assertEqual(self.game.player_y, 13.5)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.bombs, 2)
        self.assertEqual(self.game.graze_count, 0)

    def test_player_micro_movement_and_bounds(self):
        """测试八向灵动微操移动与边界限制"""
        init_x = self.game.player_x
        init_y = self.game.player_y

        # 左移
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.player_x, init_x)

        # 压到左限位 0.5
        for _ in range(40):
            self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player_x, 0.5)

        # 上移压到上限位 4.0
        for _ in range(40):
            self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.player_y, 4.0)

    def test_player_shooting_and_boss_damage(self):
        """测试按住 A 发射高频主炮命中 Boss 造成伤害"""
        self.game.bullets.clear()
        self.assertEqual(self.game.boss["hp"], 100)

        # 玩家在 Boss 正下方发射主炮
        self.game.player_x = 7.5
        self.game.player_y = 6.0
        self.game.boss["x"] = 7.5
        self.game.boss["y"] = 2.5

        self.game.update(0.05, KEY_A, 0)
        self.assertGreaterEqual(len(self.game.bullets), 1)
        self.assertTrue(self.game.bullets[0]["is_player"])

        # 子弹高速向上飞击中 Boss
        for _ in range(10):
            self.game.update(0.05, 0, 0)

        self.assertLess(self.game.boss["hp"], 100)
        self.assertGreater(self.game.score, 0)

    def test_graze_mechanic_near_miss(self):
        """测试擦弹(Graze)核心机制: 弹幕擦肩而过积累分数且不扣命"""
        self.assertEqual(self.game.graze_count, 0)
        self.assertEqual(self.game.lives, 3)
        self.game.player_x = 7.5
        self.game.player_y = 12.0

        # 在玩家侧翼 1.0 像素处（擦弹区：0.65 < dist <= 1.4）放置敌弹
        self.game.bullets.append({
            "active": True,
            "x": 8.5, # 距离判定点恰好 1.0 像素
            "y": 12.0,
            "vx": 0.0,
            "vy": 0.0,
            "is_player": False,
            "grazed": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.graze_count, 1) # 成功擦弹！
        self.assertEqual(self.game.lives, 3)       # 未受伤害！
        self.assertEqual(self.game.score, 20)      # 获得擦弹分
        self.assertTrue(self.game.bullets[0]["grazed"]) # 不重复擦同颗弹

    def test_direct_hit_loses_life(self):
        """测试 1 像素核心被敌弹直接击穿扣减生命"""
        self.game.player_x = 7.5
        self.game.player_y = 12.0
        self.assertEqual(self.game.lives, 3)

        # 直击核心 (dist <= 0.65)
        self.game.bullets.append({
            "active": True,
            "x": 7.5,
            "y": 12.2,
            "vx": 0.0,
            "vy": 0.0,
            "is_player": False,
            "grazed": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)

    def test_screen_clearing_bomb(self):
        """测试按 B 释放清屏保命炸弹，消灭所有敌弹并重创 Boss"""
        self.assertEqual(self.game.bombs, 2)
        init_boss_hp = self.game.boss["hp"]

        # 场上充满敌弹
        for i in range(5):
            self.game.bullets.append({
                "active": True,
                "x": float(i * 2 + 1),
                "y": 8.0,
                "vx": 0.0,
                "vy": 2.0,
                "is_player": False,
                "grazed": False,
            })

        self.game.update(0.05, 0, KEY_B) # 轰爆炸弹！
        self.assertEqual(self.game.bombs, 1)
        self.assertEqual(self.game.boss["hp"], init_boss_hp - 25) # 重创 25 点！

        # 敌弹全数蒸发
        enemy_bullets = [b for b in self.game.bullets if not b["is_player"]]
        self.assertEqual(len(enemy_bullets), 0)
        self.assertGreaterEqual(self.game.score, 500)

    def test_spiral_and_ring_barrage_emission(self):
        """测试 Boss 阶段发射密集螺旋与圆环弹幕"""
        self.game.bullets.clear()
        self.game.boss["pattern_timer"] = 0.2
        self.game.update(0.05, 0, 0)

        # 螺旋弹幕产生
        enemy_bullets = [b for b in self.game.bullets if not b["is_player"]]
        self.assertGreater(len(enemy_bullets), 0)

    def test_boss_defeat_victory(self):
        """测试击坠 Boss 触发 STATE_VICTORY"""
        self.game.boss["hp"] = 1
        self.game.bullets.clear()

        # 玩家发射致胜一击
        self.game.bullets.append({
            "active": True,
            "x": self.game.boss["x"],
            "y": self.game.boss["y"] + 0.5,
            "vx": 0.0,
            "vy": -15.0,
            "is_player": True,
            "grazed": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 2000)

    def test_gameover_on_lives_exhausted(self):
        """测试生命耗尽触发 GAMEOVER"""
        self.game.lives = 1
        self.game.player_x = 7.5
        self.game.player_y = 12.0

        self.game.bullets.append({
            "active": True,
            "x": 7.5,
            "y": 12.0,
            "vx": 0.0,
            "vy": 0.0,
            "is_player": False,
            "grazed": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 玩家战机核心红色判定点 [255, 50, 50]
        px = int(round(self.game.player_x))
        py = int(round(self.game.player_y))
        cidx = (py * 16 + px) * 3
        self.assertEqual(fb[cidx + 0], 255)
        self.assertEqual(fb[cidx + 1], 50)
        self.assertEqual(fb[cidx + 2], 50)

    def test_status_reporting(self):
        """测试状态字典与击沉进度报告"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["bombs"], 2)
        self.assertEqual(st["graze"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)

        self.game.boss["hp"] = 50
        st = self.game.get_status()
        self.assertEqual(st["progress"], 50)


if __name__ == "__main__":
    unittest.main()
