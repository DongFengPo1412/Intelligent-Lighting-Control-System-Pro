"""
Unit Tests for Game #190: 破坏大奖赛 (Demolition Derby - 1984 Bally Midway)
"""

import unittest
import math
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    CTRL_ARCADE_AB,
)
from arcade.game_190_demolitionderby import (
    Game190DemolitionDerby,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_CAR_WRECKED,
    STATE_GAME_OVER,
)

class TestArcade190DemolitionDerby(unittest.TestCase):
    def setUp(self):
        self.game = Game190DemolitionDerby()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 190)
        self.assertEqual(self.game.name, "破坏大奖赛")
        self.assertEqual(self.game.english_name, "Demolition Derby")
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.hp, 100.0)
        self.assertEqual(len(self.game.rivals), 3)

    def test_02_rotational_steering(self):
        init_angle = self.game.angle
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.angle, init_angle)

        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertAlmostEqual(self.game.angle, init_angle, delta=0.01)

    def test_03_forward_throttle_acceleration(self):
        self.assertEqual(self.game.speed, 0.0)
        self.game.update(0.1, keys_down=KEY_A)
        self.assertGreater(self.game.speed, 0.0)
        self.assertLessEqual(self.game.speed, 7.5)

    def test_04_reverse_gear_ram_velocity(self):
        self.assertEqual(self.game.speed, 0.0)
        self.game.update(0.1, keys_down=KEY_B)
        self.assertLess(self.game.speed, 0.0)
        self.assertGreaterEqual(self.game.speed, -4.5)

    def test_05_arena_wall_rebound_clamping(self):
        self.game.px = 14.2
        self.game.speed = 6.0
        self.game.angle = 0.0 # Moving right towards boundary
        self.game.update(0.1)
        self.assertLessEqual(self.game.px, 14.5)

    def test_06_frontal_ramming_damage_exchange(self):
        # Position rival directly in front of player
        self.game.px = 8.0
        self.game.py = 8.0
        self.game.angle = -math.pi / 2.0 # Facing UP
        self.game.speed = 6.0

        r = self.game.rivals[0]
        r["x"] = 8.0
        r["y"] = 7.0
        r["speed"] = 0.0
        init_r_hp = r["hp"]
        init_p_hp = self.game.hp

        # Frontal crash
        self.game.update(0.016)
        # Rival takes heavy damage
        self.assertLess(r["hp"], init_r_hp)
        # Player radiator takes damage
        self.assertLess(self.game.hp, init_p_hp)
        self.assertGreater(self.game.score, 0)

    def test_07_tactical_reverse_ramming_mitigates_damage(self):
        self.game.px = 8.0
        self.game.py = 8.0
        self.game.angle = -math.pi / 2.0 # Facing UP
        self.game.speed = -5.0 # Backing up DOWN

        r = self.game.rivals[0]
        r["x"] = 8.0
        r["y"] = 9.0 # Rival is behind player
        r["speed"] = 0.0
        init_r_hp = r["hp"]
        init_p_hp = self.game.hp

        # Reverse ram hit
        self.game.update(0.016)
        self.assertLess(r["hp"], init_r_hp)
        self.assertLess(self.game.hp, init_p_hp)
        # Rear bumper damage to player is much lower than damage inflicted to rival
        p_loss = init_p_hp - self.game.hp
        r_loss = init_r_hp - r["hp"]
        self.assertGreater(r_loss, p_loss)

    def test_08_opponent_wrecked_turns_into_obstacle(self):
        r = self.game.rivals[0]
        r["x"] = 8.0
        r["y"] = 7.0
        r["hp"] = 1.0 # Fragile rival

        self.game.px = 8.0
        self.game.py = 8.0
        self.game.angle = -math.pi / 2.0
        self.game.speed = 6.0

        self.game.update(0.016)
        # Rival destroyed
        self.assertFalse(r["alive"])
        self.assertEqual(r["hp"], 0.0)
        self.assertEqual(r["speed"], 0.0)
        self.assertGreaterEqual(self.game.score, 2000)

    def test_09_all_rivals_wrecked_stage_clear(self):
        # Eliminate first 2 rivals
        self.game.rivals[0]["alive"] = False
        self.game.rivals[1]["alive"] = False

        # Destroy final rival
        r = self.game.rivals[2]
        r["x"] = 8.0
        r["y"] = 7.0
        r["hp"] = 1.0

        self.game.px = 8.0
        self.game.py = 8.0
        self.game.angle = -math.pi / 2.0
        self.game.speed = 6.0

        self.game.update(0.016)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 7000)

    def test_10_render_and_engine_blowout_game_over_reset(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.hp = 0.0
        self.game.update(0.016)
        self.assertEqual(self.game.state, STATE_CAR_WRECKED)
        self.assertEqual(self.game.lives, 2)

        # Reset test
        self.game.state = STATE_GAME_OVER
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.hp, 100.0)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
