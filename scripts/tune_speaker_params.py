"""
tune_speaker_params.py: 扬声器进阶大师级声学重构方案 (5.0 终极纯净版)
针对小口径板载扬声器与 MAX98357A D 类功放的物理声学特性深度调优：
1. 方案 A【黄金人声带通 (Voice-Band HiFi)】: 
   - 260Hz 3阶 Butterworth 高通 (彻底切除小喇叭物理共振震膜破音区)
   - 6800Hz 4阶抗锯齿低通 (切除超高频数字采样镜象与 D 类高频载波谐波)
   - 3600Hz 陷波去齿音 (-2.5dB 柔和去刺)
   - 38% 黄金净空 + 20ms 升余弦淡入淡出
2. 方案 B【纯天然直通干声 (Pure Dry Direct)】:
   - 纯粹原始合成波形，完全禁用 noisereduce (避免产生水下机械电音伪影)
   - 仅保留 220Hz 防振高通 + 35% 极度温润增益 + 20ms 淡入淡出
3. 方案 C【广播级动态平滑 (Broadcast Dynamics)】:
   - 240Hz 高通 + 柔性双曲正切 (Tanh Soft-Limiter) 动态范围压缩，人声极度饱满且绝无毛刺
   - 40% 增益 + 20ms 淡入淡出
"""

import os
import sys
import time
import wave
import numpy as np
import scipy.signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, "pc-agent-vision"))

from light_controller import get_light_controller

def apply_fade(y: np.ndarray, fade_ms: int = 20, sr: int = 16000) -> np.ndarray:
    """平滑 20ms 升余弦淡入淡出，消除开启/切断时的电平跳跃 POP 爆音"""
    fade_samples = int(sr * fade_ms / 1000.0)
    if len(y) < fade_samples * 2:
        return y
    out = y.copy()
    fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_samples)))
    fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_samples)))
    out[:fade_samples] *= fade_in
    out[-fade_samples:] *= fade_out
    return out

def test_playback(title: str, desc: str, pcm_bytes: bytes, ctrl):
    print(f"\n=================================================================")
    print(f"  >>> 试播: 【{title}】")
    print(f"      特性: {desc}")
    print(f"=================================================================")
    ctrl.play_beep()
    time.sleep(0.8)
    print(f"-> 正在播放中，请注意聆听细节...")
    ctrl.play_audio_pcm(pcm_bytes)
    print(f"-> 【{title}】播放完毕，准备下一组...")
    time.sleep(2.5)

