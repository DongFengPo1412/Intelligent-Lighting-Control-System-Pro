"""A missing optional vision dependency must be visible, without opening a camera."""
import builtins
import unittest
from unittest.mock import Mock, patch
from multimodal_hub import MultimodalHub


class VisionDependencyHealthTests(unittest.TestCase):
    def test_import_failure_clears_running_and_records_error(self):
        hub = MultimodalHub.__new__(MultimodalHub)
        hub.started = True
        hub.error = None
        hub._record_face = Mock()
        original = builtins.__import__

        def unavailable(name, *args, **kwargs):
            if name == "cv2":
                raise ImportError("test: cv2 unavailable")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=unavailable):
            hub._capture()
        self.assertFalse(hub.started)
        self.assertIn("cv2 unavailable", hub.error)
        hub._record_face.assert_called_once_with(None)
