# -*- coding: utf-8 -*-
"""test_arcade_target_batch1.py —— 测试第一批 10 款目标街机游戏卡带规范与运行逻辑
严格验证目标编号映射 (Target IDs):
  #009 Flappy Bird (legacy #005)
  #010 Stack (legacy #006)
  #020 Pong (legacy #007)
  #021 Breakout (legacy #008)
  #026 Space Invaders (legacy #009)
  #034 Pac-Man (legacy #010)
  #038 Bomberman (legacy #013)
  #054 Sokoban (legacy #014)
  #074 Highway Racer (legacy #012)
  #097 Frogger (legacy #011)
"""

import unittest
from arcade.game_009_flappy_bird import Game009FlappyBird
from arcade.game_010_stack import Game010Stack
from arcade.game_020_pong import Game020Pong
from arcade.game_021_breakout import Game021Breakout
from arcade.game_026_space_invaders import Game026SpaceInvaders
from arcade.game_034_pacman import Game034Pacman
from arcade.game_038_bomberman import Game038Bomberman
from arcade.game_054_sokoban import Game054Sokoban
from arcade.game_074_highway_racer import Game074HighwayRacer
from arcade.game_097_frogger import Game097Frogger

from arcade.base_cartridge import (
    CTRL_TAP_SINGLE,
    CTRL_TWO_BUTTON,
    CTRL_DPAD_4WAY,
    CTRL_ARCADE_AB,
    CTRL_VERSUS_DUAL,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
    KEY_A,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_START,
)
from arcade_runner import ArcadeSession


