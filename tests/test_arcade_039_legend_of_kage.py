import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_039_legend_of_kage import (
    Game039LegendOfKage,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame039LegendOfKage(unittest.TestCase):
    def setUp(self):
        self.game = Game039LegendOfKage()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(39)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "影子传说")
        self.assertEqual(instance.english_name, "Legend of Kage 1985")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1985)

    def test_forest_layout_and_branches(self):
        """测试密林地表、树干与三层树冠枝条平台"""
        # 地表 (Row 14..15) 为 3
        self.assertEqual(self.game.tree_map[14][5], 3)
        # 树干 (x=8, y=5) 为 1
        self.assertEqual(self.game.tree_map[5][8], 1)
        # 树冠平台 (y=6, x=7..9) 为 2 (可站立)
        self.assertEqual(self.game.tree_map[6][7], 2)
        self.assertEqual(self.game.tree_map[6][8], 2)
        self.assertEqual(self.game.tree_map[6][9], 2)

    def test_ninja_super_leap_physics(self):
        """测试影忍轻功超级纵跃腾空高跳"""
        self.game.player_x = 5.5 # 在林间空隙起跳
        self.game.player_y = 13.0
        self.assertTrue(self.game.is_grounded)

        # 按键 UP 向上轻功大跳
        self.game.update(0.05, KEY_UP, 0)
        self.assertFalse(self.game.is_grounded)
        self.assertLess(self.game.player_vy, 0.0) # 向上高速弹射

        # 跃上树梢
        for _ in range(8):
            self.game.update(0.05, 0, 0)
        self.assertLess(self.game.player_y, 10.0)

    def test_landing_on_branch_platform(self):
        """测试在下落过程中平稳着陆在树冠树枝平台上"""
        # 将玩家放置在 y=5 (正在朝 y=6 的树枝平台下落)
        self.game.player_x = 8.0
        self.game.player_y = 5.0
        self.game.player_vy = 3.0
        self.game.is_grounded = False

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.is_grounded)
        self.assertEqual(self.game.player_y, 5.0) # 稳定站立在 y=6 平台上

    def test_shuriken_throwing_mechanics(self):
        """测试按键 A 远投手里剑飞镖"""
        self.assertEqual(len(self.game.shurikens), 0)
        self.game.player_facing = 1 # 朝右

        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.shurikens), 1)
        s = self.game.shurikens[0]
        self.assertGreater(s["vx"], 0.0) # 向右飞行

    def test_shuriken_kills_enemy_ninja(self):
        """测试手里剑远程射中敌方忍者并击坠"""
        self.game.enemies[0]["x"] = 10.0
        self.game.enemies[0]["y"] = 13.0
        self.game.enemies[0]["is_red"] = False

        self.game.shurikens.append({
            "active": True,
            "x": 9.5,
            "y": 13.0,
            "vx": 14.0,
            "vy": 0.0,
        })

        initial_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.enemies_defeated, 1)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_kodachi_sword_slash_melee_kill(self):
        """测试短刀近战劈刺击杀贴身敌忍"""
        self.game.enemies[0]["x"] = 8.8
        self.game.enemies[0]["y"] = 13.0
        self.game.player_x = 8.0
        self.game.player_y = 13.0

        # 按键 B 挥刀近战
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.is_slashing())
        self.assertEqual(self.game.enemies_defeated, 1)
        self.assertEqual(self.game.score, 200)

    def test_kodachi_sword_parries_incoming_projectile(self):
        """测试短刀瞬间挥击弹刀破镖 (Deflect / Parry) 敌方暗器并获得招架奖励"""
        self.game.player_x = 8.0
        self.game.player_y = 13.0

        # 飞向玩家的敌方暗器
        self.game.enemy_bullets.append({
            "active": True,
            "x": 8.8,
            "y": 13.0,
            "vx": -7.0,
            "vy": 0.0,
        })

        initial_score = self.game.score
        # 玩家看准时机按键 B 挥刀格挡招架
        self.game.update(0.05, KEY_B, 0)

        self.assertEqual(len(self.game.enemy_bullets), 0) # 飞镖被刀光斩落
        self.assertEqual(self.game.score, initial_score + 50) # 招架奖励
        self.assertEqual(self.game.lives, 3) # 未受伤害

    def test_ten_kills_stage_clear_victory(self):
        """测试击杀 10 名敌方忍者完成树海密林救援通关"""
        self.game.enemies_defeated = 9
        self.game.enemies[0]["x"] = 8.8
        self.game.enemies[0]["y"] = 13.0
        self.game.player_x = 8.0
        self.game.player_y = 13.0

        self.game.update(0.05, KEY_B, 0) # 斩杀第 10 名
        self.assertEqual(self.game.enemies_defeated, 10)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区翡翠林海、树干、树枝与刀光着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查树干着色 (x=8, y=8 棕木色 [100, 60, 30])
        trunk_idx = (8 * 16 + 8) * 3
        self.assertEqual(fb[trunk_idx], 100)
        self.assertEqual(fb[trunk_idx + 1], 60)
        self.assertEqual(fb[trunk_idx + 2], 30)


if __name__ == "__main__":
    unittest.main()
