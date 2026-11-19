"""Bidirectional TCP PCM transport, explicitly distinct from XiaoZhi Opus.

No socket is opened until connect(). Playback is paced and checked against board
counters; socket send-success alone is not returned as playback success.
"""

import json
import socket
import struct
import threading
import time

MAGIC = b"KAP1"
HELLO = b"pcm16le/16000/mono/v2"


def packet(kind, payload):
    if not 0 < len(payload) <= 2048:
        raise ValueError("Invalid PCM packet length")
    return struct.pack("!4sBH", MAGIC, kind, len(payload)) + payload


def receive(sock):
    def exact(n):
        chunks = bytearray()
        while len(chunks) < n:
            data = sock.recv(n - len(chunks))
            if not data:
                raise ConnectionError("PCM peer disconnected")
            chunks.extend(data)
        return bytes(chunks)

    magic, kind, length = struct.unpack("!4sBH", exact(7))
    if magic != MAGIC or not 0 < length <= 2048:
        raise ValueError("Malformed PCM frame")
    payload = exact(length)
    if kind in (1, 2) and length % 2:
        raise ValueError("Incomplete PCM16 sample")
    return kind, payload


class WiFiPcmClient:
    def __init__(self, controller):
        self.controller = controller
        self.sock = None
        self.connected = False
        self.tx = threading.Lock()
        self.play_lock = threading.Lock()
        self.playback_active = False
        self.cancelled = threading.Event()
        self.closed = threading.Event()
        self.last_error = None
        self.boot_id = None
        self.state = threading.RLock()
        self._barrier_lock = threading.Lock()
        self._barriers = {}

    def connect(self):
        with self.state:
            return self._connect_locked()

    def _connect_locked(self):
        if self.connected:
            return True
        from wifi_gateway import get_wifi_gateway

        gateway = get_wifi_gateway()
        if not self.controller.wait_for_control():
            return False
        sock = None
        try:
            token = getattr(gateway, "control_token", "")
            ticket = gateway.request_audio_ticket() if (len(token) == 64 or not token) else None
            last_err = (getattr(gateway, "last_result", None) or {}).get("error")
            need_usb_pair = (len(token) != 64) or (
                (not ticket or len(ticket) != 64)
                and last_err in ("pairing_required", "invalid_token", "invalid_command")
            )
            if (
                need_usb_pair
                and not __import__("os").environ.get("PYTEST_CURRENT_TEST")
                and hasattr(gateway, "bootstrap_usb_pairing")
                and gateway.bootstrap_usb_pairing()
            ):
                token = getattr(gateway, "control_token", "")
                self.controller.wait_for_control(10.0)
                ticket = gateway.request_audio_ticket()
            if ticket and isinstance(ticket, str) and len(ticket) == 64:
                token = ticket
            if len(token) != 64:
                raise PermissionError("PCM authentication required: host must be paired with control_token or valid audio ticket")
            target_ip = gateway.board_sta_ip or gateway.board_ap_ip
            last_net_exc = None
            for attempt in range(2):
                attempt_sock = None
                try:
                    attempt_sock = socket.create_connection((target_ip, 8889), timeout=5)
                    attempt_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    attempt_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
                    attempt_sock.settimeout(6.0)
                    payload = HELLO + b"|" + token.encode("ascii")
                    attempt_sock.sendall(packet(4, payload))
                    rx_kind, rx_payload = receive(attempt_sock)
                    if rx_kind != 4 or rx_payload != HELLO:
                        raise ValueError("Unsupported PCM protocol or handshake rejected")
                    sock = attempt_sock
                    break
                except OSError as exc:
                    last_net_exc = exc
                    if attempt_sock is not None:
                        attempt_sock.close()
                    if attempt == 0:
                        time.sleep(0.3)
                except ValueError:
                    if attempt_sock is not None:
                        attempt_sock.close()
                    raise
            if sock is None:
                raise last_net_exc or OSError("PCM connection failed")
            self.sock = sock
            self.boot_id = gateway.boot_id
            self.connected = True
            self.last_error = None
            self.closed = threading.Event()
            threading.Thread(target=self._read, args=(sock, self.closed), daemon=True).start()
            threading.Thread(target=self._heartbeat, args=(sock, self.closed), daemon=True).start()
            return True
        except (OSError, ValueError, PermissionError) as exc:
            self.last_error = str(exc)
            if sock is not None:
                sock.close()
            return False

    def _send(self, kind, data, expected=None):
        with self.tx, self.state:
            if not self.connected or (expected is not None and expected is not self.sock):
                raise ConnectionError("PCM not connected")
            self.sock.sendall(packet(kind, data))

    def _read(self, sock, closed):
        try:
            while not closed.is_set():
                kind, data = receive(sock)
                if kind == 2 and self.controller.on_mic_data:
                    self.controller.on_mic_data(data)
                elif kind == 5:
                    with self._barrier_lock:
                        event = self._barriers.get(data)
                    if event is not None:
                        event.set()
        except (OSError, ValueError) as exc:
            self.last_error = str(exc)
        finally:
            self.close(sock)

    def _heartbeat(self, sock, closed):
        while not closed.wait(0.5):
            try:
                self._send(5, b"ping", sock)
            except OSError:
                self.close(sock)
                break

    def play(self, pcm, chunk_samples=512, cancelled=None):
        if not pcm or len(pcm) % 2 or not 1 <= chunk_samples <= 1024:
            raise ValueError("Invalid PCM input")
        return self.play_stream(iter([pcm]), chunk_samples, cancelled=cancelled)

    def abort(self, timeout=2.2):
        """Stop the old producer, fence TCP PCM, then drain board playback.

        UDP abort alone can overtake old TCP audio. The existing kind-5 echo
        fences those bytes without changing firmware or accepting a send as ACK.
        """
        self.cancelled.set()
        deadline = time.monotonic() + timeout
        if not self.play_lock.acquire(timeout=max(0, deadline-time.monotonic())):
            self.last_error = 'audio_abort_producer_timeout'
            return False
        marker = f'barrier:{time.monotonic_ns()}'.encode('ascii')
        event = threading.Event()
        try:
            with self._barrier_lock:
                self._barriers[marker] = event
            self._send(5, marker)
            if not event.wait(max(0, deadline-time.monotonic())):
                self.last_error = 'audio_abort_barrier_timeout'
                return False
            result = self.controller.command_result({'cmd':'audio_abort'})
            if result.get('status') != 'ok':
                self.last_error = 'audio_abort_not_acknowledged'
                return False
            # One block may already be in I2S. Require accounting to settle
            # before the next utterance's exact sample-count baseline is taken.
            previous = None
            stable_since = time.monotonic()
            while time.monotonic() < deadline:
                result = self.controller.command_result({'cmd':'status'})
                if result.get('status') != 'ok':
                    self.last_error = 'audio_abort_status_unavailable'
                    return False
                counts = tuple(result.get(k) for k in ('audio_rx','audio_played','audio_dropped','audio_errors'))
                if any(value is None for value in counts):
                    self.last_error = 'audio_abort_counters_missing'
                    return False
                if counts != previous:
                    stable_since = time.monotonic()
                    previous = counts
                elif time.monotonic()-stable_since >= .12:
                    self.last_error = None
                    print('[WiFi音频] 旧PCM传输屏障、停止回执与播放计数稳定已确认')
                    return True
                time.sleep(.03)
            self.last_error = 'audio_abort_drain_timeout'
            return False
        except (OSError, ValueError) as exc:
            self.last_error = str(exc)
            return False
        finally:
            with self._barrier_lock:
                self._barriers.pop(marker, None)
            self.play_lock.release()

    def play_stream(self, chunks, chunk_samples=512, cancelled=None):
        """One paced utterance and one final counter check across TTS chunks."""
        if not 1 <= chunk_samples <= 1024:
            raise ValueError("Invalid PCM chunk size")
        from itertools import chain
        chunks = iter(chunks)
        if cancelled is not None and cancelled.is_set():return False
        first = next(chunks, None)
        if first is None:
            return False
        with self.play_lock:
            if cancelled is not None and cancelled.is_set():return False
            if not self.connect():
                return False
            self.cancelled.clear()
            restore = self.controller._mic_enabled
            duplex = (__import__("os").environ.get("KURISU_BARGE_IN") == "1"
                      or bool(getattr(self.controller, "_music_wake_active", False)))
            try:
                if not duplex and not self.controller.enable_mic(False):
                    return False
                before = self.controller.command_result({"cmd": "status"})
                if before.get("status") != "ok":
                    time.sleep(0.1)
                    before = self.controller.command_result({"cmd": "status"})
                start = time.monotonic()
                self.playback_active = True
                self.controller.playback_started_at = start
                total = 0
                self.last_stream_stats = dict(segments=0, synthesis_gaps=0, max_synthesis_gap_ms=0)
                for pcm in chain([first], chunks):
                    if not pcm or len(pcm) % 2:
                        raise ValueError('Invalid generated PCM segment')
                    # If synthesis really falls behind, pace from its arrival
                    # rather than bursting stale scheduled data into the board.
                    arrived = time.monotonic()
                    gap_ms = max(0.0, (arrived - (start + total / 32000)) * 1000) if total else 0.0
                    self.last_stream_stats['segments'] += 1
                    if gap_ms > 60:
                        self.last_stream_stats['synthesis_gaps'] += 1
                        self.last_stream_stats['max_synthesis_gap_ms'] = max(
                            self.last_stream_stats['max_synthesis_gap_ms'], round(gap_ms, 1)
                        )
                        print(f'[PCM连续性] 等待下一合成段 {gap_ms:.0f}ms')
                    start += max(0, arrived - (start + total/32000 + .12))
                    for offset in range(0, len(pcm), chunk_samples * 2):
                        if self.cancelled.is_set() or (cancelled is not None and cancelled.is_set()):
                            return False
                        wait = start + (total+offset)/32000 - 0.12 - time.monotonic()
                        if wait > 0 and self.cancelled.wait(wait):
                            return False
                        chunk = pcm[offset : offset + chunk_samples * 2]
                        echo = getattr(self.controller, "echo_canceller", None)
                        if echo is not None:
                            echo.feed_reference(chunk)
                        try:
                            self._send(1, chunk)
                        except OSError:
                            if self.cancelled.is_set() or (cancelled is not None and cancelled.is_set()):
                                return False
                            self.close()
                            if not self.connect():
                                raise
                            self._send(1, chunk)
                    total += len(pcm)
                if self.cancelled.wait(max(0, start + total / 32000 + 0.35 - time.monotonic())):
                    return False
                expected_samples = total // 2
                confirm_deadline = time.monotonic() + 4.5
                delta = {"audio_rx": 0, "audio_played": 0, "audio_dropped": 0, "audio_errors": 0}
                after = {}
                valid = False
                while True:
                    after = self.controller.command_result({"cmd": "status"})
                    if before.get("status") == "ok" and after.get("status") == "ok":
                        delta = {
                            k: (after.get(k, 0) - before.get(k, 0)) & 0xFFFFFFFF
                            for k in ("audio_rx", "audio_played", "audio_dropped", "audio_errors")
                        }
                        valid = (
                            delta["audio_rx"] == expected_samples == delta["audio_played"]
                            and not (delta["audio_dropped"] or delta["audio_errors"])
                        )
                        if valid or delta["audio_dropped"] or delta["audio_errors"] or delta["audio_rx"] > expected_samples:
                            break
                    if time.monotonic() >= confirm_deadline or self.cancelled.is_set() or (cancelled is not None and cancelled.is_set()):
                        break
                    if self.cancelled.wait(0.18):
                        return False
                if not valid:
                    self.last_error = dict(expected=expected_samples, **delta)
                return valid
            except (OSError, ValueError) as exc:
                self.last_error = str(exc)
                return False
            finally:
                self.playback_active = False
                if restore and not duplex:
                    self.controller.enable_mic(True)

    def close(self, expected=None):
        with self.state:
            if expected is not None and expected is not self.sock:
                return
            self.connected = False
            self.closed.set()
            sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
