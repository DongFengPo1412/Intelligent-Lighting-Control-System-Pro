"""
DemoKurisu: 牧濑红莉栖 (Makise Kurisu) 具身多模态智能体全流程交互系统
整合：
  1. 16x16 LED 矩阵光场直驱 (ESP32-S3 COM9: 物理沙漏倒计时 / 世界线变动率彩蛋 / 微表情)
  2. 中日双语神经声学引擎 (Windows SAPI5 Haruka/Huihui 零延迟语音输出)
  3. 麦克风实时语音采集 (VoiceListener ASR: 免打字全语音对话)
  4. 摄像头多模态视觉感知 (VisionTracker: 面部微笑与注视追踪)
  5. 具身 MCP (Model Context Protocol) 物理工具调度与傲娇科学家灵魂
"""

import sys
import os
import time
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from kurisu_agent import KurisuAgent
from light_controller import get_light_controller
from voice_engine import get_voice_engine
from wifi_gateway import get_wifi_gateway
from voice_listener import get_voice_listener
from vision_tracker import VisionTracker

def main():
    parser = argparse.ArgumentParser(description="牧濑红莉栖具身多模态交互系统")
    parser.add_argument("--voice", action="store_true", help="开启麦克风实时语音拾音")
    parser.add_argument("--vision", action="store_true", help="开启笔记本摄像头多模态微表情检测")
    parser.add_argument("--all", action="store_true", help="开启全部多模态感知 (语音+视觉+光场)")
    args = parser.parse_args()

    enable_voice = args.voice or args.all
    enable_vision = args.vision or args.all

    print("\n" + "="*68)
    print("      【牧濑红莉栖】具身多模态智能体交互中枢 (Makise Kurisu)      ")
    print("="*68)
    
    agent = KurisuAgent()
    voice = get_voice_engine()
    wifi = get_wifi_gateway()
    
    vision_tracker = None
    if enable_vision:
        print("[视觉就绪] 正在启动笔记本摄像头多模态微表情感知...")
        vision_tracker = VisionTracker()
        vision_tracker.start()

    def on_voice_heard(text: str):
        print(f"\n[语音识别输入] >> {text}")
        reply = agent.chat(text)
        print(f"[红莉栖]: {reply}\n")

    voice_listener = None
    if enable_voice:
        print("[听觉就绪] 正在启动麦克风实时拾音...")
        voice_listener = get_voice_listener(callback=on_voice_heard)
        voice_listener.start()

    print("\n[系统就绪] 硬件端口: COM9 | 无线网关: UDP 8888 | 离线神经语音: 就绪")
    print("\n交互指南:")
    print("  * 呼叫沙漏倒计时 : '红莉栖，帮我倒计时20秒' / '倒计时一分钟'")
    print("  * 触发世界线彩蛋 : '助手，汇报现在的世界线变动率'")
    print("  * 调节矩阵特效   : '点燃赛博烈焰' / '展示代码雨' / '换成彩虹波浪'")
    print("  * 情绪微表情互动 : '克里斯蒂娜，笑一个看看' / '你生气了吗'")
    print("  * 支持键盘打字回车发送，也支持直接对着麦克风说话！")
    print("  * 输入 'exit' 或 'quit' 退出系统\n")
    print("-" * 68)

    # 初始开场白
    greeting = "未来道具研究所 LabMem No.004，牧濑红莉栖。有什么实验需要协助吗？不过事先声明，绝对不准叫我助手！"
    print(f"\n[红莉栖]: {greeting}")
    voice.speak(greeting, block=True)

    try:
        while True:
            user_input = input("\n[LabMem 键盘输入] >> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                farewell = "实验就到此为止了吗？那我回脑科学实验室了。エル・プサイ・コングルゥ。"
                print(f"\n[红莉栖]: {farewell}")
                voice.speak(farewell, block=True)
                break

            reply = agent.chat(user_input)
            print(f"\n[红莉栖]: {reply}")

    except (KeyboardInterrupt, EOFError):
        print("\n[系统退出] 用户中断")
    finally:
        if voice_listener:
            voice_listener.stop()
        if vision_tracker:
            vision_tracker.stop()
        print("[系统已安全停止]")

if __name__ == "__main__":
    main()
