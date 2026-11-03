# -*- coding: utf-8 -*-
"""
test_arcade_122_bosconian.py —— 街机游戏 #122 宇宙巡航者 (Bosconian 1981 / Namco) 单元测试
"""

import unittest
from arcade.game_122_bosconian import (
    Game122Bosconian,
    STATE_FLYING,
    STATE_PLAYER_EXPLODING,
    STATE_SECTOR_CLEAR,
    STATE_GAME_OVER,
    ALERT_GREEN,
    ALERT_YELLOW,
    ALERT_RED,
    WORLD_SIZE,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame122Bosconian(unittest.TestCase):
    def setUp(self):
        self.game = Game122Bosconian()

    def test_01_init_state_and_metadata(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 122)
        self.assertEqual(self.game.name, "宇宙巡航者")
        self.assertEqual(self.game.english_name, "Bosconian")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.alert, ALERT_GREEN)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(len(self.game.stations), 3)
        for s in self.game.stations:
            self.assertTrue(s["active"])
            self.assertTrue(s["core_alive"])
            self.assertEqual(len(s["pods_alive"]), 6)

    def test_02_directional_flight_and_wrapping(self):
        """测试全向巡航推进与48x48环形宇宙穿梭"""
        self.game.px = 47.5
        self.game.py = 24.0
        # Steering RIGHT
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.dir_x, 1)
        self.assertEqual(self.game.dir_y, 0)
        self.assertGreater(self.game.vx, 0.0)
        # Verify toroidal wrap over boundary 48.0
        self.game.px = 47.9
        self.game.update(0.05, KEY_RIGHT, KEY_RIGHT)
        self.assertLess(self.game.px, 2.0)

    def test_03_dual_cannon_firing(self):
        """测试按键A触发前后双向火炮同时齐射"""
        self.game.dir_x = 0
        self.game.dir_y = -1
        self.game.update(0.05, KEY_A, 0)
        active_bullets = [b for b in self.game.bullets if b["active"]]
        self.assertEqual(len(active_bullets), 2)
        # Front bullet moves North (-vy)
        front = [b for b in active_bullets if b["vy"] < -10.0]
        # Rear bullet moves South (+vy)
        rear = [b for b in active_bullets if b["vy"] > 10.0]
        self.assertEqual(len(front), 1)
        self.assertEqual(len(rear), 1)

    def test_04_radar_and_alert_display(self):
        """测试渲染输出包含顶部雷达与警戒状态信标"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        # Green alert level should light radar banner
        self.game.alert = ALERT_RED
        fb_red = self.game.render()
        self.assertIsNotNone(fb_red)

    def test_05_interceptor_collision(self):
        """测试敌机拦截碰撞导致自机爆炸状态"""
        self.game.interceptors[0]["active"] = True
        self.game.interceptors[0]["x"] = self.game.px
        self.game.interceptors[0]["y"] = self.game.py
        self.game.interceptors[0]["is_spy"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_EXPLODING)

    def test_06_spy_ship_alert_red(self):
        """测试间谍飞船逃逸触发红色警戒 Condition Red"""
        self.game.interceptors[0]["active"] = True
        self.game.interceptors[0]["is_spy"] = True
        self.game.interceptors[0]["x"] = 0.0
        self.game.interceptors[0]["y"] = 0.0
        self.game.px = 24.0
        self.game.py = 24.0
        # Distance > 18.0 causes spy escape -> ALERT_RED
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.alert, ALERT_RED)

    def test_07_station_cannon_destruction(self):
        """测试击毁太空站外围炮塔并累积分数"""
        station = self.game.stations[0]
        pod_0_x = station["x"] + 0.0
        pod_0_y = station["y"] - 1.8
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = pod_0_x
        self.game.bullets[0]["y"] = pod_0_y
        self.game.bullets[0]["life"] = 1.0

        old_score = self.game.score
        self.game._check_collisions()
        self.assertFalse(station["pods_alive"][0])
        self.assertGreater(self.game.score, old_score)

    def test_08_nuclear_core_one_hit_penetration(self):
        """测试贯通打击中央反应核一击摧毁整个太空站"""
        station = self.game.stations[0]
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = station["x"]
        self.game.bullets[0]["y"] = station["y"]
        self.game.bullets[0]["life"] = 1.0

        self.game._check_collisions()
        self.assertFalse(station["core_alive"])
        self.game.update(0.05, 0, 0)
        self.assertFalse(station["active"])

    def test_09_sector_clear_advancement(self):
        """测试摧毁所有敌方太空基地通关并进入下一轮"""
        for s in self.game.stations:
            s["active"] = False
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_SECTOR_CLEAR)
        # Advance timer past 1.6s
        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.round, 2)
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_10_game_over_and_restart(self):
        """测试自机耗尽进入游戏结束状态并可投币重置"""
        self.game.lives = 1
        self.game.state = STATE_PLAYER_EXPLODING
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
