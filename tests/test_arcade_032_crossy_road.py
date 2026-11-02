import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_032_crossy_road import (
    Game032CrossyRoad,
    LANE_GRASS,
    LANE_ROAD,
    LANE_RIVER,
    LANE_RAIL,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
)
from arcade.base_cartridge import (
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame032CrossyRoad(unittest.TestCase):
    def setUp(self):
        self.game = Game032CrossyRoad()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(32)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "疯狂过马路")
        self.assertEqual(instance.english_name, "Crossy Road 2014")
        self.assertEqual(instance.control_type, CTRL_DPAD_4WAY)
        self.assertEqual(instance.release_year, 2014)

    def test_initial_world_and_safe_grass(self):
        """测试初始世界安全草地与坐标基准"""
        self.assertEqual(self.game.player_world_y, 0)
        self.assertEqual(self.game.camera_world_y, 0)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.max_distance, 0)

        # 前三行应为安全草地
        for y in range(3):
            self.assertEqual(self.game.lanes[y]["type"], LANE_GRASS)

    def test_hop_forward_scoring_and_idle_reset(self):
        """测试向前单步跳跃、距离累加得分与老鹰停留计时清零"""
        self.game.idle_timer = 2.0
        prev_world_y = self.game.player_world_y

        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.player_world_y, prev_world_y + 1)
        self.assertEqual(self.game.max_distance, 1)
        self.assertEqual(self.game.score, 10)
        # 扑杀倒计时被重置并在该帧流逝 0.05 秒
        self.assertAlmostEqual(self.game.idle_timer, 0.05, places=2)

    def test_camera_following_when_advancing(self):
        """测试玩家向前推进时镜头自动向上跟随推移"""
        # 将前 20 排设为草地安全区以测试纯镜头运动
        for l in self.game.lanes:
            l["type"] = LANE_GRASS

        # 连续向前跳跃 12 步 (每步 0.01 秒，按键升起再按下)
        for _ in range(12):
            self.game.update(0.01, KEY_UP, 0)
            self.game.update(0.01, 0, KEY_UP)

        self.assertEqual(self.game.player_world_y, 12)
        self.assertGreater(self.game.camera_world_y, 0)
        # 屏幕相对坐标应在视口内部
        screen_y = 15 - (self.game.player_world_y - self.game.camera_world_y)
        self.assertGreaterEqual(screen_y, 0)
        self.assertLess(screen_y, 16)

    def test_eagle_strike_timeout(self):
        """测试原地发呆超过 3.5 秒触发天降老鹰扑杀死亡"""
        self.game.idle_timer = 3.4
        self.assertFalse(self.game.eagle_striking)

        # 推进 0.2 秒
        self.game.update(0.2, 0, 0)
        self.assertTrue(self.game.eagle_striking)

        # 老鹰高速俯冲抓走玩家
        for _ in range(20):
            if self.game.state == STATE_DEAD:
                break
            self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_DEAD)

    def test_road_car_collision_death(self):
        """测试公路上被汽车撞击阵亡"""
        # 定位在公路车道
        road_lane_idx = -1
        for i, l in enumerate(self.game.lanes):
            if l["type"] == LANE_ROAD:
                road_lane_idx = i
                break

        self.assertNotEqual(road_lane_idx, -1)
        target_world_y = self.game.lanes[road_lane_idx]["world_y"]

        self.game.player_world_y = target_world_y
        self.game.camera_world_y = target_world_y - 8
        self.game.player_x = 7.0

        # 在玩家同一位置放置汽车
        self.game.obstacles.append({
            "active": True,
            "lane_idx": road_lane_idx,
            "is_log": False,
            "length": 2.2,
            "x": 6.5,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_river_log_riding_and_drifting(self):
        """测试河流中跳上浮木安全存活并随波漂移"""
        river_lane_idx = -1
        for i, l in enumerate(self.game.lanes):
            if l["type"] == LANE_RIVER:
                river_lane_idx = i
                break

        self.assertNotEqual(river_lane_idx, -1)
        target_world_y = self.game.lanes[river_lane_idx]["world_y"]

        self.game.player_world_y = target_world_y
        self.game.camera_world_y = target_world_y - 8
        self.game.player_x = 7.0
        self.game.lanes[river_lane_idx]["speed"] = 3.0

        # 在脚下生成浮木
        self.game.obstacles.append({
            "active": True,
            "lane_idx": river_lane_idx,
            "is_log": True,
            "length": 4.0,
            "x": 5.0,
        })

        prev_x = self.game.player_x
        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_PLAYING) # 存活
        self.assertGreater(self.game.player_x, prev_x)   # 随波逐流

    def test_river_drowning_without_log(self):
        """测试河流中未踩中浮木直接溺水阵亡"""
        river_lane_idx = -1
        for i, l in enumerate(self.game.lanes):
            if l["type"] == LANE_RIVER:
                river_lane_idx = i
                break

        self.assertNotEqual(river_lane_idx, -1)
        target_world_y = self.game.lanes[river_lane_idx]["world_y"]

        self.game.player_world_y = target_world_y
        self.game.camera_world_y = target_world_y - 8
        self.game.player_x = 7.0
        self.game.obstacles.clear() # 清空所有浮木

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD) # 溺亡

    def test_train_warning_and_rail_collision(self):
        """测试铁路信号灯警报与高速列车撞击"""
        rail_lane_idx = -1
        for i, l in enumerate(self.game.lanes):
            if l["type"] == LANE_RAIL:
                rail_lane_idx = i
                break

        self.assertNotEqual(rail_lane_idx, -1)
        rail = self.game.lanes[rail_lane_idx]
        target_world_y = rail["world_y"]

        self.game.player_world_y = target_world_y
        self.game.camera_world_y = target_world_y - 8
        self.game.player_x = 7.0

        # 触发火车疾驰过境
        rail["train_passing"] = True
        rail["train_x"] = 6.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD) # 撞击

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区渲染合法性与像素规格"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 验证小鸡主角渲染 (RGB 白像素 [250, 250, 250])
        # 初始在 (7, 0 world_y -> screen_y 15)
        chicken_idx = (15 * 16 + 7) * 3
        self.assertEqual(fb[chicken_idx], 250)
        self.assertEqual(fb[chicken_idx + 1], 250)
        self.assertEqual(fb[chicken_idx + 2], 250)


if __name__ == "__main__":
    unittest.main()
