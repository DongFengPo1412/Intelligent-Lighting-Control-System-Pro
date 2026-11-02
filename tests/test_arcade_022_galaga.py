# -*- coding: utf-8 -*-
"""
test_arcade_022_galaga.py —— 星际双子战机 1981 完整单元测试
验证编队俯冲、牵引光束俘虏机制、双子战机合体火力加倍、战机救出与全灭通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_022_galaga import (
    Game022Galaga,
    ALIEN_ZAKO,
    ALIEN_GOEI,
    ALIEN_BOSS,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame022Galaga(unittest.TestCase):
    def setUp(self):
        self.game = Game022Galaga()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心挂载"""
        self.assertEqual(self.game.game_id, 22)
        self.assertEqual(self.game.name, "星际双子战机")
        self.assertEqual(self.game.english_name, "Galaga 1981")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("牵引光束", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(22)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "星际双子战机")

    def test_formation_layout(self):
        """测试敌机编队初始化: 2 只蜂后、4 只红蝶、4 只蓝蜂"""
        self.assertEqual(len(self.game.aliens), 10)
        bosses = [a for a in self.game.aliens if a["type"] == ALIEN_BOSS]
        butterflies = [a for a in self.game.aliens if a["type"] == ALIEN_GOEI]
        zakos = [a for a in self.game.aliens if a["type"] == ALIEN_ZAKO]

        self.assertEqual(len(bosses), 2)
        self.assertEqual(len(butterflies), 4)
        self.assertEqual(len(zakos), 4)
        self.assertEqual(self.game.player_x, 7.0)
        self.assertEqual(self.game.lives, 3)
        self.assertFalse(self.game.is_dual)

    def test_horizontal_movement_and_bounds(self):
        """测试战机左右移动与边界限位"""
        init_x = self.game.player_x

        # 向左移动
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.player_x, init_x)

        # 压到最左限位 0.0
        for _ in range(40):
            self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player_x, 0.0)

        # 移动到最右限位 15.0
        for _ in range(50):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_x, 15.0)

    def test_single_and_dual_firing(self):
        """测试单机单发主炮与双子战机双联齐射"""
        # 单机发射 1 发
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertEqual(len(self.game.bullets), 1)
        self.assertTrue(self.game.bullets[0]["is_player"])

        # 清空子弹冷却与弹池
        self.game.bullets.clear()
        self.game.shoot_cooldown = 0.0
        self.game.is_dual = True

        # 双子发射 2 发平行子弹
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertEqual(len(self.game.bullets), 2)
        self.assertEqual(self.game.bullets[1]["x"], self.game.bullets[0]["x"] + 1.0)

    def test_tractor_beam_capture_mechanic(self):
        """测试蜂后牵引光束捕获玩家战机并扣除生命"""
        for a in self.game.aliens[1:]:
            a["active"] = False # 屏蔽其他杂兵干扰

        boss = self.game.aliens[0]
        boss["x"] = 7.0
        boss["y"] = 7.2
        boss["is_diving"] = True
        boss["vy"] = 0.0
        self.game.player_x = 7.0

        # 触发光束
        self.game.trigger_tractor_beam(0)
        self.assertTrue(self.game.beam_active)

        # 玩家被吸取升天 (1.2s 俘虏判定，运行 25 帧 = 1.25s)
        for _ in range(25):
            self.game.bullets.clear() # 清空随机流弹，专项验证牵引俘虏
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.lives, 2)
        self.assertTrue(boss["has_captured_fighter"])
        self.assertFalse(self.game.beam_active)

    def test_dual_fighter_rescue_and_docking(self):
        """测试击落携带俘虏的蜂后，成功营救并合体为双子战机"""
        boss = self.game.aliens[0]
        boss["has_captured_fighter"] = True
        boss["is_diving"] = True
        boss["x"] = 5.0
        boss["y"] = 8.0
        boss["vx"] = 0.0
        boss["vy"] = 0.0
        self.assertFalse(self.game.is_dual)

        # 玩家发射子弹直击该蜂后 (放置在 boss 下方微小距离，经过 1 帧向上击中 boss)
        self.game.bullets.append({
            "active": True,
            "x": 5.0,
            "y": 8.5,
            "vy": -14.0,
            "is_player": True,
        })

        self.game.update(0.05, 0, 0)
        self.assertFalse(boss["active"])
        self.assertTrue(self.game.is_dual) # 成功解救合体！
        self.assertGreaterEqual(self.game.score, 700) # 200 (boss) + 500 (rescue)

    def test_dual_fighter_damage_downgrade(self):
        """测试双子战机遭受攻击时降级为单机而不损命"""
        self.game.is_dual = True
        self.game.lives = 3
        self.game.player_x = 7.0

        # 敌方子弹击中双子战机僚机 (x=8.0, y=14.0)
        self.game.bullets.append({
            "active": True,
            "x": 8.0,
            "y": 14.0,
            "vy": 6.5,
            "is_player": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.is_dual) # 降级为单机
        self.assertEqual(self.game.lives, 3) # 生命并未损失

    def test_alien_sway_and_dive_cycle(self):
        """测试敌机编队正弦摆动与俯冲状态"""
        alien = self.game.aliens[2] # 红色蝴蝶
        hx = alien["home_x"]
        self.game.update(0.05, 0, 0)
        self.assertNotEqual(alien["x"], hx) # 产生水平摆动

        # 推进俯冲计时器触发俯冲
        self.game.dive_cycle_timer = 2.98
        self.game.update(0.05, 0, 0)
        diving_count = sum(1 for a in self.game.aliens if a["is_diving"])
        self.assertGreaterEqual(diving_count, 1)

    def test_gameover_on_lives_exhausted(self):
        """测试单机被敌方击中生命耗尽判定 GAMEOVER"""
        self.game.is_dual = False
        self.game.lives = 1
        self.game.player_x = 7.0

        self.game.bullets.append({
            "active": True,
            "x": 7.0,
            "y": 14.0,
            "vy": 6.5,
            "is_player": False,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_victory_on_all_aliens_cleared(self):
        """测试清空所有敌机触发 STATE_VICTORY"""
        for a in self.game.aliens:
            a["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 玩家单机纯白 [255, 255, 255]
        px = int(round(self.game.player_x))
        pidx = (14 * 16 + px) * 3
        self.assertEqual(fb[pidx + 0], 255)
        self.assertEqual(fb[pidx + 1], 255)
        self.assertEqual(fb[pidx + 2], 255)

        # 双子战机僚机青蓝 [0, 255, 255]
        self.game.is_dual = True
        fb_dual = self.game.render()
        pidx2 = (14 * 16 + px + 1) * 3
        self.assertEqual(fb_dual[pidx2 + 0], 0)
        self.assertEqual(fb_dual[pidx2 + 1], 255)
        self.assertEqual(fb_dual[pidx2 + 2], 255)

    def test_status_reporting(self):
        """测试状态字典输出与通关进度计算"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)
        self.assertFalse(st["is_dual"])

        # 击毁 5 只敌机
        for i in range(5):
            self.game.aliens[i]["active"] = False
        st = self.game.get_status()
        self.assertEqual(st["progress"], 50)


if __name__ == "__main__":
    unittest.main()
