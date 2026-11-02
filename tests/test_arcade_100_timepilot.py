import unittest
import math
from arcade.game_100_timepilot import (
    Game100TimePilot,
    STATE_DOGFIGHT,
    STATE_TIME_WARP,
    STATE_PLAYER_SHOT_DOWN,
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


class TestGame100TimePilot(unittest.TestCase):
    def setUp(self):
        self.game = Game100TimePilot()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 100)
        self.assertEqual(self.game.name, "时空领航员")
        self.assertEqual(self.game.english_name, "Time Pilot")
        self.assertEqual(self.game.release_year, 1982)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("360度环形多向空战", self.game.core_mechanic)

    def test_360_rotation(self):
        # Initial angle is -pi/2 (facing UP)
        init_angle = self.game.player_angle
        # Press KEY_RIGHT to turn towards 0.0 rad
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertNotEqual(self.game.player_angle, init_angle)

    def test_afterburner_boost(self):
        self.assertEqual(self.game.speed, 4.5)
        # Hold KEY_B
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.speed, 7.5)
        # Release KEY_B
        self.game.update(0.05, 0, KEY_B)
        self.assertEqual(self.game.speed, 4.5)

    def test_fire_player_bullet(self):
        self.assertFalse(any(b["active"] for b in self.game.player_bullets))
        # Press KEY_A
        self.game.update(0.05, KEY_A, 0)
        active_bullets = [b for b in self.game.player_bullets if b["active"]]
        self.assertEqual(len(active_bullets), 1)

    def test_world_scrolling_clouds(self):
        init_c0_y = self.game.clouds[0]["y"]
        # Heading facing UP (vy = -speed), so world scrolls DOWN (scroll_y > 0)
        self.game.update(0.1, 0, 0)
        self.assertGreater(self.game.clouds[0]["y"], init_c0_y)

    def test_destroy_escort_and_drop_parachute(self):
        self.game.enemies[0]["x"] = 7.5
        self.game.enemies[0]["y"] = 4.0
        self.game.enemies[0]["hp"] = 1
        self.game.enemies[0]["active"] = True

        # Fire bullet towards (7.5, 4.0)
        self.game.player_bullets[0]["active"] = True
        self.game.player_bullets[0]["x"] = 7.5
        self.game.player_bullets[0]["y"] = 4.2
        self.game.player_bullets[0]["vx"] = 0.0
        self.game.player_bullets[0]["vy"] = -10.0
        self.game.player_bullets[0]["life"] = 1.0

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertGreater(self.game.score, init_score)
        self.assertEqual(self.game.squadron_defeated, 1)
        # 1st defeated escort drops parachute (squadron_defeated % 2 == 1)
        self.assertTrue(any(p["active"] for p in self.game.parachutes))

    def test_rescue_parachutist(self):
        self.game.parachutes[0]["active"] = True
        self.game.parachutes[0]["x"] = 7.5
        self.game.parachutes[0]["y"] = 7.5

        init_score = self.game.score
        self.game.update(0.05, 0, 0)

        self.assertFalse(self.game.parachutes[0]["active"])
        self.assertEqual(self.game.score, init_score + 500)

    def test_boss_spawn_and_destruction_triggers_warp(self):
        self.game.squadron_defeated = 4
        # Defeat 5th escort to spawn boss
        self.game.enemies[0]["x"] = 7.5
        self.game.enemies[0]["y"] = 5.0
        self.game.enemies[0]["vx"] = 0.0
        self.game.enemies[0]["vy"] = 0.0
        self.game.enemies[0]["hp"] = 1
        self.game.enemies[0]["active"] = True

        self.game.player_bullets[0]["active"] = True
        self.game.player_bullets[0]["x"] = 7.5
        self.game.player_bullets[0]["y"] = 5.0
        self.game.player_bullets[0]["life"] = 1.0

        self.game.update(0.05, 0, 0)
        self.assertTrue(self.game.boss_active)

        # Shoot Boss
        boss = self.game.enemies[-1]
        self.assertTrue(boss["is_boss"])
        boss["x"] = 7.5
        boss["y"] = 5.0
        boss["vx"] = 0.0
        boss["vy"] = 0.0
        boss["hp"] = 1

        self.game.player_bullets[0]["active"] = True
        self.game.player_bullets[0]["x"] = 7.5
        self.game.player_bullets[0]["y"] = 5.0
        self.game.player_bullets[0]["life"] = 1.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_TIME_WARP)

    def test_player_collision_shot_down(self):
        self.game.enemy_bullets[0]["active"] = True
        self.game.enemy_bullets[0]["x"] = 7.5
        self.game.enemy_bullets[0]["y"] = 7.5
        self.game.enemy_bullets[0]["life"] = 1.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_SHOT_DOWN)

    def test_time_warp_era_transition_and_render(self):
        self.game.state = STATE_TIME_WARP
        self.game.state_timer = 2.3
        self.game.era = 0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.era, 1)  # Era advanced to 1940
        self.assertEqual(self.game.state, STATE_DOGFIGHT)

        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)
        self.assertGreater(sum(fb), 0)


if __name__ == "__main__":
    unittest.main()
