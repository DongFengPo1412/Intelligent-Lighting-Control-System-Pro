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
        try:
            sock = socket.create_connection(
                (gateway.board_sta_ip or gateway.board_ap_ip, 8889), timeout=3
            )
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(3)
            token = gateway.control_token
            if len(token) != 64:
                raise ValueError("Board pairing required (KURISU_CONTROL_TOKEN)")
            sock.sendall(packet(4, HELLO + b"|" + token.encode("ascii")))
            if receive(sock) != (4, HELLO):
                raise ValueError("Unsupported PCM protocol")
            self.sock = sock
            self.boot_id = gateway.boot_id
            self.connected = True
            self.last_error = None
            self.closed = threading.Event()
            threading.Thread(target=self._read, args=(sock, self.closed), daemon=True).start()
            threading.Thread(target=self._heartbeat, args=(sock, self.closed), daemon=True).start()
            return True
        except (OSError, ValueError) as exc:
            self.last_error = str(exc)
            if "sock" in locals():
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
        while not closed.wait(1):
            try:
                self._send(5, b"ping", sock)
            except OSError:
                self.close(sock)
                break

    def play(self, pcm, chunk_samples=512, cancelled=None):
        if not pcm or len(pcm) % 2 or not 1 <= chunk_samples <= 1024:
            raise ValueError("Invalid PCM input")
        return self.play_stream(iter([pcm]), chunk_samples, cancelled=cancelled)

    def abort(self, timeout=1.2):
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
                start = time.monotonic()
                self.playback_active = True
                self.controller.playback_started_at = start
                total = 0
                for pcm in chain([first], chunks):
                    if not pcm or len(pcm) % 2:
                        raise ValueError('Invalid generated PCM segment')
                    # If synthesis really falls behind, pace from its arrival
                    # rather than bursting stale scheduled data into the board.
                    start += max(0, time.monotonic() - (start + total/32000 + .12))
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
                        self._send(1, chunk)
                    total += len(pcm)
                if self.cancelled.wait(max(0, start + total / 32000 + 0.35 - time.monotonic())):
                    return False
                after = self.controller.command_result({"cmd": "status"})
                delta = {
                    k: (after.get(k, 0) - before.get(k, 0)) & 0xFFFFFFFF
                    for k in ("audio_rx", "audio_played", "audio_dropped", "audio_errors")
                }
                valid = (
                    before.get("status") == "ok"
                    and after.get("status") == "ok"
                    and delta["audio_rx"] == total // 2 == delta["audio_played"]
                    and not (delta["audio_dropped"] or delta["audio_errors"])
                )
                if not valid:
                    self.last_error = dict(expected=total // 2, **delta)
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
