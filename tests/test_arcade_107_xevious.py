import unittest
from arcade.game_107_xevious import (
    Game107Xevious,
    STATE_FLYING,
    STATE_BOSS_ANDOR,
    STATE_SHIP_EXPLODED,
    STATE_AREA_CLEAR,
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


class TestGame107Xevious(unittest.TestCase):
    def setUp(self):
        self.game = Game107Xevious()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 107)
        self.assertEqual(self.game.name, "铁板阵")
        self.assertEqual(self.game.english_name, "Xevious")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("双层分立打击", self.game.core_mechanic)

    def test_ship_8way_movement(self):
        init_x = self.game.px
        init_y = self.game.py
        # Move up and right
        self.game.update(0.05, KEY_UP | KEY_RIGHT, 0)
        self.assertGreater(self.game.px, init_x)
        self.assertLess(self.game.py, init_y)

    def test_air_zapper_fire(self):
        self.assertFalse(any(b["active"] for b in self.game.player_bullets))
        # Press Button A
        self.game.update(0.05, KEY_A, 0)
        active_bullets = [b for b in self.game.player_bullets if b["active"]]
        self.assertEqual(len(active_bullets), 1)
        self.assertEqual(active_bullets[0]["vy"], -18.0)

    def test_air_zapper_destroys_air_enemy(self):
        # Enemy 0 at (8.0, 5.0)
        self.game.air_enemies[0]["active"] = True
        self.game.air_enemies[0]["x"] = 8.0
        self.game.air_enemies[0]["y"] = 5.0
        self.game.air_enemies[0]["vx"] = 0.0
        self.game.air_enemies[0]["vy"] = 0.0

        # Bullet hitting enemy
        self.game.player_bullets[0]["active"] = True
        self.game.player_bullets[0]["x"] = 8.0
        self.game.player_bullets[0]["y"] = 5.2
        self.game.player_bullets[0]["vy"] = -18.0

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.air_enemies[0]["active"])
        self.assertEqual(self.game.score, init_score + 100)

    def test_blaster_bomb_launch_towards_crosshair(self):
        self.game.px = 8.0
        self.game.py = 12.0
        # Press Button B
        self.game.update(0.05, KEY_B, 0)
        active_bombs = [b for b in self.game.ground_bombs if b["active"]]
        self.assertEqual(len(active_bombs), 1)
        self.assertEqual(active_bombs[0]["target_x"], 8.0)
        self.assertEqual(active_bombs[0]["target_y"], 12.0 - 3.5)

    def test_blaster_bomb_destroys_ground_pyramid(self):
        for g in self.game.ground_targets:
            g["active"] = False

        # Target Barra pyramid at (8.0, 6.0)
        self.game.ground_targets[0]["active"] = True
        self.game.ground_targets[0]["type"] = 0  # Barra
        self.game.ground_targets[0]["x"] = 8.0
        self.game.ground_targets[0]["y"] = 6.0

        # Bomb at target point detonating (timer <= 0.05)
        self.game.ground_bombs[0]["active"] = True
        self.game.ground_bombs[0]["target_x"] = 8.0
        self.game.ground_bombs[0]["target_y"] = 6.0
        self.game.ground_bombs[0]["timer"] = 0.04

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.ground_targets[0]["active"])
        self.assertEqual(self.game.score, init_score + 200)

    def test_blaster_bomb_unearths_hidden_sol(self):
        for g in self.game.ground_targets:
            g["active"] = False

        # Secret Sol Citadel at (8.0, 6.0)
        self.game.ground_targets[0]["active"] = True
        self.game.ground_targets[0]["type"] = 2  # Sol citadel
        self.game.ground_targets[0]["x"] = 8.0
        self.game.ground_targets[0]["y"] = 6.0

        self.game.ground_bombs[0]["active"] = True
        self.game.ground_bombs[0]["target_x"] = 8.0
        self.game.ground_bombs[0]["target_y"] = 6.0
        self.game.ground_bombs[0]["timer"] = 0.04

        init_score = self.game.score
        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.ground_targets[0]["active"])
        self.assertEqual(self.game.score, init_score + 2000)

    def test_enemy_collision_destroys_ship(self):
        self.game.px = 8.0
        self.game.py = 8.0
        self.game.air_enemies[0]["active"] = True
        self.game.air_enemies[0]["x"] = 8.0
        self.game.air_enemies[0]["y"] = 8.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_SHIP_EXPLODED)

    def test_andor_genesis_boss_defeat(self):
        self.game.spawn_andor_genesis()
        self.assertEqual(self.game.state, STATE_BOSS_ANDOR)
        self.game.andor_hp = 1
        self.game.andor_x = 5.0
        self.game.andor_y = 3.0
        self.game.andor_vx = 0.0

        # Shoot core with air bullet at (6.5, 3.5)
        self.game.player_bullets[0]["active"] = True
        self.game.player_bullets[0]["x"] = 6.5
        self.game.player_bullets[0]["y"] = 3.5
        self.game.player_bullets[0]["vy"] = 0.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_AREA_CLEAR)
        self.assertGreater(self.game.score, 4000)

    def test_framebuffer_render(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
