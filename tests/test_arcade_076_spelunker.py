import unittest
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_076_spelunker import (
    Game076Spelunker,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
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


class TestGame076Spelunker(unittest.TestCase):
    def setUp(self):
        self.game = Game076Spelunker()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 76)
        self.assertEqual(self.game.name, "经典古墓探险")
        self.assertEqual(self.game.english_name, "Spelunker")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("极限下落高度限制", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["flares_count"], 3)
        self.assertEqual(status["oxygen"], 100.0)
        self.assertEqual(self.game.px, 2.0)
        self.assertEqual(self.game.py, 4.0)
        self.assertFalse(self.game.on_rope)

    def test_horizontal_movement(self):
        start_x = self.game.px
        # Press right for 0.2s
        self.game.update(0.2, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, start_x)
        self.assertEqual(self.game.facing, 1)

        # Press left for 0.2s
        self.game.update(0.2, KEY_LEFT, 0)
        self.assertEqual(self.game.facing, -1)

    def test_rope_climbing(self):
        # Walk player to rope at x=5.0
        self.game.px = 5.0
        self.game.py = 6.0
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertTrue(self.game.on_rope)
        
        # Climb down
        old_y = self.game.py
        self.game.update(0.2, KEY_DOWN, KEY_DOWN)
        self.assertGreater(self.game.py, old_y)

        # Climb up
        self.game.update(0.2, KEY_UP, KEY_DOWN)
        self.assertLess(self.game.py, old_y + 0.7)

    def test_normal_jump_and_safe_landing(self):
        # Player is on platform at py=4.0
        self.game.px = 2.0
        self.game.py = 4.0
        self.game.fall_start_y = 4.0
        self.game.on_ground = True

        # Jump
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.pvy, 0.0)

        # Let player land back on same platform
        for _ in range(30):
            self.game.update(0.05, 0, 0)
            if self.game.on_ground:
                break

        self.assertTrue(self.game.on_ground)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

    def test_fatal_fall_fragility_death(self):
        # Spelunker's famous death: fall distance > 2.2
        # Position in mid air falling from y=4.0 to y=9.0 (delta = 5.0)
        self.game.fall_start_y = 4.0
        self.game.px = 4.0  # above middle platform at y=9.0
        self.game.py = 8.5
        self.game.pvy = 5.0
        self.game.on_ground = False
        self.game.on_rope = False

        # Next tick will land on y=9.0, delta is 5.0 > 2.2 -> death!
        self.game.update(0.15, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_flare_projectile_and_ghost_vaporization(self):
        self.game.flares_count = 2
        self.game.px = 8.0
        self.game.py = 8.0
        
        # Position ghost right above player
        self.game.ghosts = [{"x": 8.0, "y": 6.0, "vx": 0, "vy": 0, "active": True}]
        
        old_score = self.game.score
        # Fire flare
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.flares_count, 1)
        self.assertEqual(len(self.game.flares), 1)

        # Update flare physics to reach ghost
        self.game.update(0.1, 0, KEY_B)
        self.assertFalse(self.game.ghosts[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_oxygen_depletion_death(self):
        self.game.oxygen = 0.5
        self.game.update(0.5, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_item_collection_and_cavern_victory(self):
        # Disable ghosts to test collection & exit cleanly
        for g in self.game.ghosts:
            g["active"] = False

        # Collect key (item index 2)
        key_item = self.game.items[2]
        self.game.px = key_item["x"]
        self.game.py = key_item["y"]
        self.game.fall_start_y = key_item["y"]
        self.game.update(0.05, 0, 0)
        self.assertFalse(key_item["active"])

        # Reach exit at (14.0, 14.0)
        self.game.px = 14.0
        self.game.py = 14.0
        self.game.fall_start_y = 14.0
        self.game.pvy = 0.0
        self.game.on_ground = True
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 4000)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
