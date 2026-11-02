import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_068_metalgear import (
    Game068MetalGear,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    ALERT_NORMAL,
    ALERT_CAUTION,
    ALERT_EVASION,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade068MetalGear(unittest.TestCase):
    def setUp(self):
        self.game = Game068MetalGear()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 68)
        self.assertEqual(self.game.english_name, "Metal Gear")
        self.assertEqual(self.game.release_year, 1987)
        cart = ArcadeRegistry.get_cartridge(68)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game068MetalGear)

    def test_directional_movement_and_wall_collision(self):
        initial_y = self.game.py
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.py, initial_y)
        self.assertEqual(self.game.player_dir, 0)

        # Attempt to walk through crate (4, 5)
        self.game.px = 3.0
        self.game.py = 5.0
        self.game.update(0.1, KEY_RIGHT, 0)
        # Should be blocked
        self.assertLessEqual(self.game.px, 4.0)

    def test_toggle_cardboard_box(self):
        self.assertFalse(self.game.in_box)
        # Button B toggles box
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.in_box)

        # Toggle back off
        self.game.update(0.02, KEY_B, 0)
        self.assertFalse(self.game.in_box)

    def test_fire_silenced_dart(self):
        self.assertEqual(len(self.game.darts), 0)
        self.game.player_dir = 0  # Facing UP
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.darts), 1)
        self.assertLess(self.game.darts[0]["vy"], 0)

    def test_stealth_line_of_sight_detection(self):
        # Position guard at (5, 5) facing RIGHT towards (8, 5)
        guard = self.game.guards[0]
        guard["x"] = 5.0
        guard["y"] = 5.0
        guard["dir"] = 1  # Right
        guard["alert"] = False

        # Position exposed Snake at (7, 5)
        self.game.px = 7.0
        self.game.py = 5.0
        self.game.in_box = False

        self.game.check_line_of_sight()
        self.assertTrue(guard["alert"])
        self.assertEqual(self.game.alert_level, ALERT_EVASION)

    def test_cardboard_box_fools_guard_when_stationary(self):
        guard = self.game.guards[0]
        guard["x"] = 5.0
        guard["y"] = 5.0
        guard["dir"] = 1  # Right
        guard["alert"] = False

        # Position Snake at (7, 5) INSIDE CARDBOARD BOX and stationary
        self.game.px = 7.0
        self.game.py = 5.0
        self.game.in_box = True
        self.game.is_moving = False

        self.game.check_line_of_sight()
        # Guard thinks it's an ordinary box!
        self.assertFalse(guard["alert"])
        self.assertEqual(self.game.alert_level, ALERT_NORMAL)

    def test_moving_in_box_triggers_alert(self):
        guard = self.game.guards[0]
        guard["x"] = 5.0
        guard["y"] = 5.0
        guard["dir"] = 1  # Right
        guard["alert"] = False

        # Snake moves right in front of guard while inside box!
        self.game.px = 7.0
        self.game.py = 5.0
        self.game.in_box = True
        self.game.is_moving = True

        self.game.check_line_of_sight()
        self.assertTrue(guard["alert"])
        self.assertEqual(self.game.alert_level, ALERT_EVASION)

    def test_silenced_dart_neutralizes_guard(self):
        guard = self.game.guards[0]
        guard["x"] = 8.0
        guard["y"] = 8.0
        guard["active"] = True
        guard["alert"] = False

        self.game.darts.append({"x": 8.0, "y": 8.1, "vx": 0.0, "vy": -10.0, "active": True})
        self.game.check_collisions()

        self.assertFalse(guard["active"])
        self.assertEqual(self.game.guards_neutralized, 1)
        self.assertGreaterEqual(self.game.score, 400)  # Silent stealth bonus!

    def test_cqc_flanking_stealth_takedown(self):
        guard = self.game.guards[1]
        guard["x"] = 6.0
        guard["y"] = 6.0
        guard["active"] = True
        guard["alert"] = False

        # Snake walks up right behind guard
        self.game.px = 6.0
        self.game.py = 6.2
        self.game.check_collisions()

        self.assertFalse(guard["active"])
        self.assertEqual(self.game.guards_neutralized, 1)
        self.assertGreaterEqual(self.game.score, 500)

    def test_keycard_pickup_and_nuclear_terminal_victory(self):
        self.assertFalse(self.game.has_keycard)

        # Walk to keycard depot at (13, 13)
        self.game.px = 13.0
        self.game.py = 13.0
        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.has_keycard)

        # Walk through security door (7.5, 2) to terminal (7.5, 1.2)
        self.game.px = 7.5
        self.game.py = 1.2
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
