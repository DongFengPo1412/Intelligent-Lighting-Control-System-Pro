# -*- coding: utf-8 -*-
"""
test_arcade_lifecycle.py —— 街机游戏生命周期与幂等性专用测试
针对 Start / Pause / Resume / Reset / GameOver 严格验证状态机幂等转换
杜绝任何“发送 start 导致暂停”或“重复调用翻转状态”的缺陷。
"""

import unittest
from arcade.game_001_mario import Game001Mario
from arcade.game_033_snake import Game033Snake
from arcade.game_041_tetris import Game041Tetris
from arcade.base_cartridge import (
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
)


class TestArcadeLifecycle(unittest.TestCase):

    def test_01_snake_idempotent_lifecycle(self):
        snake = Game033Snake()
        snake.init()

        # 1. 初始状态为待命 (STATE_TITLE)
        self.assertEqual(snake.get_status()["state"], STATE_TITLE)

        # 2. 调用 start() 启动游戏 -> STATE_PLAYING
        snake.start()
        self.assertEqual(snake.get_status()["state"], STATE_PLAYING)

        # 3. 幂等性测试：已在 PLAYING 状态下重复调用 start()，绝不得误进 PAUSED
        snake.start()
        snake.start()
        self.assertEqual(snake.get_status()["state"], STATE_PLAYING)

        # 4. 调用 pause() -> STATE_PAUSED
        snake.pause()
        self.assertEqual(snake.get_status()["state"], STATE_PAUSED)

        # 5. 幂等性测试：重复调用 pause()，必须严格保持 PAUSED，不得翻转
        snake.pause()
        snake.pause()
        self.assertEqual(snake.get_status()["state"], STATE_PAUSED)

        # 6. 调用 resume() -> STATE_PLAYING
        snake.resume()
        self.assertEqual(snake.get_status()["state"], STATE_PLAYING)

        # 7. 幂等性测试：重复调用 resume()，保持 PLAYING
        snake.resume()
        snake.resume()
        self.assertEqual(snake.get_status()["state"], STATE_PLAYING)

        # 8. Reset() 彻底重置
        snake.reset()
        self.assertEqual(snake.get_status()["state"], STATE_TITLE)
        self.assertEqual(snake.get_status()["score"], 0)

    def test_02_tetris_idempotent_lifecycle(self):
        tetris = Game041Tetris()
        tetris.init()

        # 1. 初始为待命 (STATE_TITLE)
        self.assertEqual(tetris.get_status()["state"], STATE_TITLE)

        # 2. start() -> STATE_PLAYING
        tetris.start()
        self.assertEqual(tetris.get_status()["state"], STATE_PLAYING)

        # 3. 幂等性：重复调用 start() 保持 PLAYING
        tetris.start()
        tetris.start()
        self.assertEqual(tetris.get_status()["state"], STATE_PLAYING)

        # 4. pause() -> STATE_PAUSED
        tetris.pause()
        self.assertEqual(tetris.get_status()["state"], STATE_PAUSED)

        # 5. 幂等性：重复调用 pause() 保持 PAUSED
        tetris.pause()
        tetris.pause()
        self.assertEqual(tetris.get_status()["state"], STATE_PAUSED)

        # 6. resume() -> STATE_PLAYING
        tetris.resume()
        self.assertEqual(tetris.get_status()["state"], STATE_PLAYING)

        # 7. 重复 resume() 保持 PLAYING
        tetris.resume()
        self.assertEqual(tetris.get_status()["state"], STATE_PLAYING)

    def test_03_mario_idempotent_lifecycle(self):
        mario = Game001Mario()
        mario.init()

        # 1. 初始 TITLE
        self.assertEqual(mario.get_status()["state"], STATE_TITLE)

        # 2. start()
        mario.start()
        # 推进动画进入 PLAYING
        for _ in range(100):
            mario.update(0.02, 0, 0)
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)

        # 3. 幂等 start()
        mario.start()
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)

        # 4. pause()
        mario.pause()
        self.assertEqual(mario.get_status()["state"], STATE_PAUSED)

        # 5. 幂等 pause()
        mario.pause()
        self.assertEqual(mario.get_status()["state"], STATE_PAUSED)

        # 6. resume()
        mario.resume()
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
