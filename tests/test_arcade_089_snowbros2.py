import unittest
from arcade.game_089_snowbros2 import (
    Game089SnowBros2,
    STATE_PLAYING,
    STATE_HERO_HIT,
    STATE_STAGE_CLEAR,
    STATE_GAME_OVER,
    ELEM_SNOW,
    ELEM_WATER,
    ELEM_LIGHTNING,
    ELEM_WIND,
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


class TestGame089SnowBros2(unittest.TestCase):
    def setUp(self):
        self.game = Game089SnowBros2()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 89)
        self.assertEqual(self.game.name, "雪人兄弟2")
        self.assertEqual(self.game.english_name, "Snow Bros. 2")
        self.assertEqual(self.game.release_year, 1994)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("四属性精灵吹气充气球与多属性踢飞弹射", self.game.core_mechanic)

    def test_movement_and_gravity(self):
        init_x = self.game.px
        self.game.update(0.1, KEY_RIGHT)
        self.assertGreater(self.game.px, init_x)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_LEFT)
        self.assertEqual(self.game.facing, -1)

    def test_jump(self):
        self.assertTrue(self.game.on_ground)
        self.game.update(0.05, KEY_UP)
        self.assertFalse(self.game.on_ground)
        self.assertLess(self.game.vy, 0.0)

    def test_cycle_elemental_elf(self):
        self.assertEqual(self.game.current_element, ELEM_SNOW)

        # Cycle to Water (Down + B)
        self.game.update(0.05, KEY_DOWN | KEY_B)
        self.assertEqual(self.game.current_element, ELEM_WATER)

        # Release keys then cycle to Lightning
        self.game.update(0.05, 0)
        self.game.update(0.05, KEY_DOWN | KEY_B)
        self.assertEqual(self.game.current_element, ELEM_LIGHTNING)

        # Cycle to Wind
        self.game.update(0.05, 0)
        self.game.update(0.05, KEY_DOWN | KEY_B)
        self.assertEqual(self.game.current_element, ELEM_WIND)

        # Cycle back to Snow
        self.game.update(0.05, 0)
        self.game.update(0.05, KEY_DOWN | KEY_B)
        self.assertEqual(self.game.current_element, ELEM_SNOW)

    def test_shoot_elemental_projectile(self):
        self.game.update(0.05, KEY_A)
        active_shots = [p for p in self.game.projectiles if p["active"]]
        self.assertEqual(len(active_shots), 1)
        self.assertEqual(active_shots[0]["elem"], ELEM_SNOW)
        self.assertGreater(active_shots[0]["vx"], 0.0)

    def test_projectile_inflates_monster(self):
        # Place monster in front of hero
        m = self.game.monsters[0]
        m["x"] = self.game.px + 2.0
        m["y"] = self.game.py
        m["inflate_level"] = 0
        init_score = self.game.score

        # Fire shot
        self.game.update(0.05, KEY_A)
        # Advance until projectile hits monster
        self.game.update(0.25, 0)
        self.assertGreater(m["inflate_level"], 0)
        self.assertGreater(self.game.score, init_score)

    def test_lightning_chain_shock(self):
        # Switch to lightning
        self.game.current_element = ELEM_LIGHTNING

        # Put two monsters adjacent
        m0 = self.game.monsters[0]
        m1 = self.game.monsters[1]
        m0["x"] = self.game.px + 2.0
        m0["y"] = self.game.py
        m0["inflate_level"] = 1  # will become 2 on hit
        m1["x"] = m0["x"] + 1.5
        m1["y"] = self.game.py
        m1["inflate_level"] = 0

        # Fire lightning shot
        self.game.update(0.05, KEY_A)
        self.game.update(0.25, 0)

        # Both m0 and m1 should have their inflate_level increased by chain shock
        self.assertGreaterEqual(m0["inflate_level"], 2)
        self.assertGreaterEqual(m1["inflate_level"], 1)

    def test_kick_inflated_ball(self):
        # Fully inflate monster 0
        m0 = self.game.monsters[0]
        m0["active"] = True
        m0["x"] = self.game.px + 0.8
        m0["y"] = self.game.py
        m0["inflate_level"] = 3
        m0["is_kicked"] = False

        init_score = self.game.score
        # Press Button B to kick
        self.game.update(0.05, KEY_B)
        self.assertTrue(m0["is_kicked"])
        self.assertGreater(m0["kick_vx"], 0.0)
        self.assertEqual(self.game.score, init_score + 50)

    def test_kicked_ball_crushes_monsters(self):
        # Monster 0 is kicked rolling into Monster 1
        m0 = self.game.monsters[0]
        m0["active"] = True
        m0["is_kicked"] = True
        m0["x"] = 5.0
        m0["y"] = 13.0
        m0["kick_vx"] = 8.0

        m1 = self.game.monsters[1]
        m1["active"] = True
        m1["x"] = 5.4
        m1["y"] = 13.0

        init_score = self.game.score
        init_defeated = self.game.monsters_defeated

        self.game.update(0.05, 0)
        self.assertFalse(m1["active"])
        self.assertEqual(self.game.score, init_score + 200)
        self.assertEqual(self.game.monsters_defeated, init_defeated + 1)

    def test_monster_hurts_hero_and_stage_clear(self):
        # Case 1: uninflated monster touching hero hurts hero
        m = self.game.monsters[0]
        m["active"] = True
        m["inflate_level"] = 0
        m["is_kicked"] = False
        m["x"] = self.game.px
        m["y"] = self.game.py

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_HERO_HIT)

        # Case 2: defeating required monsters clears stage
        self.game.reset()
        self.game.monsters_defeated = 6
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1000)

        # Test render framebuffer
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))


if __name__ == "__main__":
    unittest.main()
