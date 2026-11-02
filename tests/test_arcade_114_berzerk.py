import unittest
from arcade.game_114_berzerk import (
    Game114Berzerk,
    STATE_EXPLORING,
    STATE_PLAYER_DYING,
    STATE_ROOM_TRANSITION,
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


class TestGame114Berzerk(unittest.TestCase):
    def setUp(self):
        self.game = Game114Berzerk()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 114)
        self.assertEqual(self.game.name, "狂暴机器人")
        self.assertEqual(self.game.english_name, "Berzerk")
        self.assertEqual(self.game.release_year, 1980)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("高压电网", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_EXPLORING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.rooms_cleared, 0)
        self.assertEqual(self.game.px, 8.0)
        self.assertEqual(self.game.py, 8.0)
        self.assertEqual(self.game.aim_dx, 1)
        self.assertEqual(self.game.aim_dy, 0)
        self.assertFalse(self.game.otto["active"])

    def test_player_movement_and_aim_direction(self):
        # Move Up
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.aim_dx, 0)
        self.assertEqual(self.game.aim_dy, -1)
        self.assertLess(self.game.py, 8.0)

        # Move Left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.aim_dx, -1)
        self.assertEqual(self.game.aim_dy, 0)
        self.assertLess(self.game.px, 8.0)

    def test_player_laser_fire(self):
        self.game.aim_dx = 1
        self.game.aim_dy = 0
        self.game.update(0.05, KEY_A, 0)

        active_lasers = [l for l in self.game.lasers if l["active"] and l["is_player"]]
        self.assertEqual(len(active_lasers), 1)
        self.assertGreater(active_lasers[0]["vx"], 15.0)

    def test_player_laser_destroys_robot(self):
        # Position robot at (10, 8)
        self.game.robots[0]["active"] = True
        self.game.robots[0]["x"] = 10.0
        self.game.robots[0]["y"] = 8.0

        # Laser heading into robot
        self.game.lasers[0]["active"] = True
        self.game.lasers[0]["is_player"] = True
        self.game.lasers[0]["x"] = 10.0
        self.game.lasers[0]["y"] = 8.0
        self.game.lasers[0]["vx"] = 20.0
        self.game.lasers[0]["vy"] = 0.0

        init_score = self.game.score
        self.game.update(0.01, 0, 0)

        self.assertFalse(self.game.robots[0]["active"])
        self.assertFalse(self.game.lasers[0]["active"])
        self.assertEqual(self.game.score, init_score + 100)

    def test_robot_wall_electrocution(self):
        # Push robot onto wall at (0, 0)
        self.game.robots[0]["active"] = True
        self.game.robots[0]["x"] = 0.0
        self.game.robots[0]["y"] = 0.0

        init_score = self.game.score
        self.game.update(0.01, 0, 0)

        self.assertFalse(self.game.robots[0]["active"])
        self.assertEqual(self.game.score, init_score + 50)

    def test_player_wall_electrocution(self):
        # Set player position onto wall at (0, 0)
        self.game.px = 0.0
        self.game.py = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DYING)

    def test_evil_otto_spawn_on_timer(self):
        self.assertFalse(self.game.otto["active"])
        # Fast forward room timer past 7.0 seconds
        self.game.room_timer = 7.1
        self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.otto["active"])
        self.assertEqual(self.game.otto["x"], 8.0)
        self.assertAlmostEqual(self.game.otto["y"], 0.61, delta=0.02)

    def test_evil_otto_pursuit_and_player_death(self):
        self.game.otto["active"] = True
        self.game.otto["x"] = 8.0
        self.game.otto["y"] = 7.5
        self.game.px = 8.0
        self.game.py = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DYING)

    def test_room_transition_doorway_exit(self):
        # Walk into West doorway at px < 0.2, py = 7.5
        self.game.px = 0.1
        self.game.py = 7.5

        init_rooms = self.game.rooms_cleared
        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_ROOM_TRANSITION)
        self.assertEqual(self.game.rooms_cleared, init_rooms + 1)
        self.assertEqual(self.game.score, init_score + 100)


if __name__ == "__main__":
    unittest.main()
