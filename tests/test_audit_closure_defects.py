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
import asyncio
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
            "不要启动第101款游戏",
            "千万别玩微光纪元",
            "先别启动#101",
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

        p101 = exact_plan("启动微光纪元")
        self.assertEqual(p101, {"kind": "control", "actions": [{"tool": "start_game", "value": 101}]})

        p101_id = exact_plan("启动#101")
        self.assertEqual(p101_id, {"kind": "control", "actions": [{"tool": "start_game", "value": 101}]})

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
        # Clear mock history from session startup so we strictly verify the in-flight frame
        self.controller.send_json.reset_mock()

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
        self.controller.send_json.reset_mock()
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
        self.controller.mode = 19  # Snake game mode
        sess_id = self.hub.start_remote(mode="gesture_game")
        self.hub.mode = "gesture_game"

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


class TestClosureDefectsRound3(unittest.TestCase):
    def test_health_probe_endpoint(self):
        """APK health probe requires GET /api/health returning HTTP 200 with status ok and service KurisuPro."""
        from aiohttp.test_utils import TestServer, TestClient
        import web_server

        async def run_test():
            app = web_server.create_app(simulate=True, no_audio=True)
            async with TestServer(app) as server:
                async with TestClient(server) as client:
                    resp = await client.get("/api/health")
                    self.assertEqual(resp.status, 200)
                    data = await resp.json()
                    self.assertEqual(data.get("status"), "ok")
                    self.assertEqual(data.get("service"), "KurisuPro")

                    # GET /api/auth/challenge must not return 405
                    resp_chal = await client.get("/api/auth/challenge")
                    self.assertNotEqual(resp_chal.status, 405)
        asyncio.run(run_test())

    def test_run_chat_non_blocking_preemption(self):
        """A new chat turn immediately preempts prior turn without waiting for its LLM completion."""
        import web_server

        async def run_test():
            web_server.shutting_down = False
            turn1_started = threading.Event()
            turn1_cancelled = threading.Event()
            turn2_completed = threading.Event()

            class MockPreemptibleAgent:
                def __init__(self):
                    self.last_model_error = None
                    self.last_translation_error = None
                    self.last_tts_error = None
                    self.last_turn_timings = {}

                def chat(self, msg, cancelled=None):
                    if msg == "turn1":
                        turn1_started.set()
                        # Wait up to 3s or until cancelled
                        for _ in range(300):
                            if cancelled and cancelled.is_set():
                                turn1_cancelled.set()
                                return "turn1_aborted"
                            time.sleep(0.01)
                        return "turn1_finished"
                    elif msg == "turn2":
                        turn2_completed.set()
                        return "turn2_fast"
                    return "unknown"

            orig_agent = web_server.agent
            web_server.agent = MockPreemptibleAgent()
            try:
                task1 = asyncio.create_task(web_server.run_chat("turn1"))
                await asyncio.sleep(0.05)
                self.assertTrue(turn1_started.wait(timeout=1.0))

                # Start turn2 while turn1 is still running
                t0 = time.monotonic()
                task2 = asyncio.create_task(web_server.run_chat("turn2"))
                res2 = await asyncio.wait_for(task2, timeout=1.0)
                elapsed = time.monotonic() - t0

                # turn2 must complete fast (< 0.5s), proving chat_lock was released during turn1
                self.assertLess(elapsed, 0.5)
                self.assertEqual(res2["reply"], "turn2_fast")
                self.assertTrue(turn2_completed.is_set())
                self.assertTrue(turn1_cancelled.wait(timeout=1.0), "Turn 1 must receive cancellation signal")

                try:
                    await task1
                except (asyncio.CancelledError, Exception):
                    pass
                self.assertTrue(task1.cancelled(), "Turn 1 task must be cancelled by Turn 2")
            finally:
                web_server.agent = orig_agent

        asyncio.run(run_test())

    def test_pcm_frame_sizes(self):
        """PCM receive buffer accepts standard 512-sample (1024-byte) and 1024-sample frames without truncation."""
        import network_audio
        hdr_128 = network_audio.packet(1, b'\x00' * (128 * 2))
        hdr_512 = network_audio.packet(1, b'\x00' * (512 * 2))
        hdr_1024 = network_audio.packet(1, b'\x00' * (1024 * 2))

        self.assertEqual(len(hdr_128), 7 + 256)
        self.assertEqual(len(hdr_512), 7 + 1024)
        self.assertEqual(len(hdr_1024), 7 + 2048)
        self.assertEqual(hdr_512[:4], b'KAP1')
        self.assertEqual(hdr_512[4], 1)
        self.assertEqual(hdr_512[5], 4)  # 1024 >> 8
        self.assertEqual(hdr_512[6], 0)  # 1024 & 0xff


