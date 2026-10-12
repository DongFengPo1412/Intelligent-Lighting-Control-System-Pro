"""
LightController: 16x16 LED 矩阵硬件驱动控制器 (ESP32-S3 COM9)
基于 USB-Serial-JTAG 硬件直通协议，支持双协议 (纯文本 + 结构化 cJSON)
"""

import sys
import time
import json
import threading
from typing import Optional, Dict, Any
import serial
import serial.tools.list_ports

class LightController:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, timeout: float = 0.5):
        self.baudrate = baudrate
        self.timeout = timeout
        self.port = port or self.auto_detect_port()
        self.ser: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = True
        self.on_mic_data: Optional[Callable[[bytes], None]] = None
        self.on_status_data: Optional[Callable[[Dict[str, Any]], None]] = None

        self.connect()
        self._start_reader()

    def _start_reader(self):
        """启动后台串口数据解复用接收线程 (区分麦克风二进制帧与普通文本/JSON)"""
        if self._rx_thread and self._rx_thread.is_alive():
            return
        self._rx_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._rx_thread.start()

    def _reader_loop(self):
        buf = bytearray()
        while self._running:
            if not self.is_connected or not self.ser or not self.ser.is_open:
                time.sleep(0.1)
                continue
            try:
                raw = self.ser.read(self.ser.in_waiting or 1)
                if not raw:
                    continue
                buf.extend(raw)

                # 解析缓冲区：搜索 0x55 0xAA 二进制音频帧
                while len(buf) > 0:
                    # 查找 0x55 0xAA
                    idx_sync = -1
                    for i in range(len(buf) - 1):
                        if buf[i] == 0x55 and buf[i+1] == 0xAA:
                            idx_sync = i
                            break
                    
                    if idx_sync == -1:
                        # 没有音频同步字，作为普通文本行解析
                        if b'\n' in buf:
                            newline_pos = buf.index(b'\n')
                            line_bytes = buf[:newline_pos].strip()
                            buf = buf[newline_pos+1:]
                            if line_bytes:
                                try:
                                    text = line_bytes.decode('utf-8', errors='ignore')
                                    if text.startswith('{'):
                                        data = json.loads(text)
                                        if self.on_status_data:
                                            self.on_status_data(data)
                                    else:
                                        print(f"[ESP32-S3 Log]: {text}")
                                except Exception:
                                    pass
                        else:
                            # 限制文本缓冲区大小
                            if len(buf) > 512:
                                buf = buf[-128:]
                        break
                    else:
                        # 在同步字之前有普通文本
                        if idx_sync > 0:
                            line_bytes = buf[:idx_sync].strip()
                            buf = buf[idx_sync:]
                            if b'\n' in line_bytes:
                                try:
                                    text = line_bytes.decode('utf-8', errors='ignore')
                                    print(f"[ESP32-S3 Log]: {text}")
                                except Exception:
                                    pass

                        # 检查帧头完整度 0x55 0xAA len_hi len_lo
                        if len(buf) < 4:
                            break
                        payload_len = (buf[2] << 8) | buf[3]
                        if len(buf) < 4 + payload_len:
                            # 帧未收全，等待后续字节
                            break
                        
                        # 完整麦克风音频帧就绪
                        pcm_payload = bytes(buf[4:4 + payload_len])
                        buf = buf[4 + payload_len:]
                        if self.on_mic_data:
                            self.on_mic_data(pcm_payload)
            except Exception as e:
                time.sleep(0.05)

    def auto_detect_port(self) -> str:
        """自动搜寻 ESP32-S3 JTAG 端口 (VID:PID = 303A:1001) 或回退至 COM9"""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if p.vid == 0x303A and p.pid == 0x1001:
                return p.device
            if "JTAG" in p.description or "ESP32" in p.description:
                return p.device
        # 默认回退到已经验证成功的 COM9
        return "COM9"

    def connect(self) -> bool:
        """建立串口物理连接"""
        with self._lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
                self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                time.sleep(0.1) # 等待 DTR/RTS 稳定
                self.is_connected = True
                print(f"[LightController] 成功连接 ESP32-S3 光场与声学硬件: {self.port}")
                return True
            except Exception as e:
                self.is_connected = False
                print(f"[LightController] 警告: 无法连接端口 {self.port} ({e})")
                return False

    def send_raw(self, line: str) -> bool:
        """发送单行原始指令"""
        with self._lock:
            if not self.is_connected or not self.ser:
                if not self.connect():
                    return False
            try:
                msg = (line.strip() + "\n").encode("utf-8")
                self.ser.write(msg)
                self.ser.flush()
                return True
            except Exception as e:
                print(f"[LightController] 串口写入失败: {e}")
                self.is_connected = False
                return False

    def send_json(self, payload: Dict[str, Any]) -> bool:
        """发送标准 cJSON 指令包"""
        return self.send_raw(json.dumps(payload, separators=(',', ':')))

    def play_audio_pcm(self, pcm_data: bytes, chunk_samples: int = 256) -> bool:
        """
        向板载 MAX98357A 扬声器下行直推 16kHz 16-bit 单声道 PCM 音频流
        协议格式: [0xAA, 0x55, len_hi, len_lo, <pcm payload>]
        """
        if not pcm_data:
            return False
            
        chunk_bytes = chunk_samples * 2 # 16-bit = 2 bytes/sample
        total_len = len(pcm_data)
        offset = 0

        # 每块 256 samples 在 16kHz 下对应 16ms 播放时长
        chunk_interval = chunk_samples / 16000.0 * 0.85 # 略快于实时率送入硬件 DMA 缓冲

        with self._lock:
            if not self.is_connected or not self.ser:
                if not self.connect():
                    return False

            try:
                while offset < total_len:
                    part = pcm_data[offset : offset + chunk_bytes]
                    part_len = len(part)
                    header = bytearray([0xAA, 0x55, (part_len >> 8) & 0xFF, part_len & 0xFF])
                    self.ser.write(header + part)
                    offset += part_len
                    time.sleep(chunk_interval)
                self.ser.flush()
                return True
            except Exception as e:
                print(f"[LightController] 音频推流异常: {e}")
                return False

    def enable_mic(self, enable: bool = True) -> bool:
        """开启或暂停 ESP32 板载 INMP441 麦克风音频流上传"""
        print(f"[LightController] 设置板载麦克风数据流: {'开启' if enable else '关闭'}")
        return self.send_json({"cmd": "mic", "enable": enable})

    def play_beep(self) -> bool:
        """触发硬件板载提示音"""
        return self.send_json({"cmd": "beep"})

    # ==========================
    # 核心具身光场交互 API
    # ==========================

    def countdown(self, seconds: int) -> bool:
        """启动物理沙漏倒计时 (秒)"""
        print(f"[具身指令] 启动物理沙漏倒计时: {seconds} 秒")
        return self.send_json({"cmd": "countdown", "seconds": int(seconds)})

    def stop_countdown(self) -> bool:
        """停止倒计时"""
        print(f"[具身指令] 停止物理倒计时")
        return self.send_json({"cmd": "stop_countdown"})

    def set_theme(self, theme: str) -> bool:
        """设置视觉主题 (fire, matrix, rainbow, aurora, meteor, stars, ripple, smile, cry, neutral, dynamic, off)"""
        theme_map = {
            "fire": "fire",
            "flame": "fire",
            "matrix": "matrix",
            "code": "matrix",
            "rainbow": "rainbow",
            "aurora": "aurora",
            "meteor": "meteor",
            "stars": "stars",
            "star": "stars",
            "ripple": "ripple",
            "smile": "smile",
            "cry": "cry",
            "neutral": "neutral",
            "dynamic": "dynamic",
            "off": "off"
        }
        cmd = theme_map.get(theme.lower().strip(), "rainbow")
        print(f"[具身指令] 切换光场特效主题: {cmd}")
        return self.send_raw(cmd)

    def set_brightness(self, val: int) -> bool:
        """调整全局亮度 (1-255，推荐 10-30 以维持 3.3V 单端总线安全)"""
        val = max(1, min(60, int(val)))
        print(f"[具身指令] 设置亮度: {val}")
        return self.send_json({"cmd": "brightness", "val": val})

    def trigger_steins_gate(self) -> bool:
        """
        触发《命运石之门》世界线变动率彩蛋:
        乱数滚动震颤 -> 切换至绿光代码雨 -> 定格生命微表情，代表收敛至 1.048596% 命运石之门世界线
        """
        print("[具身指令] ★★★ 触发世界线变动率 1.048596% (Steins;Gate) ★★★")
        # 1. 乱数闪烁震荡 (先切烈焰激发物理扰动)
        self.set_theme("fire")
        time.sleep(0.35)
        # 2. 模拟辉光管高频刷新 (流星穿梭)
        self.set_theme("meteor")
        time.sleep(0.35)
        # 3. 绿光字符矩阵暴走 (矩阵代码雨)
        self.set_theme("matrix")
        time.sleep(1.2)
        # 4. 锁定在灵动的红莉栖微表情
        self.set_theme("dynamic")
        return True

    def close(self):
        self._running = False
        with self._lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.is_connected = False
                print("[LightController] 串口已释放")

# 单例导出
_controller_instance: Optional[LightController] = None

def get_light_controller() -> LightController:
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = LightController()
    return _controller_instance
