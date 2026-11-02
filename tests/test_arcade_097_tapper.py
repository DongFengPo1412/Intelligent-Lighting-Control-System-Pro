import unittest
from arcade.game_097_tapper import (
    Game097Tapper,
    STATE_SERVING,
    STATE_MUG_CRASHED,
    STATE_PATRON_OVERRUN,
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


class TestGame097Tapper(unittest.TestCase):
    def setUp(self):
        self.game = Game097Tapper()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 97)
        self.assertEqual(self.game.name, "快打酒保")
        self.assertEqual(self.game.english_name, "Root Beer Tapper")
        self.assertEqual(self.game.release_year, 1983)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("多轨道吧台倒酒滑杯推退顾客", self.game.core_mechanic)

    def test_lane_navigation_and_horizontal_walk(self):
        self.assertEqual(self.game.current_lane, 0)

        # Move to Lane 1
        self.game.update(0.05, KEY_DOWN)
        self.assertEqual(self.game.current_lane, 1)

        # Move horizontally left along bar
        init_bx = self.game.bx
        self.game.update(0.1, KEY_LEFT)
        self.assertLess(self.game.bx, init_bx)

    def test_pour_and_slide_mug(self):
        # Press Button A to start pouring
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.is_filling_mug)

        # Release Button A to slide full mug
        self.game.update(0.05, 0)
        self.assertFalse(self.game.is_filling_mug)

        active_mugs = [m for m in self.game.mugs if m["active"]]
        self.assertEqual(len(active_mugs), 1)
        self.assertFalse(active_mugs[0]["is_empty"])
        self.assertLess(active_mugs[0]["vx"], 0.0)

    def test_full_mug_slides_off_counter_smashes(self):
        # Disable patrons on lane 0
        for p in self.game.patrons:
            if p["lane"] == 0:
                p["active"] = False

        # Slide full mug
        self.game.update(0.05, KEY_A)
        self.game.update(0.05, 0)

        # Advance until full beer flies off left end (x <= 0.5)
        for _ in range(35):
            self.game.update(0.05, 0)

        self.assertEqual(self.game.state, STATE_MUG_CRASHED)

    def test_patron_drinks_and_pushed_back(self):
        p = self.game.patrons[0]
        p["active"] = True
        p["lane"] = 0
        p["x"] = 5.0
        p["is_drinking"] = False

        # Bartender on lane 0 slides beer
        self.game.current_lane = 0
        self.game.update(0.05, KEY_A)
        self.game.update(0.05, 0)

        # Advance until beer reaches patron
        for _ in range(15):
            self.game.update(0.05, 0)

        self.assertTrue(p["is_drinking"])
        self.assertLess(p["x"], 5.0)  # Pushed backwards!

    def test_catch_returning_empty_mug(self):
        # Empty mug sliding right on lane 0
        m = self.game.mugs[0]
        m["active"] = True
        m["lane"] = 0
        m["x"] = 11.5
        m["vx"] = 7.5
        m["is_empty"] = True

        self.game.current_lane = 0
        self.game.bx = 12.0
        init_score = self.game.score

        self.game.update(0.05, 0)
        self.assertFalse(m["active"])  # Caught!
        self.assertEqual(self.game.score, init_score + 100)

    def test_empty_mug_uncaught_smashes(self):
        # Empty mug on lane 0 near right edge, but bartender is on lane 1!
        m = self.game.mugs[0]
        m["active"] = True
        m["lane"] = 0
        m["x"] = 14.0
        m["vx"] = 7.5
        m["is_empty"] = True

        self.game.current_lane = 1  # Wrong lane!
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_MUG_CRASHED)

    def test_collect_tips(self):
        self.game.current_lane = 0
        self.game.tips[0] = True
        self.game.tip_x[0] = 9.0
        self.game.bx = 9.2

        init_score = self.game.score
        self.game.update(0.05, 0)
        self.assertFalse(self.game.tips[0])
        self.assertEqual(self.game.score, init_score + 100)

    def test_patron_overrun(self):
        p = self.game.patrons[0]
        p["active"] = True
        p["is_drinking"] = False
        p["x"] = 13.0

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_PATRON_OVERRUN)

    def test_round_clear_and_render(self):
        self.game.patrons_satisfied = 6
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)
        self.assertGreaterEqual(self.game.score, 1500)

        # Framebuffer render check
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 97)


if __name__ == "__main__":
    unittest.main()
