"""
LightController: acknowledged Wi-Fi control and USB/optional Wi-Fi PCM audio.
Simulation substitutes the controller without opening any devices.
"""

import os
import sys
import time
import json
import threading
from typing import Optional, Dict, Any, Callable
import serial
import serial.tools.list_ports
from pro_control import ProControlMixin, DIRECT_MODES, integer

class LightController(ProControlMixin):
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, timeout: float = 0.5):
        self.baudrate = baudrate
        self.timeout = timeout
        self.port = port or self.auto_detect_port()
        self.ser: Optional[serial.Serial] = None
        self._lock = threading.RLock()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = True
        self._mic_enabled = False
        self.on_mic_data: Optional[Callable[[bytes], None]] = None
        self.on_status_data: Optional[Callable[[Dict[str, Any]], None]] = None
        self._chime_pcm: bytes = self._create_chime_pcm()
        self.audio_transport = os.environ.get('KURISU_AUDIO_TRANSPORT', 'usb')
        self._network_audio = None
        self.playback_cancel = threading.Event()
        self.playback_started_at = None

        if self.audio_transport == 'wifi':
            self.is_connected = False
        else:
            self.connect()
            self._start_reader()

    @property
    def audio_connected(self):
        return self.is_connected or bool(self._network_audio and self._network_audio.connected)

    def connect_audio(self):
        if self.audio_transport != 'wifi':return self.is_connected
        if self._network_audio is None:
            from network_audio import WiFiPcmClient
            self._network_audio = WiFiPcmClient(self)
        return self._network_audio.connect()

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
        """建立串口物理连接 (用于物理供电与底层声学流，交互控制恒定使用 WiFi)"""
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
                print(f"[LightController] 识别到 ESP32-S3 USB 接口: {self.port} (核心交互控制强制通过 WiFi 通信)")
                return True
            except Exception as e:
                self.is_connected = False
                print("[LightController] 识别为外部独立电源供电模式 (核心交互控制强制通过 WiFi 通信)")
                return False

    def send_raw(self, line: str) -> bool:
        """
        发送单行控制指令 (核心规范: 恒定必须使用 WiFi 通信)
        不论是 USB 接在电脑上还是外部单独供电，所有光场与交互控制指令均强制使用 WiFi (UDP 8888) 发送与执行！
        """
        line_clean = line.strip()
        if not line_clean:
            return False

        from wifi_gateway import get_wifi_gateway
        return get_wifi_gateway().send_command(line_clean)

    @property
    def control_connected(self) -> bool:
        from wifi_gateway import get_wifi_gateway
        return get_wifi_gateway().is_online()

    def wait_for_control(self, timeout: float = 8.0) -> bool:
        from wifi_gateway import get_wifi_gateway
        gateway = get_wifi_gateway()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if gateway.send_command('{"cmd":"status"}', timeout=0.3, retries=0):
                return True
            time.sleep(0.1)
        return False

    def send_json(self, payload: Dict[str, Any]) -> bool:
        """发送标准 cJSON 指令包"""
        return self.send_raw(json.dumps(payload, separators=(',', ':')))

    def command_result(self, payload):
        from wifi_gateway import get_wifi_gateway
        return get_wifi_gateway().request(json.dumps(payload, separators=(',', ':')))

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
        if len(pcm_data) % 2:
            raise ValueError('PCM16 payload must contain complete samples')
        if getattr(self, 'audio_transport', 'usb') == 'wifi':
            if not self.connect_audio():return False
            ok = self._network_audio.play(pcm_data, chunk_samples)
            self.last_audio_error = self._network_audio.last_error if not ok else None
            return ok
        self.playback_cancel.clear()
        self.last_audio_error = None
            
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

            restore_mic = self._mic_enabled
            muted = False
            try:
                # 硬件级静音：下发关闭麦克风推流指令，杜绝扬声器自激啸叫与回声循环
                if not self.enable_mic(False):
                    return False
                muted = True
                time.sleep(0.04)
                before_audio = self.command_result({'cmd': 'status'})
                if before_audio.get('status')!='ok':
                    return False

                # 设定 120ms 的前置安全蓄水深度，无论多长音频均严控水位不溢出、不欠载
                target_lead_sec = 0.120
                start_clock = time.perf_counter()
                self.playback_started_at = time.monotonic()

                while offset < total_len:
                    if self.playback_cancel.is_set():
                        self.send_json({'cmd':'audio_abort'})
                        self.last_audio_error='playback_cancelled'
                        return False
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

                # Sending bytes is not playback confirmation. Check board counters.
                after_audio = self.command_result({'cmd': 'status'})
                if after_audio.get('status')!='ok':
                    self.last_audio_error = 'audio_status_timeout'
                    return False
                expected = total_len // 2
                delta = {key: (after_audio.get(key, 0) - before_audio.get(key, 0)) & 0xffffffff
                         for key in ('audio_rx', 'audio_played', 'audio_dropped', 'audio_errors')}
                ok = ('audio_played' in before_audio and delta['audio_rx'] == expected
                      and delta['audio_played'] == expected and not delta['audio_dropped'] and not delta['audio_errors'])
                if not ok:
                    self.last_audio_error = {'expected_samples': expected, **delta}
                    print(f'[板端音频未完整确认]: {self.last_audio_error}')
                return ok
            except Exception as e:
                print(f"[LightController] 音频推流异常: {e}")
                return False
            finally:
                # Preserve the listener's pause ownership: playback must not
                # re-enable capture while the model callback is still running.
                if muted and restore_mic:
                    self.enable_mic(True)
                if has_winmm:
                    try:
                        ctypes.windll.winmm.timeEndPeriod(1)
                    except Exception:
                        pass

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
        return self.send_json({"cmd": "volume", "val": integer(volume,0,100)})

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
            if not self.wait_for_control(3.0):
                print("[配对失败] 未收到 Wi-Fi 回执")
                return False
            if not self.set_board_led("pairing"):
                return False
            time.sleep(0.4)
            if not self.set_board_led("connected"):
                return False
            if not self.play_beep():
                print("[配对] 控制已连接，但提示音播放失败")
            time.sleep(0.2)
            return self.set_board_led("listening")

        if async_mode:
            thread = threading.Thread(target=_ceremony, daemon=True)
            thread.start()
            return thread
        return _ceremony()

    # ==========================
    # 核心具身光场交互 API
    # ==========================

    def countdown(self, seconds: int) -> bool:
        """启动物理沙漏倒计时 (秒)"""
        print(f"[具身指令] 启动物理沙漏倒计时: {seconds} 秒")
        if isinstance(seconds, bool) or not isinstance(seconds, int):
            raise ValueError("Countdown seconds must be an integer")
        if not 1 <= seconds <= 86400:
            raise ValueError("Countdown must be between 1 and 86400 seconds")
        if hasattr(self,'_vision_hub'):self._vision_hub.manual_mode(25)
        return self.send_json({"cmd": "countdown", "seconds": seconds})

    def stop_countdown(self) -> bool:
        """停止倒计时"""
        print(f"[具身指令] 停止物理倒计时")
        return self.send_json({"cmd": "stop_countdown"})

    def enable_mic(self, enable: bool = True) -> bool:
        """开启或挂起 ESP32-S3 板载 INMP441 麦克风硬件音频采集回传"""
        print(f"[具身指令] 板载麦克风数据流: {'开启' if enable else '挂起'}")
        if enable and getattr(self,'audio_transport','usb')=='wifi' and not self.connect_audio():return False
        ok = self.send_json({"cmd": "mic", "enable": bool(enable)})
        if ok:
            self._mic_enabled = bool(enable)
        return ok

    def set_mode(self, mode_num: int) -> bool:
        """Select a direct mode (0..31 except 18/25); countdown requires seconds."""
        print(f"[具身指令] 设置模式编号: {mode_num}")
        if isinstance(mode_num, bool) or not isinstance(mode_num, int):
            raise ValueError("Mode must be an integer")
        if mode_num not in DIRECT_MODES:
            raise ValueError("Invalid display mode")
        if hasattr(self,'_arbiter'):self._arbiter.claim_user()
        if hasattr(self,'_vision_hub'):self._vision_hub.manual_mode(mode_num)
        ok = self.send_json({"cmd": "mode", "val": mode_num})
        music = getattr(self, '_music_player', None)
        if ok and music and music.running and mode_num in (15, 30):
            music.visual_fluid = mode_num == 30
        return ok

    def snake_move(self, dx: int, dy: int) -> bool:
        """贪吃蛇方向输入 (dx: -1, 0, 1; dy: -1, 0, 1)"""
        integer(dx,-1,1);integer(dy,-1,1)
        if abs(dx)+abs(dy)!=1:raise ValueError('Snake direction must be one cardinal step')
        return self.send_json({"cmd": "game", "name": "snake", "dx": dx, "dy": dy})

    def tetris_action(self, action: str) -> bool:
        """俄罗斯方块动作控制 (left, right, rot, drop)"""
        if action not in ('left','right','rot','drop'):raise ValueError('Invalid Tetris action')
        return self.send_json({"cmd": "game", "name": "tetris", "action": action})

    def set_theme(self, theme: str) -> bool:
        """设置视觉主题 (支持英文别名、数字编号、以及语义意象词汇)"""
        theme_str = theme.lower().strip()
        if theme_str in {"countdown", "timer", "hourglass", "sand"}:
            raise ValueError("Countdown requires seconds; use countdown(seconds)")
        
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
            "cycle": "cycle",
            "palette": "cycle",
            "rain": "rain",
            "raindrop": "rain",
            "ocean": "mode 10",
            "sea": "mode 10",
            "feedback": "mode 16",
            "ai": "mode 16",
            "lantern": "mode 23",
            "snake": "mode 19",
            "tetris": "mode 21",
            "spectrum": "mode 15",
        }
        cmd = theme_map.get(theme_str)
        if cmd is None:
            raise ValueError(f"Unknown theme: {theme}")
        print(f"[具身指令] 切换光场特效主题: {cmd}")
        aliases={'fire':23,'matrix':24,'rainbow':4,'aurora':5,'meteor':6,'stars':7,'ripple':10,
                 'smile':11,'cry':12,'neutral':13,'dynamic':14,'kurisu':17,'off':0,'cycle':8,'rain':9}
        return self.set_mode(int(cmd[5:]) if cmd.startswith('mode ') else aliases[cmd])

    def set_brightness(self, val: int) -> bool:
        """调整全局亮度 (1-255，推荐 10-30 以维持 3.3V 单端总线安全)"""
        integer(val,0,60)
        print(f"[具身指令] 设置亮度: {val}")
        return self.send_json({"cmd": "brightness", "val": val})

    def trigger_steins_gate(self) -> bool:
        """
        触发《命运石之门》世界线变动率彩蛋:
        板端数字滚动后锁定 1.048596%；这是作品彩蛋，不是测量值。
        """
        print("[具身指令] ★★★ 触发世界线变动率 1.048596% (Steins;Gate) ★★★")
        return self.set_mode(28)

    def close(self):
        if self._network_audio:self._network_audio.close()
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
        if os.environ.get('KURISU_SIMULATE') == '1':
            from simulator import SimulatedController
            _controller_instance = SimulatedController()
        else:
            _controller_instance = LightController()
    return _controller_instance
