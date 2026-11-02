import unittest
from arcade.game_091_ninjabaseball import (
    Game091NinjaBaseball,
    STATE_INNING,
    STATE_HERO_HIT,
    STATE_STAGE_CLEAR,
    STATE_GAME_OVER,
    ACTION_IDLE,
    ACTION_SWING,
    ACTION_BUNT,
    ACTION_HOMERUN,
    ACTION_SLIDE,
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


class TestGame091NinjaBaseball(unittest.TestCase):
    def setUp(self):
        self.game = Game091NinjaBaseball()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 91)
        self.assertEqual(self.game.name, "棒球杀手")
        self.assertEqual(self.game.english_name, "Ninja Baseball Bat Man")
        self.assertEqual(self.game.release_year, 1993)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("棒球短打挑空接全垒暴击与盗垒铲摔", self.game.core_mechanic)

    def test_infield_movement(self):
        init_x = self.game.px
        init_y = self.game.py

        self.game.update(0.1, KEY_RIGHT)
        self.assertGreater(self.game.px, init_x)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_LEFT)
        self.assertEqual(self.game.facing, -1)

        self.game.update(0.1, KEY_UP)
        self.assertLess(self.game.py, init_y)

    def test_bat_swing_ground(self):
        # Place ground thug in front of batter
        t = self.game.thugs[0]
        t["active"] = True
        t["is_airborne"] = False
        t["x"] = self.game.px + 1.2
        t["y"] = self.game.py
        t["hp"] = 2
        init_score = self.game.score

        # Press Button A to swing
        self.game.update(0.05, KEY_A)
        self.assertEqual(self.game.action_state, ACTION_SWING)
        self.assertEqual(t["hp"], 1)
        self.assertEqual(self.game.score, init_score + 100)

    def test_bat_bunt_pops_airborne(self):
        # Place thug in front
        t = self.game.thugs[0]
        t["active"] = True
        t["is_airborne"] = False
        t["x"] = self.game.px + 1.0
        t["y"] = self.game.py
        init_score = self.game.score

        # Up + Button A: Bunt
        self.game.update(0.05, KEY_UP | KEY_A)
        self.assertEqual(self.game.action_state, ACTION_BUNT)
        self.assertTrue(t["is_airborne"])
        self.assertLess(t["vy"], 0.0)
        self.assertEqual(self.game.score, init_score + 50)

    def test_airborne_enemy_falls_back(self):
        t = self.game.thugs[0]
        t["active"] = True
        t["is_airborne"] = True
        t["y"] = 6.0
        t["vy"] = -3.0

        # Simulate until enemy lands back on ground y=12.0
        for _ in range(30):
            self.game.update(0.05, 0)

        self.assertFalse(t["is_airborne"])
        self.assertEqual(t["y"], 12.0)

    def test_home_run_smash(self):
        # Set thug airborne in front of batter
        t = self.game.thugs[0]
        t["active"] = True
        t["is_airborne"] = True
        t["is_homerun_flying"] = False
        t["x"] = self.game.px + 1.2
        t["y"] = self.game.py - 1.0
        t["hp"] = 2

        init_score = self.game.score
        init_hr = self.game.home_runs
        init_thugs_def = self.game.thugs_defeated

        # Batter swings at airborne enemy
        self.game.update(0.05, KEY_A)
        self.assertEqual(self.game.action_state, ACTION_HOMERUN)
        self.assertTrue(t["is_homerun_flying"])
        self.assertFalse(t["is_airborne"])
        self.assertGreater(t["vx"], 10.0)
        self.assertEqual(self.game.score, init_score + 500)
        self.assertEqual(self.game.home_runs, init_hr + 1)
        self.assertEqual(self.game.thugs_defeated, init_thugs_def + 1)

    def test_base_stealing_slide(self):
        init_x = self.game.px
        t = self.game.thugs[0]
        t["active"] = True
        t["x"] = self.game.px + 0.8
        t["y"] = self.game.py
        t["hp"] = 2
        init_score = self.game.score

        # Press Button B: Slide
        self.game.update(0.05, KEY_B)
        self.assertEqual(self.game.action_state, ACTION_SLIDE)
        self.assertGreater(self.game.px, init_x)
        self.assertEqual(t["hp"], 1)
        self.assertEqual(self.game.score, init_score + 120)

    def test_enemy_attacks_idle_batter(self):
        t = self.game.thugs[0]
        t["active"] = True
        t["is_airborne"] = False
        t["is_homerun_flying"] = False
        t["x"] = self.game.px
        t["y"] = self.game.py

        self.game.action_state = ACTION_IDLE
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_HERO_HIT)

    def test_inning_clear(self):
        self.game.thugs_defeated = 6
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer(self):
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 91)
        self.assertEqual(status["name"], "棒球杀手")


if __name__ == "__main__":
    unittest.main()
