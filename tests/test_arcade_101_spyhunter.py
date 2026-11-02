import unittest
from arcade.game_101_spyhunter import (
    Game101SpyHunter,
    STATE_DRIVING,
    STATE_WEAPONS_VAN_DOCK,
    STATE_AMPHIBIOUS_BOATING,
    STATE_CRASHED,
    STATE_GAME_OVER,
    WEAPON_NONE,
    WEAPON_OIL_SLICK,
    WEAPON_SMOKE_SCREEN,
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


class TestGame101SpyHunter(unittest.TestCase):
    def setUp(self):
        self.game = Game101SpyHunter()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 101)
        self.assertEqual(self.game.name, "间谍猎手")
        self.assertEqual(self.game.english_name, "Spy Hunter")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("武装跑车高速追逐", self.game.core_mechanic)

    def test_steering_and_acceleration(self):
        init_x = self.game.px
        init_spd = self.game.speed

        # Steer left and throttle up
        self.game.update(0.05, KEY_LEFT | KEY_UP, 0)
        self.assertLess(self.game.px, init_x)
        self.assertGreater(self.game.speed, init_spd)

    def test_machine_gun_fire(self):
        self.assertFalse(any(b["active"] for b in self.game.bullets))
        self.game.update(0.05, KEY_A, 0)
        active_bullets = [b for b in self.game.bullets if b["active"]]
        self.assertEqual(len(active_bullets), 1)
        self.assertEqual(active_bullets[0]["vy"], -24.0)

    def test_off_road_crash(self):
        self.game.px = 0.5  # Outside road_left (which is >= 1.0)
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

    def test_call_weapons_van(self):
        self.assertFalse(self.game.van["active"])
        self.game.call_weapon_van()
        self.assertTrue(self.game.van["active"])

    def test_dock_weapons_van_and_rearm(self):
        self.game.van["active"] = True
        self.game.van["x"] = 8.0
        self.game.van["y"] = 9.2
        self.game.van["carrying_weapon"] = WEAPON_OIL_SLICK

        self.game.px = 8.0
        self.game.py = 12.0  # (py - (van.y + 2.8) = 12.0 - 12.0 = 0.0) -> Docks!

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_WEAPONS_VAN_DOCK)

        # Advance state_timer past 1.4s to exit van rearmed
        self.game.state_timer = 1.5
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DRIVING)
        self.assertEqual(self.game.current_weapon, WEAPON_OIL_SLICK)
        self.assertEqual(self.game.weapon_ammo, 3)

    def test_deploy_oil_slick_hazard(self):
        self.game.current_weapon = WEAPON_OIL_SLICK
        self.game.weapon_ammo = 2
        self.assertFalse(any(h["active"] for h in self.game.hazards))

        # Press KEY_B
        self.game.update(0.05, KEY_B, 0)
        active_hazards = [h for h in self.game.hazards if h["active"]]
        self.assertEqual(len(active_hazards), 1)
        self.assertEqual(self.game.weapon_ammo, 1)

    def test_oil_slick_spins_enemy(self):
        self.game.hazards[0]["active"] = True
        self.game.hazards[0]["x"] = 6.0
        self.game.hazards[0]["y"] = 4.0

        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["x"] = 6.0
        self.game.enemies[0]["y"] = 4.0
        self.game.enemies[0]["spinning"] = False

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.enemies[0]["spinning"])
        self.assertGreater(self.game.score, init_score)

    def test_tire_slasher_collides_and_crashes(self):
        # Enemy 1 is Tire Slasher (type=1)
        self.game.enemies[1]["active"] = True
        self.game.enemies[1]["type"] = 1
        self.game.enemies[1]["x"] = self.game.px
        self.game.enemies[1]["y"] = self.game.py
        self.game.enemies[1]["spinning"] = False

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_CRASHED)

    def test_amphibious_river_mode_and_render(self):
        self.game.distance_traveled = 510.0
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_AMPHIBIOUS_BOATING)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
