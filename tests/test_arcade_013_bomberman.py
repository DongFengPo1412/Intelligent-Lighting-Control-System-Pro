# -*- coding: utf-8 -*-
"""
test_arcade_013_bomberman.py —— 像素炸弹人 1983 完整单元测试
验证网格漫游、埋雷定时、十字爆破、软砖碎裂、自爆波及、杀怪得分与通关判定
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_013_bomberman import Game013Bomberman, TILE_EMPTY, TILE_HARD_WALL, TILE_SOFT_BRICK
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

class TestGame013Bomberman(unittest.TestCase):
    def setUp(self):
        self.game = Game013Bomberman()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 13)
        self.assertEqual(self.game.name, "像素炸弹人")
        self.assertEqual(self.game.english_name, "Bomberman 1983")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)

        cart = ArcadeRegistry.get_cartridge(13)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "像素炸弹人")

    def test_map_pillar_and_spawn_safeguard(self):
        """测试地图支柱分布与玩家出生点净空保护"""
        # 外墙为硬墙
        self.assertEqual(self.game.map[0][0], TILE_HARD_WALL)
        self.assertEqual(self.game.map[15][15], TILE_HARD_WALL)

        # 内部偶数坐标为支柱硬墙
        self.assertEqual(self.game.map[2][2], TILE_HARD_WALL)
        self.assertEqual(self.game.map[4][4], TILE_HARD_WALL)

        # 玩家出生区净空
        self.assertEqual(self.game.map[1][1], TILE_EMPTY)
        self.assertEqual(self.game.map[1][2], TILE_EMPTY)
        self.assertEqual(self.game.map[2][1], TILE_EMPTY)

    def test_player_walking_and_collision(self):
        """测试玩家可行走于空地，被硬墙阻隔"""
        self.assertEqual(self.game.player_x, 1.0)
        self.assertEqual(self.game.player_y, 1.0)

        # 向上走撞外墙 (y=0 是硬墙)
        self.game.update(0.1, KEY_UP, 0)
        self.assertEqual(self.game.player_y, 1.0)

        # 向右走进入 (2, 1) 空地
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, 1.0)

    def test_bomb_placement_and_countdown(self):
        """测试按 A 埋设炸弹与倒计时"""
        self.assertFalse(self.game.bomb.active)

        self.game.update(0.02, 0, KEY_A)
        self.assertTrue(self.game.bomb.active)
        self.assertEqual(self.game.bomb.gx, 1)
        self.assertEqual(self.game.bomb.gy, 1)
        self.assertAlmostEqual(self.game.bomb.timer, 2.0, delta=0.1)

    def test_cross_flame_breaks_soft_brick(self):
        """测试十字烈焰爆破炸碎软砖并加分"""
        # 在 (3, 1) 设置一块软砖，在 (2, 1) 埋雷
        self.game.map[1][3] = TILE_SOFT_BRICK
        self.game.bomb.active = True
        self.game.bomb.gx = 2
        self.game.bomb.gy = 1
        self.game.bomb.range = 2

        # 玩家躲在拐角 (1, 2)，受柱子 (2, 2) 遮挡保护
        self.game.player_x = 1.0
        self.game.player_y = 2.0

        initial_score = self.game.score
        self.game.bomb.timer = 0.01
        self.game.update(0.02, 0, 0)

        # 软砖已被炸碎为 EMPTY
        self.assertEqual(self.game.map[1][3], TILE_EMPTY)
        self.assertFalse(self.game.bomb.active)
        self.assertGreater(len(self.game.flames), 0)
        self.assertEqual(self.game.score, initial_score + 20)

    def test_hard_wall_blocks_flame(self):
        """测试硬墙阻断烈焰蔓延"""
        # (2, 2) 是硬墙，雷在 (1, 2)
        self.assertEqual(self.game.map[2][2], TILE_HARD_WALL)
        self.game.bomb.active = True
        self.game.bomb.gx = 1
        self.game.bomb.gy = 2
        self.game.bomb.range = 2
        self.game.player_x = 1.0
        self.game.player_y = 1.0

        self.game.bomb.timer = 0.01
        self.game.update(0.02, 0, 0)

        # 验证烈焰没有穿透硬墙到达 (3, 2)
        flame_coords = [(f.x, f.y) for f in self.game.flames]
        self.assertNotIn((3, 2), flame_coords)

    def test_self_damage_from_own_bomb(self):
        """测试自身未规避烈焰自爆损命"""
        self.assertEqual(self.game.lives, 3)
        self.game.player_x = 1.0
        self.game.player_y = 1.0
        self.game.update(0.02, 0, KEY_A)

        # 玩家不逃跑原地等死
        self.game.bomb.timer = 0.01
        self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.player_x, 1.0)
        self.assertEqual(self.game.player_y, 1.0)

    def test_flame_kills_enemy_and_scores(self):
        """测试烈焰消灭敌怪获100分"""
        self.assertEqual(self.game.remaining_enemies, 2)
        # 将敌怪 0 放置在 (4, 1)
        self.game.enemies[0].x = 4.0
        self.game.enemies[0].y = 1.0
        self.game.map[1][3] = TILE_EMPTY
        self.game.map[1][4] = TILE_EMPTY

        # 在 (2, 1) 埋雷，射程 2 (覆盖 3,1 与 4,1)
        self.game.bomb.active = True
        self.game.bomb.gx = 2
        self.game.bomb.gy = 1
        self.game.bomb.range = 2

        # 玩家避难在拐角 (1, 2)
        self.game.player_x = 1.0
        self.game.player_y = 2.0

        initial_score = self.game.score
        self.game.bomb.timer = 0.01
        self.game.update(0.02, 0, 0)

        self.assertFalse(self.game.enemies[0].alive)
        self.assertEqual(self.game.remaining_enemies, 1)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_enemy_touches_player_kills_player(self):
        """测试巡逻怪触碰玩家扣命"""
        self.assertEqual(self.game.lives, 3)
        self.game.enemies[0].x = self.game.player_x
        self.game.enemies[0].y = self.game.player_y

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.lives, 2)

    def test_victory_on_all_enemies_defeated(self):
        """测试消灭全图敌怪通关"""
        self.game.remaining_enemies = 1
        self.game.enemies[1].alive = False

        # 烈焰炸死最后一只敌怪在 (3, 1)
        self.game.enemies[0].x = 3.0
        self.game.enemies[0].y = 1.0
        self.game.map[1][3] = TILE_EMPTY

        self.game.bomb.active = True
        self.game.bomb.gx = 2
        self.game.bomb.gy = 1
        self.game.bomb.range = 2
        self.game.player_x = 1.0
        self.game.player_y = 2.0

        self.game.bomb.timer = 0.01
        self.game.update(0.02, 0, 0)

        self.assertEqual(self.game.remaining_enemies, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
