"""One camera owner and one arbitration policy for visual interaction modes."""

import threading
import time
from datetime import datetime
from pro_paths import data_dir
from visual_features import VisualFeatures


class ControlArbiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.until = 0
        self.lock = threading.RLock()

    def claim_user(self, seconds=15):
        with self.lock:
            self.until = self.clock() + seconds

    def allows_automatic(self):
        with self.lock:
            return self.clock() >= self.until


class MultimodalHub:
    MODES = {"pet", "fingertip", "sandbox", "gesture_game", "gaze_game", "identity"}

    def __init__(self, controller, voice=None):
        self.controller = controller
        self.voice = voice
        self.arbiter = ControlArbiter()
        controller._arbiter = self.arbiter
        controller._vision_hub = self
        self.automatic_enabled = True
        self.features = VisualFeatures()
        self.stop_event = threading.Event()
        self.thread = None
        self.mode = "pet"
        self.last_observation = {}
        self.error = None
        self.camera = 0
        self.last_seen = time.monotonic()
        self.last_input = 0
        self.last_greet = 0
        self.previous_auto_mode = None
        self.started = False
        self.pending_direction = None
        self.direction_since = 0
        self.last_face = None
        self.identity = None
        self.smile_since = None
        self.strain_since = None
        self.last_celebration = 0
        self.observed_at = 0

    def start(self, mode="pet", camera=0):
        if mode not in self.MODES or type(camera) is not int or not 0 <= camera <= 9:
            raise ValueError("Invalid vision mode/camera")
        if self.thread and self.thread.is_alive() and camera != self.camera:
            raise ValueError("Stop the camera before changing its index")
        desired = {"pet": 17, "identity": 17, "fingertip": 26, "sandbox": 27}.get(mode)
        if desired is not None and not self.controller.send_json({"cmd": "mode", "val": desired}):
            raise ConnectionError("Vision display mode was not acknowledged")
        self.automatic_enabled = True
        self.arbiter.until = 0
        if self.thread and self.thread.is_alive():
            if camera != self.camera:
                raise ValueError("Stop the camera before changing its index")
            self.mode = mode
            return
        self.mode = mode
        self.camera = camera
        self.error = None
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._capture, daemon=True)
        self.thread.start()

    def manual_mode(self, mode):
        compatible = {
            "pet": {17},
            "identity": {17},
            "fingertip": {26},
            "sandbox": {27},
            "gesture_game": {19, 21},
            "gaze_game": {19, 21},
        }
        self.automatic_enabled = mode in compatible[self.mode]

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=4)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Camera has not released yet")
        self.started = False

    def _capture(self):
        import cv2
        import mediapipe as mp

        cap = None
        try:
            cap = cv2.VideoCapture(self.camera)
            if not cap.isOpened():
                raise RuntimeError("Cannot open selected camera")
            with mp.solutions.hands.Hands(
                max_num_hands=1, model_complexity=0
            ) as hands, mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1, refine_landmarks=True
            ) as face:
                self.started = True
                while not self.stop_event.is_set():
                    ok, image = cap.read()
                    if not ok:
                        raise RuntimeError("Camera stream ended")
                    image = cv2.flip(image, 1)
                    h, w = image.shape[:2]
                    side = min(h, w)
                    image = image[
                        (h - side) // 2 : (h + side) // 2, (w - side) // 2 : (w + side) // 2
                    ]
                    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    hand = hands.process(rgb)
                    faces = face.process(rgb)
                    observation = {"present": bool(faces.multi_face_landmarks)}
                    if hand.multi_hand_landmarks:
                        observation["hand"] = self.features.hand(
                            [[v.x, v.y, v.z] for v in hand.multi_hand_landmarks[0].landmark]
                        )
                    if faces.multi_face_landmarks:
                        points = [[v.x, v.y, v.z] for v in faces.multi_face_landmarks[0].landmark]
                        observation.update(self.features.face(points, time.monotonic(), side, side))
                        import numpy as np

                        pts = np.array(points)
                        lo = np.clip(pts[:, :2].min(axis=0), 0, 1)
                        hi = np.clip(pts[:, :2].max(axis=0), 0, 1)
                        crop = image[
                            int(lo[1] * side) : int(hi[1] * side),
                            int(lo[0] * side) : int(hi[0] * side),
                        ]
                        if crop.size:
                            self.last_face = cv2.resize(
                                cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (100, 100)
                            )
                        if self.mode == "identity" and self.identity is None:
                            from identity_store import IdentityStore

                            self.identity = IdentityStore()
                        if self.mode == "identity" and self.identity:
                            label, confidence = self.identity.predict(self.last_face)
                            observation["identity"] = label
                            observation["identity_distance"] = confidence
                    self.process(observation)
                    self.stop_event.wait(0.04)
        except Exception as exc:
            self.error = str(exc)
        finally:
            if cap:
                cap.release()
            self.started = False

    def process(self, observation, now=None):
        self.observed_at = time.time()
        now = time.monotonic() if now is None else now
        self.last_observation = dict(observation)
        present = observation.get("present", False)
        if present:
            self.last_seen = now
        smiling = present and bool(observation.get("smiling"))
        strained = present and observation.get("frustration", 0) > 0.7
        self.smile_since = (
            (now if self.smile_since is None else self.smile_since) if smiling else None
        )
        self.strain_since = (
            (now if self.strain_since is None else self.strain_since) if strained else None
        )
        # Context does not switch a user-selected display mode.
        self.controller.pet_context(
            datetime.now().hour,
            observation.get("gaze_x", 0.5) * 2 - 1,
            present or now - self.last_seen < 15,
            bool(observation.get("tired", False)),
        )
        allowed = self.automatic_enabled and self.arbiter.allows_automatic()
        if not allowed:
            return
        hand = observation.get("hand", {})
        from wifi_gateway import get_wifi_gateway

        mode = getattr(self.controller, "mode", None)
        if mode is None:
            mode = get_wifi_gateway().last_mode
        if self.mode in ("fingertip", "sandbox"):
            desired = 26 if self.mode == "fingertip" else 27
            if mode != desired:
                if not self.controller.send_json({"cmd": "mode", "val": desired}):
                    return
            if self.mode == "fingertip":
                self.controller.track(
                    hand.get("x", 0.5), hand.get("y", 0.5), bool(hand), 1 if hand else 0
                )
            else:
                self.controller.hand(
                    hand.get("x", 0.5),
                    hand.get("y", 0.5),
                    hand.get("z", 0),
                    hand.get("pinch", False),
                    bool(hand),
                )
        elif self.mode in ("gaze_game", "gesture_game") and mode in (19, 21):
            x = observation.get("gaze_x", 0.5) if self.mode == "gaze_game" else hand.get("x", 0.5)
            y = observation.get("gaze_y", 0.5) if self.mode == "gaze_game" else hand.get("y", 0.5)
            valid = (
                present and observation.get("calibrated", False)
                if self.mode == "gaze_game"
                else bool(hand)
            )
            direction = (
                (
                    "left"
                    if x < 0.3
                    else "right" if x > 0.7 else "up" if y < 0.3 else "down" if y > 0.7 else None
                )
                if valid
                else None
            )
            if direction != self.pending_direction:
                self.pending_direction = direction
                self.direction_since = now
            if direction and now - self.direction_since > 0.2 and now - self.last_input > 0.3:
                reaction = (
                    min(10000, max(0, (now - self.last_input) * 1000)) if self.last_input else 1000
                )
                self.last_input = now
                self.controller.performance(
                    reaction, observation.get("frustration", 0), not observation.get("tired", False)
                )
                if mode == 19:
                    dx, dy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[
                        direction
                    ]
                    self.controller.snake_move(dx, dy)
                else:
                    self.controller.tetris_action(
                        {"left": "left", "right": "right", "up": "rot", "down": "drop"}[direction]
                    )
        elif self.mode == "pet":
            if now - self.last_seen > 15 and mode == 17:
                if self.controller.send_json({"cmd": "mode", "val": 31}):
                    self.previous_auto_mode = 17
            elif present and mode == 31 and self.previous_auto_mode == 17:
                self.controller.send_json({"cmd": "mode", "val": 17})
                self.previous_auto_mode = None
            if (
                observation.get("tired")
                or (self.strain_since is not None and now - self.strain_since > 2)
            ) and now - self.last_greet > 120:
                self.last_greet = now
                if self.controller.send_json({"cmd": "mode", "val": 31}):
                    self.previous_auto_mode = 17
                if self.voice:
                    self.voice.speak("休息一下眼睛吧。\n少し目を休めてね。", block=False)
            elif (
                mode == 17
                and self.smile_since is not None
                and now - self.smile_since > 1
                and now - self.last_celebration > 20
            ):
                if self.controller.send_json({"cmd": "celebrate"}):
                    self.last_celebration = now
        elif self.mode == "identity" and observation.get("identity") and now - self.last_greet > 15:
            self.last_greet = now
            if self.voice:
                self.voice.speak(
                    f"欢迎回来，{observation['identity']}。\nおかえりなさい。", block=False
                )

    def enroll(self, name):
        if not self.started or self.last_face is None:
            raise ValueError("No current face to enroll")
        if self.identity is None:
            from identity_store import IdentityStore

            self.identity = IdentityStore()
        return self.identity.enroll(name, self.last_face)

    def status(self):
        age = time.time() - self.observed_at if self.observed_at else None
        return dict(
            running=self.started,
            mode=self.mode,
            automatic_enabled=self.automatic_enabled,
            error=self.error,
            age_seconds=age,
            fresh=bool(self.started and age is not None and age < 3),
            observation=self.last_observation,
        )