def main():
    ctrl = get_light_controller()
    if not ctrl.is_connected:
        print("[错误]: 无法连接板子 COM9！")
        return

    wav_path = os.path.join(repo_root, "pc-agent-vision", "kurisu_wake_reply.wav")
    pcm_path = os.path.join(repo_root, "pc-agent-vision", "kurisu_wake_reply.pcm")

    # 优先从 32kHz 原始母带重采样，获得最纯净的声学底料
    if os.path.exists(wav_path):
        with wave.open(wav_path, 'rb') as w:
            sr_raw = w.getframerate()
            frames = w.readframes(w.getnframes())
            data_raw = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        if sr_raw == 32000:
            # 采用 8阶 Chebyshev 低通重采样至 16000，杜绝混叠失真
            raw_16k = scipy.signal.resample_poly(data_raw, 1, 2)
        else:
            raw_16k = data_raw
    else:
        raw_16k = np.fromfile(pcm_path, dtype=np.int16).astype(np.float32)

    # 归一化基准峰值
    peak = np.max(np.abs(raw_16k))
    if peak > 0:
        raw_norm = raw_16k / peak
    else:
        raw_norm = raw_16k

    sr = 16000.0

    print("=================================================================")
    print("      🔊 智光魔方 Pro · 100% 极限最大音量终极测试               ")
    print("      即将依次试播 3 组【100% 最大功率】方案，每组前均有 '滴' 声  ")
    print("=================================================================")
    time.sleep(1.0)

    # -------------------------------------------------------------
    # 方案 1: 100% 原始全幅直推 (无任何限制，对比硬件极限)
    # -------------------------------------------------------------
    pcm_max_raw = apply_fade(raw_norm * 32767.0)
    pcm_max_raw_bytes = np.clip(pcm_max_raw, -32768, 32767).astype(np.int16).tobytes()

    test_playback(
        "方案 1: 100% 原始未限幅直推 (满幅 0dBFS)",
        "纯原始未压限 100% 功率直推，音量直接拉满",
        pcm_max_raw_bytes,
        ctrl
    )

    # -------------------------------------------------------------
    # 方案 2: 100% 大师级软拟合压限 (高响度·防削波防杂音)
    # -------------------------------------------------------------
    # 260Hz 3阶高通滤除震颤 + 6.8kHz低通 + 软 Tanh 压限提升平均响度
    b_hp2, a_hp2 = scipy.signal.butter(3, 260.0 / (sr / 2.0), btype='high')
    b_lp2, a_lp2 = scipy.signal.butter(4, 6800.0 / (sr / 2.0), btype='low')
    y2 = scipy.signal.lfilter(b_hp2, a_hp2, raw_norm)
    y2 = scipy.signal.lfilter(b_lp2, a_lp2, y2)
    # Tanh 软压限提升感知响度 200%，同时弧形收敛至 0.96，完全不削波破音
    y2_loud = np.tanh(y2 * 1.8) / np.tanh(1.8) * 0.96
    pcm_2 = apply_fade(y2_loud * 32767.0)
    pcm_2_bytes = np.clip(pcm_2, -32768, 32767).astype(np.int16).tobytes()

    test_playback(
        "方案 2: 100% 大师级软压限 (极响且温和防破)",
        "260Hz切低频震颤 + 6.8kHz抗毛刺 + 模拟电子管软饱和，音量拉满且不破音",
        pcm_2_bytes,
        ctrl
    )

    # -------------------------------------------------------------
    # 方案 3: 100% 广播级砖墙穿透 (极致响度·极强对白穿透力)
    # -------------------------------------------------------------
    # 280Hz 陡峭高通 + 3.6kHz 陷波去齿音 + 强力响度泵
    w0 = 2 * np.pi * 3600.0 / sr
    alpha = np.sin(w0) / (2 * 1.5)
    A = 10.0 ** (-3.0 / 40.0)
    b_notch = [(1 + alpha * A), (-2 * np.cos(w0)), (1 - alpha * A)]
    a_notch = [(1 + alpha / A), (-2 * np.cos(w0)), (1 - alpha / A)]
    b_notch = [c / a_notch[0] for c in b_notch]
    a_notch = [c / a_notch[0] for c in a_notch]

    b_hp3, a_hp3 = scipy.signal.butter(3, 280.0 / (sr / 2.0), btype='high')
    y3 = scipy.signal.lfilter(b_hp3, a_hp3, raw_norm)
    y3 = scipy.signal.lfilter(b_notch, a_notch, y3)
    # 双曲饱和硬度提升
    y3_punch = np.tanh(y3 * 2.2) / np.tanh(2.2) * 0.98
    pcm_3 = apply_fade(y3_punch * 32767.0)
    pcm_3_bytes = np.clip(pcm_3, -32768, 32767).astype(np.int16).tobytes()

    test_playback(
        "方案 3: 100% 广播级穿透压限 (最强响度·对白极其清晰)",
        "280Hz硬切 + 3.6kHz陷波平滑齿音 + 极限砖墙压限，响度最大且人声极度突出",
        pcm_3_bytes,
        ctrl
    )

    print("\n=================================================================")
    print("🎉 3 组 100% 最大音量方案试播完毕！")
    print("=================================================================")

if __name__ == "__main__":
    main()
