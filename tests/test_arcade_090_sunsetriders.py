import unittest
from arcade.game_090_sunsetriders import (
    Game090SunsetRiders,
    STATE_SALOON_BRAWL,
    STATE_STAMPEDE,
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


class TestGame090SunsetRiders(unittest.TestCase):
    def setUp(self):
        self.game = Game090SunsetRiders()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 90)
        self.assertEqual(self.game.name, "落日骑士")
        self.assertEqual(self.game.english_name, "Sunset Riders")
        self.assertEqual(self.game.release_year, 1991)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("双枪铲地滑铲避弹与狂奔牛群借力跳跃", self.game.core_mechanic)

    def test_walk_and_facing(self):
        init_x = self.game.px
        self.game.update(0.1, KEY_RIGHT)
        self.assertGreater(self.game.px, init_x)
        self.assertEqual(self.game.facing, 1)

        self.game.update(0.1, KEY_LEFT)
        self.assertEqual(self.game.facing, -1)

    def test_jump_to_balcony_and_drop_down(self):
        # Disable bandits so test purely verifies jump/drop trajectory
        for b in self.game.bandits:
            b["active"] = False
            b["respawn_timer"] = 999.0
        for bl in self.game.bullets:
            bl["active"] = False

        # Position under balcony (x in 3.0 .. 14.5)
        self.game.px = 6.0
        self.assertEqual(self.game.py, 13.0)
        self.game.update(0.05, KEY_UP | KEY_B)
        self.assertLess(self.game.vy, 0.0)

        # Advance until landed on balcony
        for _ in range(25):
            self.game.update(0.05, 0)
        self.assertEqual(self.game.py, 8.0)
        self.assertTrue(self.game.on_ground)

        # Drop back down to ground (Down + Button B)
        self.game.update(0.05, KEY_DOWN | KEY_B)
        for _ in range(25):
            self.game.update(0.05, 0)
        self.assertEqual(self.game.py, 13.0)
        self.assertTrue(self.game.on_ground)

    def test_slide_dodge_mechanic(self):
        init_x = self.game.px
        self.assertFalse(self.game.is_sliding)

        # Trigger slide with Down + Button A
        self.game.update(0.05, KEY_DOWN | KEY_A)
        self.assertTrue(self.game.is_sliding)
        self.assertGreater(self.game.px, init_x)
        self.assertGreater(self.game.slide_timer, 0.0)

        # Slide expires after duration
        for _ in range(12):
            self.game.update(0.05, 0)
        self.assertFalse(self.game.is_sliding)

    def test_single_gun_shoot(self):
        self.game.update(0.05, KEY_A)
        active_bullets = [b for b in self.game.bullets if b["active"] and not b["is_enemy"]]
        self.assertEqual(len(active_bullets), 1)
        self.assertGreater(active_bullets[0]["vx"], 0.0)
        self.assertEqual(active_bullets[0]["vy"], 0.0)

    def test_collect_badge_and_dual_guns(self):
        self.game.badge_active = True
        self.game.badge_type = 0  # Gold Badge
        self.game.px = self.game.badge_x
        self.game.py = self.game.badge_y
        init_score = self.game.score

        self.game.update(0.05, 0)
        self.assertFalse(self.game.badge_active)
        self.assertTrue(self.game.has_dual_guns)
        self.assertEqual(self.game.score, init_score + 100)

        # Now shoot with dual guns
        for b in self.game.bullets:
            b["active"] = False
        self.game.fire_cooldown = 0.0
        self.game.update(0.05, KEY_A)
        active_bullets = [b for b in self.game.bullets if b["active"] and not b["is_enemy"]]
        self.assertEqual(len(active_bullets), 2)  # One horizontal, one angled up

    def test_rapid_fire_badge(self):
        self.game.badge_active = True
        self.game.badge_type = 1  # Silver Badge
        self.game.px = self.game.badge_x
        self.game.py = self.game.badge_y

        self.game.update(0.05, 0)
        self.assertTrue(self.game.has_rapid_fire)

    def test_slide_dodges_enemy_bullet(self):
        # Case 1: Hero is sliding, enemy bullet passes overhead safely
        self.game.is_sliding = True
        self.game.slide_timer = 0.3
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["is_enemy"] = True
        self.game.bullets[0]["x"] = self.game.px
        self.game.bullets[0]["y"] = self.game.py - 0.4
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_SALOON_BRAWL)

        # Case 2: Hero is standing, enemy bullet hits hero
        self.game.is_sliding = False
        self.game.bullets[0]["active"] = True
        self.game.bullets[0]["is_enemy"] = True
        self.game.bullets[0]["x"] = self.game.px
        self.game.bullets[0]["y"] = self.game.py - 0.4
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_HERO_HIT)

    def test_bull_stampede_hop_vs_trample(self):
        # Trigger stampede
        self.game.state = STATE_STAMPEDE
        self.game.bulls[0]["active"] = True
        self.game.bulls[0]["x"] = 5.0
        self.game.bulls[0]["y"] = 13.0

        # Subcase A: Hero jumps onto bull back
        self.game.px = 5.0
        self.game.py = 11.5
        self.game.vy = 1.0
        init_score = self.game.score

        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAMPEDE)
        self.assertLess(self.game.vy, 0.0)  # Bounced up off bull back
        self.assertEqual(self.game.score, init_score + 30)

        # Subcase B: Hero caught grounded by bull
        self.game.py = 13.0
        self.game.vy = 0.0
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_HERO_HIT)

    def test_stage_clear_and_render(self):
        self.game.reset()
        self.game.bandits_defeated = 6
        self.game.update(0.05, 0)
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreaterEqual(self.game.score, 2000)

        # Test render framebuffer
        fb = bytearray(16 * 16 * 3)
        self.game.render(fb)
        self.assertEqual(len(fb), 768)
        self.assertTrue(any(b > 0 for b in fb))

        status = self.game.get_status()
        self.assertEqual(status["game_id"], 90)


if __name__ == "__main__":
    unittest.main()
