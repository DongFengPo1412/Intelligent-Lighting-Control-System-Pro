"""Independent acoustic keyword gate; Whisper text alone cannot wake the device."""
from pathlib import Path
import sys
import threading
import numpy as np


class WakeDetector:
    def __init__(self, threshold=.50):
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / 'pc-agent-vision' / '.runtime_deps'))
        import sherpa_onnx
        model = root / 'models' / 'wake_kws'
        from pro_paths import cache_dir
        keyword_dir = cache_dir() / 'wake'
        keyword_dir.mkdir(parents=True, exist_ok=True)
        keywords = keyword_dir / 'kurisu_keywords.txt'
        keywords.write_text(
            'zh ù sh ǒu @助手\n'
            'h óng l ì q ī @红莉栖\n'
            'k è l ǐ s ī @克里斯\n'
            'm ù l ài h óng l ì q ī @牧濑红莉栖\n', encoding='utf-8')
        suffix = '-epoch-12-avg-2-chunk-16-left-64.int8.onnx'
        self.spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(model / 'tokens.txt'), encoder=str(model / ('encoder' + suffix)),
            decoder=str(model / ('decoder' + suffix)), joiner=str(model / ('joiner' + suffix)),
            keywords_file=str(keywords), keywords_threshold=threshold,
            keywords_score=1.0, num_trailing_blanks=2, num_threads=2)
        self._lock = threading.Lock()

    def detect(self, pcm_bytes):
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768
        samples -= np.mean(samples) if len(samples) else 0
        peak = float(np.max(np.abs(samples))) if len(samples) else 0
        if peak > 1e-5:
            samples *= min(8.0, .75 / peak)
        with self._lock:
            stream = self.spotter.create_stream()
            stream.accept_waveform(16000, np.concatenate([samples, np.zeros(8000, np.float32)]))
            stream.input_finished()
            while self.spotter.is_ready(stream):
                self.spotter.decode_stream(stream)
                keyword = self.spotter.get_result(stream)
                if keyword:
                    return keyword
        return ''
