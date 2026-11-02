# -*- coding: utf-8 -*-
"""
test_arcade_027_magic_tower.py —— 经典魔塔 1996 完整单元测试
验证零随机精密数值战斗、黄蓝钥匙门禁决策、红蓝宝石攻防强化、无法破防避战保护与通关
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_027_magic_tower import (
    Game027MagicTower,
    TOWER_FLOOR,
    TOWER_WALL,
    TOWER_DOOR_YELLOW,
    TOWER_DOOR_BLUE,
    TOWER_KEY_YELLOW,
    TOWER_KEY_BLUE,
    TOWER_GEM_RED,
    TOWER_GEM_BLUE,
    TOWER_POTION_RED,
    TOWER_POTION_BLUE,
    TOWER_MONSTER_SLIME,
    TOWER_MONSTER_SKELETON,
    TOWER_MONSTER_MAGE,
    TOWER_MONSTER_BOSS,
    TOWER_STAIRS,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    STATE_PLAYING,
    STATE_VICTORY,
    CTRL_DPAD_4WAY,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame027MagicTower(unittest.TestCase):
    def setUp(self):
        self.game = Game027MagicTower()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与中央注册中心集成"""
        self.assertEqual(self.game.game_id, 27)
        self.assertEqual(self.game.name, "经典魔塔")
        self.assertEqual(self.game.english_name, "Magic Tower 1996")
        self.assertEqual(self.game.release_year, 1996)
        self.assertEqual(self.game.control_type, CTRL_DPAD_4WAY)
        self.assertIn("零随机精密数值战斗", self.game.core_mechanic)

        cart = ArcadeRegistry.get_cartridge(27)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "经典魔塔")

    def test_initial_hero_stats(self):
        """测试勇士初始属性与资源"""
        self.assertEqual(self.game.hero_x, 1)
        self.assertEqual(self.game.hero_y, 14)
        self.assertEqual(self.game.hero_hp, 1000)
        self.assertEqual(self.game.hero_atk, 25)
        self.assertEqual(self.game.hero_def, 10)
        self.assertEqual(self.game.yellow_keys, 1)
        self.assertEqual(self.game.blue_keys, 0)

    def test_deterministic_damage_formula(self):
        """测试零随机绝对确定性战损计算公式"""
        # 勇士 ATK=25, DEF=10
        # 绿史莱姆: HP=50, ATK=20, DEF=1
        # 勇士每击伤害 = 25 - 1 = 24; 回合数 = ceil(50 / 24) = 3 轮
        # 史莱姆每击反击 = 20 - 10 = 10; 承受反击 = (3 - 1) * 10 = 20 点伤害
        dmg = self.game.calculate_damage(TOWER_MONSTER_SLIME)
        self.assertEqual(dmg, 20)

        # 骷髅兵: HP=110, ATK=35, DEF=5
        # 勇士每击 = 25 - 5 = 20; 回合数 = ceil(110 / 20) = 6 轮
        # 骷髅反击 = 35 - 10 = 25; 承受反击 = (6 - 1) * 25 = 125 点伤害
        dmg_skel = self.game.calculate_damage(TOWER_MONSTER_SKELETON)
        self.assertEqual(dmg_skel, 125)

    def test_gem_and_potion_buffs(self):
        """测试拾取红蓝宝石与血瓶属性增益"""
        # 拾取红宝石 (+3 ATK)
        self.game.grid[14][2] = TOWER_GEM_RED
        self.game.interact(2, 14)
        self.assertEqual(self.game.hero_atk, 28)

        # 拾取蓝宝石 (+3 DEF)
        self.game.grid[14][3] = TOWER_GEM_BLUE
        self.game.interact(3, 14)
        self.assertEqual(self.game.hero_def, 13)

        # 拾取红血瓶 (+200 HP)
        init_hp = self.game.hero_hp
        self.game.grid[14][4] = TOWER_POTION_RED
        self.game.interact(4, 14)
        self.assertEqual(self.game.hero_hp, init_hp + 200)

        # 拾取蓝血瓶 (+500 HP)
        self.game.grid[14][5] = TOWER_POTION_BLUE
        self.game.interact(5, 14)
        self.assertEqual(self.game.hero_hp, init_hp + 700)

    def test_key_pickup_and_door_unlocking(self):
        """测试钥匙收集与门禁开启"""
        self.assertEqual(self.game.yellow_keys, 1)
        self.assertEqual(self.game.blue_keys, 0)

        # 拾取黄钥匙
        self.game.grid[14][2] = TOWER_KEY_YELLOW
        self.game.interact(2, 14)
        self.assertEqual(self.game.yellow_keys, 2)

        # 开启黄门
        self.game.grid[14][3] = TOWER_DOOR_YELLOW
        success = self.game.interact(3, 14)
        self.assertTrue(success)
        self.assertEqual(self.game.yellow_keys, 1)

        # 无蓝钥匙时无法开启蓝门
        self.game.grid[14][4] = TOWER_DOOR_BLUE
        fail = self.game.interact(4, 14)
        self.assertFalse(fail)
        self.assertEqual(self.game.hero_x, 3) # 未能进入

        # 拾取蓝钥匙后成功开启
        self.game.grid[13][3] = TOWER_KEY_BLUE
        self.game.interact(3, 13)
        self.assertEqual(self.game.blue_keys, 1)

        success_blue = self.game.interact(4, 14)
        self.assertTrue(success_blue)
        self.assertEqual(self.game.blue_keys, 0)

    def test_combat_and_damage_deduction(self):
        """测试与怪物交战精确扣减生命与获得金币"""
        init_hp = self.game.hero_hp
        self.game.grid[14][2] = TOWER_MONSTER_SLIME
        expected_dmg = self.game.calculate_damage(TOWER_MONSTER_SLIME)

        self.game.interact(2, 14)
        self.assertEqual(self.game.hero_hp, init_hp - expected_dmg)
        self.assertEqual(self.game.grid[14][2], TOWER_FLOOR)
        self.assertEqual(self.game.score, 10)

    def test_insufficient_stats_blocks_combat(self):
        """测试无法破防或战损超过当前生命时自动避战保护"""
        # 削弱勇士攻击力低于魔王防御力 (魔王 DEF=20)
        self.game.hero_atk = 15
        self.game.grid[14][2] = TOWER_MONSTER_BOSS

        # 尝试走入魔王格子被坚决阻拦
        blocked = self.game.interact(2, 14)
        self.assertFalse(blocked)
        self.assertEqual(self.game.hero_x, 1) # 未踏入

        # 攻击力达标但生命值极低 (HP=10 < 战损)
        self.game.hero_atk = 30
        self.game.hero_hp = 10
        blocked2 = self.game.interact(2, 14)
        self.assertFalse(blocked2)

    def test_wall_collision_blocks_movement(self):
        """测试墙壁阻挡移动"""
        self.game.grid[14][2] = TOWER_WALL
        blocked = self.game.interact(2, 14)
        self.assertFalse(blocked)
        self.assertEqual(self.game.hero_x, 1)

    def test_boss_defeat_and_stairs_victory(self):
        """测试讨伐魔王并登梯获得通关胜利"""
        # 满级神装勇士
        self.game.hero_atk = 100
        self.game.hero_def = 80
        self.game.hero_hp = 3000

        self.game.grid[1][13] = TOWER_MONSTER_BOSS
        self.game.hero_x = 1
        self.game.hero_y = 12

        # 斩杀魔王
        self.game.interact(13, 1)
        self.assertEqual(self.game.grid[1][13], TOWER_FLOOR)

        # 登上楼梯 (14, 1)
        self.game.interact(14, 1)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer(self):
        """测试 16x16 RGB888 显存帧渲染输出"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 勇士金光 [255, 215, 0]
        hx = self.game.hero_x
        hy = self.game.hero_y
        hidx = (hy * 16 + hx) * 3
        self.assertEqual(fb[hidx + 0], 255)
        self.assertEqual(fb[hidx + 1], 215)
        self.assertEqual(fb[hidx + 2], 0)

        # 通关楼梯纯白 [255, 255, 255]
        sidx = (1 * 16 + 14) * 3
        self.assertEqual(fb[sidx + 0], 255)
        self.assertEqual(fb[sidx + 1], 255)
        self.assertEqual(fb[sidx + 2], 255)

    def test_status_reporting(self):
        """测试状态字典属性导出与进度计算"""
        st = self.game.get_status()
        self.assertEqual(st["hp"], 1000)
        self.assertEqual(st["atk"], 25)
        self.assertEqual(st["def"], 10)
        self.assertEqual(st["yellow_keys"], 1)
        self.assertEqual(st["blue_keys"], 0)
        self.assertEqual(st["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
