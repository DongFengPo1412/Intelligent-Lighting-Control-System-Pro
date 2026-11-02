import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_080_cadillacs import (
    Game080Cadillacs,
    STATE_PLAYING,
    STATE_CADILLAC_DRIVE,
    STATE_PLAYER_DEAD,
    STATE_VICTORY,
    WEAPON_FIST,
    WEAPON_UZI,
    WEAPON_BAZOOKA,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)


class TestGame080Cadillacs(unittest.TestCase):
    def setUp(self):
        self.game = Game080Cadillacs()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 80)
        self.assertEqual(self.game.name, "恐龙快打")
        self.assertEqual(self.game.english_name, "Cadillacs and Dinosaurs")
        self.assertEqual(self.game.release_year, 1993)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("枪械捡拾射击", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["player_hp"], 100)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["current_weapon"], WEAPON_FIST)
        self.assertFalse(status["dino_enraged"])
        self.assertEqual(self.game.px, 3.0)
        self.assertEqual(self.game.py, 10.0)

    def test_player_movement_and_jump(self):
        # Walk right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 3.0)
        self.assertEqual(self.game.facing, 1)

        # Jump with B
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.in_air)
        self.assertLess(self.game.pvy, 0.0)

    def test_weapon_pickup_and_fire(self):
        # Move onto Uzi drop at (7.0, 11.0)
        self.game.px = 7.0
        self.game.py = 11.0
        self.assertTrue(self.game.drops[0]["active"])

        # Press A to pick up weapon
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.current_weapon, WEAPON_UZI)
        self.assertEqual(self.game.weapon_ammo, 15)
        self.assertFalse(self.game.drops[0]["active"])

        # Next A press fires weapon
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.weapon_ammo, 14)
        self.assertEqual(len(self.game.bullets), 1)

    def test_dino_enrage_and_calm_mechanic(self):
        # Position player in front of calm dino
        self.game.px = self.game.dino["x"] - 1.5
        self.game.py = self.game.dino["y"]
        self.assertFalse(self.game.dino["enraged"])

        # Punch dino with A
        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.dino["enraged"])

        # Whirlwind kick calms dino back down
        self.game.update(0.05, KEY_A | KEY_B, 0)
        self.assertFalse(self.game.dino["enraged"])

    def test_dino_tramples_enemies(self):
        self.game.dino["enraged"] = True
        self.game.dino["x"] = 5.0
        self.game.dino["y"] = 9.0
        self.game.dino["vx"] = 5.0

        # Place enemy right in front of charging dino
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 9.0
        self.game.enemies[0]["active"] = True

        self.game.update(0.1, 0, 0)
        # Enemy trampled!
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertGreater(self.game.score, 0)

    def test_whirlwind_kick(self):
        old_hp = self.game.player_hp
        self.game.px = 5.0
        self.game.py = 9.0

        # Place enemy close
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 9.0
        self.game.enemies[0]["hp"] = 1
        self.game.enemies[0]["active"] = True

        # Execute whirlwind kick (A + B)
        self.game.update(0.05, KEY_A | KEY_B, 0)
        self.assertEqual(self.game.player_hp, old_hp - 10)
        self.assertFalse(self.game.enemies[0]["active"])

    def test_cadillac_drive_trigger(self):
        self.game.enemies_defeated = 8
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CADILLAC_DRIVE)

        # Update drive across screen
        for _ in range(40):
            self.game.update(0.1, 0, 0)
            if self.game.state == STATE_VICTORY:
                break

        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 5000)

    def test_player_damage_and_death(self):
        self.game.player_hp = 1
        # Place enemy touching player
        self.game.enemies[0]["x"] = self.game.px
        self.game.enemies[0]["y"] = self.game.py
        self.game.enemies[0]["active"] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.player_hp, 100)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
