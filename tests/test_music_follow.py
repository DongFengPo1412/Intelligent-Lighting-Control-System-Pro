"""Timing and frequency contracts without any audio/serial/network device."""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pc-agent-vision"))
from music_engine import MusicFeatures, MusicPlayer
from pro_control import ProControlMixin


class SlowController:
    port = "TEST"

    def __init__(self, duration=0.55, delay=0.07, start_delay=0):
        self.playback_started_at = None
        self.duration = duration
        self.delay = delay
        self.start_delay = start_delay
        self.mir = []
        self.spectrum = []
        self.mode = None

    def set_mode(self, mode):
        self.mode = mode
        return True

    def play_audio_pcm(self, pcm):
        time.sleep(self.start_delay)
        self.playback_started_at = time.monotonic()
        time.sleep(self.duration)
        return True

    def music_features(self, energy, flux, onset, tempo, phase, bands=None):
        self.mir.append((time.monotonic(), energy, bands))
        time.sleep(self.delay)
        return True

    def send_raw(self, value):
        self.spectrum.append(value)
        return True


class MusicFollowTests(unittest.TestCase):
    def play(self, controller, fluid=True):
        t = np.arange(int(controller.duration * 16000)) / 16000
        pcm = (np.sin(t * 2 * np.pi * 440) * 6000).astype("<i2").tobytes()
        player = MusicPlayer(controller)
        with patch("music_engine.decode_audio", return_value=pcm):
            player.play(b"fixture", fluid)
        player.thread.join(3)
        self.assertFalse(player.thread.is_alive())
        self.assertIsNone(player.error)
        return player

    def test_slow_ack_skips_stale_windows_instead_of_accumulating_delay(self):
        controller = SlowController()
        player = self.play(controller)
        self.assertGreater(player.analysis_stats["skipped_frames"], 2)
        self.assertLess(player.analysis_stats["max_dispatch_lag_ms"], 200)
        self.assertFalse(controller.spectrum)
        self.assertTrue(any(energy > 0 for _, energy, _ in controller.mir))
        self.assertEqual(controller.mir[-1][1:], (0, [0] * 16))

    def test_analysis_waits_for_actual_playback_after_connection_setup(self):
        controller = SlowController(duration=0.25, delay=0, start_delay=0.15)
        self.play(controller)
        active = [timestamp for timestamp, energy, _ in controller.mir if energy > 0]
        self.assertTrue(active)
        self.assertGreaterEqual(min(active), controller.playback_started_at)

    def test_spectrum_uses_only_frequency_columns_and_clears_on_completion(self):
        controller = SlowController(duration=0.2, delay=0)
        self.play(controller, False)
        self.assertEqual(controller.mode, 15)
        self.assertFalse(controller.mir)
        self.assertGreater(len(controller.spectrum), 1)
        self.assertEqual(controller.spectrum[-1], "f,0," + ",".join(["0"] * 16))

    def test_different_tones_move_the_fft_peak_to_higher_frequency_bands(self):
        peaks = []
        for frequency in (110, 440, 1760, 6000):
            t = np.arange(1024) / 16000
            feature = MusicFeatures().analyze(
                0.2 * np.sin(2 * np.pi * frequency * t), 0
            )
            peaks.append(int(np.argmax(feature["bands"])))
        self.assertTrue(all(a < b for a, b in zip(peaks, peaks[1:])), peaks)

    def test_optional_band_payload_is_strict_and_old_call_still_works(self):
        class Capture(ProControlMixin):
            def send_json(self, payload):
                self.payload = payload
                return True

        c = Capture()
        c.music_features(0.5, 0.2, True, 120)
        self.assertNotIn("bands", c.payload)
        c.music_features(0.5, 0.2, True, 120, bands=list(range(16)))
        self.assertEqual(c.payload["bands"], list(range(16)))
        for bad in ([0] * 15, [True] * 16, [16] * 16, [0.5] * 16, [float("nan")] * 16):
            with self.assertRaises(ValueError):
                c.music_features(0.5, 0.2, True, 120, bands=bad)

    def test_music_restores_only_the_voice_pause_it_owns(self):
        for already_paused in (False, True):

            class Listener:
                is_listening = True
                is_paused = already_paused

                def __init__(self):
                    self.calls = []

                def pause(self):
                    self.calls.append("pause")
                    self.is_paused = True

                def resume(self):
                    self.calls.append("resume")
                    self.is_paused = False

            controller = SlowController(duration=0.15, delay=0)
            controller._voice_listener = Listener()
            self.play(controller)
            self.assertEqual(
                controller._voice_listener.calls,
                [] if already_paused else ["pause", "resume"],
            )

    def test_live_visual_switch_routes_new_frames_to_the_selected_mode(self):
        controller = SlowController(duration=0.4, delay=0)
        player = MusicPlayer(controller)
        pcm = (np.sin(np.arange(6400) * 0.2) * 6000).astype("<i2").tobytes()
        with patch("music_engine.decode_audio", return_value=pcm):
            player.play(b"fixture")
        time.sleep(0.15)
        player.visual_fluid = False
        player.thread.join(2)
        self.assertIsNone(player.error)
        self.assertTrue(controller.mir)
        self.assertTrue(controller.spectrum)


if __name__ == "__main__":
    unittest.main()
