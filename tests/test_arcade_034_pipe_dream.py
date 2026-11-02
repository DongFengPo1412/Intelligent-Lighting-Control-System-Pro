import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_034_pipe_dream import (
    Game034PipeDream,
    PIPE_EMPTY,
    PIPE_HORIZ,
    PIPE_VERT,
    PIPE_CORNER_UR,
    PIPE_CORNER_RD,
    PIPE_CORNER_DL,
    PIPE_CORNER_LU,
    PIPE_CROSS,
    PIPE_START,
    PIPE_END,
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


class TestGame034PipeDream(unittest.TestCase):
    def setUp(self):
        self.game = Game034PipeDream()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(34)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "疯狂水管工")
        self.assertEqual(instance.english_name, "Pipe Dream 1989")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1989)

    def test_board_initialization_and_queue(self):
        """测试棋盘起点龙头、终点水槽与管道队列初始化"""
        self.assertEqual(self.game.grid[1][1]["pipe"], PIPE_START)
        self.assertTrue(self.game.grid[1][1]["filled"])
        self.assertEqual(self.game.grid[6][6]["pipe"], PIPE_END)
        self.assertFalse(self.game.grid[6][6]["filled"])
        self.assertEqual(len(self.game.pipe_queue), 4)

    def test_cursor_navigation_and_clamping(self):
        """测试 8x8 网格光标移动与边界限制"""
        self.game.cursor_x = 0
        self.game.cursor_y = 0

        # 尝试越界向左和向上
        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.cursor_x, 0)
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.cursor_y, 0)

        # 向右移动
        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.cursor_x, 1)

    def test_pipe_placement_and_queue_advancement(self):
        """测试放置管道、队列推进与不可覆盖已充水管"""
        next_pipe = self.game.pipe_queue[0]
        self.game.cursor_x = 2
        self.game.cursor_y = 1 # 正好在起点的右侧

        # 按键 A 放置管道
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.grid[1][2]["pipe"], next_pipe)
        self.assertEqual(len(self.game.pipe_queue), 4) # 队列自动补充

        # 尝试覆盖已注水起点龙头
        self.game.cursor_x = 1
        self.game.cursor_y = 1
        self.game.update(0.05, 0, KEY_A)
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.grid[1][1]["pipe"], PIPE_START) # 起点未被覆盖

    def test_fluid_countdown_and_fast_forward(self):
        """测试原油流动启动倒计时与按键 B 极速泵油"""
        self.game.flow_start_countdown = 5.0
        self.assertFalse(self.game.flow_started)

        # 按键 B 瞬间开始泵油并在该帧直接启动流动
        self.game.update(0.05, KEY_B, 0)
        self.assertEqual(self.game.flow_start_countdown, 0.0)
        self.assertTrue(self.game.flow_started)

    def test_straight_pipe_flow_and_scoring(self):
        """测试横向直管导流注水与累积分数"""
        self.game.grid[1][2]["pipe"] = PIPE_HORIZ # 正好接在 (1,1) 右侧
        self.game.flow_started = True
        self.game.flow_step_timer = 0.99
        self.game.flow_step_interval = 1.0

        self.game.update(0.05, 0, 0) # 触发前进一步
        self.assertEqual(self.game.flow_x, 2)
        self.assertEqual(self.game.flow_y, 1)
        self.assertTrue(self.game.grid[1][2]["filled"])
        self.assertEqual(self.game.score, 100)

    def test_pipe_spill_triggers_game_over(self):
        """测试管道未连通原油泄漏导致游戏失败"""
        self.game.grid[1][2]["pipe"] = PIPE_EMPTY # 空地导致泄漏
        self.game.flow_started = True
        self.game.flow_step_timer = 0.99

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_cross_double_bridge_bonus(self):
        """测试十字交叉管双向贯通与双十字大奖"""
        self.game.grid[2][2]["pipe"] = PIPE_CROSS

        # 模拟第一次横向穿过 (由左向右 enter_dir=1)
        can_c, exit_dir = self.game.can_connect(PIPE_CROSS, 1)
        self.assertTrue(can_c)
        self.assertEqual(exit_dir, 1)

        # 模拟第二次纵向穿过 (由上向下 enter_dir=2)
        can_c2, exit_dir2 = self.game.can_connect(PIPE_CROSS, 2)
        self.assertTrue(can_c2)
        self.assertEqual(exit_dir2, 2)

    def test_drain_victory_condition(self):
        """测试连接水管达到要求并成功流入排水槽通关胜利"""
        self.game.pipes_filled = 8
        self.game.required_pipes = 8
        self.game.flow_x = 5
        self.game.flow_y = 6
        self.game.flow_dir = 1 # 向右流向 (6, 6) 的 PIPE_END

        self.game.flow_started = True
        self.game.flow_step_timer = 0.99
        self.game.update(0.05, 0, 0)

        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区管道渲染规格"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查起点龙头处的像素着色 (绿色 [0, 255, 128])
        # (1, 1) 对应屏幕像素 (2, 2)
        idx = (2 * 16 + 2) * 3
        self.assertEqual(fb[idx], 0)
        self.assertEqual(fb[idx + 1], 255)
        self.assertEqual(fb[idx + 2], 128)


if __name__ == "__main__":
    unittest.main()
