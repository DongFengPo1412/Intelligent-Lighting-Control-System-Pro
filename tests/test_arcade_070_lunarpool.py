import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_070_lunarpool import (
    Game070LunarPool,
    STATE_START,
    STATE_PLAYING,
    STATE_BALLS_MOVING,
    STATE_DEAD,
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


class TestArcade070LunarPool(unittest.TestCase):
    def setUp(self):
        self.game = Game070LunarPool()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 70)
        self.assertEqual(self.game.english_name, "Lunar Pool")
        self.assertEqual(self.game.release_year, 1985)
        cart = ArcadeRegistry.get_cartridge(70)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game070LunarPool)

    def test_cue_aim_angle_rotation(self):
        initial_angle = self.game.aim_angle
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.aim_angle, initial_angle)

        self.game.update(0.1, KEY_LEFT, 0)
        self.assertAlmostEqual(self.game.aim_angle, initial_angle, delta=0.05)

    def test_cue_power_charging_and_strike(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        # Hold A to charge
        self.game.update(0.2, KEY_A, 0)
        self.assertTrue(self.game.is_charging_power)
        self.assertGreater(self.game.shot_power, 0.0)

        # Release A to strike cue ball
        self.game.update(0.02, 0, KEY_A)
        self.assertEqual(self.game.state, STATE_BALLS_MOVING)
        self.assertGreater(self.game.balls[0]["vx"], 0.0)

    def test_cushion_reflection_and_friction(self):
        cue = self.game.balls[0]
        cue["x"] = 14.0
        cue["vx"] = 10.0
        self.game.state = STATE_BALLS_MOVING

        # Advance physics tick into right cushion (x >= 14.2)
        self.game.update_physics(0.05)
        self.assertLess(cue["vx"], 0.0)  # Rebounded leftward!

    def test_ball_to_ball_elastic_collision(self):
        b0 = self.game.balls[0]
        b1 = self.game.balls[1]

        b0["x"] = 9.0
        b0["y"] = 8.0
        b0["vx"] = 8.0
        b0["vy"] = 0.0

        b1["x"] = 9.8
        b1["y"] = 8.0
        b1["vx"] = 0.0
        b1["vy"] = 0.0

        self.game.check_ball_collisions()
        # Momentum transfer: b1 gains positive vx, b0 slows/rebounds
        self.assertGreater(b1["vx"], 0.0)
        self.assertLess(b0["vx"], 8.0)

    def test_target_ball_pocketing_and_score(self):
        self.assertEqual(self.game.get_balls_remaining(), 4)
        target = self.game.balls[1]
        target["x"] = 1.6
        target["y"] = 1.6  # Near corner pocket (1.5, 1.5)

        self.game.check_pocket_collisions()
        self.assertTrue(target["in_pocket"])
        self.assertEqual(self.game.get_balls_remaining(), 3)
        self.assertGreater(self.game.score, 0)

    def test_consecutive_pocket_combo_multiplier(self):
        self.assertEqual(self.game.combo_multiplier, 1)

        # First ball pocketed
        self.game.balls[1]["x"] = 1.6
        self.game.balls[1]["y"] = 1.6
        self.game.check_pocket_collisions()
        self.assertEqual(self.game.combo_multiplier, 2)

        # Second ball pocketed in same turn
        self.game.balls[2]["x"] = 14.4
        self.game.balls[2]["y"] = 1.6
        self.game.check_pocket_collisions()
        self.assertEqual(self.game.combo_multiplier, 4)

    def test_scratch_foul_penalizes_life(self):
        cue = self.game.balls[0]
        cue["x"] = 1.5
        cue["y"] = 1.5  # Falls into pocket!

        self.game.check_pocket_collisions()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_all_balls_pocketed_victory(self):
        # Pocket all target balls
        for i in range(1, 5):
            self.game.balls[i]["in_pocket"] = True

        # Check victory trigger on final ball
        self.game.balls[1]["in_pocket"] = False
        self.game.balls[1]["x"] = 1.5
        self.game.balls[1]["y"] = 1.5
        self.game.check_pocket_collisions()

        self.assertEqual(self.game.get_balls_remaining(), 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_framebuffer_and_status(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 70)
        self.assertEqual(status["name"], "经典台球")


if __name__ == "__main__":
    unittest.main()
