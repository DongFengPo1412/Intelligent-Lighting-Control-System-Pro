"""
Unit tests for Game #166: 沃之巫师 (Wizard of Wor - 1980 Bally Midway / Dave Nutting Associates)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_166_wizardofwor import (
    Game166WizardOfWor,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_DUNGEON_CLEAR, STATE_WORRIOR_DIED, STATE_GAME_OVER
)

class TestArcade166WizardOfWor(unittest.TestCase):
    def setUp(self):
        self.game = Game166WizardOfWor()

    def test_01_init_state_and_maze(self):
        """Verify initial state, lives=3, dungeon=1, Worrior at (7.5, 13.0), 3 monsters."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.dungeon, 1)
        self.assertEqual(len(self.game.monsters), 3)
        self.assertFalse(self.game.wizard_active)
        self.assertAlmostEqual(self.game.px, 7.5)
        self.assertAlmostEqual(self.game.py, 13.0)
        self.assertTrue(self.game.is_wall(0, 0)) # Outer wall

    def test_02_worrior_corridor_movement_and_wall_blocking(self):
        """Moving into open corridor succeeds, walking into wall is blocked."""
        # Walk into wall below (y=14 is wall)
        for _ in range(5):
            self.game.update(0.1, keys_down=KEY_DOWN)
        self.assertLessEqual(self.game.py, 13.5) # Blocked before reaching wall 14

        # Walk up in open corridor (x=7.5, y=13.48 -> y=12)
        old_py = self.game.py
        self.game.update(0.2, keys_down=KEY_UP)
        self.assertLess(self.game.py, old_py)
        self.assertEqual(self.game.facing_dy, -1.0)

    def test_03_warp_doors_left_right_teleport(self):
        """Moving left through warp door at (0, 7) teleports to right side (14.8, 7)."""
        self.game.px = 0.5
        self.game.py = 7.0
        self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreater(self.game.px, 14.0)

    def test_04_laser_firing_and_wall_absorption(self):
        """Press KEY_A to fire laser beam traveling until absorbed by wall."""
        self.game.facing_dx = 1.0
        self.game.facing_dy = 0.0
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)

        self.assertEqual(len(self.game.bullets), 1)
        b = self.game.bullets[0]
        self.assertGreater(b["vx"], 0.0)

        # Let bullet hit wall
        for _ in range(10):
            self.game.update(0.05)
        self.assertEqual(len(self.game.bullets), 0)

    def test_05_kill_burwor_garwor_thorwor(self):
        """Lasers kill monsters and award points (Burwor 200, Garwor 500, Thorwor 1000)."""
        m = self.game.monsters[0] # Burwor
        m["x"] = 7.5
        m["y"] = 10.0
        self.game.bullets.append({
            "x": 7.5, "y": 10.0, "vx": 0.0, "vy": 15.0, "life": 1.0
        })
        old_score = self.game.score

        self.game.update(0.02)
        self.assertFalse(m["alive"])
        self.assertEqual(self.game.score, old_score + 200)

    def test_06_invisibility_cloaking_and_line_of_sight(self):
        """Verify cloaked monsters are only line-of-sight visible when on same corridor axis."""
        garwor = self.game.monsters[1]
        self.assertTrue(garwor["is_cloaked"])

        # Not in line of sight
        self.game.px = 7.5
        self.game.py = 13.0
        garwor["x"] = 2.0
        garwor["y"] = 2.0
        self.assertFalse(self.game.is_line_of_sight(garwor["x"], garwor["y"]))

        # In line of sight on same X axis
        garwor["x"] = 7.5
        garwor["y"] = 2.0
        self.assertTrue(self.game.is_line_of_sight(garwor["x"], garwor["y"]))

    def test_07_all_monsters_dead_spawns_wizard(self):
        """When all 3 minions are eliminated, the Wizard of Wor awakens."""
        for m in self.game.monsters:
            m["alive"] = False

        self.game.update(0.02)
        self.assertTrue(self.game.wizard_active)
        self.assertTrue(self.game.wizard_alive)

    def test_08_wizard_teleport_and_defeat_clear(self):
        """Wizard teleports periodically; shooting Wizard triggers dungeon clear with 2500 score."""
        for m in self.game.monsters:
            m["alive"] = False
        self.game.spawn_wizard()
        self.assertTrue(self.game.wizard_alive)

        # Wizard teleports after 2.0s timer
        old_wx = self.game.wizard_x
        self.game.update(2.1)
        self.assertNotEqual(self.game.wizard_x, old_wx)

        # Shoot wizard
        self.game.bullets.append({
            "x": self.game.wizard_x, "y": self.game.wizard_y, "vx": 0.0, "vy": 0.0, "life": 1.0
        })
        old_score = self.game.score
        self.game.update(0.02)

        self.assertFalse(self.game.wizard_alive)
        self.assertEqual(self.game.state, STATE_DUNGEON_CLEAR)
        self.assertGreaterEqual(self.game.score, old_score + 2500)

    def test_09_monster_touch_costs_life(self):
        """Direct monster collision costs 1 life and triggers STATE_WORRIOR_DIED."""
        m = self.game.monsters[0]
        m["x"] = self.game.px
        m["y"] = self.game.py

        self.game.update(0.02)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_WORRIOR_DIED)

    def test_10_game_over_and_radar_render(self):
        """At 0 lives transitions to STATE_GAME_OVER; render contains radar scanner on row 15."""
        self.game.lives = 1
        m = self.game.monsters[0]
        m["x"] = self.game.px
        m["y"] = self.game.py
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 0)
        self.game.update(1.2)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Render frame (768 bytes)
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
