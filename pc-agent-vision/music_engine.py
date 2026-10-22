"""PCM music playback plus MIR features. No audio devices opened on import."""

import io
import math
import threading
import time
from collections import deque
from urllib.parse import urlsplit
from urllib.request import urlopen
import numpy as np


class MusicFeatures:
    def __init__(self, sample_rate=16000, size=1024):
        self.sample_rate = sample_rate
        self.size = size
        self.previous = np.zeros(size // 2 + 1)
        self.flux_history = deque(maxlen=43)
        self.onsets = deque(maxlen=12)
        self.last_onset = -10.0

    def analyze(self, samples, now):
        data = np.asarray(samples, dtype=np.float64)
        if data.shape != (self.size,) or not np.isfinite(data).all():
            raise ValueError("Invalid analysis frame")
        spectrum = np.abs(np.fft.rfft(data * np.hanning(self.size)))
        norm = spectrum / (np.linalg.norm(spectrum) + 1e-12)
        flux = float(np.maximum(0, norm - self.previous).sum())
        self.previous = norm
        rms = float(np.sqrt(np.mean(data * data)))
        baseline = float(np.median(self.flux_history)) if self.flux_history else 0
        onset = rms > 0.01 and flux > max(0.2, baseline * 1.5) and now - self.last_onset > 0.15
        self.flux_history.append(flux)
        if onset:
            self.last_onset = now
            self.onsets.append(now)
        intervals = np.diff(self.onsets)
        valid = intervals[(intervals >= 0.25) & (intervals <= 2)]
        tempo = float(np.clip(60 / np.median(valid), 30, 240)) if len(valid) else 120.0
        frequencies = np.fft.rfftfreq(self.size, 1 / self.sample_rate)
        edges = np.geomspace(20, self.sample_rate / 2, 17)
        bands = np.array(
            [
                (
                    spectrum[(frequencies >= edges[i]) & (frequencies < edges[i + 1])].mean()
                    if np.any((frequencies >= edges[i]) & (frequencies < edges[i + 1]))
                    else 0
                )
                for i in range(16)
            ]
        )
        peak = max(1e-8, float(bands.max()))
        levels = np.rint(np.log1p(9 * bands / peak) / np.log(10) * 15).astype(int)
        return dict(
            energy=float(np.clip(rms * 4, 0, 1)),
            flux=float(np.clip(flux / 5, 0, 1)),
            onset=bool(onset),
            tempo=tempo,
            beat_phase=float(((now - self.last_onset) * tempo / 60) % 1),
            centroid=float(np.sum(frequencies * spectrum) / max(1e-8, spectrum.sum())),
            bands=levels.tolist(),
        )


def decode_audio(raw):
    import soundfile as sf
    from scipy.signal import resample_poly

    data, rate = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
    if not 1 <= len(data) <= rate * 1800 or rate < 8000 or rate > 192000:
        raise ValueError("Music duration/rate outside limits")
    mono = data.mean(axis=1)
    if rate != 16000:
        divisor = math.gcd(rate, 16000)
        mono = resample_poly(mono, 16000 // divisor, rate // divisor)
    return (np.clip(mono, -1, 1) * 32767).astype("<i2").tobytes()


class MusicPlayer:
    def __init__(self, controller):
        self.controller = controller
        self.cancel = threading.Event()
        self.thread = None
        self.error = None
        self.features = {}
        self.running = False

    def play(self, raw, fluid=True):
        pcm = decode_audio(raw)
        self.stop()
        self.cancel.clear()
        self.error = None
        if not self.controller.set_mode(30 if fluid else 15):
            raise ConnectionError("Board rejected music mode")
        self.running = True
        self.thread = threading.Thread(target=self._run, args=(pcm,), daemon=True)
        self.thread.start()

    def play_url(self, url):
        if not isinstance(url, str):
            raise ValueError("Audio URL must be a string")
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Use a direct HTTP(S) audio URL")
        with urlopen(url, timeout=15) as response:
            raw = response.read(20 * 1024 * 1024 + 1)
        if len(raw) > 20 * 1024 * 1024:
            raise ValueError("Music file exceeds 20 MiB")
        self.play(raw)

    def _run(self, pcm):
        self.running = True
        analysis_stop = threading.Event()

        def analyze():
            engine = MusicFeatures()
            samples = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768
            start = time.monotonic()
            for offset in range(0, len(samples) - engine.size + 1, 512):
                if self.cancel.is_set() or analysis_stop.is_set():
                    break
                wait = start + offset / 16000 - time.monotonic()
                if wait > 0 and self.cancel.wait(wait):
                    break
                f = engine.analyze(samples[offset : offset + engine.size], offset / 16000)
                self.features = f
                if not self.controller.music_features(
                    f["energy"], f["flux"], f["onset"], f["tempo"], f["beat_phase"]
                ):
                    self.error = "MIR command not acknowledged"
                    break
                self.controller.send_raw(
                    "f," + str(int(f["onset"])) + "," + ",".join(map(str, f["bands"]))
                )

        worker = threading.Thread(target=analyze, daemon=True)
        worker.start()
        try:
            if not self.controller.play_audio_pcm(pcm):
                self.error = "PCM playback not confirmed or cancelled"
        except Exception as exc:
            self.error = str(exc)
        finally:
            analysis_stop.set()
            worker.join(timeout=3)
            self.running = False

    def stop(self):
        self.cancel.set()
        client = getattr(self.controller, "_network_audio", None)
        if client:
            client.cancelled.set()
        cancel = getattr(self.controller, "playback_cancel", None)
        if cancel:
            cancel.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=4)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Previous music playback has not stopped")
        self.running = False
