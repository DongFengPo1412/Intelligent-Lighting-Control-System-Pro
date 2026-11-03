"""
Unit Tests for Game #184: 战场之狼 (Commando - 1985 Capcom)
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
from arcade.game_184_commando import (
    Game184Commando,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_JOE_KILLED,
    STATE_GAME_OVER,
)

class TestArcade184Commando(unittest.TestCase):
    def setUp(self):
        self.game = Game184Commando()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 184)
        self.assertEqual(self.game.name, "战场之狼")
        self.assertEqual(self.game.english_name, "Commando")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.grenades, 6)
        self.assertAlmostEqual(self.game.px, 7.5)
        self.assertAlmostEqual(self.game.py, 13.0)

    def test_02_super_joe_8way_movement_and_bounds(self):
        # Move up-left
        init_px = self.game.px
        init_py = self.game.py
        self.game.update(0.1, keys_down=KEY_UP | KEY_LEFT)
        self.assertLess(self.game.px, init_px)
        self.assertLess(self.game.py, init_py)
        # Facing vector updated
        self.assertAlmostEqual(self.game.facing_x, -0.7071, places=3)
        self.assertAlmostEqual(self.game.facing_y, -0.7071, places=3)

        # Move far right to test boundary clamping
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertLessEqual(self.game.px, 14.0)

    def test_03_fire_machine_gun_button_a(self):
        self.assertEqual(len(self.game.bullets), 0)
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.bullets), 1)
        b = self.game.bullets[0]
        self.assertAlmostEqual(b["vy"], -16.0)
        self.assertTrue(b["active"])

    def test_04_machine_gun_eliminates_infantry_and_officer(self):
        # Place an infantry directly in front of Joe, with a second enemy so wave doesn't immediately respawn
        self.game.enemies = [
            {"x": 7.5, "y": 10.0, "vx": 0.0, "vy": 0.0, "type": "infantry", "hp": 1, "alive": True},
            {"x": 1.0, "y": 1.0, "vx": 0.0, "vy": 0.0, "type": "infantry", "hp": 1, "alive": True},
        ]
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0
        self.game.update(0.016, keys_pressed=KEY_A) # Fire bullet
        self.assertEqual(len(self.game.bullets), 1)

        # Bullet travels towards enemy
        for _ in range(15):
            self.game.update(0.016)
        self.assertFalse(self.game.enemies[0]["alive"])
        self.assertEqual(self.game.score, 100)

        # Now test officer gives extra grenade resupply crate
        self.game.grenades = 2
        self.game.enemies = [
            {"x": 7.5, "y": 10.0, "vx": 0.0, "vy": 0.0, "type": "officer", "hp": 1, "alive": True},
            {"x": 1.0, "y": 1.0, "vx": 0.0, "vy": 0.0, "type": "infantry", "hp": 1, "alive": True},
        ]
        self.game.update(0.016, keys_pressed=KEY_A)
        for _ in range(15):
            self.game.update(0.016)
        self.assertFalse(self.game.enemies[0]["alive"])
        self.assertEqual(self.game.grenades, 6) # 2 + 4 = 6
        self.assertEqual(self.game.score, 100 + 400) # 100 + 100 + 300 = 500

    def test_05_bullets_bounce_off_hardened_bunkers(self):
        # Pillbox/bunker cannot be destroyed by normal bullets
        self.game.enemies = [
            {"x": 7.5, "y": 10.0, "vx": 0.0, "vy": 0.0, "type": "bunker", "hp": 2, "alive": True},
            {"x": 1.0, "y": 1.0, "vx": 0.0, "vy": 0.0, "type": "infantry", "hp": 1, "alive": True},
        ]
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0
        self.game.update(0.016, keys_pressed=KEY_A) # Fire
        self.assertEqual(len(self.game.bullets), 1)

        for _ in range(15):
            self.game.update(0.016) # Bullet hits bunker and vanishes
        self.assertEqual(len(self.game.bullets), 0)
        self.assertTrue(self.game.enemies[0]["alive"])
        self.assertEqual(self.game.enemies[0]["hp"], 2)

    def test_06_lob_grenade_button_b_detonation(self):
        init_grenades = self.game.grenades
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0
        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertEqual(self.game.grenades, init_grenades - 1)
        self.assertEqual(len(self.game.grenade_projectiles), 1)

        # Advance until detonation
        for _ in range(25):
            self.game.update(0.016)
        self.assertEqual(len(self.game.grenade_projectiles), 0)
        self.assertGreaterEqual(len(self.game.explosions), 1)

    def test_07_grenade_explosion_destroys_bunkers(self):
        self.game.px = 7.5
        self.game.py = 10.0
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0
        # Target will be 7.5, 6.0
        self.game.enemies = [
            {"x": 7.5, "y": 6.0, "vx": 0.0, "vy": 0.0, "type": "bunker", "hp": 2, "alive": True},
            {"x": 1.0, "y": 1.0, "vx": 0.0, "vy": 0.0, "type": "infantry", "hp": 1, "alive": True},
        ]
        self.game.update(0.016, keys_pressed=KEY_B) # Lob grenade
        for _ in range(26):
            self.game.update(0.016) # Detonate on bunker
        self.assertFalse(self.game.enemies[0]["alive"])
        self.assertEqual(self.game.score, 300)

    def test_08_rescue_captured_pow(self):
        self.game.pows = [{"x": 7.5, "y": 12.0, "rescued": False}]
        self.game.px = 7.5
        self.game.py = 13.0
        # Move up into POW
        self.game.update(0.2, keys_down=KEY_UP)
        self.assertTrue(self.game.pows[0]["rescued"])
        self.assertEqual(self.game.score, 500)

    def test_09_vertical_advancement_and_screen_scrolling(self):
        self.game.distance = 50.0
        self.game.target_distance = 180.0
        self.game.py = 7.0 # Above py = 8.0 threshold
        self.game.pows = [{"x": 3.0, "y": 5.0, "rescued": False}]
        init_pow_y = self.game.pows[0]["y"]

        self.game.update(0.01) # Triggers scroll
        self.assertEqual(self.game.py, 8.0)
        self.assertAlmostEqual(self.game.distance, 51.0)
        self.assertAlmostEqual(self.game.pows[0]["y"], init_pow_y + 1.0)

    def test_10_breach_fortress_iron_gate_stage_clear_and_render(self):
        # Reach the fortress gate
        self.game.distance = self.game.target_distance
        self.game.px = 7.5
        self.game.py = 5.5
        self.game.facing_x = 0.0
        self.game.facing_y = -1.0 # Target will be 7.5, 1.5 (Fortress gate)

        self.game.update(0.016, keys_pressed=KEY_B)
        for _ in range(26):
            self.game.update(0.016) # Grenade detonates on gate

        self.assertTrue(self.game.gate_breached)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 3000)

        # Test render does not crash and produces valid 16x16x3 buffer
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
