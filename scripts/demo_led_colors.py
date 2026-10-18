"""
demo_led_colors.py: 物理演示 ESP32-S3 板载指示灯 (GPIO 48) 的全部光色与呼吸效果
特别重点对比：
1. 幽蓝 (深邃冷蓝 - Deep Blue) vs 青蓝 (灵动青白/蓝绿 - Cyan/Aqua)
2. 微光暗红 (静默待命) vs 鲜艳鲜红 (说话拾音)
3. 翠绿常亮 (语音播报)
"""

import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pc-agent-vision")
sys.path.insert(0, agent_dir)

from light_controller import get_light_controller

def main():
    ctrl = get_light_controller()
    if not ctrl.is_connected:
        print("[错误]: 无法连接到 ESP32-S3 (COM9)！")
        return

    print("=" * 65)
    print("  🎨 ESP32-S3 板载 RGB 指示灯 (GPIO 48) 物理光效现场演示")
    print("  ★ 请目光锁定 ESP32-S3 主板上的那颗独立单颗 RGB 灯珠！★")
    print("=" * 65)

    try:
        # 0. 准备提示
        print("\n准备开始！扬声器将发出一声提示音...")
        ctrl.play_beep()
        time.sleep(1.0)

        # 1. 幽蓝呼吸演示 (超长 8 秒)
        print("\n=========================================================")
        print("▶ 【第 1 项：幽蓝呼吸 (Deep Blue Breathing - 模式 1)】")
        print("  视觉效果: 纯深海冷蓝色 (Pure Dark Blue)，如海水涌动般缓缓由暗到亮、由亮到暗")
        print("  中阶对应: 开机配对搜寻、WiFi 搜寻配置等待 (kDeviceStateWifiConfiguring)")
        print("=========================================================")
        ctrl.set_board_led("pairing")
        for i in range(8, 0, -1):
            print(f"  >>> 请看灯珠！当前展示【幽蓝呼吸 (深海纯蓝)】... 剩余 {i} 秒 <<<", end="\r")
            time.sleep(1)

        # 提示音切换
        ctrl.play_beep()
        time.sleep(0.3)

        # 2. 幽蓝常亮演示 (6 秒)
        print("\n\n=========================================================")
        print("▶ 【第 2 项：幽蓝常亮 (Solid Deep Blue - 模式 6)】")
        print("  视觉效果: 静止不动的纯正深蓝色冷光")
        print("  中阶对应: 配对成功、握手连接确立 (kDeviceStateConnecting)")
        print("=========================================================")
        ctrl.set_board_led("connected")
        for i in range(6, 0, -1):
            print(f"  >>> 请看灯珠！当前展示【幽蓝常亮 (纯深蓝静止)】... 剩余 {i} 秒 <<<", end="\r")
            time.sleep(1)

        # 提示音切换
        ctrl.play_beep()
        time.sleep(0.3)

        # 3. 青蓝微呼吸演示 (超长 8 秒)
        print("\n\n=========================================================")
        print("▶ 【第 3 项：青蓝/青白微呼吸 (Cyan-Blue Breathing - 模式 3)】")
        print("  视觉效果: 浅青蓝色 / 蓝绿色 (Cyan / Aqua)，带有一点高科技淡白光感的浅蓝绿流光")
        print("  中阶对应: 唤醒后思考运算中、等待用户输入指令态")
        print("=========================================================")
        ctrl.set_board_led("thinking")
        for i in range(8, 0, -1):
            print(f"  >>> 请看灯珠！当前展示【青蓝微呼吸 (浅蓝绿/青白)】... 剩余 {i} 秒 <<<", end="\r")
            time.sleep(1)

        # 4. 【直观对比环节】：幽蓝 vs 青蓝 快速轮替对比 3 次 (每次 3.5 秒)
        print("\n\n=========================================================")
        print("★ 【对比环节】：幽蓝 与 青蓝 现场来回切换对比 3 轮 (每次 3.5 秒)！")
        print("=========================================================")
        for turn in range(3):
            ctrl.play_beep()
            print(f"\n[轮替第 {turn+1}/3 轮] -> 瞬间切为【深海纯幽蓝】(深冷蓝色) 持续 3.5 秒...")
            ctrl.set_board_led("pairing")
            time.sleep(3.5)

            ctrl.play_beep()
            print(f"[轮替第 {turn+1}/3 轮] -> 瞬间切为【科技浅青蓝】(蓝绿微白) 持续 3.5 秒...")
            ctrl.set_board_led("thinking")
            time.sleep(3.5)

        # 5. 其他中阶状态演示
        print("\n\n=========================================================")
        print("▶ 【第 4 项：红光状态 (暗红 vs 鲜红)】")
        print("=========================================================")
        print("  1. 微光暗红: 静默待命监听中 (没有说话时的低功耗微光)")
        ctrl.set_board_led("listening")
        time.sleep(3.5)

        print("  2. 鲜艳鲜红: 麦克风 VAD 感应到人声说话拾音中...")
        ctrl.set_board_led("hearing")
        time.sleep(3.5)

        print("\n=========================================================")
        print("▶ 【第 5 项：翠绿常亮 (Solid Green - 模式 2)】")
        print("  中阶对应: 语音播报输出中 (红莉栖说话，麦克风硬件静音)")
        print("=========================================================")
        ctrl.set_board_led("speaking")
        time.sleep(4.0)

        # 演示完毕
        print("\n=========================================================")
        print("✅ 演示完整结束！板载指示灯已复位为【微光暗红待命监听】状态。")
        print("=========================================================\n")
        ctrl.set_board_led("listening")

    except Exception as e:
        print(f"[演示异常]: {e}")

if __name__ == "__main__":
    main()
