# -*- coding: utf-8 -*-
"""
test_arcade_147_crazyballoon.py —— 街机游戏 #147 疯狂气球 (Crazy Balloon 1980 / Taito) 单元测试
验证元数据、摆锤式谐振摆动物理、按键A阻尼减摆、按键B反向翻相、风道吹拂、尖刺碰撞爆破与登顶过关
"""

import os
import sys
import unittest
import math

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "pc-agent-vision"))

from arcade.game_147_crazyballoon import (
    Game147CrazyBalloon,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_BALLOON_POPPED,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestGame147CrazyBalloon(unittest.TestCase):
    def setUp(self):
        self.game = Game147CrazyBalloon()

    def test_01_metadata_and_initial_state(self):
        self.assertEqual(self.game.game_id, 147)
        self.assertIn("疯狂气球", self.game.name)
        self.assertEqual(self.game.english_name, "Crazy Balloon")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.level, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.cx, 2.0)
        self.assertEqual(self.game.cy, 13.0)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 147)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["hazards_count"], 2)

    def test_02_harmonic_oscillation_physics(self):
        # Update dt without movement and check pendulum harmonic oscillation
        initial_angle = self.game.swing_angle
        self.game.update(0.1, 0, 0)
        self.assertGreater(self.game.swing_angle, initial_angle)
        # Balloon position should be calculated from trolley plus pendulum arm
        actual_theta = self.game.swing_amp * math.sin(self.game.swing_angle)
        expected_bx = self.game.cx + self.game.arm_length * math.sin(actual_theta)
        expected_by = self.game.cy - self.game.arm_length * math.cos(actual_theta)
        self.assertAlmostEqual(self.game.bx, expected_bx, places=3)
        self.assertAlmostEqual(self.game.by, expected_by, places=3)

    def test_03_stabilizer_damping_with_key_a(self):
        # Holding KEY_A should damp the swing amplitude towards 0.25
        initial_amp = self.game.swing_amp
        for _ in range(10):
            self.game.update(0.05, KEY_A, KEY_A)
        self.assertLess(self.game.swing_amp, initial_amp)
        self.assertLess(self.game.swing_amp, 0.45)

    def test_04_burst_thruster_phase_flip_with_key_b(self):
        # Button B should instantly invert swing_angle phase
        self.game.swing_angle = 1.25
        self.game.update(0.016, KEY_B, 0)
        # After flip, swing_angle should be close to -1.25 + dt * swing_speed
        self.assertLess(self.game.swing_angle, 0.0)

    def test_05_wind_corridor_drift(self):
        # Position trolley in wind corridor (y=6.0)
        self.game.cx = 2.0
        self.game.cy = 6.0
        # No buttons pressed, wind should push cart east (+x)
        self.game.update(0.1, 0, 0)
        self.assertGreater(self.game.cx, 2.0)

    def test_06_trolley_movement_and_wall_blocking(self):
        self.game.cx = 2.0
        self.game.cy = 13.0
        # Move right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.cx, 2.0)

        # Move into outer wall (x=0) should be blocked
        self.game.cx = 1.2
        self.game.cy = 13.0
        self.game.update(0.2, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.cx, 1.0)

    def test_07_spike_wall_collision_pops_balloon(self):
        # Move trolley so balloon collides into interior spike wall (x=4, y=5)
        self.game.cx = 3.8
        self.game.cy = 5.0
        self.game.swing_angle = 0.0
        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_BALLOON_POPPED)
        self.assertEqual(self.game.lives, 2)
        self.assertGreater(len(self.game.particles), 0)

    def test_08_moving_hazard_collision_pops_balloon(self):
        # Move hazard onto balloon
        self.game.cx = 2.0
        self.game.cy = 13.0
        h = self.game.hazards[0]
        h["x"] = self.game.bx
        h["y"] = self.game.by

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_BALLOON_POPPED)
        self.assertEqual(self.game.lives, 2)

    def test_09_goal_reached_clears_stage(self):
        # Place balloon right at goal
        self.game.cx = self.game.gx
        self.game.cy = self.game.gy + self.game.arm_length
        self.game.swing_angle = 0.0

        self.game.update(0.016, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertEqual(self.game.score, 1500)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytearray)
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertTrue(any(b > 0 for b in fb))

        # Check game over after 3 lives lost
        self.game.lives = 0
        self.game.state = STATE_BALLOON_POPPED
        self.game.state_timer = 2.0
        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Press A to reset
        self.game.update(0.016, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)


if __name__ == "__main__":
    unittest.main()
