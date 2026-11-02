import unittest
from arcade.game_096_pooyan import (
    Game096Pooyan,
    STATE_DEFENDING,
    STATE_MAMA_HIT,
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


class TestGame096Pooyan(unittest.TestCase):
    def setUp(self):
        self.game = Game096Pooyan()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 96)
        self.assertEqual(self.game.name, "经典猪小弟")
        self.assertEqual(self.game.english_name, "Pooyan")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("悬崖升降吊篮滑行", self.game.core_mechanic)

    def test_elevator_basket_scrolling(self):
        init_y = self.game.basket_y
        self.game.update(0.1, KEY_UP)
        self.assertLess(self.game.basket_y, init_y)

        self.game.update(0.1, KEY_DOWN)
        self.assertGreater(self.game.basket_y, 2.0)

    def test_shoot_arrow(self):
        self.game.update(0.05, KEY_A)
        active_arrows = [a for a in self.game.arrows if a["active"]]
        self.assertEqual(len(active_arrows), 1)
        self.assertLess(active_arrows[0]["x"], 13.0)
        self.assertEqual(active_arrows[0]["y"], self.game.basket_y)
        self.assertLess(active_arrows[0]["vx"], 0.0)

    def test_arrow_pops_balloon(self):
        # Place wolf in path of arrow
        w = self.game.wolves[0]
        w["active"] = True
        w["is_falling"] = False
        w["balloon_hp"] = 1
        w["x"] = 8.0
        w["y"] = self.game.basket_y + 1.0  # Balloon is at y-1.0 = basket_y

        init_score = self.game.score
        init_def = self.game.wolves_defeated

        # Shoot arrow
        self.game.update(0.05, KEY_A)
        # Advance arrow until collision
        for _ in range(10):
            self.game.update(0.05, 0)

        self.assertTrue(w["is_falling"])
        self.assertEqual(self.game.score, init_score + 260)  # 10 shoot + 50 hit + 200 pop
        self.assertEqual(self.game.wolves_defeated, init_def + 1)

    def test_two_hit_balloon(self):
        w = self.game.wolves[0]
        w["active"] = True
        w["is_falling"] = False
        w["balloon_hp"] = 2
        w["x"] = 10.0
        w["y"] = self.game.basket_y + 1.0

        # Shoot first arrow
        self.game.update(0.05, KEY_A)
        for _ in range(5):
            self.game.update(0.05, 0)

        self.assertEqual(w["balloon_hp"], 1)
        self.assertFalse(w["is_falling"])

        # Shoot second arrow
        self.game.shoot_cooldown = 0.0
        self.game.update(0.05, KEY_A)
        for _ in range(5):
            self.game.update(0.05, 0)

        self.assertEqual(w["balloon_hp"], 0)
        self.assertTrue(w["is_falling"])

    def test_throw_meat_parabolic_arc(self):
        self.assertTrue(self.game.meat_available)
        self.assertFalse(self.game.meat_active)

        # Press Button B to throw meat
        self.game.update(0.05, KEY_B)
        self.assertFalse(self.game.meat_available)
        self.assertTrue(self.game.meat_active)
        self.assertLess(self.game.meat_x, 13.0)
        init_vy = self.game.meat_vy

        # Advance flight
        for _ in range(10):
            self.game.update(0.05, 0)

        self.assertLess(self.game.meat_x, 13.0)
        self.assertGreater(self.game.meat_vy, init_vy)  # Curved downward by gravity

    def test_meat_cleaves_wolves(self):
        w = self.game.wolves[0]
        w["active"] = True
        w["is_falling"] = False
        w["x"] = 8.0
        w["y"] = self.game.basket_y

        self.game.update(0.05, KEY_B)
        # Advance until meat connects with wolf
        for _ in range(15):
            self.game.update(0.05, 0)

        self.assertTrue(w["is_falling"])

    def test_meat_reloads_after_cooldown(self):
        self.game.update(0.05, KEY_B)
        self.assertFalse(self.game.meat_available)

        # Fast forward reload timer (5.0s)
        self.game.meat_active = False
        self.game.meat_reload_timer = 0.08
        self.game.update(0.05, 0)
        self.game.update(0.05, 0)
        self.assertTrue(self.game.meat_available)

    def test_wolf_attacks_basket(self):
        w = self.game.wolves[0]
        w["active"] = True
        w["is_falling"] = False
        w["x"] = 14.0
        w["y"] = self.game.basket_y

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_MAMA_HIT)

    def test_stage_clear_and_render(self):
        self.game.wolves_defeated = 6
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

        # Framebuffer render check
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 96)


if __name__ == "__main__":
    unittest.main()
