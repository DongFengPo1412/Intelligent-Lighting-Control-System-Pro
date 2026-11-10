"""Unit, framing, binary, and security tests for ESP32-S3 Jetson Nano UART1 protocol v2.3.0."""
import binascii
import json
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "jetson-nano")))

MAGIC = b"\x55\xaa\x43\x46"  # 0x55, 0xAA, 'C', 'F'
BIN_FULL_FRAME = 0x01
BIN_CHUNK_FRAME = 0x02
BIN_SINGLE_PIXEL = 0x03
BIN_CLEAR = 0x04

FLAG_COMMIT_NOW = 1 << 0
FLAG_AUTO_MODE = 1 << 1


def crc16_ccitt(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)


class JetsonUartParser:
    """Python reference parser reflecting firmware-s3/main/protocol/jetson_uart.cc & canvas_protocol.cc."""

    def __init__(self, max_line_len=1024, version="2.3.0"):
        self.max_line_len = max_line_len
        self.version = version
        self.rx_buffer = bytearray()
        self.discarding_oversized = False
        self.dispatched_commands = []
        self.state = "TEXT"
        self.header_buf = bytearray()
        self.binary_payload = bytearray()
        self.current_header = None

        # System & Arcade mock state
        self.system_state = {
            "mode": 17,
            "brightness": 20,
            "mic_streaming": False,
            "arcade_active": 0,
            "arcade_game_id": 0,
            "canvas_active": False,
            "held_keys": 0,
            "canvas_frames": 0,
            "session_id": "",
        }

        # Canvas Assembler mock state
        self.canvas_buffer = bytearray(768)
        self.canvas_received = bytearray(768)
        self.canvas_frame_id = 0
        self.canvas_in_progress = False

    def feed_bytes(self, chunk: bytes) -> list[dict]:
        replies = []
        for b in chunk:
            if self.state == "TEXT":
                if len(self.rx_buffer) == 0 and b == 0x55:
                    self.header_buf = bytearray([b])
                    self.state = "BINARY_HEADER"
                    continue

                c = chr(b)
                if c in ("\n", "\r"):
                    if self.discarding_oversized:
                        self.discarding_oversized = False
                        self.rx_buffer.clear()
                    elif len(self.rx_buffer) > 0:
                        line = self.rx_buffer.decode("utf-8", errors="replace").strip()
                        self.rx_buffer.clear()
                        if line:
                            reply = self.process_line(line)
                            if reply:
                                replies.append(reply)
                else:
                    if self.discarding_oversized:
                        continue
                    if len(self.rx_buffer) < self.max_line_len:
                        self.rx_buffer.append(b)
                    else:
                        self.discarding_oversized = True
                        self.rx_buffer.clear()
                        replies.append({
                            "status": "error",
                            "error": "frame_overflow",
                            "max_bytes": self.max_line_len,
                        })

            elif self.state == "BINARY_HEADER":
                self.header_buf.append(b)
                h_len = len(self.header_buf)

                if h_len == 2 and b != 0xAA:
                    self.state = "TEXT"
                    self.rx_buffer.extend(self.header_buf)
                    self.header_buf.clear()
                    continue
                if h_len == 3 and b != 0x43:
                    self.state = "TEXT"
                    self.rx_buffer.extend(self.header_buf)
                    self.header_buf.clear()
                    continue
                if h_len == 4 and b != 0x46:
                    self.state = "TEXT"
                    self.rx_buffer.extend(self.header_buf)
                    self.header_buf.clear()
                    continue

                if h_len >= 16:
                    # Unpack header: magic(4), type(1), version(1), frame_seq(2), payload_len(2), offset(2), flags(2), crc16(2)
                    magic, b_type, ver, seq, plen, offset, flags, crc = struct.unpack(
                        "<4sBBHHHHH", self.header_buf
                    )
                    self.current_header = {
                        "magic": magic,
                        "type": b_type,
                        "version": ver,
                        "frame_seq": seq,
                        "payload_len": plen,
                        "offset": offset,
                        "flags": flags,
                        "crc16": crc,
                    }
                    if plen > 768:
                        self.state = "TEXT"
                        self.header_buf.clear()
                        replies.append({
                            "status": "error",
                            "error": "frame_overflow",
                            "max_bytes": 768,
                        })
                    elif plen == 0:
                        reply = self.process_binary_frame(self.current_header, b"")
                        if reply:
                            replies.append(reply)
                        self.state = "TEXT"
                        self.header_buf.clear()
                    else:
                        self.binary_payload = bytearray()
                        self.state = "BINARY_PAYLOAD"

            elif self.state == "BINARY_PAYLOAD":
                self.binary_payload.append(b)
                if len(self.binary_payload) >= self.current_header["payload_len"]:
                    reply = self.process_binary_frame(
                        self.current_header, bytes(self.binary_payload)
                    )
                    if reply:
                        replies.append(reply)
                    self.state = "TEXT"
                    self.header_buf.clear()
                    self.binary_payload.clear()

        return replies

    def process_binary_frame(self, header: dict, payload: bytes) -> dict:
        b_type = header["type"]
        seq = header["frame_seq"]
        offset = header["offset"]
        flags = header["flags"]
        expected_crc = header["crc16"]
        auto_mode = bool(flags & FLAG_AUTO_MODE)
        commit_now = bool(flags & FLAG_COMMIT_NOW)

        if self.system_state.get("session_state") in ("stopped", "expired"):
            err = "session_stopped" if self.system_state.get("session_state") == "stopped" else "session_expired"
            return {
                "status": "error",
                "type": "bin_frame",
                "frame_id": seq,
                "committed": False,
                "displayed": False,
                "received_bytes": 0,
                "mode_overridden": self.system_state.get("manual_override", False),
                "error": err,
            }

        if expected_crc != 0:
            actual_crc = crc16_ccitt(payload)
            if actual_crc != expected_crc:
                return {
                    "status": "error",
                    "type": "bin_frame",
                    "frame_id": seq,
                    "error": "crc_mismatch",
                }

        if b_type == BIN_FULL_FRAME:
            if len(payload) != 768:
                return {
                    "status": "error",
                    "type": "bin_frame",
                    "frame_id": seq,
                    "error": "invalid_full_frame_length",
                }
            self.canvas_buffer[:] = payload
            self.system_state["canvas_frames"] += 1
            if auto_mode and not self.system_state.get("manual_override", False):
                self.system_state["mode"] = 29
                self.system_state["canvas_active"] = True
            manual_overridden = self.system_state.get("manual_override", False)
            displayed = not manual_overridden and (self.system_state.get("mode") == 29)
            return {
                "status": "ok",
                "type": "bin_frame",
                "frame_id": seq,
                "committed": True,
                "displayed": displayed,
                "received_bytes": 768,
                "mode_overridden": manual_overridden,
            }

        elif b_type == BIN_CHUNK_FRAME:
            if offset + len(payload) > 768:
                return {
                    "status": "error",
                    "type": "bin_frame",
                    "frame_id": seq,
                    "error": "bounds_exceeded",
                }
            self.canvas_buffer[offset : offset + len(payload)] = payload
            for i in range(offset, offset + len(payload)):
                self.canvas_received[i] = 1

            complete = all(self.canvas_received)
            should_commit = commit_now or complete
            manual_overridden = self.system_state.get("manual_override", False)
            if should_commit:
                self.system_state["canvas_frames"] += 1
                if auto_mode and not manual_overridden:
                    self.system_state["mode"] = 29
                    self.system_state["canvas_active"] = True
                self.canvas_received = bytearray(768)
                displayed = not manual_overridden and (self.system_state.get("mode") == 29)
                return {
                    "status": "ok",
                    "type": "bin_frame",
                    "frame_id": seq,
                    "committed": True,
                    "displayed": displayed,
                    "received_bytes": 768,
                    "mode_overridden": manual_overridden,
                }
            return {
                "status": "ok",
                "type": "bin_frame",
                "frame_id": seq,
                "committed": False,
                "displayed": False,
                "received_bytes": sum(self.canvas_received),
                "mode_overridden": manual_overridden,
            }

        elif b_type == BIN_SINGLE_PIXEL:
            if len(payload) < 5:
                return {
                    "status": "error",
                    "type": "bin_frame",
                    "frame_id": seq,
                    "error": "pixel_payload_too_short",
                }
            x, y, r, g, b = payload[0], payload[1], payload[2], payload[3], payload[4]
            if x >= 16 or y >= 16:
                return {
                    "status": "error",
                    "type": "bin_frame",
                    "frame_id": seq,
                    "error": "pixel_out_of_bounds",
                }
            idx = (y * 16 + x) * 3
            self.canvas_buffer[idx : idx + 3] = bytes([r, g, b])
            if auto_mode:
                self.system_state["mode"] = 29
                self.system_state["canvas_active"] = True
            return {
                "status": "ok",
                "type": "bin_frame",
                "frame_id": seq,
                "committed": True,
                "received_bytes": 3,
            }

        elif b_type == BIN_CLEAR:
            r = payload[0] if len(payload) >= 3 else 0
            g = payload[1] if len(payload) >= 3 else 0
            b = payload[2] if len(payload) >= 3 else 0
            for i in range(256):
                self.canvas_buffer[i * 3 : i * 3 + 3] = bytes([r, g, b])
            if auto_mode:
                self.system_state["mode"] = 29
                self.system_state["canvas_active"] = True
            return {
                "status": "ok",
                "type": "bin_frame",
                "frame_id": seq,
                "committed": True,
                "received_bytes": 0,
            }

        return {
            "status": "error",
            "type": "bin_frame",
            "frame_id": seq,
            "error": "unknown_binary_type",
        }

    def process_line(self, line: str) -> dict:
        req_id = None
        cmd = ""
        is_json = False
        parsed = None

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
                    **self.system_state,
                }
                return with_req_id(resp)
            elif cmd_lower == "version":
                return with_req_id({"status": "ok", "version": self.version})
            elif cmd_lower in ("get_capabilities", "capabilities"):
                feats = [
                    "mode_switch", "brightness", "board_led", "fingertip_tracker", "light_sandbox",
                    "desk_pet", "celebrate", "pet_context", "arcade_100", "pixel_canvas",
                    "canvas_chunk", "canvas_binary", "difficulty", "performance", "mir", "gamma",
                    "session_control", "key_release"
                ]
                return with_req_id({
                    "status": "ok",
                    "version": self.version,
                    "features": feats,
                    "display": {
                        "width": 16,
                        "height": 16,
                        "color_format": "rgb888",
                        "canvas_mode": 29,
                        "fingertip_mode": 26,
                        "sandbox_mode": 27,
                        "pet_mode": 17,
                    },
                    "uart": {
                        "baud": 115200,
                        "rx_pin": 8,
                        "tx_pin": 9,
                        "max_json_line": self.max_line_len,
                        "binary_magic": "0x55AA4346",
                    },
                })
            elif cmd_lower == "release_input":
                self.system_state["held_keys"] = 0
                return with_req_id({"status": "ok", "released": True})
            elif cmd_lower == "session":
                action = (parsed.get("action") or "").lower()
                sid = parsed.get("session_id") or parsed.get("id") or ""
                if action in ("start", "resume"):
                    self.system_state["session_id"] = sid
                    self.system_state["session_active"] = True
                    self.system_state["session_state"] = "active"
                    m = parsed.get("mode")
                    if m == "fingertip" or m == 26:
                        self.system_state["mode"] = 26
                    elif m == "sandbox" or m == 27:
                        self.system_state["mode"] = 27
                    elif m == "canvas" or m == 29:
                        self.system_state["mode"] = 29
                        self.system_state["canvas_active"] = True
                    elif m == "pet" or m == 17:
                        self.system_state["mode"] = 17
                    return with_req_id({"status": "ok", "active": True, "session_id": sid})
                elif action == "stop":
                    self.system_state["session_id"] = ""
                    self.system_state["session_active"] = False
                    self.system_state["session_state"] = "stopped"
                    self.system_state["held_keys"] = 0
                    if self.system_state.get("mode") == 29:
                        self.system_state["mode"] = 1
                    return with_req_id({"status": "ok", "active": False, "session_state": "stopped"})
                elif action in ("heartbeat", "ping"):
                    if self.system_state.get("session_state") == "active":
                        return with_req_id({"status": "ok", "heartbeat": True, "active": True})
                    err = "session_stopped" if self.system_state.get("session_state") == "stopped" else "session_expired"
                    return with_req_id({"status": "error", "error": err, "active": False})
                return with_req_id({"status": "error", "error": "unknown_session_action"})

            elif cmd_lower == "canvas_chunk":
                if self.system_state.get("session_state") in ("stopped", "expired") or (self.system_state.get("session_id") and not self.system_state.get("session_active", True)):
                    err = "session_stopped" if self.system_state.get("session_state") == "stopped" else "session_expired"
                    return with_req_id({"status": "error", "error": err, "committed": False, "displayed": False})
                frame_id = parsed.get("frame_id", parsed.get("frame", 0))
                chunk_idx = parsed.get("chunk_idx", parsed.get("chunk", 0))
                total_chunks = parsed.get("total_chunks", parsed.get("total", 1))
                offset = parsed.get("offset", 0)
                hex_str = parsed.get("hex", "")
                commit_now = bool(parsed.get("commit", False))
                auto_mode = bool(parsed.get("auto_mode", True))
                crc_val = parsed.get("crc", 0)

                if not hex_str or len(hex_str) % 2 != 0:
                    return with_req_id({"status": "error", "error": "invalid_hex_length"})

                if len(hex_str) // 2 > 384 or (len(hex_str) // 2 + offset > 768):
                    return with_req_id({"status": "error", "error": "chunk_bounds_overflow"})

                if total_chunks == 0 or total_chunks > 16 or chunk_idx >= total_chunks:
                    return with_req_id({"status": "error", "error": "invalid_chunk_indices"})

                try:
                    raw = bytes.fromhex(hex_str)
                except ValueError:
                    return with_req_id({"status": "error", "error": "invalid_hex_chars"})

                if crc_val != 0:
                    act_crc = crc16_ccitt(raw)
                    if act_crc != crc_val:
                        return with_req_id({"status": "error", "error": "crc_mismatch"})

                self.canvas_buffer[offset : offset + len(raw)] = raw
                for i in range(offset, offset + len(raw)):
                    self.canvas_received[i] = 1

                complete = all(self.canvas_received)
                if commit_now and not complete:
                    return with_req_id({"status": "error", "error": "incomplete_frame_premature_commit"})

                manual_overridden = self.system_state.get("manual_override", False)
                if complete:
                    self.system_state["canvas_frames"] += 1
                    if auto_mode and not manual_overridden:
                        self.system_state["mode"] = 29
                        self.system_state["canvas_active"] = True
                    self.canvas_received = bytearray(768)
                    displayed = not manual_overridden and (self.system_state.get("mode") == 29)
                    return with_req_id({
                        "status": "ok",
                        "frame_id": frame_id,
                        "chunk_idx": chunk_idx,
                        "committed": True,
                        "displayed": displayed,
                        "received_bytes": 768,
                        "mode_overridden": manual_overridden,
                    })

                return with_req_id({
                    "status": "ok",
                    "frame_id": frame_id,
                    "chunk_idx": chunk_idx,
                    "committed": False,
                    "displayed": False,
                    "received_bytes": sum(self.canvas_received),
                    "mode_overridden": manual_overridden,
                })

            elif cmd_lower in ("clear_canvas", "canvas_clear"):
                r = int(parsed.get("r", 0))
                g = int(parsed.get("g", 0))
                b = int(parsed.get("b", 0))
                for i in range(256):
                    self.canvas_buffer[i * 3 : i * 3 + 3] = bytes([r, g, b])
                if parsed.get("auto_mode"):
                    self.system_state["mode"] = 29
                    self.system_state["canvas_active"] = True
                return with_req_id({"status": "ok", "cleared": True})

            elif cmd_lower == "arcade":
                action = (parsed.get("action") or "").lower()
                if action == "status":
                    return with_req_id({
                        "status": "ok",
                        "active": bool(self.system_state["arcade_active"]),
                        "game_id": self.system_state["arcade_game_id"],
                        "score": 120,
                        "high_score": 500,
                        "lives": 3,
                        "state": 1,
                    })
                elif action == "select":
                    gid = parsed.get("game_id", 0)
                    if 1 <= gid <= 101:
                        self.system_state["arcade_active"] = 1
                        self.system_state["arcade_game_id"] = gid
                        self.system_state["mode"] = 32
                        self.dispatched_commands.append(line)
                        return with_req_id({"status": "ok", "executed": True})
                    return with_req_id({"status": "error", "error": "command_rejected"})
                elif action == "input":
                    down = parsed.get("down", 0)
                    self.system_state["held_keys"] = down
                    self.dispatched_commands.append(line)
                    return with_req_id({"status": "ok", "executed": True})
                elif action in ("start", "pause", "resume", "reset", "exit", "config"):
                    if action == "exit":
                        self.system_state["arcade_active"] = 0
                        self.system_state["held_keys"] = 0
                    self.dispatched_commands.append(line)
                    return with_req_id({"status": "ok", "executed": True})
                return with_req_id({"status": "error", "error": "command_rejected"})

            else:
                disallowed = {
                    "pair", "control_token", "token", "reboot", "restart",
                    "factory_reset", "reset_nvs", "erase_flash", "write_flash",
                    "mic_export", "audio_capture", "ota"
                }
                if cmd_lower in disallowed:
                    return with_req_id({"status": "error", "error": "unauthorized_command", "executed": False})

                allowed_json = {
                    "mode", "brightness", "b", "board_led", "led", "arcade",
                    "pet", "kurisu", "countdown", "stop_countdown", "stop_cd", "beep", "key",
                    "track_cal", "track", "hand", "pet_context", "celebrate",
                    "difficulty", "performance", "mir", "pixel", "canvas", "gamma"
                }
                if cmd_lower in allowed_json:
                    if self.system_state.get("session_state") in ("stopped", "expired") or (self.system_state.get("session_id") and not self.system_state.get("session_active", True)):
                        if cmd_lower in ("track", "hand", "pet_context", "face", "track_cal", "pixel", "canvas", "clear_canvas", "arcade"):
                            err = "session_stopped" if self.system_state.get("session_state") == "stopped" else "session_expired"
                            return with_req_id({"status": "error", "error": err, "executed": False})

                    if cmd_lower == "mode":
                        val = parsed.get("val", parsed.get("mode"))
                        if val is not None:
                            val_int = int(val)
                            if self.system_state.get("manual_override", False):
                                return with_req_id({
                                    "status": "ok",
                                    "executed": False,
                                    "mode_overridden": True,
                                    "current_mode": self.system_state.get("mode", 17),
                                })
                            self.system_state["mode"] = val_int
                            self.system_state["canvas_active"] = (val_int == 29)
                            return with_req_id({
                                "status": "ok",
                                "executed": True,
                                "mode_overridden": False,
                                "mode": val_int,
                            })
                    elif cmd_lower in ("brightness", "b"):
                        val = parsed.get("val", parsed.get("brightness"))
                        if val is not None:
                            self.system_state["brightness"] = int(val)
                    elif cmd_lower in ("pixel", "canvas") and parsed.get("auto_mode"):
                        if not self.system_state.get("manual_override", False):
                            self.system_state["mode"] = 29
                            self.system_state["canvas_active"] = True
                    self.dispatched_commands.append(line)
                    return with_req_id({"status": "ok", "executed": True})
                else:
                    return with_req_id({"status": "error", "error": "unauthorized_command", "executed": False})

        # Plain text commands
        text_lower = line.strip().lower()
        if text_lower == "ping":
            return {"status": "ok", "pong": True, "version": self.version}
        elif text_lower in ("status", "get_status"):
            return {
                "status": "ok",
                "version": self.version,
                "board": "esp32s3_pro",
                **self.system_state,
            }
        elif text_lower == "version":
            return {"status": "ok", "version": self.version}
        elif text_lower == "release_input":
            self.system_state["held_keys"] = 0
            return {"status": "ok", "released": True}
        elif text_lower in ("reboot", "restart", "factory_reset", "pair"):
            return {"status": "error", "error": "unauthorized_command", "cmd": line}
        else:
            allowed = False
            if text_lower.startswith("f,"):
                allowed = True
            for prefix in ("mode ", "brightness ", "b ", "board_led ", "led ", "countdown ", "arcade "):
                if text_lower.startswith(prefix):
                    allowed = True
                    break
            if not allowed:
                allowed_exact = {
                    "pet", "kurisu", "stop_countdown", "stop_cd", "beep",
                    "snake", "tetris", "fire", "matrix", "spectrum"
                }
                if text_lower in allowed_exact:
                    allowed = True

            if allowed:
                self.dispatched_commands.append(line)
                return {"status": "ok", "executed": True, "cmd": line}
            else:
                return {"status": "error", "error": "unauthorized_command", "cmd": line}


