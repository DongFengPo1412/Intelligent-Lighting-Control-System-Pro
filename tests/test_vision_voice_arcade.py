"""Unit tests for Group 2: Multimodal Hub Arbiter Priority & Voice Arcade Launching."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure repo packages can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "pc-agent-vision"))

from arcade_catalog import resolve_arcade_game
from multimodal_hub import ControlArbiter, MultimodalHub
from semantic_control import exact_plan, to_wire, from_wire, validate_plan, describe_action
from light_tools import execute_tool, LIGHT_TOOL_DEFINITIONS


class TestVisionArbiterPriority(unittest.TestCase):
    """Issue 3: Remote frames must respect user manual priority and not clear arbiter hold."""

    def test_remote_frame_does_not_clear_manual_hold(self):
        controller = MagicMock()
        controller.send_json.return_value = True
        controller.mode = 2  # e.g., manual Blue light
        hub = MultimodalHub(controller)

        # User claims manual priority for 15 seconds
        fake_time = 1000.0
        hub.arbiter.clock = lambda: fake_time
        hub.arbiter.claim_user(15)

        self.assertFalse(hub.arbiter.allows_automatic(), "User manual priority should be active")
        self.assertEqual(hub.arbiter.until, 1015.0)

        # Create a small valid JPEG for process_remote_frame
        import cv2
        import numpy as np
        img = np.zeros((40, 40, 3), dtype=np.uint8)
        _, enc = cv2.imencode(".jpg", img)
        raw_jpeg = enc.tobytes()

        # Remote camera frame arrives with mode='fingertip'
        sent_commands = []
        controller.send_json.side_effect = lambda payload: sent_commands.append(payload) or True

        hub.process_remote_frame(raw_jpeg, mode="fingertip")

        # 1. Mode tracking attribute is updated
        self.assertEqual(hub.mode, "fingertip")

        # 2. Manual hold must NOT be cleared!
        self.assertEqual(hub.arbiter.until, 1015.0, "arbiter.until must not be reset to 0 by remote frame")
        self.assertFalse(hub.arbiter.allows_automatic(), "Automatic control must remain disallowed")

        # 3. Hardware mode must NOT have been switched to fingertip (26) during user hold
        mode_switches = [c for c in sent_commands if c.get("cmd") == "mode"]
        self.assertEqual(len(mode_switches), 0, "Hardware mode must not be preempted by remote frame")

        # After user hold expires
        fake_time = 1016.0
        self.assertTrue(hub.arbiter.allows_automatic(), "Automatic control allowed after hold expires")


class TestArcadeVoiceResolution(unittest.TestCase):
    """Issue 4: Voice resolution covering canonical 100 cartridges and aliases."""

    def test_resolve_arcade_game(self):
        self.assertEqual(resolve_arcade_game("mario"), (1, "超级马里奥"))
        self.assertEqual(resolve_arcade_game("超级马里奥"), (1, "超级马里奥"))
        self.assertEqual(resolve_arcade_game("#001"), (1, "超级马里奥"))
        self.assertEqual(resolve_arcade_game(1), (1, "超级马里奥"))
        self.assertEqual(resolve_arcade_game("1"), (1, "超级马里奥"))

        self.assertEqual(resolve_arcade_game("snake"), (33, "贪吃蛇"))
        self.assertEqual(resolve_arcade_game("贪吃蛇"), (33, "贪吃蛇"))
        self.assertEqual(resolve_arcade_game(33), (33, "贪吃蛇"))

        self.assertEqual(resolve_arcade_game("tetris"), (41, "俄罗斯方块"))
        self.assertEqual(resolve_arcade_game("俄罗斯方块"), (41, "俄罗斯方块"))
        self.assertEqual(resolve_arcade_game(41), (41, "俄罗斯方块"))

        self.assertEqual(resolve_arcade_game("pong"), (20, "双人乒乓"))
        self.assertEqual(resolve_arcade_game("双人乒乓"), (20, "双人乒乓"))

        self.assertEqual(resolve_arcade_game("breakout"), (21, "经典打砖块"))
        self.assertEqual(resolve_arcade_game("打砖块"), (21, "经典打砖块"))

        self.assertEqual(resolve_arcade_game("赛车")[0], 74)
        self.assertEqual(resolve_arcade_game("切水果")[0], 92)
        self.assertEqual(resolve_arcade_game("青蛙过河")[0], 97)

        self.assertIsNone(resolve_arcade_game("invalid_game_name_xyz"))
        self.assertIsNone(resolve_arcade_game(999))


class TestSemanticGamePlan(unittest.TestCase):
    """Issue 4: Fast-path semantic planning for game launches, negations, and ambiguities."""

    def test_positive_game_launches(self):
        p1 = exact_plan("启动马里奥")
        self.assertEqual(p1, {"kind": "control", "actions": [{"tool": "start_game", "value": 1}]})

        p2 = exact_plan("玩超级马里奥")
        self.assertEqual(p2, {"kind": "control", "actions": [{"tool": "start_game", "value": 1}]})

        p3 = exact_plan("玩俄罗斯方块")
        self.assertEqual(p3, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

        p4 = exact_plan("打开贪吃蛇")
        self.assertEqual(p4, {"kind": "control", "actions": [{"tool": "start_game", "value": 33}]})

        p5 = exact_plan("来局双人乒乓吧")
        self.assertEqual(p5, {"kind": "control", "actions": [{"tool": "start_game", "value": 20}]})

        p6 = exact_plan("启动打砖块")
        self.assertEqual(p6, {"kind": "control", "actions": [{"tool": "start_game", "value": 21}]})

        p7 = exact_plan("启动第1款游戏")
        self.assertEqual(p7, {"kind": "control", "actions": [{"tool": "start_game", "value": 1}]})

        p8 = exact_plan("玩第41个游戏")
        self.assertEqual(p8, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

    def test_negations_return_chat(self):
        self.assertEqual(exact_plan("不要玩游戏"), {"kind": "chat", "actions": []})
        self.assertEqual(exact_plan("别打开马里奥"), {"kind": "chat", "actions": []})
        self.assertEqual(exact_plan("不想玩游戏了"), {"kind": "chat", "actions": []})
        self.assertEqual(exact_plan("不用玩俄罗斯方块"), {"kind": "chat", "actions": []})
        self.assertEqual(exact_plan("别玩打砖块"), {"kind": "chat", "actions": []})
        self.assertEqual(exact_plan("不要玩切水果"), {"kind": "chat", "actions": []})

    def test_ambiguity_returns_clarify(self):
        self.assertEqual(exact_plan("玩游戏"), {"kind": "clarify", "actions": []})
        self.assertEqual(exact_plan("我想玩游戏"), {"kind": "clarify", "actions": []})
        self.assertEqual(exact_plan("打开游戏"), {"kind": "clarify", "actions": []})
        self.assertEqual(exact_plan("来局游戏吧"), {"kind": "clarify", "actions": []})
        self.assertEqual(exact_plan("启动街机"), {"kind": "clarify", "actions": []})

    def test_wire_and_describe(self):
        action = {"tool": "start_game", "value": 1}
        wire = to_wire("control", [action])
        self.assertEqual(wire["game_id"], 1)
        plan = from_wire(wire)
        self.assertEqual(plan["actions"], [action])

        zh, ja = describe_action(action)
        self.assertIn("超级马里奥", zh)
        self.assertIn("超级马里奥", ja)


class TestLightControllerArcadeExecution(unittest.TestCase):
    """Issue 4: LightController.start_arcade and tool execution with offline handling."""

    def test_start_arcade_and_execute_tool_success(self):
        from light_controller import LightController

        controller = LightController(port="SIMULATION")
        res = controller.start_arcade("mario")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["game_id"], 1)
        self.assertEqual(res["game_name"], "超级马里奥")

        # Test execute_tool with mocked controller returning ok
        mock_ctrl = MagicMock()
        mock_ctrl.start_arcade.return_value = {
            "status": "ok",
            "game_id": 1,
            "game_name": "超级马里奥",
            "source": "simulator",
            "simulated": True,
        }
        with patch("light_tools.get_light_controller", return_value=mock_ctrl):
            t_res = execute_tool("start_game", {"game": "超级马里奥"})
            self.assertEqual(t_res["status"], "success")
            self.assertEqual(t_res["game_id"], 1)
            mock_ctrl.start_arcade.assert_called_once_with("超级马里奥")

    def test_start_arcade_device_offline(self):
        from light_controller import LightController

        controller = MagicMock()
        controller.port = "COM3"
        controller.control_connected = False
        controller.is_connected = False
        controller._lock = MagicMock()
        controller.send_json.return_value = False

        real_start_arcade = LightController.start_arcade.__get__(controller, LightController)
        res = real_start_arcade("mario")

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error"], "device_offline")

        # Verify execute_tool reflects offline failure
        mock_ctrl = MagicMock()
        mock_ctrl.start_arcade.return_value = {
            "status": "error",
            "error": "device_offline",
            "message": "ESP32 硬件灯板未连接或网络离线，请先检查 Wi-Fi 连接",
        }
        with patch("light_tools.get_light_controller", return_value=mock_ctrl):
            t_res = execute_tool("start_game", {"game": "mario"})
            self.assertEqual(t_res["status"], "error")

    def test_unknown_game(self):
        from light_controller import LightController
        controller = LightController(port="SIMULATION")
        res = controller.start_arcade("unknown_xyz")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error"], "unknown_game")


if __name__ == "__main__":
    unittest.main()
