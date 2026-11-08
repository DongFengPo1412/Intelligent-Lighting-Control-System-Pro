"""Unit and regression tests for Codex whole-system review defects:
1. Speech game negation protection and injection defense (semantic_control.py, kurisu_agent.py)
2. Vision stopping race condition: in-flight stale frames dropped on stop/source-switch (multimodal_hub.py)
"""
import io
import json
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
VISION_DIR = REPO_ROOT / "pc-agent-vision"
if str(VISION_DIR) not in sys.path:
    sys.path.insert(0, str(VISION_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np

from arcade_catalog import find_arcade_games, resolve_arcade_game
from kurisu_agent import KurisuAgent
from multimodal_hub import ControlArbiter, MultimodalHub
from semantic_control import (
    SemanticControl,
    exact_plan,
    extract_negated_games,
    from_wire,
    validate_plan,
)
from simulator import SilentVoice, SimulatedController


class TestSpeechGameNegation(unittest.TestCase):
    """Defect 1: speech negative arcade game instructions must not enter execution chain."""

    def test_negation_forms_route_to_chat(self):
        """Cover #041, game name, and '第41款' forms."""
        test_inputs = [
            "不要启动#041",
            "别打开俄罗斯方块",
            "不要玩第41款游戏",
            "不要玩游戏",
            "不想玩俄罗斯方块",
            "别启动#41",
            "千万别打开#041",
            "不要启动041号游戏",
        ]
        for utterance in test_inputs:
            plan = exact_plan(utterance)
            self.assertEqual(
                plan,
                {"kind": "chat", "actions": []},
                f"Utterance '{utterance}' should route to chat without control actions",
            )

    def test_positive_commands_preserved(self):
        """Positive commands for games, colors, and timers must be preserved."""
        # Cartridge launch by ID and name
        p1 = exact_plan("启动#041")
        self.assertEqual(p1, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

        p2 = exact_plan("打开第41款游戏")
        self.assertEqual(p2, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

        p3 = exact_plan("打开俄罗斯方块")
        self.assertEqual(p3, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

        # Other modules
        green = exact_plan("纯绿灯")
        self.assertEqual(green, {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 3}]})

        countdown = exact_plan("停止倒计时")
        self.assertEqual(countdown, {"kind": "control", "actions": [{"tool": "stop_countdown", "value": 0}]})

    def test_mixed_sentence_executes_only_permitted_light(self):
        """'不要启动#041，给我切到红灯' should safely separate and execute only the permitted light."""
        mixed1 = exact_plan("不要启动#041，给我切到红灯")
        self.assertEqual(
            mixed1,
            {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 1}]},
            "Mixed sentence should execute red light without starting #041",
        )

        mixed2 = exact_plan("别玩俄罗斯方块，把灯调成蓝色")
        self.assertEqual(
            mixed2,
            {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 2}]},
            "Mixed sentence should execute blue light without starting #041",
        )

    def test_mixed_ambiguous_sentence_returns_clarify_not_game(self):
        """Ambiguous non-game requests in mixed sentence should request clarification, never launch negated game."""
        mixed_ambig = exact_plan("不要启动#041，换个好玩点的灯")
        self.assertEqual(mixed_ambig, {"kind": "clarify", "actions": []})

    def test_plan_validation_rejects_injected_negated_game(self):
        """Plan validator MUST reject any plan containing explicitly negated game IDs."""
        injected = {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]}

        # Negative utterance with #041
        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected, user_text="不要启动#041")
        self.assertIn("explicitly negated", str(ctx.exception))

        # Negative utterance with game name
        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected, user_text="别打开俄罗斯方块")
        self.assertIn("explicitly negated", str(ctx.exception))

        # General game negation
        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected, user_text="不要玩游戏")
        self.assertIn("explicitly negated", str(ctx.exception))

        # Positive utterance allows game 41
        validated = validate_plan(injected, user_text="启动#041")
        self.assertEqual(validated, injected)

    def test_agent_hardware_execution_blocked_on_injected_plan(self):
        """Even if an injected model bypasses planner and proposes negated game,
        hardware execution is intercepted and controller is never called."""
        ctrl = MagicMock()
        ctrl.port = "COM3"
        ctrl.is_connected = True
        ctrl.start_arcade = MagicMock(return_value={"status": "ok"})

        voice = SilentVoice()
        agent = KurisuAgent(controller=ctrl, voice=voice)

        # Mock the semantic planner to inject #041 plan on negative prompt
        mock_injected_plan = {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]}
        agent.semantic = MagicMock()
        agent.semantic.plan.return_value = mock_injected_plan

        # Simulate turn with negative user message
        agent.chat("不要启动#041")

        # Hardware controller start_arcade MUST NOT be called!
        ctrl.start_arcade.assert_not_called()


