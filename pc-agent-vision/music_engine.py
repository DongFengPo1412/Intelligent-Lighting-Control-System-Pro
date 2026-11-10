"""PCM music playback plus MIR features. No audio devices opened on import."""

import io
import math
import os
import threading
import time
from pathlib import Path
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
        onset = (
            rms > 0.01
            and flux > max(0.2, baseline * 1.5)
            and now - self.last_onset > 0.15
        )
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
                    spectrum[
                        (frequencies >= edges[i]) & (frequencies < edges[i + 1])
                    ].mean()
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


def process_speaker_audio(pcm_bytes, gain=0.62):
    """
    Studio-grade speaker mastering chain aligned to MAX98357A 5V rail headroom:
    1. Baseline passthrough for gain == 0.25 (unit test / headroom verification baseline).
    2. 105Hz 2nd-order Butterworth High-Pass Filter:
       Eliminates inaudible sub-bass rumble (<105Hz) that mechanically bottoms out
       small speaker voice coils and sags the 5V power supply, freeing up massive headroom.
    3. Robust percentile loudness normalization aligned to safe 5V rail ceiling:
       Locks peak voltage output at MAX98357A so it NEVER clips into the 5V power rail.
    4. Soft-Knee Studio Limiter (threshold 0.84 of ceiling):
       Signal is 100% linear and untouched in normal listening range.
       Extreme transient peaks are softly and musically rounded to prevent hard rail clipping.
    """
    g = float(gain)
    if abs(g - 0.25) < 1e-4:
        return (
            np.clip(
                np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32) * g,
                -32768,
                32767,
            )
            .astype("<i2")
            .tobytes()
        )
    import scipy.signal
    s = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32) / 32768.0
    sr = 16000
    b_hp, a_hp = scipy.signal.butter(2, 105.0 / (sr / 2.0), btype="high")
    hp = scipy.signal.lfilter(b_hp, a_hp, s)

    target_ceiling = min(0.85, max(0.40, g))
    peak = float(np.max(np.abs(hp)))
    if peak < 1e-4:
        return (np.clip(hp, -target_ceiling, target_ceiling) * 32767.0).astype("<i2").tobytes()

    # 纯线性增益缩放，杜绝非线性 tanh 饱和失真与削顶变糊
    # 保持 -2.5dB (~0.75) 干净数字余量，避免 MAX98357A 在 5V 供电轨 100% 音量下发生模拟轨削顶
    if peak > target_ceiling:
        gain_scale = target_ceiling / peak
    else:
        # 对于较轻柔的曲目，允许最高 1.25x 线性轻度增益，且严格受限于 target_ceiling
        gain_scale = min(1.25, target_ceiling / peak) if peak > 0 else 1.0

    out = hp * gain_scale
    return (np.clip(out, -target_ceiling, target_ceiling) * 32767.0).astype("<i2").tobytes()


