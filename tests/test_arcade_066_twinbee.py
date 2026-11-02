import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_066_twinbee import (
    Game066TwinBee,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    BELL_YELLOW,
    BELL_WHITE,
    BELL_BLUE,
    BELL_RED,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade066TwinBee(unittest.TestCase):
    def setUp(self):
        self.game = Game066TwinBee()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 66)
        self.assertEqual(self.game.english_name, "TwinBee")
        self.assertEqual(self.game.release_year, 1985)
        cart = ArcadeRegistry.get_cartridge(66)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game066TwinBee)

    def test_movement_and_bounds(self):
        initial_x = self.game.px
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, initial_x)

        # Clamping
        for _ in range(50):
            self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreaterEqual(self.game.px, 1.0)

    def test_air_shoot_and_ground_bomb(self):
        self.assertEqual(len(self.game.shots), 0)
        self.assertEqual(len(self.game.bombs), 0)

        # Air shot with Button A
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.shots), 1)
        self.assertLess(self.game.shots[0]["vy"], 0)

        # Ground bomb with Button B
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.bombs), 1)
        self.assertGreater(self.game.bombs[0]["vy"], 0)

    def test_bell_spawn_and_juggling(self):
        self.game.spawn_bell(7.5, 5.0)
        self.assertEqual(len(self.game.bells), 1)
        self.assertEqual(self.game.bells[0]["color_type"], BELL_YELLOW)

        # Shoot bell to juggle it upward
        self.game.shots.append({
            "x": 7.5,
            "y": 5.1,
            "vx": 0.0,
            "vy": -10.0,
            "active": True,
        })
        self.game.check_collisions()
        self.assertEqual(self.game.bells[0]["hit_count"], 1)
        self.assertLess(self.game.bells[0]["vy"], 0)  # Bounced upward!

    def test_bell_color_morph_cycle(self):
        self.game.spawn_bell(8.0, 6.0)
        bell = self.game.bells[0]

        # Hit 5 times -> white
        bell["hit_count"] = 4
        self.game.shots.append({"x": 8.0, "y": 6.0, "vx": 0.0, "vy": -10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(bell["color_type"], BELL_WHITE)

        # Hit 10 times -> blue
        bell["hit_count"] = 9
        self.game.shots.append({"x": 8.0, "y": 6.0, "vx": 0.0, "vy": -10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(bell["color_type"], BELL_BLUE)

        # Hit 15 times -> red
        bell["hit_count"] = 14
        self.game.shots.append({"x": 8.0, "y": 6.0, "vx": 0.0, "vy": -10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(bell["color_type"], BELL_RED)

    def test_collecting_white_bell_grants_twin_gun(self):
        self.assertFalse(self.game.has_twin_gun)
        self.game.spawn_bell(self.game.px, self.game.py)
        self.game.bells[0]["color_type"] = BELL_WHITE
        self.game.check_collisions()
        self.assertTrue(self.game.has_twin_gun)

        # Twin gun fires dual parallel shots
        self.game.shots.clear()
        self.game.shoot_cooldown = 0.0
        self.game.update(0.02, KEY_A, 0)
        self.assertEqual(len(self.game.shots), 2)

    def test_collecting_blue_bell_grants_shield(self):
        self.assertFalse(self.game.has_shield)
        self.game.spawn_bell(self.game.px, self.game.py)
        self.game.bells[0]["color_type"] = BELL_BLUE
        self.game.check_collisions()
        self.assertTrue(self.game.has_shield)

        # Enemy collision is absorbed by shield
        self.game.enemies = [{"x": self.game.px, "y": self.game.py, "vx": 0.0, "vy": 0.0, "type": 0, "active": True}]
        self.game.check_collisions()
        self.assertFalse(self.game.has_shield)  # Shield absorbed hit
        self.assertEqual(self.game.lives, 3)     # Still full lives

    def test_ground_bomb_destroys_ground_target(self):
        self.game.ground_targets = [{"x": 7.0, "y": 8.0, "type": 0, "active": True}]
        self.game.bombs.append({"x": 7.0, "y": 8.0, "vx": 0.0, "vy": 4.0, "active": True})
        self.game.check_collisions()
        self.assertFalse(self.game.ground_targets[0]["active"])
        self.assertGreater(self.game.score, 0)

    def test_arm_damage_and_ambulance_rescue(self):
        self.assertTrue(self.game.has_arms)
        self.assertFalse(self.game.ambulance_active)

        # Collide with enemy without shield: loses arms, spawns ambulance!
        self.game.enemies = [{"x": self.game.px, "y": self.game.py, "vx": 0.0, "vy": 0.0, "type": 0, "active": True}]
        self.game.check_collisions()
        self.assertFalse(self.game.has_arms)
        self.assertTrue(self.game.ambulance_active)

        # Cannot drop bomb without arms
        self.game.bombs.clear()
        self.game.bomb_cooldown = 0.0
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(len(self.game.bombs), 0)

        # Ambulance reaches player
        self.game.amb_x = self.game.px
        self.game.amb_y = self.game.py
        self.game.check_collisions()
        self.assertFalse(self.game.ambulance_active)
        self.assertTrue(self.game.has_arms)  # Restored!

    def test_stage_clear_victory_and_render(self):
        self.game.enemies_defeated = 7
        self.game.enemies = [{"x": 5.0, "y": 5.0, "vx": 0.0, "vy": 0.0, "type": 0, "active": True}]
        self.game.shots.append({"x": 5.0, "y": 5.0, "vx": 0.0, "vy": -10.0, "active": True})
        self.game.check_collisions()
        self.assertEqual(self.game.enemies_defeated, 8)
        self.assertEqual(self.game.state, STATE_VICTORY)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)


if __name__ == "__main__":
    unittest.main()
