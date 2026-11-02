import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_087_streetsofrage import (
    Game087StreetsOfRage,
    STATE_STREET_BRAWL,
    STATE_POLICE_BACKUP,
    STATE_STAGE_CLEAR,
    STATE_HERO_DEAD,
    ATK_NONE,
    ATK_PUNCH,
    ATK_FLYING_KICK,
    ATK_SUPLEX,
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


class TestGame087StreetsOfRage(unittest.TestCase):
    def setUp(self):
        self.game = Game087StreetsOfRage()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 87)
        self.assertEqual(self.game.name, "怒之铁拳")
        self.assertEqual(self.game.english_name, "Streets of Rage")
        self.assertEqual(self.game.release_year, 1991)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("呼叫警车火箭筒", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_STREET_BRAWL)
        self.assertEqual(status["hero_hp"], 100)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["backup_calls"], 1)
        self.assertEqual(self.game.px, 3.5)
        self.assertEqual(self.game.py, 10.5)

    def test_street_movement(self):
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 3.5)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.py, 10.5)

    def test_punch_combo(self):
        self.game.px = 4.0
        self.game.py = 10.0
        self.game.facing = 1

        # Place thug in front
        self.game.thugs[0]["x"] = 5.2
        self.game.thugs[0]["y"] = 10.0
        self.game.thugs[0]["hp"] = 3
        self.game.thugs[0]["active"] = True

        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.atk_state, ATK_PUNCH)
        self.assertEqual(self.game.thugs[0]["hp"], 2)

    def test_german_suplex_back_grapple(self):
        self.game.px = 4.0
        self.game.py = 10.0
        self.game.facing = 1

        # Place thug in tight grapple contact (< 0.9)
        self.game.thugs[0]["x"] = 4.6
        self.game.thugs[0]["y"] = 10.0
        self.game.thugs[0]["hp"] = 3
        self.game.thugs[0]["active"] = True

        old_score = self.game.score
        # Suplex with A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.atk_state, ATK_SUPLEX)
        self.assertEqual(self.game.thugs[0]["hp"], 0)
        self.assertFalse(self.game.thugs[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_flying_jump_kick(self):
        self.game.px = 4.0
        self.game.py = 10.0
        self.game.facing = 1

        # Press B for jump kick
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.atk_state, ATK_FLYING_KICK)
        self.assertGreater(self.game.px, 4.0)

    def test_police_backup_call(self):
        self.assertEqual(self.game.backup_calls, 1)
        # Call police with A + B
        self.game.update(0.05, KEY_A | KEY_B, 0)
        self.assertEqual(self.game.backup_calls, 0)
        self.assertEqual(self.game.state, STATE_POLICE_BACKUP)

    def test_napalm_rocket_full_screen_explosion(self):
        self.game.backup_calls = 1
        self.game.update(0.05, KEY_A | KEY_B, 0)

        # Advance rocket to center of screen (x >= 8.0)
        for _ in range(20):
            self.game.update(0.05, 0, 0)
            if self.game.explosion_timer > 0.0:
                break

        self.assertGreater(self.game.explosion_timer, 0.0)
        # All normal thugs should have been wiped out by 6 damage
        for t in self.game.thugs:
            self.assertFalse(t["active"])

    def test_stage_clear_victory(self):
        self.game.thugs_defeated = 7
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 10000)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
