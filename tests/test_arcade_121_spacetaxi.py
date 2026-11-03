import unittest
from arcade.game_121_spacetaxi import (
    Game121SpaceTaxi,
    STATE_FLYING,
    STATE_BOARDING,
    STATE_FARE_PAID,
    STATE_CRASHED,
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


class TestGame121SpaceTaxi(unittest.TestCase):
    def setUp(self):
        self.game = Game121SpaceTaxi()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 121)
        self.assertEqual(self.game.name, "太空出租车")
        self.assertEqual(self.game.english_name, "Space Taxi")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("反重力穿梭对接", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.fuel, 100.0)
        self.assertTrue(self.game.gear_deployed)
        self.assertFalse(self.game.passenger["in_taxi"])

    def test_gravity_and_thrusters(self):
        # Position taxi in mid-air
        self.game.set_position_and_velocity(x=5.0, y=3.0, vx=0.0, vy=0.0)

        # Gravity accelerates vy downwards
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.vy, 0.0)

        # Up thruster overcomes gravity
        init_fuel = self.game.fuel
        self.game.update(0.05, KEY_UP, 0)
        self.assertLess(self.game.fuel, init_fuel)

    def test_toggle_landing_gear(self):
        # Position taxi in mid-air so gear retraction doesn't crash on pad
        self.game.set_position_and_velocity(x=5.0, y=3.0, vx=0.0, vy=0.0)
        self.assertTrue(self.game.gear_deployed)

        # Toggle with Key B
        self.game.update(0.05, KEY_B, 0)
        self.assertFalse(self.game.gear_deployed)

        # Toggle back
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.gear_deployed)

    def test_gear_retracted_landing_crashes(self):
        # Retract gear
        self.game.gear_deployed = False
        # Descend onto Pad 1 at (2.0, 13.0) with gentle speed
        self.game.set_position_and_velocity(x=2.0, y=13.0, vx=0.0, vy=0.5)

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

    def test_safe_docking_and_passenger_boarding(self):
        # Gear deployed, soft landing on Pad 1 (where passenger waits)
        self.game.gear_deployed = True
        self.game.passenger["current_pad"] = 1
        self.game.set_position_and_velocity(x=2.0, y=13.0, vx=0.1, vy=0.6)

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_BOARDING)

        # Step through boarding timer
        for _ in range(30):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_FLYING)
        self.assertTrue(self.game.passenger["in_taxi"])

    def test_delivery_and_fare_payment(self):
        # Passenger in taxi, destination Pad 2 (at x=13.0, y=14.0)
        self.game.passenger["in_taxi"] = True
        self.game.passenger["target_pad"] = 2
        self.game.gear_deployed = True
        self.game.set_position_and_velocity(x=13.0, y=13.0, vx=0.0, vy=0.5)

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_FARE_PAID)
        self.assertGreaterEqual(self.game.score, init_score + 250)
        self.assertEqual(self.game.fares_completed, 1)

    def test_skyscraper_core_collision(self):
        # Fly into center skyscraper core (x=7.5, y=8.0)
        self.game.set_position_and_velocity(x=7.5, y=8.0, vx=0.0, vy=0.0)

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

    def test_excess_landing_speed_crash(self):
        # Landing on Pad 1 with excessive vertical velocity (vy = 2.5 > 1.4)
        self.game.gear_deployed = True
        self.game.set_position_and_velocity(x=2.0, y=13.0, vx=0.0, vy=2.5)

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

    def test_fuel_burn_and_depletion(self):
        # Position taxi in mid-air
        self.game.set_position_and_velocity(x=5.0, y=3.0, vx=0.0, vy=0.0)
        self.game.fuel = 0.0
        init_vy = self.game.vy

        # Thrusters ineffective with 0 fuel
        self.game.update(0.05, KEY_UP, 0)
        # Still falling with downward acceleration
        self.assertGreater(self.game.vy, init_vy)


if __name__ == "__main__":
    unittest.main()
