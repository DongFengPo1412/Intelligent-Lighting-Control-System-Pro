"""Explicit controller substitute. Never imports/opens a serial or UDP device."""

import json
import math
import os
import re
import threading
import time
from pathlib import Path
from light_controller import LightController
from pro_control import DIRECT_MODES


class SimulatedController(LightController):
    def __init__(self):
        self.port = "SIMULATION"
        self.is_connected = False
        self.ser = None
        self.mode = 17
        self.brightness = 20
        self.volume = 70
        self._mic_enabled = False
        self._sim_lock = threading.RLock()
        self._timer = None
        self._frame_id = 0
        self._pixels = "000000" * 256
        self.last_audio_error = None
        self.stats = dict(
            audio_rx=0, audio_played=0, audio_dropped=0, audio_errors=0, audio_stack_free=0
        )
        self.last_result = {}
        self.on_mic_data = None
        self._network_audio = None
        self.audio_transport = "simulation"
        self.playback_cancel = threading.Event()
        self.renderer = None
        self.gamma = False
        header = (
            Path(__file__).parents[1] / "firmware-s3/main/display/srgb_transfer.h"
        ).read_text()
        values = re.search(r"SRGB_TO_LINEAR\[256\] = \{(.*?)\};", header, re.S).group(1)
        self.linear = tuple(map(int, re.findall(r"\d+", values)))
        if os.environ.get("KURISU_RENDERER_WASM"):
            from offline_renderer import OfflineRenderer

            self.renderer = OfflineRenderer(os.environ["KURISU_RENDERER_WASM"])

    @property
    def control_connected(self):
        return True

    def wait_for_control(self, timeout=8):
        return True

    def command_result(self, payload):
        with self._sim_lock:
            self.send_json(payload)
            return dict(self.last_result)

    def send_raw(self, line):
        aliases = {
            "fire": 23,
            "matrix": 24,
            "rainbow": 4,
            "aurora": 5,
            "meteor": 6,
            "stars": 7,
            "ripple": 10,
            "cycle": 8,
            "rain": 9,
            "smile": 11,
            "cry": 12,
            "neutral": 13,
            "dynamic": 14,
            "kurisu": 17,
            "off": 0,
        }
        try:
            if line in aliases:
                cmd = {"cmd": "mode", "val": aliases[line]}
            elif line.startswith("mode "):
                cmd = {"cmd": "mode", "val": int(line[5:])}
            elif line.startswith("b "):
                cmd = {"cmd": "brightness", "val": int(line[2:])}
            elif line.startswith("f,"):
                parts = [int(v) for v in line.split(",")[1:]]
                if (
                    len(parts) != 17
                    or parts[0] not in (0, 1)
                    or any(not 0 <= v <= 15 for v in parts[1:])
                ):
                    raise ValueError("Invalid bands")
                cmd = {"cmd": "bands", "beat": parts[0], "bands": parts[1:]}
            else:
                cmd = json.loads(line)
            with self._sim_lock:
                name = cmd.get("cmd")
                ok = True
                if name == "mode":
                    n = cmd.get("val")
                    ok = type(n) is int and n in DIRECT_MODES
                    if ok:
                        self.mode = n
                        self._timer = None
                elif name == "brightness":
                    n = cmd.get("val")
                    ok = type(n) is int and 0 <= n <= 60
                    if ok:
                        self.brightness = n
                elif name == "volume":
                    n = cmd.get("val")
                    ok = type(n) is int and 0 <= n <= 100
                    if ok:
                        self.volume = n
                elif name == "mic":
                    self._mic_enabled = bool(cmd.get("enable"))
                elif name == "countdown":
                    n = cmd.get("seconds")
                    ok = type(n) is int and 1 <= n <= 86400
                    if ok:
                        self.mode = 25
                        self._timer = (time.monotonic(), n)
                elif name == "stop_countdown":
                    self._timer = None
                    self.mode = 0
                elif name == "gamma":
                    ok = type(cmd.get("enable")) is bool
                    if ok:
                        self.gamma = cmd["enable"]
                elif name == "canvas":
                    value = cmd.get("hex", "")
                    ok = bool(re.fullmatch("[0-9a-fA-F]{1536}", value))
                    if ok:
                        self._pixels = value.lower()
                elif name not in (
                    "status",
                    "frame",
                    "beep",
                    "board_led",
                    "track",
                    "track_cal",
                    "hand",
                    "pet_context",
                    "mir",
                    "difficulty",
                    "performance",
                    "game",
                    "gamma",
                    "celebrate",
                    "bands",
                ):
                    ok = False
                if ok and self.renderer and name not in ("status", "frame", "countdown"):
                    command = dict(cmd)
                    if name == "game":
                        command["cmd"] = cmd["name"]
                    self.renderer.call(command=command)
                    if name == "mode":
                        self.renderer.call(mode=self.mode)
                self.last_result = self.status()
                self.last_result["status"] = "ok" if ok else "error"
                if name == "frame" and ok:
                    self.last_result.update(self._frame())
                return ok
        except (ValueError, TypeError):
            self.last_result = {"status": "error", "error": "invalid_command", "simulated": True}
            return False

    def status(self):
        remaining = 0
        if self._timer:
            remaining = max(0, math.ceil(self._timer[1] - (time.monotonic() - self._timer[0])))
        return dict(
            status="ok",
            mode=self.mode,
            volume=self.volume,
            mic_streaming=self._mic_enabled,
            simulation_renderer="real-cpp-wasm" if self.renderer else "limited-static-fixtures",
            countdown_active=remaining > 0,
            countdown_remaining=remaining,
            simulated=True,
            **self.stats,
        )

    def _frame(self):
        if self.mode == 25 and self._timer:
            fraction = max(0, 1 - (time.monotonic() - self._timer[0]) / self._timer[1])
            active = int(fraction * 256)
            pixels = "00ff80" * active + "000000" * (256 - active)
        elif self.renderer:
            pixels = self.renderer.call(mode=self.mode)["pixels"]
        elif self.mode == 29:
            pixels = self._pixels
        elif self.mode in (1, 2, 3):
            pixels = ({1: "ff0000", 2: "0000ff", 3: "00ff00"}[self.mode]) * 256
        elif self.mode in (16, 17):
            header = (
                Path(__file__).parents[1] / "firmware-s3/main/display/kurisu_sprites.h"
            ).read_text()
            body = header.split("KURISU_FRAME_IDLE[16][16] = {", 1)[1].split("\n};", 1)[0]
            pixels = "".join(
                f"{int(v):02x}"
                for rgb in re.findall(r"ColorRGB\((\d+), (\d+), (\d+)\)", body)
                for v in rgb
            )
        else:
            pixels = "000000" * 256

        def pwm(c):
            return (
                (self.linear[c] * self.brightness + 32767) // 65535
                if self.gamma
                else c * self.brightness // 255
            )

        scaled = "".join(f"{pwm(int(pixels[i:i+2],16)):02x}" for i in range(0, len(pixels), 2))
        self._frame_id += 1
        return dict(
            pixels=scaled,
            frame_id=self._frame_id,
            frame_source="simulation_cpp_pwm" if self.renderer else "simulation_pwm",
        )

    def play_audio_pcm(self, pcm_data, chunk_samples=512):
        self.stats["audio_rx"] += len(pcm_data) // 2
        self.stats["audio_played"] += len(pcm_data) // 2
        return True  # Simulated counters, not hardware/acoustic evidence.

    def play_beep(self, *args, **kwargs):
        return True

    def run_boot_ceremony(self, *args, **kwargs):
        return True

    def close(self):
        if self.renderer:
            self.renderer.close()


class SilentVoice:
    volume = 70

    def speak(self, text, block=True):
        return None

    def _split_zh_ja(self, text):
        lines = text.splitlines()
        return (lines[0] if lines else "", "\n".join(lines[1:]))

    def _translate_zh_to_ja_kurisu(self, text):
        return ""
