"""Audio startup failure contracts; fake transport, no models or hardware opened."""

from pathlib import Path
import queue
import sys
import threading
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pc-agent-vision"))
from voice_listener import VoiceListener


class VoiceStartupTests(unittest.TestCase):
    def make_listener(self, connected=False, mic_ack=True):
        listener = VoiceListener.__new__(VoiceListener)
        listener._lifecycle_lock = threading.Lock()
        listener._stop_event = threading.Event()
        listener._ready_event = threading.Event()
        listener._session_generation = 0
        listener.is_listening = False
        listener.is_paused = False
        listener.stop_pending = False
        listener.stop_pending_threads = []
        listener._heal_circuit_broken = False
        listener._process_thread = None
        listener._worker_thread = None
        listener._watchdog_thread = None
        listener._teardown_thread = None
        listener._pcm_queue = queue.Queue()
        listener._utterance_queue = queue.Queue()
        listener.duplex = False
        listener._on_board_pcm = lambda pcm: None
        listener._update_board_led = lambda mode: None
        self.mic_calls = []

        def enable_mic(enabled):
            self.mic_calls.append(enabled)
            return mic_ack

        listener.controller = types.SimpleNamespace(
            audio_connected=connected,
            connect_audio=lambda: connected,
            enable_mic=enable_mic,
            on_mic_data=None,
            _voice_listener=None,
        )

        def wait_for_stop():
            listener._ready_event.wait(1)
            listener._stop_event.wait(2)

        listener._process_loop = wait_for_stop
        listener._worker_loop = wait_for_stop
        listener._watchdog_loop = wait_for_stop
        self.addCleanup(listener.stop, 1)
        return listener

    def assert_rolled_back(self, listener):
        self.assertFalse(listener.is_listening)
        self.assertFalse(listener.is_healthy())
        self.assertTrue(listener.last_start_error)
        self.assertTrue(listener._stop_event.is_set())
        self.assertTrue(listener._ready_event.is_set())
        self.assertFalse(listener.has_live_threads())
        self.assertFalse(listener.stop_pending)
        self.assertIsNone(listener.controller.on_mic_data)
        self.assertIsNone(listener.controller._voice_listener)
        self.assertEqual(self.mic_calls[-1], False)

    def test_false_audio_connection_cannot_report_listening_or_healthy(self):
        listener = self.make_listener()
        self.assertFalse(listener.start())
        self.assert_rolled_back(listener)
        self.assertNotIn(True, self.mic_calls)

    def test_microphone_rejection_rolls_back_without_starting_threads(self):
        listener = self.make_listener(connected=True, mic_ack=False)
        self.assertFalse(listener.start())
        self.assert_rolled_back(listener)
        self.assertEqual(self.mic_calls, [True, False])

    def test_connection_exception_rolls_back(self):
        listener = self.make_listener()

        def fail_connect():
            raise OSError("fake disconnected transport")

        listener.controller.connect_audio = fail_connect
        self.assertFalse(listener.start())
        self.assert_rolled_back(listener)
        self.assertIn("fake disconnected transport", listener.last_start_error)

    def test_explicit_restart_after_transport_recovers(self):
        listener = self.make_listener()
        self.assertFalse(listener.start())
        listener.controller.audio_connected = True
        listener.controller.connect_audio = lambda: True
        self.assertTrue(listener.start())
        self.assertTrue(listener.is_listening)
        self.assertTrue(listener.is_healthy())
        self.assertIsNone(listener.last_start_error)
        self.assertIs(listener.controller._voice_listener, listener)
        self.assertTrue(listener.stop(1))
        self.assertFalse(listener.has_live_threads())


if __name__ == "__main__":
    unittest.main()