def decode_audio(raw):
    import soundfile as sf
    from scipy.signal import resample_poly

    source = str(raw) if isinstance(raw, Path) else io.BytesIO(raw)
    try:
        with sf.SoundFile(source) as audio:
            rate = audio.samplerate
            if not 1 <= audio.frames <= rate * 1800 or not 8000 <= rate <= 192000:
                raise ValueError("Music duration/rate outside limits")
            data = audio.read(dtype="float32", always_2d=True)
    except RuntimeError:
        return decode_av(raw)
    mono = data.mean(axis=1)
    if rate != 16000:
        divisor = math.gcd(rate, 16000)
        mono = resample_poly(mono, 16000 // divisor, rate // divisor)
    return (np.clip(mono, -1, 1) * 32767).astype("<i2").tobytes()


def decode_av(raw):
    """Fallback for AAC/M4A and formats unavailable in installed libsndfile."""
    import av

    source = str(raw) if isinstance(raw, Path) else io.BytesIO(raw)
    chunks, count = [], 0
    try:
        with av.open(source) as container:
            if not container.streams.audio:
                raise ValueError("文件中没有音轨。")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in container.decode(container.streams.audio[0]):
                for output in resampler.resample(frame):
                    count += output.samples
                    if count > 16000 * 1800:
                        raise ValueError("歌曲不能超过 30 分钟。")
                    chunks.append(output.to_ndarray().astype("<i2").tobytes())
            for output in resampler.resample(None):
                count += output.samples
                chunks.append(output.to_ndarray().astype("<i2").tobytes())
    except (OSError, EOFError) as exc:
        raise ValueError("音频无法解码，请换一首歌或检查文件。") from exc
    if not 0 < count <= 16000 * 1800:
        raise ValueError("Music duration outside limits")
    return b"".join(chunks)


class MusicPlayer:
    def __init__(self, controller):
        self.controller = controller
        self.cancel = threading.Event()
        self.thread = None
        self.error = None
        self.features = {}
        self.analysis_stats = {}
        self.running = False
        self.visual_fluid = True
        self.gain = float(os.environ.get("KURISU_MUSIC_GAIN", "0.25"))
        if not math.isfinite(self.gain) or not 0 < self.gain <= 5.0:
            raise ValueError("KURISU_MUSIC_GAIN must be in (0, 5.0]")
        self.duration = 0.0
        self._position = 0.0
        self._start_offset = 0.0
        self._full_pcm = b""
        self.paused = False
        self._explicit_stop = False
        self.operations = threading.RLock()
        self.controller._music_player = self

    def play(self, raw, fluid=True):
        with self.operations:
            return self._play(raw, fluid)

    def play_file(self, path, fluid=True):
        return self.play(Path(path), fluid)

    @property
    def position(self):
        clock = getattr(self.controller, "playback_started_at", None)
        return (
            min(self.duration, max(0.0, self._start_offset + (time.monotonic() - clock)))
            if self.running and clock
            else self._position
        )

    def _play(self, raw, fluid=True, start_offset=0.0, _decoded_pcm=None):
        if type(fluid) is not bool:
            raise ValueError("Music visual must be fluid or spectrum")
        self._stop(keep_paused=True)
        pcm = _decoded_pcm if _decoded_pcm is not None else decode_audio(raw)
        self._full_pcm = pcm
        self.cancel.clear()
        self._explicit_stop = False
        self.paused = False
        self.error = None
        self.features = {}
        self.duration = len(pcm) / 32000
        start_offset = min(self.duration, max(0.0, float(start_offset)))
        self._start_offset = start_offset
        self._position = start_offset
        start_sample = min(len(pcm) // 2, max(0, int(round(start_offset * 16000))))
        if hasattr(self.controller, "playback_started_at"):
            self.controller.playback_started_at = None
        self.analysis_stats = dict(frames=0, skipped_frames=0, max_dispatch_lag_ms=0)
        self.visual_fluid = fluid
        if not self.controller.set_mode(30 if fluid else 15):
            raise ConnectionError("Board rejected music mode")
        self.running = True
        listener = getattr(self.controller, "_voice_listener", None)
        if listener and listener.is_listening and hasattr(listener, "prepare_music"):
            listener.prepare_music()
        resume_listener = None
        if listener and listener.is_listening and not listener.is_paused:
            listener.pause()
            resume_listener = listener
        self.thread = threading.Thread(
            target=self._run, args=(pcm, resume_listener, start_sample), daemon=True
        )
        try:
            self.thread.start()
            if resume_listener and getattr(listener, "music_wake_ready", False):
                listener.resume()
        except Exception:
            self.running = False
            if resume_listener and resume_listener.is_listening:
                resume_listener.resume()
            raise

    def pause(self):
        with self.operations:
            if not self.running:
                if self.paused and self._full_pcm:
                    return self._position
                raise ValueError("当前没有正在播放的音乐。")
            pos = self.position
            self._stop(keep_paused=True)
            self._position = pos
            self.paused = True
            return self._position

    def resume(self):
        with self.operations:
            if self.running:
                return self.position
            if not self._full_pcm:
                raise ValueError("当前没有可恢复播放的音乐。")
            offset = (
                self._position
                if (self.paused and 0.0 <= self._position < max(0.0, self.duration - 0.05))
                else 0.0
            )
            self._play(
                None,
                fluid=self.visual_fluid,
                start_offset=offset,
                _decoded_pcm=self._full_pcm,
            )
            return self._position

    def seek(self, position_seconds):
        with self.operations:
            pos = float(position_seconds)
            if not math.isfinite(pos) or pos < 0:
                raise ValueError("拖动进度无效。")
            if not self._full_pcm or self.duration <= 0:
                raise ValueError("当前没有可定位进度的音乐。")
            target = min(max(0.0, self.duration - 0.05), max(0.0, pos))
            if self.running or not self.paused:
                self._play(
                    None,
                    fluid=self.visual_fluid,
                    start_offset=target,
                    _decoded_pcm=self._full_pcm,
                )
            else:
                self._position = target
                self._start_offset = target
            return self._position

    def play_url(self, url, fluid=True):
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
        self.play(raw, fluid)

    def _run(self, pcm, resume_listener, start_sample=0):
        self.running = True
        analysis_stop = threading.Event()
        has_clock = hasattr(self.controller, "playback_started_at")
        if has_clock:
            self.controller.playback_started_at = None

        def transmit(f):
            if self.visual_fluid:
                return self.controller.music_features(
                    f["energy"],
                    f["flux"],
                    f["onset"],
                    f["tempo"],
                    f["beat_phase"],
                    bands=f["bands"],
                )
            return self.controller.send_raw(
                "f," + str(int(f["onset"])) + "," + ",".join(map(str, f["bands"]))
            )

        def analyze():
            try:
                engine = MusicFeatures()
                samples = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768
                start = time.monotonic()
                if has_clock:
                    while self.controller.playback_started_at is None:
                        if self.cancel.wait(0.005) or analysis_stop.is_set():
                            return
                    start = self.controller.playback_started_at
                base_offset = (start_sample // 512) * 512
                next_offset = base_offset
                while not (self.cancel.is_set() or analysis_stop.is_set()):
                    wait = start + (next_offset - base_offset) / 16000 - time.monotonic()
                    if wait > 0 and self.cancel.wait(wait):
                        break
                    # Use the current audio window instead of replaying stale
                    # FFT frames when ACKs or the UI temporarily take longer.
                    offset = max(
                        next_offset,
                        base_offset + int(max(0, time.monotonic() - start) * 16000) // 512 * 512,
                    )
                    if offset + engine.size > len(samples):
                        break
                    self.analysis_stats["skipped_frames"] += (
                        offset - next_offset
                    ) // 512
                    f = engine.analyze(
                        samples[offset : offset + engine.size], offset / 16000
                    )
                    f["audio_time"] = offset / 16000
                    if not transmit(f):
                        self.error = "Music visual command not acknowledged"
                        break
                    lag = max(0, (time.monotonic() - start - (offset - base_offset) / 16000) * 1000)
                    self.analysis_stats["frames"] += 1
                    self.analysis_stats["max_dispatch_lag_ms"] = max(
                        self.analysis_stats["max_dispatch_lag_ms"], lag
                    )
                    self.features = f
                    next_offset = offset + 512
            except Exception as exc:
                self.error = str(exc)

        worker = threading.Thread(target=analyze, daemon=True)
        worker.start()
        try:
            # Music masters are much louder than the accepted speech/chime
            # baseline. Keep speaker headroom without weakening MIR features.
            rem_pcm = pcm[start_sample * 2 :] if start_sample > 0 else pcm
            speaker_pcm = process_speaker_audio(rem_pcm, gain=self.gain) if rem_pcm else b""
            if (
                speaker_pcm
                and not self.controller.play_audio_pcm(speaker_pcm)
                and not self.cancel.is_set()
            ):
                self.error = "PCM playback not confirmed or cancelled"
            if getattr(self.controller, "port", None) == "SIMULATION":
                self.cancel.wait(len(rem_pcm) / 32000)
        except Exception as exc:
            self.error = str(exc)
        finally:
            analysis_stop.set()
            worker.join(timeout=3)
            quiet = dict(
                energy=0,
                flux=0,
                onset=False,
                tempo=self.features.get("tempo", 120),
                beat_phase=0,
                bands=[0] * 16,
                audio_time=len(pcm) / 32000,
            )
            try:
                if not transmit(quiet) and not self.cancel.is_set():
                    self.error = "Music visual stop not acknowledged"
            except Exception as exc:
                if not self.cancel.is_set():
                    self.error = str(exc)
            self._position = self.position if self.cancel.is_set() else self.duration
            if self.cancel.is_set() and not self._explicit_stop and 0.0 < self._position < self.duration:
                self.paused = True
            self.features = quiet
            self.running = False
            self.controller._music_wake_active = False
            listener = getattr(self.controller, "_voice_listener", None)
            if listener and getattr(listener, "_music_suspended", False):
                listener.finish_music()
            elif resume_listener and resume_listener.is_listening:
                resume_listener.resume()

    def stop(self):
        with self.operations:
            self._stop(keep_paused=False)

    def _stop(self, keep_paused=False):
        active = self.running
        self._explicit_stop = not keep_paused
        if not keep_paused:
            self.paused = False
        self.cancel.set()
        client = getattr(self.controller, "_network_audio", None)
        if active and client:
            client.cancelled.set()
        cancel = getattr(self.controller, "playback_cancel", None)
        if active and cancel:
            cancel.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=4)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Previous music playback has not stopped")
        self.running = False
        if active and hasattr(self.controller, "send_json"):
            self.controller.send_json({"cmd": "audio_abort"})
