"""
Unit tests for Game #162: 翻滚战机1942 (1942 - 1984 Capcom / Yoshiki Okamoto)
Cartridge verification for 16x16 WS2812B LED Matrix.
"""

import unittest
from arcade.game_162_1942 import (
    Game162Roll1942,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_B,
    STATE_PLAYING, STATE_STAGE_CLEAR, STATE_PLAYER_EXPLODING, STATE_GAME_OVER
)

class TestArcade162Roll1942(unittest.TestCase):
    def setUp(self):
        self.game = Game162Roll1942()

    def test_01_init_state_and_p38(self):
        """Verify initial state, lives=3, stage=1, loops=3, no wingmen, position at (8, 13)."""
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.stage, 1)
        self.assertEqual(self.game.loops_left, 3)
        self.assertFalse(self.game.is_looping)
        self.assertFalse(self.game.has_wingmen)
        self.assertAlmostEqual(self.game.px, 8.0)
        self.assertAlmostEqual(self.game.py, 13.0)

    def test_02_loop_the_loop_maneuver(self):
        """Trigger KEY_B, loops decrease to 2, is_looping is True, awards score."""
        old_score = self.game.score
        self.game.update(0.02, keys_down=0, keys_pressed=KEY_B)
        self.assertEqual(self.game.loops_left, 2)
        self.assertTrue(self.game.is_looping)
        self.assertGreater(self.game.score, old_score)

        # Loop ends after duration
        self.game.update(0.9)
        self.assertFalse(self.game.is_looping)

    def test_03_loop_invulnerability(self):
        """During loop-the-loop, colliding with enemy does NOT cost life."""
        self.game.update(0.02, keys_down=0, keys_pressed=KEY_B)
        self.assertTrue(self.game.is_looping)

        # Collide with enemy plane
        self.game.enemies.append({
            "id": 1, "x": self.game.px, "y": self.game.py,
            "vx": 0.0, "vy": 0.0, "hp": 1, "is_red": False, "is_boss": False, "active": True
        })
        self.game.update(0.05)

        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_04_cannon_shooting_and_cooldown(self):
        """Press KEY_A to fire single cannon shot upward with cooldown."""
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.player_bullets), 1)
        b = self.game.player_bullets[0]
        self.assertAlmostEqual(b["x"], 8.0)
        self.assertLess(b["vy"], 0.0)

        # Immediate fire blocked by cooldown
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.player_bullets), 1)

    def test_05_red_formation_all_killed_spawns_pow(self):
        """Destroying all 4 red squadron fighters spawns a POW upgrade."""
        self.game.spawn_red_formation()
        self.assertEqual(len(self.game.enemies), 4)

        # Destroy each red plane directly with colliding bullets
        for e in list(self.game.enemies):
            bullet = {"x": e["x"], "y": e["y"] + 0.2, "vy": -5.0}
            self.game.player_bullets.append(bullet)
            self.game.update(0.02)

        self.assertEqual(len(self.game.pow_items), 1)
        self.assertGreater(self.game.score, 1000)

    def test_06_pow_pickup_grants_wingmen_and_loop(self):
        """Touching a floating POW item equips escort wingmen and restores loop count."""
        self.game.loops_left = 1
        self.game.pow_items.append({"x": self.game.px, "y": self.game.py, "vy": 1.5})
        self.game.update(0.02)

        self.assertTrue(self.game.has_wingmen)
        self.assertEqual(self.game.loops_left, 2)
        self.assertEqual(len(self.game.pow_items), 0)

    def test_07_wingmen_triple_cannon_fire(self):
        """With wingmen equipped, pressing KEY_A fires 3 parallel bullets."""
        self.game.has_wingmen = True
        self.game.update(0.01, keys_down=0, keys_pressed=KEY_A)
        self.assertEqual(len(self.game.player_bullets), 3)

    def test_08_wingmen_absorb_damage(self):
        """When hit by enemy bullet, wingmen are sacrificed and player life is saved."""
        self.game.has_wingmen = True
        self.game.enemy_bullets.append({"x": self.game.px, "y": self.game.py, "vy": 5.0})
        self.game.update(0.02)

        self.assertFalse(self.game.has_wingmen)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_09_boss_bomber_ayako_defeat_stage_clear(self):
        """Defeating heavy boss bomber Ayako triggers stage clear."""
        self.game.spawn_boss()
        boss = self.game.enemies[0]
        self.assertTrue(boss["is_boss"])

        # Deal enough damage to kill boss
        boss["hp"] = 1
        self.game.player_bullets.append({"x": boss["x"], "y": boss["y"], "vy": -14.0})
        self.game.update(0.02)

        self.assertFalse(boss["active"])
        self.assertEqual(self.game.state, STATE_STAGE_CLEAR)
        self.assertGreater(self.game.score, 3000)

    def test_10_game_over_and_rendering(self):
        """Player death without wingmen costs life; 0 lives triggers game over; valid render."""
        self.game.lives = 1
        self.game.has_wingmen = False
        self.game.enemy_bullets.append({"x": self.game.px, "y": self.game.py, "vy": 5.0})
        self.game.update(0.02)

        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.state, STATE_PLAYER_EXPLODING)

        # Wait for explosion animation
        self.game.update(1.1)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Test frame rendering (768-byte bytearray)
        frame = self.game.render()
        self.assertEqual(len(frame), 768)
        self.assertIsInstance(frame, bytearray)

if __name__ == "__main__":
    unittest.main()
