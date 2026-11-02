import unittest
import math
from arcade.game_109_spaceharrier import (
    Game109SpaceHarrier,
    STATE_FLYING,
    STATE_BOSS_DRAGON,
    STATE_HERO_HIT,
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


class TestGame109SpaceHarrier(unittest.TestCase):
    def setUp(self):
        self.game = Game109SpaceHarrier()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 109)
        self.assertEqual(self.game.name, "太空哈利")
        self.assertEqual(self.game.english_name, "Space Harrier")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("伪3D纵深棋盘地平线飞行", self.game.core_mechanic)

    def test_hero_8way_movement(self):
        init_x = self.game.hero_x
        init_y = self.game.hero_y
        self.game.update(0.05, KEY_LEFT | KEY_UP, 0)
        self.assertLess(self.game.hero_x, init_x)
        self.assertLess(self.game.hero_y, init_y)

    def test_dodge_roll(self):
        self.assertEqual(self.game.roll_timer, 0.0)
        self.game.update(0.05, KEY_B, 0)
        self.assertGreater(self.game.roll_timer, 0.0)

    def test_plasma_shot_fire(self):
        self.assertFalse(any(s["active"] for s in self.game.shots))
        self.game.update(0.05, KEY_A, 0)
        active_shots = [s for s in self.game.shots if s["active"]]
        self.assertEqual(len(active_shots), 1)
        self.assertAlmostEqual(active_shots[0]["z"], 0.5 + 16.0 * 0.05, places=2)

    def test_plasma_shot_destroys_drone(self):
        # Drone (type=0) at (8.0, 6.0, z=5.0)
        self.game.entities[0]["active"] = True
        self.game.entities[0]["type"] = 0
        self.game.entities[0]["x"] = 8.0
        self.game.entities[0]["y"] = 6.0
        self.game.entities[0]["z"] = 5.0

        # Shot matching location
        self.game.shots[0]["active"] = True
        self.game.shots[0]["x"] = 8.0
        self.game.shots[0]["y"] = 6.0
        self.game.shots[0]["z"] = 5.0

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.entities[0]["active"])
        self.assertEqual(self.game.score, init_score + 150)

    def test_tree_pillar_cannot_be_shot(self):
        # Tree (type=1) at (8.0, 6.0, z=5.0)
        self.game.entities[0]["active"] = True
        self.game.entities[0]["type"] = 1
        self.game.entities[0]["x"] = 8.0
        self.game.entities[0]["y"] = 6.0
        self.game.entities[0]["z"] = 5.0

        self.game.shots[0]["active"] = True
        self.game.shots[0]["x"] = 8.0
        self.game.shots[0]["y"] = 6.0
        self.game.shots[0]["z"] = 5.0

        self.game.update(0.05, 0, 0)
        # Tree remains active!
        self.assertTrue(self.game.entities[0]["active"])

    def test_oncoming_entity_hits_hero(self):
        self.game.hero_x = 8.0
        self.game.hero_y = 10.0
        self.game.roll_timer = 0.0

        self.game.entities[0]["active"] = True
        self.game.entities[0]["x"] = 8.0
        self.game.entities[0]["y"] = 10.0
        self.game.entities[0]["z"] = 1.0  # Close camera distance

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_HERO_HIT)

    def test_dodge_roll_invulnerability(self):
        self.game.hero_x = 8.0
        self.game.hero_y = 10.0
        self.game.roll_timer = 0.3  # Actively rolling!

        self.game.entities[0]["active"] = True
        self.game.entities[0]["x"] = 8.0
        self.game.entities[0]["y"] = 10.0
        self.game.entities[0]["z"] = 1.0

        self.game.update(0.05, 0, 0)
        # Did not get hit!
        self.assertEqual(self.game.state, STATE_FLYING)

    def test_dragon_boss_defeat(self):
        self.game.spawn_dragon_boss()
        self.assertEqual(self.game.state, STATE_BOSS_DRAGON)
        self.game.dragon_hp = 1
        self.game.dragon_angle = 0.0

        # After dt=0.05: dragon_angle = 0.125
        # dragon_x = 8.0 + cos(0.125)*3.5 = 11.47
        # dragon_y = 6.0 + sin(0.1875)*2.0 = 6.37
        # dragon_z = 5.5 + sin(0.125)*1.5 = 5.69
        # Shot z starts at 5.69 - 16.0*0.05 = 4.89
        self.game.shots[0]["active"] = True
        self.game.shots[0]["x"] = 8.0 + math.cos(0.125) * 3.5
        self.game.shots[0]["y"] = 6.0 + math.sin(0.125 * 1.5) * 2.0
        self.game.shots[0]["z"] = 5.5 + math.sin(0.125) * 1.5 - 0.8

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 4500)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
