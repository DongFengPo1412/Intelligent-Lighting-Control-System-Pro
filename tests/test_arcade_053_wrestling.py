import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_053_wrestling import (
    Game053Wrestling,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    MODE_NEUTRAL,
    MODE_ROPE_BOUNCE,
    MODE_GRAPPLE,
    MODE_DOWNED,
    MODE_PINNING,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade053Wrestling(unittest.TestCase):
    def setUp(self):
        self.game = Game053Wrestling()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 53)
        self.assertEqual(self.game.english_name, "The Main Event")
        self.assertEqual(self.game.release_year, 1988)
        cart = ArcadeRegistry.get_cartridge(53)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game053Wrestling)

    def test_neutral_movement_and_ring_bounds(self):
        # Move up/down within ring
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.player_y, 7.5)
        self.assertGreaterEqual(self.game.player_y, 2.5)

    def test_rope_bounce_physics(self):
        # Position player near left rope and move left
        self.game.player_x = 2.6
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.player_mode, MODE_ROPE_BOUNCE)
        self.assertGreater(self.game.player_vx, 0.0)  # Rebounding to the right

    def test_flying_clothesline_knockdown(self):
        self.game.player_x = 3.0
        self.game.player_y = 7.5
        self.game.player_vx = 12.0
        self.game.player_mode = MODE_ROPE_BOUNCE

        self.game.opp_x = 3.5
        self.game.opp_y = 7.5
        self.game.opp_mode = MODE_NEUTRAL
        self.game.opp_stamina = 100

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.opp_mode, MODE_DOWNED)
        self.assertEqual(self.game.opp_stamina, 70)
        self.assertGreater(self.game.score, 0)

    def test_collar_elbow_grapple_initiation(self):
        self.game.player_x = 7.0
        self.game.player_y = 7.0
        self.game.opp_x = 7.5
        self.game.opp_y = 7.0
        self.game.player_mode = MODE_NEUTRAL
        self.game.opp_mode = MODE_NEUTRAL

        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(self.game.player_mode, MODE_GRAPPLE)
        self.assertEqual(self.game.opp_mode, MODE_GRAPPLE)

    def test_grapple_bodyslam_victory(self):
        self.game.player_mode = MODE_GRAPPLE
        self.game.opp_mode = MODE_GRAPPLE
        self.game.grapple_advantage = 2
        self.game.opp_stamina = 100

        # Press A to push advantage to 3
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(self.game.opp_mode, MODE_DOWNED)
        self.assertEqual(self.game.player_mode, MODE_NEUTRAL)
        self.assertEqual(self.game.opp_stamina, 75)

    def test_pin_fall_3_count_victory(self):
        self.game.player_x = 7.0
        self.game.player_y = 7.0
        self.game.opp_x = 7.2
        self.game.opp_y = 7.0
        self.game.opp_mode = MODE_DOWNED
        self.game.opp_stamina = 10  # Depleted stamina so cannot kick out

        # Button B initiates pin
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(self.game.player_mode, MODE_PINNING)

        # Advance referee count: 3 counts of 0.8s = 2.4s
        for _ in range(35):
            self.game.update(0.1, 0, 0)

        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_opponent_kickout_with_high_stamina(self):
        self.game.opp_mode = MODE_DOWNED
        self.game.opp_stamina = 80  # Full stamina allows kick out!
        self.game.player_mode = MODE_PINNING
        self.game.pin_timer = 0.79

        # Trigger first count tick
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.player_mode, MODE_NEUTRAL)  # Kicked out!
        self.assertEqual(self.game.opp_mode, MODE_NEUTRAL)

    def test_player_pinned_defeat(self):
        self.game.player_mode = MODE_DOWNED
        self.game.player_stamina = 10
        self.game.opp_mode = MODE_PINNING

        # 3 counts against player
        for _ in range(35):
            self.game.update(0.1, 0, 0)

        self.assertEqual(self.game.state, STATE_DEAD)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 53)
        self.assertEqual(status["state"], STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
