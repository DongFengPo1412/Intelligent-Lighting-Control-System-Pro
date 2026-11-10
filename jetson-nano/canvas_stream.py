"""Jetson Nano 16x16 Universal Pixel Canvas Streamer & Procedural Animation Generators.
Supports single pixel, 2-chunk JSON with CRC, and 1-shot high-speed binary frame delivery.
"""
import logging
import math
import random
import threading
import time
from typing import List, Tuple, Union

from protocol import BIN_FULL_FRAME, CommandBuilder, pack_binary_frame

logger = logging.getLogger("CanvasStreamer")

ColorRGB = Tuple[int, int, int]


class CanvasStreamer:
    """Streams 16x16 RGB frames or single pixels to ESP32."""

    def __init__(self, transport):
        self.transport = transport
        self.frame_seq = 0
        self.last_reply = None
        self.last_committed = False
        self.last_displayed = False
        self.last_overridden = False
        self.session_active = False
        self.session_id = ""
        self._heartbeat_thread = None
        self._stop_heartbeat = threading.Event()
        self.heartbeat_alive = False
        self.last_heartbeat_time = 0.0

    @property
    def is_displayed(self) -> bool:
        """Returns True if the last frame was actually displayed on the LED matrix (not overridden)."""
        return self.last_displayed

    @property
    def is_committed(self) -> bool:
        """Returns True if the last frame was received and assembled into canvas memory."""
        return self.last_committed

    @property
    def is_overridden(self) -> bool:
        """Returns True if user manual control suppressed the canvas frame from becoming active on display."""
        return self.last_overridden

    def reset_sequence(self, initial_seq: int = 0):
        """Resets the client-side frame sequence number."""
        self.frame_seq = int(initial_seq)

    def start(
        self,
        session_id: str = "canvas_stream",
        initial_seq: int = 0,
        mode_name: str = None,
        take_control: bool = False,
        heartbeat_interval: float = 3.0,
        timeout: float = 2.0,
    ) -> bool:
        """Starts a vision canvas streaming session with the ESP32.

        Sends session_start command, verifies ESP32 ACK ('active': True),
        resets sequence number, and spawns background heartbeat thread.
        """
        if hasattr(self.transport, "is_connected") and not self.transport.is_connected:
            if hasattr(self.transport, "connect"):
                self.transport.connect()

        self.reset_sequence(initial_seq)
        cmd = CommandBuilder.session_start(
            session_id=session_id,
            initial_seq=initial_seq,
            mode_name=mode_name,
            take_control=take_control,
        )
        reply = self.transport.send_line(cmd, wait_reply=True, timeout=timeout)
        if not reply or reply.get("status") != "ok" or not reply.get("active"):
            logger.error(f"[CanvasStreamer] Session start failed. Reply: {reply}")
            self.session_active = False
            return False

        self.session_id = session_id
        self.session_active = True
        self.heartbeat_alive = True
        self.last_heartbeat_time = time.time()

        # Stop any existing heartbeat thread
        self._stop_heartbeat.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)

        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            args=(heartbeat_interval, timeout),
            daemon=True,
            name="CanvasHeartbeatWorker",
        )
        self._heartbeat_thread.start()
        logger.info(f"[CanvasStreamer] Session '{session_id}' started (seq={initial_seq}). Heartbeat active.")
        return True

    def _heartbeat_worker(self, interval: float, timeout: float):
        while not self._stop_heartbeat.wait(interval):
            if not self.session_active:
                break
            try:
                cmd = CommandBuilder.session_ping()
                reply = self.transport.send_line(cmd, wait_reply=True, timeout=timeout)
                if reply and reply.get("status") == "ok" and reply.get("active", True):
                    self.heartbeat_alive = True
                    self.last_heartbeat_time = time.time()
                else:
                    self.heartbeat_alive = False
                    logger.warning(f"[CanvasStreamer] Heartbeat ping unacknowledged: {reply}")
            except Exception as e:
                self.heartbeat_alive = False
                logger.warning(f"[CanvasStreamer] Heartbeat ping exception: {e}")

    def stop(self, timeout: float = 1.0) -> bool:
        """Stops the session and terminates heartbeat thread."""
        self._stop_heartbeat.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)
        self._heartbeat_thread = None

        self.session_active = False
        cmd = CommandBuilder.session_stop()
        reply = self.transport.send_line(cmd, wait_reply=True, timeout=timeout)
        logger.info("[CanvasStreamer] Session stopped.")
        return reply is not None and reply.get("status") == "ok"

    def send_pixel(self, x: int, y: int, r: int, g: int, b: int, auto_mode: bool = True) -> bool:
        cmd = CommandBuilder.pixel(x, y, r, g, b, auto_mode=auto_mode)
        reply = self.transport.send_line(cmd, wait_reply=True)
        return reply is not None and reply.get("status") == "ok"

    def send_full_frame(
        self,
        frame_data: Union[bytes, bytearray, List[ColorRGB], List[int]],
        auto_mode: bool = True,
        timeout: float = 1.0,
        require_displayed: bool = False,
    ) -> bool:
        """Sends full 16x16 frame (768 bytes) in a single high-speed binary packet and verifies ESP32 commit ACK.

        Supports:
            - bytes or bytearray of length 768
            - list of 256 (r, g, b) tuples
            - list of 768 integers
        """
        if isinstance(frame_data, (bytes, bytearray)):
            payload = bytes(frame_data)
            if len(payload) != 768:
                raise ValueError(f"Expected 768 bytes, got {len(payload)}")
        elif isinstance(frame_data, (list, tuple)):
            if len(frame_data) == 256:
                raw = bytearray(768)
                for i, (r, g, b) in enumerate(frame_data):
                    idx = i * 3
                    raw[idx] = max(0, min(255, int(r)))
                    raw[idx + 1] = max(0, min(255, int(g)))
                    raw[idx + 2] = max(0, min(255, int(b)))
                payload = bytes(raw)
            elif len(frame_data) == 768:
                payload = bytes([max(0, min(255, int(v))) for v in frame_data])
            else:
                raise ValueError(f"Expected 256 RGB tuples or 768 bytes, got length {len(frame_data)}")
        else:
            raise TypeError(f"Unsupported frame data type: {type(frame_data)}")

        self.frame_seq = (self.frame_seq + 1) & 0xFFFF
        packet = pack_binary_frame(
            frame_type=BIN_FULL_FRAME,
            frame_seq=self.frame_seq,
            payload=payload,
            offset=0,
            commit_now=True,
            auto_mode=auto_mode,
        )
        reply = self.transport.send_raw_with_ack(
            packet, expected_frame_seq=self.frame_seq, timeout=timeout
        )
        if not reply:
            self.last_reply = None
            self.last_committed = False
            self.last_displayed = False
            self.last_overridden = False
            return False

        self.last_reply = reply
        self.last_committed = bool(reply.get("status") == "ok" and reply.get("committed", False) is True)
        self.last_overridden = bool(reply.get("mode_overridden", False))
        if "displayed" in reply:
            self.last_displayed = bool(reply.get("displayed"))
        else:
            self.last_displayed = bool(self.last_committed and not self.last_overridden)

        if require_displayed:
            return self.last_displayed
        return self.last_committed

    def send_binary_frame(
        self, colors: List[ColorRGB], auto_mode: bool = True, timeout: float = 1.0, require_displayed: bool = False
    ) -> bool:
        """Legacy helper: sends 256 RGB tuples."""
        return self.send_full_frame(colors, auto_mode=auto_mode, timeout=timeout, require_displayed=require_displayed)

    def send_chunked_frame(
        self, colors: List[ColorRGB], chunk_count: int = 2, auto_mode: bool = True, require_displayed: bool = False
    ) -> bool:
        """Sends full 16x16 frame as chunked JSON lines (portable text protocol)."""
        if len(colors) != 256:
            raise ValueError(f"Expected exactly 256 pixels, got {len(colors)}")

        self.frame_seq = (self.frame_seq + 1) & 0xFFFF
        raw_payload = bytearray(768)
        for i, (r, g, b) in enumerate(colors):
            idx = i * 3
            raw_payload[idx] = max(0, min(255, int(r)))
            raw_payload[idx + 1] = max(0, min(255, int(g)))
            raw_payload[idx + 2] = max(0, min(255, int(b)))

        chunk_size = 768 // chunk_count
        all_ok = True
        last_reply = None

        for chunk_idx in range(chunk_count):
            offset = chunk_idx * chunk_size
            chunk_bytes = raw_payload[offset : offset + chunk_size]
            commit = (chunk_idx == chunk_count - 1)

            cmd = CommandBuilder.canvas_chunk(
                frame_id=self.frame_seq,
                chunk_idx=chunk_idx,
                total_chunks=chunk_count,
                offset=offset,
                raw_bytes=bytes(chunk_bytes),
                commit=commit,
                auto_mode=auto_mode,
            )
            reply = self.transport.send_line(cmd, wait_reply=True)
            last_reply = reply
            if not reply or reply.get("status") != "ok":
                all_ok = False
            if commit and (not reply or not reply.get("committed")):
                all_ok = False

        self.last_reply = last_reply
        if last_reply:
            self.last_committed = (all_ok and last_reply.get("committed", False) is True)
            self.last_overridden = bool(last_reply.get("mode_overridden", False))
            self.last_displayed = bool(last_reply.get("displayed", self.last_committed and not self.last_overridden))
        else:
            self.last_committed = False
            self.last_overridden = False
            self.last_displayed = False

        if require_displayed:
            return all_ok and self.last_displayed
        return all_ok and self.last_committed

    def clear(self, r: int = 0, g: int = 0, b: int = 0, auto_mode: bool = False) -> bool:
        cmd = CommandBuilder.clear_canvas(r, g, b, auto_mode=auto_mode)
        reply = self.transport.send_line(cmd, wait_reply=True)
        return reply is not None and reply.get("status") == "ok"


