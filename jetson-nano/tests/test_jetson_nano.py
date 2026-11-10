"""Unit tests for Jetson Nano Python client modules."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from protocol import (
    BIN_FULL_FRAME,
    CommandBuilder,
    crc16_ccitt,
    pack_binary_frame,
)
from canvas_stream import (
    generate_bouncing_ball,
    generate_color_wave,
    FireSimulation,
    MatrixRainAnimation,
)
from uart_transport import JetsonUartTransport
from vision_mapping import VisionMapper


class TestJetsonProtocol(unittest.TestCase):
    def test_crc16(self):
        data = b"hello world"
        # Matches binascii.crc_hqx
        self.assertEqual(crc16_ccitt(data), 0xEFEB)

    def test_binary_header_pack(self):
        payload = b"\x00\x01\x02" * 256  # 768 bytes
        packet = pack_binary_frame(
            frame_type=BIN_FULL_FRAME,
            frame_seq=42,
            payload=payload,
            offset=0,
            commit_now=True,
            auto_mode=True,
        )
        self.assertEqual(len(packet), 16 + 768)
        self.assertEqual(packet[0:4], b"\x55\xaa\x43\x46")
        self.assertEqual(packet[4], BIN_FULL_FRAME)
        self.assertEqual(packet[5], 1)  # Version

    def test_command_builder(self):
        ping_json = json.loads(CommandBuilder.ping(req_id="p1"))
        self.assertEqual(ping_json["cmd"], "ping")
        self.assertEqual(ping_json["req_id"], "p1")

        track_json = json.loads(CommandBuilder.track(0.3, 0.7, visible=True, conf=0.95))
        self.assertEqual(track_json["cmd"], "track")
        self.assertAlmostEqual(track_json["x"], 0.3)
        self.assertAlmostEqual(track_json["y"], 0.7)

        hand_json = json.loads(CommandBuilder.hand(0.5, 0.5, -0.1, pinch=True))
        self.assertEqual(hand_json["cmd"], "hand")
        self.assertTrue(hand_json["pinch"])

        arcade_in = json.loads(CommandBuilder.arcade_input(down=2, pressed=2))
        self.assertEqual(arcade_in["action"], "input")
        self.assertEqual(arcade_in["down"], 2)


class TestCanvasGenerators(unittest.TestCase):
    def test_color_wave(self):
        pixels = generate_color_wave(1.0)
        self.assertEqual(len(pixels), 256)
        for r, g, b in pixels:
            self.assertTrue(0 <= r <= 255)
            self.assertTrue(0 <= g <= 255)
            self.assertTrue(0 <= b <= 255)

    def test_bouncing_ball(self):
        pixels = generate_bouncing_ball(2.5)
        self.assertEqual(len(pixels), 256)

    def test_matrix_rain(self):
        sim = MatrixRainAnimation()
        pixels = sim.step()
        self.assertEqual(len(pixels), 256)

    def test_fire_sim(self):
        sim = FireSimulation()
        pixels = sim.step()
        self.assertEqual(len(pixels), 256)


class TestVisionMapper(unittest.TestCase):
    def setUp(self):
        self.transport = JetsonUartTransport(simulate=True)
        self.transport.connect()
        self.mapper = VisionMapper(self.transport, {
            "gesture_mappings": {
                "1": {"action": "mode", "value": 1},
                "2": {"action": "mode", "value": 2},
            }
        })

    def test_gesture_mode_dispatch(self):
        self.mapper.handle_gesture("1")
        self.mapper.handle_gesture("2")

    def test_hand_loss_key_release(self):
        # Hand visible
        self.mapper.handle_hand_frame(visible=True, x=0.5, y=0.5, mode="arcade")
        self.assertTrue(self.mapper.last_hand_visible)

        # Hand lost -> should trigger release
        self.mapper.handle_hand_frame(visible=False, mode="arcade")
        self.assertFalse(self.mapper.last_hand_visible)
        self.assertEqual(self.mapper.last_arcade_keys, 0)


class TestCanvasStreamerAck(unittest.TestCase):
    def test_streamer_ack_distinction(self):
        from canvas_stream import CanvasStreamer

        class FakeTransport:
            def __init__(self, reply):
                self.reply = reply
            def send_raw_with_ack(self, pkt, expected_frame_seq, timeout=1.0):
                return self.reply
            def send_line(self, line, wait_reply=True):
                return self.reply

        # When overridden by user manual control
        tr_overridden = FakeTransport({"status": "ok", "committed": True, "displayed": False, "mode_overridden": True})
        st1 = CanvasStreamer(tr_overridden)
        dummy_colors = [(0, 0, 0)] * 256
        ok1 = st1.send_binary_frame(dummy_colors, auto_mode=True, require_displayed=False)
        self.assertTrue(ok1)
        self.assertTrue(st1.is_committed)
        self.assertFalse(st1.is_displayed)
        self.assertTrue(st1.is_overridden)

        # When actively rendered to matrix
        tr_displayed = FakeTransport({"status": "ok", "committed": True, "displayed": True, "mode_overridden": False})
        st2 = CanvasStreamer(tr_displayed)
        ok2 = st2.send_binary_frame(dummy_colors, auto_mode=True, require_displayed=True)
        self.assertTrue(ok2)
        self.assertTrue(st2.is_displayed)
        self.assertFalse(st2.is_overridden)


if __name__ == "__main__":
    unittest.main()
