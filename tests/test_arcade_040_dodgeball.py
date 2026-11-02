import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_040_dodgeball import (
    Game040Dodgeball,
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


class TestGame040Dodgeball(unittest.TestCase):
    def setUp(self):
        self.game = Game040Dodgeball()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(40)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "热血躲避球")
        self.assertEqual(instance.english_name, "Super Dodge Ball 1987")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1987)

    def test_court_division_and_player_clamping(self):
        """测试中线分割球场与玩家半场活动限制"""
        self.assertEqual(self.game.player["x"], 4.0)
        self.assertEqual(self.game.player["hp"], 3)
        self.assertEqual(self.game.enemy["hp"], 3)
        self.assertTrue(self.game.ball["state"] == 1) # 玩家初始持球

        # 尝试越过中线向右突破
        self.game.player["x"] = 6.9
        for _ in range(10):
            self.game.update(0.05, KEY_RIGHT, 0)
        # 无法越过中线 (x <= 7.0)
        self.assertLessEqual(self.game.player["x"], 7.0)

    def test_normal_ball_throw(self):
        """测试按键 A 轻点释放普通直球掷投"""
        self.assertEqual(self.game.ball["state"], 1)

        # 轻点 A 投球
        self.game.update(0.05, KEY_A, 0)
        self.game.update(0.05, 0, KEY_A) # 释放按键

        # 球已脱手飞出
        self.assertEqual(self.game.ball["state"], 3)
        self.assertFalse(self.game.ball["is_super"])
        self.assertGreater(self.game.ball["vx"], 0.0) # 向敌方半场疾飞

    def test_super_killer_shot_charging(self):
        """测试按住 A 键蓄力超过 0.5 秒释放超级魔球 (Super Shot)"""
        self.assertEqual(self.game.ball["state"], 1)

        # 蓄力按住 A 键 0.6 秒
        for _ in range(12):
            self.game.update(0.05, KEY_A, 0)

        # 释放 A 键触发暴扣
        self.game.update(0.05, 0, KEY_A)

        self.assertEqual(self.game.ball["state"], 3)
        self.assertTrue(self.game.ball["is_super"]) # 超级必杀魔球
        self.assertGreater(self.game.ball["vx"], 15.0) # 超音速球速

    def test_active_ball_catch_from_mid_air(self):
        """测试迎击敌方来球瞬间按下 B 键空手极限抓球 (Catch)"""
        # 敌方掷球飞向玩家
        self.game.ball["state"] = 4
        self.game.ball["x"] = 5.0
        self.game.ball["y"] = 8.0
        self.game.ball["vx"] = -10.0
        self.game.ball["vy"] = 0.0

        self.game.player["x"] = 4.2
        self.game.player["y"] = 8.0

        initial_score = self.game.score
        # 玩家看准球路按键 B 接球
        self.game.update(0.05, KEY_B, 0)

        self.assertEqual(self.game.ball["state"], 1) # 截获并重新持球
        self.assertEqual(self.game.player["hp"], 3)  # 未受任何伤害
        self.assertEqual(self.game.score, initial_score + 100) # 截球奖励

    def test_normal_ball_hits_enemy_one_damage(self):
        """测试普通掷球命中敌方扣除 1 点体力"""
        self.game.enemy["hp"] = 3
        self.game.ball["state"] = 3
        self.game.ball["is_super"] = False
        self.game.ball["x"] = 10.5
        self.game.ball["y"] = 8.0
        self.game.ball["vx"] = 10.0
        self.game.ball["vy"] = 0.0

        self.game.enemy["x"] = 11.0
        self.game.enemy["y"] = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.enemy["hp"], 2) # 扣除 1 点血
        self.assertEqual(self.game.ball["state"], 0) # 球掉落变自由球

    def test_super_killer_shot_deals_double_damage(self):
        """测试超级魔球必杀技造成 2 点致命重创"""
        self.game.enemy["hp"] = 3
        self.game.ball["state"] = 3
        self.game.ball["is_super"] = True
        self.game.ball["x"] = 10.5
        self.game.ball["y"] = 8.0
        self.game.ball["vx"] = 18.0
        self.game.ball["vy"] = 0.0

        self.game.enemy["x"] = 11.0
        self.game.enemy["y"] = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.enemy["hp"], 1) # 造成 2 点暴击伤害

    def test_enemy_knockout_triggers_victory(self):
        """测试敌方体力清零达成比赛胜利"""
        self.game.enemy["hp"] = 1
        self.game.ball["state"] = 3
        self.game.ball["x"] = 10.5
        self.game.ball["y"] = 8.0
        self.game.enemy["x"] = 11.0
        self.game.enemy["y"] = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.enemy["hp"], 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000)

    def test_player_hit_and_death(self):
        """测试玩家被敌球砸中扣血并在体力清零时阵亡"""
        self.game.player["hp"] = 1
        self.game.ball["state"] = 4 # 敌方来球
        self.game.ball["x"] = 4.5
        self.game.ball["y"] = 8.0
        self.game.player["x"] = 4.0
        self.game.player["y"] = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.player["hp"], 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区木地板球场、中线与双方体力着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查硬木地板 (x=5, y=5 橙木色 [211, 84, 0])
        floor_idx = (5 * 16 + 5) * 3
        self.assertEqual(fb[floor_idx], 211)
        self.assertEqual(fb[floor_idx + 1], 84)
        self.assertEqual(fb[floor_idx + 2], 0)

        # 检查白色中线 (x=7, y=5 白色 [245, 245, 245])
        mid_idx = (5 * 16 + 7) * 3
        self.assertEqual(fb[mid_idx], 245)
        self.assertEqual(fb[mid_idx + 1], 245)
        self.assertEqual(fb[mid_idx + 2], 245)


if __name__ == "__main__":
    unittest.main()
