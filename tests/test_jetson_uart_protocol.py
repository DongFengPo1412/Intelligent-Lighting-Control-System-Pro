"""Unit and framing tests for ESP32-S3 Jetson Nano UART1 communication protocol."""
import json
import unittest

class JetsonUartParser:
    """Python reference parser reflecting firmware-s3/main/protocol/jetson_uart.cc."""
    def __init__(self, max_line_len=1024, version="2.2.0"):
        self.max_line_len = max_line_len
        self.version = version
        self.rx_buffer = bytearray()
        self.dispatched_commands = []
        self.system_state = {
            "mode": 14,
            "brightness": 20,
            "mic_streaming": False,
            "arcade_active": 0,
            "arcade_game_id": 0
        }

    def feed_bytes(self, chunk: bytes) -> list[dict]:
        replies = []
        for b in chunk:
            c = chr(b)
            if c in ('\n', '\r'):
                if len(self.rx_buffer) > 0:
                    line = self.rx_buffer.decode('utf-8', errors='replace').strip()
                    self.rx_buffer.clear()
                    if line:
                        reply = self.process_line(line)
                        if reply:
                            replies.append(reply)
            else:
                if len(self.rx_buffer) < self.max_line_len:
                    self.rx_buffer.append(b)
                else:
                    self.rx_buffer.clear()
                    replies.append({
                        "status": "error",
                        "error": "frame_overflow",
                        "max_bytes": self.max_line_len
                    })
        return replies

    def process_line(self, line: str) -> dict:
        req_id = None
        cmd = ""
        is_json = False

        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                is_json = True
                req_id = parsed.get("req_id")
                if req_id is None:
                    req_id = parsed.get("id")
                cmd = parsed.get("cmd") or parsed.get("action") or ""
        except json.JSONDecodeError:
            pass

        def with_req_id(resp: dict) -> dict:
            if req_id is not None:
                resp["req_id"] = req_id
            return resp

        if is_json:
            cmd_lower = cmd.lower()
            if cmd_lower == "ping":
                return with_req_id({"status": "ok", "pong": True, "version": self.version})
            elif cmd_lower in ("get_status", "status"):
                resp = {
                    "status": "ok",
                    "version": self.version,
                    "board": "esp32s3_pro",
                    **self.system_state
                }
                return with_req_id(resp)
            elif cmd_lower == "version":
                return with_req_id({"status": "ok", "version": self.version})
            else:
                self.dispatched_commands.append(line)
                return with_req_id({"status": "ok", "executed": True})

        # Plain text commands
        text_lower = line.strip().lower()
        if text_lower == "ping":
            return {"status": "ok", "pong": True, "version": self.version}
        elif text_lower in ("status", "get_status"):
            return {
                "status": "ok",
                "version": self.version,
                "board": "esp32s3_pro",
                **self.system_state
            }
        elif text_lower == "version":
            return {"status": "ok", "version": self.version}
        else:
            self.dispatched_commands.append(line)
            return {"status": "ok", "executed": True, "cmd": line}


class TestJetsonUartProtocol(unittest.TestCase):
    def setUp(self):
        self.parser = JetsonUartParser()

    def test_01_ping_with_string_req_id(self):
        replies = self.parser.feed_bytes(b'{"cmd":"ping","req_id":"req_001"}\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["pong"])
        self.assertEqual(replies[0]["req_id"], "req_001")
        self.assertEqual(replies[0]["version"], "2.2.0")

    def test_02_ping_with_numeric_req_id(self):
        replies = self.parser.feed_bytes(b'{"cmd":"ping","req_id":42}\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["pong"])
        self.assertEqual(replies[0]["req_id"], 42)

    def test_03_get_status_response(self):
        replies = self.parser.feed_bytes(b'{"cmd":"get_status","req_id":"st_99"}\n')
        self.assertEqual(len(replies), 1)
        r = replies[0]
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["req_id"], "st_99")
        self.assertEqual(r["board"], "esp32s3_pro")
        self.assertEqual(r["mode"], 14)
        self.assertEqual(r["brightness"], 20)
        self.assertFalse(r["mic_streaming"])

    def test_04_action_alias(self):
        replies = self.parser.feed_bytes(b'{"action":"ping"}\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["pong"])

    def test_05_business_command_dispatch(self):
        replies = self.parser.feed_bytes(b'{"cmd":"countdown","seconds":30,"req_id":"c1"}\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["executed"])
        self.assertEqual(replies[0]["req_id"], "c1")
        self.assertEqual(len(self.parser.dispatched_commands), 1)

    def test_06_plain_text_ping_and_status(self):
        replies = self.parser.feed_bytes(b'ping\r\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["pong"])

        replies = self.parser.feed_bytes(b'status\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertEqual(replies[0]["board"], "esp32s3_pro")

    def test_07_packet_fragmentation(self):
        # Frame split across multiple chunks
        replies = self.parser.feed_bytes(b'{"cmd"')
        self.assertEqual(len(replies), 0)
        replies = self.parser.feed_bytes(b':"ping",')
        self.assertEqual(len(replies), 0)
        replies = self.parser.feed_bytes(b'"req_id":"frag_1"}\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["req_id"], "frag_1")
        self.assertTrue(replies[0]["pong"])

    def test_08_sticky_packets_concatenation(self):
        # Two frames packed into a single chunk
        chunk = b'{"cmd":"ping","req_id":"p1"}\n{"cmd":"version","req_id":"v1"}\n'
        replies = self.parser.feed_bytes(chunk)
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["req_id"], "p1")
        self.assertTrue(replies[0]["pong"])
        self.assertEqual(replies[1]["req_id"], "v1")
        self.assertEqual(replies[1]["version"], "2.2.0")

    def test_09_frame_overflow_drop(self):
        # Send > 1024 bytes without newline
        big_chunk = b'X' * 1025
        replies = self.parser.feed_bytes(big_chunk)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "error")
        self.assertEqual(replies[0]["error"], "frame_overflow")

        # Next normal frame must be parsed cleanly
        replies = self.parser.feed_bytes(b'{"cmd":"ping","req_id":"recovered"}\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["req_id"], "recovered")
        self.assertTrue(replies[0]["pong"])

    def test_10_empty_lines_and_whitespace_ignored(self):
        chunk = b'   \r\n\n\t\n{"cmd":"ping"}\n   \n'
        replies = self.parser.feed_bytes(chunk)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["pong"])


if __name__ == "__main__":
    unittest.main()
