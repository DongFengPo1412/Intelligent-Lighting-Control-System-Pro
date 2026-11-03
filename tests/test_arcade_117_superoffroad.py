import unittest
import math
from arcade.game_117_superoffroad import (
    Game117SuperOffRoad,
    STATE_RACING,
    STATE_LAP_COMPLETE,
    STATE_RACE_FINISHED,
    STATE_GAME_OVER,
    TOTAL_LAPS,
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


class TestGame117SuperOffRoad(unittest.TestCase):
    def setUp(self):
        self.game = Game117SuperOffRoad()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 117)
        self.assertEqual(self.game.name, "超级越野赛车")
        self.assertEqual(self.game.english_name, "Super Off Road")
        self.assertEqual(self.game.release_year, 1989)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("泥地弯道漂移", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_RACING)
        self.assertEqual(self.game.nitro_charges, 3)
        self.assertEqual(self.game.player["laps_completed"], 0)
        self.assertEqual(self.game.player["x"], 3.0)
        self.assertEqual(self.game.player["y"], 13.0)
        self.assertEqual(self.game.player["speed"], 0.0)
        self.assertFalse(self.game.player["is_airborne"])

    def test_steering_rotation(self):
        # Rotate Left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.player["angle"], 0.0)

        # Rotate Right two ticks to exceed left rotation
        self.game.update(0.05, KEY_RIGHT, 0)
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.player["angle"], 0.0)

    def test_forward_acceleration_and_loose_dirt_friction(self):
        # Accelerate Forward
        self.game.update(0.05, KEY_UP, 0)
        self.assertGreater(self.game.player["speed"], 0.5)

        # Release throttle: dirt friction slows vehicle down
        spd1 = self.game.player["speed"]
        self.game.update(0.05, 0, 0)
        self.assertLess(self.game.player["speed"], spd1)

    def test_nitro_booster_activation(self):
        self.assertEqual(self.game.nitro_charges, 3)
        # Press A for Nitro
        self.game.update(0.05, KEY_A, 0)

        self.assertEqual(self.game.nitro_charges, 2)
        self.assertGreaterEqual(self.game.player["speed"], 10.0)
        self.assertGreater(self.game.nitro_timer, 0.5)

    def test_airborne_ramp_jump(self):
        # Place truck right on mud ramp at (8.0, 13.0) with forward speed
        self.game.player["x"] = 8.0
        self.game.player["y"] = 13.0
        self.game.player["speed"] = 5.0
        self.game.player["is_airborne"] = False

        self.game.update(0.01, 0, 0)

        self.assertTrue(self.game.player["is_airborne"])
        self.assertGreater(self.game.player["jump_vz"], 3.0)
        self.assertGreater(self.game.player["jump_z"], 0.1)

    def test_airborne_landing_gravity(self):
        # Truck is airborne
        self.game.player["is_airborne"] = True
        self.game.player["jump_z"] = 0.5
        self.game.player["jump_vz"] = 0.0

        # Step time until touchdown
        for _ in range(15):
            self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.player["is_airborne"])
        self.assertEqual(self.game.player["jump_z"], 0.0)

    def test_outer_barrier_and_infield_collision(self):
        # Head into west barrier (facing West, angle = pi)
        self.game.player["angle"] = math.pi
        self.game.player["x"] = 1.25
        self.game.player["speed"] = 4.0
        self.game.update(0.05, 0, 0)

        self.assertGreaterEqual(self.game.player["x"], 1.2)
        self.assertLess(self.game.player["speed"], 0.0) # Bounced back

    def test_collectible_pickup(self):
        # Drive onto Cash bag item at (2.0, 7.5)
        self.game.player["x"] = 2.0
        self.game.player["y"] = 7.5
        init_score = self.game.score

        self.game.update(0.01, 0, 0)

        self.assertFalse(self.game.items[1]["active"])
        self.assertEqual(self.game.score, init_score + 200)

    def test_lap_completion_and_race_finish(self):
        init_score = self.game.score
        # Simulate completing 3 laps
        self.game.player["current_waypoint"] = 3
        self.game.player["x"] = 2.5
        self.game.player["y"] = 13.0
        self.game.player["laps_completed"] = 2

        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.player["laps_completed"], 3)
        self.assertEqual(self.game.state, STATE_RACE_FINISHED)
        self.assertEqual(self.game.score, init_score + 300 + 1000)


if __name__ == "__main__":
    unittest.main()
