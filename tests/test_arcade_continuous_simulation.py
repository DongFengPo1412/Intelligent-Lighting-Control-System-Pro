# -*- coding: utf-8 -*-
"""
test_continuous_simulation.py —— 连续多帧动态画面演进测试验证
针对三大基石游戏（超级马里奥、经典贪吃蛇、俄罗斯方块）
验证 30+ 帧连续动态演进、动力学轨迹、状态流转以及非死图断言。
"""

import unittest
from arcade.game_001_mario import Game001Mario
from arcade.game_033_snake import Game033Snake
from arcade.game_041_tetris import Game041Tetris, BOARD_LEFT, BOARD_RIGHT
from arcade.base_cartridge import (
    STATE_TITLE,
    STATE_PLAYING,
    STATE_GAMEOVER,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
)


def frame_diff_pixels(fb_a: bytearray, fb_b: bytearray) -> int:
    """计算两帧之间发生变化的像素点数量"""
    diff_count = 0
    for i in range(256):
        idx = i * 3
        if (fb_a[idx] != fb_b[idx] or
            fb_a[idx + 1] != fb_b[idx + 1] or
            fb_a[idx + 2] != fb_b[idx + 2]):
            diff_count += 1
    return diff_count


class TestContinuousSimulation(unittest.TestCase):

    def test_01_mario_continuous_jump_and_run(self):
        """马里奥起跳、腾空、下落与奔跑连续多帧演进"""
        mario = Game001Mario()
        mario.init()

        # 1. Title -> Start -> Ready -> Play
        mario.update(0.02, KEY_A, KEY_A)
        for _ in range(100):
            mario.update(0.02, 0, 0)
        self.assertEqual(mario.get_status()["state"], STATE_PLAYING)

        frames = []
        # 2. 连续 40 帧模拟：奔跑并跳跃
        for frame_idx in range(40):
            if frame_idx == 5:
                # 在第 5 帧触发跳跃按键
                mario.update(0.02, KEY_RIGHT | KEY_A, KEY_A)
            elif frame_idx < 15:
                # 持续保持跳跃键上升
                mario.update(0.02, KEY_RIGHT | KEY_A, 0)
            else:
                # 释放跳跃键，由于重力回落并着陆
                mario.update(0.02, KEY_RIGHT, 0)

            fb = mario.render()
            frames.append(bytes(fb))

        # 3. 验证多帧动态性：绝不是静态死图 (在16x16像素离散化下，亚像素运动每2-3帧跨越一个LED像素)
        dynamic_transitions = 0
        for i in range(1, len(frames)):
            diff = frame_diff_pixels(frames[i], frames[i - 1])
            if diff > 0:
                dynamic_transitions += 1

        self.assertGreater(dynamic_transitions, 15, "Mario running/jumping must show continuous frame transitions")

    def test_02_snake_continuous_crawling_and_eating(self):
        """贪吃蛇连续爬行、直角转向、进食生长与画面动态演进"""
        snake = Game033Snake(wrap_walls=True)
        snake.init()
        snake.start()

        frames = []
        # 1. 爬行 4 步向右
        for _ in range(4):
            snake.update(0.36, 0, 0)
            frames.append(bytes(snake.render()))

        # 2. 向下转向并爬行 3 步
        snake.update(0.01, KEY_DOWN, KEY_DOWN)
        for _ in range(3):
            snake.update(0.36, 0, 0)
            frames.append(bytes(snake.render()))

        # 3. 强制在蛇头前生成食物并进食
        hx, hy = snake._snake[0]
        snake._food = ((hx + 1) % 16, hy)
        snake.update(0.01, KEY_RIGHT, KEY_RIGHT)
        snake.update(0.36, 0, 0)
        frames.append(bytes(snake.render()))

        # 验证身长生长 (至少吃到 1 颗食物)
        self.assertGreaterEqual(len(snake._snake), 4)

        # 验证每一帧与前一帧均有像素移动
        for i in range(1, len(frames)):
            diff = frame_diff_pixels(frames[i], frames[i - 1])
            self.assertGreater(diff, 0, f"Snake frame {i} must move relative to frame {i-1}")

    def test_03_tetris_continuous_drop_rotate_and_lock(self):
        """俄罗斯方块连续下落、旋转、触底固定与新方块生成演进"""
        tetris = Game041Tetris()
        tetris.init()
        tetris.start()

        # 固定测试方块为 L 型
        tetris._piece_type = 3  # L 型
        tetris._piece_x = 6
        tetris._piece_y = 0
        tetris._piece_rot = 0

        frames = []
        frames.append(bytes(tetris.render()))

        # 1. 旋转方块 (第 1 帧)
        tetris.update(0.01, KEY_A, KEY_A)
        frames.append(bytes(tetris.render()))
        self.assertEqual(tetris._piece_rot, 1)

        # 2. 连续下落至底部 (15 步快速下落)
        for _ in range(15):
            tetris.update(0.06, KEY_DOWN, 0)
            frames.append(bytes(tetris.render()))

        # 3. 验证方块触底并已锁定在场地中
        locked_pixel_count = 0
        for y in range(16):
            for x in range(BOARD_LEFT, BOARD_RIGHT + 1):
                if tetris._field[y][x] != 0:
                    locked_pixel_count += 1
        self.assertGreaterEqual(locked_pixel_count, 4, "Tetris piece must be locked into field")

        # 4. 验证画面连续动态演变
        dynamic_steps = 0
        for i in range(1, len(frames)):
            diff = frame_diff_pixels(frames[i], frames[i - 1])
            if diff > 0:
                dynamic_steps += 1
        self.assertGreater(dynamic_steps, 10, "Tetris falling and rotating must produce continuous visual changes")


if __name__ == "__main__":
    unittest.main()
