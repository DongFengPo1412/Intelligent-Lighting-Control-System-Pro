"""Offline, look-ahead digital peak control. Does not model analog speaker limits."""

import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d

SPEECH_TARGET_RMS = 0.07
SPEECH_PEAK_CEILING = 0.22
SPEECH_DSP_PROFILE = 'rms070-peak220-v1'


def limit_peaks(samples, sample_rate=32000, ceiling=0.82):
    """Attenuate a smooth envelope around peaks instead of clipping their waveform.

    The peak window is wider than the smoothing window, so every gain value
    averaged at sample i is already safe for sample i. No sample hard clipping,
    inserted silence, or extra physical playback latency is required.
    """
    data = np.asarray(samples, dtype=np.float64)
    if data.ndim != 1 or not np.isfinite(data).all():
        raise ValueError("Expected finite mono audio")
    if not 0 < ceiling < 1 or sample_rate < 8000:
        raise ValueError("Invalid limiter configuration")
    if not data.size:
        return data.copy()
    radius = max(1, int(sample_rate * 0.008))
    peaks = maximum_filter1d(np.abs(data), size=4 * radius + 1, mode="nearest")
    gain = np.minimum(1.0, ceiling / np.maximum(peaks, 1e-12))
    gain = uniform_filter1d(gain, size=2 * radius + 1, mode="nearest")
    return data * gain


def coalesce_speech_chunks(chunks, max_chars=48):
    """Keep short neighbouring sentences in one synthesis request."""
    result = []
    for chunk in chunks:
        if result and len(result[-1]) + len(chunk) <= max_chars:
            result[-1] += chunk
        else:
            result.append(chunk)
    return result
