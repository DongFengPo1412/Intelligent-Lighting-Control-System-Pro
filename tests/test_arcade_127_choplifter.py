# -*- coding: utf-8 -*-
"""
test_arcade_127_choplifter.py —— 街机游戏 #127 救难直升机 (Choplifter 1982 / Sega) 单元测试
"""

import unittest
from arcade.game_127_choplifter import (
    Game127Choplifter,
    STATE_FLYING,
    STATE_CHOPPER_DOWN,
    STATE_MISSION_CLEAR,
    STATE_GAME_OVER,
    FACING_LEFT,
    FACING_FORWARD,
    FACING_RIGHT,
    GROUND_Y,
    MAX_HOSTAGES,
    MAX_ONBOARD,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame127Choplifter(unittest.TestCase):
    def setUp(self):
        self.game = Game127Choplifter()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 127)
        self.assertEqual(self.game.name, "救难直升机")
        self.assertEqual(self.game.english_name, "Choplifter")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.onboard_count, 0)
        self.assertEqual(self.game.rescued_count, 0)
        self.assertEqual(self.game.facing, FACING_RIGHT)

    def test_02_cycle_facing_orientation(self):
        """测试按键B切换三向飞行姿态(右向/左向/俯视向心)"""
        self.assertEqual(self.game.facing, FACING_RIGHT)
        # B -> LEFT
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.facing, FACING_LEFT)
        # B -> FORWARD
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.facing, FACING_FORWARD)
        # B -> RIGHT
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.facing, FACING_RIGHT)

    def test_03_fire_machinegun_and_bomb(self):
        """测试侧向航向机炮射击与正向俯冲重力航弹投放"""
        self.game.facing = FACING_RIGHT
        self.game.update(0.05, KEY_A, 0)
        bullet_right = [b for b in self.game.bullets if b["active"]][0]
        self.assertFalse(bullet_right["is_bomb"])
        self.assertGreater(bullet_right["vx"], 0.0)

        # Clear bullets
        for b in self.game.bullets:
            b["active"] = False

        # Switch to FORWARD mid-air -> drops bomb
        self.game.hy = 6.0
        self.game.facing = FACING_FORWARD
        self.game.update(0.05, KEY_A, 0)
        bomb = [b for b in self.game.bullets if b["active"]][0]
        self.assertTrue(bomb["is_bomb"])
        self.assertGreater(bomb["vy"], 0.0)

    def test_04_bomb_breaks_barracks_and_frees_hostages(self):
        """测试轰炸集中营牢房解救人质狂奔撤离"""
        self.assertFalse(self.game.barracks_broken)
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = 10.5
        self.game.bullets[0]["y"] = 12.5
        self.game.bullets[0]["is_bomb"] = True
        self.game.barracks_hp = 1.0

        self.game._check_collisions()
        self.assertTrue(self.game.barracks_broken)
        running = [h for h in self.game.hostages if h["state"] == 1]
        self.assertEqual(len(running), MAX_HOSTAGES)

    def test_05_landing_and_hostage_embarkation(self):
        """测试敌后平稳着陆开门接纳奔跑的人质登机"""
        self.game.hx = 9.0
        self.game.hy = GROUND_Y
        self.game.hvx = 0.0
        self.game.hvy = 0.0
        self.game.is_landed = True

        # Hostage near chopper
        self.game.hostages[0]["state"] = 1
        self.game.hostages[0]["x"] = 9.1
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.hostages[0]["state"], 2) # Onboard
        self.assertEqual(self.game.onboard_count, 1)

    def test_06_base_disembarkation_and_scoring(self):
        """测试返航友军基地着陆安全转运人质每人加500分"""
        self.game.hx = 2.0
        self.game.hy = 13.78
        self.game.hvx = 0.0
        self.game.hvy = 0.5
        self.game.onboard_count = 4

        old_score = self.game.score
        # Soft touchdown at base camp
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.onboard_count, 0)
        self.assertEqual(self.game.rescued_count, 4)
        self.assertEqual(self.game.score, old_score + 4 * 500)

    def test_07_hard_landing_crash(self):
        """测试超速俯冲硬着陆导致直升机失事坠毁"""
        self.game.hx = 8.0
        self.game.hy = GROUND_Y - 0.2
        self.game.hvy = 6.0 # Excessive sink rate
        self.game.hvx = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CHOPPER_DOWN)

    def test_08_jet_collision_loss(self):
        """测试空中遭遇敌军防空喷气机迎头相撞战损"""
        self.game.jets[0]["active"] = True
        self.game.jets[0]["x"] = self.game.hx
        self.game.jets[0]["y"] = self.game.hy

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CHOPPER_DOWN)

    def test_09_mission_success_clear(self):
        """测试撤离满编人质完成营救任务晋级下一战役"""
        self.game.rescued_count = 12
        self.game.kia_count = 4
        self.game.onboard_count = 0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_MISSION_CLEAR)

        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.mission, 2)
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_10_game_over_and_restart(self):
        """测试战机损耗殆尽游戏结束与按键投币重开"""
        self.game.lives = 1
        self.game.state = STATE_CHOPPER_DOWN
        self.game.state_timer = 2.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
