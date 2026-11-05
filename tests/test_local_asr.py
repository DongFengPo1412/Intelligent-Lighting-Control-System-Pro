"""Adapter contracts only; no model download or microphone access."""
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc-agent-vision'))
from local_asr import SenseVoiceASR


class LocalAsrTests(unittest.TestCase):
    def adapter(self, text):
        decoder = SenseVoiceASR.__new__(SenseVoiceASR)
        decoder.lock = threading.Lock()
        self.inputs = []
        stream = SimpleNamespace(
            result=SimpleNamespace(text=text),
            accept_waveform=lambda rate, audio: self.inputs.append((rate, audio)),
        )
        decoder.recognizer = SimpleNamespace(create_stream=lambda: stream, decode_stream=lambda s: None)
        return decoder

    def test_pcm_conversion_and_no_invented_confidence(self):
        decoder = self.adapter('<|zh|><|NEUTRAL|>胆小鬼博弈。')
        segments, info = decoder.transcribe(np.array([0, 16384], dtype=np.int16), beam_size=5)
        segment = list(segments)[0]
        self.assertEqual(segment.text, '胆小鬼博弈。')
        self.assertEqual(self.inputs[0][0], 16000)
        np.testing.assert_array_equal(self.inputs[0][1], [0, .5])
        self.assertFalse(hasattr(segment, 'avg_logprob'))
        self.assertFalse(hasattr(info, 'no_speech_prob'))

    def test_invalid_or_non_speech_input_does_not_create_a_reply(self):
        decoder = self.adapter('<|zh|><|BGM|>')
        self.assertEqual(list(decoder.transcribe(np.zeros(1600))[0]), [])
        for audio in (np.zeros((2, 20)), np.array([float('nan')]), np.zeros(16000*31)):
            with self.assertRaises(ValueError):
                decoder.transcribe(audio)


if __name__ == '__main__':
    unittest.main()
