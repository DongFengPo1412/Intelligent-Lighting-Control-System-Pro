"""Jetson Nano Vision Mapping Logic.
Translates detected gestures, fingertips, pinches, faces, and emotions into ESP32 commands.
Features automatic key release on hand loss to prevent runaway inputs in arcade games.
"""
from datetime import datetime
import logging
from typing import Any, Dict, Optional
from protocol import CommandBuilder

logger = logging.getLogger("VisionMapper")


class VisionMapper:
    """Dispatches vision events from camera/models to the ESP32 UART interface."""

    def __init__(self, transport, config: Optional[Dict[str, Any]] = None):
        self.transport = transport
        self.config = config or {}
        self.gesture_mappings = self.config.get("gesture_mappings", {})
        self.face_mappings = self.config.get("face_mappings", {})

        self.last_hand_visible = False
        self.last_arcade_keys = 0

    def handle_gesture(self, gesture_name: str, x: float = 0.5, y: float = 0.5, z: float = 0.0):
        """Dispatches an explicit gesture (e.g. '1', '2', 'fist', 'pinch', 'pointing')."""
        rule = self.gesture_mappings.get(str(gesture_name))
        if not rule:
            logger.debug(f"[VisionMapper] No mapping configured for gesture: {gesture_name}")
            return

        action = rule.get("action")
        if action == "mode":
            mode_val = rule.get("value", 1)
            logger.info(f"[VisionMapper] Gesture '{gesture_name}' -> Set Mode {mode_val}")
            self.transport.send_line(CommandBuilder.mode(mode_val))

        elif action == "track_fingertip":
            self.transport.send_line(CommandBuilder.track(x, y, visible=True, conf=1.0))

        elif action == "hand_pinch":
            self.transport.send_line(CommandBuilder.hand(x, y, z, pinch=True, visible=True))

        elif action == "arcade_key":
            key_name = rule.get("key", "down")
            from protocol import KEY_MAP
            mask = KEY_MAP.get(key_name, 0)
            self.last_arcade_keys = mask
            self.transport.send_line(CommandBuilder.arcade_input(mask, mask))

    def handle_hand_frame(
        self,
        visible: bool,
        x: float = 0.5,
        y: float = 0.5,
        z: float = 0.0,
        pinch: bool = False,
        mode: str = "fingertip",
    ):
        """Continuous hand landmark tracking.
        If hand disappears, immediately sends key release to avoid stuck game inputs.
        """
        if visible:
            self.last_hand_visible = True
            if mode == "fingertip":
                self.transport.send_line(CommandBuilder.track(x, y, visible=True, conf=1.0))
            elif mode == "sandbox":
                self.transport.send_line(CommandBuilder.hand(x, y, z, pinch=pinch, visible=True))
            elif mode == "arcade":
                # Directional D-pad mapping
                from protocol import KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_UP
                down = 0
                if x < 0.3:
                    down |= KEY_LEFT
                elif x > 0.7:
                    down |= KEY_RIGHT
                elif y < 0.3:
                    down |= KEY_UP
                elif y > 0.7:
                    down |= KEY_DOWN
                if pinch:
                    from protocol import KEY_A
                    down |= KEY_A

                self.last_arcade_keys = down
                self.transport.send_line(CommandBuilder.arcade_input(down, down))
        else:
            # Hand disappeared!
            if self.last_hand_visible:
                logger.info("[VisionMapper] Hand lost: releasing all inputs and fingertip focus.")
                self.last_hand_visible = False
                if mode == "fingertip":
                    self.transport.send_line(CommandBuilder.track(0.5, 0.5, visible=False, conf=0.0))
                elif mode == "sandbox":
                    self.transport.send_line(CommandBuilder.hand(0.5, 0.5, 0.0, pinch=False, visible=False))
                elif mode == "arcade":
                    self.last_arcade_keys = 0
                    self.transport.send_line(CommandBuilder.arcade_input(0, 0))
                # Global safety release
                self.transport.send_line(CommandBuilder.release_input())

    def handle_face_frame(
        self, present: bool, gaze_x: float = 0.0, smile_prob: float = 0.0, tired: bool = False
    ):
        """Dispatches face mesh presence, gaze direction, smile events, and fatigue."""
        hour = datetime.now().hour
        smile_thresh = self.face_mappings.get("smile_threshold", 0.6)

        # Desktop pet context update
        self.transport.send_line(
            CommandBuilder.pet_context(hour=hour, gaze=gaze_x, present=present, tired=tired)
        )

        # If user smiles, trigger celebration fireworks!
        if smile_prob >= smile_thresh:
            logger.info(f"[VisionMapper] Smile detected ({smile_prob:.2f})! Triggering celebration.")
            self.transport.send_line(CommandBuilder.celebrate())
