"""Jetson Nano Serial UART Transport Layer.
Handles robust bidirectional communication, timeout re-sync, req_id matching,
and binary frame delivery over /dev/ttyTHS1 (or configurable port).
"""
import json
import logging
import time
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("JetsonUart")

try:
    import serial
except ImportError:
    serial = None


class JetsonUartTransport:
    """Manages serial connection and bidirectional packet flow with ESP32-S3."""

    def __init__(
        self,
        port: str = "/dev/ttyTHS1",
        baudrate: int = 115200,
        timeout: float = 1.0,
        simulate: bool = False,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.simulate = simulate

        self.ser = None
        self.is_connected = False
        self._lock = threading.Lock()
        self._running = False
        self._reader_thread = None

        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._request_events: Dict[str, threading.Event] = {}
        self._req_counter = 0

        self.on_frame_received: Optional[Callable[[Dict[str, Any]], None]] = None

    def connect(self) -> bool:
        """Opens the serial port."""
        if self.simulate:
            logger.info("[UART] Running in SIMULATION mode (no physical serial port).")
            self.is_connected = True
            return True

        if serial is None:
            logger.error("[UART] pyserial is not installed! Run: pip3 install pyserial")
            return False

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            self.is_connected = True
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True, name="JetsonUartReader"
            )
            self._reader_thread.start()
            logger.info(f"[UART] Connected to {self.port} at {self.baudrate} baud.")
            return True
        except Exception as e:
            logger.error(f"[UART] Failed to open {self.port}: {e}")
            self.is_connected = False
            return False

    def close(self):
        """Closes the serial connection."""
        self._running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.is_connected = False
        with self._lock:
            for ev in self._request_events.values():
                ev.set()
            self._request_events.clear()
            self._pending_requests.clear()
        logger.info("[UART] Connection closed.")

    def _next_req_id(self) -> str:
        with self._lock:
            self._req_counter += 1
            return f"j_{int(time.time()*1000)%1000000}_{self._req_counter}"

    def send_line(self, line: str, wait_reply: bool = False, timeout: float = 1.5) -> Optional[Dict[str, Any]]:
        """Sends a JSON line (automatically appends \n). If wait_reply is True, blocks until reply matches req_id."""
        if not self.is_connected:
            return None

        line = line.strip()
        req_id = None
        ev = None

        if wait_reply:
            try:
                data = json.loads(line)
                req_id = data.get("req_id")
                if not req_id:
                    req_id = self._next_req_id()
                    data["req_id"] = req_id
                    line = json.dumps(data)
                ev = threading.Event()
                with self._lock:
                    self._request_events[req_id] = ev
            except Exception:
                pass

        if self.simulate:
            logger.debug(f"[SIM TX] {line}")
            if wait_reply and req_id:
                return {"status": "ok", "simulated": True, "req_id": req_id}
            return {"status": "ok"}

        raw = (line + "\n").encode("utf-8")
        try:
            with self._lock:
                self.ser.write(raw)
                self.ser.flush()
        except Exception as e:
            logger.error(f"[UART] TX error: {e}")
            self.is_connected = False
            return None

        if wait_reply and ev:
            signaled = ev.wait(timeout)
            with self._lock:
                self._request_events.pop(req_id, None)
                reply = self._pending_requests.pop(req_id, None)
            if not signaled or reply is None:
                logger.warning(f"[UART] Request {req_id} timed out after {timeout}s")
                return None
            return reply

        return {"status": "ok"}

    def send_raw(self, raw_bytes: bytes) -> bool:
        """Sends raw bytes (e.g. Binary Canvas Frame) directly without newline."""
        if not self.is_connected or not raw_bytes:
            return False

        if self.simulate:
            logger.debug(f"[SIM RAW TX] {len(raw_bytes)} bytes")
            return True

        try:
            with self._lock:
                self.ser.write(raw_bytes)
                self.ser.flush()
            return True
        except Exception as e:
            logger.error(f"[UART] Raw TX error: {e}")
            self.is_connected = False
            return False

    def send_raw_with_ack(
        self, raw_bytes: bytes, expected_frame_seq: int, timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Sends raw binary frame and blocks until ESP32 acknowledges matching frame_id and commit status."""
        if not self.is_connected or not raw_bytes:
            return None

        key = f"bin_{expected_frame_seq}"
        ev = threading.Event()
        with self._lock:
            self._request_events[key] = ev

        if self.simulate:
            logger.debug(f"[SIM RAW TX+ACK] {len(raw_bytes)} bytes, seq={expected_frame_seq}")
            with self._lock:
                self._request_events.pop(key, None)
            return {
                "status": "ok",
                "type": "bin_frame",
                "frame_id": expected_frame_seq,
                "committed": True,
                "received_bytes": max(0, len(raw_bytes) - 16),
                "simulated": True,
            }

        try:
            with self._lock:
                self.ser.write(raw_bytes)
                self.ser.flush()
        except Exception as e:
            logger.error(f"[UART] Raw TX error: {e}")
            with self._lock:
                self._request_events.pop(key, None)
            self.is_connected = False
            return None

        signaled = ev.wait(timeout)
        with self._lock:
            self._request_events.pop(key, None)
            reply = self._pending_requests.pop(key, None)

        if not signaled or reply is None:
            logger.warning(
                f"[UART] Binary frame {expected_frame_seq} timed out waiting for ACK after {timeout}s"
            )
            return None

        return reply

    def _reader_loop(self):
        """Background thread reading lines from ESP32."""
        buffer = bytearray()
        while self._running and self.ser and self.ser.is_open:
            try:
                chunk = self.ser.read(self.ser.in_waiting or 1)
                if not chunk:
                    continue
                for b in chunk:
                    if b in (ord("\n"), ord("\r")):
                        if len(buffer) > 0:
                            line_str = buffer.decode("utf-8", errors="replace").strip()
                            buffer.clear()
                            if line_str:
                                self._dispatch_line(line_str)
                    else:
                        buffer.append(b)
                        if len(buffer) > 4096:
                            buffer.clear()
            except Exception as e:
                if self._running:
                    logger.warning(f"[UART] RX exception: {e}")
                break

    def _dispatch_line(self, line: str):
        logger.debug(f"[UART RX] {line}")
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                req_id = parsed.get("req_id")
                if req_id and req_id in self._request_events:
                    with self._lock:
                        self._pending_requests[req_id] = parsed
                        ev = self._request_events.get(req_id)
                        if ev:
                            ev.set()

                # Match binary frame ACKs: type == "bin_frame" and "frame_id"
                if parsed.get("type") == "bin_frame" and "frame_id" in parsed:
                    bin_key = f"bin_{parsed.get('frame_id')}"
                    if bin_key in self._request_events:
                        with self._lock:
                            self._pending_requests[bin_key] = parsed
                            ev = self._request_events.get(bin_key)
                            if ev:
                                ev.set()

                if self.on_frame_received:
                    self.on_frame_received(parsed)
        except Exception:
            pass


# Friendly alias for handoff docs and concise scripts
UartTransport = JetsonUartTransport


