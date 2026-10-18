import os
import wave
import numpy as np

def analyze(name, path):
    if not os.path.exists(path):
        print(f"{name}: file not found {path}")
        return
    if path.endswith(".pcm"):
        data = np.fromfile(path, dtype=np.int16)
        sr = 16000
    elif path.endswith(".wav"):
        with wave.open(path, 'rb') as w:
            sr = w.getframerate()
            frames = w.readframes(w.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)
    
    peak = np.max(np.abs(data))
    rms = np.sqrt(np.mean(data.astype(np.float64)**2))
    mean = np.mean(data)
    clipping_count = np.sum(np.abs(data) >= 32700)
    high_count = np.sum(np.abs(data) >= 28000)
    
    print(f"[{name}] Samples: {len(data)} ({len(data)/sr:.2f}s) | Peak: {peak} ({peak/32768*100:.1f}%) | RMS: {rms:.1f} | DC Mean: {mean:.2f}")
    print(f"      >=32700 (Hard clip): {clipping_count} | >=28000 (Near clip): {high_count}")

analyze("Wake PCM", "pc-agent-vision/kurisu_wake_reply.pcm")
analyze("Wake WAV", "pc-agent-vision/kurisu_wake_reply.wav")
analyze("Prompt Shy WAV", "models/kurisu_tts/prompt_shy.wav")
