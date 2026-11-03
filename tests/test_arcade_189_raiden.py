"""
Unit Tests for Game #189: 雷电 (Raiden - 1990 Seibu Kaihatsu)
"""

import unittest
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    CTRL_ARCADE_AB,
)
from arcade.game_189_raiden import (
    Game189Raiden,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_DESTROYED,
    STATE_GAME_OVER,
    WEAPON_VULCAN,
    WEAPON_LASER,
)

class TestArcade189Raiden(unittest.TestCase):
    def setUp(self):
        self.game = Game189Raiden()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 189)
        self.assertEqual(self.game.name, "雷电")
        self.assertEqual(self.game.english_name, "Raiden")
        self.assertEqual(self.game.release_year, 1990)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.bombs, 3)
        self.assertEqual(self.game.weapon_type, WEAPON_VULCAN)
        self.assertAlmostEqual(self.game.px, 7.5)
        self.assertAlmostEqual(self.game.py, 13.0)

    def test_02_fighter_8way_movement_and_bounds(self):
        init_x = self.game.px
        init_y = self.game.py
        self.game.update(0.1, keys_down=KEY_UP | KEY_LEFT)
        self.assertLess(self.game.px, init_x)
        self.assertLess(self.game.py, init_y)

        # Clamping
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreaterEqual(self.game.px, 1.0)

        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_UP)
        self.assertGreaterEqual(self.game.py, 2.0)

    def test_03_vulcan_cannon_3way_spread_firing(self):
        self.assertEqual(self.game.weapon_type, WEAPON_VULCAN)
        self.assertEqual(len(self.game.bullets), 0)

        self.game.update(0.016, keys_pressed=KEY_A)
        # Fires 3 spread bullets
        self.assertEqual(len(self.game.bullets), 3)
        self.assertFalse(self.game.bullets[0]["is_laser"])
        self.assertLess(self.game.bullets[1]["vx"], 0.0) # Left spread
        self.assertGreater(self.game.bullets[2]["vx"], 0.0) # Right spread

    def test_04_collect_blue_crystal_swaps_to_laser(self):
        # Place blue crystal on top of fighter
        self.game.crystal = {
            "x": 7.5,
            "y": 13.0,
            "vx": 0.0,
            "vy": 0.0,
            "color": "blue",
            "swap_timer": 3.0,
        }
        self.game.update(0.016)
        self.assertEqual(self.game.weapon_type, WEAPON_LASER)
        self.assertEqual(self.game.score, 500)
        self.assertIsNone(self.game.crystal)

    def test_05_laser_high_damage_piercing_beam(self):
        self.game.weapon_type = WEAPON_LASER
        self.game.bullets = []
        self.game.update(0.016, keys_pressed=KEY_A)
        # Fires twin piercing laser beams
        self.assertEqual(len(self.game.bullets), 2)
        self.assertTrue(self.game.bullets[0]["is_laser"])
        self.assertEqual(self.game.bullets[0]["damage"], 3)

    def test_06_thermonuclear_bomb_deployment_fuse(self):
        self.assertEqual(self.game.bombs, 3)
        self.assertIsNone(self.game.mega_bomb)

        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertEqual(self.game.bombs, 2)
        self.assertIsNotNone(self.game.mega_bomb)
        self.assertFalse(self.game.mega_bomb["exploding"])

        # Fuse ticks down to explosion
        for _ in range(35):
            self.game.update(0.016)
        self.assertTrue(self.game.mega_bomb["exploding"])

    def test_07_mega_bomb_detonation_shockwave_clears_bullets(self):
        # Setup active bomb and active enemy bullets
        self.game.mega_bomb = {
            "x": 7.5,
            "y": 8.0,
            "fuse": 0.5,
            "radius": 2.0,
            "exploding": True,
            "active": True,
        }
        self.game.enemy_bullets = [{"x": 7.5, "y": 8.0, "vx": 0.0, "vy": 5.0}]

        self.game.update(0.016)
        # Shockwave incinerates all enemy bullets
        self.assertEqual(len(self.game.enemy_bullets), 0)

    def test_08_enemy_bullet_destroys_player(self):
        self.game.px = 7.5
        self.game.py = 13.0
        self.game.enemy_bullets = [{"x": 7.5, "y": 13.0, "vx": 0.0, "vy": 5.0}]

        self.game.update(0.016)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_SHIP_DESTROYED)

    def test_09_destroy_boss_tank_stage_clear(self):
        boss = [e for e in self.game.enemies if e["type"] == "boss"][0]
        boss["hp"] = 1
        boss["x"] = 7.5
        boss["y"] = 5.0

        # Laser beam hits boss
        self.game.bullets = [{"x": 7.5, "y": 5.2, "vx": 0.0, "vy": -10.0, "is_laser": True, "damage": 3, "active": True}]
        self.game.update(0.016)

        self.assertFalse(boss["alive"])
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 10000)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.state = STATE_GAME_OVER
        self.game.score = 9000
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
