# -*- coding: utf-8 -*-
"""
test_arcade_015_tron.py —— 创战纪光轮摩托 1982 完整单元测试
验证光轮摩托极速行进、永久光痕墙壁、禁180度掉头、自撞/撞墙判定、AI智能避障与对局胜负
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_015_tron import Game015Tron, TRON_NONE, TRON_WALL, TRON_P1, TRON_P2_AI
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_DPAD_4WAY,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame015Tron(unittest.TestCase):
    def setUp(self):
        self.game = Game015Tron()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 15)
        self.assertEqual(self.game.name, "创战纪光轮摩托")
        self.assertEqual(self.game.english_name, "Tron Light Cycles 1982")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)

        cart = ArcadeRegistry.get_cartridge(15)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "创战纪光轮摩托")

    def test_arena_and_cycle_initialization(self):
        """测试竞技场电栅与双方摩托初始站位"""
        # 外围是墙
        self.assertEqual(self.game.grid[0][0], TRON_WALL)
        self.assertEqual(self.game.grid[15][15], TRON_WALL)
        # 初始站位已落下初始光痕
        self.assertEqual(self.game.p1.x, 3)
        self.assertEqual(self.game.p1.y, 8)
        self.assertEqual(self.game.grid[8][3], TRON_P1)

        self.assertEqual(self.game.p2.x, 12)
        self.assertEqual(self.game.p2.y, 8)
        self.assertEqual(self.game.grid[8][12], TRON_P2_AI)

    def test_stepping_and_trail_persistence(self):
        """测试行进步进与身后永久光痕留下"""
        # 设置计时器触发步进
        self.game.step_timer = self.game.step_interval
        self.game.update(0.01, 0, 0)
        # P1 向右走了 1 格到 (4, 8)
        self.assertEqual(self.game.p1.x, 4)
        self.assertEqual(self.game.p1.y, 8)
        # (3, 8) 与 (4, 8) 都留下了永久光痕
        self.assertEqual(self.game.grid[8][3], TRON_P1)
        self.assertEqual(self.game.grid[8][4], TRON_P1)

    def test_turning_disallows_180_reverse(self):
        """测试禁止 180 度反向逆行自撞"""
        self.assertEqual(self.game.p1.dir_x, 1)
        self.assertEqual(self.game.p1.dir_y, 0)

        # 尝试向左调头
        self.game.update(0.02, 0, KEY_LEFT)
        # 必须被拒绝，维持向右
        self.assertEqual(self.game.p1.dir_x, 1)

        # 允许 90 度转向 (向上)
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.p1.dir_x, 0)
        self.assertEqual(self.game.p1.dir_y, -1)

    def test_wall_collision_causes_round_loss(self):
        """测试撞击外围竞技场电栅导致当局告负"""
        self.assertEqual(self.game.p2_wins, 0)
        # 人工将 P1 放置在贴墙位置并向上撞墙 (y=0 是墙)
        self.game.p1.x = 3
        self.game.p1.y = 1
        self.game.p1.dir_x = 0
        self.game.p1.dir_y = -1

        # 触发步进
        self.game.step_timer = self.game.step_interval
        self.game.update(0.01, 0, 0)

        # P1 撞墙，P2 获得一胜，回合重置
        self.assertEqual(self.game.p2_wins, 1)
        self.assertEqual(self.game.p1.x, 3)
        self.assertEqual(self.game.p1.y, 8)

    def test_opponent_trail_collision(self):
        """测试撞击对手光痕墙壁判负"""
        # 人工在 P1 正前方 (4, 8) 放置一段 P2 的光痕
        self.game.grid[8][4] = TRON_P2_AI
        self.assertEqual(self.game.p2_wins, 0)

        # P1 向右踏入 (4, 8)
        self.game.step_timer = self.game.step_interval
        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.p2_wins, 1)

    def test_head_on_collision_draw(self):
        """测试两车迎面相撞判平局重开，双方皆不得分"""
        # 让 P1 与 P2 相距 2 格即将对撞
        self.game.p1.x = 7
        self.game.p1.y = 8
        self.game.p1.dir_x = 1
        self.game.p1.dir_y = 0

        self.game.p2.x = 9
        self.game.p2.y = 8
        self.game.p2.dir_x = -1
        self.game.p2.dir_y = 0

        # 两车将在 (8, 8) 对撞
        self.game.step_timer = self.game.step_interval
        self.game.update(0.01, 0, 0)

        # 平局，胜场皆不变
        self.assertEqual(self.game.p1_wins, 0)
        self.assertEqual(self.game.p2_wins, 0)

    def test_ai_turns_away_from_wall(self):
        """测试 AI 检测到前方挡道时自动 90 度紧急避障转向"""
        # 将 P2 放置在贴近右墙处 (14, 8)，方向仍为向右的话会撞墙，向左不会
        # 让 P2 初始向右移动朝向外墙
        self.game.p2.x = 14
        self.game.p2.y = 5
        self.game.p2.dir_x = 1
        self.game.p2.dir_y = 0

        self.game.step_ai()
        # AI 必须转向，dir_x 不再为 1
        self.assertEqual(self.game.p2.dir_x, 0)
        self.assertIn(self.game.p2.dir_y, (-1, 1))

    def test_victory_on_three_wins(self):
        """测试赢得 3 回合对决取得比赛最终胜利"""
        self.game.p1_wins = 2
        # 将 P2 困在死胡同角落 (1, 1)，四面皆死路 (左0,1墙, 上1,0墙, 下1,2墙)
        self.game.p2.x = 1
        self.game.p2.y = 1
        self.game.p2.dir_x = -1
        self.game.p2.dir_y = 0
        self.game.grid[2][1] = TRON_WALL # 封死向下退路

        self.game.step_timer = self.game.step_interval
        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.p1_wins, 3)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 0)

    def test_gameover_on_three_losses(self):
        """测试输掉 3 回合判定 Game Over"""
        self.game.p2_wins = 2
        # 让 P1 即将撞墙
        self.game.p1.x = 1
        self.game.p1.y = 1
        self.game.p1.dir_x = -1
        self.game.p1.dir_y = 0

        self.game.step_timer = self.game.step_interval
        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.p2_wins, 3)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