# ============================================================================
# Procedural 16x16 Animation Generators
# ============================================================================

def generate_color_wave(t: float) -> List[ColorRGB]:
    """Generates an evolving 16x16 smooth chromatic wave."""
    pixels = []
    for y in range(16):
        for x in range(16):
            r = int(127.5 + 127.5 * math.sin(x * 0.4 + t * 2.0))
            g = int(127.5 + 127.5 * math.sin(y * 0.4 + t * 2.5 + 2.0))
            b = int(127.5 + 127.5 * math.sin((x + y) * 0.3 + t * 1.8 + 4.0))
            pixels.append((r, g, b))
    return pixels


def generate_bouncing_ball(t: float) -> List[ColorRGB]:
    """Generates a bouncing illuminated orb with glowing radial decay."""
    cx = 7.5 + 6.0 * math.sin(t * 2.5)
    cy = 7.5 + 6.0 * math.cos(t * 3.1)
    pixels = []
    for y in range(16):
        for x in range(16):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            intensity = max(0.0, 1.0 - dist / 4.0)
            r = int(255 * intensity)
            g = int(140 * intensity * 0.8)
            b = int(220 * intensity)
            pixels.append((r, g, b))
    return pixels


class MatrixRainAnimation:
    """Classic Green Cyber Matrix digital rain drop simulation."""

    def __init__(self):
        self.drops = [random.randint(-16, 0) for _ in range(16)]

    def step(self) -> List[ColorRGB]:
        pixels = [(0, 0, 0)] * 256
        for x in range(16):
            self.drops[x] += 1
            if self.drops[x] >= 16 + 8:
                self.drops[x] = random.randint(-8, 0)

            head_y = self.drops[x]
            for trail in range(8):
                y = head_y - trail
                if 0 <= y < 16:
                    idx = y * 16 + x
                    if trail == 0:
                        pixels[idx] = (180, 255, 200)  # Bright tip
                    else:
                        g_val = max(10, 255 - trail * 32)
                        pixels[idx] = (0, g_val, 0)
        return pixels


class FireSimulation:
    """16x16 Heat convection pixel fire simulation."""

    def __init__(self):
        self.heat = [0.0] * 256

    def step(self) -> List[ColorRGB]:
        # Inject heat at bottom row
        for x in range(16):
            self.heat[15 * 16 + x] = random.uniform(0.7, 1.0)

        # Propagate upwards with diffusion
        for y in range(15):
            for x in range(16):
                idx = y * 16 + x
                below = (y + 1) * 16 + x
                left = (y + 1) * 16 + max(0, x - 1)
                right = (y + 1) * 16 + min(15, x + 1)
                avg = (self.heat[below] * 2 + self.heat[left] + self.heat[right]) / 4.1
                self.heat[idx] = max(0.0, avg - random.uniform(0.02, 0.05))

        # Color map: Black -> Red -> Orange -> Yellow -> White
        pixels = []
        for val in self.heat:
            if val < 0.3:
                r = int((val / 0.3) * 255)
                pixels.append((r, 0, 0))
            elif val < 0.7:
                g = int(((val - 0.3) / 0.4) * 220)
                pixels.append((255, g, 0))
            else:
                b = int(((val - 0.7) / 0.3) * 255)
                pixels.append((255, 220, b))
        return pixels

