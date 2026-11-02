import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_033_clay_shooting import (
    Game033ClayShooting,
    STATE_START,
    STATE_LAUNCHING,
    STATE_ROUND_CLEAR,
    STATE_GAMEOVER,
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


class TestGame033ClayShooting(unittest.TestCase):
    def setUp(self):
        self.game = Game033ClayShooting()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(33)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "经典打飞碟")
        self.assertEqual(instance.english_name, "Clay Shooting 1978")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1978)

    def test_double_trap_launch_mechanics(self):
        """测试双向抛靶机械发射与初速度"""
        self.assertEqual(len(self.game.clays), 2)
        c0 = self.game.clays[0]
        c1 = self.game.clays[1]

        self.assertTrue(c0["active"])
        self.assertTrue(c1["active"])
        self.assertLess(c0["vy"], 0.0) # 向上抛射
        self.assertLess(c1["vy"], 0.0)
        self.assertGreater(c0["vx"], 0.0) # 从左向右漂移
        self.assertLess(c1["vx"], 0.0)    # 从右向左漂移
        self.assertEqual(self.game.ammo, 2)

    def test_parabolic_trajectory_and_gravity(self):
        """测试飞碟抛物线重力衰减与下落"""
        c0 = self.game.clays[0]
        initial_vy = c0["vy"]

        # 推进 0.1 秒
        self.game.update(0.1, 0, 0)
        self.assertGreater(c0["vy"], initial_vy) # 重力加速度使向上速度变小或向下速度增加

    def test_crosshair_four_way_gliding_and_clamp(self):
        """测试准星四向滑移与屏幕边界限制"""
        self.game.crosshair_x = 7.5
        self.game.crosshair_y = 7.5

        # 向左滑移
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.crosshair_x, 7.5)

        # 移动到极左
        for _ in range(20):
            self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.crosshair_x, 0.5)

    def test_shotgun_trigger_and_ammo_decrement(self):
        """测试猎枪扣动扳机、弹药消耗与枪口火光"""
        self.assertEqual(self.game.ammo, 2)
        self.game.crosshair_x = 0.0
        self.game.crosshair_y = 0.0 # 移开准星不命中

        # 开枪
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.ammo, 1)
        self.assertGreater(self.game.muzzle_flash, 0.0)

        # 释放按键再开一枪
        self.game.update(0.05, 0, KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.ammo, 0)

        # 弹药耗尽无法开火
        self.game.update(0.05, 0, KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.ammo, 0)

    def test_single_clay_shattered_by_direct_hit(self):
        """测试准星精准引前量命中飞碟并使其碎裂爆破"""
        clay = self.game.clays[0]
        clay["x"] = 6.0
        clay["y"] = 4.0
        clay["vx"] = 0.0
        clay["vy"] = 0.0
        self.game.crosshair_x = 6.0
        self.game.crosshair_y = 4.0

        # 开枪
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(clay["shattered"])
        self.assertEqual(self.game.total_hits, 1)
        self.assertEqual(self.game.score, 100) # 顶点高空命中得分

    def test_double_trap_perfect_double_bonus(self):
        """测试单轮两发两中达成双中大满贯奖励 (Double Trap Bonus)"""
        # 第一靶
        self.game.clays[0]["x"] = 4.0
        self.game.clays[0]["y"] = 6.0
        self.game.clays[0]["vx"] = 0.0
        self.game.clays[0]["vy"] = 0.0
        self.game.crosshair_x = 4.0
        self.game.crosshair_y = 6.0
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.clays[0]["shattered"])

        # 第二靶
        self.game.clays[1]["x"] = 10.0
        self.game.clays[1]["y"] = 7.0
        self.game.clays[1]["vx"] = 0.0
        self.game.clays[1]["vy"] = 0.0
        self.game.crosshair_x = 10.0
        self.game.crosshair_y = 7.0
        self.game.update(0.05, 0, KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.clays[1]["shattered"])

        self.assertEqual(self.game.round_hits, 2)
        # 50 + 50 + 200 (Double Bonus) = 300
        self.assertEqual(self.game.score, 300)

    def test_round_progression_to_round_clear(self):
        """测试飞碟全部碎裂后回合结算并进入下一轮"""
        for clay in self.game.clays:
            clay["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)

    def test_five_rounds_completion_gameover(self):
        """测试打满 5 轮完成整场锦标赛比赛"""
        self.game.current_round = 5
        self.game.state = STATE_ROUND_CLEAR
        self.game.state_timer = 1.3

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区天际线与准星着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查天空蓝 #3498DB [52, 152, 219]
        sky_idx = (2 * 16 + 2) * 3
        self.assertEqual(fb[sky_idx], 52)
        self.assertEqual(fb[sky_idx + 1], 152)
        self.assertEqual(fb[sky_idx + 2], 219)

        # 检查草地绿 #27AE60 [39, 174, 96]
        grass_idx = (14 * 16 + 5) * 3
        self.assertEqual(fb[grass_idx], 39)
        self.assertEqual(fb[grass_idx + 1], 174)
        self.assertEqual(fb[grass_idx + 2], 96)


if __name__ == "__main__":
    unittest.main()
