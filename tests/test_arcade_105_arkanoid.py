import unittest
from arcade.game_105_arkanoid import (
    Game105Arkanoid,
    STATE_PLAYING,
    STATE_BOSS_DOH,
    STATE_BALL_LOST,
    STATE_ROUND_CLEAR,
    STATE_GAME_OVER,
    CAPSULE_LASER,
    CAPSULE_ENLARGE,
    CAPSULE_CATCH,
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


class TestGame105Arkanoid(unittest.TestCase):
    def setUp(self):
        self.game = Game105Arkanoid()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 105)
        self.assertEqual(self.game.name, "破坏者")
        self.assertEqual(self.game.english_name, "Arkanoid")
        self.assertEqual(self.game.release_year, 1986)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("激光飞船能量胶囊变异", self.game.core_mechanic)

    def test_paddle_horizontal_movement(self):
        init_x = self.game.paddle_x
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.paddle_x, init_x)

    def test_launch_caught_ball(self):
        self.assertTrue(self.game.ball_caught)
        # Press Button A to release ball
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.ball_caught)
        self.assertLess(self.game.ball_vy, 0.0)

    def test_ball_bounce_walls_and_ceiling(self):
        self.game.ball_caught = False
        # Move ball to left wall
        self.game.ball_x = 0.9
        self.game.ball_vx = -4.0
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.ball_vx, 0.0)

        # Move ball to ceiling
        self.game.ball_y = 0.9
        self.game.ball_vy = -5.0
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.ball_vy, 0.0)

    def test_ball_lost_bottom(self):
        self.game.ball_caught = False
        self.game.ball_y = 15.6
        self.game.ball_vy = 6.0  # Falling down past paddle
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_BALL_LOST)

    def test_hit_brick_and_silver_double_hit(self):
        self.game.ball_caught = False
        # Place ball colliding with colored brick at row 4 (y=6), col 2 (x=5)
        self.game.ball_x = 5.0
        self.game.ball_y = 6.2
        self.game.ball_vy = -4.0
        init_score = self.game.score

        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.score, init_score)
        self.assertGreater(self.game.ball_vy, 0.0)

        # Hit Silver brick at row 0 (y=2), col 2 (x=5)
        self.game.bricks[0][2] = 9
        self.game.ball_x = 5.0
        self.game.ball_y = 2.2
        self.game.ball_vy = -4.0

        self.game.update(0.05, 0, 0)
        # Silver brick takes 1st hit -> turns into colored brick 1
        self.assertEqual(self.game.bricks[0][2], 1)

    def test_catch_capsule_powerups(self):
        self.assertEqual(self.game.paddle_width, 3)
        self.game.set_powerup(CAPSULE_ENLARGE)
        self.assertEqual(self.game.paddle_width, 5)

        self.game.set_powerup(CAPSULE_LASER)
        self.assertEqual(self.game.paddle_width, 3)
        self.assertEqual(self.game.active_powerup, CAPSULE_LASER)

    def test_fire_lasers_destroys_brick(self):
        self.game.ball_caught = False
        self.game.set_powerup(CAPSULE_LASER)
        self.game.paddle_x = 5.0

        # Press Button A to fire laser
        self.game.update(0.05, KEY_A, 0)
        active_lasers = [l for l in self.game.lasers if l["active"]]
        self.assertEqual(len(active_lasers), 2)

        # Let laser hit brick at row 3 (y=5), col 2 (x=5.0)
        active_lasers[0]["x"] = 5.0
        active_lasers[0]["y"] = 6.2  # 6.2 - 20.0*0.05 = 5.2 -> int(5.2)-2 = row 3
        self.game.bricks[3][2] = 4

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.bricks[3][2], 0)
        self.assertGreater(self.game.score, init_score)

    def test_boss_doh_battle_and_defeat(self):
        self.game.spawn_boss_doh()
        self.assertEqual(self.game.state, STATE_BOSS_DOH)
        self.assertEqual(self.game.doh_hp, 12)

        # Hit Doh with ball
        self.game.ball_caught = False
        self.game.ball_x = self.game.doh_x + 1.0
        self.game.ball_y = 4.0
        self.game.ball_vy = -4.0

        self.game.doh_hp = 1  # 1 hit left
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)
        self.assertGreater(self.game.score, 4000)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
