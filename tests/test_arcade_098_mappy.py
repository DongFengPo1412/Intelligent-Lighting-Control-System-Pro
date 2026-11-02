import unittest
from arcade.game_098_mappy import (
    Game098Mappy,
    STATE_IN_MANSION,
    STATE_MAPPY_HIT,
    STATE_ROUND_CLEAR,
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


class TestGame098Mappy(unittest.TestCase):
    def setUp(self):
        self.game = Game098Mappy()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 98)
        self.assertEqual(self.game.name, "快乐小猫警")
        self.assertEqual(self.game.english_name, "Mappy")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("蹦床多段弹跳蹦高进层", self.game.core_mechanic)

    def test_hallway_walk(self):
        self.assertFalse(self.game.is_on_trampoline)
        init_x = self.game.px
        self.game.update(0.1, KEY_RIGHT)
        self.assertGreater(self.game.px, init_x)

    def test_enter_trampoline(self):
        # Walk left all the way into left trampoline shaft (x <= 2.2)
        for _ in range(15):
            self.game.update(0.05, KEY_LEFT)

        self.assertTrue(self.game.is_on_trampoline)
        self.assertEqual(self.game.active_tramp_idx, 0)

    def test_trampoline_bounce_and_wear(self):
        self.game.is_on_trampoline = True
        self.game.active_tramp_idx = 0
        self.game.px = 2.0
        self.game.py = 13.8
        self.game.vy = 5.0  # Falling toward base y=14.0

        self.game.update(0.05, 0)
        # Bounced!
        self.assertLess(self.game.vy, 0.0)
        self.assertEqual(self.game.tramp_wear_left, 1)

    def test_trampoline_break_on_wear_4(self):
        self.game.is_on_trampoline = True
        self.game.active_tramp_idx = 0
        self.game.px = 2.0
        self.game.py = 13.9
        self.game.vy = 4.0
        self.game.tramp_wear_left = 3  # Next bounce breaks!

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_MAPPY_HIT)

    def test_step_off_trampoline_repairs_wear(self):
        self.game.is_on_trampoline = True
        self.game.active_tramp_idx = 0
        self.game.tramp_wear_left = 2
        self.game.px = 2.0
        self.game.py = 6.2  # Near floor y=6

        # Hold KEY_RIGHT to step onto floor
        self.game.update(0.05, KEY_RIGHT)
        self.assertFalse(self.game.is_on_trampoline)
        self.assertEqual(self.game.py, 6.0)
        self.assertEqual(self.game.tramp_wear_left, 0)  # Repaired!

    def test_trampoline_midair_invulnerability(self):
        self.game.is_on_trampoline = True
        self.game.px = 2.0
        self.game.py = 7.5  # Mid-air in trampoline shaft

        # Cat passes through
        c = self.game.cats[0]
        c["active"] = True
        c["x"] = 2.0
        c["floor_y"] = 6

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_IN_MANSION)  # Safe!

    def test_microwave_door_blasts_cats(self):
        # Mappy at door (7, 6)
        self.game.px = 7.0
        self.game.py = 6.0
        self.game.facing = 1

        # Cat on floor 6
        c = self.game.cats[0]
        c["active"] = True
        c["floor_y"] = 6
        c["x"] = 8.5
        c["is_blasted"] = False

        init_score = self.game.score
        # Open door with Button A
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.wave_active)

        # Advance wave
        for _ in range(5):
            self.game.update(0.05, 0)

        self.assertTrue(c["is_blasted"])
        self.assertGreater(self.game.score, init_score)

    def test_cat_catches_mappy_on_floor(self):
        self.game.is_on_trampoline = False
        self.game.px = 6.0
        self.game.py = 6.0

        c = self.game.cats[0]
        c["active"] = True
        c["is_blasted"] = False
        c["floor_y"] = 6
        c["x"] = 6.0

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_MAPPY_HIT)

    def test_collect_loot_and_round_clear(self):
        # Disable cats for loot test
        for c in self.game.cats:
            c["active"] = False

        self.game.is_on_trampoline = False
        # Collect item 0 at (4, 3)
        self.game.px = 4.0
        self.game.py = 3.0
        init_score = self.game.score

        self.game.update(0.05, 0)
        self.assertTrue(self.game.loot[0]["collected"])
        self.assertEqual(self.game.loot_collected, 1)
        self.assertGreater(self.game.score, init_score)

        # Mark all loot collected
        for item in self.game.loot:
            item["collected"] = True
        self.game.loot_collected = 6

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

        # Framebuffer render check
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 98)


if __name__ == "__main__":
    unittest.main()
