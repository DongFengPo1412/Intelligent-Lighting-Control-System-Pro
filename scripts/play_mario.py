#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
play_mario.py —— 16x16 超级马里奥 PC 试玩 / 运行器

用法：
    python scripts/play_mario.py              # 本地窗口试玩 (OpenCV 仿真 16x16 灯板)
    python scripts/play_mario.py --board      # 连带推流到已连接的 ESP32-S3 灯板

按键说明：
    A / D 或 ← / →       左右移动
    Space / W / J         跳跃 (长按跳得更高)
    Shift / K             加速跑
    Enter / S             开始 / 暂停
    R                     重新开局
    Esc                   退出
"""

import sys
import time
import ctypes
from pathlib import Path
import numpy as np

# 确保控制台与依赖正常
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DLL_PATH = ROOT / "pc-agent-vision" / "mario16.dll"

if not DLL_PATH.is_file():
    raise FileNotFoundError(f"未找到马里奥引擎动态库: {DLL_PATH}，请先编译。")

# 加载 C 动态库
dll = ctypes.CDLL(str(DLL_PATH))

dll.mario_create.restype = ctypes.c_void_p
dll.mario_destroy.argtypes = [ctypes.c_void_p]
dll.mario_reset.argtypes = [ctypes.c_void_p]
dll.mario_update.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_uint16, ctypes.c_uint16]
dll.mario_render.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
dll.mario_get_status.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint16),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8)
]

KEY_LEFT   = 1 << 0
KEY_RIGHT  = 1 << 1
KEY_UP     = 1 << 2
KEY_DOWN   = 1 << 3
KEY_A      = 1 << 4   # 跳跃
KEY_B      = 1 << 5   # 加速跑
KEY_START  = 1 << 6   # 暂停 / 开始
KEY_SELECT = 1 << 7

STATE_NAMES = {
    0: "标题画面 (按 Enter 或 空格 开始)",
    1: "准备中 (READY)...",
    2: "游戏中 (PLAYING)",
    3: "已暂停 (PAUSED)",
    4: "死亡 (DEAD)",
    5: "游戏结束 (GAME OVER)",
    6: "🎉 通关获胜 (YOU WIN!)",
}


def render_display(raw_rgb, score, lives, coins, state, progress, scale=26):
    """把 16x16 灯板渲染为高质感圆珠 LED 矩阵仿真画面与 HUD 状态栏"""
    import cv2
    panel_size = 16 * scale
    hud_h = 70
    canvas = np.zeros((panel_size + hud_h, panel_size, 3), dtype=np.uint8)
    canvas[:panel_size, :] = (12, 16, 22)  # 深色背景底板

    # 绘制 16x16 圆珠 LED
    radius = int(scale * 0.42)
    for y in range(16):
        for x in range(16):
            r, g, b = raw_rgb[y, x]
            # OpenCV 使用 BGR 格式
            color_bgr = (int(b), int(g), int(r))
            cx = int((x + 0.5) * scale)
            cy = int((y + 0.5) * scale)
            # 灯珠发光感
            cv2.circle(canvas, (cx, cy), radius, color_bgr, -1, lineType=cv2.LINE_AA)
            if r > 40 or g > 40 or b > 40:
                cv2.circle(canvas, (cx, cy), radius + 1, (int(b * 0.35), int(g * 0.35), int(r * 0.35)), 1, lineType=cv2.LINE_AA)

    # 绘制 HUD 状态栏
    hud_y = panel_size
    cv2.rectangle(canvas, (0, hud_y), (panel_size, panel_size + hud_h), (20, 24, 32), -1)
    cv2.line(canvas, (0, hud_y), (panel_size, hud_y), (45, 55, 70), 1)

    # 状态文本
    font = cv2.FONT_HERSHEY_SIMPLEX
    st_text = STATE_NAMES.get(state, f"State {state}")
    cv2.putText(canvas, st_text, (10, hud_y + 24), font, 0.48, (230, 230, 240), 1, cv2.LINE_AA)

    info_text = f"SCORE: {score:05d}   LIVES: {lives}   COINS: {coins:02d}   PROGRESS: {progress}%"
    cv2.putText(canvas, info_text, (10, hud_y + 52), font, 0.44, (255, 215, 60), 1, cv2.LINE_AA)

    return canvas


def run_mario(stream_to_board=False):
    import cv2
    game = dll.mario_create()
    fb = np.zeros((16, 16, 3), dtype=np.uint8)

    score = ctypes.c_uint16()
    lives = ctypes.c_uint8()
    coins = ctypes.c_uint8()
    state = ctypes.c_uint8()
    prog = ctypes.c_uint8()

    controller = None
    if stream_to_board:
        try:
            sys.path.insert(0, str(ROOT / "pc-agent-vision"))
            from light_controller import get_light_controller
            controller = get_light_controller()
            if getattr(controller, "is_connected", False):
                print("[Mario] 已连接到 ESP32-S3 灯板控制通道。")
            else:
                print("[Mario] 未检测到板端连接，仅在 PC 窗口仿真。")
                controller = None
        except Exception as e:
            print(f"[Mario] 板端连接跳过: {e}")
            controller = None

    print("\n" + "=" * 60)
    print("  🍄 16x16 WS2812 超级马里奥 · 试玩仿真已启动")
    print("  ● 移动: 方向键 / A / D")
    print("  ● 跳跃: 空格 / W / J (按住跳得更高)")
    print("  ● 加速跑: Shift / K")
    print("  ● 开始/暂停: Enter / S")
    print("  ● 重开: R   |   退出: Esc")
    print("=" * 60 + "\n")

    win_name = "16x16 Super Mario (WS2812 Retro Simulator)"
    cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)

    prev_down = 0
    running = True
    last_frame_time = time.monotonic()

    try:
        while running:
            now = time.monotonic()
            dt = max(0.001, min(0.04, now - last_frame_time))
            last_frame_time = now

            # 处理按键事件 (OpenCV waitKeyEx 支持扩展键码)
            key = cv2.waitKeyEx(18)
            down = 0
            pressed = 0

            if key == 27:  # Esc
                break
            elif key in (13, ord('s'), ord('S')):  # Enter / S -> Start
                pressed |= KEY_START
                down |= KEY_START
            elif key in (ord('r'), ord('R')):  # R -> Reset
                dll.mario_reset(game)
                pressed |= KEY_START

            # 方向与动作键
            if key in (2424832, ord('a'), ord('A')):  # Left
                down |= KEY_LEFT
            elif key in (2555904, ord('d'), ord('D')):  # Right
                down |= KEY_RIGHT
            elif key in (2490368, ord('w'), ord('W'), 32, ord('j'), ord('J')):  # Up / Space / J -> Jump
                down |= KEY_A
                if not (prev_down & KEY_A):
                    pressed |= KEY_A
            elif key in (ord('k'), ord('K')):  # Run
                down |= KEY_B

            # 如果窗口关闭
            if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                break

            # 步进物理与逻辑 (50Hz)
            dll.mario_update(game, ctypes.c_float(0.02), ctypes.c_uint16(down), ctypes.c_uint16(pressed))
            prev_down = down

            # 渲染画面
            dll.mario_render(game, fb.ctypes.data_as(ctypes.c_char_p))
            dll.mario_get_status(
                game,
                ctypes.byref(score),
                ctypes.byref(lives),
                ctypes.byref(coins),
                ctypes.byref(state),
                ctypes.byref(prog)
            )

            # 可视化展示
            frame = render_display(fb, score.value, lives.value, coins.value, state.value, prog.value)
            cv2.imshow(win_name, frame)

            # 帧率控制 (约 50 FPS)
            elapsed = time.monotonic() - now
            if elapsed < 0.020:
                time.sleep(0.020 - elapsed)

    finally:
        dll.mario_destroy(game)
        cv2.destroyAllWindows()
        print("[Mario] 游戏已退出。")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="16x16 Super Mario 试玩")
    parser.add_argument("--board", action="store_true", help="同时推流到板载灯板")
    args = parser.parse_args()
    run_mario(stream_to_board=args.board)
