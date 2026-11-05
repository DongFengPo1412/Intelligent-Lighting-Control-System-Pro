"""Optional CPU Chinese ASR; no downloads, microphone or hardware on import."""

from pathlib import Path
from types import SimpleNamespace
import re
import sys
import threading

import numpy as np


class SenseVoiceASR:
    """Small transcribe facade used by VoiceListener's existing turn pipeline.

    SenseVoice does not provide Whisper's probability/log-probability fields.
    They remain absent rather than being fabricated for the caller.
    """

    def __init__(self, model_dir, num_threads=2):
        if not model_dir:
            raise ValueError('KURISU_SENSEVOICE_DIR is required')
        folder = Path(model_dir).expanduser().resolve(strict=True)
        model, tokens = folder / 'model.int8.onnx', folder / 'tokens.txt'
        if not model.is_file() or not tokens.is_file():
            raise ValueError('SenseVoice model.int8.onnx and tokens.txt are required')
        sys.path.insert(0, str(Path(__file__).parent / '.runtime_deps'))
        import sherpa_onnx
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model), tokens=str(tokens), num_threads=num_threads,
            language='zh', use_itn=True, provider='cpu',
        )
        self.lock = threading.Lock()

    def transcribe(self, samples, **unused_whisper_options):
        audio = np.asarray(samples)
        if audio.ndim != 1 or not 0 < audio.size <= 16000 * 30 or not np.isfinite(audio).all():
            raise ValueError('Expected finite mono 16kHz audio, at most 30 seconds')
        audio = (audio.astype(np.float32) / 32768 if audio.dtype == np.int16
                 else audio.astype(np.float32))
        with self.lock:
            stream = self.recognizer.create_stream()
            stream.accept_waveform(16000, audio)
            self.recognizer.decode_stream(stream)
            text = re.sub(r'<\|[^|]+\|>', '', stream.result.text).strip()
        segments = [SimpleNamespace(text=text)] if text else []
        return iter(segments), SimpleNamespace(backend='sensevoice', language='zh')
