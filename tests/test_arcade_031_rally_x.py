import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_031_rally_x import (
    Game031RallyX,
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


class TestGame031RallyX(unittest.TestCase):
    def setUp(self):
        self.game = Game031RallyX()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(31)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "像素拉力赛车")
        self.assertEqual(instance.english_name, "Rally-X 1980")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1980)

    def test_maze_walls_and_rocks_initialization(self):
        """测试迷宫边界与内部岩石障碍物初始化"""
        # 边界为墙体
        self.assertTrue(self.game.is_wall_or_rock(0, 5))
        self.assertTrue(self.game.is_wall_or_rock(15, 5))
        self.assertTrue(self.game.is_wall_or_rock(5, 1))
        self.assertTrue(self.game.is_wall_or_rock(5, 15))

        # 内部岩石障碍
        self.assertTrue(self.game.is_wall_or_rock(3, 3))
        self.assertTrue(self.game.is_wall_or_rock(7, 7))

        # 内部主干道应为畅通
        self.assertFalse(self.game.is_wall_or_rock(7, 13))
        self.assertFalse(self.game.is_wall_or_rock(2, 4))

    def test_player_four_way_steering_and_wall_blocking(self):
        """测试玩家赛车四向转向与岩石碰撞阻挡"""
        self.game.player_x = 7.0
        self.game.player_y = 13.0
        self.game.player_dir = 0 # 向上

        # 向上行驶
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.player_y, 13.0)

        # 试图冲撞左侧外墙
        self.game.player_x = 1.0
        self.game.player_y = 5.0
        self.game.player_dir = 3 # 向左
        self.game.next_dir = 3
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.player_x, 1.0) # 无法穿墙

    def test_fuel_consumption_and_low_fuel_speed(self):
        """测试燃油自然消耗与耗尽减速"""
        self.game.fuel = 10.0
        self.game.update(1.0, 0, 0)
        self.assertLess(self.game.fuel, 10.0)

        # 燃油耗尽
        self.game.fuel = 0.0
        self.game.player_x = 7.0
        self.game.player_y = 13.0
        self.game.player_dir = 0 # 向上
        self.game.update(0.1, KEY_UP, 0)
        # 减速状态下单步位移显著小于满油状态
        out_fuel_dy = 13.0 - self.game.player_y

        self.game.fuel = 100.0
        self.game.player_x = 7.0
        self.game.player_y = 13.0
        self.game.update(0.1, KEY_UP, 0)
        full_fuel_dy = 13.0 - self.game.player_y
        self.assertGreater(full_fuel_dy, out_fuel_dy)

    def test_smoke_screen_deployment_and_fuel_cost(self):
        """测试尾部喷射烟幕、燃油扣除与冷却机制"""
        self.game.fuel = 50.0
        self.game.smoke_cooldown = 0.0
        self.game.smokes.clear()
        self.game.player_x = 7.0
        self.game.player_y = 8.0
        self.game.player_dir = 0 # 向上开

        # 按下按键 A 释放烟幕
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.smokes), 1)
        # 50.0 - 6.0 (烟幕) - 0.075 (时间消耗) = 43.925
        self.assertAlmostEqual(self.game.fuel, 43.925, places=2)
        self.assertGreater(self.game.smoke_cooldown, 0.0)

        smoke = self.game.smokes[0]
        self.assertEqual(smoke["x"], 7)
        self.assertEqual(smoke["y"], 9) # 向上开时，尾部在下方 (y + 1)

    def test_smoke_stuns_chasing_red_car(self):
        """测试敌方追击红车进入烟幕导致失控眩晕旋转 (Spinout)"""
        self.game.enemies[0]["x"] = 5.0
        self.game.enemies[0]["y"] = 6.0
        self.game.enemies[0]["stun_timer"] = 0.0

        # 在红车前方放置烟雾
        self.game.smokes.append({
            "x": 5,
            "y": 6,
            "timer": 3.0,
            "active": True
        })

        initial_score = self.game.score
        self.game.update(0.05, 0, 0)

        # 红车应被眩晕
        self.assertGreater(self.game.enemies[0]["stun_timer"], 2.0)
        self.assertEqual(self.game.score, initial_score + 100) # 击晕得分

    def test_flag_pickup_and_lucky_flag_bonus(self):
        """测试军旗收集与特殊幸运旗双倍燃油结算奖励"""
        self.game.flags = [
            {"x": 7, "y": 12, "collected": False, "is_special": False},
            {"x": 7, "y": 10, "collected": False, "is_special": True},
        ]
        self.game.player_x = 7.0
        self.game.player_y = 12.0
        self.game.fuel = 60.0

        # 吃普通旗帜
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.flags[0]["collected"])
        self.assertEqual(self.game.score, 100)

        # 移动并吃特殊幸运旗帜
        self.game.player_y = 10.0
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.flags[1]["collected"])
        # 400 + int(fuel) * 5
        self.assertGreater(self.game.score, 500)

    def test_chasing_red_car_hits_player_death(self):
        """测试未被眩晕的敌车撞击玩家导致扣命"""
        self.game.lives = 3
        self.game.player_x = 7.0
        self.game.player_y = 7.0
        self.game.enemies[0]["x"] = 7.0
        self.game.enemies[0]["y"] = 7.2
        self.game.enemies[0]["stun_timer"] = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_collect_all_flags_triggers_victory(self):
        """测试收集齐所有军旗达成关卡胜利"""
        for flag in self.game.flags:
            flag["collected"] = True
        # 仅留最后一面
        self.game.flags[0]["collected"] = False
        self.game.flags[0]["x"] = 7
        self.game.flags[0]["y"] = 12

        self.game.player_x = 7.0
        self.game.player_y = 12.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000) # 通关大奖

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区渲染合法性与元素着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查顶部油量条 (绿色)
        self.assertEqual(fb[0], 46)
        self.assertEqual(fb[1], 204)
        self.assertEqual(fb[2], 113)

        # 检查生命心 (红色)
        heart_idx = 15 * 3
        self.assertEqual(fb[heart_idx], 231)
        self.assertEqual(fb[heart_idx + 1], 76)
        self.assertEqual(fb[heart_idx + 2], 60)


if __name__ == "__main__":
    unittest.main()
