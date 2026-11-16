"""Round 1 rectification regression suite reaching production code paths.

Covers F01, F04, F05, F07, F08, F09, F10, F11, F13 and vision-to-board command closure.
No physical ESP32 hardware, live webcam, microphone, or private user data accessed.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

import access_control
import kurisu_agent
import music_engine
import service_discovery
import web_server
from access_control import (
    AccessPolicy,
    _parse_posix_ip_addr,
    _parse_windows_ipconfig,
    resolve_trust_private,
)
from kurisu_agent import KurisuAgent
from memory_store import MemoryStore
from multimodal_hub import MultimodalHub
from music_engine import (
    DEFAULT_MUSIC_GAIN,
    MusicPlayer,
    SpeakerAudioProcessor,
    process_speaker_audio,
)
from simulator import SilentVoice, SimulatedController


def _tmp_dir():
    base = os.environ.get("KURISU_TEST_TMP")
    if base:
        Path(base).mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=base)
    return tempfile.TemporaryDirectory()


class F07SpeakerAudioContinuityTests(unittest.TestCase):
    def test_continuous_monotonic_gains_without_shortcut_bypass(self):
        sr = 16000
        t = np.linspace(0, 0.5, sr // 2, endpoint=False)
        sig = np.sin(2 * np.pi * 440 * t) * 0.8 + np.sin(2 * np.pi * 30 * t) * 0.15
        pcm = (np.clip(sig, -1.0, 1.0) * 32767).astype("<i2").tobytes()

        rms_values = []
        peak_values = []
        for g in (0.15, 0.25, 0.35, 0.50, 0.62, 0.75, 1.0):
            out = process_speaker_audio(pcm, gain=g)
            arr = np.frombuffer(out, dtype="<i2").astype(np.float64) / 32768.0
            rms_values.append(float(np.sqrt(np.mean(arr * arr))))
            peak_values.append(float(np.max(np.abs(arr))))
            self.assertLessEqual(peak_values[-1], 0.85 + 1e-4, f"Digital ceiling exceeded at gain={g}")

        # Monotonically non-decreasing across the full gain range without a 0.25 discontinuity jump
        for i in range(len(rms_values) - 1):
            self.assertLess(rms_values[i], rms_values[i + 1] + 1e-4)

        # Even at 0.25 baseline, 105Hz HPF removes 30Hz sub-bass rumble cleanly instead of raw bypass
        low_only = (np.sin(2 * np.pi * 30 * t) * 0.5 * 32767).astype("<i2").tobytes()
        low_out = np.frombuffer(process_speaker_audio(low_only, gain=0.25), dtype="<i2").astype(np.float64) / 32768.0
        self.assertLess(float(np.sqrt(np.mean(low_out[800:] ** 2))), 0.025)

    def test_quiet_signal_not_auto_maximized_above_gain(self):
        sr = 16000
        t = np.linspace(0, 0.5, sr // 2, endpoint=False)
        quiet = (np.sin(2 * np.pi * 440 * t) * 0.05 * 32767).astype("<i2").tobytes()
        out = np.frombuffer(process_speaker_audio(quiet, gain=0.30), dtype="<i2").astype(np.float64) / 32768.0
        self.assertLessEqual(float(np.max(np.abs(out))), 0.05 * 0.30 + 1e-3)

    def test_chunked_filter_preserves_state_continuously(self):
        sr = 16000
        t = np.linspace(0, 0.5, sr // 2, endpoint=False)
        sig = np.sin(2 * np.pi * 440 * t) * 0.7
        pcm = (sig * 32767).astype("<i2").tobytes()

        ref_peak = float(np.max(np.abs(sig))) * 0.999
        whole_proc = SpeakerAudioProcessor(gain=0.62)
        whole_arr = np.frombuffer(whole_proc.process_chunk(pcm, reference_peak=ref_peak), dtype="<i2")

        chunk_proc = SpeakerAudioProcessor(gain=0.62)
        chunks_out = []
        step = 960 * 2  # odd 960-sample chunk boundaries
        for off in range(0, len(pcm), step):
            chunks_out.append(chunk_proc.process_chunk(pcm[off : off + step], reference_peak=ref_peak))
        chunk_arr = np.frombuffer(b"".join(chunks_out), dtype="<i2")
        # Stateful HPF filtering across chunks must be bit-identical to filtering the whole stream
        self.assertEqual(chunk_arr.tolist(), whole_arr.tolist())

    def test_music_player_uses_unified_default_gain(self):
        ctrl = SimulatedController()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KURISU_MUSIC_GAIN", None)
            player = MusicPlayer(ctrl)
            self.assertEqual(player.gain, DEFAULT_MUSIC_GAIN)


class F08RunChatPauseOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.orig_listener = web_server.listener
        self.orig_agent = web_server.agent
        self.orig_voice = web_server.voice
        self.orig_pro = web_server.pro_api
        web_server.shutting_down = False
        web_server.pro_api = None
        web_server.voice = SilentVoice()

    async def asyncTearDown(self):
        web_server.shutting_down = False
        web_server.listener = self.orig_listener
        web_server.agent = self.orig_agent
        web_server.voice = self.orig_voice
        web_server.pro_api = self.orig_pro

    def _make_listener(self, initially_paused=False, listening=True, music_suspended=False):
        calls = []

        class MockListener:
            def __init__(self):
                self.is_paused = initially_paused
                self.is_listening = listening
                self._music_suspended = music_suspended

            def pause(self):
                calls.append("pause")
                self.is_paused = True

            def resume(self):
                calls.append("resume")
                self.is_paused = False

        return MockListener(), calls

    async def test_preemption_a_to_b_to_c_resumes_exactly_once_at_end(self):
        listener, calls = self._make_listener()
        web_server.listener = listener

        gate_a = threading.Event()
        gate_b = threading.Event()

        class MockAgent:
            def chat(self, msg, cancelled=None):
                if msg == "A":
                    gate_a.wait(timeout=2.0)
                    return "A_done"
                if msg == "B":
                    gate_b.wait(timeout=2.0)
                    return "B_done"
                return f"{msg}_done"

        web_server.agent = MockAgent()

        t_a = asyncio.create_task(web_server.run_chat("A"))
        await asyncio.sleep(0.05)
        self.assertTrue(listener.is_paused)
        self.assertEqual(calls, ["pause"])

        t_b = asyncio.create_task(web_server.run_chat("B"))
        await asyncio.sleep(0.05)
        gate_a.set()
        try:
            await t_a
        except (asyncio.CancelledError, Exception):
            pass
        # A exited while B is STILL running -> listener must stay paused!
        self.assertTrue(listener.is_paused)
        self.assertEqual(calls, ["pause"])

        # C preempts B
        t_c = asyncio.create_task(web_server.run_chat("C"))
        await asyncio.sleep(0.05)
        gate_b.set()
        try:
            await t_b
        except (asyncio.CancelledError, Exception):
            pass
        res_c = await t_c
        self.assertEqual(res_c["reply"], "C_done")
        for job in list(web_server.get_active_chat_jobs()):
            job.wait(timeout=1.5)
        await asyncio.sleep(0.02)
        # After A, B, and C have all finished -> exactly 1 resume!
        self.assertFalse(listener.is_paused)
        self.assertEqual(calls, ["pause", "resume"])

    async def test_b_exception_or_tts_failure_still_resumes_listener(self):
        listener, calls = self._make_listener()
        web_server.listener = listener
        gate_a = threading.Event()

        class FailingAgent:
            def chat(self, msg, cancelled=None):
                if msg == "A":
                    gate_a.wait(timeout=1.0)
                    return "A"
                raise RuntimeError("TTS synthetic exception")

        web_server.agent = FailingAgent()
        t_a = asyncio.create_task(web_server.run_chat("A"))
        await asyncio.sleep(0.04)
        t_b = asyncio.create_task(web_server.run_chat("B"))
        await asyncio.sleep(0.04)
        gate_a.set()
        for t in (t_a, t_b):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        for job in list(web_server.get_active_chat_jobs()):
            job.wait(timeout=1.5)
        await asyncio.sleep(0.02)
        self.assertFalse(listener.is_paused)
        self.assertEqual(calls, ["pause", "resume"])

    async def test_external_music_or_manual_stop_never_overridden(self):
        listener, calls = self._make_listener(initially_paused=True, listening=False, music_suspended=True)
        web_server.listener = listener

        class OkAgent:
            def chat(self, msg, cancelled=None):
                return "ok"

        web_server.agent = OkAgent()
        res = await web_server.run_chat("hi")
        self.assertEqual(res["reply"], "ok")
        self.assertTrue(listener.is_paused)
        self.assertEqual(calls, [])


class F09F10KurisuAgentUnifiedSpeechTests(unittest.TestCase):
    def test_f09_shortcut_does_not_block_chat_lock_during_tts(self):
        with _tmp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "f09.sqlite3")
            try:
                speech_entered = threading.Event()
                speech_release = threading.Event()
                spoken_texts = []

                class BlockingVoice(SilentVoice):
                    def speak(self, text, block=True, to_board=True, cancelled=None):
                        spoken_texts.append(text)
                        if "我记住了" in text:
                            speech_entered.set()
                            for _ in range(200):
                                if (cancelled and cancelled.is_set()) or speech_release.is_set():
                                    break
                                time.sleep(0.01)

                agent = KurisuAgent(controller=SimulatedController(), voice=BlockingVoice(), memory=store)
                agent.semantic.plan = lambda text, ctx=(): {"kind": "clarify", "actions": []}

                t1 = threading.Thread(target=lambda: agent.chat("请记住：今天做实验"))
                t1.start()
                self.assertTrue(speech_entered.wait(timeout=1.5))

                # While t1 shortcut is blocked in voice.speak(), t2 must acquire _chat_lock fast!
                t0 = time.monotonic()
                res2 = agent.chat("帮我")
                elapsed = time.monotonic() - t0
                speech_release.set()
                t1.join(timeout=2.0)

                self.assertLess(elapsed, 0.5, f"t2 blocked for {elapsed}s on t1 shortcut TTS lock!")
                self.assertIn("请说清想要哪一种灯效", res2)
            finally:
                store.close()

    def test_f10_semantic_planner_exception_still_executes_speech(self):
        with _tmp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "f10.sqlite3")
            try:
                spoken = []

                class CaptureVoice(SilentVoice):
                    def speak(self, text, block=True, to_board=True, cancelled=None):
                        spoken.append(text)

                agent = KurisuAgent(controller=SimulatedController(), voice=CaptureVoice(), memory=store)

                def broken_plan(text, ctx=()):
                    raise TimeoutError("planner timeout")

                agent.semantic.plan = broken_plan
                reply = agent.chat("红莉栖打开蓝灯", speak=True)
                self.assertIn("控制意图暂时无法确认", reply)
                self.assertIn("planner timeout", agent.last_model_error)
                self.assertEqual(len(spoken), 1, "Fallback reply after semantic error MUST be spoken!")
            finally:
                store.close()


class F01F11F13NetworkAndSecurityTests(unittest.IsolatedAsyncioTestCase):
    def test_f11_windows_and_posix_subnet_parsing_excludes_vpn_and_finds_hotspots(self):
        win_sample = """
