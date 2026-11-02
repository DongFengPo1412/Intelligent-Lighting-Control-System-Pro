import unittest
from arcade.game_095_burgertime import (
    Game095BurgerTime,
    STATE_COOKING,
    STATE_CHEF_HIT,
    STATE_STAGE_CLEAR,
    STATE_GAME_OVER,
    ING_BUN_TOP,
    ING_PATTY,
    ING_BUN_BOTTOM,
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


class TestGame095BurgerTime(unittest.TestCase):
    def setUp(self):
        self.game = Game095BurgerTime()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 95)
        self.assertEqual(self.game.name, "汉堡时代")
        self.assertEqual(self.game.english_name, "BurgerTime")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("踩踏巨型汉堡分层下落拼接压怪", self.game.core_mechanic)

    def test_walkway_and_ladder_movement(self):
        # Walk horizontally on floor y=13
        self.game.px = 4.0
        self.game.py = 13.0
        self.game.update(0.1, KEY_RIGHT)
        self.assertGreater(self.game.px, 4.0)
        self.assertEqual(self.game.facing, 1)

        # Climb up ladder at x=4.0
        self.game.px = 4.0
        self.game.update(0.1, KEY_UP)
        self.assertLess(self.game.py, 13.0)

    def test_trample_burger_segments(self):
        # Position chef on layer 0 (y=3, x=2..5)
        layer = self.game.layers[0]
        self.assertEqual(layer["stepped_mask"], 0)

        self.game.py = 3.0
        # Step through segments 0, 1, 2, 3
        for x_pos in (2.0, 3.0, 4.0, 5.0):
            self.game.px = x_pos
            self.game.update(0.05, 0)

        # All 4 segments stepped -> layer is falling!
        self.assertTrue(layer["is_falling"])
        self.assertEqual(layer["target_y"], 6.0)

    def test_burger_layer_falls_to_plate(self):
        # Set layer 2 (bottom bun) falling toward plate y=13
        layer = self.game.layers[2]
        layer["y"] = 12.0
        layer["target_y"] = 13.0
        layer["is_falling"] = True

        for _ in range(10):
            self.game.update(0.05, 0)

        self.assertFalse(layer["is_falling"])
        self.assertEqual(layer["y"], 13.0)
        self.assertTrue(layer["on_plate"])

    def test_falling_layer_squashes_enemy(self):
        layer = self.game.layers[0]
        layer["y"] = 4.0
        layer["target_y"] = 6.0
        layer["is_falling"] = True

        # Place hot dog under falling layer
        e = self.game.enemies[0]
        e["active"] = True
        e["x"] = 3.0
        e["y"] = 4.5

        init_score = self.game.score
        self.game.update(0.05, 0)

        self.assertFalse(e["active"])
        self.assertEqual(self.game.score, init_score + 500)

    def test_domino_cascading_drop(self):
        # Layer 0 (top bun) lands on Layer 1 (patty at y=6)
        l0 = self.game.layers[0]
        l1 = self.game.layers[1]

        l0["y"] = 5.8
        l0["target_y"] = 6.0
        l0["is_falling"] = True

        l1["y"] = 6.0
        l1["target_y"] = 6.0
        l1["is_falling"] = False

        self.game.update(0.05, 0)
        # Layer 1 should now be triggered to fall!
        self.assertTrue(l1["is_falling"])
        self.assertEqual(l1["target_y"], 9.0)

    def test_pepper_shaker_spray(self):
        self.assertEqual(self.game.peppers_left, 5)
        init_score = self.game.score

        # Press Button A to shake pepper
        self.game.update(0.05, KEY_A)
        self.assertEqual(self.game.peppers_left, 4)
        self.assertGreater(self.game.pepper_spray_timer, 0.0)
        self.assertEqual(self.game.score, init_score + 10)

    def test_pepper_stuns_enemy(self):
        # Place enemy in front of chef
        e = self.game.enemies[0]
        e["active"] = True
        e["x"] = self.game.px + 1.2
        e["y"] = self.game.py
        e["stun_timer"] = 0.0

        self.game.update(0.05, KEY_A)
        self.assertGreater(e["stun_timer"], 0.0)

    def test_enemy_attacks_chef(self):
        e = self.game.enemies[0]
        e["active"] = True
        e["stun_timer"] = 0.0
        e["x"] = self.game.px
        e["y"] = self.game.py

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_CHEF_HIT)

    def test_all_burgers_completed_and_render(self):
        for l in self.game.layers:
            l["on_plate"] = True

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)
        self.assertEqual(self.game.burgers_completed, 2)

        # Test framebuffer rendering
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 95)


if __name__ == "__main__":
    unittest.main()
