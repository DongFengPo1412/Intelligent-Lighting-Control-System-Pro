import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arcade.arcade_registry import ArcadeRegistry
from arcade.game_073_gradius import (
    Game073Gradius,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
    TIER_SPEED_UP,
    TIER_MISSILE,
    TIER_DOUBLE,
    TIER_LASER,
    TIER_OPTION,
    TIER_SHIELD,
)
from arcade.base_cartridge import (
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestArcade073Gradius(unittest.TestCase):
    def setUp(self):
        self.game = Game073Gradius()
        self.game.reset()

    def test_metadata_and_registry(self):
        self.assertEqual(self.game.game_id, 73)
        self.assertEqual(self.game.english_name, "Gradius")
        self.assertEqual(self.game.release_year, 1985)
        cart = ArcadeRegistry.get_cartridge(73)
        self.assertIsNotNone(cart)
        self.assertIsInstance(cart, Game073Gradius)

    def test_movement_and_speed_up_upgrade(self):
        initial_x = self.game.px
        self.game.update(0.1, KEY_RIGHT, 0)
        dist_normal = self.game.px - initial_x

        # Collect capsule and activate Speed Up (Slot 1)
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, TIER_SPEED_UP)
        self.game.activate_power_meter()
        self.assertTrue(self.game.has_speed_up)

        # Move right again, speed should be higher!
        start_x2 = self.game.px
        self.game.update(0.1, KEY_RIGHT, 0)
        dist_fast = self.game.px - start_x2
        self.assertGreater(dist_fast, dist_normal)

    def test_capsule_collection_advances_power_meter(self):
        self.assertEqual(self.game.meter_slot, 0)
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 1)  # Speed
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 2)  # Missile
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 3)  # Double
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 4)  # Laser
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 5)  # Option
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 6)  # Shield
        self.game.collect_capsule()
        self.assertEqual(self.game.meter_slot, 1)  # Wrap to 1

    def test_activate_missile_upgrade(self):
        self.assertFalse(self.game.has_missile)
        self.game.meter_slot = TIER_MISSILE
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.has_missile)
        self.assertEqual(self.game.meter_slot, 0)

        # Shoot: should drop missile downward
        self.game.shoot()
        self.assertEqual(len(self.game.missiles), 1)
        self.assertGreater(self.game.missiles[0]["vy"], 0)

    def test_activate_double_shot_upgrade(self):
        self.assertFalse(self.game.has_double)
        self.game.meter_slot = TIER_DOUBLE
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.has_double)

        self.game.shoot()
        # Fires 2 shots (one forward, one 45 deg up)
        self.assertEqual(len(self.game.shots), 2)

    def test_activate_laser_upgrade(self):
        self.assertFalse(self.game.has_laser)
        self.game.meter_slot = TIER_LASER
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.has_laser)

        self.game.shoot()
        self.assertEqual(len(self.game.shots), 1)
        self.assertTrue(self.game.shots[0]["is_laser"])

    def test_activate_option_follower_upgrade(self):
        self.assertFalse(self.game.has_option)
        self.game.meter_slot = TIER_OPTION
        self.game.update(0.02, KEY_B, 0)
        self.assertTrue(self.game.has_option)

        # Shoot: option also fires!
        self.game.shoot()
        self.assertEqual(len(self.game.shots), 2)

    def test_activate_shield_absorbs_damage(self):
        self.assertEqual(self.game.shield_hp, 0)
        self.game.meter_slot = TIER_SHIELD
        self.game.update(0.02, KEY_B, 0)
        self.assertEqual(self.game.shield_hp, 2)

        # Take enemy shot
        self.game.shots.append({
            "x": self.game.px,
            "y": self.game.py,
            "vx": -10.0,
            "vy": 0.0,
            "is_laser": False,
            "active": True,
        })
        self.game.check_collisions()
        self.assertEqual(self.game.shield_hp, 1)  # Shield absorbed!
        self.assertEqual(self.game.lives, 3)     # Still full lives

    def test_big_core_spawn_barrier_breach_and_victory(self):
        self.assertFalse(self.game.boss_active)
        self.game.enemies_defeated = 6
        self.game.update(0.02, 0, 0)
        self.assertTrue(self.game.boss_active)

        # Shoot barrier down to 0
        self.game.boss_barrier_health = 1
        self.game.shots.append({
            "x": self.game.boss_x - 1.0,
            "y": self.game.boss_y,
            "vx": 15.0,
            "vy": 0.0,
            "is_laser": False,
            "active": True,
        })
        self.game.check_collisions()
        self.assertEqual(self.game.boss_barrier_health, 0)

        # Shoot core to 0 -> Victory!
        self.game.boss_core_health = 1
        self.game.shots.append({
            "x": self.game.boss_x - 1.0,
            "y": self.game.boss_y,
            "vx": 15.0,
            "vy": 0.0,
            "is_laser": False,
            "active": True,
        })
        self.game.check_collisions()
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_framebuffer_and_status(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 73)
        self.assertEqual(status["name"], "宇宙巡航舰")


if __name__ == "__main__":
    unittest.main()
