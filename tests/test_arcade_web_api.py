# -*- coding: utf-8 -*-
"""
test_arcade_web_api.py —— 手机端 Web API / WebSocket 端到端协议集成测试
测试手机 App / Web App 控制器与后端 ArcadeRunner、卡带切换、按键下发与 HUD 状态同步。
"""

import unittest
import json
from arcade_runner import ArcadeSession
from arcade.base_cartridge import (
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    CTRL_ARCADE_AB,
    CTRL_DPAD_4WAY,
)


class MockDeviceController:
    def __init__(self):
        self.sent_commands = []

    def send_command(self, cmd_str: str) -> bool:
        self.sent_commands.append(cmd_str)
        return True


class TestArcadeWebApi(unittest.TestCase):

    def setUp(self):
        self.mock_ctrl = MockDeviceController()
        self.broadcast_messages = []

        async def mock_broadcast(msg):
            self.broadcast_messages.append(msg)

        self.session = ArcadeSession(controller=self.mock_ctrl, broadcast_fn=mock_broadcast)

    def test_01_select_games_and_dispatch_protocol(self):
        # 1. 手机端选择 #001 超级马里奥
        ok = self.session.select_game(1)
        self.assertTrue(ok)
        self.assertEqual(self.session.status["game_id"], 1)
        self.assertEqual(self.session.status["game_name"], "超级马里奥")
        self.assertEqual(self.session.status["control_type"], CTRL_ARCADE_AB)
        # 验证下发了合法 JSON 协议包
        parsed_cmds = [json.loads(c) for c in self.mock_ctrl.sent_commands]
        self.assertTrue(any(c.get("cmd") == "arcade" and c.get("action") == "select" and c.get("game_id") == 1 for c in parsed_cmds))

        # 2. 手机端切换至 #033 经典贪吃蛇
        ok = self.session.select_game(33)
        self.assertTrue(ok)
        self.assertEqual(self.session.status["game_id"], 33)
        self.assertEqual(self.session.status["control_type"], CTRL_DPAD_4WAY)

        # 3. 手机端切换至 #041 俄罗斯方块
        ok = self.session.select_game(41)
        self.assertTrue(ok)
        self.assertEqual(self.session.status["game_id"], 41)
        self.assertEqual(self.session.status["control_type"], CTRL_ARCADE_AB)

    def test_02_lifecycle_controls_and_hud_status(self):
        self.session.select_game(33)  # Snake
        self.assertEqual(self.session.status["state"], STATE_TITLE)

        # 手机点击 Start
        self.session.start()
        self.assertEqual(self.session.status["state"], STATE_PLAYING)

        # 手机点击 Pause
        self.session.pause()
        self.assertEqual(self.session.status["state"], STATE_PAUSED)

        # 手机点击 Resume
        self.session.resume()
        self.assertEqual(self.session.status["state"], STATE_PLAYING)

        # 手机点击 Reset
        self.session.reset()
        self.assertEqual(self.session.status["state"], STATE_TITLE)

    def test_03_key_input_dispatch(self):
        self.session.select_game(1)  # Mario
        self.session.start()

        # 按下跳跃键 A
        self.session.key("a", True)
        self.assertTrue(self.session.keys_down & (1 << 4))
        parsed_cmds = [json.loads(c) for c in self.mock_ctrl.sent_commands]
        self.assertTrue(any(c.get("action") == "input" and c.get("down") == 16 for c in parsed_cmds))

        # 释放跳跃键 A
        self.session.key("a", False)
        self.assertEqual(self.session.keys_down & (1 << 4), 0)


if __name__ == "__main__":
    unittest.main()
