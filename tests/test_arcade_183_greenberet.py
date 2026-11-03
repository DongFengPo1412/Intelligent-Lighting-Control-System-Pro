# -*- coding: utf-8 -*-
import unittest
from arcade.game_183_greenberet import (
    Game183GreenBeret,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SOLDIER_KILLED,
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

class TestArcade183GreenBeret(unittest.TestCase):
    def setUp(self):
        self.game = Game183GreenBeret()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 183)
        self.assertEqual(self.game.name, "绿色兵团")
        self.assertEqual(self.game.english_name, "Green Beret")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(len(self.game.enemies), 0)

    def test_02_movement_and_prone_crawl(self):
        self.game.px = 3.0
        # Move right
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.px, 3.0)
        self.assertEqual(self.game.facing, 1)

        # Drop into prone crawl (Down key)
        self.assertFalse(self.game.is_prone)
        self.game.update(0.01, keys_down=KEY_DOWN)
        self.assertTrue(self.game.is_prone)

    def test_03_forward_scrolling_increases_mission_distance(self):
        self.game.px = 8.0
        init_dist = self.game.distance
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.distance, init_dist)

    def test_04_combat_knife_thrust_neutralizes_infantry(self):
        # Enemy at (4.0, 13.0)
        self.game.px = 3.0
        self.game.facing = 1
        e = self.game.enemies[0]
        e["x"] = 4.0
        e["y"] = 13.0
        e["is_officer"] = False
        e["alive"] = True
        initial_score = self.game.score

        # Knife thrust (Button A)
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertFalse(e["alive"])
        self.assertEqual(self.game.score, initial_score + 100)
        self.assertGreater(self.game.knife_timer, 0.0)

    def test_05_defeat_officer_scavenges_rpg_ammo(self):
        self.game.px = 3.0
        self.game.facing = 1
        self.game.rpg_ammo = 0

        # Red officer enemy
        e = self.game.enemies[0]
        e["x"] = 4.0
        e["y"] = 13.0
        e["is_officer"] = True
        e["alive"] = True
        initial_score = self.game.score

        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertFalse(e["alive"])
        self.assertEqual(self.game.rpg_ammo, 3) # Scavenged 3 RPG rounds!
        self.assertEqual(self.game.score, initial_score + 500)

    def test_06_fire_scavenged_rpg_rocket(self):
        self.game.rpg_ammo = 1
        self.assertEqual(len(self.game.rockets), 0)

        # Fire RPG (Button B)
        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertEqual(self.game.rpg_ammo, 0)
        self.assertEqual(len(self.game.rockets), 1)
        r = self.game.rockets[0]
        self.assertTrue(r["active"])
        self.assertGreater(r["vx"], 0.0)

    def test_07_paratrooper_descent_and_landing(self):
        self.game.paratroopers = [{
            "x": 8.0,
            "y": 5.0,
            "vy": 4.0,
            "alive": True,
        }]
        self.game.update(0.1)
        self.assertGreater(self.game.paratroopers[0]["y"], 5.0)

    def test_08_enemy_touch_kills_commando(self):
        self.game.px = 5.0
        self.game.enemies = [{
            "x": 5.2,
            "y": 13.0,
            "vx": -1.0,
            "is_officer": False,
            "alive": True,
        }]
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_SOLDIER_KILLED)

    def test_09_destroy_missile_silo_stage_clear(self):
        self.game.enemies.clear()
        self.game.paratroopers.clear()
        self.game.distance = self.game.target_distance + 1.0
        self.game.silo_hp = 1
        self.game.px = 12.5
        self.game.facing = 1

        # Stab silo
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.silo_hp, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 3000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_SOLDIER_KILLED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
