# -*- coding: utf-8 -*-
import unittest
from arcade.game_173_gorf import (
    Game173Gorf,
    STATE_PLAYING,
    STATE_PHASE_TRANSITION,
    STATE_FLAGSHIP_EXPLODING,
    STATE_PLAYER_DIED,
    STATE_GAME_OVER,
    PHASE_LASER_ATTACK,
    PHASE_SPACE_WARP,
    PHASE_FLAGSHIP_CORE,
)
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
)

class TestArcade173Gorf(unittest.TestCase):
    def setUp(self):
        self.game = Game173Gorf()

    def test_01_initialization_and_metadata(self):
        self.assertEqual(self.game.game_id, 173)
        self.assertEqual(self.game.name, "高尔夫太空战")
        self.assertEqual(self.game.english_name, "Gorf")
        self.assertEqual(self.game.release_year, 1981)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.phase, PHASE_LASER_ATTACK)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(len(self.game.escorts), 4)

    def test_02_player_2d_movement_and_clamping(self):
        # 2D movement in lower grid
        self.game.px = 7.5
        self.game.py = 13.0
        # Move Up and Left
        self.game.update(0.1, keys_down=(KEY_UP | KEY_LEFT))
        self.assertLess(self.game.px, 7.5)
        self.assertLess(self.game.py, 13.0)

        # Upper vertical clamp is 9.0
        for _ in range(30):
            self.game.update(0.1, keys_down=KEY_UP)
        self.assertEqual(self.game.py, 9.0)

    def test_03_fire_quark_laser(self):
        self.assertFalse(self.game.laser_active)
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertTrue(self.game.laser_active)
        self.assertEqual(self.game.lx, self.game.px)

    def test_04_laser_attack_destroy_escort(self):
        target = self.game.escorts[0]
        self.assertTrue(target["alive"])
        # Fire laser directly below target escort
        self.game.laser_active = True
        self.game.lx = target["x"]
        self.game.ly = target["y"] + 0.5
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(target["alive"])
        self.assertFalse(self.game.laser_active)
        self.assertEqual(self.game.score, initial_score + 200)

    def test_05_laser_attack_continuous_beam_kills_player(self):
        # Escort fires continuous beam
        esc = self.game.escorts[0]
        esc["x"] = 7.5
        esc["y"] = 2.0
        esc["firing_beam"] = 0.3
        self.game.px = 7.5
        self.game.py = 12.0
        initial_lives = self.game.lives

        self.game.update(0.01)
        self.assertEqual(self.game.lives, initial_lives - 1)
        self.assertEqual(self.game.state, STATE_PLAYER_DIED)

    def test_06_space_warp_destroy_spiraling_ship(self):
        self.game.phase = PHASE_SPACE_WARP
        self.game._init_phase()
        self.assertEqual(self.game.phase, PHASE_SPACE_WARP)

        s = self.game.warp_ships[0]
        # Position laser on ship
        cx, cy = 7.5, 6.0
        import math
        sx = cx + math.cos(s["angle"]) * s["radius"]
        sy = cy + math.sin(s["angle"]) * s["radius"]

        self.game.laser_active = True
        self.game.lx = sx
        self.game.ly = sy
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertFalse(s["alive"])
        self.assertEqual(self.game.score, initial_score + 150)

    def test_07_space_warp_clear_transition_to_flagship(self):
        self.game.phase = PHASE_SPACE_WARP
        self.game._init_phase()
        # Kill all warp ships except one
        for s in self.game.warp_ships[1:]:
            s["alive"] = False

        # Destroy final ship
        last = self.game.warp_ships[0]
        import math
        self.game.laser_active = True
        self.game.lx = 7.5 + math.cos(last["angle"]) * last["radius"]
        self.game.ly = 6.0 + math.sin(last["angle"]) * last["radius"]

        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_PHASE_TRANSITION)

        # Let transition timer elapse
        self.game.update(1.1)
        self.assertEqual(self.game.phase, PHASE_FLAGSHIP_CORE)

    def test_08_flagship_force_shield_ablation(self):
        self.game.phase = PHASE_FLAGSHIP_CORE
        self.game._init_phase()
        self.assertEqual(self.game.shield_bits, 0xFF) # 8 blocks intact

        # Hit column 4 (shield column 0)
        self.game.laser_active = True
        self.game.lx = 4.0
        self.game.ly = 5.0
        initial_score = self.game.score

        self.game.update(0.01)
        # Bit 0 should be blown away
        self.assertEqual(self.game.shield_bits & 0x01, 0)
        self.assertFalse(self.game.laser_active)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_09_flagship_reactor_core_snipe_and_detonation(self):
        self.game.phase = PHASE_FLAGSHIP_CORE
        self.game._init_phase()
        # Blow hole in shield at column 7.5
        self.game.shield_bits &= ~0x0C # clear center shield bits
        self.game.flagship_x = 7.5

        # Thread laser directly into reactor core (y=3.0)
        self.game.laser_active = True
        self.game.lx = 7.5
        self.game.ly = 3.0
        initial_score = self.game.score

        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_FLAGSHIP_EXPLODING)
        self.assertGreaterEqual(self.game.score, initial_score + 2500)

    def test_10_render_and_game_over_restart(self):
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # Trigger Game Over
        self.game.lives = 0
        self.game.state = STATE_PLAYER_DIED
        self.game.state_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(self.game.state, STATE_GAME_OVER)

        # Press A to restart
        self.game.update(0.01, keys_pressed=KEY_A)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.lives, 3)

if __name__ == "__main__":
    unittest.main()

