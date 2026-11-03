import unittest
import math
from arcade.game_120_goldminer import (
    Game120GoldMiner,
    STATE_MINING,
    STATE_ROUND_CLEAR,
    STATE_TIME_UP,
    STATE_GAME_OVER,
    CLAW_SWINGING,
    CLAW_EXTENDING,
    CLAW_RETRACTING,
    ITEM_SMALL_GOLD,
    ITEM_LARGE_GOLD,
    ITEM_DIAMOND,
    ITEM_ROCK,
    ITEM_TNT_BARREL,
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


class TestGame120GoldMiner(unittest.TestCase):
    def setUp(self):
        self.game = Game120GoldMiner()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 120)
        self.assertEqual(self.game.name, "黄金矿工")
        self.assertEqual(self.game.english_name, "Gold Miner")
        self.assertEqual(self.game.release_year, 2003)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("简谐摆动绞盘", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_MINING)
        self.assertEqual(self.game.claw_state, CLAW_SWINGING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.target_quota, 600)
        self.assertEqual(self.game.dynamite_count, 2)
        self.assertEqual(self.game.time_remaining, 45.0)

    def test_winch_harmonic_angle_oscillation(self):
        initial_angle = self.game.winch_angle
        # Advance swing
        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.winch_angle != initial_angle or self.game.swing_time > 0.0)
        self.assertTrue(-1.3 <= self.game.winch_angle <= 1.3)

    def test_launch_claw(self):
        self.assertEqual(self.game.claw_state, CLAW_SWINGING)
        # Launch with Key A
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.claw_state, CLAW_EXTENDING)

        # Step extension
        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.claw_dist, 1.2)

    def test_claw_reaches_boundary_and_retracts(self):
        # Launch directly downward (angle = 0)
        self.game.winch_angle = 0.0
        self.game.launch_claw()

        # Step extension until bottom boundary
        while self.game.claw_state == CLAW_EXTENDING:
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.claw_state, CLAW_RETRACTING)

    def test_hook_gold_and_mass_retract(self):
        # Position Small Gold at (7.5, 5.0)
        self.game.items[0]["x"] = 7.5
        self.game.items[0]["y"] = 5.0
        self.game.items[0]["active"] = True

        # Launch straight down
        self.game.winch_angle = 0.0
        self.game.launch_claw()

        # Step until hooked
        for _ in range(15):
            if self.game.hooked_item_idx == 0:
                break
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.hooked_item_idx, 0)
        self.assertEqual(self.game.claw_state, CLAW_RETRACTING)

    def test_deposit_gold_awards_score(self):
        # Hook Small Gold (value = 100)
        self.game.hooked_item_idx = 0
        self.game.claw_state = CLAW_RETRACTING
        self.game.claw_dist = 1.3 # Almost home
        self.game.claw_dir_x = 0.0
        self.game.claw_dir_y = 1.0

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.claw_state, CLAW_SWINGING)
        self.assertEqual(self.game.score, init_score + 100)
        self.assertFalse(self.game.items[0]["active"])

    def test_use_dynamite_detonates_unwanted_rock(self):
        # Hook Rock (item 5)
        self.game.hooked_item_idx = 5
        self.game.claw_state = CLAW_RETRACTING
        self.assertEqual(self.game.dynamite_count, 2)

        # Press B for Dynamite
        self.game.update(0.05, KEY_B, 0)

        self.assertEqual(self.game.dynamite_count, 1)
        self.assertEqual(self.game.hooked_item_idx, -1)
        self.assertFalse(self.game.items[5]["active"])

    def test_tnt_barrel_detonation(self):
        # Position TNT barrel at (7.5, 6.0) and rock nearby at (7.5, 7.0)
        self.game.items[7]["x"] = 7.5
        self.game.items[7]["y"] = 6.0
        self.game.items[7]["active"] = True

        self.game.items[5]["x"] = 7.5
        self.game.items[5]["y"] = 7.0
        self.game.items[5]["active"] = True

        # Extend claw directly into TNT barrel
        self.game.winch_angle = 0.0
        self.game.launch_claw()

        for _ in range(15):
            self.game.update(0.05, 0, 0)
            if not self.game.items[7]["active"]:
                break

        self.assertFalse(self.game.items[7]["active"])
        self.assertFalse(self.game.items[5]["active"]) # Vaporized by blast
        self.assertEqual(self.game.hooked_item_idx, -1) # Nothing hooked

    def test_quota_round_clear(self):
        self.game.score = 750 # Exceeds 600 target quota
        self.game.time_remaining = 0.02

        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)


if __name__ == "__main__":
    unittest.main()
