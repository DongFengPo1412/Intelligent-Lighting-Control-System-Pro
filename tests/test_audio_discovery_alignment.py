import unittest
import types
import numpy as np
import json
import time
import ipaddress
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from access_control import AccessPolicy, REVOKED_TOKENS
from music_engine import process_speaker_audio
from music_commands import parse_music_request, MusicCommands
from music_library import MusicLibrary, LibraryPlayback
from pro_paths import data_dir, cache_dir


class AudioAlignmentAndDistortionTests(unittest.TestCase):
    def test_music_engine_linear_scaling_no_tanh_distortion(self):
        """Verify process_speaker_audio uses pure linear scaling without tanh saturation."""
        # Synthesize a 16kHz test tone with extreme peaks
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        # Dynamic signal: quiet section + loud peaks at 0.95 full-scale
        signal = np.sin(2 * np.pi * 440 * t) * 0.95
        pcm_in = (signal * 32767).astype("<i2").tobytes()

        # Process through speaker audio pipeline
        pcm_out = process_speaker_audio(pcm_in, gain=0.62)
        out_samples = np.frombuffer(pcm_out, dtype="<i2").astype(np.float32) / 32768.0

        # Peak must strictly observe digital headroom to prevent MAX98357A 5V rail clipping
        max_peak = float(np.max(np.abs(out_samples)))
        self.assertLessEqual(max_peak, 0.85)
        self.assertGreater(max_peak, 0.40)

        # Check linearity: ratio between fundamental and 3rd harmonic must not show tanh odd-harmonic explosion
        # In tanh distortion, 3rd harmonic is severely elevated (> -20 dB). In linear filter, 3rd harmonic is near zero.
        spectrum = np.abs(np.fft.rfft(out_samples))
        freqs = np.fft.rfftfreq(len(out_samples), 1.0 / sr)
        f0_idx = np.argmin(np.abs(freqs - 440))
        f3_idx = np.argmin(np.abs(freqs - 1320))
        h3_ratio = spectrum[f3_idx] / max(spectrum[f0_idx], 1e-6)
        self.assertLess(h3_ratio, 0.05, f"3rd harmonic ratio {h3_ratio} indicates non-linear distortion")

    def test_music_engine_silence_preservation(self):
        silence = b"\x00" * 3200
        out = process_speaker_audio(silence, gain=0.62)
        self.assertEqual(out, silence)


class AccessControlTokenRevocationTests(unittest.TestCase):
    def test_revoked_token_is_strictly_rejected(self):
        class DummyRequest:
            def __init__(self, headers=None, query=None, cookies=None, remote="192.168.186.254"):
                self.headers = headers or {}
                self.query = query or {}
                self.cookies = cookies or {}
                self.remote = remote
                self.path = "/api/pro/status"

        policy = AccessPolicy(token="ValidSecureTestTokenAtLeast32CharsLong12345", trust_private=True)
        # Even with trust_private=True, explicit revoked token must be rejected
        revoked = "dPBYG-Ew4zA8U3rMAAS5tX6sA0_fWrbsWTrr1IjBMZk"
        self.assertIn(revoked, REVOKED_TOKENS)

        req_revoked_bearer = DummyRequest(headers={"Authorization": f"Bearer {revoked}"})
        self.assertFalse(policy.authorized(req_revoked_bearer))

        req_revoked_query = DummyRequest(query={"token": revoked})
        self.assertFalse(policy.authorized(req_revoked_query))

        req_revoked_cookie = DummyRequest(cookies={"kurisu_session": revoked})
        self.assertFalse(policy.authorized(req_revoked_cookie))

        # Legitimate token must pass
        req_valid = DummyRequest(headers={"Authorization": f"Bearer {policy.token}"})
        self.assertTrue(policy.authorized(req_valid))


