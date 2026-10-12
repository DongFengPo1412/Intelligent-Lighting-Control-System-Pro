"""
VisionTracker: 笔记本自带摄像头轻量多模态感知引擎
基于 OpenCV 与 MediaPipe Face Mesh 提取视线注意力与面部情绪特征
零额外硬件成本，实现“看、听、思、行”具身多模态闭环
"""

import sys
import time
import threading
from typing import Optional, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import cv2
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
except Exception as e:
    mp_face_mesh = None

from light_controller import get_light_controller

class VisionTracker:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.is_running = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.controller = get_light_controller()
        self.thread: Optional[threading.Thread] = None
        
        # 情绪与注意力状态
        self.is_user_present = False
        self.is_smiling = False
        self.last_state_change = time.time()
        self.current_emotion = "neutral"

    def _calculate_mouth_aspect_ratio(self, landmarks):
        """计算嘴角微笑开合度"""
        # MediaPipe 唇部关键点: 左嘴角 61, 右嘴角 291, 上唇 0, 下唇 17
        p_left = landmarks[61]
        p_right = landmarks[291]
        p_top = landmarks[0]
        p_bottom = landmarks[17]

        width = ((p_left.x - p_right.x)**2 + (p_left.y - p_right.y)**2)**0.5
        height = ((p_top.x - p_bottom.x)**2 + (p_top.y - p_bottom.y)**2)**0.5
        
        return width / (height + 1e-6)

    def _process_loop(self):
        """后台感知处理流水线 (低帧率节能模式: 10 FPS)"""
        if mp_face_mesh is None:
            print("[VisionTracker] 错误: MediaPipe 模块未加载")
            return

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"[VisionTracker] 提示: 摄像头 {self.camera_index} 未开启或被占用")
            return

        with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:
            
            print("[VisionTracker] 摄像头多模态视觉感知已启动 (检测人脸、视线与微笑)...")
            last_smile_time = 0

            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                # 镜像翻转并转换 RGB
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)

                now = time.time()

                if results.multi_face_landmarks:
                    self.is_user_present = True
                    face_landmarks = results.multi_face_landmarks[0].landmark
                    
                    # 微笑判断 (横纵比大于一定阈值)
                    ratio = self._calculate_mouth_aspect_ratio(face_landmarks)
                    if ratio > 2.8 and (now - last_smile_time > 3.0):
                        last_smile_time = now
                        self.is_smiling = True
                        print("[多模态感知] 捕捉到用户微笑！联动光场反馈: 微笑微表情")
                        self.controller.set_theme("smile")
                    elif ratio <= 2.8 and self.is_smiling and (now - last_smile_time > 2.0):
                        self.is_smiling = False
                        # 恢复灵动眨眼微表情
                        self.controller.set_theme("dynamic")
                else:
                    self.is_user_present = False

                time.sleep(0.08) # 约 12 FPS，低 CPU/GPU 占用

        if self.cap:
            self.cap.release()

    def start(self):
        """异步启动视觉线程"""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[VisionTracker] 视觉感知已停止")

if __name__ == "__main__":
    vt = VisionTracker()
    vt.start()
    print("视觉感知测试中，按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        vt.stop()