Windows IP Configuration

Ethernet adapter Radmin VPN:

   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 26.59.0.60
   Subnet Mask . . . . . . . . . . . : 255.0.0.0

Ethernet adapter 以太网:

   Media State . . . . . . . . . . . : Media disconnected

Ethernet adapter vEthernet (WSL):

   IPv4 Address. . . . . . . . . . . : 172.25.160.1
   Subnet Mask . . . . . . . . . . . : 255.255.240.0

Wireless LAN adapter WLAN:

   IPv4 Address. . . . . . . . . . . : 172.20.10.3
   Subnet Mask . . . . . . . . . . . : 255.255.255.240
   Default Gateway . . . . . . . . . : 172.20.10.1
"""
        nets = _parse_windows_ipconfig(win_sample)
        self.assertEqual(nets, [ipaddress.ip_network("172.20.10.0/28")])

        posix_sample = (
            "1: lo    inet 127.0.0.1/8 scope host lo\n"
            "2: tun0  inet 10.8.0.2/24 scope global tun0\n"
            "3: wlan0 inet 192.168.43.15/24 brd 192.168.43.255 scope global wlan0\n"
        )
        posix_nets = _parse_posix_ip_addr(posix_sample)
        self.assertEqual(posix_nets, [ipaddress.ip_network("192.168.43.0/24")])

    def test_f13_discovery_matches_app_policy_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KURISU_TRUST_PRIVATE", None)
            self.assertTrue(resolve_trust_private())
            app = web_server.create_app(simulate=True, no_audio=True)
            adv = service_discovery.ServiceAdvertisement(
                pairing_required=not app["access_policy"].trust_private
            )
            payload = json.loads(adv._build_discovery_payload("192.168.43.20", "192.168.43.1", 8080))
            self.assertEqual(payload["pairing_required"], not app["access_policy"].trust_private)
            self.assertFalse(payload["pairing_required"])

        with patch.dict(os.environ, {"KURISU_TRUST_PRIVATE": "0"}):
            self.assertFalse(resolve_trust_private())
            app_locked = web_server.create_app(simulate=True, no_audio=True)
            adv_locked = service_discovery.ServiceAdvertisement(
                pairing_required=not app_locked["access_policy"].trust_private
            )
            payload_locked = json.loads(adv_locked._build_discovery_payload("192.168.43.20", "192.168.43.1", 8080))
            self.assertTrue(payload_locked["pairing_required"])

    async def test_f01_hotspot_graded_access_and_scoped_vision_capability(self):
        app = web_server.create_app(simulate=True, no_audio=True)
        async with TestServer(app) as server:
            async with TestClient(server) as client:
                policy = app["access_policy"]
                # Make loopback look like a remote hotspot peer ("192.168.43.22") on trusted active subnet
                with patch.object(policy, "local", return_value=False), \
                     patch.object(AccessPolicy, "is_trusted_peer", return_value=True):
                    # 1. Ordinary controls work without token: status, GET library, POST music, POST chat
                    self.assertEqual((await client.get("/api/pro/status")).status, 200)
                    self.assertEqual((await client.get("/api/pro/library")).status, 200)
                    self.assertNotEqual((await client.post("/api/pro/music", json={"stop": True})).status, 401)

                    # 2. Sensitive paths strictly return 401 without admin token or scoped capability
                    for sens_method, sens_path, body in [
                        ("GET", "/api/pro/memory", None),
                        ("POST", "/api/pro/documents", {"text": "secret"}),
                        ("POST", "/api/pro/library", {"action": "scan"}),
                        ("POST", "/api/pro/enroll", {"name": "attacker"}),
                        ("POST", "/api/pro/camera/frame", b"fakejpeg"),
                        ("POST", "/api/pro/vision/frame", b"fakejpeg"),
                        ("GET", "/api/pro/camera/feed", None),
                        ("POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                    ]:
                        resp = await client.request(sens_method, sens_path, data=body if isinstance(body, bytes) else None, json=body if isinstance(body, dict) else None)
                        self.assertEqual(resp.status, 401, f"{sens_method} {sens_path} leaked without token!")

                    # 3. Cross-site Origin forbidden (403)
                    bad_origin = await client.post("/api/pro/vision", json={"enabled": True}, headers={"Origin": "https://evil.example"})
                    self.assertEqual(bad_origin.status, 403)

                    # 4. Scoped vision capability issued on active session cannot be abused for memory or mismatched session
                    vtok = policy.issue_vision_capability("remote_sess_1", "127.0.0.1", source="remote")
                    # Memory with vision token -> STILL 401!
                    self.assertEqual(
                        (await client.get("/api/pro/memory", headers={"Authorization": f"Bearer {vtok}"})).status,
                        401,
                    )
                    # Frame upload with matching session & vision token -> reaches handler (400 empty/no remote sim rather than 401!)
                    resp_frame = await client.post(
                        "/api/pro/camera/frame?session_id=remote_sess_1",
                        headers={"X-Vision-Token": vtok, "X-Vision-Session": "remote_sess_1"},
                        data=b"abc",
                    )
                    self.assertNotEqual(resp_frame.status, 401)
                    # Wrong session_id with valid token -> 401!
                    resp_wrong_sess = await client.post(
                        "/api/pro/camera/frame?session_id=remote_sess_OTHER",
                        headers={"X-Vision-Token": vtok, "X-Vision-Session": "remote_sess_OTHER"},
                        data=b"abc",
                    )
                    self.assertEqual(resp_wrong_sess.status, 401)
                    # Revoked after stop -> 401!
                    policy.revoke_vision_capability("remote_sess_1")
                    resp_revoked = await client.post(
                        "/api/pro/camera/frame?session_id=remote_sess_1",
                        headers={"X-Vision-Token": vtok, "X-Vision-Session": "remote_sess_1"},
                        data=b"abc",
                    )
                    self.assertEqual(resp_revoked.status, 401)


class F04F05VisionConcurrencyAndCalibrationTests(unittest.TestCase):
    def test_f04_concurrent_mediapipe_process_and_close_never_race(self):
        import cv2
        import mediapipe as mp

        ctrl = SimulatedController()
        ctrl.port = "COM9"
        hub = MultimodalHub(ctrl)
        sess_id = hub.start_remote(mode="pet")

        state = {"active_infer": 0, "max_infer": 0, "closed_while_infer": False, "closed_count": 0}
        lock = threading.Lock()
        infer_entered = threading.Event()
        infer_release = threading.Event()

        class FakeHands:
            def process(self, rgb):
                with lock:
                    state["active_infer"] += 1
                    state["max_infer"] = max(state["max_infer"], state["active_infer"])
                infer_entered.set()
                infer_release.wait(timeout=1.5)
                with lock:
                    state["active_infer"] -= 1
                return types.SimpleNamespace(multi_hand_landmarks=None)

            def close(self):
                with lock:
                    if state["active_infer"] > 0:
                        state["closed_while_infer"] = True
                    state["closed_count"] += 1

        class FakeFace:
            def process(self, rgb):
                return types.SimpleNamespace(multi_face_landmarks=None)

            def close(self):
                pass

        # Encode a tiny valid 32x32 JPEG
        ok, buf = cv2.imencode(".jpg", np.zeros((32, 32, 3), dtype=np.uint8))
        self.assertTrue(ok)
        jpg = buf.tobytes()

        fake_mp_solutions = types.SimpleNamespace(
            hands=types.SimpleNamespace(Hands=lambda **kw: FakeHands(), HAND_CONNECTIONS=[]),
            face_mesh=types.SimpleNamespace(FaceMesh=lambda **kw: FakeFace()),
            drawing_utils=types.SimpleNamespace(draw_landmarks=lambda *a, **k: None),
        )
        results = []
        with patch.object(mp, "solutions", fake_mp_solutions):
            # 1. Start frame 1 -> blocks inside FakeHands.process()
            t1 = threading.Thread(target=lambda: results.append(hub.process_remote_frame(jpg, session_id=sess_id)))
            t1.start()
            self.assertTrue(infer_entered.wait(timeout=2.0))

            # 2. Frame 2 arrives concurrently while frame 1 is in MediaPipe process()
            t2 = threading.Thread(target=lambda: results.append(hub.process_remote_frame(jpg, session_id=sess_id)))
            t2.start()

            # 3. Third frame overflows MAX_REMOTE_PENDING_FRAMES=2 and drops cleanly instead of piling up
            time.sleep(0.05)
            overflow_res = hub.process_remote_frame(jpg, session_id=sess_id)
            self.assertTrue(overflow_res.get("dropped"))

            # 4. stop_remote() called WHILE t1 is still inside FakeHands.process()
            hub.stop_remote(sess_id)
            # FakeHands.close MUST NOT be called while active_infer > 0!
            self.assertFalse(state["closed_while_infer"])

            infer_release.set()
            t1.join(timeout=2.0)
            t2.join(timeout=2.0)

        self.assertEqual(state["max_infer"], 1, "MediaPipe .process() must NEVER run concurrently!")
        self.assertFalse(state["closed_while_infer"], ".close() must NEVER race with active .process()!")
        self.assertEqual(state["closed_count"], 1, "Detached MediaPipe handle must close cleanly after release!")

    def test_f05_gaze_calibration_invalidated_across_camera_or_rotation_switch(self):
        ctrl = SimulatedController()
        ctrl.port = "COM9"
        hub = MultimodalHub(ctrl)
        samples = [
            [0.2, 0.2, 0.1, 0.1],
            [0.8, 0.2, 0.9, 0.1],
            [0.2, 0.8, 0.1, 0.9],
            [0.8, 0.8, 0.9, 0.9],
            [0.5, 0.5, 0.5, 0.5],
        ]
        # Calibrate on PC camera (0, rot=0)
        prof_cam0 = hub.current_calibration_profile(source="camera", camera_id=0, rotation=0, mirrored=True)
        hub.features.gaze.fit(samples, profile=prof_cam0)

        ctrl.mode = 32
        with patch("arcade_runner.get_arcade_session", return_value=types.SimpleNamespace(status={"game_id": 33})):
            # Switch to phone remote camera -> old PC calibration MUST NOT silently apply to gaze_game!
            with self.assertRaises(ValueError) as ctx:
                hub.start_remote(mode="gaze_game", rotation=90)
            self.assertIn("校准", str(ctx.exception))

            # Recalibrate specifically for remote rotation=90
            prof_phone90 = hub.current_calibration_profile(source="remote", rotation=90, mirrored=True)
            hub.features.gaze.fit(samples, profile=prof_phone90)
            sid = hub.start_remote(mode="gaze_game", rotation=90)
            self.assertTrue(hub.started)
            self.assertTrue(hub.status()["calibration_valid"])

            # Rotate phone to 0 -> compatibility check marks calibration invalid
            hub.input_rotation = 0
            st = hub.status()
            self.assertFalse(st["calibration_valid"])
            self.assertIn("rotation", st["calibration_invalidated_reason"])
            hub.stop_remote(sid)

    def test_f04_camera_source_switch_ack_propagation_and_hand_loss(self):
        import cv2
        import mediapipe as mp

        class AckTrackingController(SimulatedController):
            def __init__(self, ack_ok=True):
                super().__init__()
                self.port = "COM9"
                self.ack_ok = ack_ok
                self.sent_cmds = []

            def send_json(self, payload):
                self.sent_cmds.append(dict(payload))
                if not self.ack_ok:
                    return False
                return super().send_json(payload)

            def track(self, x, y, present, count=1):
                self.sent_cmds.append({"cmd": "track", "x": x, "y": y, "present": present, "count": count})
                if not self.ack_ok:
                    return False
                return super().track(x, y, present, count)

        ctrl = AckTrackingController(ack_ok=True)
        hub = MultimodalHub(ctrl)
        sid = hub.start_remote(mode="fingertip")
        self.assertTrue(hub.status()["device_command_acknowledged"])

        lm_list = [types.SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
        frame_calls = {"n": 0}

        class SwitchingHands:
            def process(self, rgb):
                frame_calls["n"] += 1
                if frame_calls["n"] == 1:
                    return types.SimpleNamespace(multi_hand_landmarks=[types.SimpleNamespace(landmark=lm_list)])
                return types.SimpleNamespace(multi_hand_landmarks=None)

            def close(self):
                pass

        class FakeFace:
            def process(self, rgb):
                return types.SimpleNamespace(multi_face_landmarks=None)

            def close(self):
                pass

        ok, buf = cv2.imencode(".jpg", np.zeros((32, 32, 3), dtype=np.uint8))
        self.assertTrue(ok)
        jpg = buf.tobytes()

        fake_mp_solutions = types.SimpleNamespace(
            hands=types.SimpleNamespace(Hands=lambda **kw: SwitchingHands(), HAND_CONNECTIONS=[]),
            face_mesh=types.SimpleNamespace(FaceMesh=lambda **kw: FakeFace()),
            drawing_utils=types.SimpleNamespace(draw_landmarks=lambda *a, **k: None),
        )
        with patch.object(mp, "solutions", fake_mp_solutions):
            # 1. Hand present while board NACKs -> device_command_acknowledged must be False!
            ctrl.ack_ok = False
            res1 = hub.process_remote_frame(jpg, session_id=sid)
            self.assertFalse(res1.get("dropped"))
            self.assertFalse(hub.status()["device_command_acknowledged"])

            # 2. Board recovers ACK -> hand lost frame releases track (present=False, count=0) and recovers ACK=True
            ctrl.ack_ok = True
            res2 = hub.process_remote_frame(jpg, session_id=sid)
            self.assertFalse(res2.get("dropped"))
            st2 = hub.status()
            self.assertFalse(st2.get("hand"))
            self.assertTrue(st2["device_command_acknowledged"])
            track_cmds = [c for c in ctrl.sent_cmds if c.get("cmd") == "track" and "present" in c]
            self.assertGreaterEqual(len(track_cmds), 2)
            self.assertTrue(track_cmds[0]["present"])
            self.assertFalse(track_cmds[-1]["present"])
            hub.stop_remote(sid)
            self.assertFalse(hub.status()["running"])

        # 3. Switching back from remote to PC local camera (mocked VideoCapture failure-safe open) clears remote state
        class FakeCap:
            def isOpened(self):
                return True

            def set(self, *a):
                return True

            def read(self):
                return False, None

            def release(self):
                pass

        with patch("cv2.VideoCapture", return_value=FakeCap()), patch.object(mp, "solutions", fake_mp_solutions):
            hub.start(mode="pet", camera=0)
            self.assertEqual(hub.status()["source"], "camera")
            hub.stop()
            self.assertFalse(hub.status()["running"])


class F08MusicChatAlternationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.orig_listener = web_server.listener
        self.orig_agent = web_server.agent
        self.orig_voice = web_server.voice
        self.orig_pro = web_server.pro_api
        self.orig_coordinator = web_server.chat_pause_coordinator
        web_server.shutting_down = False
        web_server.pro_api = None
        web_server.voice = SilentVoice()

    async def asyncTearDown(self):
        web_server.shutting_down = False
        web_server.listener = self.orig_listener
        web_server.agent = self.orig_agent
        web_server.voice = self.orig_voice
        web_server.pro_api = self.orig_pro
        web_server.chat_pause_coordinator = self.orig_coordinator

    async def test_music_and_chat_alternation_keeps_music_paused_and_resumes_listener(self):
        calls = []

        class StubListener:
            def __init__(self):
                self.is_paused = True
                self.is_listening = True
                self._music_suspended = True

            def pause(self):
                self.is_paused = True
                self.is_listening = False
                calls.append("pause")

            def resume(self):
                self.is_paused = False
                self.is_listening = True
                calls.append("resume")

        web_server.listener = StubListener()
        web_server.chat_pause_coordinator = web_server.ChatPauseCoordinator()

        class QuickAgent:
            def chat(self, msg, cancelled=None):
                return f"reply:{msg}"

        web_server.agent = QuickAgent()
        res = await web_server.run_chat("你好")
        self.assertEqual(res["reply"], "reply:你好")
        # Because _music_suspended was True before chat, listener MUST stay paused and NOT resume over playing music!
        self.assertTrue(web_server.listener.is_paused)
        self.assertEqual(calls, [])


class F09F10BilingualAndNackTests(unittest.TestCase):
    def test_hardware_nack_and_chinese_first_japanese_fallback(self):
        with _tmp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "nack.sqlite3")
            try:
                spoken = []

                class CaptureVoice(SilentVoice):
                    def __init__(self):
                        super().__init__()
                        self.bilingual_mode = "chinese_first"

                    def speak(self, text, block=True, to_board=True, cancelled=None):
                        spoken.append((text, to_board))

                ctrl = SimulatedController()
                ctrl.port = "COM9"
                ctrl.command_result = lambda payload: {"status": "error", "error": "hardware_nack"}
                agent = KurisuAgent(controller=ctrl, voice=CaptureVoice(), memory=store)
                # Explicit device NACK on mode command must NOT pretend success
                reply = agent.chat("帮我打开星空模式", speak=True)
                self.assertTrue(spoken, "NACK/error reply must still be spoken")
                self.assertNotIn("已切换为星空模式，你可以", reply)

                # Explicit negative non-command ("别开灯") must NOT switch controller on
                sent_modes = []
                ctrl2 = SimulatedController()
                ctrl2.command_result = lambda p: (sent_modes.append(p), {"status": "ok"})[1]
                agent2 = KurisuAgent(controller=ctrl2, voice=CaptureVoice(), memory=store)
                agent2.semantic.plan = lambda text, ctx=(): {"kind": "chat", "actions": []}
                agent2.chat("别开灯，我们只是聊聊天", speak=True)
                self.assertEqual([c for c in sent_modes if c.get("cmd") == "mode"], [])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
