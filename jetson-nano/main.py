#!/usr/bin/env python3
"""Intelligent Lighting Control System Pro - Jetson Nano Client.
Main entry point for Jetson Nano vision and canvas interaction with ESP32-S3 over UART.
"""
import argparse
import json
import logging
import math
import os
import sys
import time

from camera_adapter import CameraAdapter
from canvas_stream import (
    CanvasStreamer,
    FireSimulation,
    MatrixRainAnimation,
    generate_bouncing_ball,
    generate_color_wave,
)
from protocol import CommandBuilder, KEY_MAP
from uart_transport import JetsonUartTransport
from vision_mapping import VisionMapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("JetsonMain")


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config.json: {e}")
    return {
        "port": "/dev/ttyTHS1",
        "baudrate": 115200,
        "timeout": 1.0,
        "camera": {"source": "usb", "device_index": 0},
    }


def run_interactive(transport: JetsonUartTransport):
    """Interactive command-line console for direct testing."""
    print("=" * 60)
    print("  ESP32-S3 Jetson Nano UART1 Interactive Console")
    print("  Commands:")
    print("    ping                     - Test bidirectional communication")
    print("    status                   - Query ESP32 system state")
    print("    caps                     - Query hardware & protocol capabilities")
    print("    mode <num>               - Switch display mode (e.g. mode 1, mode 17)")
    print("    b <val>                  - Set global brightness (0-60)")
    print("    led <color>              - Set board LED (green/red/blue/off)")
    print("    track <x> <y>            - Feed fingertip coords (0.0-1.0)")
    print("    hand <x> <y> <z> <pinch> - Feed 3D hand & pinch state")
    print("    celebrate                - Trigger Kurisu celebration fireworks")
    print("    arcade select <id>       - Select game (e.g. 33: Snake, 41: Tetris)")
    print("    arcade start             - Start current arcade game")
    print("    arcade in <key>          - Send arcade key (left/right/up/down/a/b)")
    print("    arcade status            - Query game score & state")
    print("    pixel <x> <y> <r> <g> <b>- Set single pixel on Mode 29")
    print("    clear                    - Clear canvas")
    print("    release                  - Emergency release all held keys")
    print("    quit / exit              - Exit interactive console")
    print("=" * 60)

    while True:
        try:
            line = input("kurisu@jetson> ").strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()

            if cmd in ("quit", "exit"):
                break
            elif cmd == "ping":
                reply = transport.send_line(CommandBuilder.ping(), wait_reply=True)
                print(f"[REPLY] {reply}")
            elif cmd in ("status", "get_status"):
                reply = transport.send_line(CommandBuilder.get_status(), wait_reply=True)
                print(f"[REPLY] {json.dumps(reply, indent=2, ensure_ascii=False)}")
            elif cmd in ("caps", "get_capabilities"):
                reply = transport.send_line(CommandBuilder.get_capabilities(), wait_reply=True)
                print(f"[REPLY] {json.dumps(reply, indent=2, ensure_ascii=False)}")
            elif cmd == "mode" and len(parts) > 1:
                reply = transport.send_line(CommandBuilder.mode(int(parts[1])), wait_reply=True)
                print(f"[REPLY] {reply}")
            elif cmd in ("b", "brightness") and len(parts) > 1:
                reply = transport.send_line(CommandBuilder.brightness(int(parts[1])), wait_reply=True)
                print(f"[REPLY] {reply}")
            elif cmd in ("led", "board_led") and len(parts) > 1:
                reply = transport.send_line(CommandBuilder.board_led(parts[1]), wait_reply=True)
                print(f"[REPLY] {reply}")
            elif cmd == "track" and len(parts) > 2:
                reply = transport.send_line(
                    CommandBuilder.track(float(parts[1]), float(parts[2])), wait_reply=True
                )
                print(f"[REPLY] {reply}")
            elif cmd == "hand" and len(parts) > 4:
                reply = transport.send_line(
                    CommandBuilder.hand(
                        float(parts[1]),
                        float(parts[2]),
                        float(parts[3]),
                        parts[4].lower() in ("1", "true", "pinch"),
                    ),
                    wait_reply=True,
                )
                print(f"[REPLY] {reply}")
            elif cmd == "celebrate":
                reply = transport.send_line(CommandBuilder.celebrate(), wait_reply=True)
                print(f"[REPLY] {reply}")
            elif cmd == "arcade" and len(parts) > 1:
                sub = parts[1].lower()
                if sub == "select" and len(parts) > 2:
                    reply = transport.send_line(
                        CommandBuilder.arcade_select(int(parts[2])), wait_reply=True
                    )
                elif sub == "start":
                    reply = transport.send_line(CommandBuilder.arcade_start(), wait_reply=True)
                elif sub in ("in", "input") and len(parts) > 2:
                    k_name = parts[2].lower()
                    mask = KEY_MAP.get(k_name, 0)
                    reply = transport.send_line(
                        CommandBuilder.arcade_input(mask, mask), wait_reply=True
                    )
                elif sub == "status":
                    reply = transport.send_line(CommandBuilder.arcade_status(), wait_reply=True)
                else:
                    print(f"Unknown arcade subcommand: {sub}")
                    continue
                print(f"[REPLY] {json.dumps(reply, indent=2, ensure_ascii=False) if reply else 'timeout'}")
            elif cmd == "pixel" and len(parts) > 5:
                reply = transport.send_line(
                    CommandBuilder.pixel(
                        int(parts[1]),
                        int(parts[2]),
                        int(parts[3]),
                        int(parts[4]),
                        int(parts[5]),
                        auto_mode=True,
                    ),
                    wait_reply=True,
                )
                print(f"[REPLY] {reply}")
            elif cmd in ("clear", "clear_canvas"):
                reply = transport.send_line(CommandBuilder.clear_canvas(), wait_reply=True)
                print(f"[REPLY] {reply}")
            elif cmd == "release":
                reply = transport.send_line(CommandBuilder.release_input(), wait_reply=True)
                print(f"[REPLY] {reply}")
            else:
                # Direct raw pass-through
                reply = transport.send_line(line, wait_reply=True)
                print(f"[REPLY] {reply}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"[ERROR] {e}")


def run_canvas_demo(transport: JetsonUartTransport, pattern: str = "wave", protocol: str = "binary", fps: int = 12):
    """Streams procedural animations to Mode 29 on the ESP32 matrix."""
    streamer = CanvasStreamer(transport)
    logger.info(f"Starting Canvas Demo: pattern='{pattern}', protocol='{protocol}', fps={fps}")
    logger.info("Press Ctrl+C to stop.")

    matrix_sim = MatrixRainAnimation() if pattern == "matrix" else None
    fire_sim = FireSimulation() if pattern == "fire" else None

    # Switch to canvas mode
    transport.send_line(CommandBuilder.mode(29), wait_reply=True)

    start_time = time.time()
    frame_interval = 1.0 / max(1, fps)
    frames_sent = 0

    try:
        while True:
            t_now = time.time() - start_time
            loop_start = time.time()

            if pattern == "matrix":
                colors = matrix_sim.step()
            elif pattern == "fire":
                colors = fire_sim.step()
            elif pattern == "ball":
                colors = generate_bouncing_ball(t_now)
            else:
                colors = generate_color_wave(t_now)

            if protocol == "binary":
                ok = streamer.send_binary_frame(colors, auto_mode=True)
            else:
                ok = streamer.send_chunked_frame(colors, chunk_count=2, auto_mode=True)

            if ok:
                frames_sent += 1

            if frames_sent % 30 == 0 and frames_sent > 0:
                elapsed = time.time() - start_time
                actual_fps = frames_sent / elapsed
                logger.info(f"Canvas stream active: {frames_sent} frames sent ({actual_fps:.1f} FPS)")

            spent = time.time() - loop_start
            sleep_time = max(0.001, frame_interval - spent)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\nCanvas demo stopped by user.")
        streamer.clear()


def run_vision_demo(transport: JetsonUartTransport, config: dict, simulate: bool = False):
    """Runs vision processing and maps gestures to ESP32."""
    camera = CameraAdapter(config.get("camera", {}), simulate=simulate)
    if not camera.open():
        logger.error("Failed to initialize camera adapter!")
        return

    mapper = VisionMapper(transport, config)
    logger.info("Starting Vision Demo. Press Ctrl+C to stop.")

    # Start vision session
    transport.send_line(
        CommandBuilder.session(action="start", session_id="jetson_cam", mode_name="fingertip"),
        wait_reply=True,
    )

    t0 = time.time()
    try:
        while True:
            ret, frame = camera.read_frame()
            if not ret:
                time.sleep(0.03)
                continue

            now = time.time() - t0

            if camera.simulate:
                # Generate smooth synthetic orbit movement
                x = 0.5 + 0.35 * math.sin(now * 1.5)
                y = 0.5 + 0.35 * math.cos(now * 1.5)
                pinch = (int(now) % 4) == 0
                visible = (int(now) % 8) != 7  # Periodically test hand loss

                mapper.handle_hand_frame(visible=visible, x=x, y=y, pinch=pinch, mode="fingertip")
            else:
                # Teammate hooks custom MediaPipe / PyTorch / TensorRT inference here
                # Example: pass detected results into mapper.handle_hand_frame()
                pass

            time.sleep(0.033)  # ~30 FPS

    except KeyboardInterrupt:
        logger.info("\nVision demo stopped by user.")
        mapper.handle_hand_frame(visible=False)
        transport.send_line(CommandBuilder.session(action="stop"), wait_reply=True)
    finally:
        camera.release()


def run_self_tests(transport: JetsonUartTransport) -> bool:
    """Executes automated diagnostic tests against the ESP32."""
    print("=" * 60)
    print("  Running ESP32-S3 Jetson UART Protocol Verification")
    print("=" * 60)

    tests_passed = 0
    total_tests = 0

    def check(name: str, cond: bool, detail: str = ""):
        nonlocal tests_passed, total_tests
        total_tests += 1
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {name} {detail}")
        if cond:
            tests_passed += 1

    # 1. Ping
    r_ping = transport.send_line(CommandBuilder.ping(), wait_reply=True)
    check("Ping Pong Response", r_ping is not None and r_ping.get("pong") is True, f"-> {r_ping}")

    # 2. Status
    r_stat = transport.send_line(CommandBuilder.get_status(), wait_reply=True)
    check(
        "Get Status Query",
        r_stat is not None and r_stat.get("board") == "esp32s3_pro",
        f"-> mode={r_stat.get('mode') if r_stat else 'N/A'}",
    )

    # 3. Capabilities
    r_caps = transport.send_line(CommandBuilder.get_capabilities(), wait_reply=True)
    check(
        "Get Capabilities",
        r_caps is not None and "pixel_canvas" in r_caps.get("features", []),
        f"-> features={len(r_caps.get('features', [])) if r_caps else 0}",
    )

    # 4. Mode switch
    r_mode = transport.send_line(CommandBuilder.mode(17), wait_reply=True)
    check("Mode Switch (Mode 17 Kurisu)", r_mode is not None and r_mode.get("status") == "ok")

    # 5. Brightness
    r_bri = transport.send_line(CommandBuilder.brightness(20), wait_reply=True)
    check("Brightness Adjustment", r_bri is not None and r_bri.get("status") == "ok")

    # 6. Fingertip Tracker Feed
    r_trk = transport.send_line(CommandBuilder.track(0.5, 0.5), wait_reply=True)
    check("Fingertip Track Feed", r_trk is not None and r_trk.get("status") == "ok")

    # 7. Hand Pinch Feed
    r_hnd = transport.send_line(CommandBuilder.hand(0.5, 0.5, 0.0, pinch=True), wait_reply=True)
    check("Hand 3D Pinch Feed", r_hnd is not None and r_hnd.get("status") == "ok")

    # 8. Desktop Pet Context
    r_pet = transport.send_line(CommandBuilder.pet_context(12, 0.0, True, False), wait_reply=True)
    check("Desktop Pet Context", r_pet is not None and r_pet.get("status") == "ok")

    # 9. Key Release
    r_rel = transport.send_line(CommandBuilder.release_input(), wait_reply=True)
    check("Safety Key Release", r_rel is not None and r_rel.get("released") is True)

    # 10. Single Pixel Canvas
    r_px = transport.send_line(CommandBuilder.pixel(8, 8, 255, 0, 0, auto_mode=True), wait_reply=True)
    check("Canvas Single Pixel", r_px is not None and r_px.get("status") == "ok")

    # 11. Chunked Canvas 2-Chunk Delivery
    streamer = CanvasStreamer(transport)
    test_colors = [(i, (i * 2) % 256, (i * 3) % 256) for i in range(256)]
    ok_chunk = streamer.send_chunked_frame(test_colors, chunk_count=2, auto_mode=True)
    check("Canvas 2-Chunk Reassembly", ok_chunk)

    # 12. High-speed Binary Frame Delivery
    ok_bin = streamer.send_binary_frame(test_colors, auto_mode=True)
    check("Canvas High-Speed Binary Frame", ok_bin)

    print("=" * 60)
    print(f"Results: {tests_passed}/{total_tests} tests passed.")
    print("=" * 60)
    return tests_passed == total_tests


def main():
    parser = argparse.ArgumentParser(description="Kurisu Pro - Jetson Nano UART Client")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Subcommand: interactive
    subparsers.add_parser("interactive", help="Start interactive text console")

    # Subcommand: canvas
    p_canvas = subparsers.add_parser("canvas", help="Run canvas procedural animation demo")
    p_canvas.add_argument(
        "--pattern", choices=["wave", "matrix", "fire", "ball"], default="wave", help="Pattern name"
    )
    p_canvas.add_argument(
        "--protocol", choices=["binary", "chunked"], default="binary", help="Transport protocol"
    )
    p_canvas.add_argument("--fps", type=int, default=12, help="Target FPS (default 12)")

    # Subcommand: vision
    p_vision = subparsers.add_parser("vision", help="Run vision gesture & camera tracking demo")
    p_vision.add_argument("--simulate", action="store_true", help="Run with synthetic simulated tracking")

    # Subcommand: test
    subparsers.add_parser("test", help="Run automated protocol test suite against ESP32")

    # Global options
    parser.add_argument("--port", type=str, default=None, help="Serial port (e.g. /dev/ttyTHS1, COM9)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    parser.add_argument(
        "--simulate-uart", action="store_true", help="Simulate serial connection without hardware"
    )

    args = parser.parse_args()
    config = load_config()

    port = args.port or config.get("port", "/dev/ttyTHS1")
    baud = args.baud or config.get("baudrate", 115200)
    simulate_uart = args.simulate_uart

    transport = JetsonUartTransport(port=port, baudrate=baud, simulate=simulate_uart)
    if not transport.connect():
        logger.error(
            f"Could not connect to {port}. If running without ESP32, use --simulate-uart."
        )
        sys.exit(1)

    try:
        if args.command == "interactive" or not args.command:
            run_interactive(transport)
        elif args.command == "canvas":
            run_canvas_demo(transport, pattern=args.pattern, protocol=args.protocol, fps=args.fps)
        elif args.command == "vision":
            run_vision_demo(transport, config, simulate=args.simulate)
        elif args.command == "test":
            ok = run_self_tests(transport)
            sys.exit(0 if ok else 1)
    finally:
        transport.close()


if __name__ == "__main__":
    main()
