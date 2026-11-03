# -*- coding: utf-8 -*-
"""
test_arcade_132_babypacman.py —— 街机游戏 #132 幼年吃豆人弹珠台 (Baby Pac-Man 1982 / Bally Midway) 单元测试
"""

import unittest
from arcade.game_132_babypacman import (
    Game132BabyPacman,
    MODE_MAZE,
    MODE_PINBALL,
    STATE_PLAYING,
    STATE_DEATH,
    STATE_MAZE_CLEAR,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B


class TestGame132BabyPacman(unittest.TestCase):
    def setUp(self):
        self.game = Game132BabyPacman()

    def test_01_init_metadata_and_state(self):
        """测试卡带元数据与初始配置"""
        self.assertEqual(self.game.game_id, 132)
        self.assertEqual(self.game.name, "幼年吃豆人弹珠台")
        self.assertEqual(self.game.english_name, "Baby Pac-Man")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.mode, MODE_MAZE)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.energizers_earned, 0)
        self.assertGreater(self.game.remaining_dots, 0)

    def test_02_maze_movement_and_dot_consumption(self):
        """测试吃豆迷宫巡航与豆子吞噬得分"""
        self.game.px = 2.0
        self.game.py = 2.0
        self.game.dots[2][2] = True
        old_dots = self.game.remaining_dots
        old_score = self.game.score

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.dots[2][2])
        self.assertEqual(self.game.remaining_dots, old_dots - 1)
        self.assertEqual(self.game.score, old_score + 10)

    def test_03_tunnel_drop_into_pinball(self):
        """测试钻入迷宫底部逃逸管道无缝切换至实体弹珠台模式"""
        self.game.px = 7.5
        self.game.py = 14.6
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.mode, MODE_PINBALL)
        self.assertTrue(self.game.ball["in_play"])

    def test_04_pinball_flipper_deflection(self):
        """测试弹珠台左右挡板强力抽击钢珠"""
        self.game.start_pinball()
        self.game.ball["x"] = 4.0
        self.game.ball["y"] = 13.5
        self.game.ball["vy"] = 4.0

        # Press Left Flipper (KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertLess(self.game.ball["vy"], 0.0)

    def test_05_pinball_bumper_bounce(self):
        """测试弹珠撞击高弹力缓冲蘑菇反弹得分"""
        self.game.start_pinball()
        self.game.ball["x"] = 5.0
        self.game.ball["y"] = 7.0
        old_score = self.game.score

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.score, old_score + 50)
        self.assertLess(self.game.ball["vy"], 0.0)

    def test_06_pinball_target_unlocks_energizer(self):
        """测试击落目标靶槽解锁大力丸进阶道具"""
        self.game.start_pinball()
        self.game.ball["x"] = 4.0
        self.game.ball["y"] = 3.0

        old_earned = self.game.energizers_earned
        old_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.pinball_targets[0])
        self.assertEqual(self.game.energizers_earned, old_earned + 1)
        self.assertEqual(self.game.score, old_score + 100)

    def test_07_pinball_drain_returns_to_maze(self):
        """测试弹珠出槽漏球返航迷宫并布设解锁的大力丸"""
        self.game.start_pinball()
        self.game.energizers_earned = 2
        self.game.ball["y"] = 15.4
        self.game.ball["vy"] = 4.0 # Moving down towards outlane drain

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.mode, MODE_MAZE)
        self.assertTrue(self.game.energizer_active[0])
        self.assertTrue(self.game.energizer_active[1])

    def test_08_eat_energizer_frightens_ghosts(self):
        """测试吞食大力丸使全体幽灵进入受惊怯敌状态"""
        self.game.energizer_active[0] = True
        self.game.px = 2.0
        self.game.py = 2.0

        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.frightened_timer, 0.0)
        self.assertTrue(self.game.ghosts[0]["frightened"])

    def test_09_eat_frightened_ghost_scores(self):
        """测试吞噬受惊幽灵获得200分逆转绝杀"""
        self.game.frightened_timer = 5.0
        self.game.ghosts[0]["frightened"] = True
        self.game.ghosts[0]["x"] = 7.5
        self.game.ghosts[0]["y"] = 5.0
        self.game.px = 7.5
        self.game.py = 5.0

        old_score = self.game.score
        self.game._check_maze_collisions()
        self.assertEqual(self.game.score, old_score + 200)

    def test_10_unfrightened_ghost_death_and_restart(self):
        """测试常态幽灵捕获玩家致死及生命耗尽重开"""
        self.game.frightened_timer = 0.0
        self.game.ghosts[0]["frightened"] = False
        self.game.ghosts[0]["x"] = self.game.px
        self.game.ghosts[0]["y"] = self.game.py

        self.game._check_maze_collisions()
        self.assertEqual(self.game.state, STATE_DEATH)

        self.game.lives = 1
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertEqual(self.game.lives, 0)

        # Press KEY_A to restart
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
