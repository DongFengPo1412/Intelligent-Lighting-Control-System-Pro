import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_035_othello import (
    Game035Othello,
    PIECE_EMPTY,
    PIECE_BLACK,
    PIECE_WHITE,
    STATE_PLAYER_TURN,
    STATE_AI_TURN,
    STATE_GAMEOVER,
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


class TestGame035Othello(unittest.TestCase):
    def setUp(self):
        self.game = Game035Othello()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(35)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "极简黑白棋")
        self.assertEqual(instance.english_name, "Othello 1980")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1980)

    def test_initial_board_and_piece_counts(self):
        """测试经典开局 4 颗中心棋子与黑白各 2 计数"""
        self.assertEqual(self.game.board[3][3], PIECE_WHITE)
        self.assertEqual(self.game.board[3][4], PIECE_BLACK)
        self.assertEqual(self.game.board[4][3], PIECE_BLACK)
        self.assertEqual(self.game.board[4][4], PIECE_WHITE)

        self.assertEqual(self.game.black_count, 2)
        self.assertEqual(self.game.white_count, 2)
        self.assertEqual(self.game.state, STATE_PLAYER_TURN)

    def test_cursor_navigation_and_clamping(self):
        """测试 8x8 棋盘光标移动与边界限制"""
        self.game.cursor_x = 0
        self.game.cursor_y = 0

        self.game.update(0.05, KEY_LEFT, 0)
        self.assertEqual(self.game.cursor_x, 0)
        self.game.update(0.05, KEY_UP, 0)
        self.assertEqual(self.game.cursor_y, 0)

        self.game.update(0.05, KEY_RIGHT, 0)
        self.assertEqual(self.game.cursor_x, 1)

    def test_invalid_move_rejection(self):
        """测试非法落子（无法形成夹吃）被系统拒绝"""
        # (0, 0) 角落此时无法夹吃任何棋子
        self.assertFalse(self.game.is_valid_move(0, 0, PIECE_BLACK))
        self.game.cursor_x = 0
        self.game.cursor_y = 0

        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.board[0][0], PIECE_EMPTY) # 未落子
        self.assertEqual(self.game.state, STATE_PLAYER_TURN) # 仍为玩家回合

    def test_legal_move_and_disc_flipping(self):
        """测试合法落子、翻转被夹住的白棋与棋子计数变化"""
        # (2, 3) 垂直方向夹住 (3, 3) 的白棋，与 (4, 3) 的黑棋连通
        self.assertTrue(self.game.is_valid_move(2, 3, PIECE_BLACK))

        self.game.cursor_x = 2
        self.game.cursor_y = 3
        self.game.update(0.05, KEY_A, 0)

        self.assertEqual(self.game.board[3][2], PIECE_BLACK) # 落子成功 (注意：x=2, y=3)
        # 被夹住的棋子应翻转为黑棋
        # 在 (3, 3) 的白棋被水平翻转 (x=2, y=3) 与 (x=4, y=3) 夹吃 (3,3)
        self.assertEqual(self.game.board[3][3], PIECE_BLACK)
        self.assertEqual(self.game.black_count, 4)
        self.assertEqual(self.game.white_count, 1)

    def test_ai_turn_execution_and_heuristics(self):
        """测试黑棋落子后自动进入 AI 回合并由启发式权值完成落子"""
        self.game.cursor_x = 2
        self.game.cursor_y = 3
        self.game.update(0.05, KEY_A, 0) # 玩家落子

        self.assertEqual(self.game.state, STATE_AI_TURN)

        # AI 思考 0.5 秒
        self.game.update(0.6, 0, 0)

        # AI 必定完成了有效落子并切回玩家回合
        self.assertEqual(self.game.state, STATE_PLAYER_TURN)
        self.assertGreater(self.game.white_count, 1)

    def test_multi_directional_flipping(self):
        """测试单次落子触发横向、纵向与斜向多方向同时翻转"""
        # 手动构造一个三向夹吃格局
        self.game.board = [[PIECE_EMPTY for _ in range(8)] for _ in range(8)]
        # 在 (3, 3) 落黑子
        # 横向右侧 (4, 3)=白, (5, 3)=黑
        self.game.board[3][4] = PIECE_WHITE
        self.game.board[3][5] = PIECE_BLACK
        # 纵向下侧 (3, 4)=白, (3, 5)=黑
        self.game.board[4][3] = PIECE_WHITE
        self.game.board[5][3] = PIECE_BLACK

        self.assertTrue(self.game.is_valid_move(3, 3, PIECE_BLACK))
        self.game.place_move(3, 3, PIECE_BLACK)

        self.assertEqual(self.game.board[3][3], PIECE_BLACK)
        self.assertEqual(self.game.board[3][4], PIECE_BLACK) # 横向翻转
        self.assertEqual(self.game.board[4][3], PIECE_BLACK) # 纵向翻转

    def test_game_over_when_no_moves_remain(self):
        """测试全局无子可落时游戏结束并决出胜负"""
        # 构造全黑棋盘
        for y in range(8):
            for x in range(8):
                self.game.board[y][x] = PIECE_BLACK

        self.assertFalse(self.game.has_any_valid_move(PIECE_BLACK))
        self.assertFalse(self.game.has_any_valid_move(PIECE_WHITE))

        self.game.update_counts()
        self.assertEqual(self.game.black_count, 64)
        self.assertEqual(self.game.white_count, 0)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区棋盘绿呢、黑白子与光标规格"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查中心 (4, 4) 白棋像素 (对应屏幕像素 8, 8，颜色 [245, 245, 245])
        white_idx = (8 * 16 + 8) * 3
        self.assertEqual(fb[white_idx], 245)
        self.assertEqual(fb[white_idx + 1], 245)
        self.assertEqual(fb[white_idx + 2], 245)


if __name__ == "__main__":
    unittest.main()
