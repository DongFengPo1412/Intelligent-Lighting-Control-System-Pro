"""
WiFiGateway: 局域网高速无线通信网关 (UDP 广播与 WebSocket 双工流)
摆脱物理 USB 串口数据线束缚，实现 PC 端 Agent 到 ESP32-S3 边缘光场的无线毫秒级直连
"""

import socket
import json
import threading
import time
from typing import Optional, Dict, Any

class WiFiGateway:
    def __init__(self, port: int = 8888, broadcast_ip: str = "255.255.255.255"):
        self.port = port
        self.broadcast_ip = broadcast_ip
        self.sock: Optional[socket.socket] = None
        self.is_running = False
        self._init_socket()

    def _init_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", self.port))
            self.sock.settimeout(0.5)
            self.is_running = True
            print(f"[WiFiGateway] 无线 UDP 物联网网关已在端口 {self.port} 监听就绪")
        except Exception as e:
            print(f"[WiFiGateway] UDP 端口初始化异常: {e}")

    def broadcast_command(self, cmd_str: str) -> bool:
        """向局域网广播光场控制指令"""
        if not self.sock:
            return False
        try:
            data = (cmd_str.strip() + "\n").encode("utf-8")
            self.sock.sendto(data, (self.broadcast_ip, self.port))
            return True
        except Exception as e:
            print(f"[WiFiGateway] 广播发送失败: {e}")
            return False

    def broadcast_json(self, payload: Dict[str, Any]) -> bool:
        """广播结构化 cJSON 指令包"""
        return self.broadcast_command(json.dumps(payload, separators=(',', ':')))

    def close(self):
        self.is_running = False
        if self.sock:
            self.sock.close()
            self.sock = None

# 单例导出
_wifi_instance: Optional[WiFiGateway] = None

def get_wifi_gateway() -> WiFiGateway:
    global _wifi_instance
    if _wifi_instance is None:
        _wifi_instance = WiFiGateway()
    return _wifi_instance
