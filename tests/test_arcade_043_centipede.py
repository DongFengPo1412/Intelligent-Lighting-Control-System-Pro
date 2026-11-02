"""
Comprehensive Unit Tests for Arcade Cartridge #043: 蜈蚣大战 (Centipede 1980 / Atari)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_043_centipede import (
    Game043Centipede,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
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


class TestArcade043Centipede(unittest.TestCase):
    def setUp(self):
        self.game = Game043Centipede()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 43)
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "蜈蚣大战")
        self.assertIn("Centipede", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(43)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game043Centipede)

    def test_initial_state_and_layout(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.get_active_segment_count(), 8)
        self.assertTrue(self.game.segments[0]["is_head"])
        self.assertFalse(self.game.segments[1]["is_head"])
        self.assertGreater(len(self.game.mushrooms), 5)
        self.assertEqual(self.game.player_y, 14.0)

    def test_player_movement_and_safety_zone_bounds(self):
        # Move up towards top screen - should be clamped to y >= 11.0
        for _ in range(20):
            self.game.update(0.1, KEY_UP, 0)
        self.assertGreaterEqual(self.game.player_y, 11.0)

        # Move down - clamped to y <= 15.0
        for _ in range(20):
            self.game.update(0.1, KEY_DOWN, 0)
        self.assertLessEqual(self.game.player_y, 15.0)

        # Move left - clamped to x >= 0.0
        for _ in range(20):
            self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.player_x, 0.0)

        # Move right - clamped to x <= 15.0
        for _ in range(20):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertLessEqual(self.game.player_x, 15.0)

    def test_bullet_firing_and_upward_trajectory(self):
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.bullets), 1)
        b = self.game.bullets[0]
        self.assertTrue(b["active"])
        self.assertLess(b["y"], 14.0)

        prev_y = b["y"]
        self.game.update_bullets(0.05)
        self.assertLess(b["y"], prev_y)

    def test_bullet_destroys_mushroom(self):
        self.game.mushrooms = [{"x": 7, "y": 10, "health": 1, "active": True}]
        self.game.bullets = [{"x": 7.0, "y": 10.0, "active": True}]

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.mushrooms[0]["active"])
        self.assertFalse(self.game.bullets[0]["active"])
        self.assertEqual(self.game.score, prev_score + 5)

    def test_centipede_fission_and_splitting_into_new_head(self):
        # Segment 2 is body segment. Segment 3 is behind it.
        self.assertFalse(self.game.segments[2]["is_head"])
        self.assertFalse(self.game.segments[3]["is_head"])
        self.game.segments[2]["x"] = 5.0
        self.game.segments[2]["y"] = 2.0

        prev_count = self.game.get_active_segment_count()
        self.game.hit_centipede_segment(2)

        # Segment 2 is deactivated
        self.assertFalse(self.game.segments[2]["active"])
        self.assertEqual(self.game.get_active_segment_count(), prev_count - 1)

        # Mushroom spawned at (5, 2)
        mushroom_at_pos = any(m["active"] and m["x"] == 5 and m["y"] == 2 for m in self.game.mushrooms)
        self.assertTrue(mushroom_at_pos)

        # Segment 3 has split and become a new head!
        self.assertTrue(self.game.segments[3]["is_head"])

    def test_centipede_stepping_and_direction_reversal(self):
        # Head at right edge x = 15.0, dir_x = +1
        self.game.segments[0]["x"] = 15.0
        self.game.segments[0]["y"] = 2.0
        self.game.segments[0]["dir_x"] = 1
        self.game.centipede_step_timer = self.game.centipede_step_interval

        self.game.update_centipede(0.01)

        # Drops down to y = 3.0 and reverses direction to dir_x = -1
        self.assertEqual(self.game.segments[0]["y"], 3.0)
        self.assertEqual(self.game.segments[0]["dir_x"], -1)

    def test_spider_spawning_and_shot(self):
        self.game.spider = {"x": 5.0, "y": 12.0, "vx": 3.0, "vy": 2.0, "active": True}
        self.game.bullets = [{"x": 5.0, "y": 12.0, "active": True}]

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.spider["active"])
        self.assertFalse(self.game.bullets[0]["active"])
        self.assertEqual(self.game.score, prev_score + 300)

    def test_centipede_collision_with_player_causes_death(self):
        self.game.segments[0]["x"] = 7.5
        self.game.segments[0]["y"] = 14.0
        self.game.player_x = 7.5
        self.game.player_y = 14.0

        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_victory_condition(self):
        # Eliminate all segments
        for i in range(len(self.game.segments)):
            if self.game.segments[i]["active"]:
                self.game.hit_centipede_segment(i)

        self.assertEqual(self.game.get_active_segment_count(), 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Player at (7.5, 14.0) -> (8, 14), color Cyan (0, 255, 255)
        px = int(round(self.game.player_x))
        py = int(round(self.game.player_y))
        idx = (py * 16 + px) * 3
        self.assertEqual(fb[idx + 0], 0)
        self.assertEqual(fb[idx + 1], 255)
        self.assertEqual(fb[idx + 2], 255)


if __name__ == "__main__":
    unittest.main()
