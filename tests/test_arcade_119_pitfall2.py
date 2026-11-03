import unittest
from arcade.game_119_pitfall2 import (
    Game119Pitfall2,
    STATE_EXPLORING,
    STATE_CHECKPOINT_RESPAWN,
    STATE_EXPEDITION_CLEAR,
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


class TestGame119Pitfall2(unittest.TestCase):
    def setUp(self):
        self.game = Game119Pitfall2()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 119)
        self.assertEqual(self.game.name, "黄金城之谜")
        self.assertEqual(self.game.english_name, "Pitfall II: Lost Caverns")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("地下溶洞", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_EXPLORING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.treasures_collected, 0)
        self.assertEqual(self.game.px, 2.0)
        self.assertEqual(self.game.py, 3.0)
        self.assertFalse(self.game.checkpoint_active)
        self.assertFalse(self.game.on_vine)
        self.assertFalse(self.game.on_balloon)

    def test_player_walk_and_jump(self):
        # Move Right
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 2.0)

        # Jump
        self.game.update(0.05, KEY_A, 0)
        self.assertLess(self.game.vy, -2.0)

    def test_ladder_climbing(self):
        # Position player at ladder 0 at (13.0, 5.0)
        self.game.set_player_pos(13.0, 5.0)
        init_y = self.game.py

        # Climb Up
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.on_ladder)
        self.assertLess(self.game.py, init_y)

    def test_vine_latch_and_release(self):
        # Position player near vine trajectory at (7.5, 3.8)
        self.game.set_player_pos(7.5, 3.8)
        self.game.update(0.05, 0, 0)

        # If aligned with vine, latches on
        self.game.on_vine = True
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.on_vine)

        # Press B to dismount
        self.game.update(0.05, KEY_B, 0)
        self.assertFalse(self.game.on_vine)

    def test_balloon_floating_ascent(self):
        # Position player near balloon at x=10.5, y=10.0 (bat placed safely away)
        self.game.hazards[2]["x"] = 1.0
        self.game.balloon_y = 10.0
        self.game.set_player_pos(10.5, 10.0)

        # Press Up to catch balloon
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.on_balloon)

        # Dismount balloon with Down
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertFalse(self.game.on_balloon)

    def test_checkpoint_cross_activation(self):
        self.assertFalse(self.game.checkpoint_active)
        # Walk past cross at (5.0, 12.0)
        self.game.set_player_pos(5.0, 12.0)
        init_score = self.game.score

        self.game.update(0.01, 0, 0)
        self.assertTrue(self.game.checkpoint_active)
        self.assertEqual(self.game.checkpoint_x, 5.0)
        self.assertEqual(self.game.checkpoint_y, 12.0)
        self.assertEqual(self.game.score, init_score + 100)

    def test_hazard_checkpoint_resurrection(self):
        # Activate checkpoint at (5.0, 12.0)
        self.game.checkpoint_active = True
        self.game.checkpoint_x = 5.0
        self.game.checkpoint_y = 12.0

        # Player touches scorpion at (7.0, 7.0)
        self.game.set_player_pos(7.0, 7.0)
        self.game.hazards[1]["x"] = 7.0
        self.game.hazards[1]["y"] = 7.0

        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.state, STATE_CHECKPOINT_RESPAWN)
        # Advance through respawn timer
        for _ in range(20):
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_EXPLORING)
        self.assertEqual(self.game.px, 5.0)
        self.assertEqual(self.game.py, 12.0)

    def test_treasures_collection(self):
        # Walk onto Gold Ingot at (13.0, 3.0)
        self.game.set_player_pos(13.0, 3.0)
        init_score = self.game.score

        self.game.update(0.01, 0, 0)

        self.assertTrue(self.game.treasures[0]["collected"])
        self.assertEqual(self.game.score, init_score + 200)
        self.assertEqual(self.game.treasures_collected, 1)

    def test_expedition_clear(self):
        self.game.treasures_collected = 2
        self.game.treasures[0]["collected"] = True
        self.game.treasures[1]["collected"] = True

        # Collect final treasure at (14.0, 12.0)
        self.game.set_player_pos(14.0, 12.0)
        init_score = self.game.score

        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.state, STATE_EXPEDITION_CLEAR)
        self.assertEqual(self.game.treasures_collected, 3)
        self.assertEqual(self.game.score, init_score + 500 + 1000)


if __name__ == "__main__":
    unittest.main()
