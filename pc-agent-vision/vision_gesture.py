"""
vision_gesture.py: 基于 MediaPipe 的视觉隔空手势控光中枢 (移植自中阶 jetson-nano-py36)
支持普通 USB 摄像头 / 笔记本自带摄像头，无需佩戴任何传感器即可隔空手势切光：
- ✊ 握拳 (0 指): 关灯 / 息屏待机 (off)
- ☝️ 伸出 1 指: 模式 1 (纯红理智模式)
- ✌️ 胜利剪刀手 (2 指): 模式 17 (牧濑红莉栖桌宠伴侣)
- 🤟 伸出 3 指: 模式 23 (赛博壁炉物理烈焰)
- 🖖 伸出 4 指: 模式 24 (黑客帝国代码雨 Pro)
- 🖐️ 摊开手掌 (5 指): 模式 4 (幻彩霓虹对流波浪)
"""

import cv2
import time
import os
import sys

# 优先导入 PyTorch 保证环境一致性
import torch
import mediapipe as mp

from light_controller import get_light_controller

def is_finger_straight(landmark, tip_id, pip_id):
    """判断手指是否伸直 (指尖 Y 轴高度高于关节)"""
    return landmark[tip_id].y < landmark[pip_id].y - 0.02

def get_gesture(landmark):
    """
    解算手势:
    返回:
      0: 握拳 (所有手指弯曲)
      1~5: 伸直的手指数量
      6: 胜利剪刀手 ✌️ (食指+中指伸直)
    """
    # 拇指：判断 X 坐标 (右手拇指尖在关节左侧判定为伸直)
    thumb_straight = landmark[4].x < landmark[3].x
    # 其余四指：判断 Y 坐标 (指尖比关节高为伸直)
    index_straight = is_finger_straight(landmark, 8, 6)
    middle_straight = is_finger_straight(landmark, 12, 10)
    ring_straight = is_finger_straight(landmark, 16, 14)
    pinky_straight = is_finger_straight(landmark, 20, 18)

    fingers = [thumb_straight, index_straight, middle_straight, ring_straight, pinky_straight]
    finger_count = sum(fingers)

    # 胜利手势 ✌️: 食指+中指伸直，其余弯曲
    if index_straight and middle_straight and not thumb_straight and not ring_straight and not pinky_straight:
        return 6
    # 握拳: 所有手指弯曲
    elif finger_count == 0:
        return 0
    # 摊手: 5 指全部伸直
    elif finger_count == 5:
        return 5
    else:
        return finger_count

def run_gesture_controller(cam_index=0, headless=False):
    print("=" * 60)
    print("  🖐️ 智光魔方 Pro · 视觉隔空手势控光中枢 (移植自中阶)")
    print("  ● 0 指握拳 ✊: 熄屏关灯 (off)")
    print("  ● 1 指伸出 ☝️: 纯红模式 (mode 1)")
    print("  ● 2 指剪刀 ✌️: 牧濑红莉栖桌宠 (mode 17)")
    print("  ● 3 指伸出 🤟: 赛博壁炉烈焰 (fire / mode 23)")
    print("  ● 4 指伸出 🖖: 黑客帝国代码雨 (matrix / mode 24)")
    print("  ● 5 指摊掌 🖐️: 幻彩霓虹波浪 (rainbow / mode 4)")
    print("=" * 60)

    ctrl = get_light_controller()
    if not ctrl.is_connected:
        print("[Gesture 警告]: 硬件串口未就绪，将仅运行手势视觉识别预览")

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.6)

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"❌ [错误]: 无法打开摄像头 (Index {cam_index})！")
        return

    last_gesture = None
    last_trigger_time = 0.0

    gesture_to_mode = {
        0: ("off", "熄屏关灯"),
        1: ("mode 1", "纯红理智模式"),
        6: ("kurisu", "牧濑红莉栖桌宠伴侣"),
        2: ("kurisu", "牧濑红莉栖桌宠伴侣"),
        3: ("fire", "赛博烈焰壁炉"),
        4: ("matrix", "黑客帝国代码雨 Pro"),
        5: ("rainbow", "幻彩霓虹波浪")
    }

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1) # 镜像翻转，符合镜面交互习惯
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            current_gesture = None

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    current_gesture = get_gesture(hand_landmarks.landmark)

            now = time.time()
            if current_gesture is not None:
                cmd_info = gesture_to_mode.get(current_gesture)
                desc = cmd_info[1] if cmd_info else f"{current_gesture} 指"
                cv2.putText(frame, f"GESTURE: {current_gesture} -> {desc}", (30, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 128), 2)

                # 防抖节流：手势变化且保持 0.6 秒以上触发
                if current_gesture != last_gesture and (now - last_trigger_time > 0.6):
                    last_gesture = current_gesture
                    last_trigger_time = now
                    if cmd_info and ctrl.is_connected:
                        cmd, name = cmd_info
                        print(f"✨ [隔空手势触发]: {name} (执行指令: '{cmd}')")
                        ctrl.send_raw(cmd)
                        if cmd == "kurisu":
                            ctrl.send_raw("b 150")
            else:
                last_gesture = None

            if not headless:
                cv2.imshow("SmartLight Gesture Control (Press 'q' or ESC to exit)", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord('q'):
                    break
            else:
                time.sleep(0.03)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[Gesture] 隔空手势交互已停止。")

if __name__ == "__main__":
    run_gesture_controller()
