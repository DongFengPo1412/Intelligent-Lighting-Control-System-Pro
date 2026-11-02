import unittest
from arcade.game_094_crashboys import (
    Game094CrashBoys,
    STATE_RUNNING,
    STATE_VAULTING,
    STATE_AIRBORNE,
    STATE_HERO_FALL,
    STATE_STAGE_CLEAR,
    STATE_GAME_OVER,
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


class TestGame094CrashBoys(unittest.TestCase):
    def setUp(self):
        self.game = Game094CrashBoys()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 94)
        self.assertEqual(self.game.name, "热血新纪录")
        self.assertEqual(self.game.english_name, "Crash 'n' the Boys")
        self.assertEqual(self.game.release_year, 1992)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("大楼楼顶撑杆弯曲弹射跳跃", self.game.core_mechanic)

    def test_sprint_acceleration(self):
        init_speed = self.game.run_speed
        self.game.update(0.1, KEY_RIGHT)
        self.assertGreater(self.game.run_speed, init_speed)
        self.assertGreater(self.game.distance, 0.0)

    def test_plant_vaulting_pole(self):
        self.assertEqual(self.game.state, STATE_RUNNING)
        self.game.update(0.05, KEY_B)
        self.assertEqual(self.game.state, STATE_VAULTING)
        self.assertGreater(self.game.pole_flex, 0.0)

    def test_pole_flex_charge(self):
        self.game.update(0.05, KEY_B)
        init_flex = self.game.pole_flex

        # Continue holding KEY_B to bend pole
        for _ in range(8):
            self.game.update(0.05, KEY_B)

        self.assertGreater(self.game.pole_flex, init_flex)

    def test_catapult_into_air(self):
        self.game.update(0.05, KEY_B)
        for _ in range(5):
            self.game.update(0.05, KEY_B)

        # Release KEY_B to launch!
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_AIRBORNE)
        self.assertLess(self.game.air_vy, 0.0)  # Flung upward!
        self.assertGreater(self.game.air_vx, 0.0)

    def test_midair_dropkick(self):
        # Enter airborne state
        self.game.state = STATE_AIRBORNE
        self.game.air_vy = -4.0
        self.game.air_vx = 6.0
        self.game.is_dropkicking = False

        # Press KEY_A to dropkick
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.is_dropkicking)
        self.assertGreater(self.game.air_vx, 6.0)

    def test_dropkick_knocks_rival_off_roof(self):
        self.game.state = STATE_AIRBORNE
        self.game.is_dropkicking = True
        self.game.py = 11.5
        self.game.px = 6.0

        r = self.game.rivals[0]
        r["active"] = True
        r["x"] = 6.0
        r["y"] = 12.0
        r["knocked_down"] = False

        init_score = self.game.score
        init_def = self.game.rivals_defeated

        self.game.update(0.05, 0)
        self.assertTrue(r["knocked_down"])
        self.assertEqual(self.game.score, init_score + 300)
        self.assertEqual(self.game.rivals_defeated, init_def + 1)

    def test_safe_rooftop_landing(self):
        self.game.state = STATE_AIRBORNE
        self.game.py = 12.95
        self.game.air_vy = 3.0  # Descending
        self.game.distance = self.game.next_gap_dist + self.game.gap_width + 10.0  # Past gap!

        init_score = self.game.score
        self.game.update(0.05, 0)

        self.assertEqual(self.game.state, STATE_RUNNING)
        self.assertEqual(self.game.py, 13.0)
        self.assertEqual(self.game.score, init_score + 200)

    def test_unvaulted_fall_into_gap(self):
        # Run straight into gap
        self.game.state = STATE_RUNNING
        self.game.distance = self.game.next_gap_dist + 1.0

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_HERO_FALL)

    def test_stage_clear_and_render(self):
        self.game.distance = self.game.stage_length
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1500)

        # Framebuffer render check
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 94)


if __name__ == "__main__":
    unittest.main()
