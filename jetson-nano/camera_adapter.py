"""Jetson Nano Camera Hardware Adapter.
Supports standard USB V4L2 (/dev/video0), Jetson CSI (GStreamer nvarguscamerasrc),
and software simulation fallback when no camera is connected.
"""
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("CameraAdapter")

try:
    import cv2
except ImportError:
    cv2 = None


def get_gstreamer_pipeline(
    capture_width: int = 1280,
    capture_height: int = 720,
    display_width: int = 640,
    display_height: int = 480,
    framerate: int = 30,
    flip_method: int = 0,
) -> str:
    """GStreamer pipeline for Jetson Nano CSI camera (Raspberry Pi Camera v2 / IMX219 / IMX477)."""
    return (
        f"nvarguscamerasrc ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, "
        f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! appsink"
    )


class CameraAdapter:
    """Abstracts video feed on Jetson Nano with automatic simulation fallback."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, simulate: bool = False):
        self.config = config or {}
        self.simulate = simulate
        self.cap = None
        self.is_opened = False

        self.source = self.config.get("source", "usb")
        self.device_idx = self.config.get("device_index", 0)
        self.width = self.config.get("width", 640)
        self.height = self.config.get("height", 480)
        self.fps = self.config.get("fps", 30)

    def open(self) -> bool:
        if self.simulate:
            logger.info("[Camera] Running in explicit SIMULATION mode.")
            self.is_opened = True
            return True

        if cv2 is None:
            logger.error("[Camera] OpenCV (cv2) not available! To run in simulation mode without OpenCV, pass --simulate.")
            return False

        try:
            if self.source == "csi":
                pipeline = get_gstreamer_pipeline(
                    display_width=self.width, display_height=self.height, framerate=self.fps
                )
                logger.info(f"[Camera] Opening CSI camera with pipeline: {pipeline}")
                self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            else:
                logger.info(f"[Camera] Opening USB camera index {self.device_idx}")
                self.cap = cv2.VideoCapture(self.device_idx)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            if self.cap and self.cap.isOpened():
                self.is_opened = True
                logger.info("[Camera] Hardware camera successfully opened.")
                return True
            else:
                logger.error("[Camera] Failed to open hardware camera! If no camera is connected, pass --simulate.")
                return False
        except Exception as e:
            logger.error(f"[Camera] Exception during camera open: {e}. Pass --simulate to run synthetic tests.")
            return False

    def read_frame(self) -> Tuple[bool, Any]:
        """Reads a frame. In simulation mode, returns synthetic frame placeholder."""
        if self.simulate:
            time.sleep(1.0 / self.fps)
            return True, None

        if not self.cap or not self.is_opened:
            return False, None

        ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        self.is_opened = False

