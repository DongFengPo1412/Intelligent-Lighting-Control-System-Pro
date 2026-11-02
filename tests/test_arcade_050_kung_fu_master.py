"""
Comprehensive Unit Tests for Arcade Cartridge #050: 功夫大师 (Kung-Fu Master 1984 / Irem)
"""

import unittest
from arcade.arcade_registry import ArcadeRegistry
from arcade.game_050_kung_fu_master import (
    Game050KungFuMaster,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    TYPE_GRIPPER,
    TYPE_KNIFE_THROWER,
    TYPE_BOSS_STAFF,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade050KungFuMaster(unittest.TestCase):
    def setUp(self):
        self.game = Game050KungFuMaster()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 50)
        self.assertEqual(self.game.release_year, 1984)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertEqual(self.game.name, "功夫大师")
        self.assertIn("Kung-Fu Master", self.game.english_name)

        cart = ArcadeRegistry.get_cartridge(50)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game050KungFuMaster)

    def test_initial_state_and_dojo(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.player_health, 100)
        self.assertEqual(self.game.enemies_defeated, 0)
        self.assertEqual(self.game.num_gripping, 0)
        self.assertEqual(self.game.player_x, 2.0)
        self.assertEqual(len(self.game.enemies), 4)

    def test_three_tier_attacks(self):
        # 1. Standing Punch (KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.attack_stance, 1)

        self.game.attack_timer = 0.0

        # 2. Standing Mid Kick (KEY_B)
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.attack_stance, 2)

        self.game.attack_timer = 0.0

        # 3. Crouching Low Sweep (KEY_DOWN + KEY_B)
        self.game.update(0.05, KEY_DOWN | KEY_B, 0)
        self.assertEqual(self.game.attack_stance, 3)

        self.game.attack_timer = 0.0

        # 4. Jumping Jump Kick (In air + KEY_B)
        self.game.is_jumping = True
        self.game.jump_y_offset = 2.0
        self.game.jump_vy = 5.0
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.attack_stance, 4)

    def test_crouch_and_jump_controls(self):
        # Crouch (KEY_DOWN)
        self.game.is_jumping = False
        self.game.update(0.05, KEY_DOWN, 0)
        self.assertTrue(self.game.is_crouching)

        # Jump (KEY_UP)
        self.game.update(0.05, KEY_UP, 0)
        self.assertTrue(self.game.is_jumping)
        self.assertGreater(self.game.jump_vy, 0.0)

    def test_mid_air_dagger_interception(self):
        # Dagger flying towards player at x=2.8
        self.game.player_x = 2.0
        self.game.player_facing = 1
        self.game.daggers = [{"x": 2.8, "y": 11.0, "vx": -8.5, "active": True}]

        prev_score = self.game.score
        # Execute punch to intercept
        self.game.execute_punch()
        self.game.check_hitboxes()

        self.assertFalse(self.game.daggers[0]["active"])
        self.assertEqual(self.game.score, prev_score + 100)

    def test_gripper_hug_and_shake_off(self):
        self.game.player_x = 5.0
        self.game.enemies[0]["x"] = 5.2
        self.game.enemies[0]["type"] = TYPE_GRIPPER
        self.game.enemies[0]["active"] = True

        self.game.update_enemies(0.05)
        # Clamped!
        self.assertTrue(self.game.enemies[0]["is_gripping"])
        self.assertEqual(self.game.num_gripping, 1)

        # Wiggle 3 times to shake off
        self.game.shake_off_grippers()
        self.game.shake_off_grippers()
        self.game.shake_off_grippers()

        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.num_gripping, 0)

    def test_striking_enemies_deals_damage(self):
        self.game.player_x = 5.0
        self.game.player_facing = 1
        self.game.enemies[0]["x"] = 5.8
        self.game.enemies[0]["health"] = 15
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["is_gripping"] = False

        self.game.execute_kick()
        self.game.check_hitboxes()

        # Defeated!
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertEqual(self.game.enemies_defeated, 1)

    def test_damage_and_player_death(self):
        self.game.player_health = 10
        self.game.daggers = [{"x": 2.0, "y": 11.0, "vx": -8.0, "active": True}]
        self.game.player_x = 2.0
        self.game.is_crouching = False
        self.game.is_jumping = False

        self.game.check_hitboxes()
        self.assertEqual(self.game.player_health, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_boss_defeat_and_stage_victory(self):
        # Deactivate regular thugs
        self.game.enemies[0]["active"] = False
        self.game.enemies[1]["active"] = False
        self.game.enemies[2]["active"] = False
        self.game.enemies_defeated = 4

        self.game.player_x = 10.0
        self.game.player_facing = 1
        self.game.enemies[3]["x"] = 10.8
        self.game.enemies[3]["type"] = TYPE_BOSS_STAFF
        self.game.enemies[3]["health"] = 10  # Low HP
        self.game.enemies[3]["active"] = True

        self.game.execute_kick()
        self.game.check_hitboxes()

        self.assertFalse(self.game.enemies[3]["active"])
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 768)
        self.assertIsInstance(fb, bytes)
        # Check dojo wooden floor at row 12, col 0: (110, 65, 25)
        f_idx = (12 * 16 + 0) * 3
        self.assertEqual(fb[f_idx + 0], 110)
        self.assertEqual(fb[f_idx + 1], 65)
        self.assertEqual(fb[f_idx + 2], 25)
        # Check gold pillar at row 2, col 4: (183, 149, 11)
        p_idx = (2 * 16 + 4) * 3
        self.assertEqual(fb[p_idx + 0], 183)
        self.assertEqual(fb[p_idx + 1], 149)
        self.assertEqual(fb[p_idx + 2], 11)


if __name__ == "__main__":
    unittest.main()
