"""Jetson Nano 16x16 Universal Pixel Canvas Streamer & Procedural Animation Generators.
Supports single pixel, 2-chunk JSON with CRC, and 1-shot high-speed binary frame delivery.
"""
import math
import random
import time
from typing import List, Tuple
from protocol import BIN_FULL_FRAME, CommandBuilder, pack_binary_frame

ColorRGB = Tuple[int, int, int]


class CanvasStreamer:
    """Streams 16x16 RGB frames or single pixels to ESP32."""

    def __init__(self, transport):
        self.transport = transport
        self.frame_seq = 0

    def send_pixel(self, x: int, y: int, r: int, g: int, b: int, auto_mode: bool = True) -> bool:
        cmd = CommandBuilder.pixel(x, y, r, g, b, auto_mode=auto_mode)
        reply = self.transport.send_line(cmd, wait_reply=True)
        return reply is not None and reply.get("status") == "ok"

    def send_binary_frame(self, colors: List[ColorRGB], auto_mode: bool = True) -> bool:
        """Sends full 16x16 frame (768 bytes) in a single high-speed binary packet."""
        if len(colors) != 256:
            raise ValueError(f"Expected exactly 256 pixels, got {len(colors)}")

        self.frame_seq = (self.frame_seq + 1) & 0xFFFF
        raw_payload = bytearray(768)
        for i, (r, g, b) in enumerate(colors):
            idx = i * 3
            raw_payload[idx] = max(0, min(255, int(r)))
            raw_payload[idx + 1] = max(0, min(255, int(g)))
            raw_payload[idx + 2] = max(0, min(255, int(b)))

        packet = pack_binary_frame(
            frame_type=BIN_FULL_FRAME,
            frame_seq=self.frame_seq,
            payload=bytes(raw_payload),
            offset=0,
            commit_now=True,
            auto_mode=auto_mode,
        )
        return self.transport.send_raw(packet)

    def send_chunked_frame(
        self, colors: List[ColorRGB], chunk_count: int = 2, auto_mode: bool = True
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
            if not reply or reply.get("status") != "ok":
                all_ok = False

        return all_ok

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
