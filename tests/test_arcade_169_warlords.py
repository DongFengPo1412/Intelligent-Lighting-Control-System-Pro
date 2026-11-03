"""
Unit tests for Game #169: 军阀混战 / 四国城堡 (Warlords - 1980 Atari / Carla Meninsky)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_169_warlords import (
    Game169Warlords,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_ROUND_CLEAR, STATE_PLAYER_ELIMINATED, STATE_GAME_OVER
)

class TestArcade169Warlords(unittest.TestCase):
    def setUp(self):
        self.game = Game169Warlords()

    def test_01_init_state_and_kings(self):
        """Verify initial state, round=1, 4 warlord kings alive, bricks intact, ball in center."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.round, 1)
        self.assertEqual(len(self.game.warlords), 4)
        for w in self.game.warlords:
            self.assertTrue(w["alive"])
        self.assertEqual(len(self.game.bricks[0]), 6)
        self.assertAlmostEqual(self.game.ball["x"], 7.5)
        self.assertAlmostEqual(self.game.ball["y"], 7.5)

    def test_02_player_shield_arc_movement(self):
        """Test moving shield slider along quadrant perimeter arc."""
        init_t = self.game.warlords[0]["shield_t"]
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertLess(self.game.warlords[0]["shield_t"], init_t)

        for _ in range(20):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.warlords[0]["shield_t"], 1.0)

    def test_03_ball_reflection_off_screen_bounds(self):
        """Verify fireball reflects at arena bounds."""
        self.game.ball["x"] = 15.0
        self.game.ball["vx"] = 5.0
        self.game.update(0.02)
        self.assertLessEqual(self.game.ball["vx"], 0.0)

    def test_04_ball_shield_bounce(self):
        """Verify fireball deflecting off shield away from king corner."""
        wid = 0
        sx, sy = self.game.get_shield_coord(wid, self.game.warlords[wid]["shield_t"])
        self.game.ball["x"] = sx
        self.game.ball["y"] = sy
        self.game.ball["vx"] = -4.0
        self.game.ball["vy"] = 4.0

        old_score = self.game.score
        self.game.update(0.01)
        # Should reflect outward towards center
        self.assertGreater(self.game.ball["vx"], 0.0)
        self.assertGreater(self.game.score, old_score)

    def test_05_player_catch_and_sling_fireball(self):
        """Holding KEY_A catches ball in shield, releasing KEY_A slings ball."""
        sx, sy = self.game.get_shield_coord(0, self.game.warlords[0]["shield_t"])
        self.game.ball["x"] = sx
        self.game.ball["y"] = sy

        # Catch with KEY_A
        self.game.update(0.01, keys_down=KEY_A, keys_pressed=0)
        self.assertEqual(self.game.ball["caught_by"], 0)

        # Release with press KEY_A
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(self.game.ball["caught_by"], -1)
        self.assertGreater(self.game.ball["vx"], 0.0) # Slung toward center!

    def test_06_brick_destruction_and_score(self):
        """Ball colliding with brick destroys the brick and awards score."""
        target_brick = (3, 1) # CPU 1 top-left brick
        self.assertIn(target_brick, self.game.bricks[1])
        self.game.ball["x"] = 3.0
        self.game.ball["y"] = 1.0
        old_score = self.game.score

        self.game.update(0.01)
        self.assertNotIn(target_brick, self.game.bricks[1])
        self.assertEqual(self.game.score, old_score + 100)

    def test_07_enemy_king_assassination(self):
        """Ball striking enemy king eliminates that CPU warlord (+1000 score)."""
        cpu_w = self.game.warlords[2] # Top-Right
        self.assertTrue(cpu_w["alive"])
        self.game.ball["x"] = cpu_w["king_x"]
        self.game.ball["y"] = cpu_w["king_y"]
        old_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(cpu_w["alive"])
        self.assertEqual(self.game.score, old_score + 1000)

    def test_08_player_king_slain_elimination(self):
        """Ball striking player king eliminates player and triggers STATE_PLAYER_ELIMINATED."""
        player_w = self.game.warlords[0]
        self.game.ball["x"] = player_w["king_x"]
        self.game.ball["y"] = player_w["king_y"]

        self.game.update(0.01)
        self.assertFalse(player_w["alive"])
        self.assertEqual(self.game.state, STATE_PLAYER_ELIMINATED)

    def test_09_all_opponents_slain_round_clear(self):
        """Eliminating all 3 CPU kings triggers round clear with 3000 bonus."""
        self.game.warlords[1]["alive"] = False
        self.game.warlords[2]["alive"] = False
        # Strike last CPU king
        cpu3 = self.game.warlords[3]
        self.game.ball["x"] = cpu3["king_x"]
        self.game.ball["y"] = cpu3["king_y"]
        old_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(cpu3["alive"])
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)
        self.assertGreater(self.game.score, old_score + 3500)

    def test_10_game_over_and_rendering(self):
        """Player elimination transitions to GAME_OVER after timer; frame is 768 bytes."""
        self.game.state = STATE_PLAYER_ELIMINATED
        self.game.state_timer = 0.5
        self.game.update(0.6)

        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Render frame
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()

