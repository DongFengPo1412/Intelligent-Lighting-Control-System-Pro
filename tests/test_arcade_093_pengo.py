import unittest
from arcade.game_093_pengo import (
    Game093Pengo,
    STATE_PLAYING,
    STATE_PENGO_HIT,
    STATE_ROUND_CLEAR,
    STATE_GAME_OVER,
    BLOCK_EMPTY,
    BLOCK_ICE,
    BLOCK_DIAMOND,
    BLOCK_WALL,
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


class TestGame093Pengo(unittest.TestCase):
    def setUp(self):
        self.game = Game093Pengo()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 93)
        self.assertEqual(self.game.name, "企鹅推冰块")
        self.assertEqual(self.game.english_name, "Pengo")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("推滑冰块碾压击杀、粉碎开路", self.game.core_mechanic)

    def test_pengo_grid_movement(self):
        init_x = self.game.px
        init_y = self.game.py

        # Step up into empty space
        self.game.update(0.05, KEY_UP)
        self.assertEqual(self.game.py, init_y - 1)
        self.assertEqual(self.game.facing_y, -1)

    def test_push_ice_block_slides(self):
        # Place ice block directly in front of Pengo, with empty behind it
        self.game.px = 5
        self.game.py = 5
        self.game.facing_x = 1
        self.game.facing_y = 0
        self.game.grid[5][6] = BLOCK_ICE
        self.game.grid[5][7] = BLOCK_EMPTY

        init_score = self.game.score
        # Press Button A to push
        self.game.update(0.05, KEY_A)
        self.assertTrue(self.game.sliding_active)
        self.assertEqual(self.game.grid[5][6], BLOCK_EMPTY)
        self.assertGreater(self.game.sl_vx, 0.0)
        self.assertEqual(self.game.score, init_score + 20)

    def test_push_ice_block_shatters_if_blocked(self):
        # Place ice block against perimeter wall
        self.game.px = 13
        self.game.py = 5
        self.game.facing_x = 1
        self.game.facing_y = 0
        self.game.grid[5][14] = BLOCK_ICE
        # grid[5][15] is BLOCK_WALL

        init_score = self.game.score
        self.game.update(0.05, KEY_A)
        self.assertFalse(self.game.sliding_active)
        self.assertEqual(self.game.grid[5][14], BLOCK_EMPTY)  # Shattered!
        self.assertEqual(self.game.score, init_score + 100)

    def test_sliding_block_crushes_snobee(self):
        self.game.sliding_active = True
        self.game.sl_x = 3.0
        self.game.sl_y = 5.0
        self.game.sl_vx = 12.0
        self.game.sl_vy = 0.0

        # Place Sno-Bee in path
        b = self.game.snobees[0]
        b["active"] = True
        b["x"] = 4
        b["y"] = 5

        init_score = self.game.score
        init_crush = self.game.snobees_crushed

        self.game.update(0.05, 0)
        self.assertFalse(b["active"])
        self.assertEqual(self.game.score, init_score + 400)
        self.assertEqual(self.game.snobees_crushed, init_crush + 1)

    def test_sliding_block_stops_at_wall(self):
        self.game.sliding_active = True
        self.game.sl_x = 13.0
        self.game.sl_y = 5.0
        self.game.sl_vx = 12.0
        self.game.sl_vy = 0.0
        self.game.sl_is_diamond = False

        # Advance until block hits wall x=15
        for _ in range(5):
            self.game.update(0.05, 0)

        self.assertFalse(self.game.sliding_active)
        self.assertEqual(self.game.grid[5][14], BLOCK_ICE)

    def test_perimeter_wall_shake(self):
        # Pengo faces left outer wall
        self.game.px = 1
        self.game.py = 5
        self.game.facing_x = -1
        self.game.facing_y = 0

        # Place Sno-Bee on perimeter wall
        b = self.game.snobees[0]
        b["active"] = True
        b["x"] = 1
        b["y"] = 2
        b["stun_timer"] = 0.0

        init_score = self.game.score
        self.game.update(0.05, KEY_B)
        self.assertGreater(b["stun_timer"], 0.0)
        self.assertEqual(self.game.score, init_score + 50)

    def test_diamond_alignment_flash(self):
        # Clear existing diamonds
        for y in range(16):
            for x in range(16):
                if self.game.grid[y][x] == BLOCK_DIAMOND:
                    self.game.grid[y][x] = BLOCK_EMPTY

        # Align 3 diamonds horizontally at y=5, x=4, 5, 6
        self.game.grid[5][4] = BLOCK_DIAMOND
        self.game.grid[5][5] = BLOCK_DIAMOND
        self.game.grid[5][6] = BLOCK_DIAMOND

        init_score = self.game.score
        self.game._check_diamond_alignment()
        self.assertEqual(self.game.score, init_score + 5000)
        for b in self.game.snobees:
            if b["active"]:
                self.assertGreater(b["stun_timer"], 0.0)

    def test_snobee_stuns_and_hit(self):
        # Case 1: active bee touches Pengo
        b = self.game.snobees[0]
        b["active"] = True
        b["stun_timer"] = 0.0
        b["x"] = self.game.px
        b["y"] = self.game.py
        b["move_timer"] = 0.3

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_PENGO_HIT)

        # Case 2: stunned bee is safely squished
        self.game.reset()
        b = self.game.snobees[0]
        b["active"] = True
        b["stun_timer"] = 3.0
        b["x"] = self.game.px
        b["y"] = self.game.py
        init_score = self.game.score

        self.game.update(0.05, 0)
        self.assertFalse(b["active"])
        self.assertEqual(self.game.score, init_score + 100)

    def test_round_clear_and_render(self):
        self.game.snobees_crushed = 4
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_ROUND_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

        # Framebuffer render check
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 93)


if __name__ == "__main__":
    unittest.main()