class TestJetsonUartProtocol(unittest.TestCase):
    def setUp(self):
        self.parser = JetsonUartParser()

    def test_01_ping_with_string_and_numeric_req_id(self):
        r1 = self.parser.feed_bytes(b'{"cmd":"ping","req_id":"req_001"}\n')[0]
        self.assertEqual(r1["status"], "ok")
        self.assertTrue(r1["pong"])
        self.assertEqual(r1["req_id"], "req_001")
        self.assertEqual(r1["version"], "2.3.0")

        r2 = self.parser.feed_bytes(b'{"cmd":"ping","req_id":42}\n')[0]
        self.assertEqual(r2["req_id"], 42)

    def test_02_get_status_and_capabilities(self):
        status = self.parser.feed_bytes(b'{"cmd":"get_status","req_id":"st_01"}\n')[0]
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["board"], "esp32s3_pro")
        self.assertEqual(status["mode"], 17)
        self.assertIn("canvas_active", status)
        self.assertIn("held_keys", status)

        caps = self.parser.feed_bytes(b'{"cmd":"get_capabilities","req_id":"cap_01"}\n')[0]
        self.assertEqual(caps["status"], "ok")
        self.assertIn("pixel_canvas", caps["features"])
        self.assertIn("canvas_binary", caps["features"])
        self.assertIn("fingertip_tracker", caps["features"])
        self.assertEqual(caps["display"]["width"], 16)
        self.assertEqual(caps["display"]["height"], 16)
        self.assertEqual(caps["uart"]["baud"], 115200)

    def test_03_visual_tracking_commands(self):
        # track_cal calibration
        r1 = self.parser.feed_bytes(b'{"cmd":"track_cal","x0":0.1,"y0":0.1,"x1":0.9,"y1":0.9,"invert_x":true,"req_id":"tc"}\n')[0]
        self.assertEqual(r1["status"], "ok")
        self.assertTrue(r1["executed"])

        # track coordinates stream
        r2 = self.parser.feed_bytes(b'{"cmd":"track","x":0.45,"y":0.65,"visible":true,"conf":0.98,"req_id":"tr"}\n')[0]
        self.assertEqual(r2["status"], "ok")
        self.assertTrue(r2["executed"])

    def test_04_hand_pinch_and_depth(self):
        r = self.parser.feed_bytes(b'{"cmd":"hand","x":0.5,"y":0.5,"z":-0.2,"pinch":true,"visible":true,"req_id":"h1"}\n')[0]
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["executed"])

    def test_05_desk_pet_context_and_celebrate(self):
        r1 = self.parser.feed_bytes(b'{"cmd":"pet_context","hour":14,"gaze":0.2,"present":true,"tired":false,"req_id":"pc"}\n')[0]
        self.assertEqual(r1["status"], "ok")
        self.assertTrue(r1["executed"])

        r2 = self.parser.feed_bytes(b'{"cmd":"celebrate","req_id":"cel"}\n')[0]
        self.assertEqual(r2["status"], "ok")
        self.assertTrue(r2["executed"])

    def test_06_arcade_game_select_input_and_key_release(self):
        # Select Snake (#033)
        r_sel = self.parser.feed_bytes(b'{"cmd":"arcade","action":"select","game_id":33,"req_id":"a_sel"}\n')[0]
        self.assertEqual(r_sel["status"], "ok")
        self.assertTrue(r_sel["executed"])
        self.assertEqual(self.parser.system_state["arcade_game_id"], 33)

        # Input Direction: KEY_RIGHT (2)
        r_in = self.parser.feed_bytes(b'{"cmd":"arcade","action":"input","down":2,"pressed":2,"req_id":"a_in"}\n')[0]
        self.assertEqual(r_in["status"], "ok")
        self.assertEqual(self.parser.system_state["held_keys"], 2)

        # Query Arcade Status
        r_stat = self.parser.feed_bytes(b'{"cmd":"arcade","action":"status","req_id":"a_st"}\n')[0]
        self.assertEqual(r_stat["status"], "ok")
        self.assertTrue(r_stat["active"])
        self.assertEqual(r_stat["game_id"], 33)

        # Hand lost safety release
        r_rel = self.parser.feed_bytes(b'{"cmd":"release_input","req_id":"rel"}\n')[0]
        self.assertEqual(r_rel["status"], "ok")
        self.assertTrue(r_rel["released"])
        self.assertEqual(self.parser.system_state["held_keys"], 0)

    def test_07_session_arbitration(self):
        # Start vision session with fingertip tracker
        r_start = self.parser.feed_bytes(b'{"cmd":"session","action":"start","session_id":"sess_123","mode":"fingertip","req_id":"s_st"}\n')[0]
        self.assertEqual(r_start["status"], "ok")
        self.assertTrue(r_start["active"])
        self.assertEqual(self.parser.system_state["mode"], 26)
        self.assertEqual(self.parser.system_state["session_id"], "sess_123")

        # Stop session releases keys and clears session
        self.parser.system_state["held_keys"] = 4
        r_stop = self.parser.feed_bytes(b'{"cmd":"session","action":"stop","req_id":"s_sp"}\n')[0]
        self.assertEqual(r_stop["status"], "ok")
        self.assertFalse(r_stop["active"])
        self.assertEqual(self.parser.system_state["session_id"], "")
        self.assertEqual(self.parser.system_state["held_keys"], 0)

    def test_08_canvas_single_pixel(self):
        # Single pixel with auto_mode switch
        r = self.parser.feed_bytes(b'{"cmd":"pixel","x":7,"y":8,"r":255,"g":128,"b":0,"auto_mode":true,"req_id":"px"}\n')[0]
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["executed"])
        self.assertEqual(self.parser.system_state["mode"], 29)
        self.assertTrue(self.parser.system_state["canvas_active"])

    def test_09_canvas_chunked_json_with_crc(self):
        # Prepare 768 bytes test pattern: Chunk 0 (384 bytes), Chunk 1 (384 bytes)
        payload0 = bytes([i % 256 for i in range(384)])
        payload1 = bytes([(i + 128) % 256 for i in range(384)])
        crc0 = crc16_ccitt(payload0)
        crc1 = crc16_ccitt(payload1)

        chunk0_json = json.dumps({
            "cmd": "canvas_chunk",
            "frame_id": 10,
            "chunk_idx": 0,
            "total_chunks": 2,
            "offset": 0,
            "hex": payload0.hex(),
            "crc": crc0,
            "commit": False,
            "auto_mode": True,
            "req_id": "c0",
        }).encode("utf-8") + b"\n"

        r0 = self.parser.feed_bytes(chunk0_json)[0]
        self.assertEqual(r0["status"], "ok")
        self.assertEqual(r0["frame_id"], 10)
        self.assertFalse(r0["committed"])

        chunk1_json = json.dumps({
            "cmd": "canvas_chunk",
            "frame_id": 10,
            "chunk_idx": 1,
            "total_chunks": 2,
            "offset": 384,
            "hex": payload1.hex(),
            "crc": crc1,
            "commit": True,
            "auto_mode": True,
            "req_id": "c1",
        }).encode("utf-8") + b"\n"

        r1 = self.parser.feed_bytes(chunk1_json)[0]
        self.assertEqual(r1["status"], "ok")
        self.assertEqual(r1["frame_id"], 10)
        self.assertTrue(r1["committed"])
        self.assertEqual(r1["received_bytes"], 768)
        self.assertEqual(self.parser.canvas_buffer[0:384], payload0)
        self.assertEqual(self.parser.canvas_buffer[384:768], payload1)

    def test_10_canvas_chunked_json_crc_mismatch_rejected(self):
        payload = b"\x11\x22\x33\x44" * 10
        bad_crc = 0x1234
        chunk_json = json.dumps({
            "cmd": "canvas_chunk",
            "frame_id": 12,
            "offset": 0,
            "hex": payload.hex(),
            "crc": bad_crc,
            "req_id": "bad_crc",
        }).encode("utf-8") + b"\n"

        r = self.parser.feed_bytes(chunk_json)[0]
        self.assertEqual(r["status"], "error")
        self.assertEqual(r["error"], "crc_mismatch")

    def test_11_canvas_clear(self):
        r = self.parser.feed_bytes(b'{"cmd":"clear_canvas","r":0,"g":0,"b":0,"req_id":"clr"}\n')[0]
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["cleared"])

    def test_12_binary_canvas_full_frame(self):
        # 768 bytes RGB pattern (contains 0x0A and 0x0D bytes inside payload!)
        payload = bytes([i % 256 for i in range(768)])
        crc = crc16_ccitt(payload)
        # Header: magic(4), type(1), ver(1), seq(2), len(2), offset(2), flags(2), crc(2)
        header = struct.pack(
            "<4sBBHHHHH",
            MAGIC,
            BIN_FULL_FRAME,
            1,
            105,
            768,
            0,
            FLAG_AUTO_MODE | FLAG_COMMIT_NOW,
            crc,
        )
        packet = header + payload

        replies = self.parser.feed_bytes(packet)
        self.assertEqual(len(replies), 1)
        r = replies[0]
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["type"], "bin_frame")
        self.assertEqual(r["frame_id"], 105)
        self.assertTrue(r["committed"])
        self.assertEqual(self.parser.canvas_buffer, payload)
        self.assertEqual(self.parser.system_state["mode"], 29)

    def test_13_binary_canvas_crc_mismatch(self):
        payload = b"\xAA" * 768
        bad_crc = 0x9999
        header = struct.pack(
            "<4sBBHHHHH", MAGIC, BIN_FULL_FRAME, 1, 106, 768, 0, FLAG_COMMIT_NOW, bad_crc
        )
        replies = self.parser.feed_bytes(header + payload)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "error")
        self.assertEqual(replies[0]["error"], "crc_mismatch")

    def test_14_binary_interleaved_with_json_lines(self):
        # Send JSON line -> Binary Full Frame -> JSON line
        r1 = self.parser.feed_bytes(b'{"cmd":"ping","req_id":"p1"}\n')
        self.assertEqual(len(r1), 1)
        self.assertTrue(r1[0]["pong"])

        payload = bytes([0x55] * 768)
        crc = crc16_ccitt(payload)
        header = struct.pack("<4sBBHHHHH", MAGIC, BIN_FULL_FRAME, 1, 107, 768, 0, FLAG_COMMIT_NOW, crc)
        r2 = self.parser.feed_bytes(header + payload)
        self.assertEqual(len(r2), 1)
        self.assertTrue(r2[0]["committed"])

        r3 = self.parser.feed_bytes(b'{"cmd":"version","req_id":"v2"}\n')
        self.assertEqual(len(r3), 1)
        self.assertEqual(r3[0]["version"], "2.3.0")

    def test_15_strict_security_rejections(self):
        bad_commands = [
            b'{"cmd":"pair"}\n',
            b'{"cmd":"control_token"}\n',
            b'{"cmd":"reboot"}\n',
            b'{"cmd":"factory_reset"}\n',
            b'{"cmd":"reset_nvs"}\n',
            b'{"cmd":"erase_flash"}\n',
            b'{"cmd":"mic_export"}\n',
            b'reboot\n',
            b'pair\n',
        ]
        for cmd in bad_commands:
            r = self.parser.feed_bytes(cmd)
            self.assertEqual(len(r), 1, f"Failed on {cmd}")
            self.assertEqual(r[0]["status"], "error")
            self.assertEqual(r[0]["error"], "unauthorized_command")

    def test_16_frame_overflow_drop_and_recovery(self):
        oversized = b"X" * 1025 + b'mode 1\n{"cmd":"ping","req_id":"rec"}\n'
        replies = self.parser.feed_bytes(oversized)
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["status"], "error")
        self.assertEqual(replies[0]["error"], "frame_overflow")
        self.assertEqual(replies[1]["status"], "ok")
        self.assertEqual(replies[1]["req_id"], "rec")

    def test_17_canvas_chunk_buffer_overflow_defense(self):
        # 400 bytes hex (exceeds 384 chunk limit)
        oversized_hex = "aa" * 400
        cmd = json.dumps({
            "cmd": "canvas_chunk",
            "frame_id": 1,
            "chunk_idx": 0,
            "total_chunks": 2,
            "offset": 0,
            "hex": oversized_hex,
        }) + "\n"
        replies = self.parser.feed_bytes(cmd.encode("utf-8"))
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "error")
        self.assertEqual(replies[0]["error"], "chunk_bounds_overflow")

    def test_18_canvas_chunk_incomplete_premature_commit_rejection(self):
        # 192 bytes with commit: true (incomplete frame)
        partial_hex = "55" * 192
        cmd = json.dumps({
            "cmd": "canvas_chunk",
            "frame_id": 2,
            "chunk_idx": 0,
            "total_chunks": 4,
            "offset": 0,
            "hex": partial_hex,
            "commit": True,
        }) + "\n"
        replies = self.parser.feed_bytes(cmd.encode("utf-8"))
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "error")
        self.assertEqual(replies[0]["error"], "incomplete_frame_premature_commit")

    def test_19_cross_source_manual_override_arbitration(self):
        # Simulate mobile/PC user setting Mode 3 (manual override)
        self.parser.system_state["mode"] = 3
        self.parser.system_state["manual_override"] = True

        # Jetson sends full 768-byte frame in 2 chunks with auto_mode: true
        chunk1 = "11" * 384
        chunk2 = "22" * 384
        c1 = json.dumps({
            "cmd": "canvas_chunk", "frame_id": 10, "chunk_idx": 0, "total_chunks": 2,
            "offset": 0, "hex": chunk1, "commit": False, "auto_mode": True
        }) + "\n"
        c2 = json.dumps({
            "cmd": "canvas_chunk", "frame_id": 10, "chunk_idx": 1, "total_chunks": 2,
            "offset": 384, "hex": chunk2, "commit": True, "auto_mode": True
        }) + "\n"
        self.parser.feed_bytes(c1.encode())
        r2 = self.parser.feed_bytes(c2.encode())
        self.assertEqual(len(r2), 1)
        self.assertTrue(r2[0]["committed"])
        self.assertTrue(r2[0]["mode_overridden"])
        # Mode remains 3, not stolen to 29!
        self.assertEqual(self.parser.system_state["mode"], 3)

        # Clear override (user selects Jetson mode or Jetson session starts)
        self.parser.system_state["manual_override"] = False
        self.parser.feed_bytes(c1.encode())
        r4 = self.parser.feed_bytes(c2.encode())
        self.assertEqual(self.parser.system_state["mode"], 29)

    def test_20_binary_frame_ack_commit_verification(self):
        from protocol import pack_binary_frame, BIN_FULL_FRAME
        payload = bytes([100] * 768)
        pkt = pack_binary_frame(BIN_FULL_FRAME, frame_seq=99, payload=payload, offset=0, commit_now=True, auto_mode=True)
        replies = self.parser.feed_bytes(pkt)
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertEqual(replies[0]["type"], "bin_frame")
        self.assertEqual(replies[0]["frame_id"], 99)
        self.assertTrue(replies[0]["committed"])
        self.assertTrue(replies[0]["displayed"])

    def test_21_binary_frame_displayed_flag_and_overridden(self):
        from protocol import pack_binary_frame, BIN_FULL_FRAME
        payload = bytes([120] * 768)
        pkt = pack_binary_frame(BIN_FULL_FRAME, frame_seq=100, payload=payload, offset=0, commit_now=True, auto_mode=True)

        # 1. Under manual override: committed is True, but displayed is False
        self.parser.system_state["manual_override"] = True
        self.parser.system_state["mode"] = 5
        replies = self.parser.feed_bytes(pkt)
        self.assertEqual(len(replies), 1)
        self.assertTrue(replies[0]["committed"])
        self.assertFalse(replies[0]["displayed"])
        self.assertTrue(replies[0]["mode_overridden"])
        self.assertEqual(self.parser.system_state["mode"], 5)

        # 2. When override released: committed is True AND displayed is True
        self.parser.system_state["manual_override"] = False
        pkt2 = pack_binary_frame(BIN_FULL_FRAME, frame_seq=101, payload=payload, offset=0, commit_now=True, auto_mode=True)
        replies2 = self.parser.feed_bytes(pkt2)
        self.assertEqual(len(replies2), 1)
        self.assertTrue(replies2[0]["committed"])
        self.assertTrue(replies2[0]["displayed"])
        self.assertFalse(replies2[0]["mode_overridden"])
        self.assertEqual(self.parser.system_state["mode"], 29)

    def test_22_jetson_mode_command_does_not_set_manual_override(self):
        # Jetson sets mode 26 (fingertip)
        cmd = json.dumps({"cmd": "mode", "mode": 26}) + "\n"
        replies = self.parser.feed_bytes(cmd.encode())
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "ok")
        self.assertTrue(replies[0]["executed"])
        self.assertFalse(replies[0]["mode_overridden"])
        self.assertEqual(self.parser.system_state["mode"], 26)
        # Verify manual_override remains False!
        self.assertFalse(self.parser.system_state.get("manual_override", False))

        # Now simulate user manual override (Mode 1 - Rainbow Wave)
        self.parser.system_state["manual_override"] = True
        self.parser.system_state["mode"] = 1

        # Jetson tries to change mode to 27 (sandbox)
        cmd2 = json.dumps({"cmd": "mode", "mode": 27}) + "\n"
        replies2 = self.parser.feed_bytes(cmd2.encode())
        self.assertEqual(len(replies2), 1)
        self.assertFalse(replies2[0]["executed"])
        self.assertTrue(replies2[0]["mode_overridden"])
        # Mode remains 1! Jetson cannot steal display from user
        self.assertEqual(self.parser.system_state["mode"], 1)

    def test_23_session_expired_rejects_visual_data(self):
        # Configure session then mark inactive
        self.parser.system_state["session_id"] = "session_xyz"
        self.parser.system_state["session_active"] = False

        # Visual tracking command rejected
        cmd = json.dumps({"cmd": "track", "x": 0.5, "y": 0.5}) + "\n"
        replies = self.parser.feed_bytes(cmd.encode())
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["status"], "error")
        self.assertEqual(replies[0]["error"], "session_expired")

        # Canvas chunk rejected
        cmd2 = json.dumps({"cmd": "canvas_chunk", "frame_id": 1, "offset": 0, "hex": "11" * 100}) + "\n"
        replies2 = self.parser.feed_bytes(cmd2.encode())
        self.assertEqual(len(replies2), 1)
        self.assertEqual(replies2[0]["status"], "error")
        self.assertEqual(replies2[0]["error"], "session_expired")

    def test_24_streamer_is_displayed_and_is_overridden_properties(self):
        from canvas_stream import CanvasStreamer

        class MockTransport:
            def __init__(self):
                self.mock_reply = None
            def send_raw_with_ack(self, pkt, expected_frame_seq, timeout=1.0):
                return self.mock_reply

        mock_tr = MockTransport()
        streamer = CanvasStreamer(mock_tr)

        # Case A: Board replies committed=True, displayed=False, mode_overridden=True
        mock_tr.mock_reply = {"status": "ok", "committed": True, "displayed": False, "mode_overridden": True}
        colors = [(255, 0, 0)] * 256
        ok = streamer.send_binary_frame(colors, auto_mode=True, require_displayed=False)
        self.assertTrue(ok)
        self.assertTrue(streamer.is_committed)
        self.assertFalse(streamer.is_displayed)
        self.assertTrue(streamer.is_overridden)

        # With require_displayed=True, must return False!
        ok_disp = streamer.send_binary_frame(colors, auto_mode=True, require_displayed=True)
        self.assertFalse(ok_disp)

        # Case B: Board replies committed=True, displayed=True, mode_overridden=False
        mock_tr.mock_reply = {"status": "ok", "committed": True, "displayed": True, "mode_overridden": False}
        ok2 = streamer.send_binary_frame(colors, auto_mode=True, require_displayed=True)
        self.assertTrue(ok2)
        self.assertTrue(streamer.is_displayed)
        self.assertFalse(streamer.is_overridden)

    def test_25_session_stop_and_late_data_rejection(self):
        # 1. Start session
        cmd_start = json.dumps({"cmd": "session", "action": "start", "session_id": "sess_1", "mode": 29}) + "\n"
        r1 = self.parser.feed_bytes(cmd_start.encode())
        self.assertEqual(len(r1), 1)
        self.assertTrue(r1[0]["active"])
        self.assertEqual(self.parser.system_state["mode"], 29)

        # 2. Stop session
        cmd_stop = json.dumps({"cmd": "session", "action": "stop"}) + "\n"
        r2 = self.parser.feed_bytes(cmd_stop.encode())
        self.assertEqual(len(r2), 1)
        self.assertFalse(r2[0]["active"])
        self.assertEqual(r2[0]["session_state"], "stopped")
        # Mode 29 must revert cleanly to fallback mode 1
        self.assertEqual(self.parser.system_state["mode"], 1)

        # 3. Late tracking command after stop is rejected with session_stopped
        cmd_late_track = json.dumps({"cmd": "track", "x": 0.5, "y": 0.5}) + "\n"
        r3 = self.parser.feed_bytes(cmd_late_track.encode())
        self.assertEqual(len(r3), 1)
        self.assertEqual(r3[0]["status"], "error")
        self.assertEqual(r3[0]["error"], "session_stopped")

        # 4. Late binary frame after stop is rejected with session_stopped
        from protocol import pack_binary_frame, BIN_FULL_FRAME
        payload = bytes([128] * 768)
        pkt = pack_binary_frame(BIN_FULL_FRAME, frame_seq=999, payload=payload)
        r4 = self.parser.feed_bytes(pkt)
        self.assertEqual(len(r4), 1)
        self.assertEqual(r4[0]["status"], "error")
        self.assertEqual(r4[0]["error"], "session_stopped")
        self.assertFalse(r4[0]["committed"])
        self.assertFalse(r4[0]["displayed"])

        # 5. Late heartbeat cannot revive stopped session
        cmd_hb = json.dumps({"cmd": "session", "action": "heartbeat"}) + "\n"
        r5 = self.parser.feed_bytes(cmd_hb.encode())
        self.assertEqual(len(r5), 1)
        self.assertEqual(r5[0]["status"], "error")
        self.assertEqual(r5[0]["error"], "session_stopped")


if __name__ == "__main__":
    unittest.main()
