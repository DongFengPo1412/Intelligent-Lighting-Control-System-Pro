"""Jetson Nano - ESP32-S3 UART Protocol Definitions & Serialization.
Supports Protocol v2.3.1 with JSON Lines and High-Efficiency Binary Canvas Frames.
"""
import binascii
import json
import struct
from typing import Any, Dict, List, Optional, Tuple

MAGIC = b"\x55\xaa\x43\x46"  # 0x55, 0xAA, 'C', 'F' (Canvas Frame)
VERSION = "2.3.1"

# Binary Frame Types
BIN_FULL_FRAME = 0x01   # Full 768-byte frame payload
BIN_CHUNK_FRAME = 0x02  # Chunk payload (<= 384 bytes)
BIN_SINGLE_PIXEL = 0x03 # 5 bytes payload: [x, y, r, g, b]
BIN_CLEAR = 0x04        # Clear canvas [r, g, b]

# Flags bitmask
FLAG_NONE = 0
FLAG_COMMIT_NOW = 1 << 0
FLAG_AUTO_MODE = 1 << 1
FLAG_SKIP_CRC = 1 << 2

# Arcade Keys bitmask
KEY_LEFT = 1 << 0
KEY_RIGHT = 1 << 1
KEY_UP = 1 << 2
KEY_DOWN = 1 << 3
KEY_A = 1 << 4
KEY_B = 1 << 5
KEY_START = 1 << 6
KEY_SELECT = 1 << 7

KEY_MAP = {
    "left": KEY_LEFT,
    "right": KEY_RIGHT,
    "up": KEY_UP,
    "down": KEY_DOWN,
    "a": KEY_A,
    "b": KEY_B,
    "start": KEY_START,
    "select": KEY_SELECT,
}


def crc16_ccitt(data: bytes) -> int:
    """Standard CRC16-CCITT (poly 0x1021, init 0xFFFF).
    Uses Python's standard C-optimized binascii module.
    """
    return binascii.crc_hqx(data, 0xFFFF)


def pack_binary_frame(
    frame_type: int,
    frame_seq: int,
    payload: bytes,
    offset: int = 0,
    commit_now: bool = True,
    auto_mode: bool = True,
) -> bytes:
    """Packs a 16-byte BinaryHeader + payload into a streamable byte packet."""
    flags = 0
    if commit_now:
        flags |= FLAG_COMMIT_NOW
    if auto_mode:
        flags |= FLAG_AUTO_MODE

    payload_crc = crc16_ccitt(payload) if payload else 0
    payload_len = len(payload)

    header = struct.pack(
        "<4sBBHHHHH",
        MAGIC,
        frame_type,
        1,  # Version 1
        frame_seq & 0xFFFF,
        payload_len & 0xFFFF,
        offset & 0xFFFF,
        flags & 0xFFFF,
        payload_crc & 0xFFFF,
    )
    return header + payload


