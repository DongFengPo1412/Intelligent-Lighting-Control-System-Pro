import unittest
from arcade.game_118_yiearkungfu import (
    Game118YieArKungFu,
    STATE_FIGHTING,
    STATE_KO_VICTORY,
    STATE_PLAYER_DEFEATED,
    STATE_GAME_OVER,
    STANCE_IDLE,
    STANCE_MID_PUNCH,
    STANCE_MID_KICK,
    STANCE_HIGH_JUMP_KICK,
    STANCE_LOW_SWEEP,
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


class TestGame118YieArKungFu(unittest.TestCase):
    def setUp(self):
        self.game = Game118YieArKungFu()

    def test_metadata(self):
        self.assertEqual(self.game.game_id, 118)
        self.assertEqual(self.game.name, "功夫小子")
        self.assertEqual(self.game.english_name, "Yie Ar Kung-Fu")
        self.assertEqual(self.game.release_year, 1985)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)
        self.assertIn("八向摇杆", self.game.core_mechanic)

    def test_initial_state(self):
        self.assertEqual(self.game.state, STATE_FIGHTING)
        self.assertEqual(self.game.round, 1)
        self.assertEqual(self.game.player["hp"], 100)
        self.assertEqual(self.game.opponent["hp"], 100)
        self.assertEqual(self.game.player["x"], 4.0)
        self.assertEqual(self.game.opponent["x"], 12.0)
        self.assertEqual(self.game.player["stance"], STANCE_IDLE)

    def test_player_lateral_movement_and_bounds(self):
        # Move Left
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertLess(self.game.player["x"], 4.0)

        # Move far right past maximum bounds
        for _ in range(50):
            self.game.update(0.05, KEY_RIGHT, 0)
        self.assertLessEqual(self.game.player["x"], 14.5)

    def test_player_mid_punch_attack(self):
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.player["stance"], STANCE_MID_PUNCH)

    def test_player_mid_front_kick(self):
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.player["stance"], STANCE_MID_KICK)

    def test_player_flying_jump_kick(self):
        self.game.update(0.05, KEY_UP | KEY_B, 0)
        self.assertEqual(self.game.player["stance"], STANCE_HIGH_JUMP_KICK)
        self.assertLess(self.game.player["vy"], -2.0)

    def test_player_low_sweep_duck(self):
        self.game.update(0.05, KEY_DOWN | KEY_B, 0)
        self.assertEqual(self.game.player["stance"], STANCE_LOW_SWEEP)

    def test_shuriken_parry_deflection(self):
        # Active projectile flying towards player
        self.game.projectiles[0]["active"] = True
        self.game.projectiles[0]["x"] = 5.0
        self.game.projectiles[0]["y"] = 12.0
        self.game.projectiles[0]["vx"] = -7.5

        # Player executes punch
        self.game.player["x"] = 4.0
        self.game.player["facing"] = 1
        self.game.execute_player_attack(STANCE_MID_PUNCH)

        init_score = self.game.score
        self.game.update(0.01, 0, 0)

        # Projectile deflected
        self.assertFalse(self.game.projectiles[0]["active"])
        self.assertEqual(self.game.score, init_score + 100)

    def test_player_strike_damages_opponent(self):
        # Position player close to opponent
        self.game.player["x"] = 10.2
        self.game.player["facing"] = 1
        self.game.opponent["x"] = 12.0
        self.game.opponent["hp"] = 100

        # Execute Front Kick (damage = 15)
        self.game.execute_player_attack(STANCE_MID_KICK)

        init_score = self.game.score
        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.opponent["hp"], 85)
        self.assertGreater(self.game.opponent["hurt_timer"], 0.2)
        self.assertEqual(self.game.score, init_score + 150)

    def test_ko_victory_and_round_advance(self):
        # Opponent with low HP
        self.game.player["x"] = 10.2
        self.game.player["facing"] = 1
        self.game.opponent["x"] = 12.0
        self.game.opponent["hp"] = 10

        # High Jump Kick (damage = 25 > 10)
        self.game.execute_player_attack(STANCE_HIGH_JUMP_KICK)

        self.game.update(0.01, 0, 0)

        self.assertEqual(self.game.opponent["hp"], 0)
        self.assertEqual(self.game.state, STATE_KO_VICTORY)


if __name__ == "__main__":
    unittest.main()
