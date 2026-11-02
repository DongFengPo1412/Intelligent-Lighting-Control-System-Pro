import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_075_outrun import (
    Game075OutRun,
    STATE_START,
    STATE_PLAYING,
    STATE_CRASH,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade075OutRun(unittest.TestCase):
    def setUp(self):
        self.game = Game075OutRun()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 75)
        self.assertEqual(self.game.english_name, "Out Run")
        self.assertEqual(self.game.release_year, 1986)
        cart = ArcadeRegistry.get_cartridge(75)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game075OutRun)

    def test_steering_and_centrifugal_curve_pull(self):
        initial_x = self.game.car_x
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.car_x, initial_x)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertAlmostEqual(self.game.car_x, initial_x, delta=0.05)

    def test_acceleration_and_gear_shifting(self):
        self.assertFalse(self.game.high_gear)
        # Hold A in low gear
        for _ in range(5):
            self.game.update(0.1, KEY_A, 0)
        low_gear_speed = self.game.car_speed
        self.assertLessEqual(low_gear_speed, 105.0)

        # Shift to High Gear with Button B
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.high_gear)

        # Accelerate further in High Gear
        for _ in range(10):
            self.game.update(0.1, KEY_A, 0)
        self.assertGreater(self.game.car_speed, low_gear_speed)

    def test_radio_cassette_channel_cycle(self):
        self.assertEqual(self.game.radio_station, 0)  # Magical Sound Shower
        self.game.cycle_radio()
        self.assertEqual(self.game.radio_station, 1)  # Passing Breeze
        self.game.cycle_radio()
        self.assertEqual(self.game.radio_station, 2)  # Splash Wave
        self.game.cycle_radio()
        self.assertEqual(self.game.radio_station, 0)  # Wrap

    def test_offroad_grass_friction_deceleration(self):
        self.game.car_speed = 100.0
        self.game.car_x = 0.95  # In the grass curb!
        self.game.update(0.1, 0, 0)
        self.assertLess(self.game.car_speed, 100.0)

    def test_checkpoint_reach_and_time_extension(self):
        initial_time = self.game.time_remaining
        # Advance distance to checkpoint (1500m)
        self.game.stage_distance = 1500.0
        self.game.update_road(0.02)
        # Checkpoint passed: +25s extension and stage increment
        self.assertGreater(self.game.time_remaining, initial_time)
        self.assertEqual(self.game.current_stage, 2)

    def test_fork_junction_branch_detection(self):
        self.assertFalse(self.game.is_at_fork)
        self.game.stage_distance = 1360.0
        self.game.update_road(0.02)
        self.assertTrue(self.game.is_at_fork)

    def test_traffic_collision_crash(self):
        car = self.game.traffic[0]
        car["distance"] = 0.5
        car["x"] = self.game.car_x

        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_CRASH)
        self.assertEqual(self.game.car_speed, 0.0)

    def test_three_stage_completion_victory(self):
        self.game.current_stage = 3
        self.game.stage_distance = 1500.0
        self.game.update_road(0.02)
        self.assertEqual(self.game.current_stage, 4)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 5000)

    def test_render_framebuffer_and_status(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 75)
        self.assertEqual(status["name"], "欧陆赛车")


if __name__ == "__main__":
    unittest.main()
