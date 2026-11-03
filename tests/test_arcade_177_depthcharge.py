# -*- coding: utf-8 -*-
import unittest
from arcade.game_177_depthcharge import (
    Game177Depthcharge,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_SHIP_SUNK,
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

class TestArcade177Depthcharge(unittest.TestCase):
    def setUp(self):
        self.game = Game177Depthcharge()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 177)
        self.assertEqual(self.game.name, "深水炸弹")
        self.assertEqual(self.game.english_name, "Depthcharge")
        self.assertEqual(self.game.release_year, 1977)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(len(self.game.subs), 3)

    def test_02_destroyer_lateral_cruise_and_clamping(self):
        self.game.px = 7.5
        # Move left
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.px, 7.5)

        # Clamping left
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.px, 1.5)

        # Clamping right
        for _ in range(50):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.px, 14.5)

    def test_03_drop_port_depth_charge(self):
        self.assertEqual(len(self.game.charges), 0)
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.charges), 1)
        c = self.game.charges[0]
        self.assertLess(c["x"], self.game.px) # Port side

    def test_04_drop_starboard_depth_charge(self):
        self.assertEqual(len(self.game.charges), 0)
        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertEqual(len(self.game.charges), 1)
        c = self.game.charges[0]
        self.assertGreater(c["x"], self.game.px) # Starboard side

    def test_05_depth_charge_sinks_downward(self):
        self.game.charges.append({
            "x": 7.5,
            "y": 4.0,
            "vy": 5.0,
            "active": True,
        })
        self.game.update(0.1)
        self.assertGreater(self.game.charges[0]["y"], 4.0)

    def test_06_intercept_shallow_sub_scoring(self):
        sub = self.game.subs[0] # Tier 0 shallow sub
        sub["x"] = 7.0
        sub["y"] = 6.0
        sub["alive"] = True

        # Drop charge right on sub
        self.game.charges.append({
            "x": 7.0,
            "y": 5.8,
            "vy": 5.0,
            "active": True,
        })
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(sub["alive"])
        self.assertEqual(self.game.score, initial_score + 300)

    def test_07_intercept_deep_trench_sub_scoring(self):
        sub = self.game.subs[2] # Tier 2 deep sub
        sub["x"] = 10.0
        sub["y"] = 14.0
        sub["alive"] = True

        self.game.charges.append({
            "x": 10.0,
            "y": 13.8,
            "vy": 5.0,
            "active": True,
        })
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(sub["alive"])
        self.assertEqual(self.game.score, initial_score + 100)

    def test_08_rising_torpedo_sinks_destroyer(self):
        self.game.px = 7.5
        self.game.py = 2.0
        self.game.torpedoes.append({
            "x": 7.5,
            "y": 2.5,
            "vy": -5.0,
        })
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_SHIP_SUNK)

    def test_09_all_subs_destroyed_stage_clear(self):
        # Kill first 2 subs
        self.game.subs[0]["alive"] = False
        self.game.subs[1]["alive"] = False
        # Destroy final sub with depth charge
        last = self.game.subs[2]
        self.game.charges.append({
            "x": last["x"],
            "y": last["y"] - 0.2,
            "vy": 5.0,
            "active": True,
        })

        self.game.update(0.05)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 1000)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_SHIP_SUNK
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
