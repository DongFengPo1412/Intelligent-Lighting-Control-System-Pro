"""
VisionFace: 基于 OpenCV LBPH 的多用户人脸识别与个性化互动中枢
移植自中阶系统 jetson-nano-py36/face_system_cn.py，适配 Windows/Linux 与 Pro 具身光场
支持按键采集人脸、动态训练模型、识别不同身份并触发红莉栖个性化问候与专属灯效
"""

import sys
import os
import time
import threading
import numpy as np
import cv2

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from light_controller import get_light_controller
from voice_engine import get_voice_engine

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_DIR = os.path.join(SCRIPT_DIR, "faces")
os.makedirs(FACE_DIR, exist_ok=True)

class VisionFaceRecognizer:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.controller = get_light_controller()
        self.voice = get_voice_engine()
        self.is_running = False
        self.thread = None
        
        # 加载 Haar 人脸分类器
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # LBPH 人脸识别器
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            # opencv-contrib-python 降级处理
            print("[VisionFace] 警告: cv2.face 模块未找到，请确保安装 opencv-contrib-python")
            self.recognizer = None

        self.names = []
        self.trained = False
        self.last_greeted_person = None
        self.last_greet_time = 0

    def train_faces(self) -> bool:
        """扫描 faces 目录并训练识别模型"""
        if self.recognizer is None:
            return False
            
        self.names.clear()
        face_data = []
        labels = []

        if not os.path.exists(FACE_DIR) or not os.listdir(FACE_DIR):
            print(f"[VisionFace] 提示: 人脸库为空 ({FACE_DIR})")
            return False

        label_id = 0
        for name in sorted(os.listdir(FACE_DIR)):
            user_dir = os.path.join(FACE_DIR, name)
            if not os.path.isdir(user_dir):
                continue
            self.names.append(name)
            for img_file in os.listdir(user_dir):
                if not (img_file.endswith(".jpg") or img_file.endswith(".png")):
                    continue
                img_path = os.path.join(user_dir, img_file)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, (100, 100))
                    face_data.append(img)
                    labels.append(label_id)
            label_id += 1

        if face_data:
            self.recognizer.train(face_data, np.array(labels))
            self.trained = True
            print(f"[VisionFace] 人脸模型训练完成！已载入 {len(self.names)} 位成员: {self.names}")
            return True
        return False

    def on_person_recognized(self, name: str):
        """识别到成员后的具身联动"""
        now = time.time()
        # 冷却 15 秒防止刷屏
        if name == self.last_greeted_person and (now - self.last_greet_time < 15):
            return

        self.last_greeted_person = name
        self.last_greet_time = now
        print(f"\n[VisionFace] ★ 成功锁定认证成员: 【{name}】！")

        if name == "ylk":
            # 专属灯效: 纯红警戒/实验室学者模式
            self.controller.set_mode(1)
            # 红莉栖专属声线问候
            self.voice.speak(
                f"哟，{name}，你总算舍得回实验室了？今天的数据整理完了吗？\n"
                f"あら、{name}、やっとラボに戻る気になったの？今日のデータ整理は終わったのかしら？"
            )
        elif name == "zzc":
            # 专属灯效: 纯蓝深邃模式
            self.controller.set_mode(2)
            self.voice.speak(
                f"是{name}啊。今天的波形测试看起来进展不错嘛，可别大意了哦。\n"
                f"{name}ね。今日の波形テストは順調そうじゃない、油断しちゃダメよ。"
            )
        else:
            # 其他注册成员
            self.controller.set_theme("smile")
            self.voice.speak(
                f"欢迎回到未来道具研究所，{name}。\n"
                f"未来ガジェット研究所へようこそ、{name}。"
            )

    def run_gui(self):
        """桌面可视化人脸交互窗口 (按 S 采集, T 重训, Q 退出)"""
        self.train_faces()
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"[VisionFace] 无法打开摄像头 {self.camera_index}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("\n===== 人脸识别系统操作指南 =====")
        print("按 S: 录入当前人脸并保存")
        print("按 T: 重新训练人脸特征库")
        print("按 Q: 退出人脸识别")
        print("================================\n")

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60, 60))

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                roi_gray = gray[y:y+h, x:x+w]
                roi_gray = cv2.resize(roi_gray, (100, 100))

                if self.trained and self.recognizer is not None:
                    try:
                        idx, conf = self.recognizer.predict(roi_gray)
                        if conf < 80 and idx < len(self.names):
                            name = self.names[idx]
                            cv2.putText(frame, f"{name} ({int(conf)})", (x, y-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            self.on_person_recognized(name)
                        else:
                            cv2.putText(frame, "Unknown", (x, y-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    except Exception as e:
                        pass

            cv2.putText(frame, "S: Save | T: Retrain | Q: Quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow("Kurisu Lab - Face Recognition", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s') and len(faces) > 0:
                x, y, w, h = faces[0]
                face_img = gray[y:y+h, x:x+w]
                name = input("输入人脸成员代号 (如 ylk / zzc / okabe): ").strip()
                if name:
                    user_dir = os.path.join(FACE_DIR, name)
                    os.makedirs(user_dir, exist_ok=True)
                    save_path = os.path.join(user_dir, f"{int(time.time())}.jpg")
                    cv2.imwrite(save_path, face_img)
                    print(f"[VisionFace] 已成功保存人脸采样: {save_path}")
            elif key == ord('t'):
                self.train_faces()

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = VisionFaceRecognizer()
    app.run_gui()
