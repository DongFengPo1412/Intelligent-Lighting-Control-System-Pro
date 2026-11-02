import unittest
from arcade.game_092_sengokublade import (
    Game092SengokuBlade,
    STATE_AIR_BATTLE,
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


class TestGame092SengokuBlade(unittest.TestCase):
    def setUp(self):
        self.game = Game092SengokuBlade()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 92)
        self.assertEqual(self.game.name, "战国之刃")
        self.assertEqual(self.game.english_name, "Sengoku Blade")
        self.assertEqual(self.game.release_year, 1996)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("横版贴脸拔刀斩消弹、式神蓄力喷射与忍法曼荼罗", self.game.core_mechanic)

    def test_8way_flight_movement(self):
        init_x = self.game.px
        init_y = self.game.py

        self.game.update(0.1, KEY_RIGHT | KEY_DOWN)
        self.assertGreater(self.game.px, init_x)
        self.assertGreater(self.game.py, init_y)

        self.game.update(0.1, KEY_LEFT | KEY_UP)
        self.assertLess(self.game.px, 14.5)
        self.assertGreater(self.game.py, 1.0)

    def test_talisman_normal_shot(self):
        # Move hero far away from enemies
        self.game.px = 2.0
        self.game.py = 2.0
        for e in self.game.enemies:
            e["x"] = 14.0
            e["y"] = 14.0

        # Tap Button A (press on frame 1, release on frame 2)
        self.game.update(0.05, KEY_A)
        self.game.update(0.05, 0)

        active_shots = [b for b in self.game.hero_bullets if b["active"]]
        self.assertEqual(len(active_shots), 1)
        self.assertFalse(active_shots[0]["is_charge_shot"])
        self.assertGreater(active_shots[0]["vx"], 0.0)

    def test_close_range_katana_melee_slash(self):
        # Place enemy within 2.0 units directly in front
        e = self.game.enemies[0]
        e["active"] = True
        e["x"] = self.game.px + 1.5
        e["y"] = self.game.py
        e["hp"] = 4
        init_score = self.game.score

        # Tap Button A
        self.game.update(0.05, KEY_A)
        self.game.update(0.05, 0)

        self.assertGreater(self.game.melee_timer, 0.0)
        self.assertLess(e["hp"], 4)  # Melee damage inflicted
        self.assertGreater(self.game.score, init_score)

    def test_melee_slash_erases_enemy_bullets(self):
        # Place enemy and enemy bullet in front of hero
        e = self.game.enemies[0]
        e["active"] = True
        e["x"] = self.game.px + 1.8
        e["y"] = self.game.py

        eb = self.game.enemy_bullets[0]
        eb["active"] = True
        eb["x"] = self.game.px + 1.2
        eb["y"] = self.game.py

        init_score = self.game.score
        # Trigger melee slash
        self.game.update(0.05, KEY_A)
        self.game.update(0.05, 0)

        # Bullet should be sliced/erased!
        self.assertFalse(eb["active"])
        self.assertGreater(self.game.score, init_score)

    def test_shikigami_charge_shot(self):
        # Hold Button A for 0.8s
        for _ in range(16):
            self.game.update(0.05, KEY_A)

        self.assertGreaterEqual(self.game.charge_timer, 0.75)
        self.assertTrue(self.game.is_charging)

        # Release Button A
        self.game.update(0.05, 0)
        active_charge_shots = [b for b in self.game.hero_bullets if b["active"] and b["is_charge_shot"]]
        self.assertEqual(len(active_charge_shots), 1)
        self.assertGreater(active_charge_shots[0]["vx"], 12.0)

    def test_ninja_mandala_bomb(self):
        self.game.enemy_bullets[0]["active"] = True
        self.game.enemy_bullets[0]["x"] = 8.0
        self.game.enemy_bullets[0]["y"] = 8.0

        init_bombs = self.game.bombs
        init_score = self.game.score

        # Press Button B
        self.game.update(0.05, KEY_B)
        self.assertEqual(self.game.bombs, init_bombs - 1)
        self.assertGreater(self.game.bomb_timer, 0.0)
        self.assertFalse(self.game.enemy_bullets[0]["active"])  # Cleared!
        self.assertGreater(self.game.score, init_score)

    def test_enemy_bullet_hits_hero(self):
        eb = self.game.enemy_bullets[0]
        eb["active"] = True
        eb["x"] = self.game.px
        eb["y"] = self.game.py
        self.game.bomb_timer = 0.0

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_HERO_HIT)

    def test_bomb_invulnerability(self):
        self.game.bomb_timer = 1.0  # Bomb barrier active
        eb = self.game.enemy_bullets[0]
        eb["active"] = True
        eb["x"] = self.game.px
        eb["y"] = self.game.py

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_AIR_BATTLE)

    def test_stage_clear_and_render(self):
        self.game.enemies_defeated = 6
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 1500)

        # Framebuffer render check
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 92)


if __name__ == "__main__":
    unittest.main()