class ThreePartyDiscoveryTests(unittest.TestCase):
    def test_wifi_gateway_target_ips_includes_broadcasts_when_offline(self):
        from wifi_gateway import WiFiGateway
        from unittest.mock import patch
        gw = WiFiGateway.__new__(WiFiGateway)
        gw.board_sta_ip = ""
        gw.board_ap_ip = "192.168.4.1"
        gw.last_seen = 0.0

        with patch("access_control.detect_active_local_subnets", return_value=[ipaddress.ip_network("192.168.43.0/24")]):
            targets = gw.get_target_ips()
        self.assertIn("192.168.43.255", targets)
        self.assertIn("255.255.255.255", targets)
        self.assertIn("192.168.4.1", targets)

    def test_wifi_gateway_target_ips_unicast_when_online(self):
        from wifi_gateway import WiFiGateway
        gw = WiFiGateway.__new__(WiFiGateway)
        gw.board_sta_ip = "192.168.186.161"
        gw.board_ap_ip = "192.168.4.1"
        gw.last_seen = time.monotonic()

        targets = gw.get_target_ips()
        self.assertEqual(targets, ["192.168.186.161"])


class VoiceMusicCommandE2ETests(unittest.TestCase):
    """Fully isolated synthetic fixture E2E music-command suite (F21: zero reliance on private user library)."""

    @staticmethod
    def _write_synth_wav(path: Path, freq_hz: float = 440.0, dur_s: float = 0.25, sr: int = 16000):
        import wave
        t = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False)
        samples = (np.sin(2 * np.pi * freq_hz * t) * 0.25 * 32767).astype("<i2")
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(samples.tobytes())

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.music_dir = self.root / "songs"
        self.music_dir.mkdir(parents=True, exist_ok=True)
        for name, freq in (
            ("周杰伦 - 七里香.wav", 440.0),
            ("BEYOND - 海阔天空.wav", 523.25),
            ("汪苏泷 - 有点甜.wav", 587.33),
            ("周杰伦 - 晴天.wav", 659.25),
            ("独立翻唱 - 晴天.wav", 698.46),
        ):
            self._write_synth_wav(self.music_dir / name, freq_hz=freq)

        with patch.dict(os.environ, {"KURISU_MUSIC_DIR": ""}):
            self.library = MusicLibrary(
                self.root / "music-library.json",
                self.root / "music-library-tags.json",
            )
        self.library.configure(str(self.music_dir))

        class DummyPlayer:
            def __init__(self):
                self.running = False
                self.paused = False
                self.current_track = None
                self.thread = types.SimpleNamespace(join=lambda: None)
                self.controller = types.SimpleNamespace(is_connected=True)
                self.cancel = types.SimpleNamespace(is_set=lambda: True)
                self.position = 0.0
                self.duration = 0.25
                self.visual_fluid = True
                self._full_pcm = b"\x00\x00"

            def play_file(self, path, fluid=True):
                self.running = True
                self.paused = False
                self.current_track = str(path)
                return True

            def pause(self):
                if self.running:
                    self.paused = True
                    self.running = False
                return self.paused

            def resume(self):
                self.running = True
                self.paused = False
                return True

            def stop(self, restore=True):
                self.running = False
                self.paused = False

        self.player = DummyPlayer()
        self.playback = LibraryPlayback(self.library, self.player)
        self.commands = MusicCommands(self.library, self.playback)

    def tearDown(self):
        self._tmp.cleanup()

    def test_e2e_qilixiang_match(self):
        res = self.commands.handle("播放七里香")
        self.assertIsNotNone(res)
        self.assertIn("七里香", res["reply"])
        self.assertIn("开始播放", res["reply"])
        self.assertFalse(res["speak"]) # TTS must not speak over music

    def test_e2e_artist_beyond_match(self):
        res = self.commands.handle("播放海阔天空")
        self.assertIsNotNone(res)
        self.assertIn("海阔天空", res["reply"])
        self.assertIn("BEYOND", res["reply"])

    def test_e2e_artist_wang_sulong_match(self):
        res = self.commands.handle("我想听有点甜")
        self.assertIsNotNone(res)
        self.assertIn("有点甜", res["reply"])

    def test_e2e_non_existent_song(self):
        res = self.commands.handle("播放不存在的神奇魔力歌12345")
        self.assertIsNotNone(res)
        self.assertIn("没有找到", res["reply"])

    def test_e2e_ambiguous_song_requests_candidate_choice(self):
        res = self.commands.handle("播放晴天")
        self.assertIsNotNone(res)
        self.assertTrue("请说“播放第几首”" in res["reply"] or "开始播放" in res["reply"])

    def test_e2e_playback_pause_resume_step_and_stop(self):
        res = self.commands.handle("播放七里香")
        self.assertIn("开始播放", res["reply"])
        self.assertTrue(self.player.running)
        self.assertTrue(self.playback.pause())
        self.assertTrue(self.player.paused)
        self.assertTrue(self.playback.resume())
        self.assertFalse(self.player.paused)
        nxt = self.playback.step(1)
        self.assertIsNotNone(nxt)
        self.playback.stop()
        self.assertFalse(self.player.running)

    def test_e2e_edge_empty_corrupt_unsupported_and_invalid_path(self):
        # 1. Empty directory
        empty_dir = self.root / "empty_songs"
        empty_dir.mkdir()
        lib_empty = MusicLibrary(self.root / "empty.json", self.root / "empty-tags.json")
        res_empty = lib_empty.configure(str(empty_dir))
        self.assertEqual(res_empty["count"], 0)
        self.assertEqual(lib_empty.search("七里香")["items"], [])

        # 2. Unsupported file format + corrupt .wav bytes
        bad_dir = self.root / "bad_songs"
        bad_dir.mkdir()
        (bad_dir / "readme.txt").write_text("not audio", encoding="utf-8")
        (bad_dir / "corrupt.wav").write_bytes(b"RIFF\x00\x00\x00\x00NOT_A_VALID_WAVE_BODY")
        lib_bad = MusicLibrary(self.root / "bad.json", self.root / "bad-tags.json")
        scan_bad = lib_bad.configure(str(bad_dir))
        self.assertFalse(any(t["filename"].endswith(".txt") for t in scan_bad.get("items", [])))
        if scan_bad.get("count", 0) > 0:
            corrupt_id = lib_bad.search("")["items"][0]["id"]
            from music_engine import decode_audio
            with self.assertRaises(Exception):
                decode_audio(str(bad_dir / "corrupt.wav"))

        # 3. Nonexistent / invalid root path
        missing_path = self.root / "does_not_exist_folder"
        with self.assertRaises((ValueError, FileNotFoundError, OSError)):
            lib_bad.configure(str(missing_path))

    def test_normal_chat_and_silence_not_triggered(self):
        self.assertIsNone(self.commands.handle("今天天气真好啊"))
        self.assertIsNone(self.commands.handle("帮我开一下客厅的灯"))
        self.assertIsNone(self.commands.handle("你叫什么名字"))
        self.assertIsNone(self.commands.handle("......"))


class ConditionalRealMusicLibraryTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("KURISU_REAL_MUSIC_DIR"), "Conditional test: requires KURISU_REAL_MUSIC_DIR")
    def test_optional_real_user_music_dir_scan(self):
        real_dir = Path(os.environ["KURISU_REAL_MUSIC_DIR"])
        self.assertTrue(real_dir.is_dir())
        with tempfile.TemporaryDirectory() as tmp:
            lib = MusicLibrary(Path(tmp) / "real.json", Path(tmp) / "real-tags.json")
            res = lib.configure(str(real_dir))
            self.assertGreaterEqual(res["count"], 0)


class PreDefenseWifiDiscoveryFixTests(unittest.TestCase):
    def _make_mock_gateway(self):
        import socket
        import threading
        from wifi_gateway import WiFiGateway

        gw = WiFiGateway.__new__(WiFiGateway)
        gw.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        gw.sock.bind(("127.0.0.1", 0))
        gw.sock.settimeout(0.1)
        gw.port = 8888
        gw.is_running = True
        gw._trust_private = True
        gw.control_token = ""
        gw.boot_id = None
        gw.client_id = "c" * 32
        gw._sequence = 1
        gw.board_sta_ip = None
        gw.board_ap_ip = "192.168.4.1"
        gw.last_seen = 0.0
        gw.last_mode = None
        gw.last_result = {}
        gw._pending = {}
        gw._pending_lock = threading.Lock()
        gw._send_lock = threading.RLock()
        gw._read_lock = threading.Lock()
        gw._read_sequence = 1
        gw._read_boot = None
        tmp = tempfile.TemporaryDirectory()
        gw._state_path = Path(tmp.name) / "device-state.json"
        return gw, tmp

    def test_first_discovery_without_token_probes_broadcast_then_sends_unicast_mode(self):
        import ipaddress
        import threading
        from wifi_gateway import WiFiGateway

        gw, tmp = self._make_mock_gateway()
        sent_packets = []
        boot_id = "b" * 32
        board_ip = "192.168.43.88"

        class FakeSock:
            def sendto(self, data, addr):
                sent_packets.append((json.loads(data.decode("utf-8")), addr))
                msg = json.loads(data.decode("utf-8"))
                rid = msg["request_id"]
                if "command" not in msg:
                    # Simulate ESP32 STA reply from hotspot IP on port 8888
                    def inject():
                        with gw._pending_lock:
                            p = gw._pending.get(rid)
                            if p and gw._is_valid_unicast_target(board_ip):
                                p["result"] = {"request_id": rid, "status": "error", "error": "pairing_required", "boot_id": boot_id}
                                p["sender_ip"] = board_ip
                                gw.board_sta_ip = board_ip
                                p["event"].set()
                    threading.Thread(target=inject, daemon=True).start()
                else:
                    def ack():
                        with gw._pending_lock:
                            p = gw._pending.get(rid)
                            if p and addr[0] == board_ip:
                                p["result"] = {"request_id": rid, "status": "ok", "mode": 2}
                                gw.last_seen = time.monotonic()
                                p["event"].set()
                    threading.Thread(target=ack, daemon=True).start()
                return len(data)

            def close(self):
                pass

        gw.sock.close()
        gw.sock = FakeSock()
        try:
            with patch("access_control.AccessPolicy.get_trusted_subnets", return_value=[ipaddress.ip_network("192.168.43.0/24")]):
                ok = gw.send_command('{"cmd":"mode","val":2}', timeout=0.5, retries=0)
                self.assertTrue(ok, f"Expected first-discovery mode ok, got: {gw.last_result}")
                self.assertEqual(gw.board_sta_ip, board_ip)
                # Ensure read-only probe hit broadcast, while side-effect mode command ONLY hit verified unicast IP!
                probes = [p for p in sent_packets if "command" not in p[0]]
                cmds = [p for p in sent_packets if "command" in p[0]]
                self.assertTrue(any(addr[0] in ("255.255.255.255", "192.168.43.255") for _, addr in probes))
                self.assertEqual(len(cmds), 1)
                self.assertEqual(cmds[0][1][0], board_ip)
                self.assertNotIn("255.255.255.255", [addr[0] for _, addr in cmds])

                # Stale cached IP from another network must NOT block discovery on new hotspot
                gw.board_sta_ip = "192.168.186.161"
                gw.last_seen = 0.0
                gw.boot_id = None
                sent_packets.clear()
                self.assertTrue(gw.send_command('{"cmd":"brightness","val":20}', timeout=0.5, retries=0))
                self.assertEqual(gw.board_sta_ip, board_ip)

                # Sensitive commands MUST still fail closed without control_token
                sent_packets.clear()
                for sens in ('{"cmd":"request_audio_ticket"}', '{"cmd":"reboot"}', '{"cmd":"pair"}'):
                    self.assertFalse(gw.send_command(sens, timeout=0.2, retries=0))
                    self.assertEqual(gw.last_result.get("error"), "pairing_required")
                self.assertEqual(sent_packets, [])

                # VPN / untrusted / broadcast IPs rejected by unicast guard
                self.assertFalse(WiFiGateway._is_valid_unicast_target("26.59.0.60"))
                self.assertFalse(WiFiGateway._is_valid_unicast_target("255.255.255.255"))
                self.assertFalse(WiFiGateway._is_valid_unicast_target("192.168.43.255"))
                self.assertTrue(WiFiGateway._is_valid_unicast_target("192.168.43.88"))
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
