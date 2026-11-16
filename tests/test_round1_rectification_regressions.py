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


class Round2TargetedPatchTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _make_jpg(w=64, h=48):
        import cv2
        ok, buf = cv2.imencode(".jpg", np.zeros((h, w, 3), dtype=np.uint8))
        assert ok
        return buf.tobytes()

    @staticmethod
    def _make_face_landmarks():
        pts = [types.SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(478)]
        # Give left/right eye corners, eyelids, mouth, and iris valid non-degenerate separation
        coords = {
            33: (0.35, 0.40), 133: (0.45, 0.40), 159: (0.40, 0.37), 145: (0.40, 0.43), 468: (0.40, 0.40),
            362: (0.55, 0.40), 263: (0.65, 0.40), 386: (0.60, 0.37), 374: (0.60, 0.43), 473: (0.60, 0.40),
            61: (0.42, 0.65), 291: (0.58, 0.65), 13: (0.50, 0.64), 14: (0.50, 0.66),
            70: (0.35, 0.33), 300: (0.65, 0.33), 1: (0.50, 0.50), 152: (0.50, 0.78),
        }
        for idx, (x, y) in coords.items():
            pts[idx] = types.SimpleNamespace(x=x, y=y, z=0.0)
        return pts

    async def test_r1_01_and_r1_02_per_frame_ack_isolation_and_scoped_camera_get(self):
        import mediapipe as mp

        app = web_server.create_app(simulate=True, no_audio=True)
        async with TestServer(app) as server:
            async with TestClient(server) as client:
                policy = app["access_policy"]
                pro = app.get("pro_api") or web_server.pro_api
                # Replace controller with deterministic non-SIMULATION board stub whose ACK can be toggled
                class FakeCtrl(SimulatedController):
                    def __init__(self):
                        super().__init__()
                        self.port = "COM9"
                        self.ack_ok = True
                        self.fail_on_call_n = None
                        self.track_calls = 0

                    def send_json(self, payload):
                        return bool(self.ack_ok)

                    def track(self, x, y, present, count=1):
                        self.track_calls += 1
                        if self.fail_on_call_n is not None and self.track_calls >= self.fail_on_call_n:
                            return False
                        return bool(self.ack_ok)

                fake_ctrl = FakeCtrl()
                pro.controller = fake_ctrl
                pro.vision.controller = fake_ctrl
                hub = pro.vision

                face_lms = self._make_face_landmarks()
                hand_lms = [types.SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
                state = {"include_hand": True}

                class StubHands:
                    def process(self, rgb):
                        if state["include_hand"]:
                            return types.SimpleNamespace(multi_hand_landmarks=[types.SimpleNamespace(landmark=hand_lms)])
                        return types.SimpleNamespace(multi_hand_landmarks=None)

                    def close(self):
                        pass

                class StubFace:
                    def process(self, rgb):
                        return types.SimpleNamespace(multi_face_landmarks=[types.SimpleNamespace(landmark=face_lms)])

                    def close(self):
                        pass

                fake_mp = types.SimpleNamespace(
                    hands=types.SimpleNamespace(Hands=lambda **kw: StubHands(), HAND_CONNECTIONS=[]),
                    face_mesh=types.SimpleNamespace(FaceMesh=lambda **kw: StubFace()),
                    drawing_utils=types.SimpleNamespace(draw_landmarks=lambda *a, **k: None),
                )
                jpg = self._make_jpg()

                with patch.object(mp, "solutions", fake_mp):
                    # Emulate trusted hotspot peer IP ("172.20.10.5")
                    with patch.object(policy, "local", return_value=False), \
                         patch.object(AccessPolicy, "is_trusted_peer", return_value=True):
                        # Unauthenticated LAN GET /api/pro/camera/frame & /feed -> 401
                        self.assertEqual((await client.get("/api/pro/camera/frame")).status, 401)
                        self.assertEqual((await client.get("/api/pro/camera/feed")).status, 401)

                        # 1. Start remote session in fingertip mode (issues scoped vision_token)
                        start_resp = await client.post("/api/pro/vision", json={"enabled": True, "source": "remote", "mode": "fingertip"})
                        self.assertEqual(start_resp.status, 200)
                        start_data = await start_resp.json()
                        sid = start_data["session_id"]
                        vtok = start_data["vision_token"]
                        self.assertTrue(sid and vtok)

                        # Frame N: fingertip mode sends track() and ACK=True
                        resp_n = await client.post(
                            f"/api/pro/camera/frame?session_id={sid}",
                            headers={"X-Vision-Token": vtok, "X-Vision-Session": sid, "X-Vision-Mode": "fingertip"},
                            data=jpg,
                        )
                        self.assertEqual(resp_n.status, 200)
                        body_n = await resp_n.json()
                        self.assertTrue(body_n["device_command_attempted"])
                        self.assertTrue(body_n["device_command_acknowledged"])

                        # R1-02: GET /api/pro/camera/frame with valid scoped token + session -> 200 JPEG!
                        get_ok = await client.get(
                            f"/api/pro/camera/frame?session_id={sid}",
                            headers={"X-Vision-Token": vtok},
                        )
                        self.assertEqual(get_ok.status, 200)
                        self.assertEqual(get_ok.headers["Content-Type"], "image/jpeg")
                        self.assertGreater(len(await get_ok.read()), 0)

                        # Wrong session_id / missing session_id / sensitive endpoints with vision token -> 401!
                        self.assertEqual(
                            (await client.get("/api/pro/camera/frame", headers={"X-Vision-Token": vtok})).status,
                            401,
                        )
                        self.assertEqual(
                            (await client.get(f"/api/pro/camera/frame?session_id=wrong", headers={"X-Vision-Token": vtok, "X-Vision-Session": "wrong"})).status,
                            401,
                        )
                        self.assertEqual(
                            (await client.get("/api/pro/memory", headers={"Authorization": f"Bearer {vtok}"})).status,
                            401,
                        )

                        # R1-01 CRITICAL: Frame N+1 switches mode to 'pet' with face present -> sends ZERO hardware commands!
                        # It MUST NOT inherit Frame N's device_command_acknowledged=True!
                        state["include_hand"] = False
                        resp_n1 = await client.post(
                            f"/api/pro/camera/frame?session_id={sid}",
                            headers={"X-Vision-Token": vtok, "X-Vision-Session": sid, "X-Vision-Mode": "pet"},
                            data=jpg,
                        )
                        self.assertEqual(resp_n1.status, 200)
                        body_n1 = await resp_n1.json()
                        self.assertFalse(body_n1["device_command_attempted"], "pet frame sent 0 commands")
                        self.assertIsNone(body_n1["device_command_acknowledged"], "Must NOT inherit previous frame True ACK!")

                        # Frame N+2: fingertip mode with NACK -> device_command_acknowledged=False!
                        state["include_hand"] = True
                        fake_ctrl.ack_ok = False
                        resp_n2 = await client.post(
                            f"/api/pro/camera/frame?session_id={sid}",
                            headers={"X-Vision-Token": vtok, "X-Vision-Session": sid, "X-Vision-Mode": "fingertip"},
                            data=jpg,
                        )
                        body_n2 = await resp_n2.json()
                        self.assertTrue(body_n2["device_command_attempted"])
                        self.assertFalse(body_n2["device_command_acknowledged"])

                        # Multi-command aggregation inside one frame: 1st succeeds, 2nd fails -> frame ACK must be False!
                        hub._frame_cmd_ctx.current = {
                            "session_id": sid, "epoch": hub.session_epoch, "frame_seq": 99,
                            "attempted": False, "command_count": 0, "failed_count": 0,
                            "acknowledged": None, "error": None, "frame_meta": ("remote", sid, hub.session_epoch),
                        }
                        hub._record_device_command(True)
                        hub._record_device_command(False)
                        self.assertEqual(hub._frame_cmd_ctx.current["command_count"], 2)
                        self.assertFalse(hub._frame_cmd_ctx.current["acknowledged"])
                        hub._frame_cmd_ctx.current = None

                        # Stop session revokes capability -> GET /api/pro/camera/frame returns 401
                        await client.post("/api/pro/vision", json={"enabled": False, "source": "remote", "session_id": sid})
                        self.assertEqual(
                            (await client.get(f"/api/pro/camera/frame?session_id={sid}", headers={"X-Vision-Token": vtok})).status,
                            401,
                        )

    def test_r1_03_chat_pause_coordinator_handoff_race_and_bounded_history(self):
        class TrackedListener:
            def __init__(self):
                self.is_paused = False
                self.is_listening = True
                self._music_suspended = False
                self.calls = []
                self.resume_entered = threading.Event()
                self.resume_release = None

            def pause(self):
                self.calls.append("pause")
                self.is_paused = True

            def resume(self):
                self.calls.append("resume")
                if self.resume_release is not None:
                    self.resume_entered.set()
                    self.resume_release.wait(timeout=2.0)
                self.is_paused = False

        # Part 1: Turn A leaves release() _lock BEFORE acquiring _hw_lock -> Turn B enters prepare_pause()!
        coord = web_server.ChatPauseCoordinator()
        listener = TrackedListener()
        handoff_entered = threading.Event()
        handoff_release = threading.Event()

        def paused_handoff():
            handoff_entered.set()
            handoff_release.wait(timeout=2.0)

        coord._on_before_resume_handoff = paused_handoff
        owns_a, need_a = coord.prepare_pause(listener, 1)
        self.assertTrue(owns_a and need_a)
        coord.execute_pause(listener)
        self.assertTrue(listener.is_paused)

        res_a = []
        t_a = threading.Thread(target=lambda: res_a.append(coord.release(listener, 1)))
        t_a.start()
        self.assertTrue(handoff_entered.wait(timeout=1.5))

        # Turn B enters WHILE Turn A is between _lock and _hw_lock/resume()!
        owns_b, need_b = coord.prepare_pause(listener, 2)
        self.assertTrue(owns_b, "Turn B MUST NOT misdiagnose in-flight handoff as external pause!")
        self.assertFalse(need_b, "Listener is already paused; Turn A resume was cancelled")

        # Release Turn A -> Turn A MUST NOT call listener.resume() while Turn B owns pause!
        handoff_release.set()
        t_a.join(timeout=2.0)
        self.assertEqual(res_a, [False])
        self.assertTrue(listener.is_paused)
        self.assertEqual(listener.calls, ["pause"])

        # Turn B completes -> NOW listener resumes exactly once
        coord._on_before_resume_handoff = lambda: None
        self.assertTrue(coord.release(listener, 2))
        self.assertFalse(listener.is_paused)
        self.assertEqual(listener.calls, ["pause", "resume"])

        # Part 2: Turn A ALREADY inside slow listener.resume() while Turn B calls prepare_pause() -> serializes pause behind resume without deadlock!
        listener2 = TrackedListener()
        listener2.resume_release = threading.Event()
        coord2 = web_server.ChatPauseCoordinator()
        coord2.prepare_pause(listener2, 10)
        coord2.execute_pause(listener2)

        t_a2 = threading.Thread(target=lambda: coord2.release(listener2, 10))
        t_a2.start()
        self.assertTrue(listener2.resume_entered.wait(timeout=1.5))

        owns_b2, need_b2 = coord2.prepare_pause(listener2, 11)
        self.assertTrue(owns_b2 and need_b2, "Active in-flight resume requires Turn B to re-pause behind _hw_lock")

        b2_paused = threading.Event()

        def run_b2_pause():
            coord2.execute_pause(listener2)
            b2_paused.set()

        t_b2 = threading.Thread(target=run_b2_pause)
        t_b2.start()
        time.sleep(0.05)
        self.assertFalse(b2_paused.is_set(), "Turn B pause cleanly waits on _hw_lock for Turn A resume")
        listener2.resume_release.set()
        t_a2.join(timeout=2.0)
        t_b2.join(timeout=2.0)
        self.assertTrue(b2_paused.is_set())
        self.assertTrue(listener2.is_paused, "After handoff completes, Turn B owns an actively paused listener!")

        listener2.resume_release = None
        self.assertTrue(coord2.release(listener2, 11))
        self.assertFalse(listener2.is_paused)
        self.assertEqual(listener2.calls, ["pause", "resume", "pause", "resume"])

        # Part 3: Repeated releases remain bounded (<= MAX_RETIRED_TURNS)
        listener3 = TrackedListener()
        coord3 = web_server.ChatPauseCoordinator()
        for tid in range(1, 501):
            coord3.prepare_pause(listener3, tid)
            coord3.release(listener3, tid)
        self.assertLessEqual(len(coord3._released_turns), coord3.MAX_RETIRED_TURNS)

    def test_r1_04_f05_mirrored_false_vs_true_rotation_geometry_and_cross_source(self):
        import mediapipe as mp

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

        face_lms = self._make_face_landmarks()
        jpg_64x48 = self._make_jpg(64, 48)

        class StubHands:
            def process(self, rgb):
                return types.SimpleNamespace(multi_hand_landmarks=None)

            def close(self):
                pass

        class StubFace:
            def process(self, rgb):
                return types.SimpleNamespace(multi_face_landmarks=[types.SimpleNamespace(landmark=face_lms)])

            def close(self):
                pass

        fake_mp = types.SimpleNamespace(
            hands=types.SimpleNamespace(Hands=lambda **kw: StubHands(), HAND_CONNECTIONS=[]),
            face_mesh=types.SimpleNamespace(FaceMesh=lambda **kw: StubFace()),
            drawing_utils=types.SimpleNamespace(draw_landmarks=lambda *a, **k: None),
        )

        # 1. Calibrate specifically for remote mirrored=True, rotation=0
        prof_mir = hub.current_calibration_profile(source="remote", rotation=0, mirrored=True, width=64, height=48)
        self.assertTrue(prof_mir["mirrored"])
        hub.features.gaze.fit(samples, profile=prof_mir)

        ctrl.mode = 32
        with patch("arcade_runner.get_arcade_session", return_value=types.SimpleNamespace(status={"game_id": 33})), \
             patch.object(mp, "solutions", fake_mp):
            # 2. Switch to remote with mirrored=False -> old mirrored=True calibration MUST fail & observation["calibrated"]==False!
            sid = hub.start_remote(mode="pet", rotation=0, mirrored=False)
            obs_non_mir = hub.process_remote_frame(jpg_64x48, session_id=sid, rotation=0, mirrored=False)
            self.assertFalse(obs_non_mir["calibrated"], "mirrored=False MUST NOT silently use mirrored=True calibration!")
            st = hub.status()
            self.assertFalse(st["calibration_valid"])
            self.assertIn("mirrored", st["calibration_invalidated_reason"])

            # Starting gaze_game with mismatched mirrored calibration must be rejected
            with self.assertRaises(ValueError):
                hub.start_remote(mode="gaze_game", rotation=0, mirrored=False)

            # 3. Calibrate specifically for remote mirrored=False, rotation=90 with geometry rotation applied (64x48 -> 48x64)
            ctrl.mode = 32
            prof_unmir_90 = hub.current_calibration_profile(source="remote", rotation=90, mirrored=False, width=48, height=64)
            self.assertFalse(prof_unmir_90["mirrored"])
            hub.features.gaze.fit(samples, profile=prof_unmir_90)
            sid2 = hub.start_remote(mode="gaze_game", rotation=90, mirrored=False)
            obs_rot90 = hub.process_remote_frame(
                jpg_64x48, session_id=sid2, rotation=90, mirrored=False, apply_rotation=True
            )
            self.assertEqual((hub.input_width, hub.input_height), (48, 64))
            self.assertTrue(obs_rot90["calibrated"])
            self.assertTrue(hub.status()["calibration_valid"])

            # Rotation change to 180 or 270 invalidates calibration
            obs_rot180 = hub.process_remote_frame(jpg_64x48, session_id=sid2, rotation=180, mirrored=False)
            self.assertFalse(obs_rot180["calibrated"])
            self.assertIn("rotation", hub.status()["calibration_invalidated_reason"])
            hub.stop_remote(sid2)

            # 4. Cross-source PC mirrored=True != phone mirrored=True
            ctrl.mode = 32
            prof_pc = hub.current_calibration_profile(source="camera", camera_id=0, rotation=0, mirrored=True)
            hub.features.gaze.fit(samples, profile=prof_pc)
            with self.assertRaises(ValueError):
                hub.start_remote(mode="gaze_game", rotation=0, mirrored=True)


if __name__ == "__main__":
    unittest.main()
