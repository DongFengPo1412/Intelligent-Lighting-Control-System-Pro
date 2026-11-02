import unittest
import math
from arcade.game_113_asteroids import (
    Game113Asteroids,
    STATE_PLAYING,
    STATE_PLAYER_EXPLODING,
    STATE_WAVE_CLEAR,
    STATE_GAME_OVER,
    wrap_coord,
    wrap_diff,
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


class TestGame113Asteroids(unittest.TestCase):
    def setUp(self):
        self.game = Game113Asteroids()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 113)
        self.assertEqual(self.game.name, "小行星")
        self.assertEqual(self.game.english_name, "Asteroids")
        self.assertEqual(self.game.release_year, 1979)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("牛顿惯性", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.wave, 1)
        self.assertEqual(self.game.px, 8.0)
        self.assertEqual(self.game.py, 8.0)
        self.assertAlmostEqual(self.game.angle, -math.pi / 2.0, places=2)
        active_asteroids = [a for a in self.game.asteroids if a["active"]]
        self.assertGreaterEqual(len(active_asteroids), 2)
        self.assertTrue(all(a["tier"] == 3 for a in active_asteroids))

    def test_ship_rotation(self):
        initial_angle = self.game.angle
        # Rotate Left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.angle, initial_angle)

        # Rotate Right past initial angle (two ticks to exceed the one left tick)
        self.game.update(0.05, KEY_RIGHT, 0)
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.angle, initial_angle)

    def test_ship_thrust_and_newtonian_inertia(self):
        # Facing UP (angle = -pi/2), thrust forward
        self.game.angle = -math.pi / 2.0
        self.game.update(0.05, KEY_UP, 0)

        self.assertLess(self.game.vy, -0.5)
        self.assertAlmostEqual(self.game.vx, 0.0, delta=0.01)

        # Release thrust: inertia keeps ship moving upward
        prev_y = self.game.py
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.py, prev_y)

    def test_toroidal_screen_wrap(self):
        self.game.px = 0.2
        self.game.vx = -10.0
        self.game.update(0.05, 0, 0)
        # Should wrap around left border to right edge
        self.assertGreater(self.game.px, 14.0)

    def test_laser_fire_in_heading(self):
        # Point right (angle = 0)
        self.game.angle = 0.0
        self.game.vx = 0.0
        self.game.vy = 0.0
        self.game.update(0.05, KEY_A, 0)

        active_bullets = [b for b in self.game.bullets if b["active"]]
        self.assertEqual(len(active_bullets), 1)
        self.assertGreater(active_bullets[0]["vx"], 20.0)
        self.assertAlmostEqual(active_bullets[0]["vy"], 0.0, delta=0.1)

    def test_tier_3_asteroid_split(self):
        # Target a Large tier 3 asteroid
        for a in self.game.asteroids:
            a["active"] = False

        self.game.asteroids[0]["active"] = True
        self.game.asteroids[0]["tier"] = 3
        self.game.asteroids[0]["x"] = 5.0
        self.game.asteroids[0]["y"] = 5.0
        self.game.asteroids[0]["vx"] = 2.0
        self.game.asteroids[0]["vy"] = 0.0

        init_score = self.game.score
        self.game.split_asteroid(0)

        self.assertEqual(self.game.score, init_score + 20)
        # Original Tier 3 is gone, exactly two Tier 2 asteroids spawned
        tier_3_count = sum(1 for a in self.game.asteroids if a["active"] and a["tier"] == 3)
        tier_2_count = sum(1 for a in self.game.asteroids if a["active"] and a["tier"] == 2)
        self.assertEqual(tier_3_count, 0)
        self.assertEqual(tier_2_count, 2)

    def test_tier_2_asteroid_split(self):
        # Clear all asteroids first
        for a in self.game.asteroids:
            a["active"] = False

        self.game.asteroids[0]["active"] = True
        self.game.asteroids[0]["tier"] = 2
        self.game.asteroids[0]["x"] = 6.0
        self.game.asteroids[0]["y"] = 6.0
        self.game.asteroids[0]["vx"] = 1.0
        self.game.asteroids[0]["vy"] = 1.0

        init_score = self.game.score
        self.game.split_asteroid(0)

        self.assertEqual(self.game.score, init_score + 50)
        # Original Tier 2 is gone, exactly two Tier 1 asteroids spawned
        tier_2_count = sum(1 for a in self.game.asteroids if a["active"] and a["tier"] == 2)
        tier_1_count = sum(1 for a in self.game.asteroids if a["active"] and a["tier"] == 1)
        self.assertEqual(tier_2_count, 0)
        self.assertEqual(tier_1_count, 2)

    def test_saucer_encounter_and_destruction(self):
        self.game.saucer["active"] = True
        self.game.saucer["x"] = 8.0
        self.game.saucer["y"] = 4.0

        # Bullet hitting saucer
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["x"] = 8.0
        self.game.bullets[0]["y"] = 4.0
        self.game.bullets[0]["vx"] = 0.0
        self.game.bullets[0]["vy"] = 0.0
        self.game.bullets[0]["life"] = 1.0

        init_score = self.game.score
        self.game.update(0.01, 0, 0)

        self.assertFalse(self.game.saucer["active"])
        self.assertEqual(self.game.score, init_score + 200)

    def test_hyperspace_jump(self):
        orig_px = self.game.px
        orig_py = self.game.py

        self.game.update(0.05, KEY_DOWN, 0)
        self.assertTrue(self.game.px != orig_px or self.game.py != orig_py)
        self.assertTrue(0.0 <= self.game.px < 16.0)
        self.assertTrue(0.0 <= self.game.py < 16.0)


if __name__ == "__main__":
    unittest.main()
