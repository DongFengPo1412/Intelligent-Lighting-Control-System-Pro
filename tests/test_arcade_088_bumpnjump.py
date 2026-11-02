import unittest
import math
from arcade.game_088_bumpnjump import (
    Game088BumpNJump,
    STATE_DRIVING,
    STATE_CRASHED,
    STATE_LEVEL_CLEAR,
    STATE_GAME_OVER,
    ENEMY_CAR,
    ENEMY_TRUCK,
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


class TestGame088BumpNJump(unittest.TestCase):
    def setUp(self):
        self.game = Game088BumpNJump()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 88)
        self.assertEqual(self.game.name, "疯狂碰碰车")
        self.assertEqual(self.game.english_name, "Bump 'n' Jump")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("高空飞跃下压砸扁敌车", self.game.core_mechanic)

    def test_throttle_and_brake(self):
        initial_speed = self.game.speed
        self.assertEqual(initial_speed, 110.0)

        # Accelerate with KEY_UP
        self.game.update(0.1, KEY_UP)
        self.assertGreater(self.game.speed, initial_speed)

        # Brake with KEY_DOWN
        self.game.update(0.5, KEY_DOWN)
        self.assertLess(self.game.speed, initial_speed)

    def test_lateral_steering_and_guard_rail_bounce(self):
        init_x = self.game.px
        # Steer left
        self.game.update(0.1, KEY_LEFT)
        self.assertLess(self.game.px, init_x)

        # Steer all the way left to guard rail
        for _ in range(30):
            self.game.update(0.05, KEY_LEFT)
        # Clamped to rail >= 2.2
        self.assertGreaterEqual(self.game.px, 2.2)
        self.assertGreater(self.game.bump_vx, 0.0)  # Bounced rightward

    def test_jump_requires_speed(self):
        # Slow down below 100 km/h
        self.game.speed = 80.0
        self.game.update(0.05, KEY_A)
        self.assertFalse(self.game.is_jumping)
        self.assertEqual(self.game.jump_z, 0.0)

        # Speed up to 120 km/h and press KEY_A
        self.game.speed = 120.0
        self.game.update(0.05, 0)
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.is_jumping)
        self.assertGreater(self.game.jump_z, 0.0)
        self.assertGreater(self.game.jump_vz, 0.0)

    def test_jump_airborne_trajectory(self):
        self.game.speed = 130.0
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.is_jumping)

        # Check flight progress
        for _ in range(8):
            self.game.update(0.05, 0)
        self.assertGreater(self.game.jump_z, 0.5)

        # Simulate full arc until landing
        for _ in range(40):
            self.game.update(0.05, 0)
        self.assertFalse(self.game.is_jumping)
        self.assertEqual(self.game.jump_z, 0.0)

    def test_jump_crush_enemy(self):
        # Position enemy directly in front of player
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = self.game.px
        self.game.enemies[0]["y"] = self.game.py
        init_score = self.game.score
        init_crush = self.game.crushed_count

        # Jump high
        self.game.speed = 120.0
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.is_jumping)

        # Set falling near landing directly on enemy
        self.game.jump_vz = -2.0
        self.game.jump_z = 0.8
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = self.game.px
        self.game.enemies[0]["y"] = self.game.py

        self.game.update(0.05, 0)
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.score, init_score + 200)
        self.assertEqual(self.game.crushed_count, init_crush + 1)
        # Should bounce up after crushing
        self.assertGreater(self.game.jump_vz, 0.0)

    def test_ground_bump_shove(self):
        # Ground bump: player touches enemy
        self.game.is_jumping = False
        self.game.jump_z = 0.0
        self.game.px = 6.0
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = 6.8
        self.game.enemies[0]["y"] = self.game.py
        init_enemy_x = self.game.enemies[0]["x"]
        init_score = self.game.score

        self.game.update(0.05, 0)
        # Player pushed left, enemy pushed right
        self.assertLess(self.game.px, 6.0)
        self.assertGreater(self.game.enemies[0]["x"], init_enemy_x)

        # Shove enemy off road past 12.8
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = 12.6
        self.game.px = 12.0
        self.game.update(0.05, 0)
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.score, init_score + 100)

    def test_lateral_bump_boost_button_b(self):
        init_score = self.game.score
        self.game.update(0.05, KEY_B | KEY_RIGHT)
        self.assertGreater(self.game.bump_vx, 5.0)
        self.assertEqual(self.game.score, init_score + 10)
        self.assertGreater(self.game.bump_boost_cooldown, 0.0)

    def test_water_gap_leap_vs_fall(self):
        # Case 1: Grounded car falls into water gap
        self.game.is_jumping = False
        self.game.jump_z = 0.0
        self.game.water_gap_dist = 12.0  # spans player py=13
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

        # Case 2: Airborne car leaps safely across water gap
        self.game.reset()
        self.game.is_jumping = True
        self.game.jump_z = 1.2
        self.game.water_gap_dist = 12.0
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_DRIVING)

    def test_stage_clear_and_render(self):
        self.game.distance = self.game.stage_length - 0.1
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_LEVEL_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

        # Test render framebuffer
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 88)
        self.assertEqual(status["state"], STATE_LEVEL_CLEAR)


if __name__ == "__main__":
    unittest.main()
