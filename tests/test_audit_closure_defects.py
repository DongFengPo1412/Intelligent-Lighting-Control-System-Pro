"""Unit and regression tests for Codex whole-system review defects:
1. Speech game negation protection and injection defense (semantic_control.py, kurisu_agent.py)
   - Covers #041, bare number '41', Chinese numerals '四十一', game names, and legacy modes 19/21.
   - Mixed sentences execute permitted lights only.
   - Plan validator rejects negated game IDs and normalized legacy modes.
   - Hardware execution layer intercepts both start_game and legacy set_light_mode.
   - Model retry failure strictly raises ValueError and never returns unvalidated actions.
2. Vision stopping race condition: in-flight stale frames dropped on stop/source-switch (multimodal_hub.py)
   - Performance call waiting stop drops subsequent snake/tetris input.
   - Synthetic observation injection allowed for simulation/testing without active camera.
   - Non-blocking bounded stop.
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

# Pre-import heavy CV/ML dependencies to avoid cold-start import timeouts in threaded tests
import cv2
import numpy as np
try:
    import mediapipe as mp
except ImportError:
    mp = None

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
        """Cover #041, game name, bare numbers like '41', and '第41款' forms."""
        test_inputs = [
            "不要启动#041",
            "别打开俄罗斯方块",
            "不要玩第41款游戏",
            "不要玩游戏",
            "不想玩俄罗斯方块",
            "别启动#41",
            "千万别打开#041",
            "不要启动041号游戏",
            "不要启动41",
            "别玩41",
            "不要玩41号游戏",
            "不要启动 41",
            "别启动41",
            "不要玩第四十一款游戏",
        ]
        for utterance in test_inputs:
            plan = exact_plan(utterance)
            self.assertEqual(
                plan,
                {"kind": "chat", "actions": []},
                f"Utterance '{utterance}' should route to chat without control actions",
            )

    def test_bare_number_negation_extraction_accuracy(self):
        """'不要启动41' must extract game ID 41, NOT truncate to game ID 4."""
        all_neg, neg_ids = extract_negated_games("不要启动41")
        self.assertFalse(all_neg)
        self.assertIn(41, neg_ids, "Game 41 must be extracted from '不要启动41'")
        self.assertNotIn(4, neg_ids, "Game 4 must NOT be falsely extracted from '不要启动41'")

        all_neg2, neg_ids2 = extract_negated_games("别玩41")
        self.assertIn(41, neg_ids2)
        self.assertNotIn(4, neg_ids2)

    def test_positive_commands_preserved(self):
        """Positive commands for games, bare numbers, colors, and timers must be preserved."""
        # Cartridge launch by ID, bare number, and name
        p1 = exact_plan("启动#041")
        self.assertEqual(p1, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

        p1_bare = exact_plan("启动41")
        self.assertEqual(p1_bare, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

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
        """Mixed sentences should safely separate and execute only the permitted light."""
        mixed1 = exact_plan("不要启动#041，给我切到红灯")
        self.assertEqual(
            mixed1,
            {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 1}]},
            "Mixed sentence should execute red light without starting #041",
        )

        mixed1_bare = exact_plan("不要启动41，给我切到红灯")
        self.assertEqual(
            mixed1_bare,
            {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 1}]},
            "Mixed sentence with bare 41 should execute red light without starting 41",
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

        # Negative utterance with bare number 41
        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected, user_text="不要启动41")
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

    def test_legacy_mode_normalization_and_negation_protection(self):
        """Legacy set_light_mode 19 (#033 Snake) and 21 (#041 Tetris) must be normalized
        to start_game 33 and 41, and rejected if explicitly negated."""
        # Test mode 21 with negation on 41
        injected_mode_21 = {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 21}]}
        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected_mode_21, user_text="不要启动41")
        self.assertIn("explicitly negated", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected_mode_21, user_text="别玩俄罗斯方块")
        self.assertIn("explicitly negated", str(ctx.exception))

        # Test mode 19 with negation on snake
        injected_mode_19 = {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 19}]}
        with self.assertRaises(ValueError) as ctx:
            validate_plan(injected_mode_19, user_text="别玩贪吃蛇")
        self.assertIn("explicitly negated", str(ctx.exception))

        # Positive validation normalizes to start_game
        valid_mode_21 = validate_plan(injected_mode_21, user_text="给我俄罗斯方块")
        self.assertEqual(valid_mode_21, {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})

    def test_agent_hardware_execution_blocked_on_injected_plan(self):
        """Even if an injected model bypasses planner and proposes negated game (via start_game or legacy set_light_mode),
        hardware execution is intercepted and controller is never called."""
        ctrl = MagicMock()
        ctrl.port = "COM3"
        ctrl.is_connected = True
        ctrl.start_arcade = MagicMock(return_value={"status": "ok"})
        ctrl.set_light_mode = MagicMock(return_value={"status": "ok"})

        voice = SilentVoice()
        agent = KurisuAgent(controller=ctrl, voice=voice)

        # 1. Block start_game on negated utterance
        mock_injected_plan = {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]}
        agent.semantic = MagicMock()
        agent.semantic.plan.return_value = mock_injected_plan

        agent.chat("不要启动41")
        ctrl.start_arcade.assert_not_called()

        # 2. Block legacy set_light_mode 21 on negated utterance
        mock_mode_21_plan = {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 21}]}
        agent.semantic.plan.return_value = mock_mode_21_plan

        agent.chat("不要玩俄罗斯方块")
        ctrl.start_arcade.assert_not_called()
        ctrl.set_light_mode.assert_not_called()

    def test_model_plan_second_failure_strictly_raises_without_unvalidated_fallback(self):
        """When semantic model plan fails validation on retry, it must strictly raise ValueError
        and NEVER return unvalidated actions from a malformed response."""
        sc = SemanticControl(api_base="http://127.0.0.1:11434")

        # Mock urllib to return malformed responses on both attempts
        malformed_json_1 = json.dumps({
            "message": {"content": json.dumps({"kind": "control", "invalid_field": 123})}
        }).encode("utf-8")
        # Second attempt returns an unvalidated action payload
        malformed_json_2 = json.dumps({
            "message": {"content": json.dumps({"kind": "control", "actions": [{"tool": "illegal_tool", "value": 999}]})}
        }).encode("utf-8")

        mock_resp1 = MagicMock()
        mock_resp1.read.return_value = malformed_json_1
        mock_resp1.__enter__.return_value = mock_resp1

        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = malformed_json_2
        mock_resp2.__enter__.return_value = mock_resp2

        with patch("urllib.request.build_opener") as mock_opener_cls:
            mock_opener = MagicMock()
            mock_opener.open.side_effect = [mock_resp1, mock_resp2]
            mock_opener_cls.return_value = mock_opener

            with self.assertRaises(ValueError) as ctx:
                sc.plan("灯光给我弄得像北极极光那种流动的光", timeout=5)
            self.assertIn("Semantic plan failed validation", str(ctx.exception))


