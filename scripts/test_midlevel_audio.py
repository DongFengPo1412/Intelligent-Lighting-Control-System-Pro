import os
import sys
import time
import wave
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, "pc-agent-vision"))

from light_controller import get_light_controller

def main():
    ctrl = get_light_controller()
    if not ctrl.is_connected:
        print("[错误]: 无法连接板子 COM9！")
        return

    print("=================================================================")
    print("  🚀 固件底层已完全升级为【中阶 NoAudioCodec 32-bit Slot 标准】 ")
    print("     - I2S TX: 32-bit Slot MONO (I2S_STD_SLOT_LEFT)")
    print("     - BCLK: 64 周期完整 Philips 帧 (彻底消除 MAX98357A PLL 抖动电磁音)")
    print("     - 数据映射: 16-bit 线性乘 65536 映射至 32-bit 高位")
    print("=================================================================")

    # 1. 先播放纯净硬件正弦波自检音
    print("\n-> 1. 播放硬件正弦波提示音 (滴-)...")
    ctrl.play_beep()
    time.sleep(1.2)

    # 2. 播放牧濑红莉栖纯正原声
    pcm_path = os.path.join(repo_root, "pc-agent-vision", "kurisu_wake_reply.pcm")
    if os.path.exists(pcm_path):
        raw_pcm = np.fromfile(pcm_path, dtype=np.int16)
        print(f"-> 2. 播放牧濑红莉栖原声 (共 {len(raw_pcm)/16000:.2f} 秒)...")
        ctrl.play_audio_pcm(raw_pcm.tobytes())
        print("-> 播放完成！")

if __name__ == "__main__":
    main()
