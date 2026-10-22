"""Optional LAN DNS-SD advertisement; simulation never starts this service."""

import socket


class ServiceAdvertisement:
    def __init__(self):
        self.zeroconf = None
        self.info = None
        self.error = None

    def start(self, host, port):
        if host == "127.0.0.1":
            return
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
            self.close()

    def close(self):
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
