"""Audio startup failure contracts; fake transport, no models or hardware opened."""

from pathlib import Path
import queue
import sys
import threading
import types
import unittest
from unittest.mock import patch

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
        listener.wake_detector = object()
        listener.whisper_model = object()
        listener._update_board_led = lambda mode: None
        self.mic_calls = []

        def enable_mic(enabled):
            self.mic_calls.append(enabled)
            if enabled and mic_ack and not getattr(listener, '_test_drop_pcm', False):
                listener._on_board_pcm(bytes(960))
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

    def test_success_sound_is_after_capture_preparation_and_before_wake_gate_opens(self):
        listener = self.make_listener(connected=True)
        def ready():
            self.assertEqual(self.mic_calls, [True])
            self.assertEqual(listener.controller.on_mic_data, listener._on_board_pcm)
            self.assertTrue(listener._process_thread.is_alive())
            self.assertTrue(listener._worker_thread.is_alive())
            self.assertTrue(listener._watchdog_thread.is_alive())
            self.assertFalse(listener.is_listening)
            self.assertFalse(listener.is_awake)
            self.assertFalse(listener._ready_event.is_set())
            return True
        self.assertTrue(listener.start(ready_callback=ready))
        self.assertTrue(listener._ready_event.is_set())
        self.assertTrue(listener.is_listening)
        self.assertFalse(listener.is_awake)

    def test_audio_or_mic_failure_cannot_play_success_sound(self):
        for connected, mic_ack in [(False, True), (True, False)]:
            with self.subTest(connected=connected, mic_ack=mic_ack):
                listener = self.make_listener(connected=connected, mic_ack=mic_ack)
                def forbidden():self.fail('Do not announce readiness after a failed prerequisite')
                self.assertFalse(listener.start(ready_callback=forbidden))
                self.assert_rolled_back(listener)

    def test_reconnect_reuses_ready_sound_once_without_replaying_on_duplicate_start(self):
        listener = self.make_listener(connected=True)
        calls = []
        callback = lambda: calls.append('ready') or True
        self.assertTrue(listener.start(ready_callback=callback))
        self.assertTrue(listener.start())
        self.assertEqual(calls, ['ready'])
        self.assertTrue(listener.stop(1))
        self.assertTrue(listener.start())
        self.assertEqual(calls, ['ready', 'ready'])

    def test_failed_success_sound_rolls_back_and_does_not_open_wake_gate(self):
        listener = self.make_listener(connected=True)
        self.assertFalse(listener.start(ready_callback=lambda:False))
        self.assert_rolled_back(listener)
        self.assertIn('就绪提示', listener.last_start_error)

    def test_mic_ack_without_incoming_pcm_does_not_announce_success(self):
        listener = self.make_listener(connected=True)
        listener._test_drop_pcm = True
        def forbidden():self.fail('A mic ACK without any incoming audio is not ready')
        self.assertFalse(listener.start(ready_callback=forbidden))
        self.assert_rolled_back(listener)
        self.assertIn('PCM', listener.last_start_error)

    def test_missing_wake_or_asr_model_cannot_announce_voice_readiness(self):
        for field in ('wake_detector', 'whisper_model'):
            with self.subTest(field=field):
                listener = self.make_listener(connected=True)
                setattr(listener, field, None)
                def forbidden():self.fail('No startup sound without wake and ASR')
                self.assertFalse(listener.start(ready_callback=forbidden))
                self.assert_rolled_back(listener)
                self.assertNotIn(True, self.mic_calls)

    def test_real_boot_helper_requires_audio_and_propagates_ready_sound_failure(self):
        from light_controller import LightController
        for audio, sound in [(False, True), (True, False), (True, True)]:
            with self.subTest(audio=audio, sound=sound):
                events = []
                ctrl = types.SimpleNamespace(wait_for_control=lambda timeout:True,
                    connect_audio=lambda:audio,
                    set_board_led=lambda mode: events.append(mode) or True,
                    play_beep=lambda: events.append('beep') or sound)
                self.assertEqual(LightController.run_boot_ceremony(ctrl), audio and sound)
                self.assertEqual('off' in events, audio and sound)
                self.assertEqual('beep' in events, audio)
                self.assertNotIn('pairing', events)  # Already authenticated, not re-pairing.

    def test_mid_sound_assets_are_valid_and_startup_uses_success_not_wake_popup(self):
        from light_controller import LightController
        popup = LightController._load_mid_sound('popup')
        success = LightController._load_mid_sound('success')
        self.assertEqual(len(popup), 7680*2)
        self.assertEqual(len(success), 16320*2)
        self.assertNotEqual(popup, success)
        played = []
        ctrl = types.SimpleNamespace(wait_for_control=lambda timeout:True,
            connect_audio=lambda:True, set_board_led=lambda mode:True,
            _ready_pcm=success, play_audio_pcm=lambda pcm:played.append(pcm) or True,
            play_beep=lambda:self.fail('Startup should use Mid success, not popup'))
        self.assertTrue(LightController.run_boot_ceremony(ctrl))
        self.assertEqual(played, [success])

    def test_web_warmup_passes_ready_sound_to_listener_only_after_model_ready(self):
        import asyncio
        import web_server
        events = []
        agent = types.SimpleNamespace(semantic=types.SimpleNamespace(
            warmup=lambda **kwargs:events.append('model')), model_ready=False)
        ctrl = types.SimpleNamespace(run_boot_ceremony=lambda:events.append('sound') or True)
        def start(ready_callback=None):
            self.assertTrue(agent.model_ready)
            events.append('capture')
            return ready_callback()
        listener = types.SimpleNamespace(is_paused=False, is_listening=False, start=start, wake_reply_pcm=bytes(320))
        app = {'warmup_abort_event':threading.Event()}
        with patch.multiple(web_server, agent=agent, controller=ctrl, listener=listener, shutting_down=False):
            asyncio.run(web_server.background_model_warmup(app, max_retries=1))
        self.assertEqual(events, ['model', 'capture', 'sound'])
        self.assertEqual(app['voice_startup_state'], 'waiting_wake')


if __name__ == "__main__":
    unittest.main()
