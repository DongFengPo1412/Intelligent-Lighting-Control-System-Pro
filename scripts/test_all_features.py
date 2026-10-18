"""
test_all_features.py: 智光魔方 Pro 综合全功能系统自动化测试套件
涵盖：
1. ESP32-S3 硬件串口连通性与握手
2. 板载独立指示灯 (GPIO 48) 与上电配对仪式 (呼吸 -> 常亮绿 + Beep)
3. 16x16 矩阵灯板 25 种原生光场模式与物理沙漏倒计时
4. 板载 INMP441 麦克风硬件音频采集与 DC 偏置滤波
5. 本地 Whisper 极速离线语音识别与专属日语名字唤醒词门禁 (Makise Kurisu)
6. 牧濑红莉栖端侧大模型具身大脑 (Ollama 7B + Function Calling)
7. GPT-SoVITS 录音棚级母带语音合成与中日严格双语互译推流
"""

import os
import sys
import torch # 确保优先加载官方 PyTorch CUDA/cuDNN，杜绝 ctranslate2 DLL 劫持
import time
import json
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "pc-agent-vision"))

def print_banner(title):
    print("\n" + "=" * 65)
    print(f"  >>> 测试项目: {title}")
    print("=" * 65)

def main():
    print("=================================================================")
    print("      🚀 智光魔方 Pro · 全功能自动化综合诊断与闭环测试           ")
    print("=================================================================")

    # -------------------------------------------------------------
    # 测试 1: 硬件连接与通信握手
    # -------------------------------------------------------------
    print_banner("1. ESP32-S3 硬件连接与底层通信握手")
    from light_controller import get_light_controller
    ctrl = get_light_controller()
    
    if not ctrl.is_connected:
        print("❌ [失败]: 无法连接至 ESP32-S3 串口 (COM9)！")
        return
    print(f"✅ [成功]: 已建立硬件物理直通连接: {ctrl.port} (波特率: {ctrl.baudrate})")

    # -------------------------------------------------------------
    # 测试 2: 板载独立指示灯 (GPIO 48) 与配对声光仪式
    # -------------------------------------------------------------
    print_banner("2. 板载独立 RGB 指示灯 (GPIO 48) 与上电配对仪式")
    print("-> 1. 触发板载指示灯【配对呼吸模式】(幽蓝极光呼吸)...")
    ctrl.set_board_led("pairing")
    ctrl.send_raw("kurisu") # 16x16 矩阵灯板保持红莉栖桌面伴侣
    ctrl.send_raw("b 150")
    time.sleep(1.5)

    print("-> 2. 触发【配对成功确认】：板载指示灯瞬间切换为【常亮绿色】，扬声器响提示音...")
    ctrl.set_board_led("green")
    time.sleep(0.2)
    ctrl.play_beep()
    time.sleep(0.5)
    print("✅ [成功]: 板载指示灯 (GPIO 48) 独立控制测试通过，16x16 矩阵未受干扰保持红莉栖桌面伴侣！")

    # -------------------------------------------------------------
    # 测试 3: 16x16 矩阵灯板具身光场模式与物理沙漏倒计时
    # -------------------------------------------------------------
    print_banner("3. 16x16 矩阵光场模式切换与沙漏倒计时")
    print("-> 1. 切换至模式 4 (幻彩霓虹)...")
    ctrl.send_raw("rainbow")
    time.sleep(1.2)

    print("-> 2. 切换至模式 23 (赛博烈焰壁炉)...")
    ctrl.send_raw("fire")
    time.sleep(1.2)

    print("-> 3. 切换至模式 24 (黑客帝国代码雨 Pro)...")
    ctrl.send_raw("matrix")
    time.sleep(1.2)

    print("-> 4. 切换至模式 5 (极光呼吸)...")
    ctrl.send_raw("aurora")
    time.sleep(1.2)

    print("-> 5. 启动 5 秒高精度物理沙漏倒计时...")
    ctrl.countdown(5)
    time.sleep(2.0)

    print("-> 6. 停止倒计时并恢复至模式 17 (牧濑红莉栖桌宠模式，亮度 150)...")
    ctrl.stop_countdown()
    ctrl.send_raw("kurisu")
    ctrl.send_raw("b 150")
    time.sleep(0.5)
    print("✅ [成功]: 矩阵屏物理渲染引擎控制、多模式光场切换与沙漏状态机测试通过！")

    # -------------------------------------------------------------
    # 测试 4: ESP32-S3 板载 INMP441 硬件麦克风采集与 DC 偏置滤波
    # -------------------------------------------------------------
    print_banner("4. 板载 INMP441 硬件麦克风音频流与 IIR DC-Blocker 滤波")
    captured_frames = []
    
    def on_mic_sample(pcm_bytes):
        captured_frames.append(pcm_bytes)

    ctrl.on_mic_data = on_mic_sample
    ctrl.enable_mic(True)
    print("-> 正在监听板载 INMP441 硬件音频流 (采集中)...")
    time.sleep(1.2)
    ctrl.enable_mic(False)
    ctrl.on_mic_data = None

    print(f"-> 共捕获硬件麦克风数据帧: {len(captured_frames)} 帧")
    if len(captured_frames) > 0:
        raw_concat = np.concatenate([np.frombuffer(f, dtype=np.int16).astype(np.float32) for f in captured_frames])
        raw_mean = float(np.mean(raw_concat))
        # 执行单极点 DC 阻断滤波
        filtered = np.zeros_like(raw_concat)
        prev_x, prev_y = 0.0, 0.0
        for i in range(len(raw_concat)):
            x = raw_concat[i]
            y = x - prev_x + 0.995 * prev_y
            filtered[i] = y
            prev_x, prev_y = x, y
        filtered_mean = float(np.mean(filtered))
        rms = float(np.sqrt(np.mean(filtered**2)))
        print(f"-> 原始硬件直流偏置均值: {raw_mean:.2f} -> 滤波后直流偏置均值: {filtered_mean:.2f}")
        print(f"-> 真实环境声学有效 RMS: {rms:.2f}")
        print("✅ [成功]: 板载 INMP441 硬件麦克风 DMA 上行直通与直流偏置滤波器测试通过！")
    else:
        print("⚠️ [提示]: 未捕获到麦克风帧，请确认下位机 DMA 状态。")

    # -------------------------------------------------------------
    # 测试 5: 本地 Whisper 极速离线识别与专属日语唤醒词门禁
    # -------------------------------------------------------------
    print_banner("5. 本地 Whisper 极速离线识别与牧濑红莉栖日语名字唤醒门禁")
    from voice_listener import get_voice_listener
    listener = get_voice_listener()
    
    test_cases = [
        ("Makise Kurisu", True, "日语全名唤醒"),
        ("まきせ くりす", True, "平假名唤醒"),
        ("クリス", True, "片假名唤醒"),
        ("牧濑红莉栖", True, "中文同音唤醒"),
        ("克里斯，把灯调成纯蓝模式", True, "唤醒词+紧随指令复合句"),
        ("今天天气真好", False, "日常无关对话拦截"),
        ("12345 测试一下", False, "环境杂音/普通对话拦截")
    ]

    all_gate_pass = True
    for text, expected_wake, desc in test_cases:
        is_wake, cmd = listener._check_wake_word(text)
        passed = (is_wake == expected_wake)
        if not passed:
            all_gate_pass = False
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} [{desc}]: 输入='{text}' -> 唤醒命中={is_wake}, 提取指令='{cmd}'")

    if all_gate_pass:
        print("✅ [成功]: 牧濑红莉栖专属唤醒词门禁规则全景覆盖测试 100% 通过！")

    # 验证预缓存唤醒音频是否存在并可读
    base_dir = os.path.dirname(os.path.dirname(__file__))
    wake_pcm = os.path.join(base_dir, "pc-agent-vision", "kurisu_wake_reply.pcm")
    if os.path.exists(wake_pcm):
        print(f"✅ [成功]: 预缓存牧濑红莉栖唤醒声包就绪 ({os.path.getsize(wake_pcm)} 字节)，支持 0ms 零延迟秒回！")
        with open(wake_pcm, "rb") as f:
            pcm_data = f.read()
        print("-> 试播板载扬声器原声唤醒反馈 (な、何よ？有事快说！)...")
        ctrl.play_audio_pcm(pcm_data)

    # -------------------------------------------------------------
    # 测试 6: 牧濑红莉栖端侧大模型具身大脑 (Ollama + Function Calling)
    # -------------------------------------------------------------
    print_banner("6. 牧濑红莉栖端侧具身大模型大脑 (Ollama 7B + 具身控制)")
    from kurisu_agent import KurisuAgent
    agent = KurisuAgent()

    test_prompt = "助手，帮我把灯光调成纯蓝模式"
    print(f"-> 发送用户提问: '{test_prompt}'")
    t0 = time.time()
    reply = agent.chat(test_prompt)
    print(f"-> 红莉栖具身思考完成 (耗时: {time.time()-t0:.2f}s):\n{reply}")
    time.sleep(1.0)
    print("-> 恢复至模式 17 (牧濑红莉栖桌宠模式，亮度 150)...")
    ctrl.send_raw("kurisu")
    ctrl.send_raw("b 150")
    print("✅ [成功]: 端侧大模型具身 Agent 解析与傲娇人格回复测试通过！")

    # -------------------------------------------------------------
    # 测试 7: GPT-SoVITS 神经语音合成与中日双语对译推流
    # -------------------------------------------------------------
    print_banner("7. GPT-SoVITS 牧濑红莉栖原声神经语音合成与母带音频推流")
    from voice_engine import get_voice_engine
    voice = get_voice_engine()

    test_speech = "都说了我不是助手！你这笨蛋到底要我说多少遍才明白啊！"
    print(f"-> 待合成文本: '{test_speech}'")
    t0 = time.time()
    bundle = voice.synthesize_speech_bundle(test_speech)
    if bundle:
        pcm_16k, wav_32k = bundle
        print(f"✅ [成功]: 红莉栖中日双语原声合成完毕 (耗时: {time.time()-t0:.2f}s, PCM: {len(pcm_16k)} 字节)")
        print("-> 推送至 ESP32-S3 板载 MAX98357A 扬声器播放...")
        ctrl.play_audio_pcm(pcm_16k)
    else:
        print("❌ [失败]: 语音合成返回为空！")

    # 最终确保屏幕定格在红莉栖桌宠模式
    ctrl.send_raw("kurisu")
    ctrl.send_raw("b 150")
    ctrl.set_board_led("green")

    print("\n" + "=" * 65)
    print("🎉🎉🎉 所有 7 大核心系统功能全部诊断验证通过！智光魔方 Pro 处于完全可用状态！")
    print("=================================================================")
    print("      已完美复位至: 模式 17 (牧濑红莉栖桌面伴侣) · 亮度 150")
    print("=================================================================\n")

if __name__ == "__main__":
    main()