class TestArcadeTargetBatch1(unittest.TestCase):

    def test_01_target_ids_and_metadata(self):
        games = [
            (Game009FlappyBird(), 9, "飞翔小鸟", CTRL_TAP_SINGLE),
            (Game010Stack(), 10, "堆叠大师", CTRL_TAP_SINGLE),
            (Game020Pong(), 20, "双人乒乓", CTRL_VERSUS_DUAL),
            (Game021Breakout(), 21, "经典打砖块", CTRL_TWO_BUTTON),
            (Game026SpaceInvaders(), 26, "太空侵略者", CTRL_ARCADE_AB),
            (Game034Pacman(), 34, "吃豆人", CTRL_DPAD_4WAY),
            (Game038Bomberman(), 38, "炸弹人", CTRL_ARCADE_AB),
            (Game054Sokoban(), 54, "推箱子", CTRL_DPAD_4WAY),
            (Game074HighwayRacer(), 74, "变道赛车", CTRL_TWO_BUTTON),
            (Game097Frogger(), 97, "青蛙过河", CTRL_DPAD_4WAY),
        ]

        for cart, expected_id, expected_name, expected_ctrl in games:
            self.assertEqual(cart.game_id, expected_id, f"Target ID mismatch for {expected_name}")
            self.assertEqual(cart.name, expected_name)
            self.assertEqual(cart.control_type, expected_ctrl)
            fb = cart.render()
            self.assertEqual(len(fb), 768, f"Frame buffer size mismatch for #{expected_id}")

    def test_02_flappy_bird_lifecycle_and_physics(self):
        g = Game009FlappyBird()
        self.assertEqual(g.game_id, 9)
        g.start()
        st = g.get_status()
        self.assertEqual(st["state"], STATE_PLAYING)

        initial_y = g.bird_y
        g.update(0.1, 0, 0)
        self.assertGreater(g.bird_y, initial_y, "Bird should fall under gravity")

        vy_before = g.bird_vy
        g.update(0.016, KEY_A, KEY_A)
        self.assertLess(g.bird_vy, 0, "Flap key should give upward velocity")

        # Test pause
        g.pause()
        self.assertEqual(g.get_status()["state"], STATE_PAUSED)
        g.resume()
        self.assertEqual(g.get_status()["state"], STATE_PLAYING)

    def test_03_stack_master_slicing(self):
        g = Game010Stack()
        self.assertEqual(g.game_id, 10)
        g.start()
        self.assertEqual(len(g.layers), 1)

        g.active_x = 3.5  # perfectly aligned with base
        g.update(0.016, KEY_A, KEY_A)
        self.assertEqual(len(g.layers), 2)
        self.assertEqual(g._score, 1)

    def test_04_pong_bouncing_and_scoring(self):
        g = Game020Pong()
        self.assertEqual(g.game_id, 20)
        g.start()
        self.assertEqual(g.get_status()["state"], STATE_PLAYING)

        # Move paddle down
        initial_p1_y = g.p1_y
        g.update(0.1, KEY_DOWN, 0)
        self.assertGreater(g.p1_y, initial_p1_y)

    def test_05_breakout_paddle_and_bricks(self):
        g = Game021Breakout()
        self.assertEqual(g.game_id, 21)
        g.start()
        self.assertEqual(g.lives, 3)
        self.assertEqual(g.remaining_bricks, 32)

        # Launch ball
        g.update(0.016, KEY_A, KEY_A)
        self.assertFalse(g.ball_stuck)

    def test_06_space_invaders_fleet_and_bullet(self):
        g = Game026SpaceInvaders()
        self.assertEqual(g.game_id, 26)
        g.start()
        self.assertEqual(g.remaining_aliens, 12)

        # Fire player bullet
        g.update(0.016, KEY_A, KEY_A)
        self.assertTrue(any(b.vy < 0 for b in g.bullets))

    def test_07_pacman_maze_and_dot_consumption(self):
        g = Game034Pacman()
        self.assertEqual(g.game_id, 34)
        g.start()
        initial_dots = g.remaining_dots
        self.assertGreater(initial_dots, 50)

        # Move pacman left
        for _ in range(6):
            g.update(0.05, KEY_LEFT, KEY_LEFT)
        self.assertLess(g.remaining_dots, initial_dots)

    def test_08_bomberman_bomb_placement_and_flame(self):
        g = Game038Bomberman()
        self.assertEqual(g.game_id, 38)
        g.start()
        self.assertIsNone(g.bomb)

        # Place bomb
        g.update(0.016, KEY_A, KEY_A)
        self.assertIsNotNone(g.bomb)
        self.assertTrue(g.bomb.active)

    def test_09_sokoban_crate_pushing(self):
        g = Game054Sokoban()
        self.assertEqual(g.game_id, 54)
        g.start()
        self.assertEqual(g.player_x, 7)
        self.assertEqual(g.player_y, 8)

        # Player at (7,8). Push box at (6,6) or move around
        g.update(0.016, KEY_LEFT, KEY_LEFT)
        self.assertEqual(g.player_x, 6)
        self.assertEqual(g.moves, 1)

    def test_10_highway_racer_steering_and_distance(self):
        g = Game074HighwayRacer()
        self.assertEqual(g.game_id, 74)
        g.start()
        initial_dist = g.distance_m

        g.update(0.1, 0, 0)
        self.assertGreater(g.distance_m, initial_dist)

    def test_11_frogger_log_and_river(self):
        g = Game097Frogger()
        self.assertEqual(g.game_id, 97)
        g.start()
        self.assertEqual(g.frog_y, 14)
        self.assertEqual(g.lives, 3)

        # Hop up
        g.update(0.016, KEY_UP, KEY_UP)
        self.assertEqual(g.frog_y, 13)
        self.assertEqual(g._score, 10)

    def test_12_arcade_session_hardware_and_simulation_isolation(self):
        class MockOfflineController:
            port = "COM3"
            control_connected = False

        session = ArcadeSession(controller=MockOfflineController())

        # 1. Hardware mode with offline hardware MUST NOT silently fallback to simulator
        res = session.select_game(9, force_simulation=False)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error"], "device_offline")

        res_start = session.start()
        self.assertEqual(res_start["status"], "error")
        self.assertEqual(res_start["error"], "device_offline")

        res_frame = session.get_frame()
        self.assertFalse(res_frame["running"])
        self.assertEqual(res_frame["source"], "hardware_offline")

        # 2. Explicit simulation mode is strictly isolated
        sim_res = session.select_game(9, force_simulation=True)
        self.assertEqual(sim_res["status"], "ok")
        self.assertEqual(sim_res["source"], "simulator")
        self.assertTrue(sim_res["simulated"])

        sim_frame = session.get_frame()
        self.assertEqual(sim_frame["source"], "simulator")
        self.assertEqual(len(sim_frame["hex"]), 1536)


if __name__ == "__main__":
    unittest.main()
