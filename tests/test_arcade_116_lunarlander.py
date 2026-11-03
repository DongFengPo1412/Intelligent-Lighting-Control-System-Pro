import unittest
from arcade.game_116_lunarlander import (
    Game116LunarLander,
    STATE_FLYING,
    STATE_TOUCHDOWN_SAFE,
    STATE_CRASHED,
    STATE_GAME_OVER,
    SAFE_MAX_VY,
    SAFE_MAX_VX,
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


class TestGame116LunarLander(unittest.TestCase):
    def setUp(self):
        self.game = Game116LunarLander()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 116)
        self.assertEqual(self.game.name, "月球着陆器")
        self.assertEqual(self.game.english_name, "Lunar Lander")
        self.assertEqual(self.game.release_year, 1979)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("月面重力", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.fuel, 450.0)
        self.assertEqual(self.game.px, 8.0)
        self.assertEqual(self.game.py, 1.5)
        self.assertEqual(self.game.vx, 0.0)
        self.assertEqual(self.game.vy, 0.0)
        self.assertFalse(self.game.thrusting)

    def test_gravity_acceleration(self):
        self.game.update(0.05, 0, 0)
        # vy should increase downward under gravity
        self.assertGreater(self.game.vy, 0.0)
        self.assertGreater(self.game.py, 1.5)

    def test_main_thruster_counteracts_gravity(self):
        init_fuel = self.game.fuel
        # Fire main thruster with KEY_A
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.thrusting)
        # Thrust exceeds gravity (net upward acceleration)
        self.assertLess(self.game.vy, 0.0)
        # Fuel consumed
        self.assertLess(self.game.fuel, init_fuel)

    def test_lateral_rcs_thrusters(self):
        init_fuel = self.game.fuel
        # Steer Left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.vx, 0.0)
        self.assertLess(self.game.fuel, init_fuel)

        # Steer Right twice
        self.game.update(0.05, KEY_RIGHT, 0)
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.vx, 0.0)

    def test_fuel_exhaustion(self):
        self.game.fuel = 0.0
        # Attempt to fire thrusters with empty tank
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.thrusting)
        # Should continue accelerating downwards purely under gravity
        self.assertGreater(self.game.vy, 0.0)

    def test_safe_soft_touchdown_on_pad_1x(self):
        # Position lander right above Pad 0 (col=2, surface y=14)
        self.game.set_position_and_velocity(x=2.0, y=13.0, vx=0.2, vy=0.8)
        init_score = self.game.score
        init_fuel = self.game.fuel

        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_TOUCHDOWN_SAFE)
        # 100 * 1 = 100 points
        self.assertEqual(self.game.score, init_score + 100)
        # Bonus fuel awarded
        self.assertGreater(self.game.fuel, init_fuel)

    def test_safe_soft_touchdown_on_crag_5x(self):
        # Position lander right above Pad 2 (col=13, surface y=12)
        self.game.set_position_and_velocity(x=13.0, y=11.0, vx=0.1, vy=0.6)
        init_score = self.game.score

        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_TOUCHDOWN_SAFE)
        # 100 * 5 = 500 points
        self.assertEqual(self.game.score, init_score + 500)

    def test_hard_landing_crash_speed_excess(self):
        # Land on Pad 0 with excessive vertical speed (vy = 2.5 > SAFE_MAX_VY)
        self.game.set_position_and_velocity(x=2.0, y=13.0, vx=0.0, vy=2.5)

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

    def test_craggy_rock_collision_crash(self):
        # Land on rugged crater peak (col=5, non-pad rocky terrain at y=11)
        self.game.set_position_and_velocity(x=5.0, y=10.0, vx=0.1, vy=0.5)

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)


if __name__ == "__main__":
    unittest.main()
