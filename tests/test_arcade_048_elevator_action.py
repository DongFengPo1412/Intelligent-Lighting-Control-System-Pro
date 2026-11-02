"""
Comprehensive Unit Tests for Arcade Cartridge #048: 疯狂电梯 (Elevator Action 1983 / Taito)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_048_elevator_action import (
    Game048ElevatorAction,
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


class TestArcade048ElevatorAction(unittest.TestCase):
    def setUp(self):
        self.game = Game048ElevatorAction()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 48)
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "疯狂电梯")
        self.assertIn("Elevator Action", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(48)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game048ElevatorAction)

    def test_initial_state_and_building(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.docs_collected, 0)
        self.assertEqual(self.game.get_documents_remaining(), 2)
        self.assertEqual(self.game.player_y, 3.0)
        self.assertEqual(self.game.elevator_y, 3.0)
        self.assertEqual(len(self.game.enemies), 3)

    def test_player_walk_and_crouch_controls(self):
        self.game.player_x = 3.0
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, 3.0)

        # Press KEY_DOWN on floor outside elevator -> Crouch
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertTrue(self.game.is_crouching)

    def test_elevator_vertical_transit(self):
        # Move player inside elevator shaft
        self.game.player_x = 7.5
        self.game.player_y = 3.0
        self.game.elevator_y = 3.0

        # Press KEY_DOWN to ride elevator down
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertTrue(self.game.in_elevator)
        self.assertGreater(self.game.elevator_y, 3.0)
        self.assertEqual(self.game.player_y, self.game.elevator_y)

    def test_red_door_document_collection(self):
        # Walk to Red Door 0 at Floor 1 (y=7), col 3
        self.game.player_x = 3.0
        self.game.player_y = 7.0
        self.game.in_elevator = False

        prev_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.red_doors[0]["collected"])
        self.assertEqual(self.game.docs_collected, 1)
        self.assertEqual(self.game.get_documents_remaining(), 1)
        self.assertEqual(self.game.score, prev_score + 200)

    def test_shoot_overhead_light_causes_blackout(self):
        # Shoot light on Floor 0 at col 4, y=1
        self.game.bullets = [{"x": 4.0, "y": 1.0, "vx": 0.0, "is_player": True, "active": True}]
        self.game.lights[0]["active"] = True

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.lights[0]["active"])
        self.assertGreater(self.game.blackout_timer, 0.0)
        self.assertEqual(self.game.score, prev_score + 100)

    def test_player_shoots_enemy_spy(self):
        self.game.enemies[0]["x"] = 8.0
        self.game.enemies[0]["floor"] = 1  # y = 7
        self.game.enemies[0]["active"] = True
        self.game.bullets = [{"x": 8.0, "y": 7.0, "vx": 10.0, "is_player": True, "active": True}]

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.score, prev_score + 100)

    def test_crouching_dodges_enemy_bullet(self):
        self.game.player_x = 5.0
        self.game.player_y = 7.0
        self.game.is_crouching = True
        self.game.bullets = [{"x": 5.0, "y": 7.0, "vx": -10.0, "is_player": False, "active": True}]

        self.game.check_collisions()
        # Bullet passes over crouching player without death!
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

    def test_standing_hit_by_enemy_bullet_causes_death(self):
        self.game.player_x = 5.0
        self.game.player_y = 7.0
        self.game.is_crouching = False
        self.game.bullets = [{"x": 5.0, "y": 7.0, "vx": -10.0, "is_player": False, "active": True}]

        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_elevator_crushes_enemy_underneath(self):
        # Elevator descending at y = 6.2
        self.game.elevator_y = 6.2
        self.game.elevator_vy = 4.0
        # Enemy right underneath in shaft at Floor 1 (y = 7.0)
        self.game.enemies[1]["x"] = 7.5
        self.game.enemies[1]["floor"] = 1
        self.game.enemies[1]["active"] = True

        prev_score = self.game.score
        self.game.check_collisions()

        self.assertFalse(self.game.enemies[1]["active"])
        self.assertEqual(self.game.score, prev_score + 150)

    def test_victory_condition(self):
        # Collect all documents
        self.game.docs_collected = 2
        # Reach getaway car on Floor 3 (y=15, col 2)
        self.game.player_x = 2.0
        self.game.player_y = 15.0
        self.game.in_elevator = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check steel floor at (0, 3): (86, 101, 115)
        idx = (3 * 16 + 0) * 3
        self.assertEqual(fb[idx + 0], 86)
        self.assertEqual(fb[idx + 1], 101)
        self.assertEqual(fb[idx + 2], 115)
        # Check getaway car on row 14, col 1: Orange (230, 126, 34)
        c_idx = (14 * 16 + 1) * 3
        self.assertEqual(fb[c_idx + 0], 230)
        self.assertEqual(fb[c_idx + 1], 126)
        self.assertEqual(fb[c_idx + 2], 34)


if __name__ == "__main__":
    unittest.main()
