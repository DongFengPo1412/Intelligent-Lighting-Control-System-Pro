# -*- coding: utf-8 -*-
"""
test_arcade_021_dig_dug.py —— 掘地打气人 1982 完整单元测试
验证地底隧道自由挖掘、鱼叉穿刺充气爆裂、巨石震颤下坠碾压、飞加喷火伤害与怪物全灭通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_021_dig_dug import (
    Game021DigDug,
    TILE_EMPTY,
    TILE_DIRT,
    TILE_ROCK,
    ENEMY_POOKA,
    ENEMY_FYGAR,
)
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


class TestGame021DigDug(unittest.TestCase):
    def setUp(self):
        self.game = Game021DigDug()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 21)
        self.assertEqual(self.game.name, "掘地打气人")
        self.assertEqual(self.game.english_name, "Dig Dug 1982")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("隧道挖掘", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(21)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "掘地打气人")

    def test_initial_level_layout(self):
        """测试初始关卡布局: 蓝天、地底泥土、小室与巨石"""
        for x in range(16):
            self.assertEqual(self.game.grid[0][x], TILE_EMPTY) # 地表

        # 玩家出生小室位于 (7, 7)
        self.assertEqual(self.game.player_x, 7)
        self.assertEqual(self.game.player_y, 7)
        self.assertEqual(self.game.grid[7][7], TILE_EMPTY)

        # 验证巨石分布
        self.assertEqual(len(self.game.rocks), 2)
        self.assertEqual(self.game.grid[2][4], TILE_ROCK)
        self.assertEqual(self.game.grid[8][12], TILE_ROCK)

        # 验证 4 只怪物
        self.assertEqual(len(self.game.enemies), 4)
        alive_count = sum(1 for e in self.game.enemies if e["active"])
        self.assertEqual(alive_count, 4)

    def test_digging_mechanic_and_scoring(self):
        """测试在地层中挖掘移动: 泥土变为隧道，获得挖掘积分"""
        # (7, 8) 是初始空室，(7, 9) 是泥土
        self.game.grid[7][8] = TILE_EMPTY
        self.game.grid[7][9] = TILE_DIRT
        self.game.player_x = 8
        self.game.player_y = 7
        self.assertEqual(self.game.score, 0)

        # 向右走掘开 (7, 9)
        self.game.move_timer = 0.2
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_x, 9)
        self.assertEqual(self.game.player_y, 7)
        self.assertEqual(self.game.grid[7][9], TILE_EMPTY)
        self.assertEqual(self.game.score, 10)

    def test_harpoon_pump_inflate_and_pop(self):
        """测试鱼叉刺中怪物并连续打气直到膨胀引爆"""
        # 将怪物 0 放置在玩家正右方 1 格空道中
        self.game.player_x = 6
        self.game.player_y = 6
        self.game.player_dir = 1 # 向右
        self.game.grid[6][6] = TILE_EMPTY
        self.game.grid[6][7] = TILE_EMPTY

        target = self.game.enemies[0]
        target["x"] = 7.0
        target["y"] = 6.0
        target["active"] = True
        target["inflate_stage"] = 0

        # 按 A 发射鱼叉刺入
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertTrue(self.game.harpoon["active"])
        self.assertEqual(self.game.harpoon["target_idx"], 0)
        self.assertEqual(target["inflate_stage"], 1)

        # 再次按 A 打气第 2 级
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertEqual(target["inflate_stage"], 2)

        # 第三次按 A 引爆破裂！
        self.game.update(0.05, KEY_A, KEY_A)
        self.assertFalse(target["active"]) # 怪物爆裂死亡
        self.assertFalse(self.game.harpoon["active"])
        self.assertEqual(self.game.score, 200)

    def test_enemy_deflation_when_idle(self):
        """测试停止打气后怪物漏气降级机制"""
        target = self.game.enemies[0]
        target["inflate_stage"] = 2
        target["inflate_timer"] = 0.1
        self.game.harpoon["active"] = True
        self.game.harpoon["target_idx"] = 0

        # 不打气静置一段时间 (由于 dt 限制最大 0.05s，需循环推进时间)
        for _ in range(4):
            self.game.update(0.05, 0, 0)
        self.assertEqual(target["inflate_stage"], 1)

    def test_boulder_trigger_and_squashing_monsters(self):
        """测试巨石下方被挖空后震颤下坠并碾压怪物"""
        rock = self.game.rocks[0]
        rx = rock["x"]
        ry = rock["y"] # 2
        # 挖空巨石正下方 (rx, ry+1) = (4, 3)
        self.game.grid[ry + 1][rx] = TILE_EMPTY
        self.game.grid[ry + 2][rx] = TILE_EMPTY

        # 在 (4, 4) 放置一只波卡怪物，设定负计时防止走开
        target = self.game.enemies[0]
        target["x"] = float(rx)
        target["y"] = float(ry + 2)
        target["active"] = True
        target["move_timer"] = -100.0

        # 巨石震颤
        for _ in range(16):
            self.game.update(0.05, 0, 0)
        self.assertTrue(rock["falling"])

        # 巨石下坠砸下
        for _ in range(10):
            self.game.update(0.05, 0, 0)

        # 怪物被砸死并奖励 500 分
        self.assertFalse(target["active"])
        self.assertGreaterEqual(self.game.score, 500)

    def test_fygar_fire_breath_burns_player(self):
        """测试飞加喷吐烈焰灼伤玩家"""
        self.assertEqual(self.game.player_lives, 3)
        fygar = self.game.enemies[1]
        fygar["x"] = 6.0
        fygar["y"] = 7.0
        fygar["dir"] = 1 # 向右喷火
        fygar["active"] = True

        self.game.player_x = 7 # 正好在飞加喷火右方 1 格
        self.game.player_y = 7
        self.game.grid[7][6] = TILE_EMPTY
        self.game.grid[7][7] = TILE_EMPTY

        # 触发飞加喷火
        fygar["firing"] = True
        fygar["fire_timer"] = 0.5
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.player_lives, 2)

    def test_monster_collision_kills_player(self):
        """测试怪物直接碰撞使玩家损命，并在命尽时判定 GAMEOVER"""
        self.game.player_lives = 1
        self.game.player_x = 5
        self.game.player_y = 5

        # 怪物直接步入玩家所在格
        pooka = self.game.enemies[0]
        pooka["active"] = True
        pooka["x"] = 5.0
        pooka["y"] = 5.0
        pooka["inflate_stage"] = 0
        pooka["move_timer"] = 0.3

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.player_lives, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_victory_on_all_monsters_eliminated(self):
        """测试清空关卡所有怪物后触发通关胜利"""
        for enemy in self.game.enemies:
            enemy["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 完整显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 验证天蓝色 (0, 0) = [52, 152, 219]
        self.assertEqual(fb[0], 52)
        self.assertEqual(fb[1], 152)
        self.assertEqual(fb[2], 219)

        # 验证玩家白色 [255, 255, 255]
        px = self.game.player_x
        py = self.game.player_y
        pidx = (py * 16 + px) * 3
        self.assertEqual(fb[pidx + 0], 255)
        self.assertEqual(fb[pidx + 1], 255)
        self.assertEqual(fb[pidx + 2], 255)

    def test_status_reporting(self):
        """测试状态字典与击杀进度报告"""
        st = self.game.get_status()
        self.assertEqual(st["lives"], 3)
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)
        self.assertEqual(st["progress"], 0)

        # 击杀 2 只怪物
        self.game.enemies[0]["active"] = False
        self.game.enemies[1]["active"] = False
        st = self.game.get_status()
        self.assertEqual(st["progress"], 50)


if __name__ == "__main__":
    unittest.main()
