"""Transport configuration only: never open a serial port or a network socket."""
import os
import unittest
from unittest.mock import patch
from light_controller import LightController


class WirelessDefaultTests(unittest.TestCase):
    def make(self):
        return LightController(port="TEST_ONLY")

    def test_default_never_opens_usb_and_explicit_usb_remains_available(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(LightController, "connect") as connect, patch.object(LightController, "_start_reader") as reader:
            controller = self.make()
            self.assertEqual(controller.audio_transport, "wifi")
            connect.assert_not_called()
            reader.assert_not_called()
        with patch.dict(os.environ, {"KURISU_AUDIO_TRANSPORT": "usb"}), patch.object(LightController, "connect") as connect, patch.object(LightController, "_start_reader") as reader:
            self.assertEqual(self.make().audio_transport, "usb")
            connect.assert_called_once()
            reader.assert_called_once()

    def test_invalid_transport_is_not_a_silent_usb_fallback(self):
        with patch.dict(os.environ, {"KURISU_AUDIO_TRANSPORT": "typo"}):
            with self.assertRaisesRegex(ValueError, "wifi or usb"):
                self.make()
