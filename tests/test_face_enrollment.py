"""Enrollment lifecycle regression tests; no camera, network or face files."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pc-agent-vision"))
from multimodal_hub import MultimodalHub


class Controller:
    pass


class Identity:
    def __init__(self):
        self.samples = []

    def enroll(self, name, image):
        self.samples.append(image)
        return {"name": name}


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.hub = MultimodalHub(Controller())
        self.hub.identity = Identity()
        self.hub.started = True
        self.hub.last_observation = {"present": True}
        with patch("multimodal_hub.time.monotonic", return_value=10):
            self.hub._record_face(np.zeros((100, 100), dtype=np.uint8))

    def test_current_face_is_copied(self):
        with patch("multimodal_hub.time.monotonic", return_value=10.5):
            self.assertEqual(self.hub.enroll("test"), {"name": "test"})
        self.hub.last_face.fill(255)
        self.assertEqual(int(self.hub.identity.samples[0].max()), 0)

    def test_missing_face_rejects_previous_sample(self):
        self.hub.last_observation = {"present": False}
        with patch("multimodal_hub.time.monotonic", return_value=10.1):
            with self.assertRaises(ValueError):
                self.hub.enroll("test")
        self.assertEqual(self.hub.identity.samples, [])

    def test_stale_sample_rejected(self):
        with patch("multimodal_hub.time.monotonic", return_value=11.01):
            with self.assertRaises(ValueError):
                self.hub.enroll("test")

    def test_missing_crop_invalidates_sample(self):
        self.hub._record_face(None)
        self.assertIsNone(self.hub.last_face)
        self.assertIsNone(self.hub.face_sample_at)
        with self.assertRaises(ValueError):
            self.hub.enroll("test")

    def test_stop_invalidates_sample(self):
        self.hub.stop()
        self.assertIsNone(self.hub.last_face)
        with self.assertRaises(ValueError):
            self.hub.enroll("test")

    def test_clock_reversal_is_not_fresh(self):
        with patch("multimodal_hub.time.monotonic", return_value=9):
            with self.assertRaises(ValueError):
                self.hub.enroll("test")


if __name__ == "__main__":
    unittest.main()
