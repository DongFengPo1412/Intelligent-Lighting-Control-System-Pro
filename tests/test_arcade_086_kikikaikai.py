import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_086_kikikaikai import (
    Game086KiKiKaiKai,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_HERO_DEAD,
    EN_BAKE_NEKO,
    EN_TENGU,
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


class TestGame086KiKiKaiKai(unittest.TestCase):
    def setUp(self):
        self.game = Game086KiKiKaiKai()
        self.game.init()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 86)
        self.assertEqual(self.game.name, "奇奇怪界")
        self.assertEqual(self.game.english_name, "KiKi KaiKai")
        self.assertEqual(self.game.release_year, 1986)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("御币神杖招架", self.game.core_mechanic)

    def test_initial_state(self):
        status = self.game.get_status()
        self.assertEqual(status["state"], STATE_PLAYING)
        self.assertEqual(status["lives"], 3)
        self.assertEqual(status["score"], 0)
        self.assertEqual(self.game.px, 7.5)
        self.assertEqual(self.game.py, 12.0)
        self.assertFalse(status["gohei_active"])

    def test_eight_way_movement(self):
        # Move diagonal up-right
        self.game.update(0.1, KEY_UP | KEY_RIGHT, 0)
        self.assertGreater(self.game.px, 7.5)
        self.assertLess(self.game.py, 12.0)
        self.assertEqual(self.game.facing_x, 1)
        self.assertEqual(self.game.facing_y, -1)

    def test_ofuda_talisman_projectile(self):
        self.game.projectiles = []
        self.game.facing_x = 0
        self.game.facing_y = -1

        # Fire Ofuda with A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(len(self.game.projectiles), 1)
        p = self.game.projectiles[0]
        self.assertTrue(p["is_talisman"])
        self.assertLess(p["vy"], 0.0) # Flying north

    def test_ofuda_destroys_yokai(self):
        self.game.enemies = [{
            "x": 8.0,
            "y": 8.0,
            "type": EN_BAKE_NEKO,
            "hp": 1,
            "active": True,
        }]
        self.game.projectiles = [{
            "x": 8.0,
            "y": 8.2,
            "vx": 0.0,
            "vy": -14.0,
            "is_talisman": True,
            "active": True,
        }]

        old_score = self.game.score
        self.game.check_collisions()
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertGreater(self.game.score, old_score)

    def test_gohei_wand_swing(self):
        self.assertFalse(self.game.is_swinging_gohei())
        # Swing with B
        self.game.update(0.05, KEY_B, 0)
        self.assertTrue(self.game.is_swinging_gohei())
        self.assertGreater(self.game.gohei_timer, 0.0)

    def test_gohei_reflects_enemy_fireball(self):
        self.game.px = 8.0
        self.game.py = 10.0
        self.game.facing_x = 0
        self.game.facing_y = -1

        # Hostile fireball approaching Sayo from y = 8.8 (in front)
        self.game.projectiles = [{
            "x": 8.0,
            "y": 8.8,
            "vx": 0.0,
            "vy": 7.0,  # flying toward Sayo (south)
            "is_talisman": False,
            "active": True,
        }]

        # Swing Gohei wand (B)
        self.game.update(0.05, KEY_B, 0)
        p = self.game.projectiles[0]
        # Fireball reflected! Now belongs to player and flies north!
        self.assertTrue(p["is_talisman"])
        self.assertLess(p["vy"], 0.0)

    def test_gohei_wand_melee_damage(self):
        self.game.px = 8.0
        self.game.py = 10.0
        self.game.facing_x = 0
        self.game.facing_y = -1

        # Yokai standing right in front
        self.game.enemies = [{
            "x": 8.0,
            "y": 8.8,
            "type": EN_TENGU,
            "hp": 2,
            "active": True,
        }]

        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.enemies[0]["hp"], 1)

    def test_stage_clear_victory(self):
        self.game.yokai_defeated = 15
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 6000)

    def test_render_framebuffer(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertIsInstance(fb, bytes)


if __name__ == "__main__":
    unittest.main()
