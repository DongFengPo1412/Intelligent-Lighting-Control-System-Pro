import unittest
from arcade.game_115_tempest import (
    Game115Tempest,
    STATE_PLAYING,
    STATE_PLAYER_DYING,
    STATE_TUBE_WARP,
    STATE_GAME_OVER,
    get_sector_pos,
    NUM_SECTORS,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)


class TestGame115Tempest(unittest.TestCase):
    def setUp(self):
        self.game = Game115Tempest()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 115)
        self.assertEqual(self.game.name, "暴风雨")
        self.assertEqual(self.game.english_name, "Tempest")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("3D透视几何管道", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.super_zappers, 1)
        self.assertEqual(self.game.wave, 1)
        self.assertEqual(self.game.player_sector, 0)

    def test_rim_crawling_left_and_right(self):
        self.assertEqual(self.game.player_sector, 0)

        # Move Left -> Sector 15
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.player_sector, 15)

        # Move Right -> Sector 0
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_sector, 0)

        # Move Right again -> Sector 1
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_sector, 1)

    def test_fire_shot_down_sector(self):
        self.game.player_sector = 4
        self.game.update(0.05, KEY_A, 0)

        active_shots = [s for s in self.game.shots if s["active"]]
        self.assertEqual(len(active_shots), 1)
        self.assertEqual(active_shots[0]["sector"], 4)
        self.assertAlmostEqual(active_shots[0]["depth"], 0.95, delta=0.2)

    def test_enemy_climbing_from_abyss(self):
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["sector"] = 2
        self.game.enemies[0]["depth"] = 0.2
        self.game.enemies[0]["speed"] = 0.5
        self.game.enemies[0]["on_rim"] = False

        self.game.update(0.05, 0, 0)
        self.assertGreater(self.game.enemies[0]["depth"], 0.2)

    def test_shot_destroys_climbing_enemy(self):
        # Enemy at sector 5, depth 0.6
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["sector"] = 5
        self.game.enemies[0]["depth"] = 0.6
        self.game.enemies[0]["speed"] = 0.0
        self.game.enemies[0]["on_rim"] = False

        # Shot at sector 5, depth 0.6
        self.game.shots[0]["active"] = True
        self.game.shots[0]["sector"] = 5
        self.game.shots[0]["depth"] = 0.6
        self.game.shots[0]["speed"] = 0.0

        init_score = self.game.score
        self.game.update(0.01, 0, 0)

        self.assertFalse(self.game.enemies[0]["active"])
        self.assertFalse(self.game.shots[0]["active"])
        self.assertEqual(self.game.score, init_score + 150)

    def test_enemy_reaches_rim_and_crawls(self):
        self.game.player_sector = 8
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["sector"] = 2
        self.game.enemies[0]["depth"] = 0.98
        self.game.enemies[0]["speed"] = 1.0
        self.game.enemies[0]["on_rim"] = False

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.enemies[0]["on_rim"])

    def test_super_zapper_vaporizes_all_enemies(self):
        self.game.enemies[0]["active"] = True
        self.game.enemies[1]["active"] = True
        self.assertEqual(self.game.super_zappers, 1)

        init_score = self.game.score
        self.game.update(0.05, KEY_B, 0)

        self.assertEqual(self.game.super_zappers, 0)
        self.assertFalse(self.game.enemies[0]["active"])
        self.assertFalse(self.game.enemies[1]["active"])
        self.assertEqual(self.game.score, init_score + 300)

    def test_rim_collision_destroys_player(self):
        self.game.player_sector = 4
        self.game.enemies[0]["active"] = True
        self.game.enemies[0]["sector"] = 4
        self.game.enemies[0]["on_rim"] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_DYING)

    def test_wave_clear_tube_warp(self):
        self.game.enemies_remaining = 0
        for e in self.game.enemies:
            e["active"] = False

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_TUBE_WARP)
        self.assertEqual(self.game.score, init_score + 1000)


if __name__ == "__main__":
    unittest.main()
