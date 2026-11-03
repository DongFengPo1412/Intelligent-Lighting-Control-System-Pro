# -*- coding: utf-8 -*-
"""
test_arcade_128_seawolf.py —— 街机游戏 #128 潜艇潜望镜猎杀 (Sea Wolf 1976 / Midway) 单元测试
"""

import unittest
from arcade.game_128_seawolf import (
    Game128SeaWolf,
    STATE_HUNTING,
    STATE_PATROL_CLEAR,
    STATE_GAME_OVER,
    LANE_Y,
    MINE_Y,
)
from arcade.base_cartridge import KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame128SeaWolf(unittest.TestCase):
    def setUp(self):
        self.game = Game128SeaWolf()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 128)
        self.assertEqual(self.game.name, "潜艇潜望镜猎杀")
        self.assertEqual(self.game.english_name, "Sea Wolf")
        self.assertEqual(self.game.release_year, 1976)
        self.assertEqual(self.game.state, STATE_HUNTING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.patrol_round, 1)
        self.assertEqual(self.game.time_remaining, 60.0)
        self.assertEqual(self.game.get_available_tubes(), 4)

    def test_02_periscope_traverse(self):
        """测试潜望镜左右大范围回转扫视与限位"""
        self.game.periscope_x = 7.5
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.periscope_x, 7.5)

        for _ in range(40):
            self.game.update(0.05, KEY_RIGHT, KEY_RIGHT)
        self.assertLessEqual(self.game.periscope_x, 15.5)

    def test_03_torpedo_launch_and_reload(self):
        """测试按键A发射鱼雷管序列齐射与装填计时"""
        self.assertEqual(self.game.get_available_tubes(), 4)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.get_available_tubes(), 3)
        active_torps = [t for t in self.game.torpedoes if t["active"]]
        self.assertEqual(len(active_torps), 1)
        self.assertGreater(self.game.tube_reload_timers[0], 0.0)

    def test_04_torpedo_trajectory_and_wake(self):
        """测试鱼雷直航动力学与出界销毁"""
        self.game.update(0.05, KEY_A, 0)
        torp = [t for t in self.game.torpedoes if t["active"]][0]
        initial_y = torp["y"]
        self.game.update(0.05, 0, 0)
        self.assertLess(torp["y"], initial_y)

    def test_05_torpedo_hits_sea_mine(self):
        """测试鱼雷触碰水面漂浮水雷引爆拦截"""
        mine = self.game.mines[0]
        mine["x"] = 7.5
        mine["y"] = MINE_Y
        mine["active"] = True

        self.game.torpedoes[0]["active"] = True
        self.game.torpedoes[0]["x"] = 7.5
        self.game.torpedoes[0]["y"] = MINE_Y
        self.game.torpedoes[0]["vy"] = -12.0

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(mine["active"])
        self.assertFalse(self.game.torpedoes[0]["active"])
        self.assertEqual(self.game.score, old_score + 20)

    def test_06_hit_cargo_and_destroyer(self):
        """测试鱼雷击沉中慢速驱逐舰与货轮"""
        ship = self.game.ships[0]
        ship["active"] = True
        ship["type"] = 1 # Destroyer
        ship["x"] = 5.0
        ship["y"] = LANE_Y[1]

        self.game.torpedoes[0]["active"] = True
        self.game.torpedoes[0]["x"] = 5.0
        self.game.torpedoes[0]["y"] = LANE_Y[1]

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(ship["active"])
        self.assertEqual(self.game.score, old_score + 200)

    def test_07_hit_fast_pt_boat_time_extension(self):
        """测试精准狙击高速鱼雷快艇获得500分与延长巡逻战备时间"""
        ship = self.game.ships[0]
        ship["active"] = True
        ship["type"] = 0 # PT Boat
        ship["x"] = 8.0
        ship["y"] = LANE_Y[0]

        self.game.torpedoes[0]["active"] = True
        self.game.torpedoes[0]["x"] = 8.0
        self.game.torpedoes[0]["y"] = LANE_Y[0]

        old_time = self.game.time_remaining
        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(ship["active"])
        self.assertEqual(self.game.score, old_score + 500)
        self.assertEqual(self.game.time_remaining, old_time + 5.0)

    def test_08_patrol_countdown_clear(self):
        """测试击沉达标在巡逻时间耗尽后晋级下一海区"""
        self.game.ships_sunk = 10
        self.game.time_remaining = 0.04

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PATROL_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.patrol_round, 2)
        self.assertEqual(self.game.state, STATE_HUNTING)

    def test_09_patrol_countdown_game_over(self):
        """测试战绩不达标时巡逻时间耗尽进入游戏结束"""
        self.game.ships_sunk = 2
        self.game.time_remaining = 0.04

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

    def test_10_game_over_restart(self):
        """测试游戏结束按键重新投币开启新猎杀巡航"""
        self.game.state = STATE_GAME_OVER
        self.game.time_remaining = 0.0

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_HUNTING)
        self.assertEqual(self.game.time_remaining, 60.0)


if __name__ == "__main__":
    unittest.main()
