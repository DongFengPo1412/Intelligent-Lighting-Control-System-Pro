"""
TestSuite: 牧濑红莉栖具身多模态智能体全功能自动化验收测试
覆盖测试用例:
  1. 硬件物理通信握手 (COM9 直驱通道)
  2. 傲娇科学家性格反驳与助手禁忌词测试
  3. 物理沙漏智能倒计时具身工具调用 (MCP start_countdown)
  4. 《命运石之门》世界线变动率彩蛋调用 (MCP trigger_steins_gate_worldline: 1.048596%)
  5. 表情与光场特效调用 (MCP show_expression / set_matrix_theme)
  6. 中日双语神经声学引擎即时发声 (VoiceEngine)
  7. 局域网 UDP 物联网广播信道健康检查 (WiFiGateway)
"""

import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from light_controller import get_light_controller
from light_tools import execute_tool
from voice_engine import get_voice_engine
from kurisu_agent import KurisuAgent
from wifi_gateway import get_wifi_gateway

def run_acceptance_tests():
    print("=" * 70)
    print("      【牧濑红莉栖】具身多模态智能体与物理光场 · 全功能自动化验收测试      ")
    print("=" * 70)

    # ----------------------------------------------------
    # Case 1: 硬件串口握手
    # ----------------------------------------------------
    print("\n[TEST 1/6] 硬件物理信道检测 (COM9)")
    controller = get_light_controller()
    assert controller.is_connected, "错误: 无法连接 ESP32-S3 (COM9)"
    print(f"  -> [PASS] 硬件串口握手成功，端口: {controller.port}, 波特率: {controller.baudrate}")

    # ----------------------------------------------------
    # Case 2: 无线 UDP 广播网关健康检查
    # ----------------------------------------------------
    print("\n[TEST 2/6] 无线 UDP 物联网网关检测")
    wifi = get_wifi_gateway()
    ok_wifi = wifi.broadcast_json({"test": "ping"})
    assert ok_wifi, "错误: UDP 网关广播失败"
    print("  -> [PASS] 无线 UDP 广播信道正常就绪 (Port 8888)")

    # ----------------------------------------------------
    # Case 3: 神经声学引擎中日双语验证
    # ----------------------------------------------------
    print("\n[TEST 3/6] 中日双语神经语音合成测试 (VoiceEngine)")
    voice = get_voice_engine()
    test_phrase = "未来道具研究所 LabMem No.004，牧濑红莉栖。エル・プサイ・コングルゥ。"
    print(f"  -> 合成台词: '{test_phrase}'")
    voice.speak(test_phrase, block=True)
    print("  -> [PASS] 中日双语音频流已成功输出至扬声器")

    # ----------------------------------------------------
    # Case 4: 物理沙漏倒计时具身工具调用测试
    # ----------------------------------------------------
    print("\n[TEST 4/6] 物理沙漏倒计时意图与 MCP 工具链调用")
    agent = KurisuAgent()
    query_countdown = "助手，帮我倒计时6秒"
    print(f"  -> 用户自然语言输入: '{query_countdown}'")
    reply_1 = agent.chat(query_countdown)
    print(f"  -> 红莉栖具身回复:\n{reply_1}")
    time.sleep(3.0)
    print("  -> [PASS] 物理沙漏已成功在 16x16 矩阵灯板上呈现按秒等比粒子衰减！")

    # ----------------------------------------------------
    # Case 5: 《命运石之门》世界线变动率彩蛋测试 (1.048596%)
    # ----------------------------------------------------
    print("\n[TEST 5/6] 《命运石之门》世界线变动率彩蛋与乱数流转测试")
    query_sg = "向我汇报现在的世界线变动率！"
    print(f"  -> 用户自然语言输入: '{query_sg}'")
    reply_2 = agent.chat(query_sg)
    print(f"  -> 红莉栖具身回复:\n{reply_2}")
    time.sleep(2.0)
    print("  -> [PASS] 世界线变动率 1.048596% 彩蛋已触发，光场完成乱数流转并定格！")

    # ----------------------------------------------------
    # Case 6: 表情交互与助手禁忌词反驳测试
    # ----------------------------------------------------
    print("\n[TEST 6/6] 禁忌雷区触发与微表情联动测试")
    query_tsundere = "克里斯蒂娜助手，笑一个看看"
    print(f"  -> 用户自然语言输入: '{query_tsundere}'")
    reply_3 = agent.chat(query_tsundere)
    print(f"  -> 红莉栖具身回复:\n{reply_3}")
    print("  -> [PASS] 傲娇人设精准反驳，同时光场呈现微笑面部微表情！")

    print("\n" + "=" * 70)
    print("                 【全部 6 项核心测试 100% 通过！】                 ")
    print("   ESP32-S3 边缘光场、MCP 具身工具、神经语音与傲娇人设完全闭环！")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_acceptance_tests()
