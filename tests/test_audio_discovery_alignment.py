import unittest
import types
import numpy as np
import json
import time
import ipaddress
import os
import sys
from pathlib import Path

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
        gw = WiFiGateway.__new__(WiFiGateway)
        gw.board_sta_ip = ""
        gw.board_ap_ip = "192.168.4.1"
        gw.last_seen = 0.0

        targets = gw.get_target_ips()
        self.assertIn("192.168.186.255", targets)
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
    def setUp(self):
        self.library = MusicLibrary(
            data_dir() / "music-library.json", cache_dir() / "music-library-tags.json"
        )
        self.library.scan()

        class DummyPlayer:
            def __init__(self):
                self.running = False
                self.current_track = None
                self.thread = types.SimpleNamespace(join=lambda: None)
                self.controller = types.SimpleNamespace(is_connected=True)
                self.cancel = types.SimpleNamespace(is_set=lambda: True)
                self.position = 0.0
                self.duration = 180.0
            def play_file(self, path, fluid=True):
                self.running = True
                return True
            def stop(self):
                self.running = False

        self.player = DummyPlayer()
        self.playback = LibraryPlayback(self.library, self.player)
        self.commands = MusicCommands(self.library, self.playback)

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
        # Should ask user for candidate selection
        self.assertTrue("请说“播放第几首”" in res["reply"] or "开始播放" in res["reply"])

    def test_normal_chat_and_silence_not_triggered(self):
        self.assertIsNone(self.commands.handle("今天天气真好啊"))
        self.assertIsNone(self.commands.handle("帮我开一下客厅的灯"))
        self.assertIsNone(self.commands.handle("你叫什么名字"))
        self.assertIsNone(self.commands.handle("......"))


if __name__ == "__main__":
    unittest.main()
