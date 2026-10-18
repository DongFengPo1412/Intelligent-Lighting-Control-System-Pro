import sys
import os
import time
import numpy as np
import threading
import queue

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
from light_controller import get_light_controller

ctrl = get_light_controller()
print("[测试] 正在测试板载 INMP441 麦克风实时数据流与 VAD 能量检测...")

# 单极点 DC 阻断器状态
prev_x = 0.0
prev_y = 0.0
alpha = 0.995

energies = []
start_t = time.time()

def on_mic(b):
    global prev_x, prev_y
    if len(b) < 4:
        return
    samples = np.frombuffer(b, dtype=np.int16).astype(np.float32)
    # 单极点高效 DC 阻断滤波
    filtered = np.zeros_like(samples)
    for i in range(len(samples)):
        curr_x = samples[i]
        curr_y = curr_x - prev_x + alpha * prev_y
        filtered[i] = curr_y
        prev_x = curr_x
        prev_y = curr_y
    
    rms = float(np.sqrt(np.mean(filtered**2)))
    energies.append(rms)
    # 动态打印能量条
    bars = int(min(40, rms // 200))
    bar_str = "#" * bars
    sys.stdout.write(f"\r[板载麦克风 RMS 能量]: {rms:6.1f} | {bar_str:<40}")
    sys.stdout.flush()

ctrl.on_mic_data = on_mic
ctrl.enable_mic(True)

# 实时监测 4 秒
time.sleep(4.0)

ctrl.enable_mic(False)
ctrl.close()

print(f"\n[测试完成] 共采集 {len(energies)} 帧音频。平均能量: {np.mean(energies):.1f}, 峰值能量: {max(energies):.1f}")
