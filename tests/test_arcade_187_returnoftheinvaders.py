"""
Unit Tests for Game #187: 侵略者归来 (Return of the Invaders - 1985 Taito)
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
from arcade.game_187_returnoftheinvaders import (
    Game187ReturnOfTheInvaders,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_DESTROYED,
    STATE_GAME_OVER,
)

class TestArcade187ReturnOfTheInvaders(unittest.TestCase):
    def setUp(self):
        self.game = Game187ReturnOfTheInvaders()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 187)
        self.assertEqual(self.game.name, "侵略者归来")
        self.assertEqual(self.game.english_name, "Return of the Invaders")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertAlmostEqual(self.game.px, 7.5)
        self.assertAlmostEqual(self.game.py, 14.0)

    def test_02_ship_movement_and_bounds(self):
        init_x = self.game.px
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.px, init_x)

        # Clamping
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreaterEqual(self.game.px, 1.0)

        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertLessEqual(self.game.px, 14.0)

    def test_03_fire_lasers_button_a(self):
        self.assertEqual(len(self.game.lasers), 0)
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.lasers), 1)
        self.assertAlmostEqual(self.game.lasers[0]["vy"], -16.0)

    def test_04_laser_destroys_normal_alien(self):
        # Isolate one alien in front of player
        self.game.aliens = [
            {"x": 7.5, "y": 10.0, "vx": 0.0, "vy": 0.0, "type": "normal", "hp": 1, "alive": True},
            {"x": 1.0, "y": 1.0, "vx": 0.0, "vy": 0.0, "type": "normal", "hp": 1, "alive": True},
        ]
        self.game.px = 7.5
        self.game.update(0.016, keys_pressed=KEY_A)

        # Step laser towards alien
        for _ in range(15):
            self.game.update(0.016)
        self.assertFalse(self.game.aliens[0]["alive"])
        self.assertEqual(self.game.score, 80)

    def test_05_mitosis_splitter_alien_divides_into_two_minis(self):
        # Place splitter alien (hp 1 for immediate split)
        self.game.aliens = [
            {"x": 7.5, "y": 10.0, "vx": 0.0, "vy": 0.0, "type": "splitter", "hp": 1, "alive": True},
            {"x": 1.0, "y": 1.0, "vx": 0.0, "vy": 0.0, "type": "normal", "hp": 1, "alive": True},
        ]
        self.game.px = 7.5
        self.game.update(0.016, keys_pressed=KEY_A)

        for _ in range(15):
            self.game.update(0.016)
        self.assertFalse(self.game.aliens[0]["alive"])

        # Check that two mini aliens were spawned
        mini_aliens = [a for a in self.game.aliens if a["alive"] and a["type"] == "mini"]
        self.assertEqual(len(mini_aliens), 2)
        # One travels left, one travels right
        self.assertLess(mini_aliens[0]["vx"], 0.0)
        self.assertGreater(mini_aliens[1]["vx"], 0.0)

    def test_06_launch_boomerang_cutter_button_b(self):
        self.assertIsNone(self.game.boomerang)
        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertIsNotNone(self.game.boomerang)
        self.assertEqual(self.game.boomerang["state"], "ascending")
        self.assertAlmostEqual(self.game.boomerang["vy"], -12.0)

    def test_07_boomerang_ascent_and_returning_curve(self):
        self.game.px = 7.5
        self.game.update(0.016, keys_pressed=KEY_B)

        # Advance until boomerang peaks at y <= 4.0
        for _ in range(50):
            if self.game.boomerang and self.game.boomerang["state"] == "returning":
                break
            self.game.update(0.016)

        self.assertIsNotNone(self.game.boomerang)
        self.assertEqual(self.game.boomerang["state"], "returning")

    def test_08_mothership_ufo_spawn_and_emp_bomb_clear(self):
        self.game.ufo_active = True
        self.game.ufo_x = 7.5
        # Active alien bomb on screen
        self.game.alien_bombs = [{"x": 5.0, "y": 8.0, "vy": 5.0}]

        # Fire laser at UFO
        self.game.px = 7.5
        self.game.lasers = [{"x": 7.5, "y": 2.0, "vy": -16.0, "active": True}]
        self.game.update(0.016)

        # UFO destroyed, award 1000 pts and detonate EMP clearing bombs
        self.assertFalse(self.game.ufo_active)
        self.assertEqual(len(self.game.alien_bombs), 0)
        self.assertEqual(self.game.score, 1000)

    def test_09_all_aliens_destroyed_stage_clear(self):
        # 1 alien remaining
        self.game.aliens = [
            {"x": 7.5, "y": 10.0, "vx": 0.0, "vy": 0.0, "type": "normal", "hp": 1, "alive": True}
        ]
        self.game.px = 7.5
        self.game.update(0.016, keys_pressed=KEY_A)

        for _ in range(15):
            self.game.update(0.016)

        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2080)

    def test_10_render_and_game_over_reset(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.state = STATE_GAME_OVER
        self.game.score = 6500
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()

