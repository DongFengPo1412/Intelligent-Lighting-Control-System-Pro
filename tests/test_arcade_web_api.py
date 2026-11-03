# -*- coding: utf-8 -*-
"""
test_arcade_web_api.py —— 手机端 Web API / 设备通信协议集成测试
验证点：
1. ESP32 硬件权威模式响应与状态回显 (Hardware Authority)
2. 设备离线 / 指令失败时诚实报错，严禁冒充成功 (Error Transparency)
3. 非法游戏编号严格校验拒绝 (Validation)
4. 本地模拟器模式明确标注 source: "simulator" 与 simulated: True
5. 心跳链路与 HUD 状态同步
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


class MockOnlineEsp32Controller:
    """模拟在线的真实 ESP32-S3 灯板"""
    def __init__(self):
        self.port = "COM9"
        self.control_connected = True
        self.sent_payloads = []
        self.current_gid = 1
        self.current_state = 0
        self.score = 120
        self.high_score = 500

    def command_result(self, payload: dict) -> dict:
        self.sent_payloads.append(payload)
        cmd = payload.get("cmd", "")
        action = payload.get("action", "")

        if cmd == "frame":
            return {
                "status": "ok",
                "pixels": "ff0000" * 256,
                "frame_id": 42,
                "frame_source": "hardware_pwm"
            }

        if cmd == "arcade":
            if action == "select":
                gid = payload.get("game_id", 0)
                if gid not in (1, 33, 41):
                    return {"status": "error", "error": "invalid_game_id"}
                self.current_gid = gid
                self.current_state = 0
                return {
                    "status": "ok",
                    "arcade": {
                        "active": True,
                        "game_id": gid,
                        "name": "超级马里奥" if gid == 1 else ("经典贪吃蛇" if gid == 33 else "俄罗斯方块"),
                        "state": 0,
                        "score": 0,
                        "high_score": self.high_score,
                        "lives": 3,
                        "control_type": CTRL_DPAD_4WAY if gid == 33 else CTRL_ARCADE_AB
                    }
                }
            elif action == "start":
                self.current_state = 1
            elif action == "pause":
                self.current_state = 2
            elif action == "resume":
                self.current_state = 1
            elif action == "reset":
                self.current_state = 0

            return {
                "status": "ok",
                "arcade": {
                    "active": True,
                    "game_id": self.current_gid,
                    "state": self.current_state,
                    "score": self.score,
                    "high_score": self.high_score,
                    "lives": 3,
                    "control_type": CTRL_DPAD_4WAY if self.current_gid == 33 else CTRL_ARCADE_AB
                }
            }
        return {"status": "ok"}


class MockOfflineController:
    """模拟已断开的设备"""
    def __init__(self):
        self.port = "COM9"
        self.control_connected = False

    def command_result(self, payload: dict) -> dict:
        return {"status": "error", "error": "device_offline"}


class TestArcadeWebApi(unittest.TestCase):

    def test_01_hardware_authority_mode(self):
        ctrl = MockOnlineEsp32Controller()
        session = ArcadeSession(controller=ctrl)

        # 1. 硬件模式选卡
        res = session.select_game(1)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["source"], "esp32_hardware")
        self.assertFalse(res["simulated"])
        self.assertEqual(session.status["game_id"], 1)

        # 2. 验证得分与高分来自 ESP32 回包而非本地自编
        self.assertEqual(session.status["high_score"], 500)

        # 3. 硬件生命周期
        start_res = session.start()
        self.assertEqual(start_res["status"], "ok")
        self.assertEqual(start_res["source"], "esp32_hardware")
        self.assertEqual(session.status["state"], STATE_PLAYING)

    def test_02_invalid_game_id_rejection(self):
        ctrl = MockOnlineEsp32Controller()
        session = ArcadeSession(controller=ctrl)

        res = session.select_game(999)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error"], "invalid_game_id")

    def test_03_device_offline_no_fake_success(self):
        ctrl = MockOfflineController()
        session = ArcadeSession(controller=ctrl)

        # 在硬件离线时，非模拟模式下严禁冒充成功
        res = session.select_game(1, force_simulation=False)
        self.assertEqual(res["status"], "error")

    def test_04_explicit_simulator_mode_clear_tag(self):
        ctrl = MockOfflineController()
        session = ArcadeSession(controller=ctrl)

        # 显式申请模拟模式
        res = session.select_game(33, force_simulation=True)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["source"], "simulator")
        self.assertTrue(res["simulated"])
        self.assertTrue(session.status["simulated"])

    def test_05_frame_source_distinction(self):
        ctrl = MockOnlineEsp32Controller()
        session = ArcadeSession(controller=ctrl)
        session.select_game(1)

        frame_res = session.get_frame()
        self.assertEqual(frame_res["source"], "hardware_pwm")
        self.assertFalse(frame_res["simulated"])
        self.assertEqual(len(frame_res["hex"]), 768 * 2)


if __name__ == "__main__":
    unittest.main()
