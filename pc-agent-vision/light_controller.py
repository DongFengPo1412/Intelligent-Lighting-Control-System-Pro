"""
LightController: 16x16 LED 矩阵硬件驱动控制器 (ESP32-S3 COM9)
基于 USB-Serial-JTAG 硬件直通协议，支持双协议 (纯文本 + 结构化 cJSON)
"""

import os
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
        self._lock = threading.RLock()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = True
        self.on_mic_data: Optional[Callable[[bytes], None]] = None
        self.on_status_data: Optional[Callable[[Dict[str, Any]], None]] = None
        self._chime_pcm: bytes = self._create_chime_pcm()

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
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                    self.ser = None
                self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                time.sleep(0.15) # 等待 DTR/RTS 稳定
                self.is_connected = True
                print(f"[LightController] 成功连接 ESP32-S3 光场与声学硬件: {self.port}")
                return True
            except Exception as e:
                self.is_connected = False
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
                try:
                    if self.ser:
                        self.ser.close()
                except Exception:
                    pass
                self.ser = None
                return False

    def send_json(self, payload: Dict[str, Any]) -> bool:
        """发送标准 cJSON 指令包"""
        return self.send_raw(json.dumps(payload, separators=(',', ':')))

    def play_audio_pcm(self, pcm_data: bytes, chunk_samples: int = 512) -> bool:
        """
        向板载 MAX98357A 扬声器下行直推 16kHz 16-bit 单声道 PCM 音频流
        协议格式: [0xAA, 0x55, len_hi, len_lo, <pcm payload>]
        内置基于绝对单调时钟的防溢流控算法：
        - 始终维持 120ms 的 DMA 硬件安全蓄水深度 (Pre-roll Jitter Buffer)
        - 杜绝传统相对 sleep 累计时钟漂移，从数学与通信链路上彻底杜绝溢出丢包与欠载断流
        """
        if not pcm_data:
            return False
            
        chunk_bytes = chunk_samples * 2 # 16-bit = 2 bytes/sample
        total_len = len(pcm_data)
        offset = 0

        # 启用 Windows 1ms 高精度多媒体计时器
        has_winmm = False
        try:
            if sys.platform == 'win32':
                import ctypes
                ctypes.windll.winmm.timeBeginPeriod(1)
                has_winmm = True
        except Exception:
            pass

        with self._lock:
            if not self.is_connected or not self.ser:
                if not self.connect():
                    if has_winmm:
                        ctypes.windll.winmm.timeEndPeriod(1)
                    return False

            try:
                # 硬件级静音：下发关闭麦克风推流指令，杜绝扬声器自激啸叫与回声循环
                try:
                    mute_cmd = b'{"cmd":"mic","enable":false}\n'
                    self.ser.write(mute_cmd)
                    self.ser.flush()
                except Exception:
                    pass

                # 设定 120ms 的前置安全蓄水深度，无论多长音频均严控水位不溢出、不欠载
                target_lead_sec = 0.120
                start_clock = time.perf_counter()

                while offset < total_len:
                    part = pcm_data[offset : offset + chunk_bytes]
                    part_len = len(part)
                    header = bytearray([0xAA, 0x55, (part_len >> 8) & 0xFF, part_len & 0xFF])
                    self.ser.write(header + part)
                    offset += part_len

                    # 16000 采样/秒 * 2 字节/采样 = 32000 字节/秒
                    sent_audio_duration = offset / 32000.0
                    target_time = start_clock + (sent_audio_duration - target_lead_sec)
                    now = time.perf_counter()
                    sleep_time = target_time - now

                    if sleep_time > 0.002: # 超过 2ms 精度则休眠节流，严防 USB RX 缓冲溢出丢包
                        time.sleep(sleep_time)

                self.ser.flush()
                # 确保在退出前让板载 DMA 将最后的尾音完整播完，避免后续指令过早切入造成尾音破损或杂音
                total_duration = total_len / 32000.0
                rem_play = (start_clock + total_duration) - time.perf_counter()
                if rem_play > 0:
                    time.sleep(rem_play)
                
                # 物理消音缓冲：等待 350ms 让空气回声与声学余震彻底消散
                time.sleep(0.35)

                # 清空串口输入缓冲，丢弃播放期间残留的无效数据
                try:
                    self.ser.reset_input_buffer()
                except Exception:
                    pass

                # 硬件级恢复：重新激活麦克风推流
                try:
                    unmute_cmd = b'{"cmd":"mic","enable":true}\n'
                    self.ser.write(unmute_cmd)
                    self.ser.flush()
                except Exception:
                    pass

                return True
            except Exception as e:
                print(f"[LightController] 音频推流异常: {e}")
                return False
            finally:
                if has_winmm:
                    try:
                        ctypes.windll.winmm.timeEndPeriod(1)
                    except Exception:
                        pass

    def enable_mic(self, enable: bool = True) -> bool:
        """开启或暂停 ESP32 板载 INMP441 麦克风音频流上传"""
        print(f"[LightController] 设置板载麦克风数据流: {'开启' if enable else '关闭'}")
        return self.send_json({"cmd": "mic", "enable": enable})

    @staticmethod
    def _create_chime_pcm(sample_rate: int = 16000) -> bytes:
        """生成清脆灵动的配对/唤醒双音阶上扬提示音 (880Hz -> 1320Hz)"""
        try:
            import numpy as np
            t1 = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
            t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
            s1 = np.sin(2 * np.pi * 880 * t1) * 0.45
            s2 = np.sin(2 * np.pi * 1320 * t2) * 0.55
            env1 = np.sin(np.linspace(0, np.pi, len(s1)))**0.5
            env2 = np.sin(np.linspace(0, np.pi, len(s2)))**0.5
            audio = np.concatenate([s1 * env1, s2 * env2])
            return (audio * 32767).astype(np.int16).tobytes()
        except Exception:
            return b""

    def play_beep(self) -> bool:
        """触发硬件板载提示音 (优先通过 I2S 直推清脆灵动上扬和弦，兼发硬件蜂鸣)"""
        if hasattr(self, '_chime_pcm') and self._chime_pcm:
            return self.play_audio_pcm(self._chime_pcm)
        return self.send_json({"cmd": "beep"})

    def set_volume(self, volume: int) -> bool:
        """设置 ESP32-S3 板载扬声器音量 (0-100，默认 70，采用平方律动态调校)"""
        print(f"[LightController] 设置板载扬声器音量: {volume}%")
        return self.send_json({"cmd": "volume", "val": int(volume)})

    def set_board_led(self, mode: str = "green") -> bool:
        """
        控制 ESP32-S3 核心板载独立 RGB 指示灯 (GPIO 48):
        - "pairing" / "breathe": 幽蓝呼吸灯 (模式 1: 等待配对)
        - "speaking": 翠绿色常亮 (模式 2: 正在播报语音)
        - "thinking" / "active": 青蓝微呼吸律动 (模式 3: 思考中/大模型运算)
        - "listening": 微光暗红待命 (模式 4: 静默监听唤醒词)
        - "hearing": 鲜亮红光 (模式 5: 检测到用户说话 VAD 激活)
        - "connected" / "blue": 幽蓝常亮 (模式 6: 握手连接确立)
        - "off": 熄灭
        """
        print(f"[LightController] 设置板载指示灯 (GPIO 48): {mode}")
        return self.send_json({"cmd": "board_led", "mode": mode})

    def run_boot_ceremony(self, async_mode: bool = False):
        """
        执行系统上电与配对连接成功正向反馈仪式感 (严格遵循用户交互规范):
        1. 上电进入配对模式：ESP32-S3 板载独立 LED (GPIO 48) 幽蓝呼吸灯呈现搜寻配对状态
        2. 灯板 (16x16 矩阵) 保持 17 号牧濑红莉栖半身桌宠立绘 (亮度 150)
        3. 配对握手校验成功：
           - 板载 LED 瞬间切换为【常亮幽蓝】确认连接
           - 板载扬声器发出清脆提示音 (play_beep) 确认物理连接确立
        4. 仪式完毕，板载 LED 进入【微光暗红】(listening) 待命状态，绝不自动播报长语音，静默静候唤醒词！
        """
        def _ceremony():
            print("\n[配对模式] >>> ESP32-S3 板载指示灯幽蓝呼吸律动，正在搜寻并建立配对连接... <<<")
            self.set_board_led("pairing") # 幽蓝呼吸
            self.send_raw("kurisu")       # 灯板维持 17 号牧濑红莉栖桌宠立绘
            self.send_raw("b 150")        # 保持 150 黄金亮度
            time.sleep(1.5)

            print("[配对成功] >>> 上位机与 ESP32-S3 配对成功！发出配对成功物理提示音 <<<")
            self.set_board_led("connected") # 幽蓝常亮确立连接
            time.sleep(0.3)
            self.play_beep()                # 板载扬声器发出配对成功提示音
            time.sleep(0.4)

            # 仪式结束，板载 LED 进入微光暗红监听待命状态，绝无任何自动长语音打扰
            self.set_board_led("listening")
            print("[配对完成] >>> 板载指示灯保持微光暗红待命，静候唤醒词 'Makise Kurisu' 唤醒交互 <<<\n")

        if async_mode:
            threading.Thread(target=_ceremony, daemon=True).start()
        else:
            _ceremony()

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

    def enable_mic(self, enable: bool = True) -> bool:
        """开启或挂起 ESP32-S3 板载 INMP441 麦克风硬件音频采集回传"""
        print(f"[具身指令] 板载麦克风数据流: {'开启' if enable else '挂起'}")
        return self.send_json({"cmd": "mic", "enable": bool(enable)})

    def set_mode(self, mode_num: int) -> bool:
        """设置 16x16 矩阵灯板的原生模式编号 (0~25)"""
        print(f"[具身指令] 设置模式编号: {mode_num}")
        return self.send_json({"cmd": "mode", "val": int(mode_num)})

    def snake_move(self, dx: int, dy: int) -> bool:
        """贪吃蛇方向输入 (dx: -1, 0, 1; dy: -1, 0, 1)"""
        return self.send_json({"cmd": "game", "name": "snake", "dx": int(dx), "dy": int(dy)})

    def tetris_action(self, action: str) -> bool:
        """俄罗斯方块动作控制 (left, right, rot, drop)"""
        return self.send_json({"cmd": "game", "name": "tetris", "action": action})

    def set_theme(self, theme: str) -> bool:
        """设置视觉主题 (支持英文别名、数字编号、以及语义意象词汇)"""
        theme_str = theme.lower().strip()
        
        # 如果直接是数字，直接切换编号
        if theme_str.isdigit():
            return self.set_mode(int(theme_str))

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
            "face": "dynamic",
            "emoji": "dynamic",
            "kurisu": "kurisu",
            "pet": "kurisu",
            "off": "off",
            "red": "mode 1",
            "blue": "mode 2",
            "green": "mode 3",
            "ocean": "mode 10",
            "sea": "mode 10",
            "lantern": "mode 23",
            "snake": "mode 19",
            "tetris": "mode 21",
            "spectrum": "mode 15"
        }
        cmd = theme_map.get(theme_str, "rainbow")
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
