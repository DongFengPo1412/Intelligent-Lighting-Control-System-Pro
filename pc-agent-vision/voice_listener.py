"""
VoiceListener: ESP32-S3 板载 INMP441 数字麦克风实时音频流采集与语音识别中枢 (ASR)
直接接收来自 ESP32-S3 核心通过 USB-Serial-JTAG 硬件直通的 16kHz 16-bit 原始 PCM 流
集成单极点 DC 阻断器、动态自适应能量端点检测 (VAD)、声学防自激回声抑制
本地端侧 Whisper 极速离线识别 (毫秒级响应，原生支持中日双语)
以及【牧濑红莉栖日语名字专属唤醒词门禁系统 (Makise Kurisu)】
"""

import os
import sys
import torch # 优先加载 PyTorch CUDA/cuDNN
import re
import time
import queue
import threading
import collections
from typing import Optional, Callable, Tuple
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import speech_recognition as sr
from light_controller import get_light_controller

# 配置代理兜底
if not os.environ.get("HTTP_PROXY") and not os.environ.get("http_proxy"):
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

class VoiceListener:
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True

        self.is_listening = False
        self.is_paused = False
        self._pcm_queue: queue.Queue = queue.Queue(maxsize=300)
        self._process_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None

        # 唤醒词状态机管理
        self.is_awake = False
        self.last_awake_time = 0.0
        self.awake_timeout = 30.0 # 唤醒后保持活跃的对话窗口 (秒)

        # 硬件控制器引用
        self.controller = get_light_controller()
        self.has_board_audio = False
        self._last_board_frame_time = 0.0

        # DC 阻断滤波器状态 (用于消除 INMP441 MEMS 麦克风硬件直流偏置)
        self._prev_x = 0.0
        self._prev_y = 0.0
        self._dc_alpha = 0.995

        # 初始化本地 faster-whisper 极速离线 ASR 模型
        self.whisper_model = None
        try:
            from faster_whisper import WhisperModel
            print("[VoiceListener] 正在载入本地 Whisper 离线极速语音识别引擎 (CPU int8)...")
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
            print("[VoiceListener] >>> 本地离线 Whisper ASR 引擎就绪 (端侧 0 延迟，0 网络开销，支持中日语) <<<")
        except Exception as e:
            print(f"[VoiceListener 警告] 加载本地 Whisper 失败: {e}，将采用云端兜底")

    def _check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        检验语音文本是否包含牧濑红莉栖的专属日语名字唤醒词
        支持:
          - 日语罗马音/假名: Makise Kurisu, Kurisu, Makise, まきせ くりす, くりす, クリス, マキセ
          - 中文发音识别习惯: 牧濑红莉栖, 红莉栖, 牧濑, 克里斯, 库里斯, 克莉丝, 克里斯蒂娜, 栗子
        返回: (is_wake, stripped_command_text)
        """
        t = text.strip()
        wake_patterns = [
            r'makise\s*kurisu',
            r'kurisu',
            r'makise',
            r'まきせ\s*くりす',
            r'くりす',
            r'クリス',
            r'マキセ',
            r'牧濑\s*红莉栖',
            r'红莉栖',
            r'牧濑',
            r'克里斯蒂娜',
            r'克里斯',
            r'库里斯',
            r'克莉丝',
            r'马奇赛',
            r'马基塞',
            r'苦力苏',
            r'栗子'
        ]
        matched = False
        cleaned = t
        for pat in wake_patterns:
            if re.search(pat, cleaned, flags=re.I):
                matched = True
                cleaned = re.sub(pat, '', cleaned, flags=re.I).strip()
        cleaned = re.sub(r'^[，,。！!？?\s]+', '', cleaned).strip()
        return matched, cleaned

    def _on_board_pcm(self, pcm_bytes: bytes):
        """来自 ESP32-S3 板载 INMP441 麦克风的原始 16kHz PCM 帧回调"""
        if not self.is_listening or self.is_paused:
            return
        self.has_board_audio = True
        self._last_board_frame_time = time.time()
        try:
            self._pcm_queue.put_nowait(pcm_bytes)
        except queue.Full:
            pass

    def pause(self):
        """暂停收音 (在红莉栖扬声器播报时暂停，杜绝声学自激与回声循环)"""
        self.is_paused = True
        while not self._pcm_queue.empty():
            try:
                self._pcm_queue.get_nowait()
            except queue.Empty:
                break

    def resume(self):
        """恢复收音 (播报完毕后重新唤醒板载麦克风监听)"""
        while not self._pcm_queue.empty():
            try:
                self._pcm_queue.get_nowait()
            except queue.Empty:
                break
        self._prev_x = 0.0
        self._prev_y = 0.0
        self.is_paused = False

    def _filter_dc(self, samples: np.ndarray) -> np.ndarray:
        """单极点 IIR 直流滤波 (去除 MEMS 芯片的固有直流电平偏移)"""
        filtered = np.zeros_like(samples, dtype=np.float32)
        curr_x = self._prev_x
        curr_y = self._prev_y
        alpha = self._dc_alpha
        for i in range(len(samples)):
            x = samples[i]
            y = x - curr_x + alpha * curr_y
            filtered[i] = y
            curr_x = x
            curr_y = y
        self._prev_x = curr_x
        self._prev_y = curr_y
        return filtered

    def _recognize_async(self, pcm_bytes: bytes):
        """异步执行语音识别，并通过唤醒词门禁调度交互"""
        def _task():
            try:
                text = ""
                # 1. 优先采用本地离线 Whisper 进行极速识别 (毫秒级)
                if self.whisper_model is not None:
                    try:
                        audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        segments, info = self.whisper_model.transcribe(
                            audio_np,
                            beam_size=1,
                            initial_prompt="牧濑红莉栖 Makise Kurisu まきせくりす クリス 助手"
                        )
                        parts = [s.text.strip() for s in segments]
                        text = " ".join(parts).strip()
                    except Exception as wex:
                        text = ""

                # 2. 若本地引擎输出为空，回退使用 Google ASR
                if not text:
                    try:
                        audio_data = sr.AudioData(pcm_bytes, 16000, 2)
                        text = self.recognizer.recognize_google(audio_data, language="zh-CN")
                    except Exception:
                        text = ""

                if not text or not text.strip():
                    return

                print(f"\n[ESP32-S3 板载麦克风捕获语音]: {text}")

                is_wake, stripped_cmd = self._check_wake_word(text)

                if not self.is_awake:
                    # 当前处于休眠/待唤醒状态
                    if not is_wake:
                        print(f"[VoiceListener 待命]: 未检测到专属唤醒词 'Makise Kurisu'，板载指示灯保持绿色常亮静候呼唤。")
                        return

                    # 成功命中专属唤醒词！
                    print(f"\n★★★★★ [VoiceListener 专属唤醒成功] ★★★★★")
                    print(f">>> 成功识别牧濑红莉栖日语名字唤醒词！系统进入交互状态！")
                    self.is_awake = True
                    self.last_awake_time = time.time()

                    # 1. 即时声光反馈：板载扬声器提示音 + 板载LED切为灵动活跃微呼吸
                    self.controller.play_beep()
                    self.controller.set_board_led("active")

                    # 2. 如果包含紧随的指令 (如 "Makise Kurisu，把灯调成纯蓝模式")
                    if len(stripped_cmd) >= 2:
                        self.pause()
                        try:
                            if self.callback:
                                self.callback(stripped_cmd)
                        finally:
                            pass
                    else:
                        # 仅呼唤了名字：零延迟直推预缓存的红莉栖傲娇原声应答！
                        self.pause()
                        try:
                            cur_dir = os.path.dirname(os.path.abspath(__file__))
                            wake_pcm = os.path.join(cur_dir, "kurisu_wake_reply.pcm")
                            wake_wav = os.path.join(cur_dir, "kurisu_wake_reply.wav")
                            if os.path.exists(wake_pcm):
                                with open(wake_pcm, "rb") as f:
                                    pcm_data = f.read()
                                def _play_pc():
                                    if os.path.exists(wake_wav):
                                        try:
                                            import winsound
                                            winsound.PlaySound(wake_wav, winsound.SND_FILENAME)
                                        except Exception:
                                            pass
                                threading.Thread(target=_play_pc, daemon=True).start()
                                self.controller.play_audio_pcm(pcm_data)
                            else:
                                from voice_engine import get_voice_engine
                                v = get_voice_engine()
                                v.speak("な、何よ？有事快说！\nふん、何用？早く言いなさいよ！", block=True)
                        except Exception as ex:
                            print(f"[VoiceListener 唤醒回复异常]: {ex}")
                        finally:
                            self.resume()

                else:
                    # 当前已经处于唤醒活跃状态 (连续对话中)
                    self.last_awake_time = time.time()
                    cmd_to_send = stripped_cmd if is_wake and len(stripped_cmd) >= 2 else text
                    self.pause()
                    try:
                        if self.callback:
                            self.callback(cmd_to_send)
                    finally:
                        pass

            except Exception as e:
                print(f"[VoiceListener 任务异常]: {e}")

        threading.Thread(target=_task, daemon=True).start()

    def _watchdog_loop(self):
        """后台看门狗：活跃状态超过 30 秒无指令，自动退回板载指示灯绿色常亮待唤醒状态"""
        while self.is_listening:
            time.sleep(1.0)
            if self.is_awake and not self.is_paused:
                if time.time() - self.last_awake_time > self.awake_timeout:
                    print("\n[VoiceListener 待命休眠]: 超过 30 秒无指令输入，板载指示灯自动退回常亮绿色待命状态。")
                    self.is_awake = False
                    self.controller.set_board_led("green") # 板载 LED 保持常亮绿色

    def _process_loop(self):
        """板载麦克风实时音频流处理与智能动态 VAD 端点检测"""
        print("[VoiceListener] 正在接管 ESP32-S3 板载 INMP441 麦克风硬件音频流...")
        preroll_chunks = collections.deque(maxlen=24)
        speech_chunks = []
        is_speaking = False
        silent_count = 0
        ambient_energy = 800.0

        while self.is_listening:
            try:
                pcm_bytes = self._pcm_queue.get(timeout=0.2)
            except queue.Empty:
                if self.is_listening and not self.is_paused and (time.time() - self._last_board_frame_time > 3.0):
                    if self.controller.is_connected:
                        self.controller.enable_mic(True)
                continue

            if self.is_paused:
                speech_chunks.clear()
                is_speaking = False
                silent_count = 0
                continue

            raw_samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            filtered_samples = self._filter_dc(raw_samples)
            rms = float(np.sqrt(np.mean(filtered_samples**2)))

            ambient_energy = 0.98 * ambient_energy + 0.02 * rms
            threshold = max(1600.0, ambient_energy * 2.0)

            if not is_speaking:
                preroll_chunks.append(filtered_samples)
                if rms > threshold:
                    is_speaking = True
                    silent_count = 0
                    speech_chunks = list(preroll_chunks)
                    speech_chunks.append(filtered_samples)
                    tag = "【已唤醒·倾听中】" if self.is_awake else "【待命·等待唤醒词】"
                    print(f"\n[ESP32 板载麦克风: {tag} 正在拾音...]", end="", flush=True)
            else:
                speech_chunks.append(filtered_samples)
                if rms < threshold:
                    silent_count += 1
                    # 动态端点延迟：待唤醒时仅需 16 帧 (~240ms) 静音即判定结束，大幅缩短唤醒延迟！
                    silent_limit = 20 if self.is_awake else 16
                    if silent_count >= silent_limit:
                        is_speaking = False
                        silent_count = 0
                        total_samples = sum(len(c) for c in speech_chunks)
                        if total_samples >= 16000 * 0.5:
                            full_pcm = np.clip(np.concatenate(speech_chunks), -32768, 32767).astype(np.int16).tobytes()
                            self._recognize_async(full_pcm)
                        speech_chunks.clear()
                else:
                    silent_count = 0

    def start(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.is_paused = False
        self.is_awake = False # 初始处于待唤醒状态

        # 1. 注册板载麦克风回调通道
        self.controller.on_mic_data = self._on_board_pcm

        # 2. 向下位机 ESP32-S3 下发启动板载麦克风指令
        if self.controller.is_connected:
            self.controller.enable_mic(True)

        # 3. 启动后台实时 VAD 与看门狗休眠线程
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def stop(self):
        self.is_listening = False
        if self.controller.is_connected:
            self.controller.enable_mic(False)
        self.controller.on_mic_data = None


# 单例导出
_listener_instance: Optional[VoiceListener] = None

def get_voice_listener(callback: Optional[Callable[[str], None]] = None) -> VoiceListener:
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = VoiceListener(callback=callback)
    elif callback is not None:
        _listener_instance.callback = callback
    return _listener_instance
