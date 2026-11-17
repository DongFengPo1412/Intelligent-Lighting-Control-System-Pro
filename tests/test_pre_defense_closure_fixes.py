import asyncio
import importlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

PC_DIR = Path(__file__).resolve().parents[1] / "pc-agent-vision"
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))


class PreDefenseClosureFixesTests(unittest.TestCase):
    def test_wifi_audio_connected_ignores_usb_serial_flag(self):
        from light_controller import LightController

        ctrl = LightController.__new__(LightController)
        ctrl.audio_transport = "wifi"
        ctrl.is_connected = True
        ctrl._network_audio = mock.SimpleNamespace(connected=False) if hasattr(mock, "SimpleNamespace") else type("NA", (), {"connected": False})()
        self.assertFalse(ctrl.audio_connected)

        ctrl._network_audio.connected = True
        self.assertTrue(ctrl.audio_connected)

        ctrl.audio_transport = "usb"
        ctrl._network_audio.connected = False
        self.assertTrue(ctrl.audio_connected)

    def test_usb_pair_bootstrap_saves_token_without_reset_or_secret_log(self):
        import wifi_gateway

        token = "a" * 64
        written = []

        class FakeSerial:
            def __init__(self):
                self.port = None
                self.baudrate = None
                self.timeout = None
                self.dtr = True
                self.rts = True
                self._opened = False
                self._dtr_before_open = None
                self._rts_before_open = None
                self._lines = []

            def open(self):
                self._dtr_before_open = self.dtr
                self._rts_before_open = self.rts
                self._opened = True

            def reset_input_buffer(self):
                pass

            def write(self, data):
                written.append(data)
                req = json.loads(data.decode("utf-8").strip())
                self._lines.append(b"I (12) log: boot noise\n")
                self._lines.append(
                    json.dumps(
                        {"request_id": req["request_id"], "status": "ok", "control_token": token}
                    ).encode("utf-8")
                    + b"\n"
                )

            def flush(self):
                pass

            def readline(self):
                return self._lines.pop(0) if self._lines else b""

            def close(self):
                pass

        fake_port = type("Port", (), {"device": "COM9", "vid": 0x303A, "pid": 0x1001, "description": "USB JTAG"})()
        fake_ser = FakeSerial()
        fake_serial_mod = type(
            "SerialMod",
            (),
            {
                "Serial": lambda *a, **kw: fake_ser,
                "tools": type("Tools", (), {"list_ports": type("LP", (), {"comports": staticmethod(lambda: [fake_port])})})(),
            },
        )()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            gw = wifi_gateway.WiFiGateway.__new__(wifi_gateway.WiFiGateway)
            gw.control_token = ""
            gw._pair_lock = threading.Lock()
            stdout_buf = io.StringIO()
            with mock.patch.dict(os.environ, {"KURISU_DATA_DIR": str(tmp_path)}, clear=False), \
                 mock.patch.dict(sys.modules, {"serial": fake_serial_mod, "serial.tools": fake_serial_mod.tools, "serial.tools.list_ports": fake_serial_mod.tools.list_ports}), \
                 mock.patch("sys.stdout", stdout_buf):
                ok = gw.bootstrap_usb_pairing(timeout=1.0)

            self.assertTrue(ok)
            self.assertEqual(gw.control_token, token)
            self.assertFalse(fake_ser._dtr_before_open)
            self.assertFalse(fake_ser._rts_before_open)
            cfg = tmp_path / "control-pairing.json"
            self.assertTrue(cfg.exists())
            self.assertEqual(json.loads(cfg.read_text(encoding="utf-8"))["control_token"], token)
            self.assertNotIn(token, stdout_buf.getvalue())

    def test_voice_engine_restores_board_led_on_playback_failure(self):
        from voice_engine import VoiceEngine

        eng = VoiceEngine.__new__(VoiceEngine)
        eng.chinese_first = False
        eng.last_tts_error = None
        eng.last_speech_timings = {}
        eng.synthesize_speech_bundle = lambda _t: (b"\x01\x00" * 100, b"RIFF")

        led_calls = []

        class FakeCtrl:
            audio_transport = "wifi"
            audio_connected = True
            _voice_listener = type("VL", (), {"is_awake": False})()

            def set_board_led(self, mode):
                led_calls.append(mode)
                return True

            def play_audio_pcm(self, _pcm, **_kw):
                return False

        fake_lc_mod = type("LC", (), {"get_light_controller": staticmethod(lambda: FakeCtrl())})()
        with mock.patch.dict(sys.modules, {"light_controller": fake_lc_mod}):
            eng.speak("hello", block=True, to_board=True)

        self.assertEqual(led_calls, ["speaking", "off"])

        led_calls.clear()
        fake_ctrl = FakeCtrl()
        fake_ctrl._voice_listener.is_awake = True
        fake_lc_mod2 = type("LC2", (), {"get_light_controller": staticmethod(lambda: fake_ctrl)})()
        with mock.patch.dict(sys.modules, {"light_controller": fake_lc_mod2}):
            eng.speak("hello again", block=True, to_board=True)

        self.assertEqual(led_calls, ["speaking", "listening"])

    def test_web_server_warmup_resets_led_off_on_unreachable_and_uses_90s_budget(self):
        web_server = importlib.import_module("web_server")
        led_calls = []
        seen_timeouts = []

        class FakeSemantic:
            model = "kurisu:latest"

            def warmup(self, timeout=120, abort_event=None):
                seen_timeouts.append(timeout)
                raise ConnectionRefusedError("11434 unreachable")

        fake_agent = type(
            "Agent",
            (),
            {
                "semantic": FakeSemantic(),
                "model_status": "unknown",
                "model_ready": False,
                "last_model_error": None,
                "model_recovery_guidance": None,
            },
        )()
        fake_ctrl = type("Ctrl", (), {"set_board_led": staticmethod(lambda m: led_calls.append(m) or True)})()
        app = {"warmup_abort_event": threading.Event(), "voice_startup_state": "warming_model"}

        loop = asyncio.new_event_loop()
        try:
            with mock.patch.object(web_server, "agent", fake_agent), \
                 mock.patch.object(web_server, "controller", fake_ctrl), \
                 mock.patch.object(web_server, "listener", None), \
                 mock.patch.object(web_server, "shutting_down", False):
                loop.run_until_complete(web_server.background_model_warmup(app, max_retries=1, initial_backoff=0.01))
        finally:
            loop.close()

        self.assertEqual(seen_timeouts, [90.0])
        self.assertEqual(fake_agent.model_status, "unreachable")
        self.assertEqual(led_calls[-1], "off")

    def test_wifi_pcm_play_stream_waits_for_delayed_hardware_playback_confirmation(self):
        from network_audio import WiFiPcmClient

        ctrl = type(
            "Ctrl",
            (),
            {
                "_mic_enabled": False,
                "playback_started_at": 0.0,
                "enable_mic": staticmethod(lambda _en: True),
            },
        )()
        client = WiFiPcmClient(ctrl)
        client.connect = lambda: True
        client._send = lambda *_a, **_kw: None

        status_seq = iter([
            {"status": "ok", "audio_rx": 100, "audio_played": 100, "audio_dropped": 0, "audio_errors": 0},
            {"status": "ok", "audio_rx": 100, "audio_played": 100, "audio_dropped": 0, "audio_errors": 0},
            {"status": "ok", "audio_rx": 612, "audio_played": 612, "audio_dropped": 0, "audio_errors": 0},
        ])
        ctrl.command_result = lambda _cmd: next(status_seq)

        ok = client.play_stream(iter([b"\x01\x00" * 512]), chunk_samples=512)
        self.assertTrue(ok)
        self.assertIsNone(client.last_error)

    def test_trusted_hotspot_allows_get_pro_frame_without_pairing_token(self):
        from access_control import AccessPolicy

        policy = AccessPolicy(token="t" * 32, trust_private=True)
        get_frame_req = type(
            "Req",
            (),
            {"remote": "192.168.8.146", "host": "192.168.8.90:8080", "path": "/api/pro/frame", "method": "GET", "headers": {}, "query": {}, "cookies": {}},
        )()
        get_settings_req = type(
            "Req2",
            (),
            {"remote": "192.168.8.146", "host": "192.168.8.90:8080", "path": "/api/pro/settings", "method": "GET", "headers": {}, "query": {}, "cookies": {}},
        )()
        with mock.patch.object(AccessPolicy, "is_trusted_peer", return_value=True):
            self.assertTrue(policy.authorized(get_frame_req))
            self.assertFalse(policy.authorized(get_settings_req))

    def test_play_stream_retries_before_status_and_transient_send_drop(self):
        from network_audio import WiFiPcmClient

        sent = []
        calls = {"connect": 0, "send": 0}
        ctrl = type(
            "Ctrl",
            (),
            {
                "_mic_enabled": False,
                "playback_started_at": 0.0,
                "enable_mic": staticmethod(lambda _en: True),
            },
        )()
        client = WiFiPcmClient(ctrl)

        def fake_connect():
            calls["connect"] += 1
            return True

        def fake_send(_kind, data):
            calls["send"] += 1
            if calls["send"] == 1:
                raise OSError("transient drop")
            sent.append(data)

        status_seq = iter([
            {"status": "error", "error": "ack_timeout"},
            {"status": "ok", "audio_rx": 0, "audio_played": 0, "audio_dropped": 0, "audio_errors": 0},
            {"status": "ok", "audio_rx": 512, "audio_played": 512, "audio_dropped": 0, "audio_errors": 0},
        ])
        ctrl.command_result = lambda _cmd: next(status_seq)
        client.connect = fake_connect
        client.close = lambda: None
        client._send = fake_send

        ok = client.play_stream(iter([b"\x01\x00" * 512]), chunk_samples=512)
        self.assertTrue(ok)
        self.assertEqual(calls["connect"], 2)
        self.assertEqual(len(b"".join(sent)), 1024)

    def test_stage_c_semantic_negation_hypothetical_and_short_color_fastpath(self):
        from semantic_control import SemanticControl

        planner = SemanticControl()
        self.assertEqual(
            planner.plan("开蓝灯"),
            {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 2}]},
        )
        self.assertEqual(planner.plan("不要开灯。"), {"kind": "chat", "actions": []})
        self.assertEqual(planner.plan("如果打开蓝灯会怎么样？"), {"kind": "chat", "actions": []})
        self.assertEqual(planner.plan("我不是让你关灯。"), {"kind": "chat", "actions": []})
        # Generic "开灯" must NOT be hardcoded to mode 5; it goes through LLM semantic planning.
        from semantic_control import exact_plan
        self.assertIsNone(exact_plan("开灯"))
        # Unambiguous named lighting effects resolve cleanly as keyword fast-path assist
        expected_effects = [
            ("开机红灯", 1),
            ("开幻彩霓虹", 4),
            ("呼吸极光", 5),
            ("流星", 6),
            ("星空", 7),
            ("全屏色彩", 8),
            ("雨滴", 9),
            ("波纹", 10),
            ("笑脸", 11),
            ("壁炉火焰", 23),
            ("代码雨", 24),
            ("世界线", 28),
            ("回桌宠", 17),
            ("环境微光", 31),
            ("关掉灯光", 0),
        ]
        for utterance, mode_id in expected_effects:
            self.assertEqual(
                planner.plan(utterance),
                {"kind": "control", "actions": [{"tool": "set_light_mode", "value": mode_id}]},
                msg=f"Failed lighting fast-path for {utterance!r}",
            )
        self.assertNotEqual(
            (planner.plan("不要开红灯") or {}).get("kind"),
            "control",
        )
        from conversation_session import ConversationSession
        for end_txt in ("结束对话", "结束会话", "再见", "明天见", "退下"):
            self.assertTrue(ConversationSession.should_end(end_txt))
        self.assertFalse(ConversationSession.should_end("不要结束对话"))

    def test_wake_detector_defaults_to_five_name_profile(self):
        import types
        import tempfile
        import wake_detector

        captured = {}
        fake_sherpa = types.SimpleNamespace(KeywordSpotter=lambda **kw: captured.update(kw))
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"KURISU_CACHE_DIR": tmp}), mock.patch.dict(
                sys.modules, {"sherpa_onnx": fake_sherpa}
            ):
                wake_detector.WakeDetector()
        self.assertAlmostEqual(captured["keywords_threshold"], 0.43)
        self.assertAlmostEqual(captured["keywords_score"], 1.5)

    def test_awake_asr_prompt_and_roommate_noise_filter(self):
        import types
        from voice_listener import VoiceListener

        listener = VoiceListener.__new__(VoiceListener)
        listener.controller = None
        listener._music_monitor = False
        listener.is_awake = False
        self.assertIn("红莉栖", listener._asr_prompt())

        # Once awake, _asr_prompt must not prime Whisper with wake names or "结束对话",
        # while providing Simplified Chinese hints for arcade games and songs.
        listener.is_awake = True
        awake_prompt = listener._asr_prompt()
        self.assertNotIn("红莉栖", awake_prompt)
        self.assertNotIn("结束对话", awake_prompt)
        self.assertIn("贪吃蛇", awake_prompt)
        self.assertIn("七里香", awake_prompt)

        # Low-confidence roommate noise (-1.20) or fullwidth digits ('海洋４') must be dropped even at high RMS
        dispatched = []
        listener._work_lock = mock.MagicMock()
        listener._work_lock.__enter__ = mock.Mock(return_value=None)
        listener._work_lock.__exit__ = mock.Mock(return_value=None)
        listener._update_board_led = mock.Mock()
        listener._dispatch_command = lambda cmd, **kw: dispatched.append(cmd)
        listener.last_awake_time = 100.0
        loud_pcm = (b"\x00\x20" * 16000)
        for noisy_seg in (
            types.SimpleNamespace(text="你去给这些机会，红莉栖?", avg_logprob=-1.199, no_speech_prob=0.15),
            types.SimpleNamespace(text="人机而已４时刻玩个开４", avg_logprob=-0.55, no_speech_prob=0.10),
            types.SimpleNamespace(text="红莉。", avg_logprob=-0.40, no_speech_prob=0.05),
        ):
            listener.whisper_model = types.SimpleNamespace(
                transcribe=lambda *a, _seg=noisy_seg, **k: ([_seg], types.SimpleNamespace(no_speech_prob=0.1))
            )
            listener._process_utterance(loud_pcm)
        self.assertEqual(dispatched, [])
        self.assertEqual(listener.last_awake_time, 100.0)

    def test_stage_d_remote_camera_horizontal_mirror_and_lan_status_token(self):
        import cv2
        import numpy as np
        import types
        from multimodal_hub import MultimodalHub
        from simulator import SimulatedController

        ctrl = SimulatedController()
        hub = MultimodalHub(ctrl, None)
        sid = hub.start_remote(mode="fingertip", rotation=270, mirrored=True)

        # Create a 64x64 image where left half is black (0) and right half is bright (250)
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        img[:, 32:] = 250
        _, buf = cv2.imencode(".jpg", img)

        captured_rgb = []

        class _FakeHands:
            def process(self, rgb):
                captured_rgb.append(rgb.copy())
                return types.SimpleNamespace(multi_hand_landmarks=None)

        class _FakeFace:
            def process(self, rgb):
                return types.SimpleNamespace(multi_face_landmarks=None)

        hub._remote_hands = _FakeHands()
        hub._remote_face = _FakeFace()
        hub.process_remote_frame(buf.tobytes(), mode="fingertip", session_id=sid, rotation=270, mirrored=True)
        self.assertEqual(len(captured_rgb), 1)
        # Because mirrored=True flips the remote frame horizontally, the bright right half (x>=32)
        # must now be on the left half (x<32) so moving hand left moves LED ball left!
        self.assertGreater(float(np.mean(captured_rgb[0][:, :20])), 200.0)
        self.assertLess(float(np.mean(captured_rgb[0][:, 44:])), 30.0)

    def test_outdoor_demo_asr_song_game_homophones_and_fast_imagery(self):
        from music_commands import parse_music_request
        from music_library import search_words
        from semantic_control import exact_plan

        self.assertEqual(parse_music_request("跟我播放一首起理箱"), {"action": "play", "query": "七里香", "collection": False})
        self.assertEqual(parse_music_request("播放一首七米香"), {"action": "play", "query": "七里香", "collection": False})
        self.assertEqual(parse_music_request("播放米津玄师的莱蒙"), {"action": "play", "query": "米津玄師的Lemon", "collection": False})
        self.assertEqual(parse_music_request("播放第一手"), {"action": "choose", "number": 1})
        self.assertIn("米津玄師", search_words("米津玄师"))
        self.assertIn("lemon", search_words("莱蒙"))

        # Game ASR homophones & action vs question disambiguation
        self.assertEqual(exact_plan("我想完碳之蛇"), {"kind": "control", "actions": [{"tool": "start_game", "value": 33}]})
        self.assertEqual(exact_plan("我想玩攤吃蛇"), {"kind": "control", "actions": [{"tool": "start_game", "value": 33}]})
        self.assertEqual(exact_plan("我想玩俄羅斯風範"), {"kind": "control", "actions": [{"tool": "start_game", "value": 41}]})
        self.assertEqual(exact_plan("我想玩超级马里奥"), {"kind": "control", "actions": [{"tool": "start_game", "value": 1}]})
        self.assertEqual(exact_plan("超级马里奥是一款什么样的游戏？"), {"kind": "chat", "actions": []})

        # Common imagery fast-path (<1ms) while preserving question guard
        self.assertEqual(exact_plan("我想看森林的颜色"), {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 3}]})
        self.assertEqual(exact_plan("给我西瓜的颜色"), {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 3}]})
        self.assertEqual(exact_plan("我想看春联的颜色"), {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 1}]})
        self.assertEqual(exact_plan("我想看大海的颜色"), {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 2}]})
        self.assertIsNone(exact_plan("森林为什么是绿色的？"))


if __name__ == "__main__":
    unittest.main()
