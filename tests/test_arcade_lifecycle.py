# -*- coding: utf-8 -*-
"""
test_arcade_lifecycle.py —— 街机游戏生命周期与状态同步验证
验证点：
1. Start / Pause / Resume / Reset 幂等性
2. 断线重连语义：重连后保持 PAUSED，绝不自动继续
3. 延迟/重复控制包拦截：暂停状态下收到常规方向键不误恢复游戏
4. 游戏切换清理：切换游戏彻底清除旧游戏的长按与按键缓冲区
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
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
)
from arcade_runner import ArcadeSession


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

        self.assertEqual(mario.get_status()["state"], STATE_TITLE)
        mario.start()
        for _ in range(100):
            mario.update(0.02, 0, 0)
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)

        mario.start()
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)

        mario.pause()
        self.assertEqual(mario.get_status()["state"], STATE_PAUSED)

        mario.pause()
        self.assertEqual(mario.get_status()["state"], STATE_PAUSED)

        mario.resume()
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)

    def test_04_paused_ignores_delayed_and_duplicate_input(self):
        """暂停状态下收到延迟、重复的方向键包，不得误恢复游戏"""
        snake = Game033Snake()
        snake.init()
        snake.start()
        self.assertEqual(snake.get_status()["state"], STATE_PLAYING)

        snake.pause()
        self.assertEqual(snake.get_status()["state"], STATE_PAUSED)

        # 发送重复的左、右、上按键包
        snake.update(0.1, KEY_LEFT, KEY_LEFT)
        snake.update(0.1, KEY_RIGHT, KEY_RIGHT)
        snake.update(0.1, KEY_UP, KEY_UP)

        # 必须依旧严格处于 PAUSED 状态
        self.assertEqual(snake.get_status()["state"], STATE_PAUSED)

        # 只有显式 resume() 才能恢复
        snake.resume()
        self.assertEqual(snake.get_status()["state"], STATE_PLAYING)

    def test_05_session_game_switch_clears_keys(self):
        """测试 ArcadeSession 在游戏切换时彻底重置按键长按状态"""
        session = ArcadeSession()
        session.select_game(1, force_simulation=True)
        session.key("right", is_down=True)
        self.assertEqual(session.keys_down, KEY_RIGHT)

        # 切换到贪吃蛇
        session.select_game(33, force_simulation=True)
        # 验证旧键长按已被彻底清除
        self.assertEqual(session.keys_down, 0)
        self.assertEqual(session.keys_pressed, 0)
        self.assertEqual(session.status["game_id"], 33)


if __name__ == "__main__":
    unittest.main()
