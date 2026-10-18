"""
run_voice_daemon.py: 智光魔方 Pro · 牧濑红莉栖全自动免触实时语音对讲守护中枢
涵盖中阶完整状态机视觉反馈 (GPIO 48 板载指示灯):
- 幽蓝慢闪呼吸: 等待配对/初始化 (kDeviceStateWifiConfiguring/Starting)
- 幽蓝常亮 + Beep: 配对连接成功 (kDeviceStateConnecting)
- 微光暗红: 待命监听状态 (kDeviceStateListening Low)
- 鲜亮红光: 检测到人声说话 VAD 激活 (kDeviceStateListening High)
- 青蓝流光: 大模型思考运算中 (kDeviceStateThinking)
- 翠绿常亮: 语音播报输出中 (kDeviceStateSpeaking)
"""

import os
import sys
import time
import signal
import threading

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

# 确保加载 pc-agent-vision 模块
agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pc-agent-vision")
sys.path.insert(0, agent_dir)

from light_controller import get_light_controller
from voice_engine import get_voice_engine
from voice_listener import get_voice_listener
from kurisu_agent import KurisuAgent

def main():
    print("=" * 65)
    print("  🚀 智光魔方 Pro · 牧濑红莉栖端侧具身语音常驻守护中枢")
    print("  ● 硬件中枢: ESP32-S3 (COM9 @ 115200)")
    print("  ● 视觉伴侣: 模式 17 (牧濑红莉栖 16x16 像素艺术桌宠 · 亮度 150)")
    print("  ● 板载指示: GPIO 48 RGB (中阶全状态声光同步)")
    print("  ● 声学唤醒: 'Makise Kurisu' / '牧濑红莉栖' / '克里斯'")
    print("=" * 65)

    # 1. 优先加载具身大脑 (Ollama 7B + GPT-SoVITS + 本地 Whisper，约 4 秒)
    # 此时硬件处于原生上电配对呼吸灯中，待算法全部就绪后方执行配对确认，实现零时差无缝就绪
    print("\n[具身大脑] >>> 正在加载牧濑红莉栖端侧大模型 (Ollama 7B + GPT-SoVITS)...")
    agent = KurisuAgent()

    # 2. 建立与 ESP32-S3 的通信物理链路
    controller = get_light_controller()
    if not controller.is_connected:
        print("⏳ [硬件等待]: 正在等待 ESP32-S3 串口 (COM9) 就绪...")
        while not controller.connect():
            time.sleep(1.0)

    # 3. 准备语音交互中枢
    def on_voice_command(speech_text: str):
        if not speech_text or not speech_text.strip():
            return

        print(f"\n==================================================")
        print(f"🎙️ [用户语音指令]: {speech_text}")
        print(f"==================================================")

        try:
            # 切换板载指示灯为青蓝微呼吸 (思考计算中)
            controller.set_board_led("thinking")

            t0 = time.time()
            reply = agent.chat(speech_text)
            print(f"-> 思考耗时: {time.time()-t0:.2f}s")
            print(f"🤖 [红莉栖回复]:\n{reply}\n")

        except Exception as e:
            print(f"❌ [对话处理异常]: {e}")
        finally:
            # 交互完毕，板载 LED 回到微光暗红待命监听；不强行覆盖用户指定的灯光效果！
            controller.set_board_led("listening")

    listener = get_voice_listener(on_voice_command)

    # 4. 执行中阶风格上电与配对握手仪式 (幽蓝呼吸 1.5s -> 幽蓝常亮 0.4s + Beep -> 微光暗红监听)
    print("\n[系统启动] >>> 具身算法全部就绪，正在执行上电配对握手仪式...")
    controller.run_boot_ceremony(async_mode=False)

    # 5. 瞬间启动免触全自动语音监听中枢 (零延迟无缝进入待命监听)
    listener.start()

    print("\n" + "=" * 65)
    print("✅ 全链路免触语音中枢已完全就绪！")
    print("👉 请直接对准硬件板载麦克风说话即可唤醒交互！")
    print("   唤醒词示例: 'Makise Kurisu'、'牧濑红莉栖'、'克里斯，把灯调成烈焰模式'...")
    print("=" * 65 + "\n")

    # 6. 常驻看门狗循环 (支持硬件热插拔断线自动重配对)
    stop_event = threading.Event()

    def handle_sig(sig, frame):
        print("\n[守护进程] 正在优雅退出...")
        listener.stop()
        controller.send_raw("kurisu")
        controller.send_raw("b 150")
        controller.set_board_led("green")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        while not stop_event.is_set():
            time.sleep(1.0)
            # 硬件断线自动重连与自愈
            if not controller.is_connected:
                print("\n[看门狗] 检测到硬件连接断开，正在尝试重新连接 COM9...")
                if controller.connect():
                    print("[看门狗恢复] 重新连接至 ESP32-S3，执行配对自检恢复...")
                    controller.run_boot_ceremony(async_mode=False)
                    listener.resume()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        controller.set_board_led("green")
        print("[守护进程] 已安全停止。")

if __name__ == "__main__":
    main()
