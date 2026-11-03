"""
Unit tests for Game #160: 碰碰抢夺 / 燃料守卫 (Rip Off - 1979 Cinematronics / Tim Skelly)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_160_ripoff import (
    Game160RipOff,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_GAME_OVER
)

class TestArcade160RipOff(unittest.TestCase):
    def setUp(self):
        self.game = Game160RipOff()

    def test_01_init_state_and_canisters(self):
        """Verify initial state, 4 fuel canisters at base, player position, score and wave."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.wave, 1)
        self.assertEqual(self.game.remaining_fuel_count(), 4)
        self.assertEqual(len(self.game.canisters), 4)
        for c in self.game.canisters:
            self.assertEqual(c["status"], "at_base")
            self.assertEqual(c["carrier_id"], -1)
        self.assertTrue(self.game.player_alive)
        self.assertAlmostEqual(self.game.player_x, 8.0)
        self.assertAlmostEqual(self.game.player_y, 12.0)

    def test_02_player_movement_and_clamping(self):
        """Verify 4-directional player movement and boundary clamping."""
        # Move UP
        self.game.update(0.1, keys_down=KEY_UP)
        self.assertLess(self.game.player_y, 12.0)
        self.assertEqual(self.game.facing_dy, -1.0)

        # Move LEFT to boundary
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_LEFT)
        self.assertEqual(self.game.player_x, 0.0)

        # Move RIGHT to boundary
        for _ in range(50):
            self.game.update(0.1, keys_down=KEY_RIGHT)
        self.assertEqual(self.game.player_x, 15.0)

    def test_03_laser_shooting_and_cooldown(self):
        """Verify laser firing creates active bullet in facing direction."""
        # Face UP and fire
        self.game.facing_dx = 0.0
        self.game.facing_dy = -1.0
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.bullets), 1)
        b = self.game.bullets[0]
        self.assertAlmostEqual(b["vx"], 0.0)
        self.assertLess(b["vy"], 0.0)

        # Firing immediately again is blocked by cooldown
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.bullets), 1)

    def test_04_pirate_spawning_and_targeting(self):
        """Verify pirate raiders spawn and navigate toward fuel depot."""
        self.game.spawn_pirate()
        self.assertEqual(len(self.game.pirates), 1)
        p = self.game.pirates[0]
        init_dist = (p["x"] - 7.0)**2 + (p["y"] - 7.0)**2

        # Step simulation to let pirate move towards center
        self.game.update(0.5)
        new_dist = (p["x"] - 7.0)**2 + (p["y"] - 7.0)**2
        self.assertLess(new_dist, init_dist)

    def test_05_pirate_canister_grapple_and_towing(self):
        """Verify pirate grapples a canister when reaching center depot and begins towing."""
        p = {
            "id": 99,
            "x": 7.1,
            "y": 7.1,
            "speed": 2.5,
            "target_canister": -1,
            "towing_canister": -1,
            "alive": True
        }
        self.game.pirates.append(p)
        self.game.update(0.05)

        # Pirate should have grappled canister 0
        self.assertEqual(p["towing_canister"], 0)
        self.assertEqual(self.game.canisters[0]["status"], "towed")
        self.assertEqual(self.game.canisters[0]["carrier_id"], 99)

    def test_06_shooting_pirate_drops_canister(self):
        """Verify shooting a towing pirate destroys it and leaves canister dropped."""
        p = {
            "id": 10,
            "x": 5.0,
            "y": 5.0,
            "speed": 2.5,
            "target_canister": 0,
            "towing_canister": 0,
            "alive": True
        }
        self.game.pirates.append(p)
        self.game.canisters[0]["status"] = "towed"
        self.game.canisters[0]["carrier_id"] = 10
        self.game.canisters[0]["x"] = 5.0
        self.game.canisters[0]["y"] = 5.0

        # Bullet colliding with pirate
        self.game.bullets.append({
            "x": 5.0,
            "y": 5.0,
            "vx": 0.0,
            "vy": 0.0,
            "life": 1.0
        })

        self.game.update(0.02)
        self.assertFalse(p["alive"])
        self.assertEqual(self.game.canisters[0]["status"], "dropped")
        self.assertEqual(self.game.canisters[0]["carrier_id"], -1)
        self.assertGreaterEqual(self.game.score, 100)

    def test_07_touch_or_magnet_recovers_dropped_canister(self):
        """Verify player can recover a dropped canister by touching or magnet beam."""
        c = self.game.canisters[0]
        c["status"] = "dropped"
        c["x"] = 8.0
        c["y"] = 11.0 # Close to player at (8, 12)

        # Press KEY_B for magnet recovery
        old_score = self.game.score
        self.game.update(0.02, keys_down=0, keys_pressed=KEY_B)
        self.assertEqual(c["status"], "at_base")
        self.assertEqual(c["x"], c["home_x"])
        self.assertEqual(c["y"], c["home_y"])
        self.assertGreater(self.game.score, old_score)

    def test_08_pirate_escapes_with_canister(self):
        """Verify pirate towing canister off-screen successfully steals it."""
        p = {
            "id": 20,
            "x": 0.1,
            "y": 5.0,
            "speed": 3.0,
            "target_canister": 1,
            "towing_canister": 1,
            "alive": True
        }
        self.game.pirates.append(p)
        self.game.canisters[1]["status"] = "towed"
        self.game.canisters[1]["carrier_id"] = 20

        # Step update so pirate crosses x <= -0.5
        for _ in range(5):
            self.game.update(0.3)

        self.assertEqual(self.game.canisters[1]["status"], "stolen")
        self.assertEqual(self.game.remaining_fuel_count(), 3)

    def test_09_player_pirate_collision_respawn(self):
        """Verify collision destroys both player and pirate, but player respawns if fuel remains."""
        self.game.player_x = 8.0
        self.game.player_y = 8.0
        p = {
            "id": 30,
            "x": 8.0,
            "y": 8.0,
            "speed": 2.0,
            "target_canister": -1,
            "towing_canister": -1,
            "alive": True
        }
        self.game.pirates.append(p)

        self.game.update(0.02)
        self.assertFalse(self.game.player_alive)
        self.assertFalse(p["alive"])

        # Wait for respawn timer
        self.game.update(1.2)
        self.assertTrue(self.game.player_alive)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_10_all_fuel_stolen_game_over_and_render(self):
        """Verify game over when all fuel stolen, and matrix frame rendering."""
        for c in self.game.canisters:
            c["status"] = "stolen"

        p = {
            "id": 40,
            "x": 0.1,
            "y": 5.0,
            "speed": 3.0,
            "target_canister": 0,
            "towing_canister": 0,
            "alive": True
        }
        self.game.pirates.append(p)
        for _ in range(5):
            self.game.update(0.3)

        self.assertEqual(self.game.remaining_fuel_count(), 0)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Test frame rendering (bytearray 16*16*3 = 768)
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
