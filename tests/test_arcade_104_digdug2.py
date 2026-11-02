import unittest
from arcade.game_104_digdug2 import (
    Game104DigDug2,
    STATE_EXPLORING,
    STATE_DRILLING_FAULT,
    STATE_ISLAND_COLLAPSE,
    STATE_PLAYER_DROWN,
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


class TestGame104DigDug2(unittest.TestCase):
    def setUp(self):
        self.game = Game104DigDug2()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 104)
        self.assertEqual(self.game.name, "挖金者二代")
        self.assertEqual(self.game.english_name, "Dig Dug II")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("海岛地脉钉柱钻孔打桩", self.game.core_mechanic)

    def test_player_locomotion(self):
        init_x = self.game.px
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertGreater(self.game.px, init_x)
        self.assertEqual(self.game.facing_x, 1)
        self.assertEqual(self.game.facing_y, 0)

    def test_harpoon_pump_stuns_monster(self):
        # Place monster directly ahead of player (facing right at x=8.0, y=8.0)
        self.game.facing_x = 1
        self.game.facing_y = 0
        self.game.monsters[0]["x"] = 9.5
        self.game.monsters[0]["y"] = 8.0
        self.game.monsters[0]["stun_timer"] = 0.0

        init_score = self.game.score
        # Press Button A
        self.game.update(0.05, KEY_A, 0)
        self.assertGreater(self.game.monsters[0]["stun_timer"], 0.0)
        self.assertEqual(self.game.score, init_score + 50)

    def test_walk_off_island_drowns_player(self):
        self.game.px = 1.6
        self.game.py = 8.0
        # Walk left into ocean (x < 1.5 rounds to x <= 1, which is ocean)
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DROWN)

    def test_jackhammer_drill_at_peg(self):
        # Move player to Peg 0 at (4, 4)
        self.game.px = 4.0
        self.game.py = 4.0
        # Press Button B
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.state, STATE_DRILLING_FAULT)
        self.assertEqual(self.game.active_peg_idx, 0)

    def test_fault_line_break_and_island_collapse(self):
        self.game.px = 4.0
        self.game.py = 4.0
        self.game.state = STATE_DRILLING_FAULT
        self.game.active_peg_idx = 0
        self.game.state_timer = 0.45  # Advance past 0.4s drill time

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_ISLAND_COLLAPSE)
        # Western peninsula marked for collapse
        self.assertTrue(self.game.collapse_mask[4][3])

    def test_collapse_drowns_monsters(self):
        # Monster 0 at (3, 3) inside western collapse zone
        self.game.monsters[0]["active"] = True
        self.game.monsters[0]["x"] = 3.0
        self.game.monsters[0]["y"] = 3.0

        # Taizo safe in center at (8, 8)
        self.game.px = 8.0
        self.game.py = 8.0

        self.game.state = STATE_ISLAND_COLLAPSE
        self.game.state_timer = 0.65
        # Set collapse mask for western section
        for y in range(16):
            for x in range(5):
                self.game.collapse_mask[y][x] = True

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        # Monster drowned into ocean!
        self.assertFalse(self.game.monsters[0]["active"])
        self.assertEqual(self.game.monsters_defeated, 1)
        self.assertGreater(self.game.score, init_score)
        self.assertEqual(self.game.state, STATE_EXPLORING)

    def test_taizo_caught_on_collapse_drowns(self):
        # Taizo caught in collapsing section at (3, 3)
        self.game.px = 3.0
        self.game.py = 3.0
        self.game.state = STATE_ISLAND_COLLAPSE
        self.game.state_timer = 0.65
        for y in range(16):
            for x in range(5):
                self.game.collapse_mask[y][x] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DROWN)

    def test_stage_clear_when_monsters_eliminated(self):
        self.game.monsters_defeated = 3
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
