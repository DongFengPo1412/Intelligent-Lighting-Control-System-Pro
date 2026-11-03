# -*- coding: utf-8 -*-
import unittest
from arcade.game_179_gauntlet import (
    Game179Gauntlet,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_WARRIOR_DIED,
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

class TestArcade179Gauntlet(unittest.TestCase):
    def setUp(self):
        self.game = Game179Gauntlet()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 179)
        self.assertEqual(self.game.name, "圣铠传说")
        self.assertEqual(self.game.english_name, "Gauntlet")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertGreater(self.game.health, 0.0)
        self.assertGreater(len(self.game.generators), 0)
        self.assertGreater(len(self.game.pickups), 0)

    def test_02_warrior_movement_and_wall_blocking(self):
        # Open movement right
        self.game.px = 2.0
        self.game.py = 2.0
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertGreater(self.game.px, 2.0)

        # Move into solid wall at x=0
        for _ in range(20):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertGreaterEqual(self.game.px, 0.5) # Blocked before entering wall at x=0

    def test_03_collect_food_replenishes_decaying_health(self):
        self.game.health = 200.0
        # Position food at (3, 2)
        self.game.pickups.append({"x": 3, "y": 2, "type": "food"})
        self.game.px = 3.0
        self.game.py = 2.0
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertGreater(self.game.health, 300.0)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_04_unlock_door_with_key(self):
        self.game.keys_count = 1
        # Door at (5, 5)
        self.assertEqual(self.game.grid[5][5], 2)
        self.game.px = 4.2
        self.game.py = 5.0

        # Move right into door
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.grid[5][5], 0) # Door unlocked!
        self.assertEqual(self.game.keys_count, 0) # Key consumed

    def test_05_throw_axe_projectile(self):
        self.assertEqual(len(self.game.axes), 0)
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.axes), 1)
        axe = self.game.axes[0]
        self.assertTrue(axe["active"])
        self.assertGreater(axe["vx"], 0.0)

    def test_06_axe_destroys_monster(self):
        m = self.game.monsters[0]
        m["x"] = 6.0
        m["y"] = 2.0
        m["alive"] = True

        self.game.axes.append({
            "x": 5.8,
            "y": 2.0,
            "vx": 12.0,
            "vy": 0.0,
            "active": True,
        })
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(m["alive"])
        self.assertEqual(self.game.score, initial_score + 100)

    def test_07_axe_destroys_monster_generator(self):
        g = self.game.generators[0]
        g["x"] = 8
        g["y"] = 4
        g["hp"] = 1 # One hit from destruction

        self.game.axes.append({
            "x": 8.0,
            "y": 3.8,
            "vx": 0.0,
            "vy": 12.0,
            "active": True,
        })
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertEqual(g["hp"], 0)
        self.assertEqual(self.game.score, initial_score + 150 + 500)

    def test_08_magic_potion_clears_screen_monsters(self):
        self.game.potions_count = 1
        self.game.monsters = [
            {"x": 4.0, "y": 4.0, "speed": 2.0, "alive": True},
            {"x": 10.0, "y": 10.0, "speed": 2.0, "alive": True},
        ]
        initial_score = self.game.score

        # Cast magic potion (Button B)
        self.game.update(0.01, keys_pressed=KEY_B)
        self.assertEqual(self.game.potions_count, 0)
        self.assertFalse(self.game.monsters[0]["alive"])
        self.assertFalse(self.game.monsters[1]["alive"])
        self.assertEqual(self.game.score, initial_score + 300)

    def test_09_exit_portal_triggers_stage_clear(self):
        # Exit portal is at (13, 13)
        self.game.px = 12.5
        self.game.py = 13.0

        # Step into exit stairs
        self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2500)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_WARRIOR_DIED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Restart via Button A
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()
