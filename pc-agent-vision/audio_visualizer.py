"""
audio_visualizer.py: 16 频段真音乐物理频谱发射机 (移植自中阶 audio_service.cc)
将麦克风或声卡音频流实时转换为 16 频段对数能谱与鼓点 (Beat Detection)
并通过 Wi-Fi 命令通道向 ESP32-S3 Mode 15 直推 "f,beat,b0,b1...b15" 物理驱动协议
"""

import sys
import time
import math
import numpy as np
import pyaudio

from light_controller import get_light_controller

# 24kHz/16kHz 专属 16 频带对数边界分割点 (复刻中阶 audio_service.cc band_edges)
BAND_EDGES = [1, 2, 3, 4, 5, 7, 9, 12, 16, 22, 30, 41, 56, 76, 103, 140, 200]

class AudioVisualizer:
    def __init__(self, sample_rate=16000, chunk_size=512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.controller = get_light_controller()
        self.peak_tracker = 0.05
        self.prev_low_energy = 0.0
        self.is_running = False

    def start_stream(self, device_index=None):
        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
        except Exception as e:
            print(f"[AudioVisualizer 错误]: 无法开启音频采集设备: {e}")
            p.terminate()
            return

        print("=" * 60)
        print("  🎵 智光魔方 Pro · 16 频段物理音乐频谱引擎已启动")
        print("  ● 采样率: 16000 Hz, FFT 分辨率: 512")
        print("  ● 协议: f,beat,b0,b1...b15 实时推流")
        print("  ● 正在切换灯板至: 模式 15 (音乐随动频谱)...")
        print("=" * 60)

        self.is_running = True
        try:
            if not self.controller.set_mode(15):
                raise ConnectionError("Spectrum mode was not acknowledged over Wi-Fi")
            while self.is_running:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                # 汉宁窗加权，平滑频谱截断效应
                windowed = samples * np.hanning(len(samples))
                fft_complex = np.fft.rfft(windowed)
                magnitude = np.abs(fft_complex)

                # 16 频带能量聚合
                raw_avgs = np.zeros(16, dtype=np.float32)
                current_max = 0.0

                for b in range(16):
                    start_idx = min(BAND_EDGES[b], len(magnitude) - 1)
                    end_idx = min(BAND_EDGES[b + 1], len(magnitude))
                    if end_idx > start_idx:
                        avg_val = float(np.mean(magnitude[start_idx:end_idx]))
                    else:
                        avg_val = float(magnitude[start_idx])
                    raw_avgs[b] = avg_val
                    if avg_val > current_max:
                        current_max = avg_val

                # 峰值动态追踪
                self.peak_tracker *= 0.96
                if current_max > self.peak_tracker:
                    self.peak_tracker = current_max
                if self.peak_tracker < 0.01:
                    self.peak_tracker = 0.01

                # 对数压缩归一化到 0~15 高度
                bands = []
                for b in range(16):
                    norm = raw_avgs[b] / self.peak_tracker
                    log_val = math.log(1.0 + norm * 9.0) / math.log(10.0)
                    h = int(log_val * 15.0)
                    if b >= 13:
                        h = int(h * 0.7) # 高频轻微衰减，符合听感
                    h = max(0, min(15, h))
                    bands.append(h)

                # 低频重音检测 (Beat Detection)
                low_energy = float(np.sum(magnitude[BAND_EDGES[0]:BAND_EDGES[3]]))
                rms = float(np.sqrt(np.mean(samples**2)))
                is_beat = 1 if (low_energy > self.prev_low_energy * 1.35 and low_energy > 0.12 and rms > 0.02) else 0
                self.prev_low_energy = low_energy * 0.6 + self.prev_low_energy * 0.4

                # 打包中阶原生串口协议: f,beat,b0,b1...b15
                band_str = ",".join(str(b) for b in bands)
                packet = f"f,{is_beat},{band_str}"

                if self.controller.control_connected:
                    self.controller.send_raw(packet)

        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            # 退出时恢复为红莉栖桌宠模式
            restored = False
            if self.controller.control_connected:
                restored = self.controller.set_mode(17) and self.controller.set_brightness(20)
            print("[AudioVisualizer] 推流停止；桌宠已恢复。" if restored else
                  "[AudioVisualizer] 推流停止；灯板恢复未获确认。")

if __name__ == "__main__":
    vis = AudioVisualizer()
    vis.start_stream()