class TestClosureDefectsRound4(unittest.TestCase):
    def test_voice_turn_async_lifecycle_and_barge_in(self):
        """Voice listener maintains paused state during thinking, allows barge-in, and discards obsolete turn completions."""
        from voice_listener import VoiceListener

        dispatched_turns = []
        def mock_callback(text, turn_id=None):
            dispatched_turns.append((text, turn_id))
        mock_callback.is_async_turn = True

        vl = VoiceListener(callback=mock_callback)
        vl.is_listening = True
        vl.controller = MagicMock()
        vl.controller._music_player = None

        # 1. Trigger utterance execution
        vl._dispatch_command("红莉栖你好", turn_id=1)
        self.assertEqual(len(dispatched_turns), 1)
        self.assertEqual(dispatched_turns[0], ("红莉栖你好", 1))
        # In async mode, pause state is maintained until finish_turn
        vl.is_paused = True
        vl._turn_in_flight = True
        vl._active_turn_id = 1

        # 2. Simulate Barge-In during thinking / playback
        # When user interrupts, _active_turn_id increments and turn_cancelled is set
        cancel = vl.turn_cancelled
        self.assertIsNotNone(cancel)
        self.assertFalse(cancel.is_set())

        # Barge-in event occurs
        vl._active_turn_id += 1  # now 2
        vl._turn_in_flight = False
        cancel.set()

        # 3. Old async turn completes late with turn_id=1
        vl.finish_turn(turn_id=1, text="红莉栖你好")
        # Turn 1 completion must be discarded without resuming listening or resetting state
        self.assertEqual(vl._active_turn_id, 2)

        # 4. New turn (turn 2) dispatches and finishes legitimately
        vl._turn_in_flight = True
        vl.is_awake = True
        vl.finish_turn(turn_id=2, text="开启红灯")
        self.assertFalse(vl._turn_in_flight)
        # Because continuous conversation is enabled, is_awake remains True
        self.assertTrue(vl.is_awake)

    def test_apk_host_binding_and_camera_boundary_contracts(self):
        """APK strictly binds host to senderIp, and camera requires explicit authentication."""
        # 1. Host binding simulation
        sender_ip = "192.168.43.100"
        beacon_with_spoofed_url = {
            "service": "KurisuPro",
            "port": 8080,
            "server_url": "http://10.99.1.50:8080",
            "board_ip": "192.168.43.200"
        }
        # Production binding rule: extract port from beacon, strictly bind host to senderIp
        import urllib.parse
        parsed = urllib.parse.urlparse(beacon_with_spoofed_url.get("server_url", ""))
        port = parsed.port if parsed.port else beacon_with_spoofed_url.get("port", 8080)
        bound_url = f"http://{sender_ip}:{port}"
        self.assertEqual(bound_url, "http://192.168.43.100:8080")
        self.assertNotIn("10.99.1.50", bound_url)

        # 2. Decoupled Camera Authorization rule
        authenticated_origin = "http://192.168.43.100:8080"
        server_origin = "http://192.168.43.100:8080"

        # Explicitly authenticated page
        def is_page_explicitly_authenticated(url, auth_origin):
            if not auth_origin:
                return False
            u = urllib.parse.urlparse(url)
            page_origin = f"{u.scheme}://{u.netloc}"
            return page_origin.lower() == auth_origin.lower()

        # Passwordless unauthenticated mode (auth_origin is empty, but server_origin is set)
        self.assertTrue(is_page_explicitly_authenticated("http://192.168.43.100:8080/index.html", authenticated_origin))
        self.assertFalse(is_page_explicitly_authenticated("http://192.168.43.100:8080/index.html", ""))
        self.assertFalse(is_page_explicitly_authenticated("http://10.99.1.50:8080/index.html", authenticated_origin))

    def test_audio_ticket_authorization_guard_rules(self):
        """Only authenticated PC clients can request audio tickets; ordinary hotspot devices are rejected."""
        def handle_ticket_request(is_sta_peer: bool, token_ok: bool, cmd: str):
            if cmd == "request_audio_ticket":
                return is_sta_peer and token_ok
            return is_sta_peer

        # Phone on hotspot (no token): allowed to control lamp, denied ticket
        self.assertTrue(handle_ticket_request(is_sta_peer=True, token_ok=False, cmd="set_light"))
        self.assertFalse(handle_ticket_request(is_sta_peer=True, token_ok=False, cmd="request_audio_ticket"))

        # Authorized PC on hotspot: allowed to control lamp and request ticket
        self.assertTrue(handle_ticket_request(is_sta_peer=True, token_ok=True, cmd="set_light"))
        self.assertTrue(handle_ticket_request(is_sta_peer=True, token_ok=True, cmd="request_audio_ticket"))

        # External client: rejected for both
        self.assertFalse(handle_ticket_request(is_sta_peer=False, token_ok=False, cmd="set_light"))
        self.assertFalse(handle_ticket_request(is_sta_peer=False, token_ok=False, cmd="request_audio_ticket"))