class TestVisionStopStaleFrameIsolation(unittest.TestCase):
    """Defect 2: late in-flight vision frames must be discarded after session stop or source switch."""

    def setUp(self):
        self.controller = MagicMock()
        self.controller.mode = 17
        self.controller.send_json = MagicMock(return_value=True)
        self.controller.track = MagicMock()
        self.controller.hand = MagicMock()
        self.controller.pet_context = MagicMock()
        self.hub = MultimodalHub(controller=self.controller)

    def tearDown(self):
        if self.hub.started:
            self.hub.stop()

    def _create_synthetic_jpeg(self):
        img = np.zeros((320, 320, 3), dtype=np.uint8)
        img[100:220, 100:220] = (200, 200, 200)
        _, buf = cv2.imencode(".jpg", img)
        return buf.tobytes()

    def test_in_flight_frame_discarded_on_stop_remote(self):
        """Interleaved execution: frame enters inference, session is stopped,
        inference finishes -> NO preview published, NO mode switch command sent."""
        sess_id = self.hub.start_remote(mode="fingertip")
        self.assertTrue(self.hub.started)
        self.assertEqual(self.hub.source, "remote")
        self.assertEqual(self.hub.active_session_id, sess_id)

        jpeg_bytes = self._create_synthetic_jpeg()

        in_inference_event = threading.Event()
        resume_inference_event = threading.Event()

        # Mock hands.process to simulate blocking ML inference
        orig_hands = MagicMock()

        def mock_hands_process(rgb):
            in_inference_event.set()
            # Wait for main thread to stop session
            resume_inference_event.wait(timeout=5.0)
            mock_hl = MagicMock()
            mock_hl.landmark = [MagicMock(x=0.5, y=0.5, z=0.0) for _ in range(21)]
            res = MagicMock()
            res.multi_hand_landmarks = [mock_hl]
            return res

        orig_hands.process = mock_hands_process
        mock_face = MagicMock()
        mock_face.process.return_value = MagicMock(multi_face_landmarks=[])

        self.hub._remote_hands = orig_hands
        self.hub._remote_face = mock_face

        worker_result = {}

        def worker():
            try:
                obs = self.hub.process_remote_frame(jpeg_bytes, mode="fingertip", session_id=sess_id)
                worker_result["obs"] = obs
            except Exception as e:
                worker_result["error"] = e

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        # Wait until frame enters inference
        self.assertTrue(in_inference_event.wait(timeout=3.0))

        # STOP the remote session while inference is underway
        stop_success = self.hub.stop_remote(sess_id)
        self.assertTrue(stop_success)
        self.assertFalse(self.hub.started)
        self.assertIsNone(self.hub.latest_jpeg)

        # Resume inference
        resume_inference_event.set()
        t.join(timeout=3.0)

        # Assert: stale in-flight frame did NOT publish a preview!
        self.assertIsNone(self.hub.latest_jpeg, "Stale frame must not overwrite latest_jpeg after stop")

        # Assert: stale in-flight frame did NOT switch mode to 26 on controller!
        for call_item in self.controller.send_json.call_args_list:
            arg = call_item[0][0]
            self.assertNotEqual(
                arg,
                {"cmd": "mode", "val": 26},
                "Stale in-flight frame must not send mode 26 command after stop",
            )
        self.controller.track.assert_not_called()

        # Worker returned stale observation
        self.assertTrue(worker_result.get("obs", {}).get("stale", False))

    def test_in_flight_frame_discarded_on_source_switch(self):
        """Interleaved execution: frame enters inference under session 1,
        new session 2 starts -> frame 1 finishes -> discarded, does not contaminate session 2."""
        sess_1 = self.hub.start_remote(mode="fingertip")
        jpeg_bytes = self._create_synthetic_jpeg()

        in_inference_event = threading.Event()
        resume_inference_event = threading.Event()

        orig_hands = MagicMock()

        def mock_hands_process(rgb):
            in_inference_event.set()
            resume_inference_event.wait(timeout=5.0)
            mock_hl = MagicMock()
            mock_hl.landmark = [MagicMock(x=0.5, y=0.5, z=0.0) for _ in range(21)]
            res = MagicMock()
            res.multi_hand_landmarks = [mock_hl]
            return res

        orig_hands.process = mock_hands_process
        mock_face = MagicMock()
        mock_face.process.return_value = MagicMock(multi_face_landmarks=[])

        self.hub._remote_hands = orig_hands
        self.hub._remote_face = mock_face

        t = threading.Thread(
            target=lambda: self.hub.process_remote_frame(jpeg_bytes, mode="fingertip", session_id=sess_1),
            daemon=True,
        )
        t.start()

        # Wait until frame enters inference
        self.assertTrue(in_inference_event.wait(timeout=3.0))

        # Switch to a new session
        sess_2 = self.hub.start_remote(mode="pet")
        self.assertNotEqual(sess_1, sess_2)

        resume_inference_event.set()
        t.join(timeout=3.0)

        # Stale frame from sess_1 must not change mode to 26
        for call_item in self.controller.send_json.call_args_list:
            arg = call_item[0][0]
            self.assertNotEqual(
                arg,
                {"cmd": "mode", "val": 26},
                "Stale frame from old session must not change mode to 26",
            )

    def test_bounded_stop(self):
        """Stopping vision sessions is non-blocking and completes within < 100ms."""
        sess = self.hub.start_remote(mode="pet")
        t0 = time.perf_counter()
        self.hub.stop_remote(sess)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.1, "stop_remote must be bounded and immediate")


if __name__ == "__main__":
    unittest.main()
