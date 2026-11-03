# -*- coding: utf-8 -*-
"""
test_arcade_124_carnival.py —— 街机游戏 #124 狂欢节射击场 (Carnival 1980 / Sega) 单元测试
"""

import unittest
from arcade.game_124_carnival import (
    Game124Carnival,
    STATE_PLAYING,
    STATE_ROUND_CLEAR,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame124Carnival(unittest.TestCase):
    def setUp(self):
        self.game = Game124Carnival()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 124)
        self.assertEqual(self.game.name, "狂欢节射击场")
        self.assertEqual(self.game.english_name, "Carnival")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.ammo, 40)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.round, 1)
        self.assertGreater(self.game.get_remaining_targets(), 10)

    def test_02_gun_movement(self):
        """测试炮台左右横向移动与轨道边界限制"""
        self.game.gun_x = 2.0
        # Move left
        for _ in range(10):
            self.game.update(0.05, KEY_LEFT, KEY_LEFT)
        self.assertGreaterEqual(self.game.gun_x, 0.5)

        # Move right
        for _ in range(30):
            self.game.update(0.05, KEY_RIGHT, KEY_RIGHT)
        self.assertLessEqual(self.game.gun_x, 15.5)

    def test_03_fire_bullet_decrements_ammo(self):
        """测试按键A发射子弹精确扣除弹药库存"""
        self.assertEqual(self.game.ammo, 40)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.ammo, 39)
        active_bullets = [b for b in self.game.bullets if b["active"]]
        self.assertEqual(len(active_bullets), 1)

    def test_04_bullet_movement_and_expiration(self):
        """测试弹丸向上飞行动力学与越界销毁"""
        self.game.update(0.05, KEY_A, 0)
        bullet = [b for b in self.game.bullets if b["active"]][0]
        initial_y = bullet["y"]
        self.game.update(0.05, 0, 0)
        self.assertLess(bullet["y"], initial_y)

        # Move until offscreen
        for _ in range(20):
            self.game.update(0.05, 0, 0)
        self.assertFalse(bullet["active"])

    def test_05_carousel_rotation(self):
        """测试三层传送带对向循环旋转"""
        init_offsets = list(self.game.row_offsets)
        self.game.update(0.05, 0, 0)
        self.assertNotEqual(self.game.row_offsets[0], init_offsets[0])
        self.assertNotEqual(self.game.row_offsets[1], init_offsets[1])

    def test_06_target_hit_scores_and_ammo_box(self):
        """测试击落普通靶标加分及命中补给箱+5弹药"""
        target = self.game.rows[0][2] # Ammo box (type 3)
        self.game.row_offsets[0] = 0.0
        target_x = target["x"]

        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = target_x
        self.game.bullets[0]["y"] = 3.0

        old_ammo = self.game.ammo
        self.game._check_collisions()
        self.assertFalse(target["alive"])
        self.assertEqual(self.game.ammo, old_ammo + 5)

    def test_07_top_bonus_wheel_hit(self):
        """测试击中顶部转轮飞管获得10发弹药和150分奖励"""
        self.game.bonus_wheel_alive = True
        self.game.bonus_wheel_x = 5.0

        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = 5.0
        self.game.bullets[0]["y"] = 1.0

        old_score = self.game.score
        old_ammo = self.game.ammo
        self.game._check_collisions()
        self.assertFalse(self.game.bonus_wheel_alive)
        self.assertEqual(self.game.score, old_score + 150)
        self.assertEqual(self.game.ammo, old_ammo + 10)

    def test_08_diving_duck_steals_ammo(self):
        """测试俯冲野鸭扑向炮台偷吃5发弹药"""
        self.game.gun_x = 7.5
        self.game.diving_duck["active"] = True
        self.game.diving_duck["x"] = 7.5
        self.game.diving_duck["y"] = 13.9
        self.game.diving_duck["vy"] = 5.0

        old_ammo = self.game.ammo
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.ammo, old_ammo - 5)
        self.assertFalse(self.game.diving_duck["active"])

    def test_09_round_clear_and_ammo_bonus(self):
        """测试清空所有射击靶标通关并按剩余弹药结算积分"""
        for r in range(3):
            for t in self.game.rows[r]:
                t["alive"] = False
        self.game.diving_duck["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.round, 2)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_10_ammo_depletion_game_over(self):
        """测试弹药耗尽且靶标未清空触发游戏结束"""
        self.game.ammo = 0
        for b in self.game.bullets:
            b["active"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.ammo, 40)


if __name__ == "__main__":
    unittest.main()
