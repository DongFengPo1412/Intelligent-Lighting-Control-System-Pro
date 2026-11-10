import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from multimodal_hub import MultimodalHub, ControlArbiter


class DummyController:
    def __init__(self, mode=1, port="COM9"):
        self.mode = mode
        self.port = port
        self.sent_json = []
        self._arbiter = ControlArbiter()
        self.snake_moved = []
        self.tetris_actions = []

    def send_json(self, payload):
        self.sent_json.append(payload)
        if payload.get("cmd") == "mode":
            self.mode = payload.get("val")
        return True

    def snake_move(self, dx, dy):
        self.snake_moved.append((dx, dy))
        return True

    def tetris_action(self, action):
        self.tetris_actions.append(action)
        return True

    def performance(self, reaction, frustration, success):
        return True

    def track(self, x, y, present, count):
        return True

    def hand(self, x, y, z, pinch, present):
        return True

    def pet_context(self, *args, **kwargs):
        return True


class DummyArcadeSession:
    def __init__(self, game_id=33):
        self.status = {"game_id": game_id, "state": 1}
        self.input_history = []

    def input_state(self, down, pressed):
        self.input_history.append((down, pressed))
        return {"status": "ok"}


class VisionTakeoverAndClosureTests(unittest.TestCase):
    def setUp(self):
        self.controller = DummyController(mode=1)  # Starts in pure red (mode 1)
        self.hub = MultimodalHub(controller=self.controller)

    def tearDown(self):
        if self.hub.started:
            self.hub.stop()

    def test_fingertip_takes_over_from_pure_red_and_clears_arbiter(self):
        """Active vision must override prior manual state (red light) and switch mode to 26."""
        # Simulate prior red light command setting manual lock on arbiter
        self.controller._arbiter.claim_user(seconds=60.0)
        self.hub.arbiter = self.controller._arbiter
        self.assertFalse(self.hub.arbiter.allows_automatic())

        # Actively enable fingertip
        sess_id = self.hub.start_remote(mode="fingertip")
        self.assertTrue(self.hub.started)
        self.assertTrue(self.hub.automatic_enabled)
        self.assertTrue(self.hub.arbiter.allows_automatic())  # Arbiter lock was cleared
        self.assertEqual(self.controller.mode, 26)
        self.assertIn({"cmd": "mode", "val": 26}, self.controller.sent_json)

    def test_pure_red_blocks_gesture_game_with_explicit_guidance(self):
        """Selecting gesture_game when on pure red must raise ValueError demanding arcade cartridge."""
        self.controller.mode = 1  # Pure red
        with self.assertRaises(ValueError) as ctx:
            self.hub.start_remote(mode="gesture_game")
        self.assertIn("街机菜单", str(ctx.exception))
        self.assertIn("贪吃蛇", str(ctx.exception))

    def test_unsupported_arcade_cartridge_blocks_gesture_game(self):
        """Cartridge #001 Mario does not support gesture game; must be rejected."""
        self.controller.mode = 32  # Arcade mode
        mario_session = DummyArcadeSession(game_id=1)
        with patch("arcade_runner.get_arcade_session", return_value=mario_session):
            with self.assertRaises(ValueError) as ctx:
                self.hub.start_remote(mode="gesture_game")
            self.assertIn("街机菜单", str(ctx.exception))

    def test_supported_arcade_cartridge_starts_gesture_game(self):
        """Cartridge #033 Snake supports gesture game."""
        self.controller.mode = 32
        snake_session = DummyArcadeSession(game_id=33)
        with patch("arcade_runner.get_arcade_session", return_value=snake_session):
            sess_id = self.hub.start_remote(mode="gesture_game")
            self.assertTrue(self.hub.started)
            self.assertEqual(self.hub.mode, "gesture_game")

    def test_gaze_game_requires_calibration(self):
        """Gaze game must verify gaze calibration."""
        self.controller.mode = 32
        snake_session = DummyArcadeSession(game_id=33)
        self.hub.features.gaze.coefficients = None  # Not calibrated
        with patch("arcade_runner.get_arcade_session", return_value=snake_session):
            with self.assertRaises(ValueError) as ctx:
                self.hub.start_remote(mode="gaze_game")
            self.assertIn("视线校准", str(ctx.exception))

    def test_hand_loss_releases_arcade_keys(self):
        """When hand disappears ('失踪后的释键'), input_state(0, 0) must be called immediately."""
        self.controller.mode = 32
        snake_session = DummyArcadeSession(game_id=33)
        with patch("arcade_runner.get_arcade_session", return_value=snake_session):
            sess_id = self.hub.start_remote(mode="gesture_game")
            frame_meta = ("remote", sess_id, self.hub.session_epoch)

            # 1. Hand present: x < 0.3 -> 'left'
            obs_hand = {"present": True, "hand": {"x": 0.1, "y": 0.5}}
            self.hub.process(obs_hand, now=100.0, frame_meta=frame_meta)
            self.assertEqual(self.hub.pending_direction, "left")

            # 2. Hand suddenly disappears (present=False or empty hand)
            obs_lost = {"present": False, "hand": {}}
            self.hub.process(obs_lost, now=100.1, frame_meta=frame_meta)

            # Assert: pending_direction is cleared and input_state(0, 0) was invoked!
            self.assertIsNone(self.hub.pending_direction)
            self.assertIn((0, 0), snake_session.input_history)

    def test_manual_mode_invalidation(self):
        """Manual mode switch to red light invalidates prior in-flight vision frames."""
        sess_id = self.hub.start_remote(mode="fingertip")
        old_epoch = self.hub.session_epoch

        # User presses physical button / web slider to switch to pure red (mode 1)
        self.hub.manual_mode(1)

        # Automatic must be disabled and session_epoch incremented
        self.assertFalse(self.hub.automatic_enabled)
        self.assertGreater(self.hub.session_epoch, old_epoch)

        # Late in-flight frame from old session must be rejected
        old_meta = ("remote", sess_id, old_epoch)
        self.assertFalse(self.hub._is_frame_valid(old_meta))


if __name__ == "__main__":
    unittest.main()
