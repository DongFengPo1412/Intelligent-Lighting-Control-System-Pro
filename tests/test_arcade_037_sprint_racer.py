import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_037_sprint_racer import (
    Game037SprintRacer,
    STATE_START,
    STATE_RACING,
    STATE_VICTORY,
    STATE_TIMEOUT,
    PI,
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
from arcade.arcade_registry import ArcadeRegistry


class TestGame037SprintRacer(unittest.TestCase):
    def setUp(self):
        self.game = Game037SprintRacer()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(37)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "经典赛道漂移")
        self.assertEqual(instance.english_name, "Sprint 2 1976")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1976)

    def test_track_map_and_boundaries(self):
        """测试环形沥青赛道与内外护栏防撞隔离区"""
        # 外墙
        self.assertFalse(self.game.is_on_track(0.0, 5.0))
        self.assertFalse(self.game.is_on_track(15.0, 5.0))
        # 内圈草地隔离岛 (5..10, 5..10)
        self.assertFalse(self.game.is_on_track(7.0, 7.0))
        # 环形沥青主赛道 (x=8, y=13 为底线直道)
        self.assertTrue(self.game.is_on_track(8.0, 13.0))

    def test_steering_wheel_continuous_rotation(self):
        """测试左右转向按键修改赛车连续航向角 (Heading Angle)"""
        self.game.player["angle"] = PI / 2.0
        initial_angle = self.game.player["angle"]

        # 向右转弯
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player["angle"], initial_angle)

        # 向左转弯转回
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertAlmostEqual(self.game.player["angle"], initial_angle, places=2)

    def test_throttle_acceleration_and_braking(self):
        """测试按键 A 油门加速与按键 B 刹车制动"""
        self.assertEqual(self.game.player["speed"], 0.0)

        # 踩油门
        self.game.update(0.1, KEY_A, 0)
        self.assertGreater(self.game.player["speed"], 0.0)

        # 踩刹车
        prev_speed = self.game.player["speed"]
        self.game.update(0.1, KEY_B, 0)
        self.assertLess(self.game.player["speed"], prev_speed)

    def test_barrier_collision_elastic_bounce(self):
        """测试撞向内外护栏阻挡并触发弹性减速回弹"""
        # 将赛车贴近外墙 (x=0.45) 朝向外墙冲刺 (angle=PI 向左)
        self.game.player["x"] = 0.45
        self.game.player["y"] = 13.0
        self.game.player["angle"] = PI
        self.game.player["speed"] = 5.0

        self.game.update(0.05, 0, 0)
        # 撞墙后产生负向反弹速度
        self.assertLess(self.game.player["speed"], 0.0)

    def test_oil_slick_spinout_mechanics(self):
        """测试轧过地面油污导致 360 度疯狂打滑失控 (Spinout)"""
        # 放置在 1 号油污位置 (12.5, 12.5)
        self.game.player["x"] = 12.5
        self.game.player["y"] = 12.5
        self.game.player["speed"] = 4.0
        self.game.player["spin_timer"] = 0.0

        self.game.update(0.05, 0, 0)
        # 应触发打滑计时
        self.assertGreater(self.game.player["spin_timer"], 0.5)

    def test_checkpoint_sequence_and_lap_counting(self):
        """测试按序通过检查点完成完整一圈计圈与得分"""
        p = self.game.player
        self.assertEqual(p["laps"], 0)
        self.assertEqual(p["next_checkpoint"], 1)

        # 抵达 CP 1 (Turn 1: x>=11, y in 6..10)
        p["x"] = 12.0
        p["y"] = 8.0
        self.game.check_checkpoints(p, is_player=True)
        self.assertEqual(p["next_checkpoint"], 2)

        # 抵达 CP 2 (Back Straight: y<=4, x in 6..10)
        p["x"] = 8.0
        p["y"] = 3.0
        self.game.check_checkpoints(p, is_player=True)
        self.assertEqual(p["next_checkpoint"], 3)

        # 抵达 CP 3 (Turn 2: x<=4, y in 6..10)
        p["x"] = 3.0
        p["y"] = 8.0
        self.game.check_checkpoints(p, is_player=True)
        self.assertEqual(p["next_checkpoint"], 0)

        # 抵达 CP 0 (Start/Finish: y>=11, x in 7..10)
        p["x"] = 8.0
        p["y"] = 13.0
        self.game.check_checkpoints(p, is_player=True)
        self.assertEqual(p["laps"], 1) # 完成 1 圈
        self.assertEqual(self.game.score, 500)

    def test_three_laps_championship_victory(self):
        """测试完成 3 圈达成巡回锦标赛冠军胜利并结算时间奖励"""
        self.game.player["laps"] = 2
        self.game.player["next_checkpoint"] = 0
        self.game.player["x"] = 8.0
        self.game.player["y"] = 13.0

        self.game.check_checkpoints(self.game.player, is_player=True)
        self.assertEqual(self.game.player["laps"], 3)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1500)

    def test_race_timeout(self):
        """测试比赛超时未能完赛判负"""
        self.game.race_time = 59.9
        self.game.update(0.2, 0, 0)
        self.assertEqual(self.game.state, STATE_TIMEOUT)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区赛道沥青、内圈草地与黑白终点线着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查中心内圈草地 (x=7, y=7 绿色 [39, 174, 96])
        grass_idx = (7 * 16 + 7) * 3
        self.assertEqual(fb[grass_idx], 39)
        self.assertEqual(fb[grass_idx + 1], 174)
        self.assertEqual(fb[grass_idx + 2], 96)

        # 检查黑白终点线 (x=8, y=12 白色 [255, 255, 255])
        finish_idx = (12 * 16 + 8) * 3
        self.assertEqual(fb[finish_idx], 255)
        self.assertEqual(fb[finish_idx + 1], 255)
        self.assertEqual(fb[finish_idx + 2], 255)


if __name__ == "__main__":
    unittest.main()
