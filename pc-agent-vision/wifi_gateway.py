"""Wi-Fi discovery and acknowledged, retry-safe commands to ESP32-S3."""
import json
import socket
import threading
import time
import uuid
import os
import ipaddress
from pathlib import Path
from typing import Optional, Dict, Any, List


class WiFiGateway:
    def __init__(self, port: int = 8888):
        self.port = port
        self.sock = None
        self.is_running = False
        from pro_paths import data_dir
        self._state_path = data_dir() / 'device-state.json'
        self.board_sta_ip = os.environ.get('KURISU_BOARD_IP') or None
        if not self.board_sta_ip:
            try:
                self.board_sta_ip = json.loads(self._state_path.read_text(encoding='utf-8')).get('board_ip')
            except (OSError, ValueError):
                pass
        try:
            if self.board_sta_ip:
                ipaddress.IPv4Address(self.board_sta_ip)
        except ipaddress.AddressValueError:
            self.board_sta_ip = None
        self.board_ap_ip = "192.168.4.1"
        self.last_seen = 0.0
        self.last_mode = None
        self.last_result = {"status": "error", "error": "not_connected"}
        self._pending = {}
        self._pending_lock = threading.Lock()
        self._send_lock = threading.RLock()
        self._init_socket()
        if self.is_running:
            self._receiver = threading.Thread(target=self._receiver_loop, daemon=True)
            self._receiver.start()

    def _init_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(("", self.port))
            self.sock.settimeout(0.2)
            self.is_running = True
            print(f"[WiFiGateway] UDP {self.port}：等待板端信标与命令回执")
        except OSError as exc:
            if self.sock:
                self.sock.close()
            self.sock = None
            self.last_result = {"status": "error", "error": str(exc)}
            print(f"[WiFiGateway] 初始化失败: {exc}")

    def _receiver_loop(self):
        while self.is_running and self.sock:
            try:
                data, addr = self.sock.recvfrom(4096)
                payload = json.loads(data.decode("utf-8"))
                if not isinstance(payload, dict):
                    continue
                if payload.get("event") in ("beacon", "board_online"):
                    if payload.get("sta_ip") not in (None, "0.0.0.0"):
                        self.board_sta_ip = payload["sta_ip"]
                    elif addr[0] != "192.168.4.1" and not addr[0].startswith("127."):
                        self.board_sta_ip = addr[0]
                    self.board_ap_ip = payload.get("ap_ip", self.board_ap_ip)
                    self.last_seen = time.monotonic()
                    if "mode" in payload:
                        self.last_mode = int(payload["mode"])
                elif payload.get("request_id"):
                    with self._pending_lock:
                        pending = self._pending.get(payload["request_id"])
                        if pending and payload.get("status") in ("ok", "error"):
                            # A reply must come from the board port and one of the
                            # selected destinations (broadcast discovery may vary).
                            if addr[1] != self.port or (addr[0] not in pending["targets"] and
                                    "255.255.255.255" not in pending["targets"]):
                                continue
                            pending["result"] = payload
                            self.last_seen = time.monotonic()
                            if not addr[0].startswith("127.") and addr[0] != self.board_ap_ip:
                                self.board_sta_ip = addr[0]
                            if "mode" in payload:
                                self.last_mode = int(payload["mode"])
                            self._remember_board()
                            pending["event"].set()
            except (socket.timeout, ValueError, UnicodeError):
                continue
            except OSError:
                if self.is_running:
                    time.sleep(0.1)

    def _remember_board(self):
        if self.board_sta_ip and self.board_sta_ip != getattr(self, '_saved_ip', None):
            try:
                self._state_path.write_text(json.dumps({'board_ip': self.board_sta_ip}), encoding='utf-8')
                self._saved_ip = self.board_sta_ip
            except OSError:
                pass

    def is_online(self) -> bool:
        return self.last_seen > 0 and time.monotonic() - self.last_seen < 8.0

    def get_target_ips(self) -> List[str]:
        if self.board_sta_ip and self.is_online():
            return [self.board_sta_ip]
        return list(dict.fromkeys(ip for ip in
                    [self.board_sta_ip, self.board_ap_ip, "255.255.255.255"] if ip))

    def send_command(self, cmd_str: str, timeout: float = 0.6, retries: int = 2,
                     request_id: Optional[str] = None) -> bool:
        """True means the board dispatcher acknowledged the command, not optical verification."""
        with self._send_lock:
            if not self.sock or not self.is_running or not cmd_str.strip():
                self.last_result = {"status": "error", "error": "transport_unavailable"}
                return False
            rid = request_id or uuid.uuid4().hex
            pending = {"event": threading.Event(), "result": None, "targets": self.get_target_ips()}
            data = json.dumps({"request_id": rid, "command": cmd_str.strip()}, separators=(",", ":")).encode("utf-8")
            with self._pending_lock:
                self._pending[rid] = pending
            try:
                for _ in range(retries + 1):
                    for ip in pending["targets"]:
                        try:
                            self.sock.sendto(data, (ip, self.port))
                        except OSError:
                            continue
                    if pending["event"].wait(timeout):
                        self.last_result = pending["result"] or {"status": "error", "error": "transport_closed"}
                        return self.last_result.get("status") == "ok"
                self.last_result = {"request_id": rid, "status": "error", "error": "ack_timeout"}
                return False
            finally:
                with self._pending_lock:
                    self._pending.pop(rid, None)

    def broadcast_command(self, cmd_str: str) -> bool:
        return self.send_command(cmd_str)

    def request(self, command):
        with self._send_lock:
            self.send_command(command)
            return dict(self.last_result)

    def broadcast_json(self, payload: Dict[str, Any]) -> bool:
        return self.send_command(json.dumps(payload, separators=(",", ":")))

    def get_status(self) -> Dict[str, Any]:
        return {"wifi_online": self.is_online(), "board_sta_ip": self.board_sta_ip,
                "board_ap_ip": self.board_ap_ip, "port": self.port,
                "last_seen_sec": round(time.monotonic() - self.last_seen, 1) if self.last_seen else -1,
                "last_mode": self.last_mode, "last_command": dict(self.last_result)}

    def close(self):
        self.is_running = False
        with self._pending_lock:
            for pending in self._pending.values():
                pending["event"].set()
        if self.sock:
            self.sock.close()


_wifi_instance = None
_instance_lock = threading.Lock()


def get_wifi_gateway() -> WiFiGateway:
    global _wifi_instance
    with _instance_lock:
        if _wifi_instance is None:
            _wifi_instance = WiFiGateway()
        return _wifi_instance
