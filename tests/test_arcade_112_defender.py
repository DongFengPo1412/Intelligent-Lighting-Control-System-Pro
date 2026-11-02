import unittest
from arcade.game_112_defender import (
    Game112Defender,
    STATE_PLAYING,
    STATE_PLAYER_DYING,
    STATE_WAVE_CLEAR,
    STATE_GAME_OVER,
    wrap_x,
    wrap_dist_x,
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


class TestGame112Defender(unittest.TestCase):
    def setUp(self):
        self.game = Game112Defender()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 112)
        self.assertEqual(self.game.name, "防卫者")
        self.assertEqual(self.game.english_name, "Defender")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("雷达", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.smart_bombs, 2)
        self.assertEqual(self.game.wave, 1)
        self.assertEqual(self.game.px, 8.0)
        self.assertEqual(self.game.py, 7.0)
        self.assertEqual(len(self.game.humans), 4)
        self.assertTrue(all(h["alive"] for h in self.game.humans))

    def test_player_inertia_and_directional_turn(self):
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.facing_dir, -1)
        self.assertLess(self.game.vx, 0.0)

        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.facing_dir, 1)
        self.assertGreater(self.game.vx, -1.0)

    def test_laser_fire(self):
        # Fire laser facing right
        self.game.facing_dir = 1
        self.game.update(0.05, KEY_A, 0)

        active_lasers = [l for l in self.game.lasers if l["active"]]
        self.assertEqual(len(active_lasers), 1)
        self.assertGreater(active_lasers[0]["vx"], 20.0)

    def test_alien_abduction_behavior(self):
        # Position alien right above human 0 at x=6.0, y=13.0
        self.game.aliens[0]["x"] = 6.0
        self.game.aliens[0]["y"] = 13.0
        self.game.aliens[0]["active"] = True
        self.game.aliens[0]["abducted_human_idx"] = -1

        for _ in range(6):
            self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.aliens[0]["abducted_human_idx"], 0)
        self.assertTrue(self.game.humans[0]["being_abducted"])

    def test_mutant_transformation(self):
        # Alien reaches top of stratosphere with human
        self.game.aliens[0]["active"] = True
        self.game.aliens[0]["abducted_human_idx"] = 0
        self.game.aliens[0]["y"] = 1.2
        self.game.humans[0]["being_abducted"] = True

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.aliens[0]["is_mutant"])
        self.assertFalse(self.game.humans[0]["alive"])

    def test_laser_destroys_lander_and_releases_human(self):
        # Setup alien at (10, 6) carrying human 0
        self.game.aliens[0]["active"] = True
        self.game.aliens[0]["x"] = 10.0
        self.game.aliens[0]["y"] = 6.0
        self.game.aliens[0]["abducted_human_idx"] = 0
        self.game.humans[0]["alive"] = True
        self.game.humans[0]["being_abducted"] = True

        # Position laser directly impacting alien
        self.game.lasers[0]["active"] = True
        self.game.lasers[0]["x"] = 10.0
        self.game.lasers[0]["y"] = 6.0
        self.game.lasers[0]["vx"] = 26.0

        # Collision check on update
        self.game.update(0.01, 0, 0)
        self.assertFalse(self.game.aliens[0]["active"])
        self.assertFalse(self.game.humans[0]["being_abducted"])
        self.assertTrue(self.game.humans[0]["is_falling"])

    def test_mid_air_humanoid_rescue_and_surface_landing(self):
        # Human 0 is falling near player
        self.game.px = 8.0
        self.game.py = 6.0
        self.game.humans[0]["x"] = 8.0
        self.game.humans[0]["y"] = 6.2
        self.game.humans[0]["is_falling"] = True
        self.game.humans[0]["being_carried"] = False

        init_score = self.game.score
        # Update catches human
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.carried_human_idx, 0)
        self.assertTrue(self.game.humans[0]["being_carried"])
        self.assertEqual(self.game.score, init_score + 500)

        # Descend to surface to land
        self.game.py = 13.6
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.carried_human_idx, -1)
        self.assertFalse(self.game.humans[0]["being_carried"])
        self.assertEqual(self.game.score, init_score + 1000)

    def test_smart_bomb_screen_clear(self):
        # Alien 0 on-screen (x=8.5, near px=8.0)
        self.game.aliens[0]["active"] = True
        self.game.aliens[0]["x"] = 8.5
        # Alien 1 off-screen (x=30.0, far from px=8.0)
        self.game.aliens[1]["active"] = True
        self.game.aliens[1]["x"] = 30.0

        self.assertEqual(self.game.smart_bombs, 2)
        # Press B to trigger smart bomb
        self.game.update(0.05, KEY_B, 0)

        self.assertEqual(self.game.smart_bombs, 1)
        self.assertFalse(self.game.aliens[0]["active"])
        self.assertTrue(self.game.aliens[1]["active"])

    def test_wave_clear_and_bonus(self):
        # Deactivate all aliens
        for a in self.game.aliens:
            a["active"] = False

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_WAVE_CLEAR)
        self.assertEqual(self.game.score, init_score + 1000)


if __name__ == "__main__":
    unittest.main()
