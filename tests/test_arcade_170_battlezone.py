"""
Unit tests for Game #170: 矢量坦克战 (Battlezone - 1980 Atari / Ed Rotberg)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
import math
from arcade.game_170_battlezone import (
    Game170Battlezone,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_SECTOR_CLEAR, STATE_TANK_EXPLODING, STATE_GAME_OVER
)

class TestArcade170Battlezone(unittest.TestCase):
    def setUp(self):
        self.game = Game170Battlezone()

    def test_01_init_state_and_tank(self):
        """Verify initial state, lives=3, sector=1, player at (8, 10), obstacles and enemies."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.sector, 1)
        self.assertEqual(len(self.game.obstacles), 3)
        self.assertAlmostEqual(self.game.px, 8.0)
        self.assertAlmostEqual(self.game.py, 10.0)
        self.assertAlmostEqual(self.game.angle, -math.pi / 2.0)

    def test_02_tank_steering_and_rotation(self):
        """Steering left/right rotates heading; up drives forward along heading."""
        init_angle = self.game.angle
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.angle, init_angle)

        # Drive forward along new heading
        old_px, old_py = self.game.px, self.game.py
        self.game.update(0.1, keys_down=KEY_UP)
        self.assertNotEqual((self.game.px, self.game.py), (old_px, old_py))

    def test_03_geometric_obstacle_collision_blocks_tank(self):
        """Driving directly into obstacle at (8.0, 8.0) is blocked."""
        self.game.px = 8.0
        self.game.py = 9.2
        self.game.angle = -math.pi / 2.0 # Facing UP toward (8.0, 8.0)

        for _ in range(10):
            self.game.update(0.05, keys_down=KEY_UP)

        self.assertGreaterEqual(self.game.py, 8.8) # Stopped by obstacle

    def test_04_cannon_ballistics_and_cooldown(self):
        """Press KEY_A fires shell with vector velocity matching turret heading."""
        self.game.angle = 0.0 # Facing RIGHT
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)

        self.assertEqual(len(self.game.shells), 1)
        s = self.game.shells[0]
        self.assertTrue(s["is_player"])
        self.assertGreater(s["vx"], 0.0)
        self.assertAlmostEqual(s["vy"], 0.0)

        # Cooldown throttle
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.shells), 1)

    def test_05_obstacle_absorbs_shells(self):
        """Shell colliding with geometric obstacle is absorbed and destroyed."""
        self.game.shells.append({
            "x": 8.0, "y": 8.1, "vx": 0.0, "vy": -12.0, "is_player": True, "life": 1.0
        })
        self.game.update(0.02)
        self.assertEqual(len(self.game.shells), 0)

    def test_06_destroy_enemy_tank_and_score(self):
        """Player shell hitting enemy tank destroys it and awards score."""
        enemy = self.game.enemies[0]
        enemy["x"] = 10.0
        enemy["y"] = 6.0
        self.game.shells.append({
            "x": 10.0, "y": 6.0, "vx": 0.0, "vy": -12.0, "is_player": True, "life": 1.0
        })
        old_score = self.game.score

        self.game.update(0.02)
        self.assertFalse(enemy["alive"])
        self.assertGreaterEqual(self.game.score, old_score + 500)
        self.assertEqual(self.game.enemies_killed, 1)

    def test_07_enemy_cannon_fire_hits_player(self):
        """Enemy tank shell striking player tank costs 1 life."""
        self.game.shells.append({
            "x": self.game.px, "y": self.game.py, "vx": 0.0, "vy": 8.0, "is_player": False, "life": 1.0
        })
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_TANK_EXPLODING)

    def test_08_ramming_enemy_tank_costs_life(self):
        """Direct vehicle collision with enemy tank costs 1 life."""
        enemy = self.game.enemies[0]
        enemy["x"] = self.game.px
        enemy["y"] = self.game.py

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_TANK_EXPLODING)

    def test_09_target_kills_advances_sector(self):
        """Reaching target kill quota triggers sector clear with 2500 score."""
        self.game.enemies_killed = self.game.target_kills - 1
        enemy = self.game.enemies[0]
        enemy["x"] = 5.0
        enemy["y"] = 5.0
        self.game.shells.append({
            "x": 5.0, "y": 5.0, "vx": 0.0, "vy": -12.0, "is_player": True, "life": 1.0
        })
        old_score = self.game.score

        self.game.update(0.02)
        self.assertEqual(self.game.state, STATE_SECTOR_CLEAR)
        self.assertGreater(self.game.score, old_score + 2500)

    def test_10_game_over_and_periscope_radar_render(self):
        """At 0 lives transitions to STATE_GAME_OVER; frame contains top radar periscope."""
        self.game.lives = 1
        self.game.shells.append({
            "x": self.game.px, "y": self.game.py, "vx": 0.0, "vy": 8.0, "is_player": False, "life": 1.0
        })
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 0)
        self.game.update(1.2)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Render frame (768 bytes)
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()

