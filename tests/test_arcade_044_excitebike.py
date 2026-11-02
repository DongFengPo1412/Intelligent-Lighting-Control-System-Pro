"""
Comprehensive Unit Tests for Arcade Cartridge #044: 越野机车 (Excitebike 1984 / Nintendo)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_044_excitebike import (
    Game044Excitebike,
    STATE_START,
    STATE_PLAYING,
    STATE_CRASH,
    STATE_OVERHEAT,
    STATE_VICTORY,
    OBS_SMALL_RAMP,
    OBS_BIG_RAMP,
    OBS_MUD_PUDDLE,
    OBS_COOLING_STRIP,
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


class TestArcade044Excitebike(unittest.TestCase):
    def setUp(self):
        self.game = Game044Excitebike()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 44)
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "越野机车")
        self.assertIn("Excitebike", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(44)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game044Excitebike)

    def test_initial_state_and_track(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.speed, 0.0)
        self.assertEqual(self.game.lane, 1)
        self.assertEqual(self.game.altitude, 0.0)
        self.assertEqual(self.game.world_x, 0.0)
        self.assertFalse(self.game.is_airborne)
        self.assertEqual(len(self.game.obstacles), 16)

    def test_lane_switching_on_ground(self):
        self.assertEqual(self.game.lane, 1)

        # Switch Up to lane 0
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.lane, 0)

        # Cannot switch above lane 0
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.lane, 0)

        # Switch Down to lane 1, 2, 3
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.lane, 1)
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.lane, 2)
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.lane, 3)

        # Cannot switch below lane 3
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.lane, 3)

    def test_normal_throttle_and_acceleration(self):
        self.assertEqual(self.game.speed, 0.0)
        # Hold KEY_A for normal throttle
        for _ in range(10):
            self.game.update(0.05, KEY_A, 0)

        self.assertGreater(self.game.speed, 1.0)
        self.assertGreater(self.game.world_x, 0.0)
        self.assertGreater(self.game.engine_temp, 0.0)
        self.assertLess(self.game.engine_temp, 50.0)

    def test_turbo_boost_and_engine_overheat(self):
        # Manually set engine temp near threshold
        self.game.engine_temp = 98.0
        self.game.speed = 10.0

        # Press Turbo KEY_B
        self.game.update(0.1, KEY_B, 0)
        self.assertEqual(self.game.state, STATE_OVERHEAT)
        self.assertEqual(self.game.speed, 0.0)

    def test_ramp_launch_and_airborne_flight(self):
        # Place small ramp directly in front of player
        self.game.obstacles = [{"world_x": 1.0, "lane": 1, "type": OBS_SMALL_RAMP}]
        self.game.world_x = 0.9
        self.game.lane = 1
        self.game.speed = 10.0

        self.game.check_terrain_collisions()
        self.assertTrue(self.game.is_airborne)
        self.assertGreater(self.game.vertical_vy, 0.0)
        self.assertGreater(self.game.altitude, 0.0)

    def test_airborne_pitch_adjustment_and_crash(self):
        self.game.is_airborne = True
        self.game.altitude = 8.0
        self.game.vertical_vy = 6.0
        self.game.pitch_angle = 0.0

        # Hold KEY_RIGHT in air to dive nose-first
        for _ in range(5):
            self.game.update(0.05, KEY_RIGHT, 0)

        self.assertGreater(self.game.pitch_angle, 0.42)

        # Advance until landing
        while self.game.is_airborne:
            self.game.update(0.05, 0, 0)

        # Landed nose-first -> CRASH!
        self.assertEqual(self.game.state, STATE_CRASH)
        self.assertEqual(self.game.speed, 0.0)

    def test_airborne_level_landing_bonus(self):
        self.game.is_airborne = True
        self.game.altitude = 0.1
        self.game.vertical_vy = -5.0
        self.game.pitch_angle = 0.0  # Perfect level pitch
        self.game.speed = 10.0

        prev_score = self.game.score
        self.game.update(0.05, 0, 0)

        # Touchdown smooth landing
        self.assertFalse(self.game.is_airborne)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertGreater(self.game.score, prev_score)

    def test_cooling_strip_resets_engine_temp(self):
        self.game.engine_temp = 75.0
        self.game.obstacles = [{"world_x": 5.0, "lane": 1, "type": OBS_COOLING_STRIP}]
        self.game.world_x = 5.0
        self.game.lane = 1

        self.game.check_terrain_collisions()
        self.assertEqual(self.game.engine_temp, 0.0)

    def test_mud_puddle_slowdown(self):
        self.game.speed = 15.0
        self.game.obstacles = [{"world_x": 5.0, "lane": 1, "type": OBS_MUD_PUDDLE}]
        self.game.world_x = 5.0
        self.game.lane = 1

        self.game.check_terrain_collisions()
        self.assertLess(self.game.speed, 7.0)

    def test_track_finish_victory(self):
        self.game.world_x = 119.5
        self.game.speed = 10.0
        self.game.update(0.1, KEY_A, 0)

        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 2000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check bike rendered at px=3, py=9 (lane 1 on ground)
        idx = (9 * 16 + 3) * 3
        self.assertEqual(fb[idx + 0], 231)
        self.assertEqual(fb[idx + 1], 76)
        self.assertEqual(fb[idx + 2], 60)


if __name__ == "__main__":
    unittest.main()
