"""Opt-in physical audio test. Announce playback / mic sampling beforehand."""

import argparse
import array
import json
import math
import os
from pathlib import Path
import sys
import threading
import time


def run(args):
    repo = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Use a task cache outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    os.environ["KURISU_DATA_DIR"] = str(output / "runtime-data")
    os.environ["KURISU_AUDIO_TRANSPORT"] = "usb"
    sys.path.insert(0, str(repo / "pc-agent-vision"))
    from light_controller import LightController
    from wifi_gateway import get_wifi_gateway

    controller = LightController(port=args.port)
    results = []
    try:
        if not controller.wait_for_control(30):
            raise RuntimeError("No board Wi-Fi ACK")
        if not controller.enable_mic(False) or not controller.set_volume(70):
            raise RuntimeError("Cannot set baseline")
        for transport in ("usb", "wifi"):
            controller.audio_transport = transport
            if args.playback:
                pcm = (repo / "pc-agent-vision" / "kurisu_wake_reply.pcm").read_bytes()
                before = controller.command_result(dict(cmd="status"))
                print(f"PLAY {transport}: {len(pcm)//2} samples", flush=True)
                ok = controller.play_audio_pcm(pcm)
                after = controller.command_result(dict(cmd="status"))
                delta = {
                    k: (after.get(k, 0) - before.get(k, 0)) & 0xFFFFFFFF
                    for k in (
                        "audio_rx",
                        "audio_played",
                        "audio_dropped",
                        "audio_errors",
                    )
                }
                results.append(
                    dict(
                        transport=transport,
                        passed=ok,
                        delta=delta,
                        error=controller.last_audio_error,
                        stack_free=after.get("audio_stack_free"),
                    )
                )
            else:
                samples = array.array("h")
                arrivals = []
                capture = threading.Event()

                def collect(data):
                    if capture.is_set():
                        arrivals.append((time.monotonic(), len(data) // 2))
                        samples.frombytes(data)

                controller.on_mic_data = collect
                if not controller.enable_mic(True):
                    raise RuntimeError("Cannot enable microphone")
                # Measure a steady window, excluding handshake and UDP ACK time.
                time.sleep(0.5)
                print(f"MIC {transport}: {args.seconds} seconds", flush=True)
                start = time.monotonic()
                capture.set()
                time.sleep(args.seconds)
                capture.clear()
                elapsed = time.monotonic() - start
                if not controller.enable_mic(False):
                    raise RuntimeError("Cannot stop microphone")
                time.sleep(0.2)
                controller.on_mic_data = None
                gaps = sorted(b[0] - a[0] for a, b in zip(arrivals, arrivals[1:]))
                results.append(
                    dict(
                        transport=transport,
                        samples=len(samples),
                        elapsed=elapsed,
                        samples_per_second=len(samples) / elapsed,
                        packet_gap_max=max(gaps, default=0),
                        packet_gap_p95=(
                            gaps[min(len(gaps) - 1, int(len(gaps) * 0.95))]
                            if gaps
                            else 0
                        ),
                        peak=max(map(abs, samples), default=0),
                        rms=math.sqrt(
                            sum(v * v for v in samples) / max(1, len(samples))
                        ),
                        clipped=sum(abs(v) >= 32760 for v in samples),
                        passed=15200 <= len(samples) / elapsed <= 16800
                        and max(gaps, default=0) < .5,
                    )
                )
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
            if not results[-1]["passed"]:
                raise AssertionError(f"{transport} failed")
            time.sleep(2)
    finally:
        controller.on_mic_data = None
        controller.enable_mic(False)
        controller.close()
        get_wifi_gateway().close()
        name = "playback" if args.playback else "microphone"
        (output / f"{name}-results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", default="COM9")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--playback", action="store_true")
    action.add_argument("--microphone", action="store_true")
    parser.add_argument("--seconds", type=int, choices=range(2, 31), default=6)
    run(parser.parse_args())
