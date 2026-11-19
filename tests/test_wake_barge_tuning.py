"""Production-path wake, interruption and endpoint regressions; no hardware audio."""
import os
import queue
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc-agent-vision'))
from voice_listener import VoiceListener


class WakeBargeTuningTests(unittest.TestCase):
    def listener(self, text='住手!', keyword='助手'):
        listener = VoiceListener.__new__(VoiceListener)
        listener.is_awake = True
        listener.is_listening = True
        listener.is_paused = False
        listener._music_monitor = False
        listener._stop_event = threading.Event()
        listener._work_lock = threading.Lock()
        listener._update_board_led = Mock()
        listener._acknowledge_wake = Mock()
        listener._dispatch_command = Mock()
        listener.last_awake_time = 100.
        listener.controller = None
        listener.wake_detector = types.SimpleNamespace(detect=Mock(return_value=keyword))
        listener.whisper_model = types.SimpleNamespace(transcribe=Mock(return_value=(
            [types.SimpleNamespace(text=text, avg_logprob=-1.0, no_speech_prob=.16)], object())))
        return listener

    def process(self, listener):
        pcm = (np.sin(np.arange(16000) * .2) * 5000).astype('<i2').tobytes()
        with tempfile.TemporaryDirectory(dir=os.environ.get('KURISU_TEST_TMP')) as folder:
            with patch.dict(os.environ, {'KURISU_CACHE_DIR': folder}):
                listener._process_utterance(pcm)

    def test_acoustic_confirmation_rescues_standalone_low_confidence_homophone(self):
        listener = self.listener()
        self.process(listener)
        listener._acknowledge_wake.assert_called_once_with('助手')
        listener._dispatch_command.assert_not_called()
        listener.wake_detector.detect.assert_called_once()

    def test_acoustic_confirmation_rescues_canonical_standalone_name(self):
        listener = self.listener(text='助手。')
        self.process(listener)
        listener._acknowledge_wake.assert_called_once_with('助手')

    def test_homophone_without_acoustic_evidence_is_still_rejected(self):
        listener = self.listener(keyword='')
        self.process(listener)
        listener._acknowledge_wake.assert_not_called()
        listener._dispatch_command.assert_not_called()

    def test_low_confidence_attached_command_is_not_rescued(self):
        listener = self.listener(text='住手开红灯')
        self.process(listener)
        listener._acknowledge_wake.assert_not_called()
        listener._dispatch_command.assert_not_called()

    def test_chatter_containing_a_name_does_not_bypass_noise_filter(self):
        listener = self.listener(text='我不知道助手说了什么')
        self.process(listener)
        listener.wake_detector.detect.assert_not_called()
        listener._dispatch_command.assert_not_called()

    def test_barge_requires_both_gates_then_aborts_and_reopens_wake(self):
        listener = self.listener()
        listener.is_paused = True
        listener.duplex = True
        listener._probe_wake = Mock(return_value='助手')
        listener._active_turn_id = 1
        listener._barge_audio = bytearray()
        listener.turn_cancelled = threading.Event()
        audio = types.SimpleNamespace(cancelled=threading.Event(), abort=Mock(return_value=True))
        listener.controller = types.SimpleNamespace(_network_audio=audio, playback_cancel=threading.Event())
        listener._check_barge_locked(bytes(32000))
        audio.abort.assert_called_once()
        self.assertTrue(listener.turn_cancelled.is_set())
        self.assertEqual(listener._active_turn_id, 2)
        listener._acknowledge_wake.assert_called_once_with('助手')

    def test_barge_rejects_asr_without_a_wake_name(self):
        listener = self.listener(text='普通背景声音')
        listener.is_paused = True
        listener._probe_wake = Mock(return_value='助手')
        listener.controller = types.SimpleNamespace(_network_audio=types.SimpleNamespace(abort=Mock()))
        listener._check_barge_locked(bytes(32000))
        listener.controller._network_audio.abort.assert_not_called()
        listener._acknowledge_wake.assert_not_called()

    def test_non_speech_high_energy_noise_cannot_hold_endpoint_forever(self):
        listener = self.listener()
        listener._ready_event = threading.Event()
        listener._ready_event.set()
        listener._resume_warmup_frames = 0
        listener._utterance_queue = queue.Queue()
        quiet = bytes(960)
        speech = np.tile(np.array([-5000, 5000], dtype='<i2'), 240).tobytes()
        noise = np.tile(np.array([-4000, 4000], dtype='<i2'), 240).tobytes()
        chunks = iter([quiet] * 20 + [speech] * 12 + [noise] * 100)
        def get(**kwargs):
            try:
                return next(chunks)
            except StopIteration:
                listener.is_listening = False
                raise queue.Empty
        listener._pcm_queue = types.SimpleNamespace(get=get)
        decisions = iter([True] * 12 + [False] * 100)
        listener.vad = types.SimpleNamespace(is_speech=lambda *args: next(decisions))
        listener.controller = types.SimpleNamespace(audio_connected=True)
        listener._last_board_frame_time = __import__('time').time()
        with patch.dict(os.environ, {'KURISU_AWAKE_DIM_FRAMES': '22', 'KURISU_AWAKE_SILENT_FRAMES': '92'}):
            listener._process_loop()
        self.assertEqual(listener._utterance_queue.qsize(), 1)
        self.assertFalse(listener._speech_active)


if __name__ == '__main__':
    unittest.main()
