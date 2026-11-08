"""Optional LAN DNS-SD and UDP auto-discovery; simulation never starts this service."""

import ipaddress
import json
import os
import socket
import threading

DISCOVERY_PORT = 8890


def _is_private_lan_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_IPv4 if hasattr(addr, "is_IPv4") else (addr.version == 4 and (addr.is_private or addr.is_loopback))
    except Exception:
        return False


class ServiceAdvertisement:
    def __init__(self):
        self.zeroconf = None
        self.info = None
        self.error = None
        self.udp_sock = None
        self.udp_running = False
        self.udp_thread = None

    def start(self, host, port):
        if host == "127.0.0.1" or os.environ.get("KURISU_SIMULATE") == "1":
            return
        self._start_udp_responder(host, port)
        try:
            from zeroconf import Zeroconf, ServiceInfo

            self.zeroconf = Zeroconf()
            self.info = ServiceInfo(
                "_kurisupro._tcp.local.",
                "KurisuPro._kurisupro._tcp.local.",
                addresses=[socket.inet_aton(host)],
                port=port,
                properties={"path": "/pro.html", "version": "2"},
            )
            self.zeroconf.register_service(self.info, allow_name_change=True)
        except Exception as exc:
            self.error = str(exc)

    def _start_udp_responder(self, default_host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.5)
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            self.udp_sock = sock
            self.udp_running = True
            self.udp_thread = threading.Thread(
                target=self._udp_loop,
                args=(default_host, port),
                daemon=True,
                name="kurisu_udp_discovery",
            )
            self.udp_thread.start()
        except Exception as exc:
            self.error = str(exc)

    def _build_discovery_payload(self, peer_ip, default_host, port):
        host_ip = default_host
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect((peer_ip, 80))
            host_ip = probe.getsockname()[0]
            probe.close()
        except Exception:
            pass
        board_ip = os.environ.get("KURISU_BOARD_IP", "")
        try:
            from wifi_gateway import get_wifi_gateway
            gw = get_wifi_gateway()
            if getattr(gw, "board_sta_ip", "") and gw.board_sta_ip != "0.0.0.0":
                board_ip = gw.board_sta_ip
        except Exception:
            pass
        # Security: Never transmit access_token or control_token over unauthenticated discovery broadcast.
        # Clients must authenticate/pair independently via explicit user authorization.
        return json.dumps({
            "service": "KurisuPro",
            "server_url": f"http://{host_ip}:{port}",
            "host": host_ip,
            "port": port,
            "version": "2.1.2",
            "board_ip": board_ip,
            "pairing_required": True,
        }, separators=(",", ":")).encode("utf-8")

    def _udp_loop(self, default_host, port):
        while self.udp_running and self.udp_sock:
            try:
                raw, addr = self.udp_sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            peer_ip = addr[0]
            if not _is_private_lan_ip(peer_ip):
                continue
            try:
                msg = json.loads(raw.decode("utf-8", errors="ignore").strip())
                if isinstance(msg, dict) and msg.get("cmd") == "kurisu_discover":
                    reply = self._build_discovery_payload(peer_ip, default_host, port)
                    self.udp_sock.sendto(reply, addr)
            except Exception:
                continue

    def close(self):
        self.udp_running = False
        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
            self.udp_sock = None
        if self.udp_thread and self.udp_thread.is_alive():
            self.udp_thread.join(timeout=0.6)
        self.udp_thread = None
        if self.zeroconf:
            try:
                if self.info:
                    self.zeroconf.unregister_service(self.info)
            except Exception as exc:
                self.error = str(exc)
            finally:
                self.zeroconf.close()
                self.zeroconf = None
                self.info = None
