import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_038_ice_climber import (
    Game038IceClimber,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
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


class TestGame038IceClimber(unittest.TestCase):
    def setUp(self):
        self.game = Game038IceClimber()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(38)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "敲冰块")
        self.assertEqual(instance.english_name, "Ice Climber 1985")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1985)

    def test_mountain_floors_initialization(self):
        """测试多层雪山冰层、底板与峰顶平台初始化"""
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.player_y, 13.0)
        self.assertTrue(self.game.is_grounded)

        # 检查 1、2、3 层冰砖存在
        self.assertEqual(self.game.ice_grid[11][7], 2)
        self.assertEqual(self.game.ice_grid[8][7], 2)
        self.assertEqual(self.game.ice_grid[5][7], 2)

        # 峰顶平台 (y=2, x=6..9)
        self.assertEqual(self.game.ice_grid[2][7], 1)

    def test_horizontal_running_and_screen_wrap(self):
        """测试水平奔跑与横向经典环形穿屏 (Screen Wrap)"""
        self.game.player_x = 0.2
        # 向左跑穿出左边界
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertGreater(self.game.player_x, 14.0) # 穿屏到右侧

    def test_upward_head_butt_ice_shatter(self):
        """测试向上跳跃用木槌击碎头顶冰块并开出通道"""
        self.game.player_x = 7.0
        self.game.player_y = 12.0 # 正好在 Floor 1 (y=11) 下方
        self.game.is_grounded = True
        self.assertEqual(self.game.ice_grid[11][7], 2)

        # 按键 A 垂直起跳
        self.game.update(0.05, KEY_A, 0)
        self.assertFalse(self.game.is_grounded)

        # 步进撞碎冰块
        for _ in range(5):
            self.game.update(0.05, 0, 0)

        # (7, 11) 处冰块应被粉碎开洞
        self.assertEqual(self.game.ice_grid[11][7], 0)
        self.assertEqual(self.game.score, 50)

    def test_jump_through_hole_and_land_on_upper_floor(self):
        """测试从凿开的冰洞跃上并平稳落在上层冰面上"""
        # 预先在 Floor 1 (y=11) 凿开洞口 (7, 11)
        self.game.ice_grid[11][7] = 0
        self.game.player_x = 7.0
        self.game.player_y = 12.0
        self.game.is_grounded = True

        # 起跳穿洞
        self.game.update(0.05, KEY_A, 0)

        # 跃过 y=11 并落在 y=10 的冰层上方
        for _ in range(25):
            self.game.update(0.05, 0, 0)

        # 稍微偏向右侧落在未破损的 (8, 11) 上
        self.game.player_x = 8.0
        self.game.player_y = 10.0
        self.game.update(0.05, 0, 0)

        self.assertTrue(self.game.is_grounded)
        self.assertEqual(self.game.player_y, 10.0)

    def test_hole_fall_when_floor_broken(self):
        """测试脚下冰块破损失去支撑向下坠落"""
        self.game.player_x = 7.0
        self.game.player_y = 10.0 # 站于 y=11 冰层上
        self.game.is_grounded = True

        # 砸碎脚下的 (7, 11)
        self.game.ice_grid[11][7] = 0

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.is_grounded) # 跌落

    def test_topi_seal_patches_ice_hole(self):
        """测试海豹 Topi 巡逻发现破洞自动推冰修补"""
        # 在 Floor 1 (y=11) 的 x=5 处开洞
        self.game.ice_grid[11][5] = 0
        topi = self.game.topis[0]
        topi["floor_y"] = 11
        topi["x"] = 4.8
        topi["vx"] = 2.0

        # 海豹走过该洞
        self.game.update(0.15, 0, 0)

        # 洞口被海豹重新补上冰块 (恢复为 2)
        self.assertEqual(self.game.ice_grid[11][5], 2)

    def test_hammer_swing_knocks_out_topi(self):
        """测试按键 B 挥舞木槌击飞巡逻海豹得分"""
        topi = self.game.topis[0]
        topi["x"] = 7.5
        topi["floor_y"] = 14 # 位于底楼
        self.game.player_x = 7.0
        self.game.player_y = 13.0
        self.game.is_grounded = True

        # 按键 B 挥槌
        self.game.update(0.05, KEY_B, 0)

        self.assertFalse(topi["active"]) # Topi 被击飞
        self.assertEqual(self.game.score, 200)

    def test_summit_condor_grapple_victory(self):
        """测试峰顶起跳抓取飞天神鹰达成雪山登顶通关胜利"""
        self.game.player_x = 7.0
        self.game.player_y = 2.0
        self.game.condor["x"] = 7.0
        self.game.condor["y"] = 1.0

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreaterEqual(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区极地天际、冰砖与神鹰着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查可破坏青色冰砖着色 (x=7, y=11 亮青色 [0, 210, 255])
        ice_idx = (11 * 16 + 7) * 3
        self.assertEqual(fb[ice_idx], 0)
        self.assertEqual(fb[ice_idx + 1], 210)
        self.assertEqual(fb[ice_idx + 2], 255)


if __name__ == "__main__":
    unittest.main()
