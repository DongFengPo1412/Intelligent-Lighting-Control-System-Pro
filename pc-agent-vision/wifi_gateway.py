"""Wi-Fi discovery and acknowledged, retry-safe commands to ESP32-S3."""
import json
import socket
import threading
import time
import uuid
import os
import ipaddress
import re
import copy
import hashlib
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List


class WiFiGateway:
    def __init__(self, port: int = 8888):
        self.port = port
        self.sock = None
        self.is_running = False
        from pro_paths import data_dir
        self._state_path = data_dir() / 'device-state.json'
        self.control_token = os.environ.get('KURISU_CONTROL_TOKEN', '').strip()
        if not self.control_token:
            try:
                self.control_token = json.loads((data_dir() / 'control-pairing.json').read_text(encoding='utf-8'))['control_token']
            except (OSError, ValueError, KeyError, TypeError):
                self.control_token = ''
        if not isinstance(self.control_token, str):
            self.control_token = ''
        self.boot_id = None
        self.client_id = uuid.uuid4().hex
        try:
            saved = json.loads(self._state_path.read_text(encoding='utf-8'))
            if isinstance(saved.get('client_id'), str) and len(saved['client_id']) == 32:
                self.client_id = saved['client_id']
        except (OSError, ValueError):
            pass
        self._sequence = int(time.time() * 1_000_000)
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
        self._trust_private = os.environ.get("KURISU_TRUST_PRIVATE", "1") == "1"
        self._pending = {}
        self._pending_lock = threading.Lock()
        self._send_lock = threading.RLock()
        self._read_lock = threading.Lock()
        self._read_sequence = self._sequence
        self._read_boot = None
        self._status_lock=threading.Lock()
        self._status_sequence=self._sequence
        self._status_boot=None
        self._metrics={}
        self._remember_board()
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
                if len(data) >= 4096:
                    continue
                payload = json.loads(data.decode("utf-8"))
                if not isinstance(payload, dict):
                    continue
                if payload.get("event") in ("beacon", "board_online"):
                    sender_ip = addr[0]
                    sta_ip = payload.get("sta_ip")
                    valid_sender = (isinstance(sta_ip, str) and (sta_ip == sender_ip or sta_ip == "0.0.0.0")) or payload.get("device") == "Kurisu-Matrix"
                    if valid_sender and self._is_trusted_hotspot_ip(sender_ip):
                        self.last_seen = time.monotonic()
                        if "mode" in payload and isinstance(payload["mode"], int):
                            self.last_mode = payload["mode"]
                        if self.board_sta_ip != sender_ip:
                            print(f"[WiFiGateway] 校验信标来源通过，灯板 STA IP 动态更新: {self.board_sta_ip} -> {sender_ip}")
                            self.board_sta_ip = sender_ip
                            self.boot_id = None
                            self._remember_board()
                    continue
                elif isinstance(payload.get("request_id"), str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', payload['request_id']):
                    if 'pixels_b64' in payload:
                        try:
                            encoded=payload['pixels_b64']
                            if not isinstance(encoded,str) or len(encoded)!=1024:
                                raise ValueError('invalid frame length')
                            pixels=base64.b64decode(encoded,validate=True)
                            if len(pixels)!=768: raise ValueError('invalid RGB888 frame')
                            payload['pixels']=pixels.hex()
                        except (ValueError,TypeError):
                            payload={'request_id':payload['request_id'],'status':'error','error':'invalid_frame'}
                    if 'mode' in payload and (type(payload['mode']) is not int or not 0 <= payload['mode'] <= 255):
                        continue
                    with self._pending_lock:
                        pending = self._pending.get(payload["request_id"])
                        if pending and payload.get("status") in ("ok", "error"):
                            # A reply must come from the board port and one of the
                            # selected destinations (or trusted hotspot IP when broadcast probe was sent).
                            is_target = (addr[0] in pending["targets"]) or (
                                any(t.endswith(".255") or t == "255.255.255.255" for t in pending["targets"])
                                and self._is_trusted_hotspot_ip(addr[0])
                            )
                            if addr[1] != self.port or not is_target:
                                continue
                            pending["result"] = payload
                            pending["reply_bytes"] = len(data)
                            if payload.get('status') == 'ok':
                                self.last_seen = time.monotonic()
                            if not addr[0].startswith("127.") and addr[0] != self.board_ap_ip:
                                if self.board_sta_ip != addr[0]:
                                    print(f"[WiFiGateway] 探活回执确认，更新灯板 STA IP: {self.board_sta_ip} -> {addr[0]}")
                                    self.board_sta_ip = addr[0]
                            if "mode" in payload:
                                self.last_mode = int(payload["mode"])
                            self._remember_board()
                            pending["event"].set()
            except (socket.timeout, ValueError, UnicodeError, TypeError):
                continue
            except OSError:
                if self.is_running:
                    time.sleep(0.1)

    def _remember_board(self):
        if (self.board_sta_ip != getattr(self, '_saved_ip', None) or
                self.client_id != getattr(self, '_saved_client', None)):
            try:
                self._state_path.write_text(json.dumps({'board_ip': self.board_sta_ip, 'client_id': self.client_id}), encoding='utf-8')
                self._saved_ip = self.board_sta_ip
                self._saved_client = self.client_id
            except OSError:
                pass

    @staticmethod
    def _is_private_ip(ip_str: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip_str)
            return addr.is_loopback or addr.is_private
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_trusted_hotspot_ip(ip_str: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip_str)
            if addr.is_loopback:
                return True
            trusted_net = ipaddress.ip_network(os.environ.get("KURISU_HOTSPOT_SUBNET", "192.168.186.0/24"), strict=False)
            return addr in trusted_net
        except (ValueError, TypeError):
            return False

    def is_online(self) -> bool:
        return self.last_seen > 0 and time.monotonic() - self.last_seen < 8.0

    def get_target_ips(self) -> List[str]:
        if self.board_sta_ip and (self.is_online() or self.board_sta_ip.startswith("127.")):
            return [self.board_sta_ip]
        targets: List[str] = []
        if self.board_sta_ip:
            targets.append(self.board_sta_ip)
        trusted_net = os.environ.get("KURISU_HOTSPOT_SUBNET", "192.168.186.0/24")
        try:
            net = ipaddress.ip_network(trusted_net, strict=False)
            bcast = str(net.broadcast_address)
            if bcast not in targets:
                targets.append(bcast)
        except Exception:
            pass
        if "255.255.255.255" not in targets:
            targets.append("255.255.255.255")
        if self.board_ap_ip and self.board_ap_ip not in targets:
            targets.append(self.board_ap_ip)
        return targets

    def send_command(self, cmd_str: str, timeout: Optional[float] = None, retries: Optional[int] = None,
                     request_id: Optional[str] = None) -> bool:
        """True means the board dispatcher acknowledged the command, not optical verification."""
        if timeout is None:
            timeout = float(os.environ.get("KURISU_UDP_TIMEOUT", "0.6"))
        if retries is None:
            retries = int(os.environ.get("KURISU_UDP_RETRIES", "2"))
        with self._send_lock:
            if not self.sock or not self.is_running or not cmd_str.strip():
                self.last_result = {"status": "error", "error": "transport_unavailable"}
                return False
            if len(self.control_token) != 64 or any(c not in '0123456789abcdef' for c in self.control_token):
                target_is_trusted = all(
                    self._is_trusted_hotspot_ip(ip) for ip in self.get_target_ips()
                )
                if not (self._trust_private and target_is_trusted):
                    self.last_result = {"status": "error", "error": "pairing_required"}
                    return False
            if not self.boot_id:
                # This probe only obtains a boot nonce. No command is executed.
                probe_id = uuid.uuid4().hex
                probe = {"event": threading.Event(), "result": None, "targets": self.get_target_ips()}
                with self._pending_lock:
                    self._pending[probe_id] = probe
                try:
                    wire = json.dumps({"request_id": probe_id}).encode('utf-8')
                    sent_any = False
                    for ip in probe['targets']:
                        try:
                            self.sock.sendto(wire, (ip, self.port))
                            sent_any = True
                        except OSError:
                            continue
                    if not sent_any:
                        self.last_result = {"status": "error", "error": "transport_unavailable"}
                        return False
                    if not probe['event'].wait(timeout):
                        self.last_result = {"status": "error", "error": "discovery_timeout"}
                        return False
                    self.boot_id = (probe['result'] or {}).get('boot_id')
                    if not isinstance(self.boot_id, str) or len(self.boot_id) != 32:
                        self.last_result = {"status": "error", "error": "invalid_boot_id"}
                        self.boot_id = None
                        return False
                except OSError:
                    self.last_result = {"status": "error", "error": "transport_unavailable"}
                    return False
                finally:
                    with self._pending_lock:
                        self._pending.pop(probe_id, None)
            rid = request_id or uuid.uuid4().hex
            if not isinstance(rid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', rid):
                self.last_result = {"status":"error","error":"invalid_request_id"}
                return False
            self._sequence += 1
            rid = f'{self._sequence}_{rid}'
            if len(rid) > 64:
                self.last_result = {"status":"error","error":"invalid_request_id"}
                return False
            pending = {"event": threading.Event(), "result": None, "targets": self.get_target_ips()}
            data = json.dumps({"request_id": rid, "command": cmd_str.strip(),
                               "token": self.control_token or "", "boot_id": self.boot_id,
                               "client_id": self.client_id, "seq": self._sequence}, separators=(",", ":")).encode("utf-8")
            if len(cmd_str.encode('utf-8')) > 2048 or len(data) >= 4096:
                self.last_result = {"status": "error", "error": "command_too_large"}
                return False
            timeout = max(0.05, min(float(timeout), 2.0))
            retries = max(0, min(int(retries), 2))
            with self._pending_lock:
                self._pending[rid] = pending
            try:
                started=time.monotonic()
                attempts=0
                for _ in range(retries + 1):
                    attempts+=1
                    for ip in pending["targets"]:
                        try:
                            self.sock.sendto(data, (ip, self.port))
                        except OSError:
                            continue
                    if pending["event"].wait(timeout):
                        self.last_result = pending["result"] or {"status": "error", "error": "transport_closed"}
                        if self.last_result.get('error') == 'boot_changed':
                            self.boot_id = None # Next explicit request rediscovers, never replay an action on a reboot.
                        self._record_readback(cmd_str,started,attempts,len(data),pending.get('reply_bytes',0),self.last_result)
                        return self.last_result.get("status") == "ok"
                self.last_result = {"request_id": rid, "status": "error", "error": "ack_timeout"}
                self._record_readback(cmd_str,started,attempts,len(data),0,self.last_result)
                return False
            finally:
                with self._pending_lock:
                    self._pending.pop(rid, None)

    def broadcast_command(self, cmd_str: str) -> bool:
        return self.send_command(cmd_str)

    def _record_readback(self,command,started,attempts,wire_bytes,reply_bytes,result):
        try: kind=json.loads(command).get('cmd','text')
        except (ValueError,AttributeError): kind='text'
        if kind not in ('frame','status'): kind='control'
        if not hasattr(self,'_metrics'):return
        with self._pending_lock:
            m=self._metrics.setdefault(kind,dict(requests=0,timeouts=0,errors=0,attempts=0,max_reply_bytes=0,max_ms=0))
            m['requests']+=1;m['attempts']+=attempts
            m['timeouts']+=int(result.get('error')=='ack_timeout')
            m['errors']+=int(result.get('status')!='ok')
            m['last_ms']=round((time.monotonic()-started)*1000,1)
            m['max_ms']=max(m['max_ms'],m['last_ms'])
            m['request_bytes']=wire_bytes;m['max_reply_bytes']=max(m['max_reply_bytes'],reply_bytes)

    def request(self, command):
        try:
            query=json.loads(command)
            read_only=isinstance(query,dict) and (query.get('cmd') in ('frame','status') or
                (query.get('cmd')=='arcade' and query.get('action')=='status'))
        except (ValueError,TypeError):
            query=None
            read_only=False
        if read_only:
            health=query.get('cmd')=='status'
            if health and not hasattr(self,'_status_lock'):
                self._status_lock=threading.Lock();self._status_sequence=self._sequence;self._status_boot=None
            # Share the receiver/pending table, but never the control wait lock,
            # result slot or replay sequence. The identity is stable per client.
            lane=self._status_lock if health else self._read_lock
            if not lane.acquire(blocking=False):
                return {"status":"error","error":"telemetry_busy"}
            try:
                channel=copy.copy(self)
                channel._send_lock=threading.RLock()
                channel.client_id=hashlib.sha256((self.client_id+(':status' if health else ':read')).encode()).hexdigest()[:32]
                channel._sequence=self._status_sequence if health else self._read_sequence
                channel.boot_id=self._status_boot if health else self._read_boot
                if query.get('cmd')=='frame':
                    query['encoding']='base64'
                    command=json.dumps(query,separators=(',',':'))
                # Measured hotspot readbacks take up to 375 ms. One bounded
                # disposable read, no retry storm; controls never take this lock.
                frame_timeout = float(os.environ.get("KURISU_FRAME_TIMEOUT", "0.45"))
                frame_retries = int(os.environ.get("KURISU_FRAME_RETRIES", "0"))
                channel.send_command(command, timeout=frame_timeout, retries=frame_retries)
                if health:self._status_sequence=channel._sequence;self._status_boot=channel.boot_id
                else:self._read_sequence=channel._sequence;self._read_boot=channel.boot_id
                return dict(channel.last_result)
            finally:
                lane.release()
        with self._send_lock:
            if isinstance(query,dict) and query.get('cmd')=='arcade' and query.get('action') in ('input','heartbeat'):
                self.send_command(command,timeout=0.35,retries=1)
            else:
                self.send_command(command)
            return dict(self.last_result)

    def request_audio_ticket(self, timeout: float = 1.0) -> Optional[str]:
        cmd = json.dumps({"cmd": "request_audio_ticket"}, separators=(",", ":"))
        with self._send_lock:
            if self.send_command(cmd, timeout=timeout, retries=1):
                ticket = self.last_result.get("audio_ticket")
                if ticket and isinstance(ticket, str) and len(ticket) == 64:
                    return ticket
        return None

    def broadcast_json(self, payload: Dict[str, Any]) -> bool:
        return self.send_command(json.dumps(payload, separators=(",", ":")))

    def get_status(self) -> Dict[str, Any]:
        with self._pending_lock:
            metrics=copy.deepcopy(getattr(self,'_metrics',{}))
        return {"wifi_online": self.is_online(), "board_sta_ip": self.board_sta_ip,
                "board_ap_ip": self.board_ap_ip, "port": self.port,
                "last_seen_sec": round(time.monotonic() - self.last_seen, 1) if self.last_seen else -1,
                "last_mode": self.last_mode, "last_command": dict(self.last_result),
                "diagnostics":metrics}

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
