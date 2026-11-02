# -*- coding: utf-8 -*-
"""
test_arcade_029_slither_arena.py —— 像素贪吃蛇大作战 2016 完整单元测试
验证多蛇同屏竞技、蛇头撞身暴毙解体、光子吞食激增、损躯冲刺掉尾截杀与胜负判定
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_029_slither_arena import Game029SlitherArena
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


class TestGame029SlitherArena(unittest.TestCase):
    def setUp(self):
        self.game = Game029SlitherArena()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心挂载"""
        self.assertEqual(self.game.game_id, 29)
        self.assertEqual(self.game.name, "蛇蛇大作战")
        self.assertEqual(self.game.english_name, "Slither Arena 2016")
        self.assertEqual(self.game.release_year, 2016)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("多蛇竞技追尾拦截", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(29)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "蛇蛇大作战")

    def test_initial_arena_state(self):
        """测试竞技场初始双蛇就位与光子散布"""
        self.assertEqual(len(self.game.player_body), 5)
        self.assertEqual(len(self.game.ai_body), 5)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.kill_count, 0)
        self.assertGreaterEqual(len(self.game.orbs), 6)

    def test_steering_and_movement(self):
        """测试转向与防 180° 自杀调头"""
        self.assertEqual(self.game.player_dir, 1) # 向右

        # 尝试反向向左 (应被禁止，保持向右)
        self.game.update(0.05, 0, KEY_LEFT)
        self.assertEqual(self.game.player_dir, 1)

        # 向上转向
        self.game.update(0.05, 0, KEY_UP)
        self.assertEqual(self.game.player_dir, 0)

        # 推进步进时间完成位移
        init_hy = self.game.player_body[0]["y"]
        for _ in range(4):
            self.game.update(0.05, 0, 0)
        self.assertLess(self.game.player_body[0]["y"], init_hy)

    def test_boost_speed_and_segment_drop(self):
        """测试按住 A 键冲刺消耗尾段并在原位掉落光子"""
        self.assertEqual(len(self.game.player_body), 5)
        init_orbs_count = len(self.game.orbs)

        # 按住 A 冲刺加速推进 0.4 秒 (触发掉尾)
        for _ in range(8):
            self.game.update(0.05, KEY_A, 0)

        self.assertTrue(self.game.player_boosting)
        self.assertEqual(len(self.game.player_body), 4) # 缩短 1 节
        self.assertGreater(len(self.game.orbs), init_orbs_count) # 场上新增掉落光子

    def test_eat_energy_orb_growth(self):
        """测试吞食能量光子后身体变长并增分"""
        init_len = len(self.game.player_body)
        head = self.game.player_body[0]

        # 在玩家正前方放置光子
        self.game.orbs.append({
            "active": True,
            "x": head["x"] + 1,
            "y": head["y"],
            "value": 1,
        })

        for _ in range(4):
            self.game.update(0.05, 0, 0)

        self.assertEqual(len(self.game.player_body), init_len + 1)
        self.assertGreater(self.game.score, 0)

    def test_ai_head_hits_player_body_kill(self):
        """测试 AI 蛇头撞击玩家蛇身，AI 暴毙解体掉落光子，玩家获得击杀"""
        self.assertEqual(self.game.kill_count, 0)
        self.assertTrue(self.game.ai_alive)

        # 玩家蛇身横贯在 (6, 7) 到 (2, 7)
        # 将 AI 蛇头直接置于玩家蛇身段 (5, 7)
        self.game.ai_body[0]["x"] = self.game.player_body[1]["x"]
        self.game.ai_body[0]["y"] = self.game.player_body[1]["y"]

        self.game.check_inter_snake_collisions()
        self.assertFalse(self.game.ai_alive) # AI 爆裂解体！
        self.assertEqual(self.game.kill_count, 1) # 击杀计分
        self.assertGreaterEqual(self.game.score, 500)

    def test_player_head_hits_ai_body_death(self):
        """测试玩家蛇头撞击 AI 蛇身导致自身暴毙损命"""
        self.assertEqual(self.game.lives, 3)

        # 将玩家蛇头撞向 AI 蛇身 (ai_body[1])
        self.game.player_body[0]["x"] = self.game.ai_body[1]["x"]
        self.game.player_body[0]["y"] = self.game.ai_body[1]["y"]

        self.game.check_inter_snake_collisions()
        self.assertEqual(self.game.lives, 2) # 损失一条命并复位

    def test_victory_by_kills_or_length(self):
        """测试累计击杀 3 条竞争蛇或体长达到 16 节达成霸主胜利"""
        self.game.kill_count = 3
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_gameover_on_lives_exhausted(self):
        """测试生命耗尽触发 GAMEOVER"""
        self.game.lives = 1
        self.game.player_body[0]["x"] = self.game.ai_body[1]["x"]
        self.game.player_body[0]["y"] = self.game.ai_body[1]["y"]

        self.game.check_inter_snake_collisions()
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 玩家蛇头青蓝光辉 [0, 255, 255]
        phx = self.game.player_body[0]["x"]
        phy = self.game.player_body[0]["y"]
        pidx = (phy * 16 + phx) * 3
        self.assertEqual(fb[pidx + 0], 0)
        self.assertEqual(fb[pidx + 1], 255)
        self.assertEqual(fb[pidx + 2], 255)

    def test_status_reporting(self):
        """测试状态字典与长度进度输出"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["length"], 5)
        self.assertEqual(st["kills"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)


if __name__ == "__main__":
    unittest.main()
