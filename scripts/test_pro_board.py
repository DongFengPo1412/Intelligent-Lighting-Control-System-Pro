"""Opt-in silent physical regression. No microphone or camera is enabled.

Run with the production service stopped; output must be outside the repository.
Speaker volume is set to zero before any display mode can produce a signal.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid


def run(output):
    output = output.resolve()
    repo = Path(__file__).resolve().parents[1]
    if output == repo or repo in output.parents:
        raise ValueError("Use a task cache outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    os.environ["KURISU_DATA_DIR"] = str(output / "runtime-data")
    sys.path.insert(0, str(repo / "pc-agent-vision"))
    from wifi_gateway import WiFiGateway

    gateway = WiFiGateway()
    checks = []

    def check(name, condition, detail=None):
        row = dict(test=name, passed=bool(condition), detail=detail)
        checks.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if not condition:
            raise AssertionError(name)

    def command(payload, expected=True, **kwargs):
        text = json.dumps(payload, separators=(",", ":"))
        ok = gateway.send_command(text, **kwargs)
        result = dict(gateway.last_result)
        # Preserve complete receipts on disk, keep console output bounded.
        receipt = {k: v for k, v in result.items() if k != "pixels"}
        check(payload["cmd"], ok == expected, receipt)
        return result

    muted = False
    try:
        deadline = time.monotonic() + 30
        while not gateway.is_online() and time.monotonic() < deadline:
            gateway.send_command('{"cmd":"status"}', timeout=0.3, retries=0)
            time.sleep(0.2)
        command(dict(cmd="status"))
        command(dict(cmd="volume", val=0))
        muted = True
        command(dict(cmd="mic", enable=False))
        command(dict(cmd="brightness", val=20))
        command(dict(cmd="gamma", enable=False))
        for mode in sorted(set(range(32)) - {18, 25}):
            receipt = command(dict(cmd="mode", val=mode))
            check(f"mode {mode} selected", receipt.get("mode") == mode)
            time.sleep(0.12)
            frame = command(dict(cmd="frame"))
            check(f"mode {mode} completed frame", len(frame.get("pixels", "")) == 1536)
        for payload in (
            dict(cmd="track_cal", x0=0, y0=0, x1=1, y1=1),
            dict(cmd="track", x=0.3, y=0.6, visible=True, conf=0.9),
            dict(cmd="hand", x=0.4, y=0.5, z=0, pinch=True, visible=True),
            dict(cmd="hand", x=0.7, y=0.3, z=0.2, pinch=False, visible=True),
            dict(cmd="mir", energy=0.8, flux=0.6, tempo=120, onset=True, phase=0.2),
            dict(cmd="difficulty", level=0.5, adaptive=True),
            dict(cmd="performance", reaction_ms=400, frustration=0.1, success=True),
            dict(cmd="pet_context", hour=12, gaze=0.2, present=True, tired=False),
        ):
            command(payload)
        command(dict(cmd="mode", val=29))
        command(dict(cmd="canvas", hex="ff0000" * 256))
        time.sleep(0.12)
        before = command(dict(cmd="frame"))
        check(
            "canvas uniform nonzero red PWM",
            len(set(before["pixels"][i : i + 6] for i in range(0, 1536, 6))) == 1
            and int(before["pixels"][:2], 16) > 0
            and before["pixels"][2:6] == "0000",
        )
        command(dict(cmd="canvas", hex="ff0000" * 255 + "00000z"), False)
        time.sleep(0.08)
        after = command(dict(cmd="frame"))
        check(
            "invalid canvas leaves pixels intact", before["pixels"] == after["pixels"]
        )
        for payload in (
            dict(cmd="mode", val=18),
            dict(cmd="mode", val=32),
            dict(cmd="track", x=2, y=0.5, visible=True),
            dict(cmd="hand", x=0.5, y=0.5, z=3, pinch=False, visible=True),
            dict(cmd="gamma", enable=1),
            dict(cmd="difficulty", level=2, adaptive=True),
            dict(cmd="mir", energy=2, flux=0.5, tempo=120, onset=True),
        ):
            command(payload, False)
        request_id = uuid.uuid4().hex
        command(dict(cmd="countdown", seconds=4), request_id=request_id)
        time.sleep(2.1)
        command(dict(cmd="countdown", seconds=4), request_id=request_id)
        status = command(dict(cmd="status"))
        check("retry did not restart timer", 0 < status["countdown_remaining"] <= 2)
        command(dict(cmd="mode", val=1), False, request_id=request_id)
        time.sleep(4)
        status = command(dict(cmd="status"))
        check(
            "timer completed",
            not status["countdown_active"] and status["countdown_remaining"] == 0,
        )
        check("no audio write errors", status["audio_errors"] == 0, status)
    finally:
        if muted:
            for payload in (
                dict(cmd="stop_countdown"),
                dict(cmd="gamma", enable=False),
                dict(cmd="difficulty", level=0.5, adaptive=True),
                dict(cmd="pet_context", hour=12, gaze=0, present=True, tired=False),
                dict(cmd="mode", val=17),
                dict(cmd="volume", val=70),
            ):
                gateway.send_command(json.dumps(payload))
        gateway.close()
        (output / "control-results.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"PASS: {len(checks)} physical checks", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    run(parser.parse_args().output_dir)
