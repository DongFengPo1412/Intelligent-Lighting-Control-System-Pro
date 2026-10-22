"""Optional reference NLMS for experimental barge-in; acoustic tuning is required."""

from collections import deque
import threading
import numpy as np


class EchoCanceller:
    def __init__(self, taps=128, delay_samples=1920, rate=0.15):
        self.weights = np.zeros(taps)
        self.history = np.zeros(taps)
        self.rate = rate
        self.reference = deque([0.0] * delay_samples)
        self.lock = threading.Lock()

    def feed_reference(self, pcm):
        samples = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768
        with self.lock:
            self.reference.extend(samples.tolist())
            while len(self.reference) > 64000:
                self.reference.popleft()

    def process(self, pcm):
        mic = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768
        out = np.empty_like(mic)
        with self.lock:
            for i, value in enumerate(mic):
                ref = self.reference.popleft() if self.reference else 0.0
                self.history[1:] = self.history[:-1]
                self.history[0] = ref
                predicted = float(self.weights @ self.history)
                error = value - predicted
                # Simple double-talk guard; this does not guarantee acoustic AEC.
                power = float(self.history @ self.history)
                if power > 0.001 and abs(value) < max(0.02, np.sqrt(power) * 2):
                    self.weights += self.rate * error * self.history / (power + 1e-6)
                out[i] = error
        return (np.clip(out, -1, 1) * 32767).astype("<i2").tobytes()
