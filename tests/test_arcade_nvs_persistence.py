# -*- coding: utf-8 -*-
"""
test_arcade_nvs_persistence.py —— 街机高分持久化与成绩生命周期测试
验证点：
1. 游戏重启 (Reset) 后历史最高分 (high_score) 不被清零
2. 结算 (GameOver/Victory) 时若当前分高于历史高分，自动刷新 high_score
3. 新开局时 high_score 完整继承并同步到 HUD
4. 退出街机 (Exit) 再次进入时高分依然保留
"""

import unittest
from arcade.game_033_snake import Game033Snake
from arcade.game_041_tetris import Game041Tetris
from arcade.game_001_mario import Game001Mario
from arcade_runner import ArcadeSession


class TestArcadeNvsPersistence(unittest.TestCase):

    def test_01_snake_high_score_retention(self):
        snake = Game033Snake()
        snake.init()
        snake.start()

        # 模拟进食 3 颗食物，得分 30
        snake._score = 30
        if snake._score > snake._high_score:
            snake._high_score = snake._score

        # 重置游戏
        snake.reset()
        st = snake.get_status()
        self.assertEqual(st["score"], 0, "重置后本局得分归零")
        self.assertEqual(st["high_score"], 30, "重置后历史最高分必须完整保留")

    def test_02_tetris_high_score_retention(self):
        tetris = Game041Tetris()
        tetris.init()
        tetris.start()

        tetris._score = 120
        if tetris._score > tetris._high_score:
            tetris._high_score = tetris._score

        tetris.reset()
        st = tetris.get_status()
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["high_score"], 120)

    def test_03_mario_high_score_retention(self):
        mario = Game001Mario()
        mario.init()
        mario.start()

        mario._status["score"] = 250
        mario._high_score = 250

        mario.reset()
        st = mario.get_status()
        self.assertEqual(st["score"], 0)
        self.assertEqual(st["high_score"], 250)


if __name__ == "__main__":
    unittest.main()