class CommandBuilder:
    """Helper to build validated JSON command strings for ESP32."""

    @staticmethod
    def ping(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "ping"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def get_status(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "get_status"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def get_capabilities(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "get_capabilities"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def mode(mode_val: int, req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "mode", "val": int(mode_val)}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def brightness(val: int, req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "brightness", "val": max(0, min(60, int(val)))}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def board_led(color: str = "green", req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "board_led", "val": str(color)}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def session(
        action: str = "start",
        session_id: str = "jetson_sess",
        mode_name: Optional[str] = None,
        initial_seq: int = 0,
        take_control: bool = False,
        req_id: Optional[str] = None,
    ) -> str:
        cmd = {"cmd": "session", "action": action, "session_id": session_id}
        if action in ("start", "resume"):
            cmd["initial_seq"] = int(initial_seq)
            if take_control:
                cmd["take_control"] = True
            if mode_name is not None:
                cmd["mode"] = mode_name
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def track_cal(
        x0: float = 0.0,
        y0: float = 0.0,
        x1: float = 1.0,
        y1: float = 1.0,
        invert_x: bool = False,
        invert_y: bool = False,
        req_id: Optional[str] = None,
    ) -> str:
        cmd = {
            "cmd": "track_cal",
            "x0": max(0.0, min(1.0, float(x0))),
            "y0": max(0.0, min(1.0, float(y0))),
            "x1": max(0.0, min(1.0, float(x1))),
            "y1": max(0.0, min(1.0, float(y1))),
            "invert_x": bool(invert_x),
            "invert_y": bool(invert_y),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def track(
        x: float,
        y: float,
        visible: bool = True,
        conf: float = 1.0,
        req_id: Optional[str] = None,
    ) -> str:
        cmd = {
            "cmd": "track",
            "x": max(0.0, min(1.0, float(x))),
            "y": max(0.0, min(1.0, float(y))),
            "visible": bool(visible),
            "conf": max(0.0, min(1.0, float(conf))),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def hand(
        x: float,
        y: float,
        z: float = 0.0,
        pinch: bool = False,
        visible: bool = True,
        req_id: Optional[str] = None,
    ) -> str:
        cmd = {
            "cmd": "hand",
            "x": max(0.0, min(1.0, float(x))),
            "y": max(0.0, min(1.0, float(y))),
            "z": max(-2.0, min(2.0, float(z))),
            "pinch": bool(pinch),
            "visible": bool(visible),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def pet_context(
        hour: int,
        gaze: float = 0.0,
        present: bool = True,
        tired: bool = False,
        req_id: Optional[str] = None,
    ) -> str:
        cmd = {
            "cmd": "pet_context",
            "hour": max(0, min(23, int(hour))),
            "gaze": max(-1.0, min(1.0, float(gaze))),
            "present": bool(present),
            "tired": bool(tired),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def celebrate(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "celebrate"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def arcade_select(game_id: int, req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "arcade", "action": "select", "game_id": int(game_id)}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def arcade_start(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "arcade", "action": "start"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def arcade_input(down: int, pressed: int, req_id: Optional[str] = None) -> str:
        cmd = {
            "cmd": "arcade",
            "action": "input",
            "down": int(down) & 0xFF,
            "pressed": int(pressed) & 0xFF,
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def arcade_status(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "arcade", "action": "status"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def release_input(req_id: Optional[str] = None) -> str:
        cmd = {"cmd": "release_input"}
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def pixel(
        x: int,
        y: int,
        r: int,
        g: int,
        b: int,
        auto_mode: bool = True,
        req_id: Optional[str] = None,
    ) -> str:
        cmd = {
            "cmd": "pixel",
            "x": max(0, min(15, int(x))),
            "y": max(0, min(15, int(y))),
            "r": max(0, min(255, int(r))),
            "g": max(0, min(255, int(g))),
            "b": max(0, min(255, int(b))),
            "auto_mode": bool(auto_mode),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def canvas_chunk(
        frame_id: int,
        chunk_idx: int,
        total_chunks: int,
        offset: int,
        raw_bytes: bytes,
        commit: bool = False,
        auto_mode: bool = True,
        req_id: Optional[str] = None,
    ) -> str:
        crc = crc16_ccitt(raw_bytes)
        cmd = {
            "cmd": "canvas_chunk",
            "frame_id": int(frame_id),
            "chunk_idx": int(chunk_idx),
            "total_chunks": int(total_chunks),
            "offset": int(offset),
            "hex": raw_bytes.hex(),
            "crc": crc,
            "commit": bool(commit),
            "auto_mode": bool(auto_mode),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

    @staticmethod
    def clear_canvas(
        r: int = 0, g: int = 0, b: int = 0, auto_mode: bool = False, req_id: Optional[str] = None
    ) -> str:
        cmd = {
            "cmd": "clear_canvas",
            "r": max(0, min(255, int(r))),
            "g": max(0, min(255, int(g))),
            "b": max(0, min(255, int(b))),
            "auto_mode": bool(auto_mode),
        }
        if req_id is not None:
            cmd["req_id"] = req_id
        return json.dumps(cmd)

