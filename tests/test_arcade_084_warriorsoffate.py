import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_084_warriorsoffate import (
    Game084WarriorsOfFate,
    STATE_BATTLE,
    STATE_EATING_BONUS,
    STATE_STAGE_CLEAR,
    STATE_HERO_DEAD,
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


class TestGame084WarriorsOfFate(unittest.TestCase):
    def setUp(self):
        self.game = Game084WarriorsOfFate()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 84)
        self.assertEqual(self.game.name, "吞食天地")
        self.assertEqual(self.game.english_name, "Warriors of Fate")
        self.assertEqual(self.game.release_year, 1992)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("战马骑乘长矛突刺冲锋", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_BATTLE)
        self.assertEqual(status["hero_hp"], 100)
        self.assertEqual(status["lives"], 3)
        self.assertTrue(status["mounted"])
        self.assertEqual(self.game.hx, 3.0)
        self.assertEqual(self.game.hy, 10.0)

    def test_mounted_movement_speed(self):
        # Mounted movement
        self.game.update(0.1, KEY_RIGHT, 0)
        mounted_delta = self.game.hx - 3.0

        # Dismount and measure movement
        self.game.mounted = False
        self.game.hx = 3.0
        self.game.update(0.1, KEY_RIGHT, 0)
        dismounted_delta = self.game.hx - 3.0

        self.assertGreater(mounted_delta, dismounted_delta)

    def test_spear_thrust_attack(self):
        self.game.hx = 5.0
        self.game.hy = 9.0
        self.game.facing = 1

        # Place enemy within spear reach (dx = 2.0 < 2.6)
        self.game.enemies[0]["x"] = 7.0
        self.game.enemies[0]["y"] = 9.0
        self.game.enemies[0]["hp"] = 2
        self.game.enemies[0]["active"] = True

        # Spear thrust with A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.enemies[0]["hp"], 1)
        self.assertGreater(self.game.enemies[0]["x"], 7.0) # pushed back

    def test_cavalry_charge(self):
        self.game.facing = 1
        self.assertFalse(self.game.charging)

        # Attack with forward held (A + RIGHT)
        self.game.update(0.05, KEY_A | KEY_RIGHT, 0)
        self.assertTrue(self.game.charging)
        self.assertGreater(self.game.charge_timer, 0.0)

    def test_horse_stampede(self):
        self.game.hx = 5.0
        self.game.hy = 9.0
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 9.0
        self.game.enemies[0]["hp"] = 2
        self.game.enemies[0]["active"] = True

        # Horse rear stampede (B)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.enemies[0]["hp"], 1)
        self.assertGreater(self.game.enemies[0]["x"], 6.0)

    def test_dismount_and_remount(self):
        self.game.hero_hp = 40
        self.game.enemies[0]["x"] = self.game.hx
        self.game.enemies[0]["y"] = self.game.hy
        self.game.enemies[0]["active"] = True

        # Taking damage while HP < 50 dismounts hero
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.mounted)

        # Move enemy away and press B to remount
        self.game.enemies[0]["x"] = 15.0
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.mounted)

    def test_boss_defeat_triggers_eating_stage(self):
        self.game.enemies[0]["is_boss"] = True
        self.game.enemies[0]["hp"] = 1
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 10.0
        self.game.enemies[0]["active"] = True

        self.game.hx = 5.0
        self.game.hy = 10.0
        self.game.facing = 1

        # Defeat Boss!
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.state, STATE_EATING_BONUS)

    def test_eating_bonus_mashing(self):
        self.game.start_bonus_stage()
        self.assertEqual(self.game.baozi_eaten, 0)

        # Mash A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.baozi_eaten, 1)

        # Mash B
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.baozi_eaten, 2)
        self.assertGreater(self.game.score, 0)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
