import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_079_subroc3d import (
    Game079SubRoc3D,
    STATE_PLAYING,
    STATE_PLAYER_HIT,
    STATE_GAME_OVER,
    STATE_VICTORY,
    ZONE_AIR,
    ZONE_SURFACE,
    ZONE_DEPTH,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)


class TestGame079SubRoc3D(unittest.TestCase):
    def setUp(self):
        self.game = Game079SubRoc3D()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 79)
        self.assertEqual(self.game.name, "影子潜艇")
        self.assertEqual(self.game.english_name, "SubRoc-3D")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("潜望镜伪3D立体纵深射击", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["score"], 0)
        self.assertEqual(self.game.cx, 7.5)
        self.assertEqual(self.game.cy, 7.5)
        self.assertGreaterEqual(status["active_targets"], 1)

    def test_crosshair_movement(self):
        # Move crosshair left and up
        self.game.update(0.1, KEY_LEFT | KEY_UP, 0)
        self.assertLess(self.game.cx, 7.5)
        self.assertLess(self.game.cy, 7.5)

        # Move far right - bounded by 14.0
        for _ in range(30):
            self.game.update(0.1, KEY_RIGHT, KEY_RIGHT)
        self.assertLessEqual(self.game.cx, 14.0)

    def test_fire_torpedo_mechanic(self):
        self.assertEqual(len(self.game.projectiles), 0)
        # Press A for torpedo
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.projectiles), 1)
        p = self.game.projectiles[0]
        self.assertFalse(p["is_air_missile"])
        self.assertGreaterEqual(p["y"], 7.0)

    def test_fire_air_missile_mechanic(self):
        self.game.projectiles = []
        # Press B for air missile
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(len(self.game.projectiles), 1)
        p = self.game.projectiles[0]
        self.assertTrue(p["is_air_missile"])
        self.assertLessEqual(p["y"], 7.0)

    def test_torpedo_hits_surface_ship(self):
        self.game.targets = [{
            "x": 8.0,
            "y": 7.0,
            "z": 4.0,
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0,
            "zone": ZONE_SURFACE,
            "active": True,
        }]
        self.game.cx = 8.0
        self.game.cy = 7.0

        # Launch torpedo
        self.game.fire_torpedo()
        self.assertEqual(len(self.game.projectiles), 1)

        # Manually advance torpedo depth z close to 4.0
        self.game.projectiles[0]["z"] = 3.8
        old_score = self.game.score

        self.game.check_hits()
        self.assertFalse(self.game.targets[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_air_missile_hits_fighter(self):
        self.game.targets = [{
            "x": 6.0,
            "y": 3.0,
            "z": 5.0,
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0,
            "zone": ZONE_AIR,
            "active": True,
        }]
        self.game.cx = 6.0
        self.game.cy = 3.0

        self.game.fire_air_missile()
        self.game.projectiles[0]["z"] = 4.8
        old_score = self.game.score

        self.game.check_hits()
        self.assertFalse(self.game.targets[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_weapon_incompatibility(self):
        # Surface ship vs Air Missile
        self.game.targets = [{
            "x": 8.0,
            "y": 7.0,
            "z": 4.0,
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0,
            "zone": ZONE_SURFACE,
            "active": True,
        }]
        self.game.projectiles = [{
            "x": 8.0,
            "y": 7.0,
            "z": 4.0,
            "vz": 14.0,
            "is_air_missile": True,  # Air missile cannot destroy surface vessel!
            "active": True,
        }]

        self.game.check_hits()
        # Surface ship remains active
        self.assertTrue(self.game.targets[0]["active"])

    def test_enemy_impact_damage(self):
        self.game.targets = [{
            "x": 7.5,
            "y": 7.5,
            "z": 1.3,
            "vx": 0.0,
            "vy": 0.0,
            "vz": -2.0,  # Moves past 1.2
            "zone": ZONE_SURFACE,
            "active": True,
        }]

        self.game.update(0.1, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_HIT)
        self.assertEqual(self.game.lives, 2)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