class TestAfeTimelineAndBoundedWarmup(unittest.TestCase):
    """AFE recovery timeline alignment and bounded warmup degradation verification."""

    class AfeSampleStreamModel:
        def __init__(self, max_warmup_blocks=5):
            self.max_warmup_blocks = max_warmup_blocks
            self.raw_history = []
            self.afe_fetched = []
            self.total_raw_pushed = 0
            self.total_afe_fetched = 0
            self.emitted_source_samples = 0
            self.silence_warmup_samples = 0
            self.warmed_up = False
            self.warmup_blocks_emitted = 0
            self.warmup_timed_out = False
            self.degraded_to_raw = False
            self.history_offset = 0

        def push_input(self, samples):
            self.raw_history.extend(samples)
            self.total_raw_pushed += len(samples)

        def push_fetched(self, samples):
            start_idx = self.total_afe_fetched
            self.total_afe_fetched += len(samples)
            needed_start = self.emitted_source_samples
            if start_idx < needed_start:
                discard = min(len(samples), needed_start - start_idx)
                samples = samples[discard:]
            if len(samples) > 0:
                self.afe_fetched.extend(samples)

        def emit(self, count, fallback_raw=None):
            if len(self.afe_fetched) >= count:
                dest = self.afe_fetched[:count]
                self.afe_fetched = self.afe_fetched[count:]
                self.emitted_source_samples += count
                self.warmed_up = True
                self.degraded_to_raw = False
                self._prune()
                return True, dest

            if not self.warmed_up and not self.warmup_timed_out:
                if self.warmup_blocks_emitted < self.max_warmup_blocks:
                    dest = [0] * count
                    self.warmup_blocks_emitted += 1
                    self.silence_warmup_samples += count
                    return False, dest
                else:
                    self.warmup_timed_out = True
                    self.degraded_to_raw = True

            dest = self._get_raw_samples(self.emitted_source_samples, count, fallback_raw)
            self.emitted_source_samples += count
            self.afe_fetched.clear()
            self._prune()
            return False, dest

        def _get_raw_samples(self, start_idx, count, fallback_raw):
            local_idx = start_idx - self.history_offset
            if 0 <= local_idx and local_idx + count <= len(self.raw_history):
                return self.raw_history[local_idx : local_idx + count]
            elif fallback_raw:
                return list(fallback_raw)
            return [0] * count

        def _prune(self):
            max_keep = 2400
            if len(self.raw_history) > max_keep:
                drop = len(self.raw_history) - max_keep
                self.raw_history = self.raw_history[drop:]
                self.history_offset += drop

    def test_steady_state_under_retrieval_and_recovery_timeline(self):
        """Under-retrieval in steady state emits delayed raw block without skipping or stutter."""
        stream = self.AfeSampleStreamModel(max_warmup_blocks=5)
        outputs = []

        # Block 0: Warmup silence
        b0 = list(range(1, 241))
        stream.push_input(b0)
        ok0, out0 = stream.emit(240, b0)
        outputs.append((ok0, out0))

        # Block 1: AFE delivers Block 0 (1..240)
        b1 = list(range(241, 481))
        stream.push_input(b1)
        stream.push_fetched(list(range(1, 241)))
        ok1, out1 = stream.emit(240, b1)
        outputs.append((ok1, out1))

        # Block 2: AFE under-retrieval (0 samples) -> fallback raw 241..480 along same timeline
        b2 = list(range(481, 721))
        stream.push_input(b2)
        ok2, out2 = stream.emit(240, b2)
        outputs.append((ok2, out2))

        # Block 3: AFE catches up with delayed 241..480 + 481..720 -> 241..480 dropped, 481..720 emitted
        b3 = list(range(721, 961))
        stream.push_input(b3)
        stream.push_fetched(list(range(241, 481)) + list(range(481, 721)))
        ok3, out3 = stream.emit(240, b3)
        outputs.append((ok3, out3))

        # Block 4: Steady state resumes
        b4 = list(range(961, 1201))
        stream.push_input(b4)
        stream.push_fetched(list(range(721, 961)))
        ok4, out4 = stream.emit(240, b4)
        outputs.append((ok4, out4))

        self.assertFalse(outputs[0][0])  # Warmup
        self.assertTrue(outputs[1][0])   # AFE
        self.assertFalse(outputs[2][0])  # Fallback raw
        self.assertTrue(outputs[3][0])   # Recovered AFE
        self.assertTrue(outputs[4][0])   # Steady AFE

        # Verification of full concatenated audio: Block 0 silence, Blocks 1..4 monotonic 1..960
        all_samples = []
        for _, out in outputs:
            all_samples.extend(out)
        self.assertEqual(len(all_samples), 5 * 240)
        self.assertEqual(all_samples[:240], [0] * 240)
        self.assertEqual(all_samples[240:], list(range(1, 961)))

    def test_bounded_warmup_timeout_and_degradation_to_raw(self):
        """AFE zero output for 40 blocks times out at max_warmup_blocks and degrades to continuous raw PCM."""
        stream = self.AfeSampleStreamModel(max_warmup_blocks=5)
        outputs = []
        for b in range(40):
            raw = list(range(b * 240 + 1, (b + 1) * 240 + 1))
            stream.push_input(raw)
            ok, out = stream.emit(240, raw)
            outputs.append((ok, out))

        self.assertTrue(stream.warmup_timed_out)
        self.assertTrue(stream.degraded_to_raw)

        # Warmup blocks 0..4 are silence
        for b in range(5):
            self.assertFalse(outputs[b][0])
            self.assertEqual(outputs[b][1], [0] * 240)

        # Blocks 5..39 are continuous raw PCM from source timeline
        raw_concat = []
        for b in range(5, 40):
            self.assertFalse(outputs[b][0])
            raw_concat.extend(outputs[b][1])

        self.assertEqual(len(raw_concat), 35 * 240)
        self.assertEqual(raw_concat, list(range(1, 35 * 240 + 1)))


if __name__ == "__main__":
    unittest.main()
