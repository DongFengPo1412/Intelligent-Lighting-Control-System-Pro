"""
Unit Tests for Game #191: 快打旋风 (Final Fight - 1989 Capcom)
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
from arcade.game_191_finalfight import (
    Game191FinalFight,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_HAGGAR_KO,
    STATE_GAME_OVER,
)

class TestArcade191FinalFight(unittest.TestCase):
    def setUp(self):
        self.game = Game191FinalFight()

    def test_01_metadata_and_initialization(self):
        self.assertEqual(self.game.game_id, 191)
        self.assertEqual(self.game.name, "快打旋风")
        self.assertEqual(self.game.english_name, "Final Fight")
        self.assertEqual(self.game.release_year, 1989)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.hp, 100.0)
        self.assertEqual(len(self.game.enemies), 3)

    def test_02_2_5d_belt_scroll_movement(self):
        init_x = self.game.px
        init_y = self.game.py
        self.game.update(0.1, keys_down=KEY_RIGHT | KEY_UP)
        self.assertGreater(self.game.px, init_x)
        self.assertLess(self.game.py, init_y)
        self.assertEqual(self.game.facing, 1)

        # Clamping
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreaterEqual(self.game.px, 1.0)
        self.assertEqual(self.game.facing, -1)

        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_UP)
        self.assertGreaterEqual(self.game.py, 8.0)

    def test_03_basic_punch_combo(self):
        self.game.px = 7.0
        self.game.py = 10.0
        self.game.facing = 1
        # Isolate thug directly in punch range (dist = 0.8 > 0.6 grapple)
        self.game.enemies[0]["x"] = 7.8
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["state"] = "normal"
        init_hp = self.game.enemies[0]["hp"]

        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_punching)
        self.assertLess(self.game.enemies[0]["hp"], init_hp)
        self.assertEqual(self.game.score, 200)

    def test_04_grapple_auto_catch(self):
        self.game.px = 7.5
        self.game.py = 10.0
        self.game.enemies[0]["x"] = 7.8 # Within 0.6 distance (0.3)
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["state"] = "normal"
        self.assertIsNone(self.game.grabbed_enemy_idx)

        self.game.update(0.016)
        # Haggar catches enemy into grapple
        self.assertEqual(self.game.grabbed_enemy_idx, 0)
        self.assertEqual(self.game.enemies[0]["state"], "grabbed")

    def test_05_spinning_piledriver_slam_and_shockwave(self):
        # Setup grapple
        self.game.px = 8.0
        self.game.py = 10.0
        self.game.grabbed_enemy_idx = 0
        self.game.enemies[0]["state"] = "grabbed"
        self.game.enemies[0]["hp"] = 50.0

        # Nearby second enemy to receive splash damage
        self.game.enemies[1]["x"] = 8.5
        self.game.enemies[1]["y"] = 10.0
        self.game.enemies[1]["state"] = "normal"
        init_e1_hp = self.game.enemies[1]["hp"]

        # Press A to launch Spinning Piledriver!
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.is_piledriving)

        # Execute through full aerial ascent and slam (0.45s)
        for _ in range(30):
            self.game.update(0.016)

        self.assertFalse(self.game.is_piledriving)
        self.assertIsNone(self.game.grabbed_enemy_idx)
        # Grabbed victim took 40 damage
        self.assertEqual(self.game.enemies[0]["hp"], 10.0)
        self.assertEqual(self.game.enemies[0]["state"], "knockdown")
        # Nearby thug received shockwave damage
        self.assertLess(self.game.enemies[1]["hp"], init_e1_hp)
        self.assertGreaterEqual(self.game.score, 1500)

    def test_06_spinning_clothesline_desperation_invincibility(self):
        init_hp = self.game.hp
        self.game.px = 8.0
        self.game.py = 10.0
        self.game.enemies[0]["x"] = 9.0
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["state"] = "normal"
        init_e0_hp = self.game.enemies[0]["hp"]

        # Press B for Clothesline
        self.game.update(0.016, keys_pressed=KEY_B)
        self.assertTrue(self.game.is_spinning)
        self.assertEqual(self.game.hp, init_hp - 8.0) # Consumed 8 HP

        # Enemy is hit and knocked down
        self.assertLess(self.game.enemies[0]["hp"], init_e0_hp)
        self.assertEqual(self.game.enemies[0]["state"], "knockdown")
        self.assertGreaterEqual(self.game.score, 500)

    def test_07_break_barrel_drops_roast_chicken(self):
        self.assertFalse(self.game.barrel["broken"])
        self.assertFalse(self.game.barrel["item_active"])

        self.game.px = 5.0
        self.game.py = 12.0
        self.game.facing = 1 # Towards barrel at (6.0, 12.0)

        # Punch barrel
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertTrue(self.game.barrel["broken"])
        self.assertTrue(self.game.barrel["item_active"])
        self.assertEqual(self.game.score, 300)

    def test_08_collect_roast_chicken_recovers_health(self):
        self.game.barrel["broken"] = True
        self.game.barrel["item_active"] = True
        self.game.barrel["item_x"] = 7.5
        self.game.barrel["item_y"] = 12.0

        # Haggar wounded
        self.game.hp = 40.0
        self.game.px = 7.5
        self.game.py = 12.0

        self.game.update(0.016)
        self.assertFalse(self.game.barrel["item_active"])
        self.assertEqual(self.game.hp, 40.0 + 35.0) # Restored 35 HP!
        self.assertEqual(self.game.score, 1000)

    def test_09_boss_damnd_defeated_stage_clear(self):
        # Eliminate regular thugs first
        self.game.enemies[0]["alive"] = False
        self.game.enemies[1]["alive"] = False

        boss = [e for e in self.game.enemies if e["type"] == "boss"][0]
        boss["hp"] = 5.0
        boss["x"] = 7.8
        boss["y"] = 10.0
        boss["state"] = "normal"

        self.game.px = 7.0
        self.game.py = 10.0
        self.game.facing = 1

        # Punch boss
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertFalse(boss["alive"])
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 13000)

    def test_10_render_and_haggar_ko_reset(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        self.game.hp = 0.0
        self.game.update(0.016)

        self.assertEqual(self.game.state, STATE_HAGGAR_KO)
        self.assertEqual(self.game.lives, 2)

        # Reset test
        self.game.state = STATE_GAME_OVER
        self.game.update(0.016, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.hp, 100.0)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
