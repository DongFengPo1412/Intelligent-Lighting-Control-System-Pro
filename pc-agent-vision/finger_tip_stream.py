"""
finger_tip_stream.py

PC 端指尖追踪推流脚本：
  摄像头 -> MediaPipe Hands -> 食指指尖 (landmark 8) -> 归一化坐标
  -> ESP32-S3 Wi-Fi ACK JSON -> 16x16 WS2812 追踪光点

运行示例：
  python finger_tip_stream.py --camera 0 --rate 40

坐标约定：
  - 默认先把画面水平镜像，符合“照镜子”的交互习惯；
  - 默认只取画面中央的正方形区域，再缩放到 16x16 灯板，避免宽屏横向拉伸；
  - 如果希望使用完整画面，加 --no-square-crop；
  - 如果摄像头没有镜像，加 --no-mirror。

发送协议：
  {"cmd":"track","x":0.42,"y":0.63,"visible":true,"conf":0.98}

固件端需要先切换到 26 号模式（FINGERTIP_TRACKER），脚本会自动发送。
"""

import argparse
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import cv2
import mediapipe as mp

try:
    from light_controller import get_light_controller
except ImportError:
    # 允许脚本放在项目子目录中运行；优先寻找仓库里的 pc-agent-vision。
    from pathlib import Path
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "pc-agent-vision"
        if (candidate / "light_controller.py").is_file():
            sys.path.insert(0, str(candidate))
            break
    from light_controller import get_light_controller


INDEX_FINGER_TIP = 8


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def parse_args():
    parser = argparse.ArgumentParser(description="MediaPipe 指尖坐标 -> ESP32-S3 灯光追踪")
    parser.add_argument("--camera", type=int, default=0, help="摄像头索引，默认 0")
    parser.add_argument("--rate", type=float, default=40.0, help="发送频率 Hz，默认 40")
    parser.add_argument("--square-crop", dest="square_crop", action="store_true",
                        help="使用画面中央正方形区域（默认开启）")
    parser.add_argument("--no-square-crop", dest="square_crop", action="store_false",
                        help="使用完整摄像头画面")
    parser.set_defaults(square_crop=True)
    parser.add_argument("--mirror", dest="mirror", action="store_true",
                        help="水平镜像画面（默认开启）")
    parser.add_argument("--no-mirror", dest="mirror", action="store_false",
                        help="不镜像画面")
    parser.set_defaults(mirror=True)
    parser.add_argument("--no-preview", action="store_true", help="不显示 OpenCV 预览窗口")
    parser.add_argument("--detection-confidence", type=float, default=0.6)
    parser.add_argument("--tracking-confidence", type=float, default=0.6)
    return parser.parse_args()


def crop_square(frame):
    """裁掉宽屏两侧，保留中央正方形，使摄像头画面与正方形灯阵一一对应。"""
    height, width = frame.shape[:2]
    side = min(height, width)
    x0 = (width - side) // 2
    y0 = (height - side) // 2
    return frame[y0:y0 + side, x0:x0 + side]


def main():
    args = parse_args()
    send_interval = 1.0 / max(1.0, args.rate)

    controller = get_light_controller()
    mode_selected=controller.wait_for_control(3.0)
    if mode_selected:
        # 26 = FINGERTIP_TRACKER
        if not controller.set_mode(26):
            raise ConnectionError("FingerTip mode was not acknowledged")
    else:
        print("[FingerTip] Wi-Fi 控制未连接，仅运行摄像头预览。")

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=args.detection_confidence,
        min_tracking_confidence=args.tracking_confidence,
    )

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        cap.release()
        hands.close()
        controller.close()
        print(f"[FingerTip] 无法打开摄像头 {args.camera}")
        return 1

    # 尽量降低摄像头内部缓冲造成的延迟。
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    last_send = 0.0
    last_visible = None

    print("[FingerTip] 已启动。按 q 或 ESC 退出。")
    print("[FingerTip] 食指指尖坐标会实时映射到 16x16 灯板。")

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break

            if args.mirror:
                frame = cv2.flip(frame, 1)
            if args.square_crop:
                frame = crop_square(frame)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            visible = False
            nx = 0.5
            ny = 0.5
            confidence = 0.0

            if results.multi_hand_landmarks:
                hand = results.multi_hand_landmarks[0]
                tip = hand.landmark[INDEX_FINGER_TIP]
                nx = clamp01(tip.x)
                # MediaPipe 与灯阵的 y 轴都向下，保持同向映射即可。
                ny = clamp01(tip.y)
                visible = True

                if results.multi_handedness:
                    try:
                        confidence = float(results.multi_handedness[0].classification[0].score)
                    except (AttributeError, IndexError):
                        confidence = 1.0
                else:
                    confidence = 1.0

                if not args.no_preview:
                    mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                    h, w = frame.shape[:2]
                    px = int(nx * (w - 1))
                    py = int(ny * (h - 1))
                    cv2.circle(frame, (px, py), 12, (0, 255, 255), 2)
                    cv2.circle(frame, (px, py), 3, (0, 255, 255), -1)

            now = time.monotonic()
            # 没有手时降低发送频率，避免无意义的串口流量。
            min_interval = send_interval if visible else max(send_interval, 0.10)
            if now - last_send >= min_interval:
                last_send = now
                if controller.control_connected:
                    if not mode_selected:
                        if not controller.set_mode(26):raise ConnectionError('Fingertip mode was not acknowledged after reconnect')
                        mode_selected=True
                    acknowledged = controller.send_json({
                        "cmd": "track",
                        "x": round(nx, 4),
                        "y": round(ny, 4),
                        "visible": visible,
                        "conf": round(confidence, 3),
                    })
                    if not acknowledged:raise ConnectionError('Fingertip input was not acknowledged')
                else:mode_selected=False
                if visible != last_visible:
                    state = "TRACKING" if visible else "NO HAND"
                    print(f"[FingerTip] {state}  x={nx:.3f}  y={ny:.3f}")
                    last_visible = visible

            if not args.no_preview:
                if visible:
                    cv2.putText(frame, f"FINGERTIP  x={nx:.3f}  y={ny:.3f}",
                                (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 255, 180), 2)
                else:
                    cv2.putText(frame, "NO HAND", (16, 32),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                (0, 100, 255), 2)

                cv2.imshow("FingerTip -> 16x16 Matrix (q/ESC to quit)", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord("q"):
                    break
            else:
                time.sleep(0.001)

    except KeyboardInterrupt:
        pass
    finally:
        if controller.control_connected:
            acknowledged = controller.send_json({
                "cmd": "track",
                "x": 0.5,
                "y": 0.5,
                "visible": False,
                "conf": 0.0,
            })
        controller.close()
        cap.release()
        hands.close()
        cv2.destroyAllWindows()
        print("[FingerTip] 已停止。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
