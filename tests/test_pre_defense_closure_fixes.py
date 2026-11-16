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


if __name__ == "__main__":
    unittest.main()
