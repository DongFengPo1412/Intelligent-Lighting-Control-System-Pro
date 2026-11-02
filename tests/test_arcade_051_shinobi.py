import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_051_shinobi import (
    Game051Shinobi,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    KEY_SELECT,
)


class TestArcade051Shinobi(unittest.TestCase):
    def setUp(self):
        self.game = Game051Shinobi()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 51)
        self.assertEqual(self.game.english_name, "Shinobi")
        self.assertEqual(self.game.release_year, 1987)
        cart = ArcadeRegistry.get_cartridge(51)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game051Shinobi)

    def test_horizontal_movement_and_crouch(self):
        initial_x = self.game.player_x
        # Move right
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, initial_x)
        self.assertEqual(self.game.player_facing, 1)

        # Crouch
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertTrue(self.game.is_crouching)

    def test_tier_leap(self):
        # Start at lower tier 1
        self.assertEqual(self.game.player_tier, 1)
        self.assertFalse(self.game.is_leaping_tier)

        # Press B to leap
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.is_leaping_tier)

        # Advance leap past completion
        for _ in range(10):
            self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.is_leaping_tier)
        self.assertEqual(self.game.player_tier, 0)  # Now on upper tier

    def test_ranged_shuriken_throw(self):
        # Clear nearby enemies to force ranged shuriken
        for e in self.game.enemies:
            e["active"] = False

        self.assertEqual(len(self.game.shurikens), 0)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.shurikens), 1)
        shuriken = self.game.shurikens[0]
        self.assertTrue(shuriken["is_player"])
        self.assertFalse(shuriken["is_gunshot"])
        self.assertEqual(shuriken["tier"], self.game.player_tier)

    def test_melee_slash(self):
        # Place enemy right in front of player
        self.game.player_x = 5.0
        self.game.player_tier = 1
        for e in self.game.enemies:
            e["active"] = False
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = 5.8
        self.game.enemies[0]["tier"] = 1
        self.game.enemies[0]["health"] = 2

        self.game.update(0.05, KEY_A, 0)
        self.assertTrue(self.game.is_melee_slashing)
        self.assertFalse(self.game.enemies[0]["active"])  # 2 damage kills health 2
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_hostage_rescue_and_gun_upgrade(self):
        self.assertFalse(self.game.has_gun_upgrade)
        self.game.player_tier = 0
        self.game.player_x = 6.0  # Hostage 0 is at (6.0, tier 0)

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.hostages[0]["rescued"])
        self.assertTrue(self.game.has_gun_upgrade)
        self.assertEqual(self.game.hostages_rescued, 1)

        # Now shoot with gun upgrade
        for e in self.game.enemies:
            e["active"] = False
        self.game.shurikens.clear()
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.shurikens), 1)
        self.assertTrue(self.game.shurikens[0]["is_gunshot"])

    def test_ninjutsu_screen_wipe(self):
        self.assertTrue(self.game.has_ninjutsu)
        active_count = sum(1 for e in self.game.enemies if e["active"])
        self.assertGreater(active_count, 0)

        # Trigger Ninjutsu via KEY_SELECT
        self.game.update(0.05, KEY_SELECT, 0)
        self.assertFalse(self.game.has_ninjutsu)
        self.assertGreater(self.game.ninjutsu_flash_timer, 0.0)
        remaining_active = sum(1 for e in self.game.enemies if e["active"])
        self.assertEqual(remaining_active, 0)

    def test_crouch_dodging_projectile(self):
        self.game.player_x = 5.0
        self.game.player_tier = 1
        # Add incoming enemy shuriken right at player
        self.game.shurikens.append({
            "x": 5.1,
            "tier": 1,
            "vx": -4.0,
            "is_gunshot": False,
            "is_player": False,
            "active": True
        })

        # Crouch to dodge
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertEqual(self.game.state, STATE_PLAYING)  # Still alive!

    def test_enemy_contact_causes_death(self):
        self.game.player_x = 5.0
        self.game.player_tier = 1
        for e in self.game.enemies:
            e["active"] = False
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = 5.2
        self.game.enemies[0]["tier"] = 1

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)
        self.assertEqual(self.game.lives, 2)

    def test_render_and_status(self):
        fb = self.game.render()
        self.assertIsInstance(fb, bytes)
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 51)
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["lives"], 3)


if __name__ == "__main__":
    unittest.main()
