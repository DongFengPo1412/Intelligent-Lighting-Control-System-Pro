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
        self.source = "none"
        self.active_session_id = None
        self.session_epoch = 0
        self.pending_direction = None
        self.direction_since = 0
        self.last_face = None
        self.face_sample_at = None
        self.face_lock = threading.RLock()
        self.identity = None
        self.smile_since = None
        self.strain_since = None
        self.last_celebration = 0
        self.observed_at = 0
        self.latest_jpeg = None
        self.frame_lock = threading.RLock()

    def get_latest_jpeg(self):
        if hasattr(self, "frame_lock"):
            with self.frame_lock:
                return self.latest_jpeg
        return None

    def _prepare_mode_and_takeover(self, mode):
        if mode not in self.MODES:
            raise ValueError(f"不支持的视觉交互模式: {mode}")

        if mode in ("gesture_game", "gaze_game"):
            current_mode = getattr(self.controller, "mode", None)
            if current_mode is None:
                try:
                    from wifi_gateway import get_wifi_gateway
                    current_mode = get_wifi_gateway().last_mode
                except Exception:
                    current_mode = None

            if isinstance(current_mode, int):
                is_supported_game = False
                if current_mode in (19, 21):
                    is_supported_game = True
                elif current_mode == 32:
                    try:
                        from arcade_runner import get_arcade_session
                        gid = get_arcade_session(self.controller).status.get("game_id")
                        if gid in (33, 41):
                            is_supported_game = True
                    except Exception:
                        pass
                if not is_supported_game:
                    raise ValueError("手势/视线游戏需要先在街机菜单中选择支持体感控制的游戏卡带（#033 贪吃蛇 或 #041 俄罗斯方块）并启动游戏。")
            elif current_mode is None:
                raise ValueError("手势/视线游戏需要先在街机菜单中选择支持体感控制的游戏卡带（#033 贪吃蛇 或 #041 俄罗斯方块）并启动游戏。")

            if mode == "gaze_game":
                gaze = getattr(getattr(self, "features", None), "gaze", None)
                if gaze is not None and gaze.coefficients is None:
                    raise ValueError("视线游戏需要先完成视线校准，请先在视线校准区域完成校准。")

        desired = {"pet": 17, "identity": 17, "fingertip": 26, "sandbox": 27}.get(mode)
        if desired is not None:
            if not self.controller.send_json({"cmd": "mode", "val": desired}):
                raise ConnectionError(f"视觉显示模式切换失败 (mode {desired})，未收到板端回执")

        self.automatic_enabled = True
        self.arbiter.until = 0
        self.session_epoch += 1

    def start(self, mode="pet", camera=0):
        if camera in ("remote", -1, "phone"):
            return self.start_remote(mode=mode)
        if mode not in self.MODES or type(camera) is not int or not 0 <= camera <= 9:
            raise ValueError("Invalid vision mode/camera")
        if self.thread and self.thread.is_alive() and camera != self.camera:
            raise ValueError("Stop the camera before changing its index")
        self._prepare_mode_and_takeover(mode)
        self.active_session_id = f"cam_{self.session_epoch}_{int(time.time())}"
        self.source = "camera"
        if self.thread and self.thread.is_alive():
            if camera != self.camera:
                raise ValueError("Stop the camera before changing its index")
            self.mode = mode
            return
        self.mode = mode
        self.camera = camera
        self.error = None
        self._record_face(None)
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._capture, daemon=True)
        self.thread.start()

    def start_remote(self, mode="pet"):
        if mode not in self.MODES:
            raise ValueError("Invalid vision mode")
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Stop the local camera before starting remote session")
        self.stop_event.clear()
        self._prepare_mode_and_takeover(mode)
        self.active_session_id = f"remote_{self.session_epoch}_{int(time.time())}"
        self.source = "remote"
        self.mode = mode
        self.started = True
        self.error = None
        return self.active_session_id

    def manual_mode(self, mode):
        compatible = {
            "pet": {17},
            "identity": {17},
            "fingertip": {26},
            "sandbox": {27},
            "gesture_game": {19, 21, 32},
            "gaze_game": {19, 21, 32},
        }
        was_enabled = self.automatic_enabled
        self.automatic_enabled = mode in compatible.get(self.mode, set())
        if was_enabled and not self.automatic_enabled:
            # User manually switched to a mode incompatible with current vision interaction.
            # Invalidate in-flight frames immediately so late frames don't override user choice.
            self.session_epoch += 1

    def stop_remote(self, session_id=None):
        """Only stops an active remote vision session.
        If local PC camera is running (source == 'camera'), local camera is never touched."""
        if self.source == "remote":
            if session_id is None or self.active_session_id == session_id:
                self.started = False
                self.source = "none"
                self.active_session_id = None
                self.session_epoch += 1
                self._record_face(None)
                if hasattr(self, "frame_lock"):
                    with self.frame_lock:
                        self.latest_jpeg = None
                if hasattr(self, "_remote_hands") and self._remote_hands:
                    try:
                        self._remote_hands.close()
                        self._remote_face.close()
                    except Exception:
                        pass
                    self._remote_hands = None
                    self._remote_face = None
                return True
        return False

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=4)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Camera has not released yet")
        self.started = False
        self.source = "none"
        self.active_session_id = None
        self.session_epoch += 1
        self._record_face(None)
        if hasattr(self, "frame_lock"):
            with self.frame_lock:
                self.latest_jpeg = None
        if hasattr(self, "_remote_hands") and self._remote_hands:
            try:
                self._remote_hands.close()
                self._remote_face.close()
            except Exception:
                pass
            self._remote_hands = None
            self._remote_face = None

    def _record_face(self, image):
        """Publish a detached sample; a missing/invalid crop invalidates enrollment."""
        with self.face_lock:
            self.last_face = image.copy() if image is not None else None
            self.face_sample_at = time.monotonic() if image is not None else None

    def _is_frame_valid(self, frame_meta=None):
        """Check whether in-flight frame still belongs to the active session and epoch."""
        if frame_meta is None:
            # Allow explicit synthetic/simulation observation injection
            if getattr(self.controller, "port", None) == "SIMULATION" or not self.started:
                return True
            return self.started and not self.stop_event.is_set()
        source, session_id, epoch = frame_meta
        if not self.started or self.stop_event.is_set():
            return False
        if self.source != source:
            return False
        if self.session_epoch != epoch:
            return False
        if self.active_session_id != session_id:
            return False
        return True

    def _process_cv_frame(self, image, hands, face, is_flipped=False, frame_meta=None):
        import cv2
        import numpy as np
        import mediapipe as mp

        if not is_flipped:
            image = cv2.flip(image, 1)
        h, w = image.shape[:2]
        side = min(h, w)
        image = image[
            (h - side) // 2 : (h + side) // 2, (w - side) // 2 : (w + side) // 2
        ]
        preview = image.copy()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        hand = hands.process(rgb)
        faces = face.process(rgb)

        # Check validity right after ML inference; if session was stopped or switched, discard
        if not self._is_frame_valid(frame_meta):
            return {"present": False, "stale": True}

        observation = {"present": bool(faces.multi_face_landmarks)}
        if hand.multi_hand_landmarks:
            hl = hand.multi_hand_landmarks[0]
            observation["hand"] = self.features.hand(
                [[v.x, v.y, v.z] for v in hl.landmark]
            )
            mp.solutions.drawing_utils.draw_landmarks(
                preview, hl, mp.solutions.hands.HAND_CONNECTIONS
            )
            pt8 = hl.landmark[8]
            cx, cy = int(pt8.x * side), int(pt8.y * side)
            cv2.circle(preview, (cx, cy), 8, (0, 255, 0), -1)
            cv2.circle(preview, (cx, cy), 12, (255, 255, 255), 2)
            if observation.get("hand", {}).get("pinch"):
                cv2.putText(preview, "PINCH", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        if faces.multi_face_landmarks:
            fl = faces.multi_face_landmarks[0]
            points = [[v.x, v.y, v.z] for v in fl.landmark]
            observation.update(self.features.face(points, time.monotonic(), side, side))

            pts = np.array(points)
            lo = np.clip(pts[:, :2].min(axis=0), 0, 1)
            hi = np.clip(pts[:, :2].max(axis=0), 0, 1)
            x1, y1 = int(lo[0] * side), int(lo[1] * side)
            x2, y2 = int(hi[0] * side), int(hi[1] * side)
            cv2.rectangle(preview, (x1, y1), (x2, y2), (255, 120, 0), 2)

            crop = image[y1:y2, x1:x2]
            image_sample = (
                cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (100, 100))
                if crop.size else None
            )
            if self._is_frame_valid(frame_meta):
                self._record_face(image_sample)
            if self.mode == "identity" and self.identity is None:
                from identity_store import IdentityStore

                self.identity = IdentityStore()
            if self.mode == "identity" and self.identity and self._is_frame_valid(frame_meta):
                label, confidence = self.identity.predict(self.last_face)
                observation["identity"] = label
                observation["identity_distance"] = confidence
                cv2.putText(preview, f"{label}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            if self._is_frame_valid(frame_meta):
                self._record_face(None)

        if not self._is_frame_valid(frame_meta):
            return {"present": False, "stale": True}

        enc_ok, enc_buf = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if enc_ok and hasattr(self, "frame_lock") and self._is_frame_valid(frame_meta):
            with self.frame_lock:
                if self._is_frame_valid(frame_meta):
                    self.latest_jpeg = enc_buf.tobytes()

        if self._is_frame_valid(frame_meta):
            self.process(observation, frame_meta=frame_meta)
        return observation

    def process_remote_frame(self, raw_bytes, mode=None, session_id=None):
        if not self.started or self.stop_event.is_set():
            raise RuntimeError("Vision session is stopped")
        if self.source == "camera":
            raise RuntimeError("Local camera is active; remote frame rejected")
        if self.source != "remote":
            raise RuntimeError("No remote vision session active")
        if not session_id:
            raise RuntimeError("Missing vision session ID")
        if session_id != self.active_session_id:
            raise RuntimeError("Stale or invalid session ID")

        import cv2
        import numpy as np
        import mediapipe as mp

        if mode and mode in self.MODES:
            self.mode = mode

        # Bind this frame to the active session generation snapshot
        frame_meta = (self.source, session_id, self.session_epoch)

        if not hasattr(self, "_remote_hands") or self._remote_hands is None:
            if hasattr(mp, "solutions"):
                self._remote_hands = mp.solutions.hands.Hands(max_num_hands=1, model_complexity=0)
                self._remote_face = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
            else:
                self._remote_hands = None
                self._remote_face = None

        nparr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image")

        if self._remote_hands and self._remote_face:
            return self._process_cv_frame(img, self._remote_hands, self._remote_face, is_flipped=True, frame_meta=frame_meta)
        return {"present": False}

    def _capture(self):
        cap = None
        try:
            import cv2
            import mediapipe as mp
            import sys

            # Use DirectShow on Windows to avoid MSMF capture failures
            if sys.platform == "win32":
                cap = cv2.VideoCapture(self.camera, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(self.camera)
            else:
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
                    meta = (self.source, self.active_session_id, self.session_epoch)
                    self._process_cv_frame(image, hands, face, is_flipped=False, frame_meta=meta)
                    self.stop_event.wait(0.04)
        except Exception as exc:
            self.error = str(exc)
        finally:
            if cap:
                cap.release()
            self.started = False
            self._record_face(None)
            if hasattr(self, "frame_lock"):
                with self.frame_lock:
                    self.latest_jpeg = None

    def process(self, observation, now=None, frame_meta=None):
        if not self._is_frame_valid(frame_meta):
            return
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
        if not self._is_frame_valid(frame_meta):
            return
        # Context does not switch a user-selected display mode.
        self.controller.pet_context(
            datetime.now().hour,
            observation.get("gaze_x", 0.5) * 2 - 1,
            present or now - self.last_seen < 15,
            bool(observation.get("tired", False)),
        )
        allowed = self.automatic_enabled and self.arbiter.allows_automatic()
        if not allowed or not self._is_frame_valid(frame_meta):
            return
        hand = observation.get("hand", {})
        from wifi_gateway import get_wifi_gateway

        mode = getattr(self.controller, "mode", None)
        if mode is None:
            mode = get_wifi_gateway().last_mode
        if self.mode in ("fingertip", "sandbox"):
            desired = 26 if self.mode == "fingertip" else 27
            if mode != desired:
                if not self._is_frame_valid(frame_meta):
                    return
                if not self.controller.send_json({"cmd": "mode", "val": desired}):
                    return
            if not self._is_frame_valid(frame_meta):
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
        elif self.mode in ("gaze_game", "gesture_game") and mode in (19, 21,32):
            if not self._is_frame_valid(frame_meta):
                return
            game_mode=mode
            if mode==32:
                from arcade_runner import get_arcade_session
                gid=get_arcade_session(self.controller).status.get('game_id')
                if gid not in (33,41):return
                game_mode=19 if gid==33 else 21
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
            if not valid:
                if self.pending_direction is not None:
                    self.pending_direction = None
                    if mode == 32:
                        try:
                            from arcade_runner import get_arcade_session
                            get_arcade_session(self.controller).input_state(0, 0)
                        except Exception:
                            pass
                return

            if direction != self.pending_direction:
                self.pending_direction = direction
                self.direction_since = now
                if direction is None and mode == 32:
                    try:
                        from arcade_runner import get_arcade_session
                        get_arcade_session(self.controller).input_state(0, 0)
                    except Exception:
                        pass
            if direction and now - self.direction_since > 0.2 and now - self.last_input > 0.3:
                reaction = (
                    min(10000, max(0, (now - self.last_input) * 1000)) if self.last_input else 1000
                )
                self.last_input = now
                game_success = bool(
                    observation.get(
                        "game_success",
                        observation.get("success", observation.get("frustration", 0) <= 0.6),
                    )
                )
                if not self._is_frame_valid(frame_meta):
                    return
                self.controller.performance(
                    reaction, observation.get("frustration", 0), game_success
                )
                if not self._is_frame_valid(frame_meta):
                    return
                if game_mode == 19:
                    dx, dy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[
                        direction
                    ]
                    self.controller.snake_move(dx, dy)
                else:
                    self.controller.tetris_action(
                        {"left": "left", "right": "right", "up": "rot", "down": "drop"}[direction]
                    )
        elif self.mode == "pet":
            if not self._is_frame_valid(frame_meta):
                return
            if now - self.last_seen > 15 and mode == 17:
                if self.controller.send_json({"cmd": "mode", "val": 31}):
                    self.previous_auto_mode = 17
            elif present and mode == 31 and self.previous_auto_mode == 17:
                self.controller.send_json({"cmd": "mode", "val": 17})
                self.previous_auto_mode = None
            if (
                (observation.get("tired")
                or (self.strain_since is not None and now - self.strain_since > 2))
                and mode == 17
                and now - self.last_greet > 120
            ):
                self.last_greet = now
                if self.controller.send_json({"cmd": "mode", "val": 31}):
                    self.previous_auto_mode = 17
                if self.voice and self._is_frame_valid(frame_meta):
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
            if self.voice and self._is_frame_valid(frame_meta):
                self.voice.speak(
                    f"欢迎回来，{observation['identity']}。\nおかえりなさい。", block=False
                )

    def enroll(self, name):
        with self.face_lock:
            age = (
                time.monotonic() - self.face_sample_at
                if self.face_sample_at is not None else None
            )
            if (
                not self.started or not self.last_observation.get("present", False)
                or self.last_face is None or age is None or not 0 <= age <= 1.0
            ):
                raise ValueError("No current face to enroll; a sample within 1 second is required")
            if self.identity is None:
                from identity_store import IdentityStore

                self.identity = IdentityStore()
            return self.identity.enroll(name, self.last_face.copy())

    def status(self):
        age = time.time() - self.observed_at if self.observed_at else None
        return dict(
            running=self.started,
            source=self.source,
            session_id=self.active_session_id,
            mode=self.mode,
            automatic_enabled=self.automatic_enabled,
            error=self.error,
            age_seconds=age,
            fresh=bool(self.started and age is not None and age < 3),
            observation=self.last_observation,
        )