class TestVisionStopStaleFrameIsolation(unittest.TestCase):
    """Defect 2: late in-flight vision frames must be discarded after session stop or source switch."""

    def setUp(self):
        self.controller = MagicMock()
        self.controller.mode = 17
        self.controller.send_json = MagicMock(return_value=True)
        self.controller.track = MagicMock()
        self.controller.hand = MagicMock()
        self.controller.pet_context = MagicMock()
        self.controller.performance = MagicMock(return_value=True)
        self.controller.snake_move = MagicMock(return_value=True)
        self.controller.tetris_action = MagicMock(return_value=True)
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
            resume_inference_event.wait(timeout=10.0)
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

        # Wait until frame enters inference (timeout increased to avoid cold-start races)
        self.assertTrue(in_inference_event.wait(timeout=10.0))

        # STOP the remote session while inference is underway
        stop_success = self.hub.stop_remote(sess_id)
        self.assertTrue(stop_success)
        self.assertFalse(self.hub.started)
        self.assertIsNone(self.hub.latest_jpeg)

        # Resume inference
        resume_inference_event.set()
        t.join(timeout=5.0)

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
            resume_inference_event.wait(timeout=10.0)
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

        # Wait until frame enters inference (generous timeout)
        self.assertTrue(in_inference_event.wait(timeout=10.0))

        # Switch to a new session
        sess_2 = self.hub.start_remote(mode="pet")
        self.assertNotEqual(sess_1, sess_2)

        resume_inference_event.set()
        t.join(timeout=5.0)

        # Stale frame from sess_1 must not change mode to 26
        for call_item in self.controller.send_json.call_args_list:
            arg = call_item[0][0]
            self.assertNotEqual(
                arg,
                {"cmd": "mode", "val": 26},
                "Stale frame from old session must not change mode to 26",
            )

    def test_performance_waiting_stop_drops_game_input(self):
        """Deterministic regression: frame passes epoch check, enters performance(),
        session is stopped during performance() wait -> ACK returns -> snake_move is NOT called!"""
        sess_id = self.hub.start_remote(mode="gesture_game")
        self.hub.mode = "gesture_game"
        self.controller.mode = 19  # Snake game mode

        # Mock controller.performance to stop the hub while inside the call
        def mock_performance(reaction, frustration, success):
            # Stop the remote vision session while waiting for ACK
            self.hub.stop_remote(sess_id)
            return True

        self.controller.performance.side_effect = mock_performance

        # Frame metadata bound to the active session
        frame_meta = ("remote", sess_id, self.hub.session_epoch)

        obs = {
            "present": True,
            "hand": {"x": 0.1, "y": 0.5},  # x < 0.3 means direction "left"
        }

        # First call sets pending_direction to "left"
        self.hub.process(obs, now=100.0, frame_meta=frame_meta)
        self.controller.snake_move.assert_not_called()

        # Second call (> 0.2s later) triggers action: direction is valid, performance() is called
        # Inside performance(), session is stopped.
        self.hub.process(obs, now=100.3, frame_meta=frame_meta)

        # Performance was called once
        self.controller.performance.assert_called_once()

        # BUT snake_move MUST NOT be called because session stopped during performance()!
        self.controller.snake_move.assert_not_called()
        self.controller.tetris_action.assert_not_called()

    def test_bounded_stop(self):
        """Stopping vision sessions is non-blocking and completes within < 100ms."""
        sess = self.hub.start_remote(mode="pet")
        t0 = time.perf_counter()
        self.hub.stop_remote(sess)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.1, "stop_remote must be bounded and immediate")


if __name__ == "__main__":
    unittest.main()
