import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_082_chasehq import (
    Game082ChaseHQ,
    STATE_APPROACH,
    STATE_PURSUIT,
    STATE_ARRESTED,
    STATE_TIME_UP,
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


class TestGame082ChaseHQ(unittest.TestCase):
    def setUp(self):
        self.game = Game082ChaseHQ()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 82)
        self.assertEqual(self.game.name, "烈火特警")
        self.assertEqual(self.game.english_name, "Chase H.Q.")
        self.assertEqual(self.game.release_year, 1988)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("连续猛烈撞击截停", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_APPROACH)
        self.assertEqual(status["turbos_left"], 3)
        self.assertEqual(status["time_remaining"], 45.0)
        self.assertEqual(status["distance_to_suspect"], 100.0)
        self.assertEqual(self.game.px, 7.5)
        self.assertEqual(self.game.py, 13.0)

    def test_steering_controls(self):
        # Steer left
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.px, 7.5)

        # Steer right
        self.game.update(0.2, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 7.0)

    def test_turbo_nitro_boost(self):
        self.assertEqual(self.game.turbos_left, 3)
        # Press B for turbo
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.turbos_left, 2)
        self.assertGreater(self.game.turbo_timer, 0.0)
        self.assertEqual(self.game.p_speed, 20.0)

    def test_approach_transition_to_pursuit(self):
        self.game.distance_to_suspect = 0.5
        old_time = self.game.time_remaining

        # Advance to close the gap
        self.game.update(0.1, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_PURSUIT)
        self.assertGreater(self.game.time_remaining, old_time)

    def test_ramming_suspect_car(self):
        self.game.state = STATE_PURSUIT
        self.game.px = 7.5
        self.game.py = 7.0
        self.game.sx = 7.5
        self.game.sy = 7.0  # Align coordinates for ram

        old_dmg = self.game.suspect_damage
        self.game.check_ramming()
        self.assertEqual(self.game.suspect_damage, old_dmg + 15.0)
        self.assertGreater(self.game.score, 0)

    def test_turbo_ramming_extra_damage(self):
        self.game.state = STATE_PURSUIT
        self.game.turbo_timer = 2.0
        self.game.px = 7.5
        self.game.py = 7.0
        self.game.sx = 7.5
        self.game.sy = 7.0

        old_dmg = self.game.suspect_damage
        self.game.check_ramming()
        self.assertEqual(self.game.suspect_damage, old_dmg + 25.0)

    def test_suspect_apprehended_victory(self):
        self.game.state = STATE_PURSUIT
        self.game.suspect_damage = 90.0
        self.game.px = 7.5
        self.game.py = 7.0
        self.game.sx = 7.5
        self.game.sy = 7.0

        # One final ramming blow!
        self.game.check_ramming()
        self.assertEqual(self.game.suspect_damage, 100.0)
        self.assertEqual(self.game.state, STATE_ARRESTED)
        self.assertGreater(self.game.score, 10000)

    def test_civilian_traffic_crash_penalty(self):
        self.game.turbo_timer = 2.0
        self.game.traffic = [{
            "x": self.game.px,
            "y": self.game.py,
            "speed": 5.0,
            "active": True,
        }]

        self.game.update(0.05, 0, 0)
        # Crash slows down and cancels turbo!
        self.assertEqual(self.game.turbo_timer, 0.0)
        self.assertEqual(self.game.p_speed, 4.0)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
