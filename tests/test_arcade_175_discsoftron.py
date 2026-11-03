# -*- coding: utf-8 -*-
import unittest
from arcade.game_175_discsoftron import (
    Game175DiscsOfTron,
    STATE_PLAYING,
    STATE_SARK_FALLING,
    STATE_PLAYER_DIED,
    STATE_GAME_OVER,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

class TestArcade175DiscsOfTron(unittest.TestCase):
    def setUp(self):
        self.game = Game175DiscsOfTron()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 175)
        self.assertEqual(self.game.name, "创战纪飞盘决斗")
        self.assertEqual(self.game.english_name, "Discs of Tron")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.sark_hp, 3)
        self.assertEqual(self.game.shield_energy, 100.0)

    def test_02_flynn_movement_and_bounds(self):
        self.game.px = 7.5
        self.game.py = 13.0
        # Move up and left
        self.game.update(0.1, keys_down=(KEY_LEFT | KEY_UP))
        self.assertLess(self.game.px, 7.5)
        self.assertLess(self.game.py, 13.0)

        # Clamping to lower ring
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 2.5)

    def test_03_throw_energy_disc(self):
        self.assertEqual(len(self.game.discs), 0)
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.discs), 1)
        disc = self.game.discs[0]
        self.assertTrue(disc["is_player"])
        self.assertLess(disc["vy"], 0.0)

    def test_04_side_wall_disc_ricochet(self):
        self.game.discs.append({
            "x": 1.6,
            "y": 8.0,
            "vx": -10.0,
            "vy": -5.0,
            "is_player": True,
        })
        self.game.update(0.05)
        # Should bounce off x=1.5 and reverse vx
        disc = self.game.discs[-1]
        self.assertGreater(disc["vx"], 0.0)
        self.assertGreaterEqual(disc["x"], 1.5)

    def test_05_player_disc_hits_sark(self):
        self.game.sx = 7.5
        self.game.sy = 2.5
        self.game.discs.append({
            "x": 7.5,
            "y": 3.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
        })
        initial_score = self.game.score
        initial_hp = self.game.sark_hp

        self.game.update(0.01)
        self.assertEqual(self.game.sark_hp, initial_hp - 1)
        self.assertEqual(self.game.score, initial_score + 500)

    def test_06_deflection_shield_blocks_and_reflects_sark_disc(self):
        # Flynn at (7.5, 13.0) raises shield (Button B)
        self.game.px = 7.5
        self.game.py = 13.0
        # Sark disc incoming towards Flynn
        self.game.discs.append({
            "x": 7.5,
            "y": 12.5,
            "vx": 0.0,
            "vy": 8.0,
            "is_player": False,
        })
        initial_score = self.game.score

        # Update with Button B held
        self.game.update(0.01, keys_down=KEY_B)
        self.assertTrue(self.game.shield_active)
        disc = self.game.discs[0]
        # Disc converted to player disc and reflected backwards
        self.assertTrue(disc["is_player"])
        self.assertLess(disc["vy"], 0.0)
        self.assertEqual(self.game.score, initial_score + 250)

    def test_07_sark_disc_kills_unshielded_player(self):
        self.game.px = 7.5
        self.game.py = 13.0
        self.game.discs.append({
            "x": 7.5,
            "y": 12.8,
            "vx": 0.0,
            "vy": 8.0,
            "is_player": False,
        })
        initial_lives = self.game.lives

        # Update without shield
        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_PLAYER_DIED)

    def test_08_mid_air_disc_clash_deflection(self):
        # Two discs collide mid-flight
        self.game.discs = [
            {"x": 7.5, "y": 8.0, "vx": 4.0, "vy": -6.0, "is_player": True},
            {"x": 7.6, "y": 8.1, "vx": -3.0, "vy": 6.0, "is_player": False},
        ]
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertEqual(self.game.score, initial_score + 50)

    def test_09_sark_defeated_falls_into_chasm(self):
        self.game.sark_hp = 1
        self.game.sx = 7.5
        self.game.sy = 2.5
        self.game.discs.append({
            "x": 7.5,
            "y": 3.0,
            "vx": 0.0,
            "vy": -10.0,
            "is_player": True,
        })

        self.game.update(0.01)
        self.assertEqual(self.game.sark_hp, 0)
        self.assertEqual(self.game.state, STATE_SARK_FALLING)
        self.assertGreaterEqual(self.game.score, 3000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_PLAYER_DIED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
